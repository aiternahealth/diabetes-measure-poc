"""MCP server exposing the DCG agent contract (dcg/agent/dcg_agent_contract.yaml) to Claude.

Tools: resolve_terms, list_metrics, describe_metric, explain_concept, query_metrics, run_saved_query,
compare_to_benchmark, explain_measure, cohort_evidence_summary, stewardship_queue.
Guardrails are enforced HERE, not left to the model: aggregate-only results, small-cell suppression,
<= 3 group-bys, restricted FSA combinations, equity stratifiers only for the equity role and one at a
time, governed metrics only. Every answer carries the data currency (period end, load time) and lineage
(phenotype and terminology-map versions).

Register with Claude Desktop: `make mcp-config` prints the JSON block to add.
"""
import json
import os
import re
import sys
from pathlib import Path

import datetime

import duckdb
import rdflib
import yaml
from mcp.server.mcpserver import MCPServer   # MCP Python SDK 2.x (FastMCP was renamed MCPServer)
from rdflib.namespace import RDF, RDFS, SKOS

ROOT = Path(__file__).resolve().parent.parent
DCGDIR = ROOT / "dcg"
sys.path.insert(0, str(DCGDIR / "scripts"))
from run_pipeline import MET, MEAS, SM, query_metric  # noqa: E402

DB = os.environ.get("DCG_DUCKDB", str(ROOT / "data" / "dcg.duckdb"))
VARS = yaml.safe_load(open(DCGDIR / "dbt_project.yml"))["vars"]
MIN_CELL = int(VARS.get("min_cell_size", 5))
TERMS = json.load(open(DCGDIR / "agent" / "term_index.json"))
NS = "https://ontology.hac-poc.example/dcg#"
ONTO = rdflib.Graph().parse(DCGDIR / "ontology" / "dcg-ontology.ttl")
DCG = rdflib.Namespace(NS)
DIMS = {d["name"] for s in SM["semantic_models"] for d in s["dimensions"]}
EQUITY_DIMS = {"service_language", "indigenous_identity", "racialized_group"}
EQUITY_ROLE = os.environ.get("DCG_EQUITY_ROLE", "").lower() in ("1", "true", "yes")   # set only for the restricted equity role
ALL_METRICS = set(MET) | set(MEAS)

mcp = MCPServer(
    "dcg-care-gaps",
    instructions="Governed diabetes care-gap analytics. Answer only from query_metrics results; report suppressed cells as 'suppressed (<5)'; label synthetic data; state the period end and data load time; give no advice about individual patients. Start with resolve_terms, then describe_metric. For a cohort profile use run_saved_query('cohort_profile'), then group by age_band and sex for distributions. For the DCI measure set use run_saved_query('dci_core_measures'). To explain where a number comes from use explain_measure; to explain who is in the cohort use cohort_evidence_summary. Lead with at-target rates; means and medians of BP or BMI are context only. The diabetes type is a heuristic; say so when reporting by type.",
)


def _con():
    return duckdb.connect(DB, read_only=True)


def _context():
    with _con() as con:
        pe, src, pid, pver, mver = con.execute(
            "select max(period_end), max(data_source), max(phenotype_id), max(phenotype_version), max(map_version) from fct_diabetes_patient_period").fetchone()
    loaded = datetime.datetime.fromtimestamp(os.path.getmtime(DB)).isoformat(timespec="minutes") if os.path.exists(DB) else None
    return {"period_end": str(pe), "data_source": src, "data_loaded_at": loaded,
            "lineage": {"phenotype": f"{pid} v{pver}", "terminology_map_version": mver},
            "data_label": "synthetic data — not real-world performance" if src == "synthetic" else None}


def _dim(name):
    name = name.split("__")[-1]
    if name not in DIMS:
        raise ValueError(f"Unknown dimension '{name}'. Available: {sorted(DIMS)}")
    return name


@mcp.tool()
def resolve_terms(text: str) -> list[dict]:
    """Map words in the user's request to governed metrics, dimensions and ontology classes. Call first."""
    t = " " + re.sub(r"[^a-z0-9%<>.+ ]", " ", text.lower()) + " "
    hits = []
    for term, entries in TERMS.items():
        if len(term) >= 2 and f" {term} " in t:
            for e in entries:
                hits.append({"term": term, **e, "score": round(min(1.0, 0.4 + len(term) / 25), 2)})
    hits.sort(key=lambda h: (-h["score"], h["kind"]))
    seen, out = set(), []
    for h in hits:
        key = (h["kind"], h.get("name") or h.get("iri"))
        if key not in seen:
            seen.add(key)
            out.append(h)
    return out[:15]


@mcp.tool()
def list_metrics(search: str = "") -> list[dict]:
    """List governed metrics (name, label, unit, direction, description). Optional text filter."""
    out = []
    for m in SM["metrics"]:
        meta = m.get("config", {}).get("meta", {})
        row = {"name": m["name"], "label": m["label"], "unit": meta.get("unit"), "direction": meta.get("direction"),
               "description": m["description"]}
        if not search or search.lower() in json.dumps(row).lower() or any(search.lower() in s for s in meta.get("synonyms", [])):
            out.append(row)
    return out


@mcp.tool()
def describe_metric(name: str) -> dict:
    """Full definition of a metric: numerator, denominator, parameters in force, caveats, benchmark, ontology."""
    if name not in MET:
        raise ValueError(f"'{name}' is not a governed metric. Use list_metrics or resolve_terms.")
    m = MET[name]
    tp = m["type_params"]
    parts = {k: {"measure": tp[k], "definition": MEAS[tp[k]][1]["description"]} for k in ("numerator", "denominator", "measure") if k in tp}
    return {"name": name, "label": m["label"], "type": m["type"], "description": m["description"], **parts,
            "meta": m.get("config", {}).get("meta", {}), "parameters_in_force": VARS, **_context()}


@mcp.tool()
def explain_concept(iri: str) -> dict:
    """Ontology lookup for a class or concept, e.g. 'dcg:HbA1cResult': definition, synonyms, FHIR binding, codes, hints."""
    s = rdflib.URIRef(NS + iri.split(":", 1)[1]) if iri.startswith("dcg:") else rdflib.URIRef(iri)
    if (s, None, None) not in ONTO:
        raise ValueError(f"Unknown concept {iri}")
    q = lambda p: [str(o) for o in ONTO.objects(s, p)]  # noqa: E731
    out = {"iri": iri, "label": q(RDFS.label), "definition": q(SKOS.definition), "synonyms": q(SKOS.altLabel),
           "parents": [str(o).replace(NS, "dcg:") for o in ONTO.objects(s, RDFS.subClassOf)]}
    for prop in ("fhirResourceType", "fhirPath", "caCorePlusProfile", "profileMaturity", "cacdiDataClass",
                 "semanticModelRef", "sourceGuideline", "agentHint", "sensitivity"):
        v = q(DCG[prop])
        if v:
            out[prop] = v
    for vs in ONTO.objects(s, DCG.hasValueSet):
        out.setdefault("codes", []).extend(
            {"code": str(ONTO.value(c, SKOS.notation)), "display": str(ONTO.value(c, SKOS.prefLabel))}
            for c in ONTO.subjects(SKOS.inScheme, vs))
    return out


@mcp.tool()
def query_metrics(metrics: list[str], group_by: list[str] | None = None, where: dict[str, str] | None = None) -> dict:
    """Run governed metrics. group_by: up to 3 dimension names (e.g. age_band, sex, province, diabetes_type).
    where: {dimension: value} equality filters (e.g. {"diabetes_type": "type_2", "age_band": "65+"}).
    Cells with fewer than 5 people come back suppressed — report them as 'suppressed (<5)', never back-calculate."""
    group_by = [_dim(g) for g in (group_by or [])]
    where = {_dim(k): v for k, v in (where or {}).items()}
    if not 1 <= len(metrics) <= 20:
        raise ValueError("Ask for 1 to 20 metrics.")
    if len(group_by) > 3:
        raise ValueError("At most 3 group_by dimensions.")
    used = set(group_by + list(where))
    if "fsa" in used and len(used - {"fsa"}) > 1:
        raise ValueError("FSA is restricted: use it alone or with one other dimension.")
    if used & EQUITY_DIMS:
        if not EQUITY_ROLE:
            raise ValueError("Equity stratifiers (service language, Indigenous identity, racialized group) need the restricted equity role.")
        if len(used & EQUITY_DIMS) > 1 or "fsa" in used or len(used) > 2:
            raise ValueError("Use one equity stratifier at a time, with at most one other dimension and never with FSA.")
    unknown = [m for m in metrics if m not in ALL_METRICS]
    if unknown:
        raise ValueError(f"Not governed metrics: {unknown}. Use list_metrics; do not compute ad-hoc rates.")
    results = {}
    with _con() as con:
        for m in metrics:
            rows = query_metric(con, m, group_by=tuple(group_by), where=where or None, min_cell=MIN_CELL)
            results[m] = [{**dict(zip(group_by, k)), **{kk: vv for kk, vv in cell.items()}} for k, cell in sorted(rows.items(), key=str)]
    return {"results": results, "group_by": group_by, "where": where, "min_cell_size": MIN_CELL,
            "parameters_in_force": VARS, **_context()}


@mcp.tool()
def run_saved_query(name: str, group_by: list[str] | None = None) -> dict:
    """Run a governed saved query from the semantic model, e.g. 'cohort_profile' (use it for "profile the
    diabetes patients"), 'care_gap_scorecard', 'gaps_by_age_sex' or 'data_quality_panel'. Optional group_by
    (up to 3 dimensions) overrides the saved grouping, e.g. ['age_band'] or ['sex'] for distributions."""
    saved = {q["name"]: q for q in SM.get("saved_queries", [])}
    if name not in saved:
        raise ValueError(f"Unknown saved query '{name}'. Available: {sorted(saved)}")
    params = saved[name]["query_params"]
    if group_by is None:
        group_by = [re.search(r"__(\w+)'", g).group(1) for g in params.get("group_by", [])
                    if g.startswith("Dimension(")]
    out = query_metrics(params["metrics"], group_by=group_by)
    out["saved_query"] = {"name": name, "description": saved[name]["description"]}
    return out


@mcp.tool()
def compare_to_benchmark(metric: str) -> dict:
    """The published benchmark linked to a metric, with comparability notes. Never invents a value."""
    meta = MET.get(metric, {}).get("config", {}).get("meta", {})
    bm = meta.get("benchmark")
    if not bm:
        return {"metric": metric, "benchmark": None, "note": "No benchmark is linked to this metric."}
    s = rdflib.URIRef(NS + bm["ref"].split(":", 1)[1])
    return {"metric": metric, "benchmark": {**bm, "label": str(ONTO.value(s, RDFS.label)),
            "source": str(ONTO.value(s, rdflib.URIRef("http://purl.org/dc/terms/source"))),
            "notes": str(ONTO.value(s, RDFS.comment))}, "caveats": meta.get("caveats", [])}


@mcp.tool()
def explain_measure(metric: str) -> dict:
    """Evidence trail of a metric at the definition level: the mart columns and intermediate models it is built
    from, the FHIR views and resources behind them, the value sets (with terminology-map status) and the case
    phenotype and map versions in force. Person-level evidence is not exposed in this PoC."""
    d = describe_metric(metric)
    measures = [d[k]["measure"] for k in ("numerator", "denominator", "measure") if k in d]
    if MET[metric]["type"] == "derived":
        measures = [x["name"] for x in MET[metric]["type_params"]["metrics"]]
    exprs = {m: MEAS[m][1]["expr"] for m in measures if m in MEAS}
    onto_iris = {v for k, v in d["meta"].items() if k.startswith("ontology") and isinstance(v, str)}
    onto_iris |= {MEAS[m][1]["config"]["meta"]["ontology"] for m in exprs}
    value_sets = {"vs_DiabetesMellitus", "vs_T1DM", "vs_T2DM", "vs_HbA1c", "vs_GDM"}   # cohort phenotype, behind every measure
    value_sets |= set(d["meta"].get("value_sets", []))
    for iri in onto_iris:
        node = rdflib.URIRef(NS + iri.split(":", 1)[1])
        for cls in [node, *ONTO.objects(node, RDFS.subClassOf), *ONTO.subjects(RDFS.subClassOf, node)]:
            value_sets |= {str(o).replace(NS, "") for o in ONTO.objects(cls, DCG.hasValueSet)}
        for ev in ONTO.objects(node, DCG.evidencedBy):
            value_sets |= {str(o).replace(NS, "") for o in ONTO.objects(ev, DCG.hasValueSet)}
    with _con() as con:
        maps = con.execute(
            "select value_set, map_status, count(*) from seed_code_valueset where value_set in (select unnest(?)) group by 1, 2 order by 1, 2",
            [sorted(value_sets)]).fetchall() if value_sets else []
    return {"metric": metric, "label": d["label"], "measures": exprs,
            "built_from": {"mart": "fct_diabetes_patient_period" if all(MEAS[m][0]["name"] == "diabetes_patient_period" for m in exprs) else "fct_adult_population_period",
                           "intermediate_models": ["int_dm_case_evidence (cohort)", "int_condition_coded", "int_observation_std", "int_medication_exposure"],
                           "fhir_views": ["dcg_patient", "dcg_condition", "dcg_encounter", "dcg_observation", "dcg_blood_pressure",
                                          "dcg_medication_request", "dcg_medication_dispense", "dcg_procedure"]},
            "value_sets": [{"value_set": v, "map_status": st, "codes": n} for v, st, n in maps],
            "parameters_in_force": VARS, **_context()}


@mcp.tool()
def cohort_evidence_summary(group_by: str | None = None) -> dict:
    """Why people are in the diabetes cohort: counts by the evidence route that qualified them under case
    phenotype DM-ADULT-CASE (hospital diagnosis, two ambulatory diagnoses, declared condition, two HbA1c at or
    above threshold), plus the people with medication only who are NOT in the cohort. Optional group_by: one
    dimension. Small cells suppressed."""
    out = query_metrics(["cohort_size"], group_by=["case_basis"] + ([group_by] if group_by else []))
    out["possible_cases_med_only"] = query_metrics(["possible_cases_med_only"])["results"]["possible_cases_med_only"]
    out["phenotype_definition"] = str(ONTO.value(DCG.pheno_DM_ADULT_CASE, SKOS.definition))
    return out


@mcp.tool()
def stewardship_queue(limit: int = 25) -> dict:
    """Terminology stewardship queue: source codes and units the pipeline could not map (conditions with no
    SNOMED CT or ICD-10-CA code, unclassified drugs, unrecognised lab units), with record counts. No person data."""
    with _con() as con:
        rows = con.execute("select resource_type, issue, code_system, code, source_text, record_count, stewardship_status "
                           "from rpt_code_stewardship order by record_count desc limit ?", [min(limit, 200)]).fetchall()
        mapped = con.execute("select map_status, count(*) from seed_code_valueset group by 1").fetchall()
    cols = ["resource_type", "issue", "code_system", "code", "source_text", "record_count", "status"]
    return {"queue": [dict(zip(cols, r)) for r in rows], "governed_code_maps_by_status": dict(mapped), **_context()}


if __name__ == "__main__":
    mcp.run()
