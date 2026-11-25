-- Thin pass-through over the SQL-on-FHIR view of the same name (see views/dcg_encounter.json)
select * from {{ source('fhir_views', 'dcg_encounter') }}
