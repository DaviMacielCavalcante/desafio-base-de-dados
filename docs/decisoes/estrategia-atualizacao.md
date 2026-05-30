# Decisão: estratégia de atualização da tabela `unidade_conservacao`

**Data:** 2026-05-28
**Sub-projeto afetado:** #4 (modelo dbt) e #5 (flow Prefect)
**Status:** Decidido

---

## Contexto

O `README-desafio.md` exige:
> "A tabela final reflita o status mais recente das unidades de conservação publicado na fonte. A estratégia de atualização (full refresh com overwrite, append incremental, snapshot, merge por chave, etc.) fica a seu critério — escolha a abordagem que considerar mais adequada para o volume e a cadência de mudanças desse conjunto, e justifique a decisão no README da sua solução. Espera-se apenas que rodar a pipeline mais de uma vez não corrompa a tabela."

Em outras palavras: tem que **escolher** uma estratégia, **justificar**, e garantir **idempotência**.

## Características do dado (entram na decisão)

- **Volume:** ~3.4k UCs federais + estaduais (3.421 no snapshot atual). Pequeno.
- **Cadência de mudança:** muito baixa. UCs são criadas por decreto/lei (dezenas/ano, não diárias).
- **Histórico:** o desafio pede explicitamente "status mais recente" — **não pede** série temporal de mudanças.
- **Custo:** zero (DuckDB local; e mesmo em BigQuery, com 3.4k linhas, irrelevante).
- **Tolerância a erro:** se uma run trouxer lixo, queremos que a próxima limpe — não acumular.

---

## Opções consideradas

### a) Full refresh com overwrite

**Como funciona:** a cada run, apaga a tabela inteira e reescreve do zero a partir do snapshot atual.

**Prós:**
- Simples — sem estado, sem chave de update, sem comparação.
- Idempotente por construção.
- Erros não se acumulam: uma run com lixo é limpa pela seguinte.
- Em dbt, é o default (`materialized='table'`).

**Contras:**
- Em datasets muito grandes seria caro (reprocessar tudo).
- Não preserva histórico — quem quiser saber "como estava em 2024-03" não consegue.

**Quando faz sentido:** dataset pequeno + reflete estado atual + sem necessidade de histórico.

---

### b) Append incremental

**Como funciona:** a cada run, identifica registros novos (por `data_criacao > última_processada`, ou chave inexistente) e só insere o que é novo.

**Prós:**
- Rápido em datasets grandes (não reprocessa o que já está lá).

**Contras:**
- **Não detecta mudanças.** Se uma UC mudar de nome ou área, mantém o valor antigo.
- **Não detecta deleções.** Se uma UC for descadastrada, continua na tabela pra sempre.
- Quebra a regra "status mais recente" do desafio.
- Exige rastreio de "última run" — estado externo ao dado.

**Quando faz sentido:** dado verdadeiramente imutável (eventos, logs, transações).

---

### c) Snapshot (SCD Type 2, estilo `dbt snapshot`)

**Como funciona:** cada linha ganha `valid_from` / `valid_to`. Quando algo muda, fecha a linha antiga e abre uma nova com `valid_to = NULL`.

**Prós:**
- Preserva histórico completo das mudanças.
- Permite responder "como estava em uma data X?".

**Contras:**
- Complexidade alta — exige `unique_key` + `strategy` (`timestamp` ou `check`) + tabela cresce com mudanças.
- Para "estado atual" sempre precisa filtrar `WHERE valid_to IS NULL`.
- Brief não pede histórico — overkill.

**Quando faz sentido:** o histórico de mudanças tem valor analítico (auditoria, série de SCDs).

---

### d) Merge por chave (upsert)

**Como funciona:** chave primária define identidade da linha. `MERGE INTO ... ON id_uc = ...` (SQL upsert) — atualiza colunas que mudaram, insere novas, opcionalmente deleta as sumidas (`WHEN NOT MATCHED BY SOURCE`).

**Prós:**
- Reflete estado atual.
- Eficiente em datasets grandes (não rescreve linhas inalteradas).
- Lida com deleções (com cláusula adequada).

**Contras:**
- Mais complexo que overwrite — precisa definir chave, lógica de deleção, regras de match.
- Em volume pequeno o ganho de performance é zero ou negativo.
- Em BigQuery cobra por linha varrida — em volumes pequenos pode até perder pra overwrite.

**Quando faz sentido:** dataset grande + reflete estado atual + custo de full refresh é proibitivo.

---

## Tabela comparativa aplicada ao caso

| Estratégia | Adequada aqui? | Motivo |
|---|---|---|
| (a) Full refresh + overwrite | **Sim** | Volume pequeno, sem histórico, idempotência trivial. |
| (b) Append incremental | Não | Quebra "status mais recente" (não detecta deleção/mudança). |
| (c) Snapshot | Não | Overkill — brief não pede histórico. |
| (d) Merge por chave | Possível mas ruim | Mais complexo que (a), ganho zero no volume atual. |

---

## Decisão

**Escolha: (a) Full refresh com overwrite.**

Implementação em dbt: `materialized='table'` (default).

Implementação em Python (sub-projeto #2): tratamento puramente funcional — mesma entrada → mesma saída, sem timestamp em nome de arquivo, sem aleatoriedade.

Implementação em flow (sub-projeto #5): sequência `download → trata → upload → dbt run → dbt test`. Sem comparação com versão anterior, sem lógica de "merge".

---

## Justificativa (a entrar no README final)

1. **Volume é desprezível** (~3.4k linhas). Custo de reprocessar é nulo.
2. **Brief pede "status mais recente"** — não há necessidade de histórico de mudanças.
3. **Cadência de mudança é baixa** (dezenas/ano), então rodar semanal/mensal cobre folgadamente.
4. **Idempotência é trivial**: mesmo input → mesma tabela final, sem efeitos colaterais.
5. **Erros não acumulam**: se uma run trouxer lixo, a próxima limpa.

---

## Consequências / implicações

- O modelo dbt em `models/br_mma_unidades_conservacao/...` usa `{{ config(materialized='table') }}` (ou nada — é o default).
- O tratamento Python **tem que ser determinístico**. Sem `datetime.now()` em coluna, sem ordenação não-determinística, sem `set()` onde a ordem importa.
- O flow Prefect **não precisa** de lógica de "última run" — sempre baixa o snapshot atual e reprocessa.
- Se um dia quisermos histórico (ex: "quantas UCs existiam em 2024?"), a única opção será (c) snapshot, e seria uma refatoração maior. Por enquanto não há demanda.

---

## Quando reconsiderar

Esta decisão pode precisar mudar se:

- O volume crescer muito (10×+) — provavelmente não vai, mas vale ter no radar.
- Surgir demanda explícita por histórico (perguntas tipo "como estava o cadastro em 2023?").
- A fonte passar a publicar deltas incrementais em vez de snapshot completo — aí (b) começa a fazer sentido.

---

## Referências

- `README-desafio.md` — trecho citado no §Contexto.
- `REVISAO.md` — critérios de aceite (idempotência é regra explícita).
- [dbt docs — materializations](https://docs.getdbt.com/docs/build/materializations).
- [dbt docs — snapshots](https://docs.getdbt.com/docs/build/snapshots).
