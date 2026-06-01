# Exploração do arquivo bruto — CNUC

Notas consolidadas da sessão de reconnaissance sobre o arquivo bruto do **Cadastro Nacional de Unidades de Conservação (CNUC)** baixado do portal `dados.gov.br`. Este documento é a referência viva — o notebook em `notebooks/` é o "raw trail" descartável, este aqui sintetiza o que ficou aprendido.

---

## Fonte

| Campo | Valor |
|---|---|
| Portal | https://dados.gov.br/dados/conjuntos-dados/unidadesdeconservacao |
| URL direta do resource | `https://dados.mma.gov.br/dataset/44b6dc8a-dc82-4a84-8d95-1b0da7c85dac/resource/bab6d474-d38d-457c-9092-755f23ebdc76/download/cnuc_2026_03_atualizado.csv` — descoberta inspecionando o portal `dados.mma.gov.br` (espelho CKAN do `dados.gov.br`). Usada como default no `SOURCE_URL` (`.env.example`) e como fallback embutido em `pipelines/extract.py`. |
| Órgão publicador | MMA — Ministério do Meio Ambiente |
| Sistema de origem | CNUC (Cadastro Nacional de Unidades de Conservação) |
| Nome do arquivo baixado | `cnuc_2026_03_atualizado.csv` |
| Formato | CSV |
| Tamanho | 1.3 MB |
| Última atualização | Março/2026 (refletida no nome do arquivo: `2026_03`) |
| Cobertura | UCs **federais + estaduais + municipais** (mais abrangente que o esperado pelo brief — bom) |
| Licença | Creative Commons Attribution (CC-BY) |
| Dicionário de dados | `dicionario-de-dados-unidades-de-conservacao.pdf` na raiz do repo (publicado pelo MMA) |

### Observações sobre o portal

- O portal hospeda **múltiplas versões** do dataset, organizadas por **semestre** desde ~2019. Cada versão é um snapshot do CNUC naquele momento.
- **Decisão (já registrada em `docs/decisoes/estrategia-atualizacao.md`):** usamos apenas o **snapshot mais recente** (`cnuc_2026_03_atualizado.csv`). As versões antigas seriam relevantes apenas se quiséssemos rastrear histórico de mudanças no cadastro — o que o brief explicitamente não pede.
- Se o portal mudar o padrão de nomenclatura ou descontinuar a publicação semestral, ajustar a estratégia de descoberta da URL no flow Prefect (sub-projeto #5).

---

## Validação contra dicionário oficial

O `dicionario-de-dados-unidades-de-conservacao.pdf` documenta **~13 colunas** apenas. O CSV tem **43**. Logo, há ~30 colunas no CSV **não-documentadas oficialmente** — derivadas, auxiliares, ou flags internas do MMA.

### Separador de multi-valor: **depende da coluna**

> **Correção empírica (2026-05-29):** o dicionário generaliza "separados por vírgula", mas a inspeção do dado real mostra separadores **diferentes** por coluna:
> - **`UF`** → vírgula (`,`). Confirmado: 38 linhas com `,`, ex `"RS, SC"`, `"CE, PE, PI"`. ✅ dicionário bate.
> - **`Municípios Abrangidos`** → `" - "` (espaço-hífen-espaço). **0 linhas com vírgula, 587 com `" - "`**, ex `"CAMANDUCAIA (MG) - EXTREMA (MG)"`. ❌ dicionário **não** bate.

Direto do dicionário (texto original, mantido como registro do que a fonte afirma — ver correção acima para o que o dado realmente traz):
- **UF:** *"Quando há mais de uma UF abrangida os valores são separados por vírgula."* → UF **também é multi-valor** (UCs que cruzam estados).
- **Municípios Abrangidos:** *"Quando há mais de um município os valores são separados por vírgula."*

### Valores canônicos por coluna

| Coluna | Valores permitidos | Observação |
|---|---|---|
| Esfera Administrativa | Federal, Estadual, Municipal | DF entra como Estadual |
| Categoria de Manejo | Estação Ecológica; Parque; Monumento Natural; Refúgio de Vida Silvestre; Floresta; Reserva Extrativista; Reserva de Desenvolvimento Sustentável; Reserva de Fauna; Área de Relevante Interesse Ecológico; Área de Proteção Ambiental; Reserva Particular do Patrimônio Natural; Reserva Biológica; Outros | **Dicionário diz "Parque" sem "Nacional"** — explica por que `str.contains("Parque Nacional")` deu zero |
| Categoria IUCN | Ia, Ib, II, III, IV, V, VI | CSV mostrou `Category IV` (inglês com prefixo) — **discrepância de formato** |
| Plano de Manejo | Sim, Não | |
| Conselho Gestor | Sim, Não | |

**Validado:** os valores observados no CSV para `Esfera Administrativa`, `Plano de Manejo` e `Conselho Gestor` batem com o dicionário. `Categoria de Manejo` e `Categoria IUCN` precisam de checagem caso a caso (`Parque Nacional` ≠ `Parque`; `Category IV` ≠ `IV`).

### Colunas oficialmente documentadas (sumário)

`Código_UC`, `Nome da UC`, `Esfera Administrativa`, `Categoria de Manejo`, `Categoria IUCN`, `UF`, `Ano de Criação`, `Ato legal de Criação`, `Outros atos legais`, `Municípios Abrangidos`, `Plano de Manejo`, `Conselho Gestor`, `Área (ha)` + áreas por bioma (Amazônia, Caatinga, Cerrado, Mata Atlântica, Pampa, Pantanal, Área Marinha).

**Estratégia pro modelo final:** manter prioritariamente as colunas documentadas + colunas derivadas estritamente necessárias com justificativa explícita no `schema.yml` (ex: `indicador_marinha`).

### Discrepância nominal menor

- Dicionário: `Código_UC` (underline).
- CSV: `Código UC` (espaço).
- Sem impacto técnico — só registrar.

---

## Diagnóstico do arquivo (Fase B)

| Campo | Valor |
|---|---|
| Encoding | `iso-8859-1` (latin-1) — confirmado por `file -i` |
| Separador | `;` (ponto-e-vírgula) |
| Header presente | Sim — 1 linha de cabeçalho |
| Linhas físicas (`wc -l`) | 3.422 → **3.421 registros** + 1 header |
| Quotes (`"`) | Aparentemente ausentes nos 2 primeiros registros — confirmar na Fase D varrendo o resto do arquivo |
| BOM no início | Ausente (latin-1 não usa BOM) |
| Mojibake visível na amostra | Sim no display do `head` (terminal interpreta latin-1 como utf-8); **não no arquivo em si**. Carregando no Polars com `encoding='iso-8859-1'`, os acentos voltam corretos. |

### Implicação direta pro tratamento

- No Polars: `pl.read_csv('data/raw/cnuc_2026_03_atualizado.csv', encoding='iso-8859-1', separator=';')`.
- Alternativa: converter o arquivo uma vez com `iconv -f latin1 -t utf-8` e trabalhar em utf-8 nativo daqui pra frente. Mais limpo, mas adiciona um passo no pipeline.

---

## Schema (Fase C)

### Colunas brutas (extraídas do header)

| # | Coluna bruta | Observações iniciais |
|---|---|---|
| 1 | `ID_UC` | Identificador interno (ex: `1.045`, `1.047`) — note o **ponto** como separador de milhar/decimal |
| 2 | `Código UC` | Formato `0000.00.1045` — **STRING obrigatório** (zeros à esquerda) — candidato a chave canônica |
| 3 | `Informações Gerais` | Vazio nos 2 exemplos — investigar se sempre vazio (coluna fantasma?) |
| 4 | `Nome da UC` | Em MAIÚSCULAS nos exemplos — vai precisar normalizar caixa (regra BD: inicial maiúscula com acentos) |
| 5 | `Esfera Administrativa` | `Federal` / `Estadual` / `Municipal` — categórica |
| 6 | `Categoria de Manejo` | Categoria SNUC (ex: `Reserva Particular do Patrimônio Natural`) |
| 7 | `Categoria IUCN` | Texto em inglês (ex: `Category IV`) — manter em inglês ou traduzir? |
| 8 | `UF` | Sigla 2 letras (ex: `SP`) — **`sigla_uf` já vem direto, não precisa derivar** |
| 9 | `Ano de Criação` | Inteiro (ex: `2001`, `1995`) — INT64 |
| 10 | `Ano do ato legal mais recente` | Inteiro |
| 11 | `Ato Legal de Criação` | Texto livre (ex: `Portaria 52/2001 de 23/04/2001`) |
| 12 | `Outros atos legais` | Texto livre (ex: `Sem informação.`) — note o sentinel pra ausência |
| 13 | `Municípios Abrangidos` | **A coluna crítica.** Nos exemplos veio singular: `CARAGUATATUBA (SP)`, `SÃO PAULO (SP)`. Multi-município provavelmente vem com separador interno (vírgula? `;`?). Investigar na Fase D.3. |
| 14 | `Plano de Manejo` | `Sim` / `Não` (categórica booleana) |
| 15 | `Conselho Gestor` | `Sim` / `Não` |
| 16 | `Órgão Gestor` | Texto (ex: `INSTITUTO CHICO MENDES DE CONSERVAÇÃO DA BIODIVERSIDADE`) — caixa MAIÚSCULA |
| 17 | `Fonte da Área: (1 = SHP, 0 = Ato legal)` | Booleana 0/1 — nome cabeludo, **renomear** |
| 18 | `Área soma biomas` | Numérico (ha) |
| 19 | `Área soma Biomas Continental` | Numérico (ha) |
| 20 | `Área Ato Legal de Criação` | Numérico (ha) |
| 21 | `Bioma Área (ha)` | Numérico — possivelmente vazio (`;;` no exemplo) |
| 22-28 | `Amazônia`, `Caatinga`, `Cerrado`, `Mata Atlântica`, `Pampa`, `Pantanal`, `Área Marinha` | Numérico (área por bioma em ha) |
| 29 | `Bioma declarado` | Categórica (ex: `Mata Atlântica`) |
| 30 | `% Além da linha de costa` | Percentual |
| 31 | `Grupo` | Categórica (ex: `Uso Sustentável`) |
| 32 | `PI` | Booleana 0/1 (Proteção Integral?) |
| 33 | `US` | Booleana 0/1 (Uso Sustentável?) |
| 34 | `Recortes (ha)` | Numérico, possivelmente vazio |
| 35 | `Mar Territorial` | Booleana 0/1 |
| 36 | `Município Costeiro` | Booleana 0/1 |
| 37 | `Município Costeiro + Área Marinha` | Booleana 0/1 |
| 38 | `Amazônia Legal` | Booleana 0/1 |
| 39 | `Programa/Projeto` | Texto, possivelmente vazio |
| 40 | `Sítios do Patrimônio Mundial` | Texto, possivelmente vazio |
| 41 | `Sítios Ramsar` | Texto, possivelmente vazio |
| 42 | `Mosaico` | Texto, possivelmente vazio |
| 43 | `Código WDPA` | Inteiro (ex: `555682724`) — World Database on Protected Areas |

### Observações iniciais sobre o schema

- **`shape`: (3421, 43)** confirmado.
- **Encoding `iso-8859-1` tratou direito** — acentos saem corretos no Polars (`SÃO PAULO`, `PATRIMÔNIO`, `AÇU`).
- **~43 colunas** — muito maior que o necessário. A tabela final em produção (sub-projeto #4) vai descartar várias colunas derivadas/flags. **Decidir quais manter** durante o tratamento, justificando no `schema.yml`.

### 🔴 Problemas de tipo descobertos no `glimpse()` (e como mitigar)

1. **`ID_UC` é inteiro com `.` como separador de milhar (formato BR).**
   - Sintoma inicial: Polars leu como `<f64>` e perdeu trailing zero (`1.050` → `1.05`).
   - **Mitigação aplicada:** `schema_overrides={"ID_UC": pl.Utf8}` — preserva o valor como string `'1.050'`.
   - **Tratamento posterior:** se precisar usar como inteiro, `.str.replace(".", "", literal=True).cast(pl.Int64)`. Provavelmente vai ser **descartado** no modelo final — `Código UC` é a chave canônica.

2. **Colunas de área/bioma com `.` de milhar + `,` decimal (formato BR completo).**
   - Sintoma: `Área soma biomas`, `Amazônia`, `Caatinga`, `Cerrado`, `Mata Atlântica`, `Pampa`, `Pantanal`, `Área Marinha`, `Área soma Biomas Continental`, `Área Ato Legal de Criação` lidas como `<str>`.
   - Causa: Polars com `decimal_comma=True` resolve a vírgula decimal, mas não tem opção pra separador de milhar `.`. Qualquer valor tipo `1.045,5` quebra a inferência → degrada pra string.
   - **Mitigação no tratamento (não na leitura):** sequência `.str.replace_all("\\.", "").str.replace(",", ".").cast(pl.Float64)`. Aplicar em cada coluna numérica afetada.
   - **Por que não na leitura:** Polars não expõe controle de separador de milhar no `read_csv`. Tem que ser pós-leitura.

3. **`% Além da linha de costa`** virou `<f64>` corretamente ✅ — porque tem vírgula decimal sem ponto de milhar. Confirma que `decimal_comma=True` funciona pra esse caso.

4. **`decimal_comma=True`** é a configuração correta pra esse arquivo. Manter no `read_csv` definitivo.

### Configuração final do `read_csv` (preliminar)

```python
pl.read_csv(
    "data/raw/cnuc_2026_03_atualizado.csv",
    encoding="iso-8859-1",
    separator=";",
    infer_schema_length=10_000,
    decimal_comma=True,
    schema_overrides={
        "ID_UC": pl.Utf8,
        "Código UC": pl.Utf8,
        "Código WDPA": pl.Utf8,
    },
)
```

> **No tratamento real (sub-projeto #2 implementação),** essa leitura vai estar em uma função `extract.py` ou similar, com a sequência de cast das colunas de área/bioma logo depois.

### Achados sobre os primeiros 10 registros

- Todos são **RPPN Federal SP** — o arquivo parece ordenado/agrupado por algum critério. Os primeiros não ajudam a investigar multi-município (RPPN tipicamente é unimunicipal).
- `Municípios Abrangidos` em todos os 10: formato `"NOME EM CAIXA ALTA (SIGLA_UF)"` — singular. **A pergunta D.3 (formato em multi-município) precisa de amostra de Parque Nacional ou similar.**
- `Ano de Criação` é `<i64>` puro (1995-2002 nos exemplos). **Cobertura temporal final será por ano**: `cobertura_temporal: 19XX(1)2026` no `schema.yml`.

### Colunas com null em 10/10 amostras (candidatas a fantasma)

> Confirmar com `df.null_count()` se são 100% null no dataset inteiro.

- `Informações Gerais`
- `Bioma Área (ha)`
- `Recortes (ha)`
- `Amazônia Legal`
- `Programa/Projeto`
- `Sítios do Patrimônio Mundial`
- `Sítios Ramsar`
- `Mosaico`

### Outras notas

- **`Sem informação.`** aparece como sentinel de "vazio textual" — precisa virar `NULL` no tratamento. Distribuição confirmada na exploração:
  - `Outros atos legais`: **2.424 ocorrências (~70%)** — significam UCs que não tiveram alteração legal posterior à criação. Nulo legítimo.
  - `Código WDPA`: **123 ocorrências (~4%)** — UCs sem registro no World Database on Protected Areas. Nulo legítimo.
  - Em ambos os casos, é dado válido (não corrupção). Documentar no `schema.yml` da tabela final.
- **Nomes de coluna com caracteres especiais** (`Fonte da Área: (1 = SHP, 0 = Ato legal)`, `Município Costeiro + Área Marinha`) vão precisar de renomeação cuidadosa pro snake_case.
- **Booleanas 0/1** identificadas: `Fonte da Área`, `PI`, `US`, `Mar Territorial`, `Município Costeiro`, `Município Costeiro + Área Marinha`. No style guide BD, `int64` 0/1 é o padrão pra booleanas — não precisa converter pra `bool`.
- **Candidatos a chave primária:** `Código UC` (formato `0000.00.<seq>`) parece o mais canônico do MMA — confirmar unicidade na Fase D.1. `ID_UC` também candidato **depois** de corrigir tipo.

---

## Respostas do checklist da §5 (Fase D)

### D.1 Chave natural

`Código UC` (string, formato `0000.00.<seq>`). É o identificador canônico do CNUC segundo o dicionário oficial. `ID_UC` existe no CSV mas **não está no dicionário** — provavelmente auto-incremental interno do export.

### D.2 Duplicatas

Não foram encontradas duplicatas relevantes na chave natural durante a exploração. (Confirmar como validação no tratamento.)

### D.3 Representação de município

Coluna `Municípios Abrangidos`, formato por célula:
- Singular: `"NOME EM CAIXA ALTA (SIGLA_UF)"` (ex: `"CARAGUATATUBA (SP)"`).
- Múltiplos municípios: separados por `" - "` (espaço-hífen-espaço), ex `"CAMANDUCAIA (MG) - EXTREMA (MG)"`. **(O dicionário diz "vírgula", mas o dado real usa `" - "` — ver correção empírica no topo deste doc.)**
- A sigla entre parênteses precisa ser **separada** do nome no tratamento (regex `r'\s*\([A-Z]{2}\)$'` ou split por `(`).
- Nomes com hífen interno (`SAPUCAÍ-MIRIM`, `VARRE-SAI`, `PARIQUERA-AÇU`) **não** quebram o `split(" - ")` porque o hífen interno não tem espaços em volta.

### D.4 UCs sem município (marinhas)

**Correção empírica (2026-05-29):** **não existe UC sem município** neste dataset. `Municípios Abrangidos` tem 0 nulls e 0 vazios, e as 229 UCs com `Mar Territorial = Sim` trazem todas municípios costeiros. A flag `indicador_marinha` continua na principal (derivada de `Mar Territorial`/`Área Marinha`), mas como atributo analítico — UCs marinhas **entram** normalmente na ponte `uc_municipio` com seus municípios costeiros. Ver [[ucs-marinhas]] (decisão revisada).

### D.5 UCs em múltiplos municípios

A quantificar no tratamento via `pl.col("Municípios Abrangidos").str.contains(" - ")` (587 linhas multi-município). Separador `" - "` confirmado no dado real.

### D.6 `sigla_uf`

Coluna `UF` já existe (sigla 2 letras). **Mas também é multi-valor** — UCs que cruzam estados vêm como `"AM, PA"` (separador: vírgula, confirmado pelo dicionário). Implica split também em `UF`, não só em `Municípios Abrangidos`.

### D.7 `data_criacao`

Não existe data completa — apenas `Ano de Criação` (`<i64>`). A **cobertura temporal** da tabela final será por ano: `<ano_mais_antigo>(1)<ano_do_snapshot>`. Granularidade temporal mínima é o ano.

### D.8 Categóricas — valores e qualidade

Valores observados batem com o dicionário oficial em `Esfera Administrativa`, `Plano de Manejo`, `Conselho Gestor`. `Categoria de Manejo` e `Categoria IUCN` apresentam diferenças cosméticas em relação ao dicionário (ex: "Parque Nacional" no CSV vs "Parque" no dicionário; "Category IV" no CSV vs "IV" no dicionário) — não são erros, mas exigem normalização cuidadosa antes de comparar contra a lista canônica do dicionário.

### D.9 Área

Várias colunas de área (em hectares): `Área soma biomas`, `Área soma Biomas Continental`, `Área Ato Legal de Criação`, e uma por bioma (`Amazônia`, `Caatinga`, `Cerrado`, `Mata Atlântica`, `Pampa`, `Pantanal`, `Área Marinha`).

**Formato BR completo** (`.` separador de milhar + `,` decimal). Polars não tem opção pra separador de milhar — tratamento pós-leitura: `.str.replace_all("\\.", "").str.replace(",", ".").cast(pl.Float64)`.

### D.10 Geometria

Sem coluna de geometria explícita. Existem flags relacionadas (`Mar Territorial`, `Município Costeiro`, `% Além da linha de costa`) mas nada de WKT/GeoJSON. **Geografia fica fora de escopo** — não há trabalho extra aqui.

---

## Decisões fechadas (§0 do plano)

Todas registradas em documentos próprios em `docs/decisoes/`. Esta seção lista os ponteiros.

| § | Decisão | Doc | Resumo |
|---|---|---|---|
| §0.1 | Granularidade | [granularidade.md](decisoes/granularidade.md) | Star schema: `unidade_conservacao` (1 linha por UC, sem `id_municipio`) + ponte `uc_municipio` |
| §0.2 | UCs marinhas | [ucs-marinhas.md](decisoes/ucs-marinhas.md) | Flag `indicador_marinha` na principal; marinhas não entram na ponte |
| §0.3 | Diretório IBGE | [diretorio-ibge.md](decisoes/diretorio-ibge.md) | Seed do dbt (`dbt/seeds/municipio.csv`), populado uma vez via pacote `basedosdados` |
| §0.4 | Normalização de nomes | [normalizacao-nomes.md](decisoes/normalizacao-nomes.md) | trim → strip sufixo `(UF)` → `unidecode` → lowercase. Match por `(nome, sigla_uf)` |
| §0.5 | Encoding/formato | (registrada nesta página, [seção Diagnóstico](#diagnóstico-do-arquivo-fase-b) + [Schema](#schema-fase-c)) | `iso-8859-1`, `;`, `decimal_comma=True`, `schema_overrides`, cast pós-leitura das áreas |
| §0.6 | Idempotência | [estrategia-atualizacao.md](decisoes/estrategia-atualizacao.md) | Full refresh + overwrite |
