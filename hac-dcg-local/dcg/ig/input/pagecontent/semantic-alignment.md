### One vocabulary, four layers

This IG is layer 0 of the DCG package. Each profile matches one ontology class and one SQL-on-FHIR view, so a change here can be traced to the metrics it affects.

| Profile | Ontology class (`dcg:`) | View | Metrics that read it |
|---|---|---|---|
| DCG Patient | Person | `dcg_patient` | All (cohort, age, sex, province) |
| DCG Diabetes Condition | DiabetesMellitus | `dcg_condition` | Cohort, diabetes_type, prevalence |
| DCG Complication Condition | DiabetesComplication | `dcg_condition` | complication_rate |
| DCG HbA1c | HbA1cResult | `dcg_observation` | a1c_tested_12m/recent, a1c_at_target, a1c_poor_control |
| DCG eGFR + DCG Urine ACR | EGFRResult, UACRResult | `dcg_observation` | kidney_screened_rate |
| DCG LDL | LDLResult | `dcg_observation` | lipid_tested_rate, all_four_tests_rate |
| DCG Glucose | GlucoseResult | `dcg_observation` | (future case finding) |
| DCG BMI | BMIResult | `dcg_observation` | bmi_recorded_rate, bmi_latest_mean_kg_m2, dimension bmi_category |
| DCG Blood Pressure | BloodPressureReading | `dcg_blood_pressure` | bp_at_target_rate, all_four_tests_rate, bp_systolic_mean_mmhg, bp_diastolic_mean_mmhg |
| DCG Medication Request | MedicationExposure (+ drug-class subclasses) | `dcg_medication_request` | statin_rate_40plus, metformin_rate, insulin_rate, sglt2i_rate, glp1ra_rate, dpp4i_rate, sulfonylurea_rate, acei_arb_rate, antihyperglycemic_rate, therapy_profile |
| DCG Diabetes Screening Procedure | RetinopathyScreening, DiabeticFootExam | `dcg_procedure` | eye_exam_rate, foot_exam_rate |
| DCG Encounter | Encounter | `dcg_encounter` | (future CCDSS-style case definition) |

The [DCG Minimum Data Set](StructureDefinition-DCGMinimumDataSet.html) logical model carries both mappings: to profile elements and to view columns.

### Value sets

The value sets in this IG are the same codes as the SKOS value sets in `dcg-ontology.ttl` (and `seed_code_valueset.csv`). When a code is added or removed, change the ontology first and regenerate both.

### Invariants and data quality

| Invariant | Severity | Ontology DQ class | DQ metric |
|---|---|---|---|
| `dcg-a1c-unit` | error | UnitNonConformance | dq_a1c_unit_rate |
| `dcg-a1c-range` | warning | ImplausibleValue | dq_a1c_implausible_rate |
| `dcg-bp-order` | error | ImplausibleValue | (record excluded) |
| `dcg-onset-or-recorded` | error | MissingValue | dq_missing_onset_rate |
| `dcg-performed` | error | MissingValue | (record excluded) |
| `dcg-not-future` | warning | TemporalInconsistency | (record excluded) |
