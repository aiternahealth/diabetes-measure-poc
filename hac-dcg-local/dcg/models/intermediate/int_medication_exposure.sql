-- int_medication_exposure
-- Grain: one row per medication order or pharmacy dispense x therapy class.
-- Classified by ATC prefix (DCI 4.4) or ingredient keyword; combination products count toward each ingredient class.
-- Ontology: dcg:MedicationExposure and its therapy subclasses

with mc as (select * from {{ ref('seed_medication_class') }}),

ex as (
    select medication_request_id as exposure_id, patient_id, 'order' as exposure_type, status,
           cast(authored_on as date) as exposure_date, med_text, med_display, atc_code
    from {{ ref('dcg_medication_request') }}
    where status not in ('entered-in-error', 'cancelled', 'draft')
    union all
    select medication_dispense_id, patient_id, 'dispense' as exposure_type, status,
           cast(when_handed_over as date), med_text, med_display, atc_code
    from {{ ref('dcg_medication_dispense') }}
)

select distinct ex.*, mc.therapy_class
from ex
join mc on (mc.match_kind = 'keyword'
            and lower(coalesce(ex.med_text, '') || ' ' || coalesce(ex.med_display, '')) like '%' || mc.pattern || '%')
        or (mc.match_kind = 'atc' and ex.atc_code like mc.pattern || '%')
