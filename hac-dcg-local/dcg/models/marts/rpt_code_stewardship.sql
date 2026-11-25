-- rpt_code_stewardship
-- Grain: one row per source code (or unit) that the pipeline could not map, by resource and issue.
-- This is the terminology stewardship queue (DCI 4.7): unmapped codes are kept with their original code and
-- counted here, never dropped silently or force-mapped. Record counts only; no person identifiers.
-- Ontology: dcg:StewardshipQueue, dcg:UnmappedCode, dcg:UnitNonConformance

with cond as (
    select 'Condition' as resource_type, 'no standard code (SNOMED CT or ICD-10-CA)' as issue,
           null as code_system, null as code, coalesce(code_display, '(no display)') as source_text, count(*) as record_count
    from {{ ref('dcg_condition') }}
    where snomed_code is null and icd10ca_code is null
    group by code_display
),
med as (
    select 'Medication' as resource_type, 'drug not classified to a therapy class' as issue,
           x.med_code_system as code_system, x.med_code as code, coalesce(x.med_text, x.med_display, '(no text)') as source_text, count(*) as record_count
    from (
        select medication_request_id as id, med_code_system, med_code, med_text, med_display from {{ ref('dcg_medication_request') }}
        union all
        select medication_dispense_id, med_code_system, med_code, med_text, med_display from {{ ref('dcg_medication_dispense') }}
    ) x
    where x.id not in (select exposure_id from {{ ref('int_medication_exposure') }})
    group by 1, 2, 3, 4, 5
),
unit as (
    select 'Observation' as resource_type, 'unit not recognised for ' || value_set as issue,
           'http://unitsofmeasure.org' as code_system, coalesce(ucum_unit, '(missing)') as code, loinc_code as source_text, count(*) as record_count
    from {{ ref('int_observation_std') }}
    where unit_accepted = 0
    group by value_set, ucum_unit, loinc_code
)

select *, 'pending' as stewardship_status from cond
union all select *, 'pending' from med
union all select *, 'pending' from unit
