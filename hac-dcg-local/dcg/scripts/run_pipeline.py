"""End-to-end test: fixture rows shaped like the SQL-on-FHIR views -> seeds -> marts -> metrics.
Also serves as a reference implementation of the agent's query_metrics tool (ratio/simple/derived,
group_by, where, small-cell suppression)."""
import re, csv, yaml, duckdb
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent   # the dcg/ project folder

def render(sql, vars_):
    sql = re.sub(r"\{\{\s*ref\('(\w+)'\)\s*\}\}", r"\1", sql)
    sql = re.sub(r"\{\{\s*source\('\w+',\s*'(\w+)'\)\s*\}\}", r"\1", sql)
    return re.sub(r"\{\{\s*var\(\"(\w+)\",\s*[^)]*\)\s*\}\}", lambda m: str(vars_[m.group(1)]), sql)

def build(con, vars_):
    for seed in ('seed_code_valueset', 'seed_medication_class'):
        con.execute(f"create or replace table {seed} as select * from read_csv_auto('{ROOT}/seeds/{seed}.csv', all_varchar=true)")
    for folder, model in MODELS:
        con.execute(f"create or replace table {model} as " + render(open(ROOT / 'models' / folder / f'{model}.sql').read(), vars_))

MODELS = [('intermediate', 'int_condition_coded'), ('intermediate', 'int_observation_std'), ('intermediate', 'int_medication_exposure'),
          ('intermediate', 'int_dm_case_evidence'), ('marts', 'fct_adult_population_period'), ('marts', 'fct_diabetes_patient_period'),
          ('marts', 'rpt_code_stewardship')]

SM = yaml.safe_load(open(ROOT / 'models' / 'semantic' / 'dcg_semantic_model.yml'))
MEAS = {ms['name']: (s, ms) for s in SM['semantic_models'] for ms in s['measures']}
MET = {m['name']: m for m in SM['metrics']}
TABLE = {'adult_population': 'fct_adult_population_period', 'diabetes_patient_period': 'fct_diabetes_patient_period'}

def dim_expr(model, dname):
    d = next(d for d in model['dimensions'] if d['name'] == dname); return d.get('expr', dname)

def agg(con, measure, group_by=(), where=None):
    model, ms = MEAS[measure]
    fn = {'sum': 'sum', 'average': 'avg', 'median': 'median', 'count': 'count'}[ms['agg']]
    gcols = [f"{dim_expr(model, g)} as {g}" for g in group_by]
    agg_expr = f"{fn}({ms['expr']}) as v"
    sql = f"select {', '.join(gcols + [agg_expr])} from {TABLE[model['name']]}"
    if where: sql += ' where ' + ' and '.join(f"{dim_expr(model, k)} = '{v}'" for k, v in where.items())
    if group_by: sql += ' group by ' + ', '.join(str(i + 1) for i in range(len(group_by)))
    return {tuple(r[:-1]): r[-1] for r in con.execute(sql).fetchall()}

def query_metric(con, name, group_by=(), where=None, min_cell=5):
    m = MET.get(name)
    if m is None:   # auto-created metric from a measure
        return {k: {'value': v} for k, v in agg(con, name, group_by, where).items()}
    tp = m['type_params']
    if m['type'] == 'simple':
        meta = m['config']['meta']
        vals = agg(con, tp['measure'], group_by, where)
        support = agg(con, meta['support_measure'], group_by, where) if meta.get('support_measure') else None
        out = {}
        for k, v in vals.items():
            if support is not None:            # a level (mean/median): suppress when too few people stand behind it
                n = support.get(k) or 0
                sup = n < min_cell
                out[k] = {'value': None if sup else v, 'people': None if sup else n, 'suppressed': sup}
            else:
                out[k] = {'value': v, 'suppressed': v is not None and v < min_cell and meta.get('unit') == 'persons'}
        return out
    if m['type'] == 'ratio':
        num, den = agg(con, tp['numerator'], group_by, where), agg(con, tp['denominator'], group_by, where)
        out = {}
        for k, d in den.items():
            n = num.get(k, 0) or 0
            sup = (d or 0) < min_cell or 0 < n < min_cell
            out[k] = {'value': None if sup or not d else n / d, 'numerator': None if sup else n, 'denominator': None if sup else d, 'suppressed': sup}
        return out
    if m['type'] == 'derived':
        parts = {x['name']: agg(con, x['name'], group_by, where) for x in tp['metrics']}
        keys = set.intersection(*[set(p) for p in parts.values()])
        return {k: {'value': eval(tp['expr'], {}, {n: p[k] for n, p in parts.items()})} for k in keys}

if __name__ == '__main__':
    vars_ = {}
    for k, v in yaml.safe_load(open(ROOT / 'dbt_project.yml'))['vars'].items(): vars_[k] = v
    con = duckdb.connect()
    con.execute(open(ROOT / 'scripts' / 'fixtures.sql').read())
    build(con, vars_)
    v = lambda name, **kw: query_metric(con, name, min_cell=1, **kw)[()]['value']
    # Expected values worked by hand from scripts/fixtures.sql (period end 2026-09-30).
    # Cohort (DM-ADULT-CASE): P1 P2 P3 P5 (declared), P9 (hospital ICD-10-CA), P10 (2 ambulatory claims), P11 (2 A1C >= 6.5) = 7.
    # Adults alive: 11. Not in cohort: P4 prediabetes, P8, P12 medication only, P13 GDM-window A1C.
    checks = {
        'diabetes_prevalence_crude': 7 / 11, 'cohort_size': 7, 'a1c_tested_12m_rate': 7 / 7, 'a1c_tested_recent_rate': 5 / 7,
        'a1c_at_target_rate': 3 / 6, 'bp_at_target_rate': 2 / 7, 'kidney_screened_rate': 1 / 7, 'lipid_tested_rate': 2 / 7,
        'eye_exam_rate': 1 / 7, 'foot_exam_rate': 1 / 7, 'statin_rate_40plus': 2 / 6, 'all_four_tests_rate': 1 / 7,
        'any_gap_rate': 6 / 7, 'gap_a1c_control_rate': 3 / 7, 'dq_a1c_unit_rate': 1 / 7, 'gap_statin_rate': 4 / 7,
        'complication_rate': 1 / 7, 'gaps_per_member': (0 + 9 + 5 + 5 + 7 + 5 + 7) / 7,
        'bmi_recorded_rate': 2 / 7, 'bmi_latest_mean_kg_m2': 29.3, 'bmi_latest_median_kg_m2': 29.3,
        'bp_systolic_mean_mmhg': (120 + 140 + 135 + 128 + 150) / 5, 'bp_diastolic_mean_mmhg': (75 + 85 + 82 + 78 + 95) / 5,
        'bp_systolic_median_mmhg': 135, 'metformin_rate': 1 / 7, 'insulin_rate': 3 / 7, 'sglt2i_rate': 1 / 7, 'glp1ra_rate': 1 / 7,
        'acei_arb_rate': 1 / 7, 'antihyperglycemic_rate': 6 / 7, 'dq_dm_duplicate_rate': 1 / 7,
        # v0.4 DCI-aligned measures
        'a1c_poor_control_rate': 1 / 7, 'a1c_poor_control_tested_rate': 0 / 6, 'bp_at_target_measured_rate': 2 / 5,
        'cardiorenal_agent_rate': 1 / 2, 'gap_cardiorenal_rate': 1 / 7, 'ckd_or_ascvd_rate': 2 / 7,
        'acute_dm_admissions_per_1000': 1 / 7 * 1000, 'possible_case_rate': 1 / 11, 'a1c_unit_converted': 1,
    }
    fails = 0
    for name, exp in checks.items():
        got = v(name); ok = abs(got - exp) < 1e-9
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name:28s} got={got:.4f} expected={exp:.4f}")
    gs = query_metric(con, 'any_gap_rate', group_by=('age_band',), min_cell=1)
    print('any_gap_rate by age_band:', {k[0]: round(x['value'], 3) for k, x in sorted(gs.items())})
    t2 = query_metric(con, 'a1c_at_target_rate', where={'diabetes_type': 'type_2'}, min_cell=1)[()]['value']
    print('a1c_at_target_rate (type_2 only):', t2); fails += abs(t2 - 0.5) > 1e-9
    cb = {k[0]: x['value'] for k, x in query_metric(con, 'cohort_size', group_by=('case_basis',), min_cell=1).items()}
    print('cohort_size by case_basis:', cb)
    fails += cb != {'declared_condition': 4, 'hospital_dx': 1, 'ambulatory_2x': 1, 'lab_a1c_2x': 1}
    ty = {k[0]: x['value'] for k, x in query_metric(con, 'cohort_size', group_by=('diabetes_type',), min_cell=1).items()}
    print('cohort_size by diabetes_type:', ty); fails += ty != {'type_2': 5, 'type_1': 1, 'unclassified': 1}
    lin = con.execute("select distinct phenotype_id, phenotype_version, map_version from fct_diabetes_patient_period").fetchall()
    print('lineage columns:', lin); fails += lin != [('DM-ADULT-CASE', '0.1', '0.4.0-draft')]
    st = con.execute("select resource_type, code, record_count from rpt_code_stewardship order by 1").fetchall()
    print('stewardship queue:', st); fails += st != [('Medication', '313782', 1), ('Observation', '(missing)', 1)]
    bc = {k[0]: x['value'] for k, x in query_metric(con, 'cohort_size', group_by=('bmi_category',), min_cell=1).items()}
    print('cohort_size by bmi_category:', bc)
    lv = query_metric(con, 'bmi_latest_median_kg_m2', min_cell=5)[()]
    print('BMI median with 2 people behind it, min_cell=5:', lv); fails += not lv['suppressed']
    fails += bc != {'overweight (25-29.9)': 1, 'obese (30+)': 1, 'not recorded': 5}
    sup = query_metric(con, 'a1c_tested_12m_rate', where={'diabetes_type': 'type_1'})[()]
    print('min_cell=5 suppression on a 1-person cell:', sup); fails += not sup['suppressed']
    # phenotype parameters: claims-only mode drops declared-only cases; with pheno_med_qualifies, metformin alone still does not qualify
    build(con, {**vars_, 'pheno_accept_declared_condition': False, 'pheno_med_qualifies': True})
    strict = query_metric(con, 'cohort_size', group_by=('case_basis',), min_cell=1)
    print('claims-only + medication-qualifies mode, cohort by case_basis:', {k[0]: x['value'] for k, x in strict.items()})
    # P2 and P3 return through insulin; P1 (metformin only) does not
    fails += {k[0]: x['value'] for k, x in strict.items()} != {'hospital_dx': 1, 'ambulatory_2x': 1, 'lab_a1c_2x': 1, 'medication': 2}
    build(con, vars_)
    for name in MET:   # every metric must execute
        query_metric(con, name, group_by=('sex',), min_cell=1)
    print(f'all {len(MET)} metrics executed with group_by sex')
    cq = yaml.safe_load(open(ROOT / 'agent' / 'competency_questions.yaml'))['questions']
    ran = 0
    for q in cq:
        for qq in q.get('queries', []):
            for name in qq['metrics']:
                query_metric(con, name, group_by=tuple(qq.get('group_by', [])), min_cell=1); ran += 1
    print('competency questions:', {s_: sum(q['status'] == s_ for q in cq) for s_ in ('supported', 'partial', 'out_of_scope')}, f'({ran} metric queries ran)')
    print('RESULT:', 'ALL PASS' if not fails else f'{fails} FAILURES'); raise SystemExit(fails)
