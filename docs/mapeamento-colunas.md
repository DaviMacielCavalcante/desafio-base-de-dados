# Mapeamento de colunas — bruto → tratado

Registro do mapeamento entre os nomes das colunas no CSV bruto do CNUC e os nomes finais nas tabelas `unidade_conservacao` e `uc_municipio`. As descrições aqui são fonte canônica para preencher o `description` de cada coluna no `schema.yml` do sub-projeto #4 (dbt).

Regras seguidas (`manual_estilo_bd.md`):
- `snake_case`, minúsculas, sem acento
- Sem conectores (`de`, `da`, `dos`, `e`, `a`, `em`, `com`)
- Prefixo `indicador_` para booleanas (INT64 0/1)
- Prefixo `id_` reservado para chaves primárias de entidades com diretório

---

## Tabela `unidade_conservacao`

| Bruta | Tratada | Tipo | Descrição |
|---|---|---|---|
| `Código UC` | `id_uc` | STRING | Código de identificação da UC no Cadastro Nacional de Unidades de Conservação (CNUC). Chave primária. Formato `0000.00.<seq>`. |
| `Nome da UC` | `nome_uc` | STRING | Denominação oficial da UC, mantida conforme cadastrada no CNUC. |
| `Esfera Administrativa` | `esfera_administrativa` | STRING | Esfera administrativa da UC: `Federal`, `Estadual` ou `Municipal`. (Distrito Federal entra como Estadual.) |
| `Categoria de Manejo` | `categoria_manejo` | STRING | Categoria de manejo conforme Lei 9.985/2000 (SNUC). Valores possíveis listados no dicionário oficial do MMA. |
| `Categoria IUCN` | `categoria_iucn` | STRING | Categoria equivalente no Sistema IUCN de Áreas Protegidas: `Ia`, `Ib`, `II`, `III`, `IV`, `V`, `VI`. Prefixo `Category ` removido na normalização. |
| `UF` | `sigla_uf` | STRING | Sigla(s) da(s) UF(s) que tem parte de sua área protegida pela UC. Multi-valor com separador `,` quando a UC abrange mais de uma UF. |
| `Ano de Criação` | `ano_criacao` | INT64 | Ano do ato legal que cria a UC. |
| `Ano do ato legal mais recente` | `ano_ato_legal_mais_recente` | INT64 | Ano do ato legal mais recente que altera características relevantes à UC (revisão de limites, recategorização, alteração de nome). |
| `Ato Legal de Criação` | `ato_legal_criacao` | STRING | Texto livre identificando o ato legal que cria a UC (ex: `Portaria 52/2001 de 23/04/2001`). |
| `Outros atos legais` | `outros_atos_legais` | STRING | Texto livre listando atos legais subsequentes. Sentinel `Sem informação.` (~70% dos casos) substituído por `NULL`. |
| `Plano de Manejo` | `indicador_plano_manejo` | INT64 | Indicador binário (1/0). 1 = UC possui plano de manejo concluído. 0 = não possui ou em elaboração. |
| `Conselho Gestor` | `indicador_conselho_gestor` | INT64 | Indicador binário (1/0). 1 = UC possui conselho gestor reconhecido por portaria do órgão. |
| `Órgão Gestor` | `orgao_gestor` | STRING | Nome do órgão gestor responsável pela UC. Texto não-estruturado, mantido como cadastrado no CNUC. |
| `Fonte da Área: (1 = SHP, 0 = Ato legal)` | `indicador_fonte_shp` | INT64 | Indicador binário (1/0). 1 = área obtida por geoprocessamento (SHP). 0 = área conforme ato legal. |
| `Área soma biomas` | `area_soma_biomas` | FLOAT64 | Soma das áreas da UC distribuídas pelos biomas (em hectares). |
| `Área soma Biomas Continental` | `area_soma_biomas_continental` | FLOAT64 | Soma das áreas da UC distribuídas pelos biomas continentais — exclui a porção marinha (em hectares). |
| `Área Ato Legal de Criação` | `area_ato_legal_criacao` | FLOAT64 | Área da UC conforme estabelecida no ato legal de criação (em hectares). |
| `Amazônia` | `area_amazonia` | FLOAT64 | Área da UC no Bioma Amazônia, IBGE 2004 adaptado (em hectares). |
| `Caatinga` | `area_caatinga` | FLOAT64 | Área da UC no Bioma Caatinga, IBGE 2004 adaptado (em hectares). |
| `Cerrado` | `area_cerrado` | FLOAT64 | Área da UC no Bioma Cerrado, IBGE 2004 adaptado (em hectares). |
| `Mata Atlântica` | `area_mata_atlantica` | FLOAT64 | Área da UC no Bioma Mata Atlântica, IBGE 2004 adaptado (em hectares). |
| `Pampa` | `area_pampa` | FLOAT64 | Área da UC no Bioma Pampa, IBGE 2004 adaptado (em hectares). |
| `Pantanal` | `area_pantanal` | FLOAT64 | Área da UC no Bioma Pantanal, IBGE 2004 adaptado (em hectares). |
| `Área Marinha` | `area_marinha` | FLOAT64 | Área da UC na Área Marinha (Mar Territorial e Zona Econômica Exclusiva), BCIM-IBGE 2016 (em hectares). |
| `Bioma declarado` | `bioma_declarado` | STRING | Bioma declarado/predominante da UC. |
| `% Além da linha de costa` | `proporcao_alem_linha_costa` | FLOAT64 | Proporção (0 a 1) da área da UC além da linha de costa. **Correção empírica (2026-05-30):** apesar do nome bruto usar `%`, o dado real vem como **fração 0–1**, não percentual (min 0.0, max 1.0 no parquet). O range test no `schema.yml` usa `min 0, max 1`. |
| `Grupo` | `grupo` | STRING | Grupo SNUC: `Proteção Integral` ou `Uso Sustentável`. |
| `PI` | `indicador_protecao_integral` | INT64 | Indicador binário (1/0). 1 = UC é do grupo Proteção Integral. Derivado de `Grupo`. |
| `US` | `indicador_uso_sustentavel` | INT64 | Indicador binário (1/0). 1 = UC é do grupo Uso Sustentável. Derivado de `Grupo`. |
| `Mar Territorial` | `indicador_marinha` | INT64 | Indicador binário (1/0). 1 = UC abrange área no Mar Territorial brasileiro. |
| `Município Costeiro` | `indicador_municipio_costeiro` | INT64 | Indicador binário (1/0). 1 = UC abrange município com costa marítima. |
| `Município Costeiro + Área Marinha` | `indicador_municipio_costeiro_marinha` | INT64 | Indicador binário (1/0). 1 = UC abrange **simultaneamente** município costeiro e área marinha — UCs em zona de transição terra-mar. |
| `Programa/Projeto` | `programa_projeto` | STRING | Programa ou projeto associado à UC. Texto não-estruturado. |
| `Sítios do Patrimônio Mundial` | `sitios_patrimonio_mundial` | STRING | Sítios do Patrimônio Mundial associados à UC. Texto não-estruturado. |
| `Sítios Ramsar` | `sitios_ramsar` | STRING | Sítios Ramsar associados à UC. Texto não-estruturado. |
| `Mosaico` | `mosaico` | STRING | Mosaico de UCs ao qual a UC pertence. Categórica esparsa. |
| `Código WDPA` | `codigo_wdpa` | STRING | Código de identificação da UC no World Database on Protected Areas. Sentinel `Sem informação.` (~4% dos casos) substituído por `NULL`. |
| `Municípios Abrangidos` | `municipios_abrangidos` | ARRAY[STRUCT(nome STRING, sigla_uf STRING, nome_norm STRING)] | Lista dos municípios abrangidos pela UC. Cada elemento contém o nome canônico (caixa preservada da fonte), a sigla da UF e a forma normalizada do nome (lowercase, sem acentos) usada para JOIN com o diretório IBGE no model dbt `uc_municipio` (gold). Origem: string com separador `" - "` (não vírgula). No dataset atual nunca é vazia — até UCs marinhas trazem municípios costeiros. |

---

## Tabela `uc_municipio`

> **Vive na gold (dbt), não na silver.** Decidido em 2026-05-29 — ver `docs/decisoes/granularidade.md` (histórico). Esta tabela não é produzida pelo tratamento Python; é um model dbt (`uc_municipio.sql`) derivado da source de staging via `UNNEST(municipios_abrangidos)` + **`INNER JOIN`** com o seed `municipio` por `(nome_norm, sigla_uf)`. **Implementado em 2026-05-30:** o JOIN é `INNER` (não `LEFT`) — UC cujo município não casa simplesmente não gera par, mantendo `not_null`/`relationships` verdes; e a normalização do lado seed é **inline no SQL** (`lower(strip_accents(m.nome))`), sem view `municipio_norm` separada.

Colunas esperadas no model dbt:

| Coluna | Tipo | Origem | Descrição |
|---|---|---|---|
| `id_uc` | STRING | `unidade_conservacao.id_uc` | Chave da UC (FK). |
| `id_municipio` | STRING | seed `municipio.id_municipio` (via JOIN) | Código IBGE 7 dígitos do município. |

Testes (`schema.yml`): `not_null` + `relationships` em `id_municipio`; chave composta `(id_uc, id_municipio)` única (`dbt_utils.unique_combination_of_columns`).

---

## Tabela `uc_bioma`

> **Vive na gold (dbt), não na silver.** Decidido em 2026-05-30 — ver `docs/decisoes/granularidade.md` (adendo `uc_bioma`). Model `uc_bioma.sql` derivado da source via `UNPIVOT` das 6 colunas `area_<bioma>` da `unidade_conservacao` (formato long; manual BD §"long over wide"). Uma linha por par `(id_uc, bioma)` onde `area_ha > 0`. As 6 colunas wide **saem** da `unidade_conservacao` (via `select * exclude (...)`); ficam só os agregados `area_soma_biomas`/`area_soma_biomas_continental`.

Colunas esperadas no model dbt:

| Coluna | Tipo | Origem | Descrição |
|---|---|---|---|
| `id_uc` | STRING | `unidade_conservacao.id_uc` | Chave da UC (FK). |
| `bioma` | STRING | nome da coluna `area_<bioma>` (via UNPIVOT) | Bioma legível: `Amazônia`, `Caatinga`, `Cerrado`, `Mata Atlântica`, `Pampa`, `Pantanal`. |
| `area_ha` | FLOAT64 | valor da coluna `area_<bioma>` | Área da UC no bioma, em hectares. |

Testes (`schema.yml`): chave composta `(id_uc, bioma)` única; `not_null` em `id_uc`/`bioma`/`area_ha`; `accepted_values` nos 6 biomas; `accepted_range` (`area_ha >= 0`).

---

## Decisões de naming registradas

### Prefixo `id_` para `Código UC` (chave primária da UC)

**Data:** 2026-05-29

A coluna `Código UC` do CNUC vira `id_uc` na tabela `unidade_conservacao`.

**Conflito com a letra do style guide:** o `manual_estilo_bd.md` diz: *"Só ter o prefixo `id_` quando a variável representar chaves primárias de entidades [que eventualmente teriam tabela de diretório]"*. Não existe diretório oficial `br_bd_diretorios_brasil.unidade_conservacao` na BD — então leitura estrita pediria `codigo_uc`.

**Decisão pela prática observada:** usar `id_uc`, alinhado com o padrão **de fato** adotado pela BD em registros oficiais brasileiros equivalentes.

**Precedente verificado — CNES (estrutura análoga):**

O **CNES (Cadastro Nacional de Estabelecimentos de Saúde)** é estrutura conceitualmente equivalente ao CNUC: registro oficial brasileiro de uma entidade, mantido por órgão federal, sem diretório formal `br_bd_diretorios_brasil.*` correspondente.

O dataset oficial BD [`br_ms_cnes.estabelecimento`](https://github.com/basedosdados/queries-basedosdados/blob/main/models/br_ms_cnes/br_ms_cnes__estabelecimento.sql) usa:

- `id_estabelecimento_cnes` — chave primária do estabelecimento (sem diretório formal)
- `id_regiao_saude`, `id_microrregiao_saude`, `id_distrito_sanitario`, `id_distrito_administrativo`, `id_natureza_juridica`, `id_contrato_municipio_sus`, `id_contrato_estado_sus` — todas com prefixo `id_`, todas sem diretório `br_bd_diretorios_brasil.*` correspondente

Isso estabelece **precedente publicado e auditável** de que registros oficiais brasileiros sem diretório formal usam prefixo `id_` para chaves primárias e referências internas.

**Aplicação ao CNUC:** o CNUC é o registro oficial brasileiro de UCs. Por analogia direta com o caso CNES, `id_uc` é nome canônico aceitável.

> **Nota sobre o escopo da pesquisa:** este precedente foi extraído do que é **publicamente acessível** nos repositórios e datasets da Base dos Dados (especificamente, o repo público [`queries-basedosdados`](https://github.com/basedosdados/queries-basedosdados)). Pode haver convenções internas, datasets privados ou regras adicionais não publicadas que mudariam o quadro. A decisão se baseia no que é auditável agora.

**Quando reconsiderar:** se a BD publicar um diretório oficial `br_bd_diretorios_brasil.unidade_conservacao` no futuro, o `id_uc` continua válido — pelo contrário, fica plenamente conforme.

### Prefixo `area_` para colunas de medida de área, sem sufixo de unidade

**Data:** 2026-05-29

Colunas que medem área (em hectares) recebem prefixo `area_`. Exemplos: `area_amazonia`, `area_marinha`, `area_ato_legal_criacao`, `area_soma_biomas`, etc.

**Sobre o prefixo `area_`:** não está listado no `manual_estilo_bd.md` como prefixo "oficialmente reservado" (a lista oficial é `nome_`, `data_`, `quantidade_`, `proporcao_`, `taxa_`, `razao_`, `indice_`, `indicador_`, `tipo_`, `sigla_`, `sequencial_`). Mas a lista não é exaustiva — é a relação de prefixos com significado **reservado**. Outros prefixos são livres, contanto que sigam as regras gerais (snake_case, sem acento, sem conector).

**Justificativa:**
- Sem prefixo, nomes como `amazonia`, `caatinga`, `cerrado` ficam ambíguos (área? indicador? contagem?). Com `area_*`, fica auto-documentado.
- Consistência interna: as colunas que já vinham com "Área" no nome bruto (`Área soma biomas`, `Área Marinha`, etc.) viram naturalmente `area_*`. Manter as 6 de bioma sem prefixo destoaria.
- Cumpre a regra geral do style "ser o mais intuitivo, claro e extenso possível".

**Sobre a unidade no nome (hectares):**

A unidade **não** aparece no nome da coluna. Citação direta do manual:

> "A regra é manter variáveis com suas unidades de medida originais [...]. Essa informação, como outros metadados de colunas, são registradas na tabela de arquitetura da tabela."

Ou seja, `ha` vive como metadado (no `unit` do `schema.yml` futuramente), **não** como sufixo (`area_amazonia_ha` violaria a regra). As únicas exceções listadas no manual são moeda deflacionada com ano base (`BRL_2010`) e per capita (`*_pc`) — nenhuma se aplica aqui.

**Aplicação:** `area_amazonia` (correto) — `area_amazonia_ha` (incorreto). Descrição completa no `schema.yml` informa que a unidade é `ha`.

### Justaposição sem conector para colunas que originalmente usam `+` (AND)

**Data:** 2026-05-29

A coluna bruta `Município Costeiro + Área Marinha` representa um AND ("UC tem ambos: município costeiro **e** área marinha"). O `+` no nome bruto não pode ser preservado, e o conector natural em português (`e`, `com`) viola o style guide BD (sem conectores).

**Decisão:** usar **justaposição sem conector** — `indicador_municipio_costeiro_marinha`.

**Justificativa:**
- Fiel à composição semântica original (preserva os dois conceitos: município costeiro + marinha).
- Não usa conector proibido pelo style guide BD.
- A descrição completa no `schema.yml` esclarece o sentido (AND, não OR).

**Trade-off aceito:** o nome justaposto pode ser lido como "costeiro marinho" (uma única qualidade ambígua) em vez de "costeiro AND marinho". Mitigado pela descrição.

**Quando reconsiderar:** se houver pressão por nomes mais curtos no futuro (ex: `indicador_costeiro_marinho`), revisitar com o reviewer.
