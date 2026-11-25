### What to send

A provider SHALL expose a FHIR R4 server meeting [DCG Data Provider](CapabilityStatement-dcg-data-provider.html) and SHALL support Group-level `$export` (Bulk Data Access IG v2).

```
GET [base]/Group/[cohort-id]/$export?_type=Patient,Condition,Observation,MedicationRequest,MedicationDispense,Procedure,Encounter
```

| Resource | Profile(s) | Expectation |
|---|---|---|
| Patient | [DCG Patient](StructureDefinition-dcg-patient.html) | SHALL |
| Condition | [DCG Diabetes Condition](StructureDefinition-dcg-diabetes-condition.html), [DCG Complication](StructureDefinition-dcg-complication-condition.html), [DCG Cardio-renal Comorbidity](StructureDefinition-dcg-comorbidity-condition.html) | SHALL |
| Observation | [HbA1c](StructureDefinition-dcg-hba1c.html), [eGFR](StructureDefinition-dcg-egfr.html), [Urine ACR](StructureDefinition-dcg-urine-acr.html), [LDL-C](StructureDefinition-dcg-ldl.html), [Blood Pressure](StructureDefinition-dcg-blood-pressure.html), [Glucose](StructureDefinition-dcg-glucose.html), [BMI](StructureDefinition-dcg-bmi.html) | SHALL (glucose and BMI MAY) |
| MedicationRequest | [DCG Medication Request](StructureDefinition-dcg-medication-request.html) | SHALL |
| MedicationDispense | [DCG Medication Dispense](StructureDefinition-dcg-medication-dispense.html) | SHOULD (pharmacy sources) |
| Procedure | [DCG Diabetes Screening Procedure](StructureDefinition-dcg-diabetes-procedure.html) | SHOULD |
| Encounter | [DCG Encounter](StructureDefinition-dcg-encounter.html) | SHOULD (the encounters diabetes, acute-event and comorbidity Conditions reference) |

### Lookback

Export at least **36 months** of history before the measurement period end. That is the longest window (LDL-C); eye exams need 24 months and most other indicators 12.

### Rules that most often break the numbers

1. **HbA1c in percent or mmol/mol.** Both are accepted; the pipeline converts IFCC mmol/mol to % (value / 10.929 + 2.15). Results in any other unit count as "tested" but not as "controlled" (invariant `dcg-a1c-unit`). Glucose and LDL may be in mg/dL and ACR in mg/g; they are converted too.
2. **Dates on everything.** A result, procedure or order without a date cannot be placed in a lookback window and is ignored.
3. **Name the drug ingredient.** Medications are grouped into classes by ingredient. Put it in `medicationCodeableConcept.text` or the coding display; add an ATC coding when you can.
4. **Code the diagnosis in SNOMED CT or ICD-10-CA, and link the Encounter.** Hospital and claims sources may send ICD-10-CA only (E10, E11, E13, E14 and their children). The linked Encounter class (inpatient, emergency, ambulatory) decides which route of case phenotype DM-ADULT-CASE the diagnosis supports: one hospital diagnosis, or two ambulatory diagnoses within 730 days.
5. **Use the diabetes value set for the diagnosis.** Gestational diabetes and prediabetes are excluded from the cohort ([DCG Excluded Dysglycemia](ValueSet-dcg-excluded-dysglycemia.html)).
6. **Eye exams.** Community optometry exams are often missing from EMR feeds. Send them if you have them; low eye-exam rates are reported with that caveat.

### Equity stratifiers (restricted)

Preferred service language (`Patient.communication`), [Indigenous identity](StructureDefinition-dcg-indigenous-identity.html) and [racialized group](StructureDefinition-dcg-racialized-group.html) are optional PCHDCF elements for equity stratification. They are restricted downstream: only an equity role can break results down by them, one at a time. First Nations, Inuit and Métis data follow community data governance (e.g., OCAP); send them only under an agreement with Indigenous partners.

### Synthetic data

For the PoC the first data source is a **Synthea** cohort (metabolic syndrome disease and care modules). Tag every synthetic resource with `meta.security = v3-ActReason#HTEST`; the pipeline then labels results "synthetic — not real-world performance". Synthea emits RxNorm medication codes and US-style addresses, so a post-processing step should set Canadian province and postal code.

### Privacy

The pipeline produces aggregates only and suppresses any cell under 5. Providers should still minimise: names and identifiers are not used by any indicator and may be pseudonymised before export.
