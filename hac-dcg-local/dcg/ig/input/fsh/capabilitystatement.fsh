// ═════════════════════════════════════════════════════════════════════════════
//  Export contract: what a data provider's FHIR server must offer so the PoC
//  can pull a cohort with FHIR Bulk Data (Group-level $export).
// ═════════════════════════════════════════════════════════════════════════════

Instance: dcg-data-provider
InstanceOf: CapabilityStatement
Usage: #definition
Title: "DCG Data Provider"
Description: "Requirements for a FHIR R4 server that supplies data to the diabetes care-gap pipeline through FHIR Bulk Data Group-level $export (Bulk Data Access IG v2)."
* name = "DCGDataProvider"
* status = #draft
* experimental = false
* date = "2026-11-25"
* kind = #requirements
* fhirVersion = #4.0.1
* format[0] = #json
* format[1] = #application/fhir+ndjson
* implementationGuide = "http://fhir.hac-poc.example/dcg/ImplementationGuide/hac.dcg.datainput"
* rest[0].mode = #server
* rest[0].documentation = "SHALL support Group-level $export with _type and _since. SHOULD support _typeFilter so the export can be limited to the codes in this IG's value sets. Authorization per SMART Backend Services is RECOMMENDED; synthetic-data deployments may run without it."
* rest[0].operation[0].name = "export"
* rest[0].operation[0].definition = $GroupExport
* rest[0].operation[0].extension[0].url = "http://hl7.org/fhir/StructureDefinition/capabilitystatement-expectation"
* rest[0].operation[0].extension[0].valueCode = #SHALL
* rest[0].operation[0].documentation = "Example: GET [base]/Group/[id]/$export?_type=Patient,Condition,Observation,MedicationRequest,MedicationDispense,Procedure,Encounter"

* insert ProviderResource(0, #Patient, http://fhir.hac-poc.example/dcg/StructureDefinition/dcg-patient, #SHALL)
* insert ProviderResource(1, #Condition, http://fhir.hac-poc.example/dcg/StructureDefinition/dcg-diabetes-condition, #SHALL)
* rest[0].resource[1].supportedProfile[1] = "http://fhir.hac-poc.example/dcg/StructureDefinition/dcg-complication-condition"
* rest[0].resource[1].supportedProfile[2] = "http://fhir.hac-poc.example/dcg/StructureDefinition/dcg-comorbidity-condition"
* insert ProviderResource(2, #Observation, http://fhir.hac-poc.example/dcg/StructureDefinition/dcg-hba1c, #SHALL)
* rest[0].resource[2].supportedProfile[1] = "http://fhir.hac-poc.example/dcg/StructureDefinition/dcg-egfr"
* rest[0].resource[2].supportedProfile[2] = "http://fhir.hac-poc.example/dcg/StructureDefinition/dcg-urine-acr"
* rest[0].resource[2].supportedProfile[3] = "http://fhir.hac-poc.example/dcg/StructureDefinition/dcg-ldl"
* rest[0].resource[2].supportedProfile[4] = "http://fhir.hac-poc.example/dcg/StructureDefinition/dcg-blood-pressure"
* rest[0].resource[2].supportedProfile[5] = "http://fhir.hac-poc.example/dcg/StructureDefinition/dcg-glucose"
* rest[0].resource[2].supportedProfile[6] = "http://fhir.hac-poc.example/dcg/StructureDefinition/dcg-bmi"
* insert ProviderResource(3, #MedicationRequest, http://fhir.hac-poc.example/dcg/StructureDefinition/dcg-medication-request, #SHALL)
* insert ProviderResource(4, #Procedure, http://fhir.hac-poc.example/dcg/StructureDefinition/dcg-diabetes-procedure, #SHOULD)
* insert ProviderResource(5, #Encounter, http://fhir.hac-poc.example/dcg/StructureDefinition/dcg-encounter, #SHOULD)
* rest[0].resource[5].documentation = "Encounters referenced by diabetes, acute-event and comorbidity Conditions: their class drives the hospital and ambulatory routes of DM-ADULT-CASE and the acute-admission measure."
* insert ProviderResource(6, #MedicationDispense, http://fhir.hac-poc.example/dcg/StructureDefinition/dcg-medication-dispense, #SHOULD)

RuleSet: ProviderResource(idx, type, profile, expectation)
* rest[0].resource[{idx}].type = {type}
* rest[0].resource[{idx}].supportedProfile[0] = "{profile}"
* rest[0].resource[{idx}].extension[0].url = "http://hl7.org/fhir/StructureDefinition/capabilitystatement-expectation"
* rest[0].resource[{idx}].extension[0].valueCode = {expectation}
