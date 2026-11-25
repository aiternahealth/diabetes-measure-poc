// ═════════════════════════════════════════════════════════════════════════════
//  Profiles — each derives from the CA Core+ 1.2.1-dft profile for its resource
//  and adds only what the care-gap pipeline needs. MustSupport (MS) = the
//  element is read by a SQL-on-FHIR view (views/*.json in the ontology package).
//  ^extension values are not used; ontology bindings are documented in the
//  Semantic Alignment page.
// ═════════════════════════════════════════════════════════════════════════════

// ─── Patient ─────────────────────────────────────────────────────────────────
Profile: DCGPatient
Parent: $CACorePatient
Id: dcg-patient
Title: "DCG Patient"
Description: "Person whose data is in scope. Birth date, administrative gender, deceased status and home province/postal code drive cohort eligibility and the age_band, sex, province and fsa dimensions (ontology: dcg:Person)."
* meta.security MS
* meta.security ^short = "HTEST when the record is synthetic (e.g., Synthea) → data_source = synthetic"
* birthDate 1..1 MS
* gender 1..1 MS
* deceased[x] MS
* address MS
* address.use MS
* address.state MS
* address.state ^short = "Province/territory — 2-letter code (e.g., ON)"
* address.postalCode MS
* address.postalCode ^short = "Postal code; only the first 3 characters (FSA) are used, as a restricted dimension"
* communication MS
* communication.language MS
* communication.preferred MS
* communication ^short = "Preferred service language (PCHDCF Service Language): equity stratifier, restricted"
* extension contains DCGIndigenousIdentity named indigenousIdentity 0..1 MS and DCGRacializedGroup named racializedGroup 0..1 MS

// ─── Encounter ───────────────────────────────────────────────────────────────
Profile: DCGEncounter
Parent: $CACoreEncounter
Id: dcg-encounter
Title: "DCG Encounter"
Description: "Clinical contact. Not used by v0.1 indicators; carried so a CCDSS-style case definition (1 hospitalization or 2 physician visits in 2 years) can be added later (ontology: dcg:Encounter)."
* status MS
* class MS
* period MS
* period.start MS
* reasonCode MS
* insert DCGSubjectRequired

// ─── Conditions ──────────────────────────────────────────────────────────────
Profile: DCGDiabetesCondition
Parent: $CACoreCondition
Id: dcg-diabetes-condition
Title: "DCG Diabetes Condition"
Description: "Diagnosis of type 1, type 2, other specified or unspecified diabetes, coded in SNOMED CT or ICD-10-CA. Evidence for case phenotype DM-ADULT-CASE (ontology: dcg:DiabetesMellitus, dcg:pheno_DM_ADULT_CASE): a declared condition, a hospital diagnosis (linked inpatient Encounter) or ambulatory diagnoses (2 within 730 days). Gestational diabetes and prediabetes are NOT sent with this profile."
* obeys dcg-onset-or-recorded
* insert DCGConditionCoding(DCGDiabetesMellitusVS, DCGDiabetesMellitusICDVS)
* clinicalStatus MS
* verificationStatus MS
* onset[x] MS
* onset[x] only dateTime or Period or Age
* abatement[x] MS
* recordedDate MS
* insert DCGSubjectRequired

Profile: DCGComplicationCondition
Parent: $CACoreCondition
Id: dcg-complication-condition
Title: "DCG Diabetes Complication Condition"
Description: "Recorded diabetes complication: retinopathy, kidney disease, neuropathy, foot ulcer, or an acute event (ketoacidosis, hypoglycemia) (ontology: dcg:DiabetesComplication, dcg:AcuteDiabetesEvent). Drives has_any_complication and, with an inpatient or emergency Encounter, the acute-admission measure."
* insert DCGConditionCoding(DCGDiabetesComplicationVS, DCGDiabetesComplicationICDVS)
* clinicalStatus MS
* onset[x] MS
* recordedDate MS
* insert DCGSubjectRequired

// ─── Laboratory results ──────────────────────────────────────────────────────
Profile: DCGHbA1c
Parent: $CACoreLabObservation
Id: dcg-hba1c
Title: "DCG HbA1c Result"
Description: "Glycated haemoglobin result in percent or IFCC mmol/mol (ontology: dcg:HbA1cResult). The pipeline converts mmol/mol to % (value / 10.929 + 2.15). Drives A1C testing, control, poor control and the lab route of DM-ADULT-CASE."
* code 1..1 MS
* code from DCGHbA1cVS (required)
* insert DCGQuantitativeLab
* obeys dcg-a1c-unit and dcg-a1c-range

Profile: DCGeGFR
Parent: $CACoreLabObservation
Id: dcg-egfr
Title: "DCG eGFR Result"
Description: "Estimated glomerular filtration rate (ontology: dcg:EGFRResult). With urine ACR, drives kidney screening."
* code 1..1 MS
* code from DCGeGFRVS (required)
* insert DCGQuantitativeLab

Profile: DCGUrineACR
Parent: $CACoreLabObservation
Id: dcg-urine-acr
Title: "DCG Urine Albumin-to-Creatinine Ratio Result"
Description: "Urine albumin (microalbumin) to creatinine ratio (ontology: dcg:UACRResult). With eGFR, drives kidney screening."
* code 1..1 MS
* code from DCGUrineACRVS (required)
* insert DCGQuantitativeLab

Profile: DCGLDL
Parent: $CACoreLabObservation
Id: dcg-ldl
Title: "DCG LDL Cholesterol Result"
Description: "LDL cholesterol, direct or calculated (ontology: dcg:LDLResult). Drives lipid testing."
* code 1..1 MS
* code from DCGLDLVS (required)
* insert DCGQuantitativeLab

Profile: DCGGlucose
Parent: $CACoreLabObservation
Id: dcg-glucose
Title: "DCG Plasma Glucose Result"
Description: "Random or fasting plasma glucose (ontology: dcg:GlucoseResult). Optional in v0.1; carried for future lab-based case finding."
* code 1..1 MS
* code from DCGGlucoseVS (required)
* insert DCGQuantitativeLab

// ─── Blood pressure ──────────────────────────────────────────────────────────
// CA Core+ 1.2.1-dft has no vital-signs/BP profile, so this follows the R4
// vital-signs BP pattern on top of the generic CA Core+ Observation.
Profile: DCGBloodPressure
Parent: $CACoreObservation
Id: dcg-blood-pressure
Title: "DCG Blood Pressure"
Description: "Blood pressure panel with systolic and diastolic components (ontology: dcg:BloodPressureReading). Drives BP control and the all-four-tests composite. Follows the FHIR R4 vital-signs blood pressure pattern."
* obeys dcg-not-future and dcg-bp-order
* status MS
* category MS
* category ^slicing.discriminator.type = #pattern
* category ^slicing.discriminator.path = "$this"
* category ^slicing.rules = #open
* category contains VSCat 1..1 MS
* category[VSCat] = $ObsCat#vital-signs
* code 1..1 MS
* code = $LOINC#85354-9 "Blood pressure panel with all children optional"
* effective[x] 1..1 MS
* effective[x] only dateTime or Period
* value[x] 0..0
* component 2..* MS
* component ^slicing.discriminator.type = #pattern
* component ^slicing.discriminator.path = "code"
* component ^slicing.rules = #open
* component contains
    systolic 1..1 MS and
    diastolic 1..1 MS
* component[systolic].code = $LOINC#8480-6 "Systolic blood pressure"
* component[systolic].value[x] only Quantity
* component[systolic].valueQuantity 1..1 MS
* component[systolic].valueQuantity.value 1..1 MS
* component[systolic].valueQuantity = $UCUM#mm[Hg] "mmHg"
* component[diastolic].code = $LOINC#8462-4 "Diastolic blood pressure"
* component[diastolic].value[x] only Quantity
* component[diastolic].valueQuantity 1..1 MS
* component[diastolic].valueQuantity.value 1..1 MS
* component[diastolic].valueQuantity = $UCUM#mm[Hg] "mmHg"
* insert DCGSubjectRequired

// ─── Body mass index ─────────────────────────────────────────────────────────
// Context measure for the cohort profile (mean/median BMI, BMI category). Like BP, CA Core+
// 1.2.1-dft has no vital-signs profile, so this follows the R4 vital-signs BMI pattern.
Profile: DCGBMI
Parent: $CACoreObservation
Id: dcg-bmi
Title: "DCG Body Mass Index"
Description: "Body mass index in kg/m2 (ontology: dcg:BMIResult). Drives the BMI context measures and the bmi_category dimension of the cohort profile; not a care-gap target."
* obeys dcg-not-future and dcg-bmi-range
* status MS
* category MS
* category ^slicing.discriminator.type = #pattern
* category ^slicing.discriminator.path = "$this"
* category ^slicing.rules = #open
* category contains VSCat 1..1 MS
* category[VSCat] = $ObsCat#vital-signs
* code 1..1 MS
* code = $LOINC#39156-5 "Body mass index (BMI) [Ratio]"
* effective[x] 1..1 MS
* effective[x] only dateTime or Period
* value[x] 1..1 MS
* value[x] only Quantity
* valueQuantity.value 1..1 MS
* valueQuantity = $UCUM#kg/m2 "kg/m2"
* insert DCGSubjectRequired

// ─── Medications ─────────────────────────────────────────────────────────────
Profile: DCGMedicationRequest
Parent: $CACoreMedicationRequest
Id: dcg-medication-request
Title: "DCG Medication Request"
Description: "Order for an antihyperglycemic, statin or ACE inhibitor/ARB (ontology: dcg:MedicationExposure). The pipeline classifies drugs by ingredient, so the coding display or text must name the ingredient; an ATC coding is recommended."
* status MS
* intent MS
* authoredOn 1..1 MS
* medication[x] MS
* medication[x] only CodeableConcept or Reference(Medication)
* medicationCodeableConcept MS
* medicationCodeableConcept.text MS
* medicationCodeableConcept.text ^short = "Ingredient name(s) — used for drug-class classification"
* medicationCodeableConcept.coding MS
* medicationCodeableConcept.coding ^slicing.discriminator.type = #pattern
* medicationCodeableConcept.coding ^slicing.discriminator.path = "system"
* medicationCodeableConcept.coding ^slicing.rules = #open
* medicationCodeableConcept.coding contains atc 0..* MS
* medicationCodeableConcept.coding[atc].system = $ATC
* medicationCodeableConcept.coding[atc] from DCGTherapyATCVS (required)
* medicationCodeableConcept.coding[atc] ^short = "ATC class of the drug (recommended)"
* insert DCGSubjectRequired

// ─── Procedures ──────────────────────────────────────────────────────────────
Profile: DCGDiabetesProcedure
Parent: $CACoreProcedure
Id: dcg-diabetes-procedure
Title: "DCG Diabetes Screening Procedure"
Description: "Retinopathy screening (eye exam) or diabetic foot examination (ontology: dcg:RetinopathyScreening, dcg:DiabeticFootExam). Drives eye_exam and foot_exam metrics."
* obeys dcg-performed
* status MS
* code 1..1 MS
* code from DCGDiabetesScreeningProcedureVS (required)
* performed[x] MS
* performed[x] only dateTime or Period
* insert DCGSubjectRequired

// ─── v0.4: comorbidities, dispenses ──────────────────────────────────────────
Profile: DCGComorbidityCondition
Parent: $CACoreCondition
Id: dcg-comorbidity-condition
Title: "DCG Cardio-renal Comorbidity Condition"
Description: "Chronic kidney disease or atherosclerotic cardiovascular disease (ontology: dcg:ChronicKidneyDisease, dcg:AtheroscleroticCVD). Denominator of the cardio-renal agent measure (SGLT2 inhibitor or GLP-1 RA)."
* insert DCGConditionCoding(DCGComorbidityVS, DCGComorbidityICDVS)
* clinicalStatus MS
* onset[x] MS
* recordedDate MS
* obeys dcg-onset-or-recorded
* insert DCGSubjectRequired

Profile: DCGMedicationDispense
Parent: MedicationDispense
Id: dcg-medication-dispense
Title: "DCG Medication Dispense"
Description: "Pharmacy dispense of an antihyperglycemic, statin or ACE inhibitor/ARB (ontology: dcg:MedicationExposure). Counts as use alongside orders. Derived from base R4: switch the parent to a CA Core+ dispense profile when one is published. Canadian sources SHOULD send DIN or CCDD codings; an ATC coding is recommended."
* obeys dcg-handed-over
* status MS
* whenHandedOver MS
* daysSupply MS
* medication[x] MS
* medication[x] only CodeableConcept or Reference(Medication)
* medicationCodeableConcept MS
* medicationCodeableConcept.text MS
* medicationCodeableConcept.coding MS
* medicationCodeableConcept.coding ^slicing.discriminator.type = #value
* medicationCodeableConcept.coding ^slicing.discriminator.path = "system"
* medicationCodeableConcept.coding ^slicing.rules = #open
* medicationCodeableConcept.coding contains atc 0..* MS
* medicationCodeableConcept.coding[atc].system = $ATC
* medicationCodeableConcept.coding[atc] from DCGTherapyATCVS (required)
* subject 1..1 MS
* subject only Reference($CACorePatient or DCGPatient)

// ─── v0.4: equity stratifiers (PCHDCF SDOH elements) — restricted ────────────
Extension: DCGIndigenousIdentity
Id: dcg-indigenous-identity
Title: "DCG Indigenous Identity"
Description: "Self-identified Indigenous identity (PCHDCF Indigenous Identity). RESTRICTED: equity analysis only, with First Nations, Inuit and Métis data governance (e.g., OCAP). Bind to the PCHDCF / Infoway value set when published."
Context: Patient
* value[x] only CodeableConcept

Extension: DCGRacializedGroup
Id: dcg-racialized-group
Title: "DCG Racialized Group"
Description: "Self-identified racialized group (PCHDCF Racialized Group). RESTRICTED: equity analysis only. Bind to the PCHDCF / Infoway value set when published."
Context: Patient
* value[x] only CodeableConcept
