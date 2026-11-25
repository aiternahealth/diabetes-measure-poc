"""FHIR Bulk Data Group-level $export from Medplum -> data/ndjson/<Type>.ndjson (what the views read).

Follows the Bulk Data Access IG v2 async pattern: kick-off (Prefer: respond-async) -> poll the
Content-Location -> download each output file from the manifest.

Usage: python etl/bulk_export.py [--group <id>] [--types Patient,Condition,...]
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import DATA, Medplum  # noqa: E402

TYPES = "Patient,Condition,Observation,MedicationRequest,MedicationDispense,Procedure,Encounter"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", default=None, help="Group id (default: data/group_id.txt)")
    ap.add_argument("--types", default=TYPES)
    ap.add_argument("--out", default=str(DATA / "ndjson"))
    ap.add_argument("--timeout", type=int, default=3600, help="seconds to wait for the export")
    args = ap.parse_args()
    gid = args.group or (DATA / "group_id.txt").read_text().strip()
    mp = Medplum()

    kick = mp.request("GET", f"Group/{gid}/$export",
                      params={"_type": args.types, "_outputFormat": "ndjson"},
                      headers={"Prefer": "respond-async", "Accept": "application/fhir+json"})
    if kick.status_code != 202:
        raise SystemExit(f"Export kick-off failed: {kick.status_code} {kick.text[:400]}")
    status_url = kick.headers["Content-Location"]
    print(f"Export started for Group/{gid}; polling {status_url}")

    started = time.time()
    while True:
        st = mp.request("GET", status_url, headers={"Accept": "application/json"})
        if st.status_code == 200:
            manifest = st.json()
            break
        if st.status_code != 202:
            raise SystemExit(f"Export failed: {st.status_code} {st.text[:400]}")
        if time.time() - started > args.timeout:
            raise SystemExit("Export timed out")
        print(f"  ... {st.headers.get('X-Progress', 'in progress')}")
        time.sleep(min(30, int(st.headers.get("Retry-After", 5))))

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("*.ndjson"):
        f.unlink()
    counts = {}
    for item in manifest.get("output", []):
        r = mp.request("GET", item["url"], headers={"Accept": "application/fhir+ndjson"})
        r.raise_for_status()
        text = r.text if r.text.endswith("\n") or not r.text else r.text + "\n"
        with open(out / f"{item['type']}.ndjson", "a") as fh:
            fh.write(text)
        counts[item["type"]] = counts.get(item["type"], 0) + text.count("\n")
    for err in manifest.get("error", []):
        print("  export error file:", err.get("url"))
    print(f"Exported in {time.time() - started:.0f}s -> {out}: " +
          ", ".join(f"{t} {n:,}" for t, n in sorted(counts.items())))


if __name__ == "__main__":
    main()
