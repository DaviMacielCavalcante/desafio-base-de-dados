# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository status

Implementation in progress — **sub-projetos #1–#6 done** (as of 2026-05-31). The solution README is `README.md`.

Done so far:

- **Extraction + treatment (Python, `pipelines/`):** `extract.py` → `transform.py` produce the silver parquet (3.421 UCs, 1 row per UC, `municipios_abrangidos` as `ARRAY[STRUCT]`).
- **Storage IO (`load.py`, `utils/client.py`):** `get_s3_client()` factory; `upload()` (dev) and `promote_data()` (server-side copy dev→prod) with `ensure_bucket`.
- **dbt gold layer (`dbt/models/br_mma_unidades_conservacao/`):** external source reading the bucket, models `unidade_conservacao` (flat), `uc_municipio` (bridge to IBGE) and `uc_bioma` (área por bioma, long), seeds `municipio` (IBGE directory) and `dicionario`, `schema.yml` with 29 green tests. Runs via `make dbt-build`.
- **Prefect flow (`pipe.py`):** `@flow main()` chains extract→transform→upload(dev)→dbt seed/run/test(dev)→**gate**→promote(dev→prod)→dbt seed/run(prod). dbt invoked via `prefect-dbt` `PrefectDbtRunner` (`utils/runner.py`); the gate is automatic (test failure raises → promotion tasks downstream never run). One-shot via `make pipe`; scheduled via `make serve` + a persistent `prefect server` (see README §Agendamento).
- **Quality gate (#6):** 17 unit tests for `transform.py` (`tests/unit/`, run via `make test`); `mypy` typecheck (`make typecheck`); `pre-commit` hook (ruff + mypy) blocking local commits; CI (GitHub Actions) running `make lint`/`typecheck`/`test` + `dbt parse` on push/PR.
- **Metadata + observability (#6):** `write_metadata()` task (after prod run) writes `data/metadata/<dataset>.json` with `max(ano_ato_legal_mais_recente)` + row count + timestamp, and a Prefect markdown artifact; `load.py` IO logs via `get_run_logger()` (shown in task runs).

All sub-projects (#1–#6) and the bonus items are done. Remaining items are optional hygiene only.

## What is being built

A data pipeline that emulates Base dos Dados' real ingestion flow for the **Unidades de Conservação** dataset (Ministério do Meio Ambiente, `dados.gov.br`). The pipeline must follow this exact flow:

```
Fonte (dados.gov.br)
  └─ download + tratamento (Python, inside Prefect flow)
       └─ local parquet/csv
            └─ upload to bucket (GCS or S3/MinIO)
                 └─ external table in <dataset>_staging
                      └─ dbt run/test (target=dev)  → materialized table
                           └─ promotion to prod (storage copy + dbt run target=prod)
```

**Canonical naming** (do not change without justification in the solution README):
- Dataset: `br_mma_unidades_conservacao`
- Table: `unidade_conservacao`
- dbt model path: `models/br_mma_unidades_conservacao/br_mma_unidades_conservacao__unidade_conservacao.sql`
- Storage path: `<bucket>/staging/br_mma_unidades_conservacao/unidade_conservacao/`

## Stack (mandatory)

| Layer | Tech |
| --- | --- |
| Orchestration | Prefect 3 |
| Transformation | dbt Core (adapter free choice) |
| Storage | GCS **or** S3-compatible (MinIO acceptable) |
| Warehouse | BigQuery **or** DuckDB/Postgres (dbt must connect to it) |
| Language | Python 3.11+ |

Two valid infra paths: **GCP trial** (closest to real BD) or **docker-compose with MinIO + DuckDB/Postgres**. Pick one and document it; the dev/prod gate must work in both.

## Non-negotiable architectural rules

These come straight from the spec and the review checklist — getting any of them wrong is a guaranteed deduction.

1. **Dev → gate → prod separation.** Two BQ datasets (or two schemas in local mode). `dbt test` failing on `target=dev` must **abort** the promotion to prod. The gate is real, not cosmetic.
2. **External staging table.** Treated data is uploaded to the bucket first; `<dataset>_staging` reads from the bucket as an external table. dbt materializes from staging into the public dataset.
3. **`id_municipio` with IBGE 7-digit code.** Derived by joining against `br_bd_diretorios_brasil.municipio` (columns: `id_municipio`, `nome`, `sigla_uf`). Name normalization must be reproducible — no manual fix lists.
4. **Multi-municipality and marine UCs.** Define and document the granularity (one row per UC×municipality, list column, sentinel for marine, etc.). The chosen approach must make the `not_null` and `relationships` tests on `id_municipio` pass.
5. **Idempotency.** Running the flow twice must not corrupt the table. The update strategy (overwrite / incremental / snapshot / merge) is the implementer's choice but must be **documented and justified** in the solution README.
6. **Style guide compliance.** snake_case, no accents, BigQuery types, `STRING` for codes with leading zeros. Read https://basedosdados.org/docs/style_data — most review feedback is style-guide nits.
7. **Secrets out of code.** Use `.env` or Prefect Blocks/Secrets. `.env.example` must list every required variable. `profiles.yml` reads via `{{ env_var('...') }}`. Raw data is **not** versioned in git.

## Required dbt tests (gate-blocking)

In `schema.yml`, at minimum:

- ID column of the UC: `unique` + `not_null`
- `id_municipio`: `not_null` + `relationships` to `br_bd_diretorios_brasil.municipio`

These tests must run **inside the Prefect flow** (the `dbt test` step), not just locally. Failure aborts promotion to prod.

## Suggested project layout (when implementation starts)

Not prescribed by the spec, but typical for this stack:

```
pipelines/         # Python: extraction + treatment functions, Prefect flows
dbt/               # dbt project (profiles.yml reads from env_vars)
  models/br_mma_unidades_conservacao/
docker-compose.yml # only if using local MinIO + DuckDB/Postgres path
.env.example
pyproject.toml     # uv or poetry
```

## When the implementation exists

Once code lands, this file should be updated with the actual commands for:

- Installing deps (`uv sync` / `poetry install`)
- Running the Prefect flow end-to-end locally
- Running a single dbt model and a single dbt test
- Bringing up the local stack (`docker compose up`) if applicable
- Running Python tests / lint

## Language

The challenge and review docs are in Portuguese. Solution README, code comments, and column descriptions in `schema.yml` should be in Portuguese to match BD's published datasets.
