-- int_condition_coded
-- Grain: one row per Condition x governed value set it maps to (SNOMED CT exact or ICD-10-CA prefix).
-- Carries the map governance fields (relation, status, version) for the evidence trail, and the setting
-- of the linked Encounter (inpatient | emergency | ambulatory) for the DM-ADULT-CASE phenotype routes.
-- Ontology: dcg:ConditionRecord, dcg:CohortMembership (evidence), dcg:StewardshipQueue (unmatched codes are reported elsewhere)

with vs as (select * from {{ ref('seed_code_valueset') }}),

cond as (
    select src.*, cast(coalesce(src.onset_datetime, src.recorded_date) as date) as condition_date
    from {{ ref('dcg_condition') }} src
    where coalesce(src.verification_status, 'confirmed') not in ('refuted', 'entered-in-error')
),

coded as (
    select c.condition_id, vs.value_set, 'snomed' as code_source, c.snomed_code as source_code,
           vs.map_relation, vs.map_status, vs.map_version
    from cond c
    join vs on vs.code_system = 'http://snomed.info/sct' and vs.code = c.snomed_code
    union all
    select c.condition_id, vs.value_set, 'icd10ca' as code_source, c.icd10ca_code as source_code,
           vs.map_relation, vs.map_status, vs.map_version
    from cond c
    join vs on vs.code_system = 'https://fhir.infoway-inforoute.ca/CodeSystem/icd10ca'
           and replace(c.icd10ca_code, '.', '') like replace(vs.code, '.', '') || '%'      -- prefix match
),

enc as (
    select encounter_id,
           case when lower(encounter_class) in ('imp', 'acute', 'nonac', 'inpatient', 'prenc') then 'inpatient'
                when lower(encounter_class) in ('emer', 'emergency')                         then 'emergency'
                else 'ambulatory' end as encounter_setting
    from {{ ref('dcg_encounter') }}
)

select distinct
    c.condition_id, c.patient_id, c.encounter_id, c.condition_category, c.clinical_status,
    c.condition_date, c.onset_datetime, c.snomed_code, c.icd10ca_code,
    x.value_set, x.code_source, x.source_code, x.map_relation, x.map_status, x.map_version,
    coalesce(e.encounter_setting, case when c.encounter_id is null then 'none' else 'ambulatory' end) as encounter_setting
from cond c
join coded x on x.condition_id = c.condition_id
left join enc e on e.encounter_id = c.encounter_id
