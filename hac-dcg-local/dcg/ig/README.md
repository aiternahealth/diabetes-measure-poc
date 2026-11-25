# HAC Diabetes Care Gaps — Data Input IG (FSH, draft 0.1.0)

Build: `sushi build .` then the HL7 IG Publisher (`ig.ini` is included). Requires access to packages.fhir.org for
`ca.infoway.io.core#1.2.1-dft`.

**Compile status (2026-11-19):** SUSHI 3.21.1 → 0 errors. This environment could not reach the FHIR package
registries, so the compile used the official `hl7.fhir.r4.core#4.0.1` (GitHub mirror) and a *local stub* of the
seven CA Core+ parent profiles (base R4 snapshots under the CA Core+ canonical URLs). FSH syntax, paths, slicing,
bindings and examples are verified; **conflicts with CA Core+'s own constraints are not** — run SUSHI + IG
Publisher (or the HL7 validator) against the real package before circulating.

Files: `input/fsh/` — aliases, profiles, terminology, rule sets + invariants, logical model + mappings,
CapabilityStatement, examples. `input/pagecontent/` — Home, Data Provider Guide, Semantic Alignment.
Canonical `http://fhir.hac-poc.example/dcg` and package id `hac.dcg.datainput` are placeholders.
