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
| `make pipe` | Roda o flow Prefect **uma vez** (one-shot) |
| `make serve` | Registra o deployment e agenda o flow (ver §Agendamento) |
| `make dbt-build` | `dbt seed` + `dbt run` + `dbt test` (target dev) |
| `make lint` / `make format` | Check / auto-fix com ruff |
| `make clean` | Limpa `data/*.duckdb` e `data/*.parquet` |

## Agendamento (schedule)

`make pipe` roda o flow **uma vez** contra um servidor Prefect efêmero. Para
**agendar** (rodar na cadência definida no `serve()`, ex. semanal), o Prefect
precisa de um **servidor persistente** rodando o scheduler — o efêmero não agenda.

São **dois processos**, em dois terminais:

```bash
# Terminal 1 — sobe o servidor Prefect (API + scheduler + UI em :4200). Deixa rodando.
prefect server start

# Terminal 2 — aponta o cliente pro servidor e serve o deployment
export PREFECT_API_URL=http://127.0.0.1:4200/api
make serve
```

Com isso o scheduler dispara o flow na cadência configurada; acompanhe os runs no
terminal 2 ou na UI em <http://127.0.0.1:4200>.

> **Por que o `export` só na sessão do `serve`** (e não no `.env`): se
> `PREFECT_API_URL` for permanente, **todo** comando — inclusive `make pipe` —
> passa a exigir o servidor no ar. Mantendo o `export` local ao terminal do
> `serve`, o `make pipe` continua independente (usa o efêmero).
>
> Para produção real seria um work-pool + worker dedicado; para o schedule
> demonstrável do desafio, servidor + `flow.serve()` basta.

## Apontar para outros buckets

Edite `.env` (buckets separados por ambiente — dev e prod nunca compartilham):

```bash
MINIO_BUCKET_DEV=meu-bucket-dev
MINIO_BUCKET_PROD=meu-bucket-prod
```

Para usar **um MinIO/S3 remoto** (não o local), substitua `MINIO_ENDPOINT`, `MINIO_ROOT_USER` e `MINIO_ROOT_PASSWORD` pelas credenciais correspondentes.

## Modelo de dados

Segue o estilo da BD (tabela achatada + diretórios + dicionário — **não** Kimball
fato/dimensão). O dataset `br_mma_unidades_conservacao` tem quatro tabelas:

| Tabela | Granularidade | Papel |
| --- | --- | --- |
| `unidade_conservacao` | 1 linha por UC | tabela achatada da entidade; categóricas como colunas STRING |
| `uc_municipio` | 1 linha por par `(id_uc, id_municipio)` | ponte n:n para o diretório de municípios |
| `uc_bioma` | 1 linha por par `(id_uc, bioma)` | distribuição de área por bioma em formato **long** |
| `municipio` (seed) | 1 linha por município | diretório IBGE (emula `br_bd_diretorios_brasil.municipio`) |
| `dicionario` (seed) | 1 linha por `(coluna, chave)` | dicionário BD das colunas `indicador_*` (código → significado) |

Pontos de modelagem (detalhados em [`docs/decisoes/`](docs/decisoes/)):

- **Multi-municipalidade:** uma UC abrange vários municípios. Em vez de achatar
  com `id_municipio` repetido, a UC guarda `municipios_abrangidos`
  (`ARRAY[STRUCT(nome, sigla_uf, nome_norm)]`) e a ponte `uc_municipio` explode
  isso via `UNNEST` + JOIN no diretório.
- **`id_municipio` (IBGE 7 dígitos):** derivado por JOIN reproduzível em
  `(nome_norm, sigla_uf)` — `nome_norm` pré-computado em Python (`unidecode`) de um
  lado, `lower(strip_accents(...))` no SQL do outro. Sem lista manual de correção.
- **UCs marinhas:** neste dataset todas trazem ≥1 município costeiro, então
  aparecem na ponte normalmente (o `not_null`/`relationships` passa).
- **Distribuição por bioma (long over wide):** a fonte traz 6 colunas
  `area_<bioma>` (wide). Seguindo o princípio "long over wide" do manual BD, essas
  colunas **saem** da tabela achatada e viram a `uc_bioma` (1 linha por UC×bioma
  com área > 0), via `UNPIVOT`. Os agregados `area_soma_biomas` e
  `area_soma_biomas_continental` permanecem na `unidade_conservacao`.

### Testes dbt (gate)

29 testes em [`schema.yml`](dbt/models/br_mma_unidades_conservacao/schema.yml) e nos
seeds. Obrigatórios: `unique`/`not_null` em `id_uc`, `not_null`/`relationships` em
`id_municipio`. Diferenciais: `accepted_values` (esfera, grupo, categoria IUCN,
bioma), `accepted_range` (datas, proporção, áreas) e `unique_combination_of_columns`
nas pontes — via `dbt_utils`.

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

Este repo está em **sub-projeto #5 / 6**. O que **já existe**:

- [x] Extração + tratamento + join IBGE (sub-projeto #2)
- [x] Upload e tabela externa em staging (sub-projeto #3)
- [x] Modelo dbt + testes obrigatórios + diferenciais do §4 (sub-projeto #4)
- [x] Flow Prefect (extract→transform→upload→dbt) + gate dev→prod + schedule (sub-projeto #5)

O que **ainda não existe**:

- [ ] CI, observabilidade, testes unitários do tratamento, max_date metadata (sub-projeto #6)

> `make pipe` roda o flow Prefect fim-a-fim: extract → transform → upload(dev) →
> dbt seed/run/test(dev) → **gate** → promote(dev→prod) → dbt seed/run(prod). O
> agendamento é via `make serve` (ver §Agendamento).
