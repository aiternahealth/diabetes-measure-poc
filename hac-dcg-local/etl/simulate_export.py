"""Offline stand-in for Medplum's Bulk export: turn prepared transaction bundles into NDJSON as a FHIR
server would export them (server ids assigned, urn:uuid references resolved to Type/id).

Use it to test the pipeline without Medplum (`make offline`), or to compare with a real export.
Usage: python etl/simulate_export.py [--in data/prepared] [--out data/ndjson]
"""
import argparse
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import DATA  # noqa: E402


def resolve(node, ids):
    if isinstance(node, dict):
        ref = node.get("reference")
        if isinstance(ref, str) and ref in ids:
            node["reference"] = ids[ref]
        for v in node.values():
            resolve(v, ids)
    elif isinstance(node, list):
        for v in node:
            resolve(v, ids)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default=str(DATA / "prepared"))
    ap.add_argument("--out", default=str(DATA / "ndjson"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("*.ndjson"):
        f.unlink()
    handles, counts = {}, {}
    for f in sorted(Path(args.inp).glob("*.json")):
        b = json.load(open(f))
        ids = {}
        for e in b["entry"]:
            r = e["resource"]
            r["id"] = str(uuid.uuid5(uuid.NAMESPACE_URL, e["fullUrl"]))
            ids[e["fullUrl"]] = f"{r['resourceType']}/{r['id']}"
        for e in b["entry"]:
            r = e["resource"]
            resolve(r, ids)
            t = r["resourceType"]
            if t not in handles:
                handles[t] = open(out / f"{t}.ndjson", "w")
            handles[t].write(json.dumps(r) + "\n")
            counts[t] = counts.get(t, 0) + 1
    for h in handles.values():
        h.close()
    print(f"Simulated export -> {out}: " + ", ".join(f"{t} {n:,}" for t, n in sorted(counts.items())))


if __name__ == "__main__":
    main()
