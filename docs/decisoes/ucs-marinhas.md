# Decisão: tratamento de UCs marinhas

**Data:** 2026-05-28
**Sub-projeto afetado:** #2 (tratamento) e #4 (modelo dbt)
**Status:** Decidido

---

## Contexto

Parte das UCs do CNUC são **marinhas** (reservas no oceano, área marinha exclusiva). Não têm município associado — o campo `Municípios Abrangidos` aparece vazio.

Isso colide diretamente com a regra do `REVISAO.md`: `not_null(id_municipio)` e `relationships(id_municipio)` precisam passar nos testes dbt obrigatórios.

A pergunta: **como representar UCs marinhas sem quebrar os testes nem perder a informação?**

---

## Opções consideradas

### a) Sentinel value (`id_municipio = "9999999"` ou similar)

**Prós:**
- Mantém todas as UCs na mesma tabela.
- `not_null` passa.

**Contras:**
- Quebra `relationships(id_municipio → diretório IBGE)` — o sentinel não existe no diretório.
- "Mente" sobre o dado — qualquer agregação por município incluiria o lixo.

### b) `id_municipio = NULL` na tabela principal

**Prós:**
- Honesto sobre a ausência.

**Contras:**
- Quebra `not_null`. Precisaria de custom test ou exclusão da regra.

### c) Excluir UCs marinhas da tabela final

**Prós:**
- Testes passam sem custom logic.

**Contras:**
- **Perde dado** — marinhas são UCs válidas, deveriam aparecer no inventário.
- Vai contra o propósito da tabela (status atual de **todas** as UCs).

### d) Tabela separada `unidade_conservacao_marinha`

**Prós:**
- Cada tabela tem schema próprio.

**Contras:**
- Duas tabelas com 95% do schema igual.
- "Quantas UCs no Brasil?" precisa `UNION` toda vez.

### e) Flag `indicador_marinha` + exclusão da ponte (n:n)

**Como funciona:** combina com a decisão de star schema ([[granularidade]]).

- Tabela `unidade_conservacao`: tem coluna `indicador_marinha` (INT 0/1).
- Tabela `uc_municipio` (ponte): UCs marinhas **não aparecem** (não têm município).

**Prós:**
- `not_null(id_municipio)` e `relationships` rodam **só na ponte**, onde marinhas não estão → passam limpo.
- Tabela principal preserva todas as UCs (continentais + marinhas).
- Flag descreve a UC de forma analítica útil.
- Sem sentinel, sem NULL onde precisa de chave, sem `UNION`.

**Contras:**
- Depende da arquitetura star schema (já adotada).

---

## Decisão

**Escolha: (e) flag `indicador_marinha` na principal + exclusão da ponte.**

Coluna nova:

| Coluna | Tipo | Significado |
|---|---|---|
| `indicador_marinha` | `INT64` (0/1) | 1 se a UC tem área marinha e não tem município associado |

**Como derivar:** a partir da coluna `Área Marinha` (presente no CSV bruto) e/ou `Municípios Abrangidos` vazio. Definir a regra exata no tratamento (sub-projeto #2 implementação).

---

## Justificativa

1. **Casamento natural com star schema** ([[granularidade]]). Sem essa combinação, qualquer opção resolve um problema mas cria outro.
2. **Testes dbt obrigatórios passam sem custom logic.** A ponte tem só pares válidos; a principal não precisa de teste `relationships`.
3. **Preserva todas as UCs no inventário.** Marinhas aparecem na `unidade_conservacao` normalmente — só não têm linha na ponte.
4. **Flag é analiticamente útil.** Permite responder "quantas UCs marinhas?" sem precisar inferir de outra coluna.

---

## Consequências / implicações

- **Tratamento (sub-projeto #2):** computar `indicador_marinha` durante a transformação. Regra a definir mas provavelmente: `(area_marinha > 0 AND municipios_abrangidos IS NULL)` ou `(municipios_abrangidos IS NULL)` simples.
- **Ponte:** filtrar UCs marinhas antes do explode municipal — ou explodir todas e dropar as que ficarem sem `id_municipio` após o join IBGE.
- **`schema.yml`:** marcar `indicador_marinha` como `not_null` (toda UC tem essa flag, mesmo continental). Documentar a derivação na descrição da coluna.
- **Estilo BD:** `indicador_` é prefixo permitido pra booleanas (ver `manual_estilo_bd.md`). ✅

---

## Quando reconsiderar

- Se o reviewer pedir que UCs marinhas tenham vínculo com **município costeiro adjacente** (algumas marinhas têm essa relação via Zona Costeira). Aí precisa entrar na ponte com `id_municipio` do costeiro mais próximo — e a flag perde sentido isolado.
- Se aparecer dado de "município marítimo" (entidade hipotética) no IBGE — não existe hoje.

---

## Referências

- `docs/exploracao-bruto.md` — Fase D.4 (UCs sem município).
- `dicionario-de-dados-unidades-de-conservacao.pdf` — descrição de `Área Marinha`.
- [[granularidade]] — depende dessa.
- `manual_estilo_bd.md` — prefixo `indicador_` permitido.
- `docs/superpowers/plans/2026-05-28-tratamento.md` §0.2.
