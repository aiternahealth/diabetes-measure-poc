-- int_observation_std
-- Grain: one row per governed lab or vital Observation, with the original value and unit kept and a
-- standardised value in one UCUM unit per test (DCI 4.3): HbA1c %, glucose mmol/L, urine ACR mg/mmol, LDL mmol/L.
-- unit_accepted = 0 means the unit is unknown and the result is set aside (dq_a1c_unit for HbA1c).
-- Ontology: dcg:ObservationResult, dcg:UnitConversion

with vs as (select * from {{ ref('seed_code_valueset') }} where code_system = 'http://loinc.org'),

obs as (
    select o.observation_id, o.patient_id, o.status, cast(o.effective_datetime as date) as eff_date,
           o.loinc_code, o.value_numeric, o.ucum_unit, vs.value_set, vs.map_version
    from {{ ref('dcg_observation') }} o
    join vs on vs.code = o.loinc_code
    where coalesce(o.status, 'final') not in ('entered-in-error', 'cancelled', 'registered', 'preliminary')
)

select
    obs.*,
    case when value_set = 'vs_HbA1c'   and ucum_unit = 'mmol/mol' then value_numeric / 10.929 + 2.15
         when value_set = 'vs_Glucose' and ucum_unit = 'mg/dL'    then value_numeric / 18.016
         when value_set = 'vs_UACR'    and ucum_unit = 'mg/g'     then value_numeric * 0.113
         when value_set = 'vs_LDL'     and ucum_unit = 'mg/dL'    then value_numeric * 0.02586
         else value_numeric end                                             as value_std,
    case value_set when 'vs_HbA1c' then '%' when 'vs_Glucose' then 'mmol/L'
                   when 'vs_UACR' then 'mg/mmol' when 'vs_LDL' then 'mmol/L' else ucum_unit end as unit_std,
    case when (value_set = 'vs_HbA1c'   and ucum_unit = 'mmol/mol')
           or (value_set = 'vs_Glucose' and ucum_unit = 'mg/dL')
           or (value_set = 'vs_UACR'    and ucum_unit = 'mg/g')
           or (value_set = 'vs_LDL'     and ucum_unit = 'mg/dL') then 1 else 0 end as unit_converted,
    case when value_set = 'vs_HbA1c'   then case when ucum_unit in ('%', 'mmol/mol') then 1 else 0 end
         when value_set = 'vs_Glucose' then case when ucum_unit in ('mmol/L', 'mg/dL') then 1 else 0 end
         when value_set = 'vs_UACR'    then case when ucum_unit in ('mg/mmol', 'mg/g') then 1 else 0 end
         when value_set = 'vs_LDL'     then case when ucum_unit in ('mmol/L', 'mg/dL') then 1 else 0 end
         else 1 end                                                         as unit_accepted
from obs
