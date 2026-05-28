# Decisão: granularidade da tabela `unidade_conservacao`

**Data:** 2026-05-28
**Sub-projeto afetado:** #2 (tratamento) e #4 (modelo dbt)
**Status:** Decidido

---

## Contexto

Uma UC pode estar em mais de um município. O CNUC representa multi-municipalidade na coluna `Municípios Abrangidos` com separador interno `,` (confirmado pelo dicionário oficial — ver `docs/exploracao-bruto.md`).

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

**Escolha: (c) star schema com tabela ponte `uc_municipio`.**

Estrutura:

| Tabela | Granularidade | Tem `id_municipio`? |
|---|---|---|
| `unidade_conservacao` | 1 linha por UC | Não |
| `uc_municipio` | 1 linha por par `(codigo_uc, id_municipio)` | Sim |

---

## Justificativa

1. **Testes dbt obrigatórios fluem naturalmente.** `not_null(id_municipio)` e `relationships(id_municipio)` vivem na ponte, onde a coluna é sempre escalar e não-nula.
2. **UCs marinhas resolvem-se sozinhas** — não entram na ponte (não têm município). Sem sentinel, sem NULL, sem custom test. Ver [[ucs-marinhas]].
3. **Sem duplicação de atributos da UC** (nome, ano, área total). Manutenção é mais simples; mudança na descrição da UC altera uma linha só.
4. **Modelo n:n é honesto sobre a relação** — UC e município se relacionam muitos-pra-muitos no mundo real (UCs grandes em vários municípios, municípios com várias UCs).

---

## Consequências / implicações

- **dbt:** dois models — `models/br_mma_unidades_conservacao/unidade_conservacao.sql` e `models/br_mma_unidades_conservacao/uc_municipio.sql`.
- **`schema.yml`:** testes `unique` + `not_null` em `codigo_uc` da principal. Testes `not_null` + `relationships` em `id_municipio` da ponte. Teste de **chave composta** `(codigo_uc, id_municipio)` única na ponte.
- **Tratamento (sub-projeto #2):** o parquet de saída pode ser único (com a relação já explodida) ou dois (principal + ponte). Decidir na implementação — provavelmente dois parquets em pastas separadas dentro de `data/staging/...`.
- **Documentação:** o reviewer vai esperar uma menção explícita ao star schema no README e/ou `schema.yml`.

---

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
- `docs/superpowers/plans/2026-05-28-tratamento.md` §0.1.
