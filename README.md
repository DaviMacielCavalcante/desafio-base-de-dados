# Desafio Engenheiro de Dados Jr — BD: Unidades de Conservação

Pipeline de ingestão e atualização do dataset **Unidades de Conservação** (Ministério do Meio Ambiente — `dados.gov.br`), emulando o fluxo da [Base dos Dados](https://basedosdados.org).

Tabela final: `br_mma_unidades_conservacao.unidade_conservacao`.

> **Brief do desafio:** [`README-desafio.md`](README-desafio.md) — não editar.
> **Checklist do reviewer:** [`REVISAO.md`](REVISAO.md).

## Stack

- **Storage:** MinIO local (S3-compatível) via docker-compose
- **Warehouse:** DuckDB embarcado
- **Transformação:** dbt + `dbt-duckdb`
- **Orquestração:** Prefect 3
- **Python:** 3.11+ com `uv`
- **Lint/format:** `ruff`

## Pré-requisitos

- Docker Engine + Compose plugin v2.17+ ([install Linux](https://docs.docker.com/engine/install/))
- `uv` ≥ 0.4 ([install](https://docs.astral.sh/uv/getting-started/installation/))
- GNU Make (Linux: já vem no `build-essential`, ou `sudo apt install make`)

## Setup rápido

```bash
cp .env.example .env
make setup
make pipe
```

O comando `make setup` faz: sobe MinIO, instala deps Python, instala packages dbt.

Console do MinIO: http://localhost:9001 (login `minioadmin` / `minioadmin`).

## Variáveis de ambiente

O `Makefile` carrega o `.env` automaticamente (via `-include .env` + `export` no topo) e exporta tudo pros subprocessos. Então qualquer comando via `make` (`make pipe`, `make dbt-seed`, `make dbt-build`, etc.) **já tem as env vars disponíveis** — não precisa de ritual antes.

**Quando você precisa carregar manualmente:** apenas se invocar `dbt`, `uv run dbt …` ou qualquer ferramenta CLI **fora do `make`**, em uma sessão de terminal limpa. Nesses casos:

```bash
set -a && source .env && set +a
```

**O que essa sequência faz:**
- `set -a` — liga o modo *allexport*: toda variável atribuída a partir daqui vira env var do processo.
- `source .env` — executa o `.env` (script `KEY=value`) no shell atual.
- `set +a` — desliga o *allexport*. Higiene, evita poluir env de comandos posteriores.

**Por que precisa?** O `dbt/profiles.yml` lê tudo via `{{ env_var('...') }}`. Quando você roda `uv run dbt …` direto, o `uv` cria um subprocesso, e subprocesso só herda **env vars** — não shell vars. Sem o `set -a`, o dbt estoura `Env var required but not provided`.

> **Alternativa:** [`direnv`](https://direnv.net) carrega o `.env` automaticamente ao entrar no diretório. Se você já usa, pode ignorar este passo até para invocações fora do `make`.

## Comandos

Rode `make help` pra lista completa. Os mais usados:

| Comando | O que faz |
| --- | --- |
| `make setup` | Sobe MinIO + `uv sync` + `dbt deps` |
| `make up` / `make down` | Liga/desliga MinIO |
| `make pipe` | Roda o flow Prefect |
| `make dbt-build` | `dbt run` + `dbt test` (target dev) |
| `make lint` / `make format` | Check / auto-fix com ruff |
| `make clean` | Limpa `data/*.duckdb` e `data/*.parquet` |

## Apontar para outros buckets

Edite `.env` (buckets separados por ambiente — dev e prod nunca compartilham):

```bash
MINIO_BUCKET_DEV=meu-bucket-dev
MINIO_BUCKET_PROD=meu-bucket-prod
```

Para usar **um MinIO/S3 remoto** (não o local), substitua `MINIO_ENDPOINT`, `MINIO_ROOT_USER` e `MINIO_ROOT_PASSWORD` pelas credenciais correspondentes.

## Decisões de arquitetura

### Por que stack local (MinIO + DuckDB) em vez de GCP

O brief aceita ambos. Escolhi local porque:
- Reviewer reproduz em 1 comando (sem cartão, sem service account, sem expiração).
- DuckDB tem suporte nativo a `read_parquet('s3://...')` via `httpfs` — implementa o conceito de tabela externa que o brief cobra.
- Permite focar tempo em **qualidade do tratamento + testes dbt**, não em IAM da GCP.

Migração futura para GCP fica como exercício pós-MVP (basta trocar adapter dbt e endpoint de storage; código de tratamento é agnóstico).

### Por que `dbt/profiles.yml` no repo

O default ortodoxo é `~/.dbt/profiles.yml` (fora do repo). Optei por incluir no projeto em `dbt/profiles.yml` porque:
- Reviewer não precisa mexer no `~/.dbt/` dele.
- O arquivo contém **apenas referências** a variáveis de ambiente (`{{ env_var('...') }}`) — nenhum segredo literal.
- Os valores reais vivem em `.env` (gitignored).
- A documentação oficial do dbt lista esse padrão como aceitável para "self-contained demo / CI/CD projects".

### Estratégia de atualização

**A definir no sub-projeto #5 (Prefect flow).** Candidatas: overwrite full (mais simples, dado o volume ~3.4k UCs), snapshot dbt (preserva histórico), incremental por chave. Decisão será documentada aqui após brainstorm específico.

## Layout

```
pipelines/        # Python: extração, tratamento, flow Prefect
dbt/              # projeto dbt (models, schema, profiles)
data/             # gitignored: parquet temporário + warehouse_dev.duckdb + warehouse_prod.duckdb
tests/            # pytest
docs/             # specs e plans dos sub-projetos
```

## Limitações conhecidas (estado atual)

Este repo está em **sub-projeto #1 / 6** — apenas a infra está pronta. O que **ainda não existe**:

- [ ] Extração + tratamento + join IBGE (sub-projeto #2)
- [ ] Upload e tabela externa em staging (sub-projeto #3)
- [ ] Modelo dbt + testes obrigatórios (sub-projeto #4)
- [ ] Flow Prefect + gate dev→prod + schedule (sub-projeto #5)
- [ ] CI, observabilidade, max_date metadata (sub-projeto #6)

`make pipe` por enquanto só imprime `placeholder`.
