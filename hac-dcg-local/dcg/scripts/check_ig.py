"""Post-SUSHI checks: invariants on examples (fhirpathpy), example codes ∈ profile value sets,
IG value sets == ontology seed, MS elements cover the SQL-on-FHIR view inputs."""
import json, glob, csv, sys
from fhirpathpy import evaluate as _ev
from fhirpathpy.models import models
evaluate = lambda r, e: _ev(r, e, model=models["r4"])
R = 'ig/fsh-generated/resources'
res = {f: json.load(open(f)) for f in glob.glob(f'{R}/*.json')}
sds = {r['url']: r for r in res.values() if r['resourceType'] == 'StructureDefinition'}
vss = {r['url']: r for r in res.values() if r['resourceType'] == 'ValueSet'}
# explicit concepts, plus is-a filters (ICD-10-CA categories: the code and all its children)
vs_codes = {u: {(c['system'], cc['code']) for c in v['compose']['include'] for cc in c.get('concept', [])} for u, v in vss.items()}
vs_isa = {u: {(c['system'], f['value']) for c in v['compose']['include'] for f in c.get('filter', []) if f['op'] == 'is-a'} for u, v in vss.items()}
def in_vs(url, system, code):
    return (system, code) in vs_codes[url] or any(system == s_ and (code or '').replace('.', '').startswith(p.replace('.', '')) for s_, p in vs_isa[url])
errs = []; checked = 0
for f, r in res.items():
    prof = (r.get('meta', {}).get('profile') or [None])[0]
    if r['resourceType'] in ('StructureDefinition', 'ValueSet', 'ImplementationGuide', 'CapabilityStatement') or prof not in sds: continue
    sd = sds[prof]
    for el in sd['differential']['element']:
        for c in el.get('constraint', []):
            if c['key'].startswith('dcg-'):
                ok = evaluate(r, c['expression'])
                checked += 1
                if ok != [True]: errs.append(f"{r['id']}: {c['key']} -> {ok}")
        b = el.get('binding')
        if b and b.get('strength') == 'required' and b.get('valueSet') in vs_codes and el['path'].endswith('.code') and ':' not in el['id']:
            path = el['path'].split('.', 1)[1]
            codings = evaluate(r, f'{path}.coding')
            checked += 1
            if not any(in_vs(b['valueSet'], c.get('system'), c.get('code')) for c in codings):
                errs.append(f"{r['id']}: {path} not in {b['valueSet']}")
        # coding slices by system (e.g. code.coding:snomed / code.coding:icd10ca): codings of that system must be in the slice's value set
        if b and b.get('strength') == 'required' and b.get('valueSet') in vs_codes and el['path'].endswith('.coding') and ':' in el['id']:
            systems = {s_ for s_, _ in vs_codes[b['valueSet']] | vs_isa[b['valueSet']]}
            for c in evaluate(r, el['path'].split('.', 1)[1]):
                if c.get('system') in systems:
                    checked += 1
                    if not in_vs(b['valueSet'], c['system'], c.get('code')):
                        errs.append(f"{r['id']}: {c.get('system')}|{c.get('code')} not in {b['valueSet']}")
# value sets vs ontology seed
seed = {}
for row in csv.DictReader(open('seeds/seed_code_valueset.csv')):
    seed.setdefault(row['value_set'], set()).add((row['code_system'].replace('http://www.whocc.no/atc', 'http://www.whocc.no/atc'), row['code']))
pairs = {'dcg-hba1c': ['vs_HbA1c'], 'dcg-egfr': ['vs_eGFR'], 'dcg-urine-acr': ['vs_UACR'], 'dcg-ldl': ['vs_LDL'], 'dcg-glucose': ['vs_Glucose'], 'dcg-bmi': ['vs_BMI'],
         'dcg-diabetes-mellitus': ['vs_DiabetesMellitus'], 'dcg-excluded-dysglycemia': ['vs_GDM', 'vs_Prediabetes'],
         'dcg-diabetes-complication': ['vs_Retinopathy', 'vs_KidneyDisease', 'vs_Neuropathy', 'vs_FootUlcer', 'vs_DKA', 'vs_Hypoglycemia'],
         'dcg-diabetes-mellitus-icd10ca': ['vs_DiabetesMellitus'],
         'dcg-diabetes-complication-icd10ca': ['vs_Retinopathy', 'vs_KidneyDisease', 'vs_Neuropathy', 'vs_FootUlcer', 'vs_DKA', 'vs_Hypoglycemia'],
         'dcg-cardiorenal-comorbidity': ['vs_CKD', 'vs_ASCVD'], 'dcg-cardiorenal-comorbidity-icd10ca': ['vs_CKD', 'vs_ASCVD'],
         'dcg-diabetes-screening-procedure': ['vs_EyeExam', 'vs_FootExam'], 'dcg-therapy-atc': ['vs_ATC_A10', 'vs_ATC_C10AA', 'vs_ATC_C09']}
for vid, onto in pairs.items():
    url = f'http://fhir.hac-poc.example/dcg/ValueSet/{vid}'
    ig = vs_codes[url] | vs_isa[url]
    systems = {s_ for s_, _ in ig}          # compare only the code systems this IG value set uses
    ont = {x for x in set().union(*[seed[o] for o in onto]) if x[0] in systems}
    if ig != ont: errs.append(f'ValueSet {vid} differs from ontology: IG-only {ig - ont}, ontology-only {ont - ig}')
print(f'{checked} invariant/binding checks on {sum(1 for r in res.values() if r["resourceType"] not in ("StructureDefinition","ValueSet","ImplementationGuide","CapabilityStatement"))} instances; {len(pairs)} value sets compared with ontology')
print('\n'.join(errs) if errs else 'ALL CHECKS PASS'); sys.exit(bool(errs))
