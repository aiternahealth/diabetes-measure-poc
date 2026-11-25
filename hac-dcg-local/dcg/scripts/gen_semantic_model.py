"""Generates models/semantic/dcg_semantic_model.yml (dbt Semantic Layer / MetricFlow spec + dcg meta).
Kept as a generator so metric definitions stay consistent; the YAML is the artifact tools consume."""
import copy, yaml
class NoAlias(yaml.SafeDumper):
    def ignore_aliases(self, data): return True
O = 'dcg:'
dims_common = [
    {'name': 'period_end', 'type': 'time', 'type_params': {'time_granularity': 'day'},
     'description': 'Measurement period end date (inclusive). All lookbacks are relative to it.', 'config': {'meta': {'ontology': O+'MeasurementPeriod', 'synonyms': ['as of', 'reporting period', 'year', 'quarter']}}},
    {'name': 'age_band', 'type': 'categorical', 'description': '18-39 | 40-64 | 65+ (aligned to CPG statin age cut-point).', 'config': {'meta': {'ontology': O+'AgeBand', 'synonyms': ['age group', 'age']}}},
    {'name': 'age_band_phac', 'type': 'categorical', 'description': '18-19 | 20-34 | 35-49 | 50-64 | 65-79 | 80+ (for comparison with PHAC-style age groups).', 'config': {'meta': {'ontology': O+'AgeBand'}}},
    {'name': 'sex', 'type': 'categorical', 'description': 'FHIR administrative gender.', 'config': {'meta': {'ontology': O+'Sex', 'synonyms': ['gender', 'male/female']}}},
    {'name': 'province', 'type': 'categorical', 'description': 'Province/territory from home address.', 'config': {'meta': {'ontology': O+'Province', 'synonyms': ['region', 'jurisdiction', 'PT']}}},
    {'name': 'fsa', 'type': 'categorical', 'description': 'Forward sortation area. RESTRICTED: suppression required; never combine with both age_band and sex.', 'config': {'meta': {'ontology': O+'ForwardSortationArea', 'sensitivity': 'restricted'}}},
    {'name': 'data_source', 'type': 'categorical', 'description': 'synthetic | real_world.', 'config': {'meta': {'ontology': O+'DataSource'}}},
    {'name': 'case_basis', 'type': 'categorical', 'description': 'Strongest evidence route of case phenotype DM-ADULT-CASE: hospital_dx | ambulatory_2x | declared_condition | lab_a1c_2x (non-members: medication_only | none).', 'config': {'meta': {'ontology': O+'CohortMembership', 'synonyms': ['case definition', 'evidence', 'why in cohort', 'how identified']}}},
    {'name': 'phenotype_version', 'type': 'categorical', 'description': 'Version of the case phenotype that built the cohort (lineage).', 'config': {'meta': {'ontology': O+'CasePhenotype'}}},
    {'name': 'service_language', 'type': 'categorical', 'description': 'Preferred service language (PCHDCF). RESTRICTED equity stratifier: equity role only, one at a time.', 'config': {'meta': {'ontology': O+'ServiceLanguage', 'sensitivity': 'restricted', 'synonyms': ['language', 'French', 'English']}}},
    {'name': 'indigenous_identity', 'type': 'categorical', 'description': 'Indigenous identity (PCHDCF). RESTRICTED: equity role only; OCAP and community data governance apply.', 'config': {'meta': {'ontology': O+'IndigenousIdentity', 'sensitivity': 'restricted'}}},
    {'name': 'racialized_group', 'type': 'categorical', 'description': 'Racialized group (PCHDCF). RESTRICTED equity stratifier: equity role only, one at a time.', 'config': {'meta': {'ontology': O+'RacializedGroup', 'sensitivity': 'restricted'}}},
]
entity = lambda prim: [{'name': prim, 'type': 'primary', 'expr': "patient_id || '|' || cast(period_end as varchar)"},
                  {'name': 'patient', 'type': 'foreign', 'expr': 'patient_id'}]
defaults = {'agg_time_dimension': 'period_end'}

def m(name, expr, desc, onto, agg='sum'):
    return {'name': name, 'agg': agg, 'expr': expr, 'description': desc, 'create_metric': True, 'config': {'meta': {'ontology': onto}}}

pop = {'name': 'adult_population', 'description': 'Adults (>=18) alive at period end. Denominator for prevalence.',
       'model': "ref('fct_adult_population_period')", 'defaults': defaults, 'entities': entity('population_member'),
       'dimensions': dims_common, 'measures': [
           m('adults', '1', 'Adults alive at period end.', O+'Person'),
           m('adults_with_diabetes', 'has_diabetes', 'Adults who meet case phenotype DM-ADULT-CASE.', O+'DiabetesCohort'),
           m('possible_cases_med_only', 'possible_case_med_only', 'Adults with antihyperglycemic medication but no qualifying diabetes evidence (not in the cohort; review for missing diagnoses).', O+'route_medication')]}

dm_dims = dims_common + [
    {'name': 'diabetes_type', 'type': 'categorical', 'description': 'Heuristic: type_1 (only type 1 evidence) | type_2 (only type 2) | other_specified (only secondary) | unclassified (mixed, unspecified or lab-only).', 'config': {'meta': {'ontology': O+'DiabetesMellitus', 'synonyms': ['type', 'T1/T2']}}},
    {'name': 'has_ckd_or_ascvd', 'type': 'categorical', 'expr': "case when has_ckd_or_ascvd = 1 then 'yes' else 'no' end", 'description': 'Chronic kidney disease (coded or 2 abnormal labs 90+ days apart) or atherosclerotic cardiovascular disease.', 'config': {'meta': {'ontology': O+'ChronicKidneyDisease', 'synonyms': ['CKD', 'ASCVD', 'cardio-renal', 'heart or kidney disease']}}},
    {'name': 'diabetes_duration_band', 'type': 'categorical', 'expr': "case when years_since_diagnosis < 5 then '<5y' when years_since_diagnosis < 10 then '5-9y' else '10y+' end", 'description': 'Years since first diabetes diagnosis.', 'config': {'meta': {'synonyms': ['duration', 'years with diabetes']}}},
    {'name': 'has_any_complication', 'type': 'categorical', 'expr': "case when has_any_complication = 1 then 'yes' else 'no' end", 'description': 'Any retinopathy, kidney disease, neuropathy or foot ulcer.', 'config': {'meta': {'ontology': O+'DiabetesComplication'}}},
    {'name': 'therapy_profile', 'type': 'categorical', 'expr': "case when on_insulin = 1 then 'insulin' when on_sglt2i_or_glp1ra = 1 then 'sglt2i_or_glp1ra' when on_antihyperglycemic = 1 then 'oral_other' else 'no_antihyperglycemic' end", 'description': 'Hierarchical therapy grouping.', 'config': {'meta': {'ontology': O+'TherapyClass', 'synonyms': ['treatment', 'medication']}}},
    {'name': 'bmi_category', 'type': 'categorical',
     'expr': "case when bmi_latest_value is null then 'not recorded' when bmi_latest_value < 18.5 then 'underweight (<18.5)' when bmi_latest_value < 25 then 'normal (18.5-24.9)' when bmi_latest_value < 30 then 'overweight (25-29.9)' else 'obese (30+)' end",
     'description': 'WHO adult BMI class of the latest BMI in 12 months; not recorded when there is none.', 'config': {'meta': {'ontology': O+'BMIResult', 'synonyms': ['BMI class', 'weight category', 'obesity']}}},
    {'name': 'has_any_gap', 'type': 'categorical', 'expr': "case when gap_count > 0 then 'yes' else 'no' end", 'config': {'meta': {'ontology': O+'CareGap'}}},
]
dm_measures = [
    m('cohort_members', 'in_cohort', 'People in the diabetes care-gap cohort.', O+'DiabetesCohort'),
    m('a1c_tested_recent', 'a1c_tested_recent', '>=1 HbA1c in recency window (default 6 months).', O+'cp_A1cTesting'),
    m('a1c_tested_12m', 'a1c_tested_12m', '>=1 HbA1c in 12 months.', O+'HbA1cResult'),
    m('a1c_valid_result_12m', 'a1c_has_valid_result', 'Has a valid (% unit, 3-20) HbA1c in 12 months.', O+'HbA1cResult'),
    m('a1c_at_target', 'a1c_at_target', 'Latest valid HbA1c <= target.', O+'co_A1cAtTarget'),
    m('a1c_poor_or_untested', 'a1c_poor_or_untested', 'Latest HbA1c > 9% or no valid result.', O+'param_A1cPoorControl'),
    m('a1c_poor_tested', 'a1c_poor_tested', 'Latest valid HbA1c > 9% (tested members only).', O+'ind_a1c_poor_tested'),
    m('a1c_unit_converted', 'a1c_unit_converted', 'Members whose HbA1c in 12 months arrived in mmol/mol and was converted to %.', O+'UnitConversion'),
    m('members_with_ckd', 'has_ckd', 'Members with CKD (coded, or 2 eGFR < 60 or ACR >= 3 mg/mmol 90+ days apart in 24 months).', O+'ChronicKidneyDisease'),
    m('members_with_ascvd', 'has_ascvd', 'Members with atherosclerotic cardiovascular disease.', O+'AtheroscleroticCVD'),
    m('members_ckd_or_ascvd', 'has_ckd_or_ascvd', 'Members with CKD or ASCVD (denominator of the cardio-renal measure).', O+'ChronicKidneyDisease'),
    m('ckd_or_ascvd_on_cardiorenal', 'ckd_or_ascvd_on_cardiorenal', 'Members with CKD or ASCVD on an SGLT2 inhibitor or GLP-1 RA.', O+'CardiorenalAgent'),
    m('acute_dm_admissions_12m', 'acute_dm_admissions_12m', 'Inpatient or emergency encounters with DKA or hypoglycemia in 12 months.', O+'AcuteDiabetesEvent'),
    m('a1c_latest_mean', 'a1c_latest_value', 'Mean of latest valid HbA1c (%).', O+'HbA1cResult', 'average'),
    m('a1c_latest_median', 'a1c_latest_value', 'Median of latest valid HbA1c (%).', O+'HbA1cResult', 'median'),
    m('bp_measured_12m', 'bp_measured_12m', 'BP measured in 12 months.', O+'cp_BPMeasurement'),
    m('bp_at_target', 'bp_at_target', 'Latest BP < 130/80.', O+'co_BPAtTarget'),
    m('kidney_screened_12m', 'kidney_screened_12m', 'eGFR and urine ACR in 12 months.', O+'cp_KidneyScreening'),
    m('lipid_tested_in_window', 'lipid_tested_in_window', 'LDL-C in lipid window (default 36 months).', O+'cp_LipidTesting'),
    m('eye_exam_in_window', 'eye_exam_in_window', 'Retinopathy screening in window (default 24 months).', O+'cp_EyeExam'),
    m('foot_exam_12m', 'foot_exam_12m', 'Foot exam in 12 months.', O+'cp_FootExam'),
    m('statin_eligible', 'statin_eligible', 'Cohort members aged >= statin_min_age.', O+'param_StatinAge'),
    m('statin_eligible_on_statin', 'statin_eligible * on_statin', 'Statin-eligible members with a statin.', O+'cp_StatinTherapy'),
    m('all_four_tests_12m', 'all_four_tests_12m', 'A1C, BP, LDL-C and kidney screening all in 12 months.', O+'ind_all4'),
    m('members_with_any_gap', 'case when gap_count > 0 then 1 else 0 end', 'Members with >=1 open gap.', O+'CareGap'),
    m('gap_count_total', 'gap_count', 'Total open gaps.', O+'CareGap'),
    m('members_with_complication', 'has_any_complication', 'Members with any complication.', O+'DiabetesComplication'),
] + [m(f'gap_{g}', f'gap_{g}', f'Open gap: {g}.', O+gc) for g, gc in [
    ('a1c_test', 'gap_a1c_test'), ('a1c_control', 'gap_a1c_control'), ('bp_control', 'gap_bp_control'),
    ('kidney_screen', 'gap_kidney'), ('lipid_test', 'gap_lipid'), ('eye_exam', 'gap_eye'), ('foot_exam', 'gap_foot'), ('statin', 'gap_statin'),
    ('cardiorenal', 'gap_cardiorenal')]
] + [m(f'dq_{d}', f'dq_{d}', desc, O+cls) for d, desc, cls in [
    ('a1c_no_value', 'HbA1c tests with no numeric result.', 'MissingValue'),
    ('a1c_unit', 'HbA1c results with non-% unit.', 'UnitNonConformance'),
    ('a1c_implausible', 'HbA1c outside 3-20%.', 'ImplausibleValue'),
    ('missing_onset', 'Diabetes Condition without onset date.', 'MissingValue'),
    ('dm_type_conflict', 'Both T1 and T2 coded.', 'UnmappedCode'),
    ('dm_duplicate', 'Same qualifying diabetes code recorded on more than one Condition.', 'DuplicateRecord')]]

# Cohort-profile context measures (v0.3): BMI and BP levels, medication classes
MED_CLASSES = [('metformin', 'Metformin', 'Metformin'), ('insulin', 'Insulin', 'Insulin'), ('sglt2i', 'SGLT2 inhibitor', 'SGLT2Inhibitor'),
               ('glp1ra', 'GLP-1 receptor agonist', 'GLP1ReceptorAgonist'), ('dpp4i', 'DPP-4 inhibitor', 'DPP4Inhibitor'),
               ('sulfonylurea', 'Sulfonylurea', 'Sulfonylurea'), ('tzd', 'Thiazolidinedione', 'Thiazolidinedione'),
               ('acei_arb', 'ACE inhibitor or ARB', 'ACEInhibitorOrARB'),
               ('antihyperglycemic', 'Any antihyperglycemic', 'AntihyperglycemicTherapy')]
dm_measures += [
    m('bmi_recorded_12m', 'bmi_recorded_12m', 'Has a plausible BMI (10-80) in 12 months.', O+'BMIResult'),
    m('bmi_latest_mean', 'bmi_latest_value', 'Mean of latest BMI (kg/m2) among those recorded.', O+'BMIResult', 'average'),
    m('bmi_latest_median', 'bmi_latest_value', 'Median of latest BMI (kg/m2) among those recorded.', O+'BMIResult', 'median'),
    m('bp_systolic_latest_mean', 'bp_latest_systolic', 'Mean of latest systolic BP (mmHg) among those measured.', O+'BloodPressureReading', 'average'),
    m('bp_systolic_latest_median', 'bp_latest_systolic', 'Median of latest systolic BP (mmHg) among those measured.', O+'BloodPressureReading', 'median'),
    m('bp_diastolic_latest_mean', 'bp_latest_diastolic', 'Mean of latest diastolic BP (mmHg) among those measured.', O+'BloodPressureReading', 'average'),
    m('bp_diastolic_latest_median', 'bp_latest_diastolic', 'Median of latest diastolic BP (mmHg) among those measured.', O+'BloodPressureReading', 'median'),
] + [m(f'members_on_{k}', f'on_{k}', f'Members with a {label} order or dispense in 12 months, or an active order.', O+cls) for k, label, cls in MED_CLASSES]

MEAS_DESC = {x['name']: x['description'] for x in dm_measures}
dm = {'name': 'diabetes_patient_period', 'description': 'One row per diabetes-cohort member per period with care-process, outcome, gap and DQ flags.',
      'model': "ref('fct_diabetes_patient_period')", 'defaults': defaults, 'entities': entity('patient_period'), 'dimensions': dm_dims, 'measures': dm_measures}

def ratio(name, label, num, den, desc, ind, syn, direction='higher_is_better', caveats=None, benchmark=None):
    meta = {'ontology_indicator': O+ind, 'unit': 'proportion', 'display_format': 'percent_1dp', 'direction': direction,
            'denominator_measure': den, 'numerator_measure': num, 'min_cell_size': 5, 'synonyms': syn}
    if caveats: meta['caveats'] = caveats
    if benchmark: meta['benchmark'] = benchmark
    return {'name': name, 'label': label, 'description': desc, 'type': 'ratio',
            'type_params': {'numerator': num, 'denominator': den}, 'config': {'meta': meta}}

def simple(name, label, measure, desc, unit, syn, ind=None):
    meta = {'unit': unit, 'synonyms': syn, 'min_cell_size': 5}
    if ind: meta['ontology_indicator'] = O+ind
    return {'name': name, 'label': label, 'description': desc, 'type': 'simple', 'type_params': {'measure': measure}, 'config': {'meta': meta}}

SYN = 'synthetic'
metrics = [
    simple('cohort_size', 'People with diabetes (cohort)', 'cohort_members', 'Count of the diabetes care-gap cohort.', 'persons', ['how many people have diabetes', 'number of diabetics', 'cohort size', 'denominator']),
    ratio('diabetes_prevalence_crude', 'Diabetes prevalence (crude, adults)', 'adults_with_diabetes', 'adults', 'Adults with diabetes / adults alive at period end. Crude, not age-standardised.', 'ind_prevalence',
          ['prevalence', 'percent with diabetes', 'how common is diabetes'], 'context',
          ['Crude rate; PHAC CCDSS rates use an administrative case definition and age standardisation.', 'On synthetic data this reflects generator settings, not Canada.'],
          {'ref': O+'bm_phac_ccdss', 'comparable': False}),
    ratio('a1c_tested_12m_rate', 'A1C tested in past 12 months', 'a1c_tested_12m', 'cohort_members', 'Share of cohort with >=1 HbA1c in the 12 months to period end.', 'ind_a1c_tested_12m',
          ['A1C testing rate', 'annual A1C', 'had A1C test this year', 'HbA1c screening'], caveats=['Benchmark is self-reported survey data (CCHS 2007), age-standardised.'],
          benchmark={'ref': O+'bm_cihi_2009_a1c12m', 'value': 0.81, 'comparable': 'directional only'}),
    ratio('a1c_tested_recent_rate', 'A1C tested in recency window', 'a1c_tested_recent', 'cohort_members', 'Share of cohort with >=1 HbA1c in the last a1c_recent_months (default 6). Complement = A1C testing gap.', 'ind_a1c_tested_recent',
          ['recent A1C', 'A1C up to date', 'overdue A1C', 'A1C testing gap']),
    ratio('a1c_at_target_rate', 'Latest A1C at target (among tested)', 'a1c_at_target', 'a1c_valid_result_12m', 'Among members with a valid HbA1c in 12 months, share whose latest value <= a1c_target_pct (default 7.0%).', 'ind_a1c_at_target',
          ['glycemic control', 'A1C control', 'at target', 'controlled diabetes', 'A1C under 7'], caveats=['Denominator is tested members only; untested people are not counted as controlled or uncontrolled. Pair with a1c_tested_12m_rate.']),
    ratio('a1c_poor_control_rate', 'A1C > 9% or untested', 'a1c_poor_or_untested', 'cohort_members', 'Share of cohort whose latest HbA1c is >9% or who has no valid result in 12 months.', 'ind_a1c_poor',
          ['poor control', 'uncontrolled diabetes', 'A1C over 9'], 'lower_is_better'),
    ratio('bp_at_target_rate', 'Latest BP < 130/80', 'bp_at_target', 'cohort_members', 'Share of cohort whose latest BP in 12 months is <130/80; unmeasured counts as not at target.', 'ind_bp_target',
          ['blood pressure control', 'BP at target', 'hypertension control']),
    ratio('kidney_screened_rate', 'Kidney screening (eGFR + ACR) in 12 months', 'kidney_screened_12m', 'cohort_members', 'Share with both eGFR and urine ACR in 12 months.', 'ind_kidney',
          ['kidney screening', 'nephropathy screening', 'ACR and eGFR', 'urine protein test']),
    ratio('lipid_tested_rate', 'LDL-C tested in window', 'lipid_tested_in_window', 'cohort_members', 'Share with LDL-C in lipid_months (default 36).', 'ind_lipid',
          ['cholesterol testing', 'lipid screening', 'LDL test']),
    ratio('eye_exam_rate', 'Retinopathy screening in window', 'eye_exam_in_window', 'cohort_members', 'Share with retinopathy screening in eye_exam_months (default 24).', 'ind_eye',
          ['eye exam', 'retinal screening', 'retinopathy screening'], caveats=['Community optometry exams are often missing from EMR/FHIR feeds; low values may reflect capture, not care.']),
    ratio('foot_exam_rate', 'Foot exam in 12 months', 'foot_exam_12m', 'cohort_members', 'Share with a diabetic foot exam in 12 months.', 'ind_foot',
          ['foot exam', 'foot check', 'monofilament'], caveats=['Synthea does not generate diabetic foot exams: on synthetic data this rate is 0% by construction (a generator gap, not a care gap).']),
    ratio('statin_rate_40plus', 'Statin use, age >= 40', 'statin_eligible_on_statin', 'statin_eligible', 'Among cohort members aged >= statin_min_age, share with a statin order in 12 months or active.', 'ind_statin',
          ['statin', 'cholesterol medication', 'vascular protection'], caveats=['An order or a pharmacy dispense counts as use; orders alone overstate use.']),
    ratio('all_four_tests_rate', 'All four annual tests', 'all_four_tests_12m', 'cohort_members', 'Share with A1C, BP, LDL-C and kidney screening all in 12 months.', 'ind_all4',
          ['all recommended tests', 'four tests', 'complete annual screening'], benchmark={'ref': O+'bm_dc_snapshot', 'comparable': 'directional only'}),
    ratio('any_gap_rate', 'Any open care gap', 'members_with_any_gap', 'cohort_members', 'Share of cohort with >=1 open gap of any type.', 'ind_any_gap',
          ['care gaps', 'gap in care', 'patients with gaps', 'missed care'], 'lower_is_better'),
    {'name': 'gaps_per_member', 'label': 'Open gaps per member', 'description': 'Average number of open gaps per cohort member (0-9).', 'type': 'derived',
     'type_params': {'expr': 'gap_count_total / cohort_members', 'metrics': [{'name': 'gap_count_total'}, {'name': 'cohort_members'}]},
     'config': {'meta': {'unit': 'gaps per person', 'direction': 'lower_is_better', 'synonyms': ['gap burden', 'average gaps']}}},
    simple('a1c_latest_mean_pct', 'Mean latest A1C (%)', 'a1c_latest_mean', 'Mean of latest valid HbA1c among tested.', '%', ['average A1C', 'mean HbA1c']),
    simple('a1c_latest_median_pct', 'Median latest A1C (%)', 'a1c_latest_median', 'Median of latest valid HbA1c among tested.', '%', ['median A1C']),
    ratio('complication_rate', 'Any diabetes complication', 'members_with_complication', 'cohort_members', 'Share with any recorded retinopathy, kidney disease, neuropathy or foot ulcer.', 'ind_any_gap',
          ['complications', 'end-organ damage'], 'context'),
]
# fix: complication metric should not point at any_gap indicator
metrics[-1]['config']['meta']['ontology_indicator'] = O+'DiabetesComplication'
for mt in metrics:
    if mt['name'] in ('a1c_latest_mean_pct', 'a1c_latest_median_pct'):
        mt['config']['meta'].update({'support_measure': 'a1c_valid_result_12m', 'direction': 'context',
                                     'caveats': ['Context measure: pair with a1c_at_target_rate.']})
# cohort-profile context metrics (v0.3)
CONTEXT = 'Context measure: a mean or median does not show control. Report it beside the at-target rate, never instead of it.'
metrics.append(ratio('bmi_recorded_rate', 'BMI recorded in 12 months', 'bmi_recorded_12m', 'cohort_members',
                     'Share of cohort with a plausible BMI in the 12 months to period end.', 'ind_bmi_recorded', ['BMI recorded', 'weight measured'], 'higher_is_better'))
for name, label, meas, unit, syn in [
        ('bmi_latest_mean_kg_m2', 'Mean latest BMI (kg/m2)', 'bmi_latest_mean', 'kg/m2', ['average BMI', 'mean BMI']),
        ('bmi_latest_median_kg_m2', 'Median latest BMI (kg/m2)', 'bmi_latest_median', 'kg/m2', ['median BMI']),
        ('bp_systolic_mean_mmhg', 'Mean latest systolic BP (mmHg)', 'bp_systolic_latest_mean', 'mmHg', ['average blood pressure', 'mean systolic']),
        ('bp_systolic_median_mmhg', 'Median latest systolic BP (mmHg)', 'bp_systolic_latest_median', 'mmHg', ['median systolic']),
        ('bp_diastolic_mean_mmhg', 'Mean latest diastolic BP (mmHg)', 'bp_diastolic_latest_mean', 'mmHg', ['mean diastolic']),
        ('bp_diastolic_median_mmhg', 'Median latest diastolic BP (mmHg)', 'bp_diastolic_latest_median', 'mmHg', ['median diastolic'])]:
    metrics.append(simple(name, label, meas, MEAS_DESC[meas], unit, syn))
    metrics[-1]['config']['meta'].update({'direction': 'context', 'caveats': [CONTEXT],
                                          'pair_with': 'bp_at_target_rate' if name.startswith('bp_') else 'bmi_recorded_rate',
                                          'support_measure': 'bp_measured_12m' if name.startswith('bp_') else 'bmi_recorded_12m'})
for k, label, cls in MED_CLASSES:
    metrics.append(ratio(f'{k}_rate', f'{label} use', f'members_on_{k}', 'cohort_members',
                         f'Share of cohort with a {label} order in the 12 months to period end, or still active.', f'ind_med_{k}',
                         [f'{label.lower()} use', f'on {label.lower()}', 'medications', 'drug classes'], 'context',
                         ['An order or a pharmacy dispense counts as use; orders alone overstate use.', 'Class level only (ATC); combination products count toward each ingredient class.']))
# v0.4 — DCI alignment (measures M4, M6, M9, M10 and the phenotype's possible-case count)
metrics += [
    ratio('a1c_poor_control_tested_rate', 'Latest A1C > 9% (among tested)', 'a1c_poor_tested', 'a1c_valid_result_12m',
          'Among members with a valid HbA1c in 12 months, share whose latest value > a1c_poor_pct (DCI M4 definition).', 'ind_a1c_poor_tested',
          ['poor control among tested', 'A1C over 9 among tested'], 'lower_is_better',
          ['Denominator is tested members; a1c_poor_control_rate also counts untested people as poorly controlled.']),
    ratio('bp_at_target_measured_rate', 'Latest BP < 130/80 (among measured)', 'bp_at_target', 'bp_measured_12m',
          'Among members with a plausible BP reading in 12 months, share whose latest is < 130/80 (DCI M6 definition).', 'ind_bp_target_measured',
          ['BP control among measured', 'blood pressure at target among measured'], 'higher_is_better',
          ['Denominator is measured members; bp_at_target_rate counts unmeasured people as not at target.']),
    ratio('cardiorenal_agent_rate', 'SGLT2i or GLP-1 RA with CKD or ASCVD', 'ckd_or_ascvd_on_cardiorenal', 'members_ckd_or_ascvd',
          'Among members with CKD or ASCVD, share with an SGLT2 inhibitor or GLP-1 receptor agonist order or dispense in 12 months (DCI M9).', 'ind_cardiorenal',
          ['cardio-renal protection', 'SGLT2 or GLP-1 for CKD', 'heart and kidney protection', 'cardiorenal agent'], 'higher_is_better',
          ['Tirzepatide counts as a GLP-1 RA by default (parameter tirzepatide_as_glp1ra).', 'Laboratory CKD needs 2 abnormal results 90+ days apart; single results do not count.']),
    {'name': 'acute_dm_admissions_per_1000', 'label': 'DKA or hypoglycemia admissions per 1,000', 'type': 'derived',
     'description': 'Inpatient or emergency encounters with a DKA or hypoglycemia diagnosis in 12 months, per 1,000 cohort members (DCI M10; members approximate person-years for an annual period).',
     'type_params': {'expr': 'acute_dm_admissions_12m / cohort_members * 1000', 'metrics': [{'name': 'acute_dm_admissions_12m'}, {'name': 'cohort_members'}]},
     'config': {'meta': {'ontology_indicator': O+'ind_acute_dm_hosp', 'unit': 'per 1,000 members', 'direction': 'lower_is_better', 'min_cell_size': 5,
                         'synonyms': ['acute hospitalization', 'DKA admissions', 'hypoglycemia admissions', 'diabetic emergencies'],
                         'caveats': ['Hypoglycemia counts only for cohort members; coding of DKA and hypoglycemia is incomplete in many sources.']}}},
    ratio('ckd_or_ascvd_rate', 'CKD or ASCVD', 'members_ckd_or_ascvd', 'cohort_members', 'Share of cohort with chronic kidney disease or atherosclerotic cardiovascular disease.',
          'ind_cardiorenal', ['comorbidity', 'CKD', 'ASCVD', 'cardiovascular disease'], 'context'),
    ratio('possible_case_rate', 'Possible undiagnosed cases (medication only)', 'possible_cases_med_only', 'adults',
          'Adults with antihyperglycemic medication but no qualifying diabetes evidence, per adult. Not in the cohort; a data-capture signal.', 'ind_prevalence',
          ['possible cases', 'missing diagnosis', 'medication without diagnosis'], 'context',
          ['Metformin and GLP-1 RAs are also used for prediabetes, PCOS and weight management.']),
]
metrics[-2]['config']['meta']['ontology_indicator'] = None
metrics[-1]['config']['meta']['ontology_indicator'] = None
for mt in metrics:   # value sets behind the v0.4 measures, for explain_measure's evidence trail
    vs_ = {'cardiorenal_agent_rate': ['vs_CKD', 'vs_KidneyDisease', 'vs_ASCVD', 'vs_eGFR', 'vs_UACR', 'vs_ATC_A10'],
           'ckd_or_ascvd_rate': ['vs_CKD', 'vs_KidneyDisease', 'vs_ASCVD', 'vs_eGFR', 'vs_UACR'],
           'acute_dm_admissions_per_1000': ['vs_DKA', 'vs_Hypoglycemia'], 'possible_case_rate': ['vs_ATC_A10']}.get(mt['name'])
    if vs_: mt['config']['meta']['value_sets'] = vs_
# per-gap rates
for g, label in [('a1c_test', 'No recent A1C'), ('a1c_control', 'A1C above target'), ('bp_control', 'BP not at target'), ('kidney_screen', 'No kidney screening'),
                 ('lipid_test', 'No LDL-C in window'), ('eye_exam', 'No eye exam in window'), ('foot_exam', 'No foot exam'), ('statin', 'Age 40+ without statin'),
                 ('cardiorenal', 'CKD or ASCVD without SGLT2i or GLP-1 RA')]:
    metrics.append(ratio(f'gap_{g}_rate', f'Gap: {label}', f'gap_{g}', 'cohort_members', f'Share of cohort with open gap {g}. Use with dimension breakdowns to find where gaps concentrate.',
                         'ind_any_gap', [f'{label.lower()}'], 'lower_is_better'))
    metrics[-1]['config']['meta']['ontology_gap_type'] = f'dcg:gap_{g.split("_")[0] if g in ("eye_exam","foot_exam") else g}'
# DQ metrics
for d, label in [('a1c_no_value', 'A1C tests without value'), ('a1c_unit', 'A1C unit non-conformance'), ('a1c_implausible', 'Implausible A1C'),
                 ('missing_onset', 'Missing diagnosis onset'), ('dm_type_conflict', 'Conflicting diabetes type'),
                 ('dm_duplicate', 'Duplicate diabetes diagnosis')]:
    metrics.append(ratio(f'dq_{d}_rate', f'DQ: {label}', f'dq_{d}', 'cohort_members', f'Share of cohort affected by data-quality issue: {label}.', 'ind_any_gap',
                         ['data quality', label.lower()], 'lower_is_better'))
    metrics[-1]['config']['meta']['ontology_indicator'] = None
    metrics[-1]['config']['meta']['ontology_dq_issue'] = dm_measures[[x['name'] for x in dm_measures].index(f'dq_{d}')]['config']['meta']['ontology']

# per-gap gap-type IRIs that match the ontology concept names
gapmap = {'a1c_test': 'gap_a1c_test', 'a1c_control': 'gap_a1c_control', 'bp_control': 'gap_bp_control', 'kidney_screen': 'gap_kidney',
          'lipid_test': 'gap_lipid', 'eye_exam': 'gap_eye', 'foot_exam': 'gap_foot', 'statin': 'gap_statin', 'cardiorenal': 'gap_cardiorenal'}
for mt in metrics:
    if mt['name'].startswith('gap_') and mt['name'].endswith('_rate'):
        g = mt['name'][4:-5]; mt['config']['meta']['ontology_gap_type'] = 'dcg:' + gapmap[g]; mt['config']['meta']['ontology_indicator'] = 'dcg:ind_any_gap'
    if mt['config']['meta'].get('ontology_indicator') is None: mt['config']['meta'].pop('ontology_indicator', None)

doc = {'version': 2, 'semantic_models': [pop, dm], 'metrics': metrics,
       'saved_queries': [
           {'name': 'care_gap_scorecard', 'description': 'Headline scorecard for the dashboard landing page.',
            'query_params': {'metrics': ['cohort_size', 'a1c_tested_12m_rate', 'a1c_at_target_rate', 'bp_at_target_rate', 'kidney_screened_rate', 'eye_exam_rate', 'foot_exam_rate', 'statin_rate_40plus', 'any_gap_rate'],
                             'group_by': ["TimeDimension('patient_period__period_end', 'day')"]}},
           {'name': 'gaps_by_age_sex', 'description': 'Per-gap rates by age band and sex.',
            'query_params': {'metrics': [f'gap_{g}_rate' for g in gapmap], 'group_by': ["Dimension('patient_period__age_band')", "Dimension('patient_period__sex')"]}},
           {'name': 'cohort_profile', 'description': 'Profile of the diabetes cohort in one call: size, testing and control, BMI and BP levels, complications, medication classes and gaps. Group by age_band, sex, diabetes_type or bmi_category for distributions.',
            'query_params': {'metrics': ['cohort_size', 'a1c_tested_12m_rate', 'a1c_at_target_rate', 'a1c_latest_median_pct', 'bp_at_target_rate',
                                         'bp_systolic_median_mmhg', 'bp_diastolic_median_mmhg', 'bmi_recorded_rate', 'bmi_latest_median_kg_m2',
                                         'complication_rate', 'antihyperglycemic_rate', 'metformin_rate', 'insulin_rate', 'sglt2i_rate', 'glp1ra_rate',
                                         'statin_rate_40plus', 'acei_arb_rate', 'any_gap_rate'], 'group_by': []}},
           {'name': 'dci_core_measures', 'description': 'The DCI measure set M2-M10 as implemented in DCG (prevalence M1 is in the adult_population model). Equity stratification (M11) = group by a restricted equity dimension with the equity role.',
            'query_params': {'metrics': ['a1c_tested_12m_rate', 'a1c_at_target_rate', 'a1c_poor_control_tested_rate', 'kidney_screened_rate', 'bp_at_target_measured_rate',
                                         'statin_rate_40plus', 'eye_exam_rate', 'cardiorenal_agent_rate', 'acute_dm_admissions_per_1000'], 'group_by': []}},
           {'name': 'cohort_by_case_basis', 'description': 'Cohort size and key rates by the evidence route that qualified each person (DM-ADULT-CASE).',
            'query_params': {'metrics': ['cohort_size', 'a1c_tested_12m_rate', 'antihyperglycemic_rate', 'any_gap_rate'], 'group_by': ["Dimension('patient_period__case_basis')"]}},
           {'name': 'data_quality_panel', 'description': 'DQ metrics for the AI-Ready Data Quality case study.',
            'query_params': {'metrics': [m_['name'] for m_ in metrics if m_['name'].startswith('dq_')], 'group_by': ["Dimension('patient_period__data_source')"]}}]}

hdr = """# Diabetes Care Gaps — Semantic Model (dbt Semantic Layer / MetricFlow spec)
# Layer L3 of: FHIR Bulk $export -> SQL-on-FHIR views (L1) -> marts (L2) -> THIS (L3) -> agent contract (L4)
# Every measure sets create_metric: true, so ratio numerators/denominators resolve to same-named metrics.
# Every measure/metric carries config.meta.ontology* IRIs into ontology/dcg-ontology.ttl and
# synonyms used by the AI agent for intent resolution. Parameters live in dbt_project.yml vars.
# Generated by scripts/gen_semantic_model.py — edit the generator, then regenerate.
"""
open('models/semantic/dcg_semantic_model.yml', 'w').write(hdr + yaml.dump(doc, Dumper=NoAlias, sort_keys=False, allow_unicode=True, width=140))
print(len(metrics), 'metrics,', len(dm_measures) + 2, 'measures')
