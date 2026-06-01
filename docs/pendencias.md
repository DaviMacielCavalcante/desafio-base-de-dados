# Pendências

Registro central de itens em aberto — diferenciais não obrigatórios e refatorações
candidatas. Os sub-projetos #1–#5 estão concluídos. O que sobra é bônus e melhoria,
não bloqueia a entrega.

---

## Diferenciais — sub-projeto #6 (bônus, não obrigatórios)

Diferenciais opcionais do desafio. Somam pontos, nenhum é obrigatório.

**Concluídos:**

- ✅ **Testes unitários do `transform.py`** — 17 testes (pytest) cobrindo
  `build_municipios_struct`, `cast_columns`, `normalize_*` e os guard-rails.
  Rodam via `make test`.
- ✅ **CI (GitHub Actions)** — workflow no push/PR roda `make lint`, `typecheck`,
  `test` e `dbt parse`. Gate local reforçado por hook `pre-commit` (ruff + mypy).
- ✅ **`max_date` / metadata externa** — `write_metadata()` consulta o warehouse de
  prod e grava `data/metadata/<dataset>.json` com `max(ano_ato_legal_mais_recente)`,
  contagem de linhas e timestamp; também registra um markdown artifact no Prefect.
- ✅ **Observabilidade / logs estruturados** — `print()` do `load.py` trocados por
  `get_run_logger()` (upload, ensure_bucket, promote) + markdown artifact do
  `write_metadata`. Logs aparecem nos task runs do Prefect.
- ✅ **Particionamento / clustering** — decisão documentada no README §Decisões de
  arquitetura: não particiona (volume ~3.4k linhas + DuckDB não particiona como BQ).

**Em aberto:** nenhum — todos os diferenciais opcionais cobertos.

---

## Refatorações candidatas

| Item | Onde | Resumo |
|---|---|---|
| **Consolidar `dbt build`** | flow `pipe.py` | Hoje há `dbt seed` + `run` + `test` separados por target (repetitivo). `dbt build --target dev` faz seed+run+test num comando, com gate embutido. Detalhes e trade-off em [`estrategia-atualizacao.md`](decisoes/estrategia-atualizacao.md) §Pendência de refatoração. Mantido separado por ora (gate mais explícito). |
