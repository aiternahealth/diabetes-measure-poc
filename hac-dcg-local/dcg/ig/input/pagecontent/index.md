### Purpose

This **draft** Implementation Guide defines the FHIR R4 data a provider must supply so the Health Analytics Community (HAC) FHIR Analytics PoC can compute **diabetes care-gap indicators** — A1C testing and control, blood-pressure control, kidney, lipid, eye and foot screening, and statin use.

It is the data-input contract for the PoC pipeline:

```
FHIR Bulk Data $export (this IG) → SQL-on-FHIR views → dbt marts → semantic model → dashboard + AI agent
```

### Scope

| In scope (v0.3) | Out of scope |
|---|---|
| Patient demographics, optional equity stratifiers (restricted) | Reporting outputs (MeasureReport) — indicators are computed downstream |
| Diabetes diagnoses in SNOMED CT or ICD-10-CA, with the Encounter that sets the care setting | Self-monitored glucose and CGM data |
| Complications, ketoacidosis and hypoglycemia; CKD and ASCVD | Care plans (DSME) |
| HbA1c (% or mmol/mol), eGFR, urine ACR, LDL-C, glucose results; BMI and blood pressure | Provincial fee codes and CCI interventions (jurisdiction-specific) |
| Orders and pharmacy dispenses for antihyperglycemics, statins, ACEi/ARBs | |
| Eye and foot screening procedures | |

The case phenotype **DM-ADULT-CASE v0.1** (hospital diagnosis, two ambulatory diagnoses in 730 days, a declared condition, or two HbA1c ≥ 6.5%; medication as supporting evidence) is applied downstream; this IG supplies the evidence it needs.

### Building on CA Core+

Every profile derives from the matching **CA Core+ 1.2.1-dft** profile (`ca.infoway.io.core`), and adds only what the pipeline reads. MedicationDispense derives from base R4 until CA Core+ profiles it. CA Core+ has no vital-signs profile, so [DCG Blood Pressure](StructureDefinition-dcg-blood-pressure.html) follows the FHIR R4 vital-signs pattern on top of the generic CA Core+ Observation.

### Status

Draft for HAC discussion. Canonical URL, package id and value sets are **placeholders** until the group agrees on governance and the codes are verified against the Canadian Terminology Server.
