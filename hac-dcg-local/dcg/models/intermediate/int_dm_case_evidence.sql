-- int_dm_case_evidence
-- Grain: one row per person with any diabetes evidence on or before the period end.
-- Implements case phenotype DM-ADULT-CASE (dcg:pheno_DM_ADULT_CASE), versioned by dbt vars:
--   qualifies if any of: declared diabetes Condition (when pheno_accept_declared_condition);
--   >= 1 inpatient diabetes diagnosis; >= 2 ambulatory/emergency diabetes diagnoses on different days within
--   pheno_claims_window_days; >= pheno_a1c_min_results HbA1c >= pheno_a1c_threshold on separate days
--   (results inside a gestational-diabetes window are ignored). Medication is supporting evidence only
--   unless pheno_med_qualifies (then metformin alone and GLP-1 RA alone still do not qualify).
-- Age and vital status are applied in fct_adult_population_period.
-- Ontology: dcg:CohortMembership, dcg:EvidenceRouteScheme

with params as (
    select
        cast('{{ var("period_end", "2026-09-30") }}' as date)          as period_end,
        {{ var("pheno_accept_declared_condition", true) }}              as accept_declared,
        cast({{ var("pheno_claims_window_days", 730) }} as integer)    as claims_window,
        cast({{ var("pheno_a1c_threshold", 6.5) }} as double)          as a1c_threshold,
        cast({{ var("pheno_a1c_min_results", 2) }} as integer)         as a1c_min_results,
        {{ var("pheno_med_qualifies", false) }}                         as med_qualifies,
        '{{ var("phenotype_id", "DM-ADULT-CASE") }}'                    as phenotype_id,
        '{{ var("phenotype_version", "0.1") }}'                         as phenotype_version
),

cc as (select c.* from {{ ref('int_condition_coded') }} c, params p where c.condition_date <= p.period_end),
dmc as (select * from cc where value_set = 'vs_DiabetesMellitus'),
gdm as (select patient_id, condition_date from cc where value_set = 'vs_GDM'),

declared as (select patient_id, min(condition_date) as d from dmc group by patient_id),
hospital as (select patient_id, min(condition_date) as d from dmc where encounter_setting = 'inpatient' group by patient_id),
amb_days as (select distinct patient_id, condition_date from dmc where encounter_setting in ('ambulatory', 'emergency')),
ambulatory as (   -- qualifying date = the second diagnosis within the window
    select a.patient_id, min(b.condition_date) as d
    from amb_days a
    join amb_days b on b.patient_id = a.patient_id and b.condition_date > a.condition_date
    cross join params p
    where date_diff('day', a.condition_date, b.condition_date) <= p.claims_window
    group by a.patient_id
),
a1c_days as (
    select distinct o.patient_id, o.eff_date
    from {{ ref('int_observation_std') }} o, params p
    where o.value_set = 'vs_HbA1c' and o.unit_accepted = 1 and o.eff_date <= p.period_end
      and o.value_std >= p.a1c_threshold and o.value_std between 3 and 20
      and not exists (select 1 from gdm g where g.patient_id = o.patient_id
                      and o.eff_date between g.condition_date - interval 280 days and g.condition_date + interval 84 days)
),
lab as (
    select patient_id, eff_date as d
    from (select a.*, row_number() over (partition by patient_id order by eff_date) as rn from a1c_days a) x, params p
    where x.rn = p.a1c_min_results
),
med as (
    select m.patient_id, min(m.exposure_date) as d,
           max(case when m.therapy_class in ('insulin', 'sglt2i', 'dpp4i', 'sulfonylurea', 'tzd', 'agi', 'other_antihyperglycemic') then 1 else 0 end) as specific_class
    from {{ ref('int_medication_exposure') }} m, params p
    where m.exposure_date <= p.period_end
      and m.therapy_class in ('metformin', 'insulin', 'sglt2i', 'glp1ra', 'tirzepatide', 'dpp4i', 'sulfonylurea', 'tzd', 'agi', 'other_antihyperglycemic')
    group by m.patient_id
),
types as (
    select patient_id,
           max(case when value_set = 'vs_T1DM' then 1 else 0 end)            as has_t1,
           max(case when value_set = 'vs_T2DM' then 1 else 0 end)            as has_t2,
           max(case when value_set = 'vs_OtherSpecifiedDM' then 1 else 0 end) as has_other,
           max(case when value_set = 'vs_DiabetesMellitus' and onset_datetime is null then 1 else 0 end) as dq_missing_onset,
           -- duplicate check on declared (problem-list) conditions only: repeated encounter diagnoses are expected
           count(distinct case when value_set = 'vs_DiabetesMellitus' and encounter_setting = 'none' then condition_id end) as dm_record_count,
           count(distinct case when value_set = 'vs_DiabetesMellitus' and encounter_setting = 'none'
                               then coalesce(snomed_code, replace(icd10ca_code, '.', '')) end) as dm_code_count
    from cc group by patient_id
),
people as (
    select patient_id from declared union select patient_id from hospital union select patient_id from ambulatory
    union select patient_id from lab union select patient_id from med
),
flags as (
    select
        pe.patient_id, p.phenotype_id, p.phenotype_version,
        case when de.patient_id is not null then 1 else 0 end as ev_declared_condition,
        case when ho.patient_id is not null then 1 else 0 end as ev_hospital_dx,
        case when am.patient_id is not null then 1 else 0 end as ev_ambulatory_2x,
        case when la.patient_id is not null then 1 else 0 end as ev_lab_a1c,
        case when me.patient_id is not null then 1 else 0 end as ev_medication,
        de.d as declared_date, ho.d as hospital_date, am.d as ambulatory_date, la.d as lab_date, me.d as med_date,
        coalesce(me.specific_class, 0) as med_specific_class,
        p.accept_declared, p.med_qualifies,
        coalesce(t.has_t1, 0) as has_t1, coalesce(t.has_t2, 0) as has_t2, coalesce(t.has_other, 0) as has_other,
        coalesce(t.dq_missing_onset, 0) as dq_missing_onset,
        coalesce(t.dm_record_count, 0) as dm_record_count, coalesce(t.dm_code_count, 0) as dm_code_count
    from people pe
    cross join params p
    left join declared de on de.patient_id = pe.patient_id
    left join hospital ho on ho.patient_id = pe.patient_id
    left join ambulatory am on am.patient_id = pe.patient_id
    left join lab la on la.patient_id = pe.patient_id
    left join med me on me.patient_id = pe.patient_id
    left join types t on t.patient_id = pe.patient_id
)

select
    f.*,
    case when (accept_declared and ev_declared_condition = 1) or ev_hospital_dx = 1 or ev_ambulatory_2x = 1 or ev_lab_a1c = 1
              or (med_qualifies and med_specific_class = 1) then 1 else 0 end            as qualifies,
    case when ev_hospital_dx = 1 then 'hospital_dx'
         when ev_ambulatory_2x = 1 then 'ambulatory_2x'
         when accept_declared and ev_declared_condition = 1 then 'declared_condition'
         when ev_lab_a1c = 1 then 'lab_a1c_2x'
         when med_qualifies and med_specific_class = 1 then 'medication'
         when ev_medication = 1 then 'medication_only'
         else 'insufficient' end                                                          as case_basis,
    least(case when accept_declared then declared_date end, hospital_date, ambulatory_date, lab_date,
          case when med_qualifies and med_specific_class = 1 then med_date end)            as index_date,
    case when has_t1 = 1 and has_t2 = 0 and has_other = 0 then 'type_1'
         when has_t2 = 1 and has_t1 = 0 and has_other = 0 then 'type_2'
         when has_other = 1 and has_t1 = 0 and has_t2 = 0 then 'other_specified'
         else 'unclassified' end                                                          as diabetes_type
from flags f
