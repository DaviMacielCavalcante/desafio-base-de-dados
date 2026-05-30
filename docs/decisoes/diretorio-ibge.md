# Decisão: origem do diretório IBGE de municípios

**Data:** 2026-05-28
**Sub-projeto afetado:** #2 (tratamento) e #4 (dbt)
**Status:** Decidido

---

## Contexto

O `README-desafio.md` exige `id_municipio` com **código IBGE de 7 dígitos** (ex: São Paulo capital = `3550308`), seguindo o padrão do diretório `br_bd_diretorios_brasil.municipio` da Base dos Dados. O CNUC traz apenas o nome do município (e UF entre parênteses), não o código. Para atribuir o código, é preciso cruzar `(nome_normalizado, sigla_uf)` contra uma tabela que tenha as três colunas: `nome`, `sigla_uf`, `id_municipio`.

Essa tabela é o **diretório IBGE de municípios**. Na Base dos Dados existe como `br_bd_diretorios_brasil.municipio` (BigQuery). O projeto roda em DuckDB local — precisa de uma cópia local.

A pergunta: **de onde puxar essa tabela?**

---

## Opções consideradas

### a) Pacote Python `basedosdados`

**Como funciona:** `bd.read_table('br_bd_diretorios_brasil', 'municipio')` baixa direto e retorna DataFrame.

**Prós:**
- Dado sempre atualizado (puxa do BigQuery).
- API simples.

**Contras:**
- Adiciona dep pesada e dependência viva (precisa de internet/credencial em runtime).
- Para um dataset que muda a cada ~10 anos, exagero.
- Pode pedir credencial GCP em alguns cenários.

### b) Seed do dbt (`dbt/seeds/municipio.csv`)

**Como funciona:** baixa o CSV **uma vez**, versiona em `dbt/seeds/`, e usa via `{{ ref('municipio') }}` nos models.

**Prós:**
- Versionado no git — reproduzível e auditável.
- Sem dep viva em runtime.
- ~200 KB — cabe trivialmente.
- Dado muda raramente (~10 anos, no censo IBGE).
- Padrão idiomático do dbt pra dados de referência pequenos.

**Contras:**
- Quando o IBGE atualizar o diretório (após próximo censo), precisa baixar de novo manualmente. **Não é problema** no horizonte do projeto.
- Precisa baixar uma vez de algum lugar pra popular o seed.

### c) API direto do IBGE

**Como funciona:** chama `servicodados.ibge.gov.br/api/v1/localidades/municipios` em runtime, recebe JSON, converte.

**Prós:**
- Sem dep Python específica.
- Sempre atualizado.

**Contras:**
- Schema diferente do diretório BD (JSON precisa de massagem pra virar `(nome, sigla_uf, id_municipio)`).
- Dependência viva em runtime — pipeline depende do IBGE estar no ar.
- Estrutura aninhada de mesorregiões/microrregiões — parsing chato.

---

## Decisão

**Escolha: (b) seed dbt em `dbt/seeds/municipio.csv`.**

**Origem inicial do CSV:** baixar **uma vez** via pacote `basedosdados` em um script utilitário (ou notebook descartável), salvar como `dbt/seeds/municipio.csv`, e **remover** a dep do `pyproject.toml`. O pacote não fica no projeto rodando — é só ferramenta de bootstrap.

---

## Justificativa

1. **Dado de referência pequeno + raramente muda = caso clássico de seed.** Versionado, auditável, reproduzível.
2. **Sem dependência viva** em runtime — pipeline não quebra se a BD ou IBGE ficar fora do ar.
3. **`basedosdados` é só meio**, não fim. Usa uma vez pra puxar o snapshot oficial da BD (que já está limpo no formato canônico) e descarta.
4. **Bem alinhado com o padrão dbt** — `{{ ref('municipio') }}` resolve nativamente, modelos materializam normalmente.

---

## Consequências / implicações

- **Bootstrap:**
  1. `uv add basedosdados` (temporário).
  2. Script ou notebook: `bd.read_table('br_bd_diretorios_brasil', 'municipio').to_csv('dbt/seeds/municipio.csv', index=False)`. Reduz pra `(id_municipio, nome, sigla_uf)` antes de salvar.
  3. `uv remove basedosdados`.
  4. Commitar `dbt/seeds/municipio.csv` no git.
- **dbt:** o `municipio.csv` é carregado por `dbt seed`. Alvo `dbt-seed` já existe no `Makefile`, e `dbt-build` encadeia seed antes de run.
- **Tipos do seed:** declarar `id_municipio`, `nome` e `sigla_uf` como `varchar` no `_seeds.yml` (não inferir como int — vai contra o style guide BD).
- **Tamanho:** ~5.570 linhas × 3 colunas relevantes ≈ ~200 KB. Não polui o git.
- **`nome_norm` pro join CNUC ↔ IBGE:** o seed mantém só `nome` (forma canônica). A coluna normalizada `nome_norm` (sem acento, lowercase, etc.) é produzida via **model dbt intermediário** `municipio_norm`, com algo como:

  ```sql
  SELECT
      id_municipio,
      nome,
      sigla_uf,
      lower(strip_accents(nome)) AS nome_norm
  FROM {{ ref('municipio') }}
  ```

  O `strip_accents` (ou equivalente — `accent_remove`, `unaccent`, depende da função suportada pela versão do DuckDB) precisa estar disponível. Se não estiver, alternativa: pré-computar `nome_norm` direto no CSV do seed (computado uma vez no bootstrap em Python via `unidecode`, salvo no `dbt/seeds/municipio.csv` como 4ª coluna). A função de normalização tem que ser a **mesma** que o lado CNUC usa (ver [[normalizacao-nomes]]) — não pode divergir.
- **Refresh manual:** se o IBGE publicar nova divisão (próximo censo), rodar o bootstrap de novo. Registrar em commit dedicado.

---

## Quando reconsiderar

- Se o IBGE publicar uma versão muito mais frequente (improvável) → reconsiderar API viva.
- Se aparecer demanda de "diretório vivo" com colunas adicionais (mesorregião, capital, etc.) → talvez justifique migrar pra API ou re-seed mais rico.
- Se o desafio crescer pra cobrir municípios estrangeiros (Mercosul?) → precisa de outra fonte.

---

## Referências

- `docs/exploracao-bruto.md` — Fase D.6 (UF), uso do join.
- [[granularidade]] — `id_municipio` vive na tabela ponte `uc_municipio`.
- [[normalizacao-nomes]] — algoritmo de match `(nome, sigla_uf)` entre CNUC e este diretório.
- [dbt docs — seeds](https://docs.getdbt.com/docs/build/seeds)
- [Base dos Dados — diretório municipal](https://basedosdados.org/dataset/br-bd-diretorios-brasil)
- `docs/superpowers/plans/2026-05-28-tratamento.md` §0.3.
