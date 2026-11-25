// ─── Rule sets ───────────────────────────────────────────────────────────────

// Every record must reference the patient so SQL-on-FHIR getReferenceKey(Patient) resolves.
RuleSet: DCGSubjectRequired
* subject 1..1 MS
* subject only Reference($CACorePatient or DCGPatient)

// Common rules for the quantitative lab results the marts read.
RuleSet: DCGQuantitativeLab
* status MS
* category MS
* effective[x] 1..1 MS
* effective[x] only dateTime or Period
* value[x] MS
* value[x] only Quantity
* valueQuantity.value MS
* valueQuantity.system 1..1 MS
* valueQuantity.system = $UCUM
* valueQuantity.code 1..1 MS
* obeys dcg-not-future
* insert DCGSubjectRequired

// ─── Invariants (mirror the SHACL shapes in the ontology package) ────────────

Invariant: dcg-not-future
Description: "Clinically relevant time must not be in the future (dcg:TemporalInconsistency)."
Expression: "effective.ofType(dateTime).empty() or effective.ofType(dateTime) <= now()"
Severity: #warning

Invariant: dcg-a1c-unit
Description: "HbA1c must be reported in percent (UCUM '%') or IFCC mmol/mol; the pipeline converts mmol/mol to % (dcg:UnitNonConformance, dcg:UnitConversion)."
Expression: "value.ofType(Quantity).code = '%' or value.ofType(Quantity).code = 'mmol/mol'"
Severity: #error

Invariant: dcg-a1c-range
Description: "HbA1c value should be between 3 and 20 % or 9 and 195 mmol/mol (dcg:ImplausibleValue)."
Expression: "value.ofType(Quantity).value.empty() or (value.ofType(Quantity).code = '%' and value.ofType(Quantity).value >= 3 and value.ofType(Quantity).value <= 20) or (value.ofType(Quantity).code = 'mmol/mol' and value.ofType(Quantity).value >= 9 and value.ofType(Quantity).value <= 195)"
Severity: #warning

Invariant: dcg-bp-order
Description: "Diastolic must be lower than systolic (dcg:ImplausibleValue)."
Expression: "component.where(code.coding.exists(system='http://loinc.org' and code='8462-4')).value.ofType(Quantity).value < component.where(code.coding.exists(system='http://loinc.org' and code='8480-6')).value.ofType(Quantity).value"
Severity: #error

Invariant: dcg-onset-or-recorded
Description: "A diabetes Condition needs onset[x] or recordedDate so cohort entry can be dated (dcg:MissingValue)."
Expression: "onset.exists() or recordedDate.exists()"
Severity: #error

Invariant: dcg-performed
Description: "A completed procedure needs performed[x] so it can be placed in a lookback window."
Expression: "status != 'completed' or performed.exists()"
Severity: #error

Invariant: dcg-bmi-range
Description: "BMI should be between 10 and 80 kg/m2 (dcg:ImplausibleValue)."
Expression: "value.ofType(Quantity).value.empty() or (value.ofType(Quantity).value >= 10 and value.ofType(Quantity).value <= 80)"
Severity: #warning

Invariant: dcg-condition-coded
Description: "A condition needs a SNOMED CT or an ICD-10-CA coding so the pipeline can map it (dcg:UnmappedCode)."
Expression: "code.coding.where(system = 'http://snomed.info/sct' or system = 'https://fhir.infoway-inforoute.ca/CodeSystem/icd10ca').exists()"
Severity: #error

Invariant: dcg-handed-over
Description: "A completed dispense needs whenHandedOver so it can be placed in a lookback window."
Expression: "status != 'completed' or whenHandedOver.exists()"
Severity: #error

// SNOMED CT and ICD-10-CA codings side by side (hospital and claims sources send ICD-10-CA only)
RuleSet: DCGConditionCoding(snomedVS, icdVS)
* code 1..1 MS
* code.coding 1..* MS
* code.coding ^slicing.discriminator.type = #value
* code.coding ^slicing.discriminator.path = "system"
* code.coding ^slicing.rules = #open
* code.coding contains snomed 0..1 MS and icd10ca 0..1 MS
* code.coding[snomed].system = $SCT
* code.coding[snomed] from {snomedVS} (required)
* code.coding[icd10ca].system = $ICD10CA
* code.coding[icd10ca] from {icdVS} (required)
* code.coding[icd10ca] ^short = "ICD-10-CA code (any code under the listed categories)"
* obeys dcg-condition-coded
* category MS
* encounter MS
* encounter ^short = "Encounter whose class (inpatient | emergency | ambulatory) drives the DM-ADULT-CASE hospital and ambulatory routes"
