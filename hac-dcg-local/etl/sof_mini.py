"""Minimal SQL-on-FHIR v2 runner (column, forEach, forEachOrNull, where) on fhirpathpy, for testing only."""
import json, glob, re, sys
from fhirpathpy import evaluate as _ev
from fhirpathpy.models import models
def ev(r, e):
    e = e.replace('getResourceKey()', 'id')
    e = re.sub(r"(\w+(?:\.\w+)*)\.getReferenceKey\(\w+\)", r"\1.reference.replace('Patient/','').replace('Encounter/','')", e)
    return _ev(r, e, model=models['r4'])
def run_view(view, resources):
    rows = []
    for r in resources:
        if r['resourceType'] != view['resource']: continue
        if not all(ev(r, w['path']) == [True] for w in view.get('where', [])): continue
        row_sets = [{}]
        for sel in view['select']:
            if 'forEach' in sel or 'forEachOrNull' in sel:
                items = ev(r, sel.get('forEach') or sel['forEachOrNull'])
                if not items:
                    if 'forEach' in sel: row_sets = []; break
                    items = [None]
                new = []
                for base in row_sets:
                    for it in items:
                        d = dict(base)
                        for c in sel['column']:
                            v = ev(it, c['path']) if it is not None else []
                            d[c['name']] = v[0] if v else None
                        new.append(d)
                row_sets = new
            else:
                for base in row_sets:
                    for c in sel['column']:
                        v = ev(r, c['path']); base[c['name']] = v[0] if v else None
        rows += row_sets
    return rows
if __name__ == '__main__':
    views_dir, res_dir = sys.argv[1], sys.argv[2]
    resources = [json.load(open(f)) for f in glob.glob(f'{res_dir}/*.json')]
    out = {}
    for f in sorted(glob.glob(f'{views_dir}/*.json')):
        v = json.load(open(f)); out[v['name']] = (run_view(v, resources), [c['name'] for s in v['select'] for c in s['column']])
    json.dump(out, open('scripts/.sof_out.json', 'w'), default=str)
    for k, (rows, _) in out.items(): print(f'{k}: {len(rows)} rows')
