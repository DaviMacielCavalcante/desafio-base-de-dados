.PHONY: setup up down sync flow lint format dbt-deps dbt-seed dbt-build dbt-test clean help
.DEFAULT_GOAL := help

# Carrega .env se existir e exporta tudo pros subprocessos (dbt, uv, etc.)
-include .env
export

# Flags padrão para o dbt neste projeto
# Não faça "cd dbt" para rodar estes comandos.
# Rode eles a partir da raiz do projeto
DBT_FLAGS := --project-dir dbt --profiles-dir dbt

help:
	@echo "Comandos disponíveis:"
	@echo "  setup       - sobe MinIO, instala deps Python, instala packages dbt"
	@echo "  up          - sobe MinIO (docker compose up -d --wait)"
	@echo "  down        - derruba MinIO"
	@echo "  sync        - instala/atualiza deps Python (uv sync)"
	@echo "  flow        - roda o flow Prefect localmente"
	@echo "  lint        - ruff check + ruff format --check"
	@echo "  format      - ruff format + ruff check --fix (escreve)"
	@echo "  dbt-deps    - instala dbt packages"
	@echo "  dbt-seed    - carrega seeds (dbt/seeds/*.csv) no warehouse (target dev)"
	@echo "  dbt-build   - dbt seed + dbt run + dbt test (target dev)"
	@echo "  dbt-test    - só dbt test (target dev)"
	@echo "  clean       - remove data/*.duckdb e data/*.parquet (não mexe no MinIO)"

setup: up sync dbt-deps 
	@echo "Ambiente pronto. Rode: make pipe"

up:
	docker compose up -d --wait 
down: 
	docker compose down 

sync: 
	uv sync 

pipe: 
	uv run python -m pipelines.pipe 

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff format .
	uv run ruff check . --fix 

dbt-deps:
	uv run dbt deps $(DBT_FLAGS)

dbt-seed:
	uv run dbt seed --target dev $(DBT_FLAGS)

dbt-build:
	uv run dbt seed --target dev $(DBT_FLAGS)
	uv run dbt run --target dev $(DBT_FLAGS)
	uv run dbt test --target dev $(DBT_FLAGS)

dbt-test:
	uv run dbt test --target dev $(DBT_FLAGS)

clean:
	rm -rf data/*.duckdb data/*.parquet