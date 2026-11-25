-- fct_diabetes_patient_period
-- Grain: one row per diabetes-cohort member per measurement period.
-- Every care-process, outcome, gap and data-quality flag is a 0/1 column,
-- so every indicator in the semantic model is SUM(flag) / SUM(denominator flag).
-- Dialect: DuckDB (dbt-compatible).
-- Ontology: dcg:DiabetesCohort, dcg:CareProcess, dcg:CareOutcome, dcg:CareGap, dcg:DataQualityIssue
-- v0.4: cohort from case phenotype DM-ADULT-CASE; codes from int_condition_coded (SNOMED CT + ICD-10-CA);
-- labs from int_observation_std (standardised units); medications from int_medication_exposure (orders +
-- dispenses, ATC prefix); CKD/ASCVD and the cardio-renal gap; DKA/hypoglycemia admissions; lineage columns.
-- Parameters (dcg:param_*) arrive as dbt vars; defaults = Diabetes Canada CPG-based values.

with params as (
    select
        cast('{{ var("period_end", "2026-09-30") }}' as date)                                          as period_end,
        cast('{{ var("period_end", "2026-09-30") }}' as date) - interval '{{ var("a1c_recent_months", 6) }} months'  as a1c_recent_start,
        cast('{{ var("period_end", "2026-09-30") }}' as date) - interval '12 months'                   as annual_start,
        cast('{{ var("period_end", "2026-09-30") }}' as date) - interval '{{ var("lipid_months", 36) }} months'      as lipid_start,
        cast('{{ var("period_end", "2026-09-30") }}' as date) - interval '{{ var("eye_exam_months", 24) }} months'   as eye_start,
        cast({{ var("a1c_target_pct", 7.0) }} as double)       as a1c_target,
        cast({{ var("a1c_poor_pct", 9.0) }} as double)         as a1c_poor,
        cast({{ var("bp_sys_target", 130) }} as double)        as bp_sys_target,
        cast({{ var("bp_dia_target", 80) }} as double)         as bp_dia_target,
        cast({{ var("statin_min_age", 40) }} as integer)       as statin_min_age,
        cast('{{ var("period_end", "2026-09-30") }}' as date) - interval '24 months'                   as ckd_lab_start,
        {{ var("tirzepatide_as_glp1ra", true) }}                as tirzepatide_as_glp1ra
),

pop as (select * from {{ ref('fct_adult_population_period') }} where has_diabetes = 1),
ev  as (select * from {{ ref('int_dm_case_evidence') }}),
cc  as (select c.* from {{ ref('int_condition_coded') }} c, params p where c.condition_date <= p.period_end),
map_version as (select max(map_version) as map_version from {{ ref('seed_code_valueset') }}),

complications as (
    select
        patient_id,
        max(case when value_set = 'vs_Retinopathy'   then 1 else 0 end) as has_retinopathy,
        max(case when value_set = 'vs_KidneyDisease' then 1 else 0 end) as has_kidney_disease,
        max(case when value_set = 'vs_Neuropathy'    then 1 else 0 end) as has_neuropathy,
        max(case when value_set = 'vs_FootUlcer'     then 1 else 0 end) as has_foot_ulcer,
        max(case when value_set in ('vs_CKD', 'vs_KidneyDisease') then 1 else 0 end) as has_ckd_coded,
        max(case when value_set = 'vs_ASCVD'         then 1 else 0 end) as has_ascvd
    from cc
    group by patient_id
),

acute as (   -- DKA or hypoglycemia diagnosed at an inpatient or emergency encounter in 12 months (DCI M10)
    select c.patient_id, count(distinct coalesce(c.encounter_id, c.condition_id)) as acute_dm_admissions_12m
    from cc c, params p
    where c.value_set in ('vs_DKA', 'vs_Hypoglycemia')
      and c.encounter_setting in ('inpatient', 'emergency')
      and c.condition_date > p.annual_start
    group by c.patient_id
),

-- ---------- labs ------------------------------------------------------
labs as (   -- standardised values (value_std in unit_std); original value and unit kept upstream
    select o.patient_id, o.value_set, o.eff_date, o.value_std as value_numeric, o.unit_std, o.ucum_unit, o.unit_accepted, o.unit_converted
    from {{ ref('int_observation_std') }} o
    cross join params p
    where o.eff_date <= p.period_end
      and o.eff_date >  p.lipid_start                                  -- widest window needed
),

ckd_lab as (   -- laboratory CKD: 2 eGFR < 60, or 2 urine ACR >= 3 mg/mmol, at least 90 days apart within 24 months
    select l1.patient_id, 1 as has_ckd_lab
    from labs l1
    join labs l2 on l2.patient_id = l1.patient_id and l2.value_set = l1.value_set
                and date_diff('day', l1.eff_date, l2.eff_date) >= 90
    cross join params p
    where l1.eff_date > p.ckd_lab_start and l1.unit_accepted = 1 and l2.unit_accepted = 1
      and ((l1.value_set = 'vs_eGFR' and l1.value_numeric < 60 and l2.value_numeric < 60)
        or (l1.value_set = 'vs_UACR' and l1.value_numeric >= 3 and l2.value_numeric >= 3))
    group by l1.patient_id
),

a1c_ranked as (
    select l.*, row_number() over (partition by patient_id order by eff_date desc) as rn
    from labs l, params p
    where value_set = 'vs_HbA1c'
      and eff_date > p.annual_start
      and value_numeric is not null
      and unit_accepted = 1                                             -- % or mmol/mol (converted to %)
      and value_numeric between 3 and 20                                -- SHACL HbA1cShape
),

bmi_ranked as (   -- latest plausible BMI in 12 months (context measure, not a target)
    select l.patient_id, l.value_numeric,
           row_number() over (partition by l.patient_id order by l.eff_date desc) as rn
    from labs l, params p
    where l.value_set = 'vs_BMI'
      and l.eff_date > p.annual_start
      and l.value_numeric between 10 and 80
),

lab_flags as (
    select
        l.patient_id,
        max(case when value_set = 'vs_HbA1c' and eff_date > p.a1c_recent_start then 1 else 0 end) as a1c_tested_recent,
        max(case when value_set = 'vs_HbA1c' and eff_date > p.annual_start     then 1 else 0 end) as a1c_tested_12m,
        max(case when value_set = 'vs_eGFR'  and eff_date > p.annual_start     then 1 else 0 end) as egfr_12m,
        max(case when value_set = 'vs_UACR'  and eff_date > p.annual_start     then 1 else 0 end) as uacr_12m,
        max(case when value_set = 'vs_LDL'   and eff_date > p.annual_start     then 1 else 0 end) as ldl_12m,
        max(case when value_set = 'vs_LDL'   and eff_date > p.lipid_start      then 1 else 0 end) as ldl_in_window,
        -- data-quality flags (dcg:DataQualityIssue)
        max(case when value_set = 'vs_HbA1c' and eff_date > p.annual_start and value_numeric is null then 1 else 0 end) as dq_a1c_no_value,
        max(case when value_set = 'vs_HbA1c' and eff_date > p.annual_start and value_numeric is not null
                  and unit_accepted = 0 then 1 else 0 end)                                            as dq_a1c_unit,
        max(case when value_set = 'vs_HbA1c' and eff_date > p.annual_start and unit_accepted = 1
                  and (value_numeric < 3 or value_numeric > 20) then 1 else 0 end)                    as dq_a1c_implausible,
        max(case when value_set = 'vs_HbA1c' and eff_date > p.annual_start and unit_converted = 1 then 1 else 0 end) as a1c_unit_converted
    from labs l cross join params p
    group by l.patient_id
),

-- ---------- blood pressure -------------------------------------------
bp_ranked as (
    select b.patient_id, b.systolic, b.diastolic,
           row_number() over (partition by b.patient_id order by b.effective_datetime desc) as rn
    from {{ ref('dcg_blood_pressure') }} b, params p
    where cast(b.effective_datetime as date) <= p.period_end
      and cast(b.effective_datetime as date) >  p.annual_start
      and b.systolic is not null and b.diastolic is not null
      and b.diastolic < b.systolic                                       -- SHACL BloodPressureShape
      and b.systolic between 50 and 300 and b.diastolic between 20 and 200
),

-- ---------- procedures -----------------------------------------------
proc_flags as (
    select
        pr.patient_id,
        max(case when vs.value_set = 'vs_EyeExam'  and cast(pr.performed_datetime as date) > p.eye_start    then 1 else 0 end) as eye_exam_in_window,
        max(case when vs.value_set = 'vs_FootExam' and cast(pr.performed_datetime as date) > p.annual_start then 1 else 0 end) as foot_exam_12m
    from {{ ref('dcg_procedure') }} pr
    join {{ ref('seed_code_valueset') }} vs on vs.code_system = 'http://snomed.info/sct' and vs.code = pr.snomed_code
           and vs.value_set in ('vs_EyeExam', 'vs_FootExam')
    cross join params p
    where cast(pr.performed_datetime as date) <= p.period_end
    group by pr.patient_id
),

-- ---------- medications (orders + dispenses, classified by ATC prefix or ingredient) ----
meds as (
    select m.patient_id, m.therapy_class
    from {{ ref('int_medication_exposure') }} m
    cross join params p
    where m.exposure_date <= p.period_end
      and (m.exposure_date > p.annual_start or (m.exposure_type = 'order' and m.status = 'active'))
),

med_flags as (
    select
        patient_id,
        max(case when therapy_class = 'statin'                                   then 1 else 0 end) as on_statin,
        max(case when therapy_class = 'acei_arb'                                 then 1 else 0 end) as on_acei_arb,
        max(case when therapy_class = 'metformin'                                then 1 else 0 end) as on_metformin,
        max(case when therapy_class = 'insulin'                                  then 1 else 0 end) as on_insulin,
        max(case when therapy_class in ('sglt2i', 'glp1ra')
                   or (therapy_class = 'tirzepatide' and p.tirzepatide_as_glp1ra)  then 1 else 0 end) as on_sglt2i_or_glp1ra,
        max(case when therapy_class = 'sglt2i'                                   then 1 else 0 end) as on_sglt2i,
        max(case when therapy_class = 'glp1ra'
                   or (therapy_class = 'tirzepatide' and p.tirzepatide_as_glp1ra)  then 1 else 0 end) as on_glp1ra,
        max(case when therapy_class = 'tzd'                                      then 1 else 0 end) as on_tzd,
        max(case when therapy_class = 'dpp4i'                                    then 1 else 0 end) as on_dpp4i,
        max(case when therapy_class = 'sulfonylurea'                             then 1 else 0 end) as on_sulfonylurea,
        max(case when therapy_class in ('metformin','insulin','sglt2i','glp1ra','tirzepatide','dpp4i','sulfonylurea','tzd','agi','other_antihyperglycemic')
                                                                                 then 1 else 0 end) as on_antihyperglycemic
    from meds cross join params p
    group by patient_id
),

-- ---------- assemble --------------------------------------------------
base as (
    select
        pop.patient_id, pop.period_end, pop.data_source, pop.age_at_period_end,
        pop.age_band, pop.age_band_phac, pop.sex, pop.province, pop.fsa,
        pop.service_language, pop.indigenous_identity, pop.racialized_group,
        ev.diabetes_type,                                             -- heuristic: type_1 | type_2 | other_specified | unclassified
        ev.case_basis, ev.index_date, ev.phenotype_id, ev.phenotype_version, mv.map_version,
        ev.ev_declared_condition, ev.ev_hospital_dx, ev.ev_ambulatory_2x, ev.ev_lab_a1c, ev.ev_medication,
        cast(floor(date_diff('day', ev.index_date, pop.period_end) / 365.25) as integer) as years_since_diagnosis,

        coalesce(lf.a1c_tested_recent, 0) as a1c_tested_recent,
        coalesce(lf.a1c_tested_12m, 0)    as a1c_tested_12m,
        a1c.value_numeric                 as a1c_latest_value,
        case when a1c.value_numeric is not null then 1 else 0 end    as a1c_has_valid_result,
        case when a1c.value_numeric <= p.a1c_target then 1 else 0 end as a1c_at_target,
        case when a1c.value_numeric is null or a1c.value_numeric > p.a1c_poor then 1 else 0 end as a1c_poor_or_untested,
        case when a1c.value_numeric > p.a1c_poor then 1 else 0 end    as a1c_poor_tested,
        coalesce(lf.a1c_unit_converted, 0) as a1c_unit_converted,

        case when bp.systolic is not null then 1 else 0 end          as bp_measured_12m,
        bp.systolic                                                  as bp_latest_systolic,
        bp.diastolic                                                 as bp_latest_diastolic,
        bmi.value_numeric                                            as bmi_latest_value,
        case when bmi.value_numeric is not null then 1 else 0 end    as bmi_recorded_12m,
        case when bp.systolic < p.bp_sys_target and bp.diastolic < p.bp_dia_target then 1 else 0 end as bp_at_target,

        case when coalesce(lf.egfr_12m,0) = 1 and coalesce(lf.uacr_12m,0) = 1 then 1 else 0 end as kidney_screened_12m,
        coalesce(lf.ldl_in_window, 0)     as lipid_tested_in_window,
        coalesce(lf.ldl_12m, 0)           as lipid_tested_12m,
        coalesce(pf.eye_exam_in_window,0) as eye_exam_in_window,
        coalesce(pf.foot_exam_12m, 0)     as foot_exam_12m,

        case when pop.age_at_period_end >= p.statin_min_age then 1 else 0 end as statin_eligible,
        coalesce(mf.on_statin, 0)            as on_statin,
        coalesce(mf.on_acei_arb, 0)          as on_acei_arb,
        coalesce(mf.on_metformin, 0)         as on_metformin,
        coalesce(mf.on_insulin, 0)           as on_insulin,
        coalesce(mf.on_sglt2i_or_glp1ra, 0)  as on_sglt2i_or_glp1ra,
        coalesce(mf.on_sglt2i, 0)            as on_sglt2i,
        coalesce(mf.on_glp1ra, 0)            as on_glp1ra,
        coalesce(mf.on_dpp4i, 0)             as on_dpp4i,
        coalesce(mf.on_sulfonylurea, 0)      as on_sulfonylurea,
        coalesce(mf.on_antihyperglycemic, 0) as on_antihyperglycemic,
        coalesce(mf.on_tzd, 0)               as on_tzd,
        case when coalesce(cx.has_ckd_coded, 0) = 1 or coalesce(ck.has_ckd_lab, 0) = 1 then 1 else 0 end as has_ckd,
        coalesce(cx.has_ascvd, 0)            as has_ascvd,
        case when coalesce(cx.has_ckd_coded, 0) = 1 or coalesce(ck.has_ckd_lab, 0) = 1 or coalesce(cx.has_ascvd, 0) = 1 then 1 else 0 end as has_ckd_or_ascvd,
        coalesce(ac.acute_dm_admissions_12m, 0) as acute_dm_admissions_12m,

        coalesce(cx.has_retinopathy, 0)    as has_retinopathy,
        coalesce(cx.has_kidney_disease, 0) as has_kidney_disease,
        coalesce(cx.has_neuropathy, 0)     as has_neuropathy,
        coalesce(cx.has_foot_ulcer, 0)     as has_foot_ulcer,

        coalesce(lf.dq_a1c_no_value, 0)    as dq_a1c_no_value,
        coalesce(lf.dq_a1c_unit, 0)        as dq_a1c_unit,
        coalesce(lf.dq_a1c_implausible, 0) as dq_a1c_implausible,
        coalesce(ev.dq_missing_onset, 0)   as dq_missing_onset,
        case when ev.has_t1 = 1 and ev.has_t2 = 1 then 1 else 0 end as dq_dm_type_conflict,
        case when ev.dm_record_count > ev.dm_code_count then 1 else 0 end as dq_dm_duplicate
    from pop
    cross join params p
    cross join map_version mv
    left join ev            on ev.patient_id = pop.patient_id
    left join ckd_lab ck    on ck.patient_id = pop.patient_id
    left join acute ac      on ac.patient_id = pop.patient_id
    left join lab_flags lf  on lf.patient_id = pop.patient_id
    left join a1c_ranked a1c on a1c.patient_id = pop.patient_id and a1c.rn = 1
    left join bp_ranked bp  on bp.patient_id = pop.patient_id and bp.rn = 1
    left join bmi_ranked bmi on bmi.patient_id = pop.patient_id and bmi.rn = 1
    left join proc_flags pf on pf.patient_id = pop.patient_id
    left join med_flags mf  on mf.patient_id = pop.patient_id
    left join complications cx on cx.patient_id = pop.patient_id
)

select
    base.*,
    1                                                            as in_cohort,
    case when has_retinopathy + has_kidney_disease + has_neuropathy + has_foot_ulcer > 0 then 1 else 0 end as has_any_complication,
    case when a1c_tested_12m = 1 and lipid_tested_12m = 1 and kidney_screened_12m = 1 and bp_measured_12m = 1
         then 1 else 0 end                                       as all_four_tests_12m,
    -- care gaps (dcg:GapTypeScheme notations)
    1 - a1c_tested_recent                                        as gap_a1c_test,
    case when a1c_has_valid_result = 1 and a1c_at_target = 0 then 1 else 0 end as gap_a1c_control,
    1 - bp_at_target                                             as gap_bp_control,
    1 - kidney_screened_12m                                      as gap_kidney_screen,
    1 - lipid_tested_in_window                                   as gap_lipid_test,
    1 - eye_exam_in_window                                       as gap_eye_exam,
    1 - foot_exam_12m                                            as gap_foot_exam,
    case when statin_eligible = 1 and on_statin = 0 then 1 else 0 end as gap_statin,
    case when has_ckd_or_ascvd = 1 and on_sglt2i_or_glp1ra = 0 then 1 else 0 end as gap_cardiorenal,
    has_ckd_or_ascvd * on_sglt2i_or_glp1ra                       as ckd_or_ascvd_on_cardiorenal,
    (1 - a1c_tested_recent)
      + (case when a1c_has_valid_result = 1 and a1c_at_target = 0 then 1 else 0 end)
      + (1 - bp_at_target) + (1 - kidney_screened_12m) + (1 - lipid_tested_in_window)
      + (1 - eye_exam_in_window) + (1 - foot_exam_12m)
      + (case when statin_eligible = 1 and on_statin = 0 then 1 else 0 end)
      + (case when has_ckd_or_ascvd = 1 and on_sglt2i_or_glp1ra = 0 then 1 else 0 end) as gap_count
from base
-- any_gap is derived in the semantic model as gap_count > 0 (see dimension has_any_gap)
