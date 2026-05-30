# Decisão: algoritmo de normalização de nomes de município

**Data:** 2026-05-28
**Sub-projeto afetado:** #2 (tratamento)
**Status:** Decidido

---

## Contexto

O CNUC traz o nome de município no campo `Municípios Abrangidos` em **caixa alta + acentos + sufixo `(SIGLA_UF)`**, ex: `"CARAGUATATUBA (SP)"`, `"SÃO PAULO (SP)"`. Quando UC abrange múltiplos municípios, o separador é `" - "` (espaço-hífen-espaço), ex: `"CAMANDUCAIA (MG) - EXTREMA (MG)"`. (O dicionário oficial diz "vírgula", mas isso só vale para a coluna `UF`; no dado real `Municípios Abrangidos` usa `" - "` — ver [[granularidade]].)

A tabela de diretório do IBGE ([[diretorio-ibge]]) traz o nome canônico em **caixa inicial maiúscula + acentos**, ex: `"Caraguatatuba"`, `"São Paulo"`. Os formatos não casam diretamente.

Regra rígida do desafio (`REVISAO.md`): **sem fix list manual.** Não pode ter dicionário `{"sao thome das letras": "São Tomé das Letras"}` no código — o match tem que ser por algoritmo reproduzível.

A pergunta: **qual algoritmo de normalização garante o match em ~100% dos casos sem fix list?**

---

## Decisão

**Função de normalização** (aplicada nos dois lados do join — CNUC e IBGE):

1. **Trim** — remove whitespace nas pontas.
2. **Remover sufixo `(SIGLA_UF)`** — regex `r'\s*\([A-Z]{2}\)\s*$'`. **Só aplicado ao lado CNUC** (o IBGE não tem esse sufixo).
3. **Remover acentos / caracteres especiais** — `unidecode` ou equivalente. `ç` → `c`, `ã` → `a`, etc.
4. **Lowercase** — `.lower()`.
5. (Opcional, se aparecer ruído) **Colapsar whitespace interno** — `re.sub(r'\s+', ' ', s)` pra eliminar espaços duplos.

**Não fazer:**
- Não substituir espaços por `_` — perde informação e não ajuda o match.
- Não remover preposições (`de`, `da`, `dos`) — alteraria o nome real (`Foz do Iguaçu` não é igual a `Foz Iguaçu`).
- Não usar fuzzy match (Levenshtein, etc.) — não-determinístico, gera ambiguidade.

**Chave de match:** `(nome_normalizado, sigla_uf)`. A UF entra na chave porque o Brasil tem municípios homônimos em estados diferentes (ex: "Bom Jesus" existe em vários estados).

---

## Tratamento do multi-valor

Histórico: a versão anterior previa **split + explode em Python** dentro da silver, gerando uma linha por par `(codigo_uc, municipio_normalizado, sigla_uf)`. A decisão de granularidade foi revisada em 2026-05-29 (ver [[granularidade]]) — a explosão agora acontece **no dbt (gold)** via `UNNEST`, não em Python.

**Fluxo atual:**

1. Em Python (silver, `build_municipios_struct`):
   - **Split por `" - "`** em `Municípios Abrangidos` → lista de strings.
   - Trim em cada elemento.
   - **Extrair `(SIGLA_UF)`** do final de cada elemento → `sigla_uf` escalar; resto vira `nome` com caixa preservada.
   - **Computar `nome_norm`** aplicando a função de normalização ao `nome`.
   - Montar `STRUCT { nome, sigla_uf, nome_norm }` por elemento.
   - Resultado: coluna `municipios_abrangidos: ARRAY[STRUCT(nome, sigla_uf, nome_norm)]`.
2. No dbt (gold, model `uc_municipio`):
   - `UNNEST(municipios_abrangidos)` para gerar 1 linha por par.
   - `LEFT JOIN` com `municipio` (ou view derivada `municipio_norm`) por `(nome_norm, sigla_uf)` → resolve `id_municipio`.

**Por que `nome_norm` é pré-computado em Python:** DuckDB não tem `unaccent` nativo (requer extensão `icu`). Mantendo a normalização em Python, o JOIN no dbt vira comparação simples de igualdade — sem dependência de extensão Polars/DuckDB e sem risco de divergência entre normalizações em linguagens diferentes.

**`UF` (multi-valor da UC):** continua como string multi-valor na principal (`"AM, PA"`), conforme decidido — não é explodida nem normalizada, é atributo documental.

---

## Justificativa

1. **Determinístico** — mesma entrada, mesma saída. Reroda sem variação.
2. **Reproduzível** — qualquer pessoa que olhe o algoritmo entende e replica. Sem "fix list mágica".
3. **Aplicado dos dois lados** — garante simetria. Se `IBGE.normalize("São Paulo") == CNUC.normalize("SÃO PAULO (SP)")`, o match acontece.
4. **`unidecode` é solução padrão** — biblioteca madura, lida com cantos do unicode brasileiro (`ç`, `ñ`, `á`, ligaduras raras).

---

## Estratégia para casos que não casarem

Mesmo com algoritmo bom, alguns nomes podem não casar (typos no CNUC, municípios extintos/criados depois da última atualização do diretório, etc.). **Plano:**

1. Após o join, **logar** os pares `(codigo_uc, nome_municipio_cnuc, sigla_uf)` que ficaram sem `id_municipio`.
2. **Investigar manualmente** o relatório de não-casados.
3. Se forem typos do CNUC, **reportar pro órgão** mas não corrigir no nosso código.
4. Se forem municípios novos não cobertos pelo diretório, **atualizar o seed** (não o algoritmo).
5. Idealmente: **abortar a pipeline** se mais de N% não casar (definir N — sugestão: 1%). Vira critério de aceite.

---

## Consequências / implicações

- **Dep nova:** `unidecode` (ou `anyascii`). Adicionar via `uv add unidecode`. Leve, sem deps secundárias.
- **Função utilitária `normalize_municipio(s) -> str`** em `pipelines/transform.py` ou módulo dedicado (`pipelines/normalize.py`). Aplicada:
  - **No tratamento CNUC (Python)** — dentro de `build_municipios_struct`, computando o campo `nome_norm` de cada elemento do array.
  - **No seed `municipio` ou model dbt intermediário** — a forma exata é decidida em [[diretorio-ibge]]. A garantia: o `nome_norm` no lado IBGE precisa ser produzido pelo **mesmo algoritmo** que o lado CNUC.
- **Auditoria:** o relatório de não-casados vira artefato do flow Prefect (sub-projeto #5) — salvar em `data/audit/` ou similar. Implementação: query no dbt que conta `WHERE id_municipio IS NULL` no model `uc_municipio` e publica métrica.

---

## Quando reconsiderar

- Se a taxa de não-casados for > 5% mesmo após investigação manual — algoritmo está perdendo padrão sistemático. Revisar.
- Se aparecer caso de homonímia dentro do mesmo estado (improvável no Brasil, mas teoricamente possível com renomeações) — chave `(nome, uf)` não basta, precisa de `(nome, uf, regiao_imediata)` ou similar.

---

## Referências

- `docs/exploracao-bruto.md` — Fase D.3 (formato do `Municípios Abrangidos`).
- `manual_estilo_bd.md` — regra de variáveis categóricas (inicial maiúscula com acentos no valor final).
- [[diretorio-ibge]] — fonte do nome canônico do município.
- [[granularidade]] — explode acontece dentro do contexto da tabela ponte.
- `docs/superpowers/plans/2026-05-28-tratamento.md` §0.4.
