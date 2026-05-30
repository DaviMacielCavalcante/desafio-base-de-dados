# Decisão: granularidade da tabela `unidade_conservacao`

**Data:** 2026-05-28
**Sub-projeto afetado:** #2 (tratamento) e #4 (modelo dbt)
**Status:** Decidido

---

## Contexto

Uma UC pode estar em mais de um município. O CNUC representa multi-municipalidade na coluna `Municípios Abrangidos` com separador interno `" - "` (espaço-hífen-espaço), ex: `"CAMANDUCAIA (MG) - EXTREMA (MG)"`.

> **Correção empírica (2026-05-29):** o dicionário oficial afirma "separados por vírgula", mas a inspeção do dado real (`pipelines/extract.get_data()`) mostra **0 linhas com vírgula** em `Municípios Abrangidos` e **587 com `" - "`**. A vírgula vale para a coluna `UF` (multi-UF: `"RS, SC"`), não para municípios. Nomes com hífen interno (`SAPUCAÍ-MIRIM`, `VARRE-SAI`) não quebram o split porque o hífen interno não tem espaços em volta. Ver `docs/exploracao-bruto.md`.

A pergunta: **qual o nível de granularidade da tabela final?**

A escolha condiciona diretamente:
- Os testes dbt obrigatórios (`not_null` e `relationships` em `id_municipio`)
- O número de tabelas materializadas
- A forma da query analítica típica ("quantas UCs no município X?")

---

## Opções consideradas

### a) Uma linha por UC, com `municipios` como ARRAY/STRING

**Como funciona:** mantém uma linha por UC. A coluna `municipios` vira `ARRAY<STRING>` ou string com separador.

**Prós:**
- Estrutura espelha o input.
- Cada linha = uma entidade UC clara.

**Contras:**
- `id_municipio` como ARRAY **não passa direto nos testes `not_null` / `relationships` do dbt** sem custom test.
- Queries analíticas exigem `UNNEST` toda vez.
- Style guide BD não favorece (prefere `long` a `wide`).

### b) Uma linha por UC × município (explode)

**Como funciona:** UC com 6 municípios vira 6 linhas, com atributos da UC repetidos em todas.

**Prós:**
- `id_municipio` é escalar → testes dbt passam trivialmente.
- Queries por município são naturais.

**Contras:**
- Atributos da UC (nome, ano de criação, área total, etc.) duplicados.
- "Contar UCs únicas" precisa `COUNT(DISTINCT id_uc)`.
- Mistura entidade UC com entidade município-UC numa só tabela.

### c) Star schema: tabela principal + tabela ponte

**Como funciona:** duas tabelas:
- `unidade_conservacao` — uma linha por UC, com atributos descritivos. **Sem** `id_municipio`.
- `uc_municipio` (ponte n:n) — uma linha por par `(codigo_uc, id_municipio)`.

**Prós:**
- Normalizado: sem duplicação de atributos.
- `id_municipio` na ponte é escalar → testes dbt passam.
- Queries analíticas são joins explícitos (SQL idiomático).
- UCs marinhas (sem município) simplesmente **não aparecem na ponte** — sem complicação de NULL/sentinel na chave.

**Contras:**
- Dois modelos dbt em vez de um (mais arquivos, mais testes).
- Para o reviewer "abrir a tabela e ver tudo", precisa join.

---

## Decisão

**Escolha: (c) star schema, com responsabilidades divididas entre camadas (medallion):**

- **Silver (parquet):** uma tabela única `unidade_conservacao`, 1 linha por UC. A multi-municipalidade é preservada numa coluna `municipios_abrangidos: ARRAY[STRUCT(nome, sigla_uf, nome_norm)]`.
- **Gold (dbt models):**
  - `unidade_conservacao` — espelha a silver (1 linha por UC).
  - `uc_municipio` — **derivada via UNNEST + JOIN** com o seed `municipio` do diretório IBGE. 1 linha por par `(id_uc, id_municipio)`.

Estrutura:

| Camada | Tabela | Granularidade | Forma da relação UC ↔ município |
|---|---|---|---|
| Silver | `unidade_conservacao` | 1 linha por UC | ARRAY[STRUCT] na coluna `municipios_abrangidos` |
| Gold | `unidade_conservacao` | 1 linha por UC | ARRAY[STRUCT] preservado (espelha silver) |
| Gold | `uc_municipio` | 1 linha por par `(id_uc, id_municipio)` | Escalar (UNNEST do array no model) |

**Histórico:** versão anterior desta decisão previa **dois parquets** na silver (`unidade_conservacao` + `uc_municipio`) e a bifurcação acontecia em Python. Foi revisada em 2026-05-29 para a forma acima, alinhando star schema com filosofia medallion (modelagem analítica em gold, não em silver). Ver `feedback_arquitetura-adaptavel`.

---

## Justificativa

1. **Aderência à medallion.** Silver é dado tratado e canônico. Gold é modelagem analítica. Star schema é decisão de **modelagem**, vive naturalmente em gold.
2. **Testes dbt obrigatórios fluem naturalmente.** `not_null(id_municipio)` e `relationships(id_municipio)` rodam no model gold `uc_municipio`, onde a coluna é escalar e não-nula.
3. **UCs marinhas resolvem-se sozinhas** — continuam presentes em `unidade_conservacao` com `indicador_marinha = 1`. Ver [[ucs-marinhas]]. **Correção empírica (2026-05-29):** neste dataset **não há UC sem município** — as 229 UCs com `Mar Territorial = Sim` trazem todas os municípios costeiros abrangidos. Logo elas **aparecem** no `uc_municipio` (com o `id_municipio` costeiro), e o `not_null`/`relationships` passam porque toda UC tem ≥1 município válido, não porque marinhas seriam excluídas. O cenário de lista vazia é teórico aqui.
4. **Sem duplicação de atributos da UC.** Atributos vivem em 1 linha na principal; a ponte gold só tem a relação.
5. **Pipeline Python mais simples.** Sem bifurcação. Um único `df` segue o fluxo do começo ao fim e vira um único parquet.
6. **Mais aderente ao estilo BD.** Modelagem analítica em dbt/SQL é o canônico — explode, UNNEST e joins são operações SQL idiomáticas, e dbt brilha aqui.

---

## Consequências / implicações

- **dbt (gold):** dois models — `models/br_mma_unidades_conservacao/unidade_conservacao.sql` (SELECT direto da staging) e `models/br_mma_unidades_conservacao/uc_municipio.sql` (UNNEST + JOIN com seed `municipio`). Ambos consomem a tabela externa via `source(...)` — ver [[tabela-externa-staging]].
- **`schema.yml`:** testes `unique` + `not_null` em `id_uc` no model principal. Testes `not_null` + `relationships` em `id_municipio` no model `uc_municipio`. Teste de chave composta `(id_uc, id_municipio)` única na ponte.
- **Tratamento (sub-projeto #2):** **sem bifurcação.** Pipeline linear no `df`. Em vez de explodir e separar em duas tabelas, uma função `build_municipios_struct(df)` transforma a coluna `Municípios Abrangidos` (string com separador) em `ARRAY[STRUCT(nome, sigla_uf, nome_norm)]`. A normalização do nome (`nome_norm`) é pré-computada em Python e armazenada no struct — ver [[normalizacao-nomes]] — para que o JOIN no dbt seja simples comparação de igualdade, sem precisar `unaccent`/`icu` em DuckDB.
- **Output do tratamento:** **um único parquet** em `data/staging/br_mma_unidades_conservacao/unidade_conservacao/`. Não há mais parquet `uc_municipio` na silver.
- **Seed IBGE:** precisa ter `nome_norm` pré-computado (no CSV ou via model intermediário em dbt). Ver [[diretorio-ibge]].
- **Documentação:** o reviewer vai esperar menção explícita ao star schema na gold (no `schema.yml`).

---

## Adendo: tabela `uc_bioma` (2026-05-30)

Terceiro model gold, irmão do `uc_municipio`: aplica o mesmo raciocínio
(coluna(s) multi-valor → tabela derivada) às **6 colunas `area_<bioma>`** da
fonte, que são um **formato wide**.

**Decisão: wide → long.** O manual BD é explícito (§"Tabelas devem estar no
formato long, ao invés de wide"). As 6 colunas `area_amazonia … area_pantanal`
**saem** da `unidade_conservacao` (via `select * exclude (...)`) e viram a
`uc_bioma`: 1 linha por par `(id_uc, bioma)` onde `area_ha > 0`, derivada por
`UNPIVOT` na fonte de staging. `bioma` é categórica legível (`Amazônia`,
`Caatinga`, …) — sem dicionário (o valor já é o rótulo).

**Cardinalidade real (empírica 2026-05-30):** 81 UCs têm área em >1 bioma — caso
de uso concreto pro long.

**O que permanece na achatada:** os **agregados** `area_soma_biomas` e
`area_soma_biomas_continental` (totais, não a quebra por bioma) ficam na
`unidade_conservacao`. A silver (parquet) mantém as 6 colunas wide — a reshape é
decisão de modelagem gold, não de tratamento.

**Outras candidatas avaliadas e descartadas (empírico):** `sigla_uf` é multi-UF
(38 UCs) mas **derivável** de `uc_municipio` ⋈ `municipio` — não vira tabela.
`mosaico` é single-valor (0 separadores). `sitios_ramsar`/`sitios_patrimonio_mundial`
são esparsos demais (2 multi cada). `orgao_gestor`/`outros_atos_legais` são texto
livre, não normalizam limpo.

**Testes:** `unique_combination_of_columns (id_uc, bioma)`, `not_null` em
`id_uc`/`bioma`/`area_ha`, `accepted_values` nos 6 biomas, `accepted_range`
(`area_ha >= 0`).

## Adendo: tabela `dicionario` (2026-05-30)

Além das duas tabelas-modelo e do diretório `municipio`, o dataset ganhou uma
quarta tabela: o **dicionário** (seed `dicionario.csv`), no padrão BD — uma única
tabela por base que mapeia `(id_tabela, nome_coluna, chave) → valor`.

**Escopo decidido:** cobre **apenas as colunas `indicador_*`** da
`unidade_conservacao` (8 colunas, 16 linhas: `0`/`1` → significado; `indicador_fonte_shp`
mapeia `0→Ato legal`, `1→Geoprocessamento (SHP)`, os demais `0→Não`/`1→Sim`).

**Por que só os `indicador_*`:** as outras categóricas (`esfera_administrativa`,
`grupo`, `categoria_manejo`, `bioma_declarado`) já são armazenadas como **texto
legível**, não código — no estilo BD, quando o valor já é o rótulo, não há código
a traduzir, então não entram no dicionário. Só os `indicador_*` guardam código
(`0`/`1`) com significado implícito.

**Sub-decisões:** `cobertura_temporal` deixada **vazia** (dataset é snapshot CNUC
2026-03, sem partição temporal — o mapa `0→Não` é invariante no tempo).
`categoria_iucn` (`Ia`/`II`/…) **adiada** — daria pra mapear aos nomes oficiais
IUCN, mas exige fonte dos rótulos; fica como melhoria futura. **Não** re-codificar
as categóricas que já são texto (seria trabalho a mais que piora a legibilidade).

Ver `manual_estilo_bd.md` §Dicionários e §Diretórios (a distinção dicionário ≠
diretório), e [[diretorio-ibge]].

## Quando reconsiderar

- Se o reviewer pedir uma tabela única "denormalizada" pra simplificar consulta — improvável, mas possível.
- Se aparecer demanda de extensão (ex: relação `uc_bioma` n:n também) — aí a decisão de star vira a regra do projeto.

---

## Referências

- `docs/exploracao-bruto.md` — Fase D.3 e D.5 (separador, distribuição).
- `dicionario-de-dados-unidades-de-conservacao.pdf` — formato oficial do campo `Municípios Abrangidos`.
- [[ucs-marinhas]] — decisão complementar.
- [[normalizacao-nomes]] — algoritmo do join CNUC ↔ IBGE.
- [[diretorio-ibge]] — fonte do `id_municipio`.
- [[tabela-externa-staging]] — como a gold lê o parquet do bucket (source dbt-duckdb).
- `docs/superpowers/plans/2026-05-28-tratamento.md` §0.1.
