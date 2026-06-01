# Decisão: tratamento de UCs marinhas

**Data:** 2026-05-28
**Sub-projeto afetado:** #2 (tratamento) e #4 (modelo dbt)
**Status:** Decidido

---

## Contexto

Parte das UCs do CNUC são **marinhas** (reservas no oceano, área marinha exclusiva).

> **Correção empírica (2026-05-29):** a premissa original deste doc era que UCs marinhas teriam `Municípios Abrangidos` **vazio**. A inspeção do dado real desmente isso: das 229 UCs com `Mar Territorial = Sim`, **todas** trazem municípios costeiros abrangidos (`Municípios Abrangidos` tem **0 nulls e 0 vazios** no dataset inteiro). Ou seja, **não existe UC sem município** aqui — o cenário que esta decisão buscava resolver é teórico neste dataset. As consequências práticas estão revistas abaixo; a decisão (e) de manter `indicador_marinha` segue válida, mas como **flag analítica**, não como mecanismo de exclusão da ponte.

A preocupação original era com a regra do desafio: `not_null(id_municipio)` e `relationships(id_municipio)` precisam passar nos testes dbt obrigatórios. Com municípios costeiros presentes em todas as UCs, esses testes passam naturalmente — toda UC gera ≥1 par válido na ponte.

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

**Como derivar:** a partir das colunas `Mar Territorial` (Sim/Não) e/ou `Área Marinha` (> 0) do CSV bruto. **Não** usar `Municípios Abrangidos` vazio como sinal — esse campo nunca é vazio neste dataset (ver Correção empírica acima). O CSV bruto já traz `Mar Territorial`, `Município Costeiro` e `Município Costeiro + Área Marinha` como indicadores prontos — provável caminho mais direto que recalcular de `Área Marinha`.

---

## Justificativa

1. **Casamento natural com star schema** ([[granularidade]]). Sem essa combinação, qualquer opção resolve um problema mas cria outro.
2. **Testes dbt obrigatórios passam sem custom logic.** A ponte tem só pares válidos; a principal não precisa de teste `relationships`.
3. **Preserva todas as UCs no inventário.** Marinhas aparecem na `unidade_conservacao` normalmente — só não têm linha na ponte.
4. **Flag é analiticamente útil.** Permite responder "quantas UCs marinhas?" sem precisar inferir de outra coluna.

---

## Consequências / implicações

- **Tratamento (sub-projeto #2):** computar `indicador_marinha` durante a transformação, derivado de `Mar Territorial` (ou `Área Marinha > 0`) — **não** de `municipios_abrangidos` vazio, que não ocorre neste dataset.
- **Ponte:** **não filtrar** UCs marinhas — elas têm municípios costeiros e devem entrar no `uc_municipio` normalmente. O explode universal (todas as UCs → UNNEST → JOIN IBGE) já cobre o caso; nenhuma UC fica sem `id_municipio` por ser marinha. Manter o passo de logar/dropar pares sem match IBGE (typos, municípios novos), mas isso é ortogonal à condição marinha.
- **`schema.yml`:** marcar `indicador_marinha` como `not_null` (toda UC tem essa flag, mesmo continental). Documentar a derivação na descrição da coluna.
- **Estilo BD:** `indicador_` é prefixo permitido pra booleanas (ver o manual de estilo da BD). ✅

---

## Quando reconsiderar

- Se o reviewer pedir que UCs marinhas tenham vínculo com **município costeiro adjacente** (algumas marinhas têm essa relação via Zona Costeira). Aí precisa entrar na ponte com `id_municipio` do costeiro mais próximo — e a flag perde sentido isolado.
- Se aparecer dado de "município marítimo" (entidade hipotética) no IBGE — não existe hoje.

---

## Referências

- `docs/exploracao-bruto.md` — Fase D.4 (UCs sem município).
- `dicionario-de-dados-unidades-de-conservacao.pdf` — descrição de `Área Marinha`.
- [[granularidade]] — depende dessa.
- Manual de estilo da BD — prefixo `indicador_` permitido.
