# Decisão: ferramenta de diagnóstico do arquivo bruto

**Data:** 2026-05-28
**Sub-projeto afetado:** #2 (exploração e tratamento)
**Status:** Decidido

---

## Contexto

Antes de carregar o CSV do MMA em Polars, precisamos descobrir características do arquivo (encoding, separador, contagem de linhas, presença de header, mojibake). Carregar primeiro e tentar adivinhar depois é caminho rápido pra corromper acentos silenciosamente — `pl.read_csv('arquivo.csv')` com default `utf-8` num arquivo `latin-1` lê errado sem falhar.

A pergunta: **com qual ferramenta inspecionar o arquivo bruto antes de qualquer parser interpretar?**

A exploração será conduzida em um notebook `.ipynb` (preferência do Davi). A decisão se reflete na organização desse notebook.

---

## Opções consideradas

### A) Shell direto no notebook (`!comando` ou `%%bash`)

**Como funciona:** Jupyter/IPython suporta nativamente comandos shell via prefixo `!` (linha única) ou magic `%%bash` (célula inteira). Comandos como `file -i`, `wc -l`, `head -c 500` rodam num subshell e o output aparece inline.

**Prós:**
- Tudo num arquivo só (exploração + diagnóstico).
- Iterativo — rerroda célula quando quiser.
- Output visível inline, fácil de revisitar.
- Sem coordenação entre arquivos.
- Utilitários Unix (`file`, `wc`, `head`, `iconv`) são imbatíveis pra encoding/contagem: rápidos, sem parser por trás.

**Contras:**
- Output do shell é texto solto — se for usar valor depois (ex: `charset='latin-1'` no `read_csv`), precisa parsear stdout.
- Mistura "diagnóstico cru" com "análise de DataFrame" no mesmo notebook — pode poluir.
- Não roda em Windows nativo (mas o projeto é Linux-first).

### B) Script `.sh` separado que gera `.txt` chave=valor

**Como funciona:** um arquivo `scripts/diagnose_raw.sh` faz os mesmos comandos, parseia, e grava algo como `encoding=iso-8859-1\nlinhas=3421\nseparador=;` em `reports/raw_diag.txt`. O notebook lê esse txt.

**Prós:**
- Script é reprodutível fora do notebook (CI, terminal, cron).
- Output estruturado → fácil parsear (dict direto).
- Separação clara: script diagnostica, notebook analisa.
- Versionável como ferramenta do projeto.

**Contras:**
- Overhead de manter 2 arquivos pra uma sessão exploratória.
- Se precisar mais info, edita script + reroda + reload no notebook.
- Pra arquivo único explorado uma vez, é over-engineering.
- Não roda em Windows nativo.

### C) Python puro (sem shell)

**Como funciona:** usar bibliotecas como `chardet` ou `charset-normalizer` (detecção de encoding), `pathlib.Path.read_bytes()` (primeiros bytes), `sum(1 for _ in open(p))` (contagem de linhas). Tudo dentro do notebook ou de um módulo Python.

**Prós:**
- Sem subprocess, sem parse de stdout, valores tipados direto.
- Cross-platform (funciona em Linux/Mac/Windows).
- Integrável na pipeline (validação automática a cada run no Prefect).

**Contras:**
- Mais código — `chardet` precisa abrir arquivo, ler N bytes, retornar dict.
- `chardet` às vezes erra em arquivos curtos/ambíguos — heurística do `file` Unix é geralmente mais confiável pra latin-1.
- Mais uma dep (`chardet` ou `charset-normalizer`) no `pyproject.toml`.

---

## Tabela comparativa aplicada ao caso

| Opção | Adequada aqui? | Motivo |
|---|---|---|
| (A) Shell no notebook | **Sim** | Sessão exploratória única, descartável; menor atrito; output inline no ipynb |
| (B) Script + .txt | Não | Over-engineering pra exploração one-shot; benefício só apareceria em uso recorrente |
| (C) Python puro | Possível, mas não agora | Faz sentido pra validação automática **dentro da pipeline** (sub-projetos #5/#6), não pra diagnóstico inicial |

---

## Decisão

**Escolha: (A) Shell direto no notebook**, via `%%bash` (célula inteira) ou `!comando` (linha única).

**Onde:** notebook `explorer.ipynb` na raiz do projeto, ignorado via `*.ipynb` no `.gitignore`. Achados consolidados em `docs/exploracao-bruto.md` (versionado).

**Quando usar Opção C:** quando o sub-projeto #5 implementar validação automática do arquivo bruto no flow Prefect (ex: abortar se encoding mudar entre runs). Aí `charset-normalizer` entra como dep, e a lógica vive dentro de uma task Prefect — não num script shell.

---

## Justificativa

1. **Atrito mínimo.** Não precisa criar/coordenar 2 arquivos pra uma sessão que vai rodar uma vez.
2. **Os utilitários Unix são os melhores na sua camada.** `file -i` lê os bytes magic e detecta encoding com heurística madura; `chardet` é programático mas erra mais em arquivos curtos.
3. **Output inline no notebook** = registro permanente da exploração, sem precisar abrir um `.txt` separado.
4. **O notebook é descartável.** Os achados vão pra `docs/exploracao-bruto.md` em markdown — o notebook em si não precisa virar artefato versionado.

---

## Consequências / implicações

- **Estrutura do notebook:**
  1. Setup (imports, paths)
  2. Célula `%%bash` com `file`, `wc`, `head` — diagnóstico do arquivo
  3. Markdown com anotações dos achados
  4. Carregar no Polars com encoding correto (descoberto na #2)
  5. `df.glimpse()` / `df.head(20)`
  6. Cada pergunta da §5 do plano vira 1-2 células
- **Versionamento:** o `.ipynb` em si **não** vai pro git (outputs grandes, ruim pra diff). Os achados vão pra `docs/exploracao-bruto.md`.
- **Local do notebook:** raiz do projeto, arquivo `explorer.ipynb` (decisão tomada na execução — só 1 notebook, não justifica pasta dedicada).
- **Sem nova dep** — Polars já entra pra Fase D em diante; `chardet` fica de fora por enquanto.

---

## Quando reconsiderar

- Se o arquivo bruto começar a mudar de encoding/separador entre versões da fonte → precisa de validação automática → migra pra Opção C dentro de uma task Prefect.
- Se a exploração for repetida (ex: dataset novo, mesmo padrão) → vale extrair script reutilizável (Opção B).
- Se o projeto virar cross-platform (Windows) → Opção C fica obrigatória.

---

## Referências

- [IPython magics: `%%bash`, `!`](https://ipython.readthedocs.io/en/stable/interactive/magics.html)
- [`file` man page](https://man7.org/linux/man-pages/man1/file.1.html)
- [`chardet` GitHub](https://github.com/chardet/chardet) — alternativa Python (não adotada agora)
- `docs/superpowers/plans/2026-05-28-tratamento.md` §0.5 (encoding) e Fase B do guia de exploração
