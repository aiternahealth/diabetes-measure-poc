import json, sys, yaml, duckdb
sys.path.insert(0, 'scripts')
from run_pipeline import build, query_metric
out = json.load(open('scripts/.sof_out.json'))
con = duckdb.connect()
TYPES = {'birth_date': 'date'}
for name, (rows, cols) in out.items():
    defs = ', '.join(f'{c} {"date" if c=="birth_date" else "timestamp" if any(k in c for k in ("datetime","date","authored","period_","onset","abatement")) and c!="deceased_flag" else "boolean" if c=="deceased_flag" else "double" if c in ("value_numeric","systolic","diastolic") else "varchar"}' for c in cols)
    con.execute(f'create table {name} ({defs})')
    for r in rows: con.execute(f'insert into {name} values ({",".join("?"*len(cols))})', [r.get(c) for c in cols])
vars_ = yaml.safe_load(open('dbt_project.yml'))['vars']; build(con, vars_)
print(con.execute("select patient_id, age_at_period_end, diabetes_type, a1c_latest_value, bp_at_target, on_statin, on_metformin, has_any_complication, gap_count from fct_diabetes_patient_period order by 1").fetchall())
g = dict(con.execute("select patient_id, gap_count from fct_diabetes_patient_period").fetchall())
ok = g == {'dcg-ex-patient-p1': 0, 'dcg-ex-patient-p2': 9, 'dcg-ex-patient-p9': 7}
print('E2E (IG examples -> views -> marts):', 'PASS — P1 0 gaps, P2 9 gaps (incl. cardio-renal), P9 7 gaps (hospital ICD-10-CA case)' if ok else f'FAIL {g}'); sys.exit(not ok)
