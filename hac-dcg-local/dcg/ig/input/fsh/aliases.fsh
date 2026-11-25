// ─── Code systems ────────────────────────────────────────────────────────────
Alias: $SCT        = http://snomed.info/sct
Alias: $LOINC      = http://loinc.org
Alias: $UCUM       = http://unitsofmeasure.org
Alias: $ATC        = http://www.whocc.no/atc
Alias: $RXNORM     = http://www.nlm.nih.gov/research/umls/rxnorm
Alias: $ICD10CA    = https://fhir.infoway-inforoute.ca/CodeSystem/icd10ca   // verify the canonical URI with Infoway
Alias: $BCP47      = urn:ietf:bcp:47
Alias: $ObsCat     = http://terminology.hl7.org/CodeSystem/observation-category
Alias: $CondClin   = http://terminology.hl7.org/CodeSystem/condition-clinical
Alias: $CondVer    = http://terminology.hl7.org/CodeSystem/condition-ver-status
Alias: $CondCat    = http://terminology.hl7.org/CodeSystem/condition-category
Alias: $ActReason  = http://terminology.hl7.org/CodeSystem/v3-ActReason
Alias: $ActCode    = http://terminology.hl7.org/CodeSystem/v3-ActCode

// ─── CA Core+ 1.2.1-dft parent profiles ──────────────────────────────────────
Alias: $CACorePatient           = http://fhir.infoway-inforoute.ca/cacore/StructureDefinition/patient-ca-core
Alias: $CACoreEncounter         = http://fhir.infoway-inforoute.ca/cacore/StructureDefinition/encounter-ca-core
Alias: $CACoreCondition         = http://fhir.infoway-inforoute.ca/cacore/StructureDefinition/condition-ca-core
Alias: $CACoreObservation       = http://fhir.infoway-inforoute.ca/cacore/StructureDefinition/observation-ca-core
Alias: $CACoreLabObservation    = http://fhir.infoway-inforoute.ca/cacore/StructureDefinition/observation-laboratory-Pathology-ca-core
Alias: $CACoreMedicationRequest = http://fhir.infoway-inforoute.ca/cacore/StructureDefinition/medicationrequest-ca-core
Alias: $CACoreProcedure         = http://fhir.infoway-inforoute.ca/cacore/StructureDefinition/procedure-ca-core

// ─── Bulk Data ───────────────────────────────────────────────────────────────
Alias: $GroupExport   = http://hl7.org/fhir/uv/bulkdata/OperationDefinition/group-export
Alias: $PatientExport = http://hl7.org/fhir/uv/bulkdata/OperationDefinition/patient-export
