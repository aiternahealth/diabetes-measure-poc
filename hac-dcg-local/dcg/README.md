# Diabetes Care Gaps — Ontology & Semantic Model (HAC FHIR Analytics PoC)

v0.2.0-draft · 2026-11-19 (adds the Data Input IG) · Iryna Roy (Aiterna Health) with Claude

One governed vocabulary and one set of metric definitions shared by the dashboard (BI tools) and the AI agent, so that "A1C control in seniors" means the same thing everywhere.

```
L0  ig/  FSH Implementation Guide — data-input contract (profiles on CA Core+ 1.2.1-dft)
FHIR Bulk $export (NDJSON, CA Core+)
  └─ L1  views/*.json            SQL-on-FHIR v2 ViewDefinitions  → flat tables
      └─ L2  models/staging + models/marts   dbt models → fct_adult_population_period, fct_diabetes_patient_period
          └─ L3  models/semantic  dbt Semantic Layer / MetricFlow: 35 measures, 31 metrics, 3 saved queries
              └─ L4  agent/      agent contract (tools, guardrails, few-shot tests) + term_index.json
  ontology/  dcg-ontology.ttl (OWL + SKOS) binds every layer: FHIR paths, CA Core+ profiles, CACDI
             classes, value sets (SNOMED CT / LOINC / ATC), parameters, indicators, agent hints
             dcg-shapes.ttl (SHACL) → data-quality rules feeding the dq_* metrics
```

## Files
| Path | What it is |
|---|---|
| `ontology/dcg-ontology.ttl` | 71 classes, 51 SKOS concepts, 13 indicators, 11 parameters. Namespace `https://ontology.hac-poc.example/dcg#` is a placeholder. |
| `ontology/dcg-shapes.ttl` | SHACL shapes: missing birth date/onset, unmapped codes, HbA1c unit/range, BP plausibility, future dates. |
| `views/` | 7 ViewDefinitions: patient, condition, observation, blood_pressure, medication_request, procedure, encounter. |
| `seeds/seed_code_valueset.csv` | Generated from the ontology (single source of truth for codes). |
| `seeds/seed_medication_class.csv` | Ingredient keyword → ATC class (works for RxNorm from Synthea and DIN/CCDD text). |
| `models/staging/`, `models/marts/` | Pass-through staging over the views; patient-period marts + MetricFlow time spine; every indicator becomes SUM(flag)/SUM(flag). |
| `models/semantic/dcg_semantic_model.yml` | Semantic model; `config.meta` carries ontology IRIs, synonyms, caveats, benchmarks, min cell size. |
| `dbt_project.yml` | Clinical parameters as vars (A1C target 7.0%, windows, statin age 40, min cell 5). |
| `agent/dcg_agent_contract.yaml` | Tool schemas, resolution procedure, guardrails, response template, 8 worked examples. |
| `agent/term_index.json` | 322 synonyms → metric / dimension / ontology class. |
| `scripts/` | Generators and checks (below). |

## Rebuild & test
```bash
pip install rdflib pyshacl duckdb pyyaml
python3 scripts/build_seeds.py .          # ontology -> value-set seed
python3 scripts/gen_semantic_model.py     # -> models/semantic/dcg_semantic_model.yml
python3 scripts/build_term_index.py       # -> agent/term_index.json
python3 scripts/check_crossrefs.py        # ontology <-> semantic model <-> marts <-> views
python3 scripts/run_pipeline.py           # fixture data -> marts -> all metrics (DuckDB), 18 assertions
python3 scripts/run_shacl.py              # SHACL self-test
(cd ig && sushi build .)                  # compile the IG (needs packages.fhir.org access for CA Core+)
python3 scripts/check_ig.py               # IG invariants/bindings on examples; IG value sets == ontology
python3 scripts/sof_run.py views ig/fsh-generated/resources && python3 scripts/e2e_ig_examples.py
                                          # IG examples -> views -> marts: P1 0 gaps, P2 8 gaps
```
Verified 2026-11-19 with dbt-core 1.12 + dbt-duckdb + MetricFlow: `dbt build` 12/12 pass, `mf validate-configs` 0 errors/warnings, `mf query` results match the fixture expectations.
With dbt: point a profile named `dcg` at your warehouse, load the SQL-on-FHIR output into schema `fhir_views`, then `dbt seed && dbt build` and query with MetricFlow (`mf query --metrics a1c_at_target_rate --group-by patient_period__age_band`).

## v0.2 changes
- New `ig/` Data Input IG.
- `dcg_patient` view keeps patients without a home address (`forEachOrNull`).
- `dcg_medication_request` view adds `med_text` and `atc_code`; the mart classifies drugs by ingredient in text/display **or** ATC code (an ATC-class-only order was previously missed).
- Ontology: MedicationRequest/Statement and Procedure are now profiled in CA Core+ 1.2.1-dft (2026-08-31).

## Before using with real data
- Verify value sets against the Canadian Terminology Server (SNOMED CT CA edition, pCLOCD); codes marked "verify" in the ontology especially.
- Confirm eye/foot exam codes against the generated Synthea cohort.
- Have a clinical reviewer sign off the parameters in `dbt_project.yml`.
- Fill benchmark values from the current PHAC / CIHI release (the only value filled is a 2007 survey figure, marked directional).
- Replace the placeholder namespace.
