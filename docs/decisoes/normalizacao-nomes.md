# Decisão: algoritmo de normalização de nomes de município

**Data:** 2026-05-28
**Sub-projeto afetado:** #2 (tratamento)
**Status:** Decidido

---

## Contexto

O CNUC traz o nome de município no campo `Municípios Abrangidos` em **caixa alta + acentos + sufixo `(SIGLA_UF)`**, ex: `"CARAGUATATUBA (SP)"`, `"SÃO PAULO (SP)"`. Quando UC abrange múltiplos municípios, o separador é vírgula (`,`), conforme dicionário oficial.

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

Antes da normalização:

1. **Split por vírgula** em `Municípios Abrangidos` (separador confirmado pelo dicionário). Cuidado: trim em cada elemento depois do split.
2. **Split por vírgula** em `UF` também — UCs que cruzam estados têm formato `"AM, PA"`.
3. **Explode** depois do split — gera uma linha por par `(codigo_uc, municipio_normalizado, sigla_uf)`.

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
- **Função utilitária:** em `pipelines/transform.py` ou módulo dedicado (`pipelines/normalize.py`). Aplicada uma vez na carga do seed IBGE (sub-projeto #4) e uma vez no tratamento CNUC (sub-projeto #2).
- **Auditoria:** o relatório de não-casados vira artefato do flow Prefect (sub-projeto #5) — salvar em `data/audit/` ou similar.

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
