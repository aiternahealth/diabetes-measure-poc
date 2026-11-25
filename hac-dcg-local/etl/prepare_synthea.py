"""Turn Synthea output into Canadian-flavoured, minimised, IG-tagged transaction bundles for Medplum.

For each patient bundle:
  1. Inline Medication references into MedicationRequest.medicationCodeableConcept (the views read inline codes).
  2. Keep only what the care-gap pipeline needs (data minimisation, matching the IG):
       Patient, Condition, MedicationRequest (classified drugs), Observation and Procedure (codes in the
       DCG value sets), and the Encounters those Conditions point to (the DM-ADULT-CASE phenotype needs the
       encounter class for its hospital and ambulatory routes). All encounters with --keep-encounters.
       --keep-all disables filtering.
  3. Canadianise the Patient: province/postal code (deterministic, population-weighted), drop US
     extensions, SSN/licence/passport identifiers and telecom.
  4. Tag every resource meta.security = HTEST (synthetic), add meta.profile for the DCG profiles
     (--no-profiles to skip), add an identifier carrying the Synthea id and make each entry a
     conditional create (ifNoneExist) so re-loading is idempotent.
  5. Drop references to resources that are not in the bundle (practitioners, organisations, claims...).

Usage: python etl/prepare_synthea.py [--in data/synthea/fhir] [--out data/prepared] [--no-profiles]
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import DATA, medication_classes, value_sets  # noqa: E402

SYNTHEA_ID = "https://github.com/synthetichealth/synthea/id"
HTEST = {"system": "http://terminology.hl7.org/CodeSystem/v3-ActReason", "code": "HTEST", "display": "test health data"}
CANON = "http://fhir.hac-poc.example/dcg/StructureDefinition/"
SCT, LOINC, ATC = "http://snomed.info/sct", "http://loinc.org", "http://www.whocc.no/atc"

# Province weights ≈ 2021 Census population shares; FSAs/cities are real, the last 3 postal characters are synthetic.
PROVINCES = [
    ("ON", 38.5, [("Toronto", "M5V"), ("Ottawa", "K1P"), ("Mississauga", "L5B"), ("Hamilton", "L8P"), ("London", "N6A"), ("Sudbury", "P3E")]),
    ("QC", 22.5, [("Montréal", "H3B"), ("Québec", "G1R"), ("Laval", "H7N"), ("Gatineau", "J8Y")]),
    ("BC", 13.5, [("Vancouver", "V6B"), ("Surrey", "V3T"), ("Victoria", "V8W"), ("Kelowna", "V1Y")]),
    ("AB", 11.5, [("Calgary", "T2P"), ("Edmonton", "T5J"), ("Red Deer", "T4N")]),
    ("MB", 3.6, [("Winnipeg", "R3C"), ("Brandon", "R7A")]),
    ("SK", 3.0, [("Saskatoon", "S7K"), ("Regina", "S4P")]),
    ("NS", 2.6, [("Halifax", "B3J"), ("Sydney", "B1P")]),
    ("NB", 2.1, [("Moncton", "E1C"), ("Fredericton", "E3B")]),
    ("NL", 1.4, [("St. John's", "A1C")]),
    ("PE", 0.4, [("Charlottetown", "C1A")]),
]

VS = value_sets()
MEDS = medication_classes()
LAB_PROFILES = {"vs_HbA1c": "dcg-hba1c", "vs_eGFR": "dcg-egfr", "vs_UACR": "dcg-urine-acr", "vs_LDL": "dcg-ldl",
                "vs_Glucose": "dcg-glucose", "vs_BloodPressure": "dcg-blood-pressure", "vs_BMI": "dcg-bmi"}
COMPLICATION_VS = {"vs_Retinopathy", "vs_KidneyDisease", "vs_Neuropathy", "vs_FootUlcer", "vs_DKA", "vs_Hypoglycemia"}
COMORBIDITY_VS = {"vs_CKD", "vs_ASCVD"}
PROC_VS = {"vs_EyeExam", "vs_FootExam"}


def h(s):
    return int(hashlib.sha256(s.encode()).hexdigest(), 16)


def canadian_address(seed):
    total = sum(w for _, w, _ in PROVINCES)
    x = (h(seed) % 10_000) / 10_000 * total
    for prov, w, places in PROVINCES:
        if x < w:
            city, fsa = places[h(seed + "c") % len(places)]
            n = h(seed + "p")
            ldu = f"{n % 10}{'ABCEGHJKLMNPRSTVWXYZ'[n // 10 % 20]}{n // 200 % 10}"
            return {"use": "home", "line": [f"{100 + n % 900} Synthetic St"], "city": city, "state": prov,
                    "postalCode": f"{fsa} {ldu}", "country": "CA"}
        x -= w
    raise AssertionError


def codes(cc, system):
    return [c.get("code") for c in (cc or {}).get("coding", []) if c.get("system") == system]


def value_sets_of(cc, system):
    out = set()
    for c in codes(cc, system):
        out |= VS.get((system, c), set())
    return out


def classify_medication(mr):
    cc = mr.get("medicationCodeableConcept") or {}
    text = " ".join([cc.get("text", "")] + [c.get("display", "") for c in cc.get("coding", [])]).lower()
    for kw, cls, atc in MEDS:
        if kw in text:
            return cls, atc
    return None


def profile_for(r):
    t = r["resourceType"]
    if t == "Patient":
        return "dcg-patient"
    if t == "Encounter":
        return "dcg-encounter"
    if t == "Condition":
        v = value_sets_of(r.get("code"), SCT)
        if "vs_DiabetesMellitus" in v:
            return "dcg-diabetes-condition"
        if v & COMPLICATION_VS:
            return "dcg-complication-condition"
        if v & COMORBIDITY_VS:
            return "dcg-comorbidity-condition"
    if t == "Observation":
        v = value_sets_of(r.get("code"), LOINC)
        for vs, prof in LAB_PROFILES.items():
            if vs in v:
                return prof
    if t == "MedicationRequest" and classify_medication(r):
        return "dcg-medication-request"
    if t == "Procedure" and value_sets_of(r.get("code"), SCT) & PROC_VS:
        return "dcg-diabetes-procedure"
    return None


def keep(r, args):
    t = r["resourceType"]
    if args.keep_all:
        return t not in ("Claim", "ExplanationOfBenefit", "Provenance")
    if t in ("Patient", "Condition"):
        return True
    if t == "Encounter":
        return args.keep_encounters or r.get("_dcg_referenced", False)
    if t in ("Observation", "Procedure"):
        return profile_for(r) is not None
    if t == "MedicationRequest":
        return classify_medication(r) is not None
    return False


def strip_dangling_refs(node, kept_urls):
    """Remove references to resources not in this bundle; keep the display text."""
    if isinstance(node, dict):
        ref = node.get("reference")
        if isinstance(ref, str) and ref not in kept_urls:
            node.pop("reference")
        for k in list(node):
            v = node[k]
            strip_dangling_refs(v, kept_urls)
            if isinstance(v, dict) and k != "meta" and not v:
                node.pop(k)                      # reference became empty
            elif isinstance(v, list):
                node[k] = [i for i in v if not (isinstance(i, dict) and not i)]
                if not node[k]:
                    node.pop(k)
    elif isinstance(node, list):
        for i in node:
            strip_dangling_refs(i, kept_urls)


def prepare_bundle(bundle, args):
    entries = bundle.get("entry", [])
    meds = {e["fullUrl"]: e["resource"] for e in entries if e["resource"]["resourceType"] == "Medication"}
    referenced = {c["resource"].get("encounter", {}).get("reference") for c in entries
                  if c["resource"]["resourceType"] == "Condition" and value_sets_of(c["resource"].get("code"), SCT)}
    for e in entries:
        if e["resource"]["resourceType"] == "Encounter" and e["fullUrl"] in referenced:
            e["resource"]["_dcg_referenced"] = True
    out = []
    for e in entries:
        r = e["resource"]
        if r["resourceType"] == "MedicationRequest" and "medicationReference" in r:
            m = meds.get(r["medicationReference"].get("reference"))
            if m and m.get("code"):
                r.pop("medicationReference")
                r["medicationCodeableConcept"] = m["code"]
        if keep(r, args):
            out.append(e)
    kept_urls = {e["fullUrl"] for e in out}

    for e in out:
        r = e["resource"]
        t = r["resourceType"]
        r.pop("text", None)
        r.pop("_dcg_referenced", None)
        if t == "Patient":
            r["address"] = [canadian_address(r["id"])]
            r.pop("extension", None)
            r.pop("telecom", None)
            r["identifier"] = [i for i in r.get("identifier", [])
                               if any(c.get("code") == "MR" for c in (i.get("type") or {}).get("coding", []))]
        if t == "MedicationRequest":
            cls = classify_medication(r)
            cc = r["medicationCodeableConcept"]
            if cls:
                cc.setdefault("text", (cc.get("coding") or [{}])[0].get("display", ""))
                if not any(c.get("system") == ATC for c in cc.get("coding", [])):
                    cc.setdefault("coding", []).append({"system": ATC, "code": cls[1]})
        meta = r.setdefault("meta", {})
        meta["security"] = [HTEST]
        prof = profile_for(r)
        if prof and not args.no_profiles:
            meta["profile"] = [CANON + prof]
        else:
            meta.pop("profile", None)
        r.setdefault("identifier", []).append({"system": SYNTHEA_ID, "value": r["id"]})
        e["request"] = {"method": "POST", "url": t, "ifNoneExist": f"identifier={SYNTHEA_ID}|{r['id']}"}
        r.pop("id", None)
    strip_dangling_refs([e["resource"] for e in out], kept_urls)
    return {"resourceType": "Bundle", "type": "transaction", "entry": out}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="inp", default=str(DATA / "synthea" / "fhir"))
    ap.add_argument("--out", default=str(DATA / "prepared"))
    ap.add_argument("--no-profiles", action="store_true", help="do not add meta.profile (skip IG validation on load)")
    ap.add_argument("--keep-encounters", action="store_true")
    ap.add_argument("--keep-all", action="store_true", help="no minimisation (still drops Claim/EOB/Provenance)")
    args = ap.parse_args()
    src, dst = Path(args.inp), Path(args.out)
    dst.mkdir(parents=True, exist_ok=True)
    files = sorted(f for f in src.glob("*.json")
                   if not f.name.startswith(("hospitalInformation", "practitionerInformation")))
    if not files:
        raise SystemExit(f"No Synthea patient bundles in {src}. Run `make synthea` first.")
    stats = {}
    for f in files:
        b = prepare_bundle(json.load(open(f)), args)
        for e in b["entry"]:
            stats[e["resource"]["resourceType"]] = stats.get(e["resource"]["resourceType"], 0) + 1
            p = e["resource"]["meta"].get("profile")
            if p:
                stats["profile:" + p[0].rsplit("/", 1)[1]] = stats.get("profile:" + p[0].rsplit("/", 1)[1], 0) + 1
        (dst / f.name).write_text(json.dumps(b))
    print(f"Prepared {len(files)} patient bundles -> {dst}")
    for k in sorted(stats):
        print(f"  {k:40s} {stats[k]:>8,}")


if __name__ == "__main__":
    main()
