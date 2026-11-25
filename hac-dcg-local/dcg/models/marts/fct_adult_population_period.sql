-- fct_adult_population_period
-- Grain: one row per adult (age >= 18) alive at the measurement period end.
-- Purpose: denominator for prevalence; superset of the diabetes cohort.
-- Dialect: DuckDB (dbt-compatible; ref()/var() are rendered by dbt or tests/run_pipeline.py).
-- Ontology: dcg:Person, dcg:AgeBand, dcg:Province, dcg:DiabetesCohort, dcg:EquityStratifier
-- has_diabetes comes from case phenotype DM-ADULT-CASE (int_dm_case_evidence).

with params as (
    select
        cast('{{ var("period_end", "2026-09-30") }}' as date)  as period_end,
        '{{ var("data_source", "synthetic") }}'                 as data_source
),

patient as (
    select
        p.patient_id,
        p.birth_date,
        p.administrative_gender,
        p.province,
        p.fsa,
        p.service_language, p.indigenous_identity, p.racialized_group,
        cast(floor(date_diff('day', p.birth_date, prm.period_end) / 365.25) as integer) as age_at_period_end,
        prm.period_end,
        prm.data_source
    from {{ ref('dcg_patient') }} p
    cross join params prm
    where p.birth_date is not null
      and p.birth_date <= prm.period_end
      and (p.deceased_datetime is null or cast(p.deceased_datetime as date) > prm.period_end)
      and coalesce(p.deceased_flag, false) = false
),

dm as (select * from {{ ref('int_dm_case_evidence') }})

select
    pt.patient_id,
    pt.period_end,
    pt.data_source,
    pt.age_at_period_end,
    case when pt.age_at_period_end < 40 then '18-39'
         when pt.age_at_period_end < 65 then '40-64'
         else '65+' end                                       as age_band,
    case when pt.age_at_period_end < 20 then '18-19'
         when pt.age_at_period_end < 35 then '20-34'
         when pt.age_at_period_end < 50 then '35-49'
         when pt.age_at_period_end < 65 then '50-64'
         when pt.age_at_period_end < 80 then '65-79'
         else '80+' end                                       as age_band_phac,
    coalesce(pt.administrative_gender, 'unknown')            as sex,
    coalesce(pt.province, 'unknown')                         as province,
    pt.fsa,
    coalesce(pt.service_language, 'not recorded')            as service_language,
    coalesce(pt.indigenous_identity, 'not recorded')         as indigenous_identity,
    coalesce(pt.racialized_group, 'not recorded')            as racialized_group,
    coalesce(dm.qualifies, 0)                                as has_diabetes,
    case when dm.qualifies = 0 and dm.ev_medication = 1 then 1 else 0 end as possible_case_med_only,
    coalesce(dm.case_basis, 'none')                          as case_basis,
    '{{ var("phenotype_id", "DM-ADULT-CASE") }}'              as phenotype_id,
    '{{ var("phenotype_version", "0.1") }}'                   as phenotype_version
from patient pt
left join dm on dm.patient_id = pt.patient_id
where pt.age_at_period_end >= 18
