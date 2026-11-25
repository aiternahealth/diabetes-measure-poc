// ═════════════════════════════════════════════════════════════════════════════
//  Terminology — value sets mirror the SKOS value sets in dcg-ontology.ttl
//  (seed_code_valueset.csv). STARTER content: verify against the Canadian
//  Terminology Server (SNOMED CT CA edition, pCLOCD) before production use.
// ═════════════════════════════════════════════════════════════════════════════

ValueSet: DCGDiabetesMellitusVS
Id: dcg-diabetes-mellitus
Title: "DCG Diabetes Mellitus (cohort-qualifying)"
Description: "Diagnoses that qualify a person for the diabetes care-gap cohort: Type 1, Type 2, or type unspecified. Ontology: dcg:vs_DiabetesMellitus."
* ^experimental = false
* $SCT#46635009 "Diabetes mellitus type 1"
* $SCT#44054006 "Diabetes mellitus type 2"
* $SCT#73211009 "Diabetes mellitus"
* $SCT#8801005 "Secondary diabetes mellitus"

ValueSet: DCGExcludedDysglycemiaVS
Id: dcg-excluded-dysglycemia
Title: "DCG Excluded Dysglycemia"
Description: "Gestational diabetes and prediabetes. Documented so providers know these are excluded from the cohort; they may be sent as ordinary CA Core+ Conditions. Ontology: dcg:vs_GDM, dcg:vs_Prediabetes."
* ^experimental = false
* $SCT#11687002 "Gestational diabetes mellitus"
* $SCT#15777000 "Prediabetes"
* $SCT#714628002 "Prediabetes"
* include codes from system $ICD10CA where concept is-a #O24.4

ValueSet: DCGDiabetesComplicationVS
Id: dcg-diabetes-complication
Title: "DCG Diabetes Complications"
Description: "Retinopathy, kidney disease, neuropathy and foot ulcer due to diabetes. Ontology: dcg:vs_Retinopathy, vs_KidneyDisease, vs_Neuropathy, vs_FootUlcer."
* ^experimental = false
* $SCT#4855003 "Retinopathy due to diabetes mellitus"
* $SCT#422034002 "Retinopathy due to type 2 diabetes mellitus"
* $SCT#127013003 "Disorder of kidney due to diabetes mellitus"
* $SCT#90781000119102 "Microalbuminuria due to type 2 diabetes mellitus"
* $SCT#368581000119106 "Neuropathy due to type 2 diabetes mellitus"
* $SCT#371087003 "Ulcer of foot due to diabetes mellitus"
* $SCT#230572002 "Diabetic neuropathy"
* $SCT#420422005 "Ketoacidosis due to diabetes mellitus"
* $SCT#302866003 "Hypoglycemia"

ValueSet: DCGHbA1cVS
Id: dcg-hba1c
Title: "DCG HbA1c Tests"
Description: "LOINC codes for HbA1c in percent or IFCC mmol/mol (converted to %). Ontology: dcg:vs_HbA1c."
* ^experimental = false
* $LOINC#4548-4 "Hemoglobin A1c/Hemoglobin.total in Blood"
* $LOINC#17856-6 "Hemoglobin A1c/Hemoglobin.total in Blood by HPLC"
* $LOINC#41995-2 "Hemoglobin A1c [Mass/volume] in Blood"
* $LOINC#59261-8 "Hemoglobin A1c/Hemoglobin.total in Blood by IFCC protocol"

ValueSet: DCGeGFRVS
Id: dcg-egfr
Title: "DCG eGFR Tests"
Description: "LOINC codes for estimated GFR. Ontology: dcg:vs_eGFR."
* ^experimental = false
* $LOINC#33914-3 "Glomerular filtration rate/1.73 sq M.predicted [Volume Rate/Area] in Serum or Plasma by Creatinine-based formula (MDRD)"
* $LOINC#62238-1 "Glomerular filtration rate/1.73 sq M.predicted [Volume Rate/Area] in Serum, Plasma or Blood by Creatinine-based formula (CKD-EPI)"
* $LOINC#98979-8 "Glomerular filtration rate/1.73 sq M.predicted [Volume Rate/Area] in Serum, Plasma or Blood by Creatinine-based formula (CKD-EPI 2021)"

ValueSet: DCGUrineACRVS
Id: dcg-urine-acr
Title: "DCG Urine Albumin/Creatinine Ratio Tests"
Description: "LOINC codes for urine albumin (microalbumin) to creatinine ratio. Ontology: dcg:vs_UACR."
* ^experimental = false
* $LOINC#9318-7 "Albumin/Creatinine [Mass Ratio] in Urine"
* $LOINC#14959-1 "Microalbumin/Creatinine [Mass Ratio] in Urine"
* $LOINC#32294-1 "Albumin/Creatinine [Ratio] in Urine"

ValueSet: DCGLDLVS
Id: dcg-ldl
Title: "DCG LDL Cholesterol Tests"
Description: "LOINC codes for LDL cholesterol. Ontology: dcg:vs_LDL."
* ^experimental = false
* $LOINC#18262-6 "Cholesterol in LDL [Mass/volume] in Serum or Plasma by Direct assay"
* $LOINC#13457-7 "Cholesterol in LDL [Mass/volume] in Serum or Plasma by calculation"
* $LOINC#22748-8 "Cholesterol in LDL [Moles/volume] in Serum or Plasma"
* $LOINC#2089-1 "Cholesterol in LDL [Mass/volume] in Serum or Plasma"

ValueSet: DCGBMIVS
Id: dcg-bmi
Title: "DCG Body Mass Index"
Description: "LOINC code for body mass index. Ontology: dcg:vs_BMI."
* ^experimental = false
* $LOINC#39156-5 "Body mass index (BMI) [Ratio]"

ValueSet: DCGGlucoseVS
Id: dcg-glucose
Title: "DCG Plasma Glucose Tests"
Description: "LOINC codes for blood/plasma glucose. Ontology: dcg:vs_Glucose."
* ^experimental = false
* $LOINC#2339-0 "Glucose [Mass/volume] in Blood"
* $LOINC#1558-6 "Fasting glucose [Mass/volume] in Serum or Plasma"
* $LOINC#14771-0 "Fasting glucose [Moles/volume] in Serum or Plasma"
* $LOINC#14749-6 "Glucose [Moles/volume] in Serum or Plasma"
* $LOINC#15074-8 "Glucose [Moles/volume] in Blood"
* $LOINC#2345-7 "Glucose [Mass/volume] in Serum or Plasma"

ValueSet: DCGDiabetesScreeningProcedureVS
Id: dcg-diabetes-screening-procedure
Title: "DCG Diabetes Screening Procedures"
Description: "Retinopathy screening and diabetic foot examination. Ontology: dcg:vs_EyeExam, dcg:vs_FootExam. 722161008 and 314971001 are the codes Synthea emits; 36228007 is kept for real-world sources."
* ^experimental = false
* $SCT#722161008 "Diabetic retinal eye exam"
* $SCT#314971001 "Camera fundoscopy"
* $SCT#36228007 "Ophthalmic examination and evaluation"
* $SCT#401191002 "Diabetic foot examination"

ValueSet: DCGTherapyATCVS
Id: dcg-therapy-atc
Title: "DCG Therapy Classes (ATC)"
Description: "ATC classes the pipeline reports on: antihyperglycemics, statins and ACE inhibitors/ARBs. Ontology: dcg:vs_ATC_A10, vs_ATC_C10AA, vs_ATC_C09. Includes class and ingredient levels."
* ^experimental = false
* $ATC#A10A "Insulins and analogues"
* $ATC#A10BA02 "metformin"
* $ATC#A10BB "Sulfonylureas"
* $ATC#A10BH "Dipeptidyl peptidase 4 (DPP-4) inhibitors"
* $ATC#A10BJ "Glucagon-like peptide-1 (GLP-1) analogues"
* $ATC#A10BK "Sodium-glucose co-transporter 2 (SGLT2) inhibitors"
* $ATC#A10BD "Combinations of oral blood glucose lowering drugs"
* $ATC#A10BF "Alpha glucosidase inhibitors"
* $ATC#A10BG "Thiazolidinediones"
* $ATC#A10BX "Other blood glucose lowering drugs, excl. insulins"
* $ATC#C10AA "HMG CoA reductase inhibitors"
* $ATC#C09A "ACE inhibitors, plain"
* $ATC#C09C "Angiotensin II receptor blockers (ARBs), plain"

ValueSet: DCGFinalResultStatusVS
Id: dcg-final-result-status
Title: "DCG Usable Result Status"
Description: "Observation statuses the pipeline counts. Providers may send any status; the SQL-on-FHIR views keep only these."
* ^experimental = false
* http://hl7.org/fhir/observation-status#final
* http://hl7.org/fhir/observation-status#amended
* http://hl7.org/fhir/observation-status#corrected

// ─── v0.4: ICD-10-CA (hospital and claims sources) and cardio-renal comorbidity ──
ValueSet: DCGDiabetesMellitusICDVS
Id: dcg-diabetes-mellitus-icd10ca
Title: "DCG Diabetes Mellitus (ICD-10-CA)"
Description: "ICD-10-CA categories that qualify as diabetes evidence, including all child codes: E10 type 1, E11 type 2, E13 other specified, E14 unspecified. Ontology: dcg:vs_DiabetesMellitus (ICD-10-CA rows)."
* ^experimental = false
* include codes from system $ICD10CA where concept is-a #E10
* include codes from system $ICD10CA where concept is-a #E11
* include codes from system $ICD10CA where concept is-a #E13
* include codes from system $ICD10CA where concept is-a #E14

ValueSet: DCGDiabetesComplicationICDVS
Id: dcg-diabetes-complication-icd10ca
Title: "DCG Diabetes Complications (ICD-10-CA)"
Description: "ICD-10-CA codes for diabetes complications and acute events, with children. Ophthalmic complications (E1x.3) are a broader match for retinopathy. Ontology: dcg:vs_Retinopathy, vs_KidneyDisease, vs_Neuropathy, vs_DKA, vs_Hypoglycemia (ICD-10-CA rows)."
* ^experimental = false
* include codes from system $ICD10CA where concept is-a #E10.1
* include codes from system $ICD10CA where concept is-a #E11.1
* include codes from system $ICD10CA where concept is-a #E10.2
* include codes from system $ICD10CA where concept is-a #E11.2
* include codes from system $ICD10CA where concept is-a #E10.3
* include codes from system $ICD10CA where concept is-a #E11.3
* include codes from system $ICD10CA where concept is-a #E10.4
* include codes from system $ICD10CA where concept is-a #E11.4
* include codes from system $ICD10CA where concept is-a #E16.0
* include codes from system $ICD10CA where concept is-a #E16.1
* include codes from system $ICD10CA where concept is-a #E16.2

ValueSet: DCGComorbidityVS
Id: dcg-cardiorenal-comorbidity
Title: "DCG Cardio-renal Comorbidities"
Description: "Chronic kidney disease and atherosclerotic cardiovascular disease. Ontology: dcg:vs_CKD, dcg:vs_ASCVD."
* ^experimental = false
* $SCT#709044004 "Chronic kidney disease"
* $SCT#46177005 "End-stage renal disease"
* $SCT#53741008 "Coronary arteriosclerosis"
* $SCT#22298006 "Myocardial infarction"
* $SCT#399211009 "History of myocardial infarction"
* $SCT#230690007 "Cerebrovascular accident"
* $SCT#414545008 "Ischemic heart disease"
* $SCT#400047006 "Peripheral vascular disease"

ValueSet: DCGComorbidityICDVS
Id: dcg-cardiorenal-comorbidity-icd10ca
Title: "DCG Cardio-renal Comorbidities (ICD-10-CA)"
Description: "ICD-10-CA categories for CKD (N18) and ASCVD (I20, I21, I25, I63, I70), with children. Ontology: dcg:vs_CKD, dcg:vs_ASCVD (ICD-10-CA rows)."
* ^experimental = false
* include codes from system $ICD10CA where concept is-a #N18
* include codes from system $ICD10CA where concept is-a #I20
* include codes from system $ICD10CA where concept is-a #I21
* include codes from system $ICD10CA where concept is-a #I25
* include codes from system $ICD10CA where concept is-a #I63
* include codes from system $ICD10CA where concept is-a #I70
