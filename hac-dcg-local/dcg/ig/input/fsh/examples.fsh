// ═════════════════════════════════════════════════════════════════════════════
//  Examples — two SYNTHETIC people (meta.security HTEST), matching patients P1
//  and P2 in the pipeline test fixtures (period end 2026-09-30):
//    P1  Type 2, age 60, all care up to date      → 0 open gaps
//    P2  Type 2, age 70, A1C 8.5 %, BP 140/85     → 8 open gaps, retinopathy
// ═════════════════════════════════════════════════════════════════════════════

RuleSet: SyntheticTag
* meta.security = $ActReason#HTEST "test health data"

// ─── P1 ──────────────────────────────────────────────────────────────────────
Instance: dcg-ex-patient-p1
InstanceOf: DCGPatient
Title: "P1 — synthetic patient, Type 2, care up to date"
Usage: #example
* insert SyntheticTag
* identifier.system = "https://fhir.hac-poc.example/synthetic-id"
* identifier.value = "P1"
* name.family = "Synthetic"
* name.given = "Ava"
* gender = #female
* birthDate = "1966-05-01"
* address.use = #home
* address.city = "Ottawa"
* address.state = "ON"
* address.postalCode = "K1A 0A1"
* address.country = "CA"

Instance: dcg-ex-condition-p1-t2dm
InstanceOf: DCGDiabetesCondition
Title: "P1 — Type 2 diabetes"
Usage: #example
* insert SyntheticTag
* clinicalStatus = $CondClin#active
* verificationStatus = $CondVer#confirmed
* category = $CondCat#problem-list-item
* code = $SCT#44054006 "Diabetes mellitus type 2"
* subject = Reference(dcg-ex-patient-p1)
* onsetDateTime = "2015-01-01"
* recordedDate = "2015-01-01"

Instance: dcg-ex-hba1c-p1
InstanceOf: DCGHbA1c
Title: "P1 — HbA1c 6.8 % (at target)"
Usage: #example
* insert SyntheticTag
* status = #final
* category = $ObsCat#laboratory
* code = $LOINC#4548-4 "Hemoglobin A1c/Hemoglobin.total in Blood"
* subject = Reference(dcg-ex-patient-p1)
* effectiveDateTime = "2026-07-01"
* valueQuantity = 6.8 '%' "%"

Instance: dcg-ex-egfr-p1
InstanceOf: DCGeGFR
Title: "P1 — eGFR 85"
Usage: #example
* insert SyntheticTag
* status = #final
* category = $ObsCat#laboratory
* code = $LOINC#33914-3
* subject = Reference(dcg-ex-patient-p1)
* effectiveDateTime = "2026-03-01"
* valueQuantity = 85 'mL/min/{1.73_m2}' "mL/min/1.73m2"

Instance: dcg-ex-uacr-p1
InstanceOf: DCGUrineACR
Title: "P1 — urine ACR 1.2 mg/mmol"
Usage: #example
* insert SyntheticTag
* status = #final
* category = $ObsCat#laboratory
* code = $LOINC#14959-1
* subject = Reference(dcg-ex-patient-p1)
* effectiveDateTime = "2026-03-01"
* valueQuantity = 1.2 'mg/mmol' "mg/mmol"

Instance: dcg-ex-ldl-p1
InstanceOf: DCGLDL
Title: "P1 — LDL-C 2.1 mmol/L"
Usage: #example
* insert SyntheticTag
* status = #final
* category = $ObsCat#laboratory
* code = $LOINC#18262-6
* subject = Reference(dcg-ex-patient-p1)
* effectiveDateTime = "2026-03-01"
* valueQuantity = 2.1 'mmol/L' "mmol/L"

Instance: dcg-ex-bp-p1
InstanceOf: DCGBloodPressure
Title: "P1 — BP 120/75 (at target)"
Usage: #example
* insert SyntheticTag
* status = #final
* category[VSCat] = $ObsCat#vital-signs
* subject = Reference(dcg-ex-patient-p1)
* effectiveDateTime = "2026-08-01"
* component[systolic].valueQuantity.value = 120
* component[diastolic].valueQuantity.value = 75

Instance: dcg-ex-bmi-p1
InstanceOf: DCGBMI
Title: "P1 — BMI 27.4"
Usage: #example
* insert SyntheticTag
* status = #final
* category[VSCat] = $ObsCat#vital-signs
* subject = Reference(dcg-ex-patient-p1)
* effectiveDateTime = "2026-08-01"
* valueQuantity.value = 27.4

Instance: dcg-ex-metformin-p1
InstanceOf: DCGMedicationRequest
Title: "P1 — metformin order"
Usage: #example
* insert SyntheticTag
* status = #active
* intent = #order
* medicationCodeableConcept.coding[0] = $RXNORM#860975 "24 HR metformin hydrochloride 500 MG Extended Release Oral Tablet"
* medicationCodeableConcept.coding[atc] = $ATC#A10BA02 "metformin"
* medicationCodeableConcept.text = "metformin 500 mg ER tablet"
* subject = Reference(dcg-ex-patient-p1)
* authoredOn = "2026-01-01"

Instance: dcg-ex-statin-p1
InstanceOf: DCGMedicationRequest
Title: "P1 — atorvastatin order"
Usage: #example
* insert SyntheticTag
* status = #active
* intent = #order
* medicationCodeableConcept.coding[atc] = $ATC#C10AA "HMG CoA reductase inhibitors"
* medicationCodeableConcept.text = "atorvastatin 20 mg tablet"
* subject = Reference(dcg-ex-patient-p1)
* authoredOn = "2026-01-01"

Instance: dcg-ex-eye-exam-p1
InstanceOf: DCGDiabetesProcedure
Title: "P1 — eye exam"
Usage: #example
* insert SyntheticTag
* status = #completed
* code = $SCT#36228007 "Ophthalmic examination and evaluation"
* subject = Reference(dcg-ex-patient-p1)
* performedDateTime = "2025-06-01"

Instance: dcg-ex-foot-exam-p1
InstanceOf: DCGDiabetesProcedure
Title: "P1 — foot exam"
Usage: #example
* insert SyntheticTag
* status = #completed
* code = $SCT#401191002 "Diabetic foot examination"
* subject = Reference(dcg-ex-patient-p1)
* performedDateTime = "2026-01-10"

Instance: dcg-ex-encounter-p1
InstanceOf: DCGEncounter
Title: "P1 — ambulatory visit"
Usage: #example
* insert SyntheticTag
* status = #finished
* class = $ActCode#AMB "ambulatory"
* subject = Reference(dcg-ex-patient-p1)
* period.start = "2026-07-01T09:00:00-04:00"
* period.end = "2026-07-01T09:20:00-04:00"
* reasonCode = $SCT#44054006 "Diabetes mellitus type 2"

// ─── P2 ──────────────────────────────────────────────────────────────────────
Instance: dcg-ex-patient-p2
InstanceOf: DCGPatient
Title: "P2 — synthetic patient, Type 2, multiple gaps"
Usage: #example
* insert SyntheticTag
* identifier.system = "https://fhir.hac-poc.example/synthetic-id"
* identifier.value = "P2"
* name.family = "Synthetic"
* name.given = "Ben"
* gender = #male
* birthDate = "1956-02-01"
* address.use = #home
* address.city = "Toronto"
* address.state = "ON"
* address.postalCode = "M5V 2T6"
* address.country = "CA"

Instance: dcg-ex-condition-p2-t2dm
InstanceOf: DCGDiabetesCondition
Title: "P2 — Type 2 diabetes"
Usage: #example
* insert SyntheticTag
* clinicalStatus = $CondClin#active
* verificationStatus = $CondVer#confirmed
* category = $CondCat#problem-list-item
* code = $SCT#44054006 "Diabetes mellitus type 2"
* subject = Reference(dcg-ex-patient-p2)
* onsetDateTime = "2010-01-01"

Instance: dcg-ex-condition-p2-retinopathy
InstanceOf: DCGComplicationCondition
Title: "P2 — diabetic retinopathy"
Usage: #example
* insert SyntheticTag
* clinicalStatus = $CondClin#active
* verificationStatus = $CondVer#confirmed
* category = $CondCat#problem-list-item
* code = $SCT#422034002 "Retinopathy due to type 2 diabetes mellitus"
* subject = Reference(dcg-ex-patient-p2)
* onsetDateTime = "2024-01-01"

Instance: dcg-ex-hba1c-p2
InstanceOf: DCGHbA1c
Title: "P2 — HbA1c 8.5 % (above target, not recent)"
Usage: #example
* insert SyntheticTag
* status = #final
* category = $ObsCat#laboratory
* code = $LOINC#4548-4 "Hemoglobin A1c/Hemoglobin.total in Blood"
* subject = Reference(dcg-ex-patient-p2)
* effectiveDateTime = "2026-01-15"
* valueQuantity = 8.5 '%' "%"

Instance: dcg-ex-glucose-p2
InstanceOf: DCGGlucose
Title: "P2 — fasting glucose 9.1 mmol/L"
Usage: #example
* insert SyntheticTag
* status = #final
* category = $ObsCat#laboratory
* code = $LOINC#1558-6
* subject = Reference(dcg-ex-patient-p2)
* effectiveDateTime = "2026-01-15"
* valueQuantity = 9.1 'mmol/L' "mmol/L"

Instance: dcg-ex-bp-p2
InstanceOf: DCGBloodPressure
Title: "P2 — BP 140/85 (above target)"
Usage: #example
* insert SyntheticTag
* status = #final
* category[VSCat] = $ObsCat#vital-signs
* subject = Reference(dcg-ex-patient-p2)
* effectiveDateTime = "2026-08-01"
* component[systolic].valueQuantity.value = 140
* component[diastolic].valueQuantity.value = 85

// ─── Bulk export cohort ──────────────────────────────────────────────────────
Instance: dcg-ex-cohort-group
InstanceOf: Group
Title: "Synthetic diabetes cohort for Group-level $export"
Usage: #example
* insert SyntheticTag
* type = #person
* actual = true
* name = "HAC DCG synthetic cohort"
* quantity = 3
* member[0].entity = Reference(dcg-ex-patient-p1)
* member[1].entity = Reference(dcg-ex-patient-p2)
* member[2].entity = Reference(dcg-ex-patient-p9)

// ─── P9 (v0.4): hospital ICD-10-CA diagnosis only; dispense; P2 comorbidity ───
Instance: dcg-ex-patient-p9
InstanceOf: DCGPatient
Title: "P9 — synthetic patient, hospital-coded type 2 diabetes"
Usage: #example
* insert SyntheticTag
* identifier.system = "http://fhir.hac-poc.example/dcg/sid/synthetic-mrn"
* identifier.value = "SYN-0009"
* gender = #male
* birthDate = "1960-01-01"
* address.use = #home
* address.state = "AB"
* address.postalCode = "T2P 1J9"
* address.country = "CA"
* communication.language = $BCP47#en-CA "English (Canada)"
* communication.preferred = true

Instance: dcg-ex-encounter-p9-inpatient
InstanceOf: DCGEncounter
Title: "P9 — inpatient stay"
Usage: #example
* insert SyntheticTag
* status = #finished
* class = $ActCode#IMP "inpatient encounter"
* subject = Reference(dcg-ex-patient-p9)
* period.start = "2024-03-08T10:00:00-07:00"
* period.end = "2024-03-12T11:00:00-07:00"

Instance: dcg-ex-condition-p9-t2dm-icd
InstanceOf: DCGDiabetesCondition
Title: "P9 — type 2 diabetes, ICD-10-CA E11.9 at a hospital stay (hospital route)"
Usage: #example
* insert SyntheticTag
* clinicalStatus = $CondClin#active
* verificationStatus = $CondVer#confirmed
* category = $CondCat#encounter-diagnosis
* code.coding[icd10ca] = $ICD10CA#E11.9 "Type 2 diabetes mellitus without complication"
* subject = Reference(dcg-ex-patient-p9)
* encounter = Reference(dcg-ex-encounter-p9-inpatient)
* onsetDateTime = "2024-03-10"

Instance: dcg-ex-dispense-p9-insulin
InstanceOf: DCGMedicationDispense
Title: "P9 — insulin dispense"
Usage: #example
* insert SyntheticTag
* status = #completed
* medicationCodeableConcept.text = "insulin glargine 100 units/mL pen"
* medicationCodeableConcept.coding[atc] = $ATC#A10A "Insulins and analogues"
* subject = Reference(dcg-ex-patient-p9)
* whenHandedOver = "2026-04-01"
* daysSupply.value = 30
* daysSupply.unit = "days"
* daysSupply.system = $UCUM
* daysSupply.code = #d

Instance: dcg-ex-condition-p2-mi
InstanceOf: DCGComorbidityCondition
Title: "P2 — myocardial infarction (ASCVD)"
Usage: #example
* insert SyntheticTag
* clinicalStatus = $CondClin#active
* verificationStatus = $CondVer#confirmed
* category = $CondCat#problem-list-item
* code.coding[snomed] = $SCT#22298006 "Myocardial infarction"
* subject = Reference(dcg-ex-patient-p2)
* onsetDateTime = "2023-01-01"
