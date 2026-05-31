# Decisão: mecanismo da tabela externa de staging

**Data:** 2026-05-30
**Sub-projeto afetado:** #4 (modelo dbt)
**Status:** Implementado — sub-decisões (bucket por `target.name`, `nome_norm` no SQL) resolvidas em 2026-05-30. Camada gold dbt construída e com 29 testes verdes.

---

## Contexto

O fluxo da BD (e o `REVISAO.md` §2) exige que os dados tratados subam para o
bucket **antes** da materialização dbt, e que exista uma **tabela externa em
`<dataset>_staging`** apontando para o bucket. O dbt materializa da staging para
a camada gold.

Já temos: o parquet tratado em
`s3://<bucket>/staging/br_mma_unidades_conservacao/unidade_conservacao/unidade_conservacao.parquet`
(subido pelo `pipelines/load.py`). Falta o dbt **ler dali**.

A pergunta: **como declarar essa tabela externa no dbt, rodando sobre DuckDB?**

---

## Opções consideradas

### a) Pacote `dbt_external_tables` + source

Source com bloco `external:`, materializado via `dbt run-operation
stage_external_sources` antes do `dbt run`.

**Prós:**
- Pattern "oficial BD" no papel — espelha o fluxo real da Base dos Dados.
- Semântica de source correta na linhagem.

**Contras:**
- **Suporte a DuckDB é fraco/incompleto** — o pacote foi feito para
  Snowflake/BigQuery/Redshift; o macro `stage_external_sources` pode não ter
  implementação DuckDB. Risco de brigar com a ferramenta ou escrever macros.
- Dependência extra + passo `run-operation` a mais no flow Prefect.

### b) Staging model com `read_parquet('s3://...')`

Um model `SELECT * FROM read_parquet('s3://.../*.parquet')`, materializado como
view; gold dá `ref()`.

**Prós:**
- Simplicidade total, **zero dependência**. Funciona com o httpfs já configurado.

**Contras:**
- É um *model*, não um *source* — na linhagem aparece como model sem upstream.
  Funcionalmente é tabela externa e satisfaz o §2, mas perde a semântica de
  "isso vem de fora do dbt".

### c) Source do dbt-duckdb com `meta: external_location`

O adapter dbt-duckdb resolve um *source* com `meta: external_location:
"s3://.../*.parquet"` para um `read_parquet` automático — sem pacote, sem
`run-operation`.

**Prós:**
- Melhor dos dois: **semântica de source** (linhagem, schema `<dataset>_staging`)
  **+ simplicidade** (nativo, sem dependência).
- Satisfaz o §2 de forma limpa: tabela externa declarada como source.

**Contras:**
- Depende de recurso específico do dbt-duckdb (não portável para BigQuery) — mas
  o stack local é fixo, então não pesa. Recurso menos conhecido.

---

## Tabela comparativa

| | Canônico BD | Funciona já no DuckDB | Dep extra | Semântica de source |
|---|---|---|---|---|
| (a) dbt_external_tables | ✅ no papel | ⚠️ suporte fraco | sim | ✅ |
| (b) staging model | parcial | ✅ garantido | não | ❌ (é model) |
| (c) source + external_location | ✅ | ✅ garantido | não | ✅ |

---

## Decisão

**Escolha: (c) source do dbt-duckdb com `meta: external_location`.**

Entrega a "tabela externa em `<dataset>_staging`" que o §2 cobra, é nativo do
DuckDB (não briga com a ferramenta como o (a) briga), e não vira um
model-disfarçado-de-source como o (b). O (a) só valeria para ostentar o pattern
idêntico ao da BD aceitando escrever macros DuckDB.

---

## Justificativa

1. **Satisfaz o §2 com semântica correta.** Source de verdade → linhagem mostra
   um nó externo, schema mapeia para `<dataset>_staging`.
2. **Nativo do DuckDB.** Sem o risco de suporte ausente do `dbt_external_tables`.
3. **Sem dependência nem passo extra no flow.** O `dbt run` já resolve a leitura
   do bucket; não há `run-operation` antes.
4. **httpfs/credenciais já estão no `profiles.yml`** — a conexão dbt já lê de s3.

---

## Sub-decisão (RESOLVIDA 2026-05-30): bucket dev vs prod no `external_location`

O `external_location` é uma string, mas o bucket muda por ambiente
(`MINIO_BUCKET_DEV` vs `MINIO_BUCKET_PROD`). Como o campo aceita Jinja, há três
formas:

- **Por `target.name`:** escolher a env var no Jinja conforme o target. Mantém a
  lógica declarativa no dbt; não depende de ninguém setar env certa.
- **Env var única `MINIO_BUCKET`:** o flow/Makefile seta o bucket certo antes de
  cada `dbt run`; o yml lê só `env_var('MINIO_BUCKET')`. Centraliza no orquestrador.
- **Var do dbt** via `--vars` na invocação.

**Decisão: `target.name`.** O `_staging__sources.yml` resolve o bucket com
`{% if target.name == 'prod' %}{{ env_var('MINIO_BUCKET_PROD') }}{% else %}{{ env_var('MINIO_BUCKET_DEV') }}{% endif %}`.
Mantém a lógica declarativa no dbt — `dbt run --target dev/prod` aponta pro bucket
certo sem o orquestrador precisar setar env antes. Aposta segura: não depende de
env setada corretamente fora do dbt.

---

## Consequências / implicações — o que fazer

- **Arquivo de sources em `models/`** (ex: `_staging__sources.yml`): declara um
  `source` cujo schema mapeia para `<dataset>_staging`, com uma table
  `unidade_conservacao` e a chave `meta: external_location` apontando para
  `s3://<bucket>/staging/br_mma_unidades_conservacao/unidade_conservacao/*.parquet`.
- **Models gold** referenciam via `{{ source('<nome>', 'unidade_conservacao') }}`
  (não `ref()`).
- **Materialização gold:** `table` (overwrite — ver [[estrategia-atualizacao]]);
  o `dbt_project.yml` hoje tem default `view`, precisa sobrescrever na gold.
- **Roteamento de schema:** a staging cai em `<dataset>_staging`; o `profiles.yml`
  hoje só aponta o schema para `_dev`. Resolver via `schema:` no source e/ou
  `generate_schema_name`.
- **Teste rápido:** após criar a source, montar o model gold `unidade_conservacao`
  (`SELECT * FROM {{ source(...) }}`) e rodar `dbt run -s unidade_conservacao
  --target dev`. Se materializar as 3.421 linhas, a tabela externa está lendo o
  bucket.
- **Decisão 2 (RESOLVIDA 2026-05-30): `nome_norm` do seed.** O `uc_municipio`
  precisa que os dois lados do JOIN estejam na mesma forma normalizada. O lado
  CNUC já traz `nome_norm` pré-computado no struct (em Python, via `unidecode`).
  O lado seed `municipio` mantém o nome **cru** (snapshot fiel da BD) e a
  normalização acontece **no SQL** do model: `lower(strip_accents(m.nome))`.
  Escolha de **normalizar no SQL** (não pré-computar no CSV) para o seed
  permanecer um snapshot puro do diretório. `strip_accents` é nativo do DuckDB
  core (sem extensão `icu`) e `lower(strip_accents('Boa Esperança')) =
  'boa esperanca'` bate com o `unidecode(...).lower()` do Python — o
  `relationships` passou 100% sem lista manual. Ver [[granularidade]] e
  [[normalizacao-nomes]].

---

## Quando reconsiderar

- Se migrar o warehouse de DuckDB para BigQuery — aí o `external_location` do
  dbt-duckdb não existe, e voltaria para (a) `dbt_external_tables` (que tem
  suporte BQ maduro) ou tabela externa nativa do BQ.
- Se aparecerem múltiplas tabelas externas e o boilerplate de sources crescer —
  aí o (a) com seu macro de staging em lote pode compensar.

---

## Referências

- `REVISAO.md` §2 — tabela externa em `<dataset>_staging`.
- [dbt-duckdb — external sources](https://github.com/duckdb/dbt-duckdb#reading-from-external-files).
- [[granularidade]] — os models gold que consomem esta source.
- [[estrategia-atualizacao]] — materialização `table` (overwrite) na gold.
- [[diretorio-ibge]] — seed que o `uc_municipio` cruza.
