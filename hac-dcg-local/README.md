# HAC Diabetes Care Gaps — local stack (macOS)

Everything runs on your Mac: Medplum (FHIR server) in Docker, then Synthea → Medplum → Bulk export →
SQL-on-FHIR views (Pathling) → dbt marts + MetricFlow semantic model (DuckDB) → Streamlit dashboard and
an MCP server that lets Claude Desktop answer questions from the governed metrics.

```
Synthea ──prepare──▶ Medplum (validates against DCG IG + CA Core+) ──Group $export──▶ NDJSON
   ──Pathling views──▶ DuckDB fhir_views ──dbt──▶ marts ──MetricFlow──▶ dashboard · Claude (MCP)
```

**Time:** about 1 hour the first time (mostly downloads and the Synthea/Medplum load).
**Machine:** 16 GB RAM recommended, 15 GB free disk. Synthetic data only — never load real patient data here.

| Folder | What's in it |
|---|---|
| `dcg/` | Ontology, SQL-on-FHIR views, dbt models, semantic model, agent contract, FSH IG (`dcg/ig`) |
| `etl/` | Python steps: prepare Synthea, load profiles/data into Medplum, Bulk export, run views |
| `app/` | Streamlit dashboard |
| `agent/` | MCP server for Claude Desktop |
| `medplum/` | Override for Medplum's official Docker Compose file |
| `data/` | Everything generated (git-ignored) |

---

## Steps

Run every command from this folder in Terminal. `make help` lists them all.

### 0 · Prerequisites
```bash
brew bundle          # uv, Java 21, Node, jq
make check
```
Install **Docker Desktop** (or OrbStack) yourself if `make check` says it's missing, start it, and run `make check` again until it prints `Ready.`

### 1 · Setup
```bash
make setup
```
Creates `.venv` with all Python packages (versions pinned in `uv.lock`), installs SUSHI, downloads the Synthea jar into `tools/`, creates `.env`.

### 2 · Start Medplum
```bash
make medplum-up
```
Downloads Medplum's official `docker-compose.full-stack.yml`, applies `medplum/docker-compose.override.yml`
(bigger request limit for Synthea bundles, local bots, Postgres/Redis not exposed on your host) and waits
until `http://localhost:8103/healthcheck` answers. First start pulls images and runs database migrations: allow 3–5 minutes.

### 3 · Create the pipeline's client credentials (in the browser)
1. Open http://localhost:3000 and sign in with **admin@example.com / medplum_admin** (the default seeded super-admin).
2. Open the project admin page (http://localhost:3000/admin/project), go to **Clients**, create a new client named `dcg-pipeline`.
3. Open the new client and copy its **ID** and **Secret** into `.env`:
   ```
   MEDPLUM_CLIENT_ID=...
   MEDPLUM_CLIENT_SECRET=...
   ```
For this local, synthetic PoC the default project is fine. Medplum's admin screens change between releases: if a label differs, look for "Clients" / "ClientApplication" under the project admin.

### 4 · Compile the Data Input IG
```bash
make ig
```
SUSHI compiles `dcg/ig` with snapshots into `dcg/ig/fsh-generated/`. Expect `0 Errors`; warnings about
"automatically-provided" packages are fine. This is also the first build against the **real** CA Core+ package — if
SUSHI reports conflicts with CA Core+ constraints, send me the output.

### 5 · Load profiles into Medplum
```bash
make profiles
```
Uploads CA Core+ 1.2.1-dft (downloaded from packages.fhir.org) and the DCG profiles/value sets. From now on Medplum
validates any resource whose `meta.profile` names a DCG profile.

### 6 · Generate the synthetic cohort
```bash
make synthea              # 2,000 adults (POP=5000 make synthea for more)
```
Output: `data/synthea/fhir/*.json`, one transaction bundle per person. 2,000 people take roughly 5–10 minutes.

### 7 · Prepare the bundles
```bash
make prepare
```
Per person: Canadian province/postal code (population-weighted), US identifiers/extensions removed, only the data the
pipeline needs (≈97 % smaller), every resource tagged synthetic (`meta.security = HTEST`) and with its DCG profile,
conditional creates so re-loading never duplicates. Prints counts per resource type and profile.

### 8 · Load into Medplum
```bash
make load-smoke           # first 20 people — check data/load_report.csv
make load                 # everyone; builds the cohort Group
```
`data/load_report.csv` has one row per person: `loaded`, `loaded_without_profiles` (Medplum rejected the profiled
version — the `issues` column says why, and the data was loaded without `meta.profile` so the pipeline still works), or
`failed`. **The `issues` column is your IG conformance report** — bring it to the next session.

### 9–12 · Run the analytics pipeline
```bash
make pipeline             # = export → views → dbt → metrics
```
- **export**: Group-level FHIR Bulk Data `$export` → `data/ndjson/<Type>.ndjson`
- **views**: the 7 ViewDefinitions on Pathling (first run downloads Pathling's engine, ~1 min) → DuckDB `fhir_views`
  (`ENGINE=mini make views` uses the pure-Python runner instead — no Java, fine up to a few thousand people)
- **dbt**: seeds, marts and the semantic model, 12 tests
- **metrics**: prints the headline indicators from MetricFlow

### 13 · Dashboard
```bash
make dashboard            # http://localhost:8501
```

### 14 · Ask Claude (MCP)
```bash
make mcp-config
```
Paste the printed block into `~/Library/Application Support/Claude/claude_desktop_config.json` (merge with any
existing `"mcpServers"`), quit and reopen Claude Desktop. Then ask, for example:
*"What share of people with type 2 diabetes had an A1C test in the past year, by age band?"*
Claude answers through 6 governed tools; suppression, the 3-dimension limit and the FSA rule are enforced by the server.

---

## What's new in v0.4 (alignment with the Diabetes Care Intelligence canonical-layer design)
- **Case phenotype DM-ADULT-CASE v0.1** (`models/intermediate/int_dm_case_evidence.sql`): a person qualifies on a declared
  diabetes condition, one hospital diagnosis, two ambulatory diagnoses within 730 days, or two HbA1c ≥ 6.5% on separate
  days (outside a gestational-diabetes window). Medication is supporting evidence only; medication-only people are
  counted as `possible_case_rate`, outside the cohort. Every row carries `case_basis`, `index_date`, `phenotype_id`,
  `phenotype_version` and `map_version`. All rules are dbt vars (`pheno_*`); set `pheno_accept_declared_condition: false`
  for a claims-only CCDSS-style cohort. Diabetes type is a heuristic: type_1 | type_2 | other_specified | unclassified.
- **ICD-10-CA** alongside SNOMED CT: new `icd10ca_code` view column, prefix-matched value-set rows, and condition
  profiles with SNOMED CT and ICD-10-CA coding slices. Encounters referenced by Conditions are now kept and exported.
- **Unit standardisation** (`int_observation_std`): HbA1c mmol/mol → %, glucose and LDL mg/dL → mmol/L, ACR mg/g →
  mg/mmol; originals kept. Blood pressure now also has SHACL's plausible ranges.
- **Medications**: orders and pharmacy dispenses (new `dcg_medication_dispense` view and `DCGMedicationDispense` profile),
  classified by ATC prefix or ingredient; new classes (TZD, alpha-glucosidase inhibitor, other incl. tirzepatide);
  combination products count toward each ingredient.
- **New measures**: cardio-renal agent among people with CKD or ASCVD (DCI M9) and its gap (9th gap type), DKA or
  hypoglycemia admissions per 1,000 (M10), A1C > 9% among tested (M4) and BP at target among measured (M6); CKD from codes
  or two abnormal labs 90+ days apart. Saved queries `dci_core_measures` and `cohort_by_case_basis`.
- **Equity stratifiers** (M11): service language, Indigenous identity, racialized group — restricted dimensions, only with
  `DCG_EQUITY_ROLE=1`, one at a time; Patient extensions in the IG.
- **Mapping governance**: every value-set row carries match type, SKOS relation, confidence, status and map version;
  `rpt_code_stewardship` lists unmapped codes and units (record counts only).
- **Agent**: new MCP tools `explain_measure` (definition-level evidence trail), `cohort_evidence_summary` and
  `stewardship_queue`; every answer carries data currency and lineage; DCI competency questions in
  `dcg/agent/competency_questions.yaml` run as tests.
- IG 0.3.0: 15 profiles, 2 extensions, 16 value sets, 25 examples. Ontology 0.4.0-draft with PCHDCF concept annotations.

## What's new in v0.3 (cohort profile)
- **Medication-class rates** for the whole cohort: metformin, insulin, SGLT2 inhibitor, GLP-1 receptor agonist,
  DPP-4 inhibitor, sulfonylurea, ACE inhibitor/ARB and any antihyperglycemic (order in 12 months or active, by ATC class).
- **BMI and BP levels**: BMI recorded rate, mean/median latest BMI, mean/median latest systolic and diastolic BP, and a
  `bmi_category` dimension. These are context measures: each is reported beside its at-target or recorded rate, and
  is suppressed when fewer than 5 people stand behind it. New IG profile **DCG BMI** (`dcg-bmi`).
- **Duplicate-diagnosis check**: `dq_dm_duplicate_rate`, the same diabetes code recorded on more than one Condition.
- **`cohort_profile` saved query** (18 metrics) and a `run_saved_query` tool for Claude, so "profile the diabetes
  patients" gets the same answer every time: `mf query --saved-query cohort_profile`, or ask Claude.
- Dashboard: new "Cohort profile" section.

## Day to day
```bash
make medplum-up && make pipeline && make dashboard
```
Change thresholds (A1C target, windows, period end) in `.env` (`PERIOD_END`) or `dcg/dbt_project.yml`, then `make dbt`.

**No Medplum at hand?** `make offline` runs Synthea → prepare → simulated export → views → dbt directly.

## What to expect from Synthea data
| Finding | Why |
|---|---|
| Foot-exam rate 0 % (gap 100 %) | Synthea doesn't generate diabetic foot exams — a generator gap, flagged in the dashboard and metric caveats |
| Eye exams use SNOMED 722161008 / 314971001 | Synthea's codes; added to the eye-exam value set (36228007 kept for real sources) |
| LDL and glucose in mg/dL | Synthea is US-based; the indicators only need the test to exist, not the unit |
| ~5 % of people have diabetes | Synthea's prevalence; generate 5,000+ people if breakdowns are mostly "suppressed (<5)" |
| Province/postal code are synthetic | Assigned by `prepare`; FSAs and cities are real, the last three postal characters aren't |

## Troubleshooting
| Symptom | Fix |
|---|---|
| `make medplum-up` never becomes healthy | `make medplum-logs`; give Docker 6 GB+ memory in its settings; `make medplum-reset` for a clean database |
| `Token request failed (401)` | Client id/secret in `.env` wrong, or created in another project |
| Load: `413` / payload too large | The override wasn't applied — check `medplum/docker-compose.override.yml` exists, then `make medplum-down medplum-up` |
| Many `loaded_without_profiles` | Expected while the IG matures — read the `issues`; common causes are CA Core+ must-haves Synthea lacks |
| Pathling: `Unable to locate a Java Runtime` / Java errors | `brew install openjdk@21`; the Makefile puts it on PATH automatically |
| `ports are not available` | Another app uses 3000 or 8103 — stop it (`make check` names it) |
| Dashboard: "No database" | Run `make pipeline` first |

## Tests
`make test` — metric fixtures (18 assertions), ontology/semantic-model/view cross-references, SHACL rules, and the IG
examples against its invariants and value sets. All of it was run before this kit was handed over; Medplum and
Pathling steps were tested against a mock server and the pure-Python engine, because neither can run where it was built.
