"""Load prepared Synthea bundles into Medplum as transactions, then (re)build the cohort Group.

  - Each bundle is POSTed as a FHIR transaction. Entries are conditional creates, so a re-run doesn't
    duplicate data.
  - If Medplum rejects a bundle (e.g. a resource fails DCG/CA Core+ profile validation), the issues are
    written to data/load_report.csv and, unless --no-fallback, the bundle is retried without meta.profile
    so the pipeline still gets the data. The report is your IG conformance finding list.
  - Finally a Group (identifier dcg-synthetic-cohort) is created/updated with every loaded Patient;
    its id is saved to data/group_id.txt for the Bulk export.

Usage: python etl/load_medplum.py [--in data/prepared] [--workers 4] [--limit N] [--no-fallback]
"""
import argparse
import csv
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import DATA, Medplum  # noqa: E402

GROUP_ID_SYSTEM = "https://fhir.hac-poc.example/group"
GROUP_ID_VALUE = "dcg-synthetic-cohort"


def issues(resp):
    try:
        body = resp.json()
    except ValueError:
        return resp.text[:300]
    found = []

    def walk(n):
        if isinstance(n, dict):
            if n.get("resourceType") == "OperationOutcome":
                for i in n.get("issue", []):
                    if i.get("severity") in ("error", "fatal"):
                        found.append(f"{i.get('expression', [''])[0] if i.get('expression') else ''} "
                                     f"{i.get('details', {}).get('text') or i.get('diagnostics', '')}".strip())
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)
    walk(body)
    return " | ".join(found[:5]) or json.dumps(body)[:300]


def patient_id(resp):
    for e in resp.json().get("entry", []):
        loc = (e.get("response") or {}).get("location", "")
        if loc.startswith("Patient/"):
            return loc.split("/")[1]
    return None


def strip_profiles(bundle):
    for e in bundle["entry"]:
        e["resource"].get("meta", {}).pop("profile", None)
    return bundle


def load_one(mp, path, fallback):
    bundle = json.load(open(path))
    resp = mp.request("POST", "", json=bundle)
    if resp.ok:
        return path.name, "loaded", patient_id(resp), ""
    first = issues(resp)
    if not fallback:
        return path.name, "failed", None, first
    resp2 = mp.request("POST", "", json=strip_profiles(bundle))
    if resp2.ok:
        return path.name, "loaded_without_profiles", patient_id(resp2), first
    return path.name, "failed", None, f"{first} || retry: {issues(resp2)}"


def upsert_group(mp, patient_ids):
    group = {
        "resourceType": "Group",
        "identifier": [{"system": GROUP_ID_SYSTEM, "value": GROUP_ID_VALUE}],
        "name": "HAC DCG synthetic cohort",
        "type": "person", "actual": True, "quantity": len(patient_ids),
        "meta": {"security": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ActReason", "code": "HTEST"}]},
        "member": [{"entity": {"reference": f"Patient/{p}"}} for p in sorted(patient_ids)],
    }
    r = mp.request("GET", "Group", params={"identifier": f"{GROUP_ID_SYSTEM}|{GROUP_ID_VALUE}"})
    hits = r.json().get("entry", []) if r.ok else []
    if hits:
        existing = {m["entity"]["reference"].split("/")[1] for m in hits[0]["resource"].get("member", [])}
        patient_ids = set(patient_ids) | existing                    # re-runs add members, never drop them
        group["member"] = [{"entity": {"reference": f"Patient/{p}"}} for p in sorted(patient_ids)]
        group["quantity"] = len(patient_ids)
        group["id"] = hits[0]["resource"]["id"]
        resp = mp.request("PUT", f"Group/{group['id']}", json=group)
    else:
        resp = mp.request("POST", "Group", json=group)
    if not resp.ok:
        raise SystemExit(f"Group upsert failed: {resp.status_code} {resp.text[:300]}")
    gid = resp.json()["id"]
    (DATA / "group_id.txt").write_text(gid)
    return gid, len(patient_ids)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="inp", default=str(DATA / "prepared"))
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0, help="load only the first N bundles (smoke test)")
    ap.add_argument("--no-fallback", action="store_true")
    args = ap.parse_args()
    files = sorted(Path(args.inp).glob("*.json"))
    if args.limit:
        files = files[: args.limit]
    if not files:
        raise SystemExit("No prepared bundles. Run `make prepare` first.")
    mp = Medplum()
    rows, done = [], 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(load_one, mp, f, not args.no_fallback) for f in files]
        for fut in as_completed(futures):
            rows.append(fut.result())
            done += 1
            if done % 50 == 0 or done == len(files):
                print(f"  {done}/{len(files)} bundles")
    with open(DATA / "load_report.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["bundle", "status", "patient_id", "issues"])
        w.writerows(sorted(rows))
    status = {}
    for r in rows:
        status[r[1]] = status.get(r[1], 0) + 1
    print("Load result:", status, "-> data/load_report.csv")
    pids = {r[2] for r in rows if r[2]}
    if pids:
        gid, n = upsert_group(mp, pids)
        print(f"Cohort Group: {gid} ({n} patients) -> data/group_id.txt")


if __name__ == "__main__":
    main()
