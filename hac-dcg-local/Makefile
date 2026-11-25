# HAC diabetes care-gaps PoC — local stack. `make help` lists the steps.
SHELL := /bin/bash
-include .env
export

ROOT        := $(CURDIR)
POP         ?= $(or $(SYNTHEA_POPULATION),2000)
SEED        ?= $(or $(SYNTHEA_SEED),20261119)
PERIOD_END  ?= 2026-09-30
ENGINE      ?= pathling
COMPOSE     := docker compose -p medplum -f medplum/docker-compose.yml -f medplum/docker-compose.override.yml
SYNTHEA_JAR := tools/synthea-with-dependencies.jar
DBT_ENV     := DBT_PROFILES_DIR=$(ROOT)/profiles DCG_DUCKDB=$(ROOT)/data/dcg.duckdb
DBT_VARS    := --vars '{period_end: "$(PERIOD_END)", data_source: "synthetic"}'
HEADLINE    := cohort_size,diabetes_prevalence_crude,a1c_tested_12m_rate,a1c_at_target_rate,bp_at_target_rate,kidney_screened_rate,eye_exam_rate,statin_rate_40plus,any_gap_rate

# Homebrew's openjdk@21 is keg-only: put it on PATH for java-based steps.
BREW_JDK := $(shell brew --prefix openjdk@21 2>/dev/null)
ifneq ($(BREW_JDK),)
  export JAVA_HOME := $(BREW_JDK)/libexec/openjdk.jdk/Contents/Home
  export PATH := $(JAVA_HOME)/bin:$(PATH)
endif

.PHONY: help check setup medplum-up medplum-down medplum-logs medplum-reset ig profiles synthea prepare \
        load load-smoke export views dbt metrics dashboard mcp-config pipeline all offline test ig-publish clean-data

help:  ## List the steps
	@grep -E '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*?## ' '{printf "  make %-14s %s\n", $$1, $$2}'

check:  ## 0. Check prerequisites (Docker, Java 17+, uv, Node/SUSHI, memory, ports)
	@bash scripts/check.sh

setup:  ## 1. Python env (.venv), SUSHI, Synthea jar, .env
	uv sync
	@command -v sushi >/dev/null || npm install -g fsh-sushi
	@mkdir -p tools data
	@test -f $(SYNTHEA_JAR) || curl -L --fail -o $(SYNTHEA_JAR) https://github.com/synthetichealth/synthea/releases/download/master-branch-latest/synthea-with-dependencies.jar
	@test -f .env || (cp .env.example .env && echo "Created .env — add the Medplum client id/secret after step 3")
	@echo "Setup done."

medplum-up:  ## 2. Start Medplum (server :8103, app :3000) and wait until healthy
	@test -f medplum/docker-compose.yml || curl -L --fail -o medplum/docker-compose.yml https://raw.githubusercontent.com/medplum/medplum/refs/heads/main/docker-compose.full-stack.yml
	$(COMPOSE) up -d
	@echo -n "Waiting for Medplum"; for i in $$(seq 1 60); do curl -sf http://localhost:8103/healthcheck >/dev/null && echo " — ready: app http://localhost:3000 (admin@example.com / medplum_admin)" && exit 0; echo -n "."; sleep 5; done; echo " not healthy after 5 min: run make medplum-logs"; exit 1

medplum-down:  ## Stop Medplum (data kept)
	$(COMPOSE) down

medplum-logs:  ## Tail Medplum server logs
	$(COMPOSE) logs -f --tail=100 medplum-server

medplum-reset:  ## Stop Medplum and DELETE its database (fresh start)
	$(COMPOSE) down -v

ig:  ## 4. Compile the Data Input IG with snapshots (SUSHI)
	cd dcg/ig && sushi build . --snapshot

profiles:  ## 5. Load CA Core+ and DCG profiles/value sets into Medplum
	uv run python etl/load_profiles.py

synthea:  ## 6. Generate the synthetic cohort (POP=2000 adults by default)
	java -jar $(SYNTHEA_JAR) -p $(POP) -s $(SEED) -a 18-90 \
	  --exporter.baseDirectory=./data/synthea/ --exporter.fhir.transaction_bundle=true \
	  --exporter.years_of_history=5 --exporter.hospital.fhir.export=false --exporter.practitioner.fhir.export=false

prepare:  ## 7. Canadianise, minimise and tag the Synthea bundles
	uv run python etl/prepare_synthea.py

load-smoke:  ## 8a. Load the first 20 patients (check data/load_report.csv)
	uv run python etl/load_medplum.py --limit 20

load:  ## 8b. Load all patients into Medplum and build the cohort Group
	uv run python etl/load_medplum.py

export:  ## 9. FHIR Bulk Data Group export from Medplum -> data/ndjson
	uv run python etl/bulk_export.py

views:  ## 10. Run the SQL-on-FHIR views (ENGINE=pathling|mini) -> DuckDB
	uv run python etl/run_views.py --engine $(ENGINE)

dbt:  ## 11. Build marts + semantic model (dbt + DuckDB)
	cd dcg && $(DBT_ENV) uv run dbt seed --quiet --full-refresh && $(DBT_ENV) uv run dbt build $(DBT_VARS)

metrics:  ## 12. Print the headline metrics with MetricFlow
	cd dcg && $(DBT_ENV) uv run mf query --metrics $(HEADLINE)

dashboard:  ## 13. Open the Streamlit dashboard (http://localhost:8501)
	DCG_DUCKDB=$(ROOT)/data/dcg.duckdb uv run streamlit run app/dashboard.py

mcp-config:  ## 14. Print the Claude Desktop config block for the MCP server
	@uv run python scripts/mcp_config.py "$(ROOT)"

pipeline: export views dbt metrics  ## Re-run export -> views -> dbt -> metrics

all: ig profiles synthea prepare load pipeline  ## Everything after Medplum is up and .env is filled

offline:  ## Run the analytics pipeline WITHOUT Medplum (Synthea -> NDJSON directly)
	@test -d data/synthea/fhir || $(MAKE) synthea
	uv run python etl/prepare_synthea.py
	uv run python etl/simulate_export.py
	$(MAKE) views dbt metrics

test:  ## Run the offline test suite (fixtures, cross-references, SHACL, IG examples)
	cd dcg && uv run python scripts/check_crossrefs.py && uv run python scripts/run_pipeline.py | tail -1 \
	  && uv run python scripts/run_shacl.py | tail -1
	@test -d dcg/ig/fsh-generated || $(MAKE) ig
	cd dcg && uv run python scripts/check_ig.py | tail -1

ig-publish:  ## Optional: full IG web site with the HL7 IG Publisher (needs Ruby + Jekyll)
	@mkdir -p tools && test -f tools/publisher.jar || curl -L --fail -o tools/publisher.jar https://github.com/HL7/fhir-ig-publisher/releases/latest/download/publisher.jar
	cd dcg/ig && java -jar ../../tools/publisher.jar -ig .

clean-data:  ## Delete generated data (keeps Medplum's database)
	rm -rf data/synthea data/prepared data/ndjson data/views data/dcg.duckdb data/load_report.csv
