"""Load conformance resources into Medplum so it validates incoming data against the DCG IG on write.

Order: CA Core+ 1.2.1-dft package (StructureDefinitions incl. extensions, ValueSets, small CodeSystems)
then the DCG IG (SUSHI output with snapshots: `make ig`). Each resource is upserted by canonical URL
(search by url -> update, else create), so re-running is safe.

Usage: python etl/load_profiles.py [--skip-cacore] [--ig dcg/ig/fsh-generated/resources]
"""
import argparse
import io
import json
import sys
import tarfile
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from common import DATA, DCG, Medplum  # noqa: E402

CACORE = ("ca.infoway.io.core", "1.2.1-dft")
TYPES = ("CodeSystem", "ValueSet", "StructureDefinition")       # load order: terminology first
MAX_CS_BYTES = 1_000_000


def cacore_resources():
    cache = DATA / "packages" / f"{CACORE[0]}#{CACORE[1]}.tgz"
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        url = f"https://packages.fhir.org/{CACORE[0]}/{CACORE[1]}"
        print(f"Downloading {url}")
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        cache.write_bytes(r.content)
    out = []
    with tarfile.open(fileobj=io.BytesIO(cache.read_bytes()), mode="r:gz") as tar:
        for m in tar.getmembers():
            if m.name.startswith("package/") and m.name.endswith(".json") and "/" not in m.name[8:] \
                    and not m.name.endswith(("package.json", ".index.json")):
                raw = tar.extractfile(m).read()
                res = json.loads(raw)
                if res.get("resourceType") in TYPES:
                    if res["resourceType"] == "CodeSystem" and len(raw) > MAX_CS_BYTES:
                        print(f"  skip large CodeSystem {res.get('url')}")
                        continue
                    out.append(res)
    return out


def ig_resources(path):
    files = sorted(Path(path).glob("*.json"))
    if not files:
        raise SystemExit(f"No IG output in {path}. Run `make ig` first.")
    out = [json.load(open(f)) for f in files]
    return [r for r in out if r.get("resourceType") in TYPES]


def upsert(mp, res):
    t, url = res["resourceType"], res["url"]
    r = mp.request("GET", f"{t}", params={"url": url, "_count": 2})
    hits = [e["resource"] for e in r.json().get("entry", [])] if r.ok else []
    res = {k: v for k, v in res.items() if k not in ("id", "meta")}
    if hits:
        res["id"] = hits[0]["id"]
        resp = mp.request("PUT", f"{t}/{res['id']}", json=res)
    else:
        resp = mp.request("POST", t, json=res)
    return resp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-cacore", action="store_true")
    ap.add_argument("--ig", default=str(DCG / "ig" / "fsh-generated" / "resources"))
    args = ap.parse_args()
    mp = Medplum()
    batches = ([("CA Core+", cacore_resources())] if not args.skip_cacore else []) + [("DCG IG", ig_resources(args.ig))]
    failures = []
    for label, resources in batches:
        resources.sort(key=lambda r: (TYPES.index(r["resourceType"]),
                                      0 if r.get("type") == "Extension" else 1))   # extensions before profiles
        ok = 0
        for res in resources:
            resp = upsert(mp, res)
            if resp.ok:
                ok += 1
            else:
                failures.append((label, res["resourceType"], res.get("url"), resp.status_code, resp.text[:300]))
        print(f"{label}: {ok}/{len(resources)} loaded")
    if failures:
        print("\nFailures:")
        for f in failures:
            print("  ", *f)
        sys.exit(1)


if __name__ == "__main__":
    main()
