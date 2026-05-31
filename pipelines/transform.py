from pathlib import Path

import polars as pl
from unidecode import unidecode

STR_COLUMNS = [
    "Código UC",
    "Nome da UC",
    "Esfera Administrativa",
    "Categoria de Manejo",
    "Categoria IUCN",
    "UF",
    "Ato Legal de Criação",
    "Outros atos legais",
    "Municípios Abrangidos",
    "Bioma declarado",
    "Grupo",
    "Programa/Projeto",
    "Sítios do Patrimônio Mundial",
    "Sítios Ramsar",
    "Mosaico",
    "Código WDPA",
    "Órgão Gestor",
]
INT_COLUMNS = [
    "Ano de Criação",
    "Ano do ato legal mais recente",
    "Fonte da Área: (1 = SHP, 0 = Ato legal)",
    "PI",
    "US",
    "Mar Territorial",
    "Município Costeiro",
    "Município Costeiro + Área Marinha",
    "Plano de Manejo",
    "Conselho Gestor",
]
FLOAT_COLUMNS = [
    "Área soma biomas",
    "Área soma Biomas Continental",
    "Área Ato Legal de Criação",
    "Área Marinha",
    "% Além da linha de costa",
    "Amazônia",
    "Caatinga",
    "Cerrado",
    "Mata Atlântica",
    "Pampa",
    "Pantanal",
]
DROP_COLUMNS = ["ID_UC", "Recortes (ha)", "Bioma Área (ha)", "Amazônia Legal", "Informações Gerais"]
RENAME_MAP = {
    "Código UC": "id_uc",
    "Nome da UC": "nome_uc",
    "Esfera Administrativa": "esfera_administrativa",
    "Categoria de Manejo": "categoria_manejo",
    "Categoria IUCN": "categoria_iucn",
    "UF": "sigla_uf",
    "Ano de Criação": "ano_criacao",
    "Ano do ato legal mais recente": "ano_ato_legal_mais_recente",
    "Ato Legal de Criação": "ato_legal_criacao",
    "Outros atos legais": "outros_atos_legais",
    "Municípios Abrangidos": "municipios_abrangidos",
    "Plano de Manejo": "indicador_plano_manejo",
    "Conselho Gestor": "indicador_conselho_gestor",
    "Órgão Gestor": "orgao_gestor",
    "Fonte da Área: (1 = SHP, 0 = Ato legal)": "indicador_fonte_shp",
    "Área soma biomas": "area_soma_biomas",
    "Área soma Biomas Continental": "area_soma_biomas_continental",
    "Área Ato Legal de Criação": "area_ato_legal_criacao",
    "Amazônia": "area_amazonia",
    "Caatinga": "area_caatinga",
    "Cerrado": "area_cerrado",
    "Mata Atlântica": "area_mata_atlantica",
    "Pampa": "area_pampa",
    "Pantanal": "area_pantanal",
    "Área Marinha": "area_marinha",
    "Bioma declarado": "bioma_declarado",
    "% Além da linha de costa": "proporcao_alem_linha_costa",
    "Grupo": "grupo",
    "PI": "indicador_protecao_integral",
    "US": "indicador_uso_sustentavel",
    "Mar Territorial": "indicador_marinha",
    "Município Costeiro": "indicador_municipio_costeiro",
    "Município Costeiro + Área Marinha": "indicador_municipio_costeiro_marinha",
    "Programa/Projeto": "programa_projeto",
    "Sítios do Patrimônio Mundial": "sitios_patrimonio_mundial",
    "Sítios Ramsar": "sitios_ramsar",
    "Mosaico": "mosaico",
    "Código WDPA": "codigo_wdpa",
}
REQUIRED_COLUMNS = [
    "Código UC",
    "Nome da UC",
    "Esfera Administrativa",
    "Categoria de Manejo",
    "Categoria IUCN",
    "UF",
    "Ano de Criação",
    "Ato Legal de Criação",
    "Outros atos legais",
    "Municípios Abrangidos",
    "Plano de Manejo",
    "Conselho Gestor",
    "Área soma biomas",
    "Área soma Biomas Continental",
    "Área Ato Legal de Criação",
    "Amazônia",
    "Caatinga",
    "Cerrado",
    "Mata Atlântica",
    "Pampa",
    "Pantanal",
    "Área Marinha",
]
ORDERED_COLUMNS = [
    # Zona 1: chaves (ordem descendente de abrangência)
    "sigla_uf",
    "id_uc",
    # Zona 2: qualitativas
    # 2a — identificação + categóricas oficiais
    "nome_uc",
    "esfera_administrativa",
    "categoria_manejo",
    "categoria_iucn",
    "grupo",
    # 2b — localização (ecológica + administrativa)
    "bioma_declarado",
    "mosaico",
    "municipios_abrangidos",
    # 2c — programas, sítios, atos
    "programa_projeto",
    "sitios_patrimonio_mundial",
    "sitios_ramsar",
    "orgao_gestor",
    "ato_legal_criacao",
    "outros_atos_legais",
    "codigo_wdpa",
    # 2d — indicadores binários (booleanas)
    "indicador_plano_manejo",
    "indicador_conselho_gestor",
    "indicador_fonte_shp",
    "indicador_protecao_integral",
    "indicador_uso_sustentavel",
    "indicador_marinha",
    "indicador_municipio_costeiro",
    "indicador_municipio_costeiro_marinha",
    # Zona 3: quantitativas (crescente de relevância)
    "ano_criacao",
    "ano_ato_legal_mais_recente",
    "proporcao_alem_linha_costa",
    "area_amazonia",
    "area_caatinga",
    "area_cerrado",
    "area_mata_atlantica",
    "area_pampa",
    "area_pantanal",
    "area_marinha",
    "area_soma_biomas_continental",
    "area_soma_biomas",
    "area_ato_legal_criacao",
]


def validate_schema(df: pl.DataFrame) -> None:

    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]

    if len(missing) > 0:
        raise ValueError(f"Colunas não encontradas: {missing}")


def check_duplicates_uc_codes(df: pl.DataFrame) -> None:

    duplicates = df.group_by("Código UC").len().filter(pl.col("len") > 1)

    if duplicates.height > 0:
        raise ValueError(f"Duplicated data found! {duplicates.height} found!")


def drop_null_or_empty_rows(df: pl.DataFrame) -> pl.DataFrame:

    df_filtered = df = df.filter(pl.col("Código UC").is_not_null())

    return df_filtered


def drop_columns(df):
    return df.drop(DROP_COLUMNS)


def cast_columns(df: pl.DataFrame) -> pl.DataFrame:

    expressions = []
    for col in df.columns:
        if col in STR_COLUMNS:
            expressions.append(pl.col(col).cast(pl.String))
        elif col in INT_COLUMNS:
            if df[col].dtype == pl.String:
                expressions.append(pl.col(col).replace_strict({"Sim": 1, "Não": 0}).cast(pl.Int64))
            else:
                expressions.append(pl.col(col).cast(pl.Int64))
        elif col in FLOAT_COLUMNS:
            if df[col].dtype == pl.String:
                expressions.append(
                    pl.col(col).str.replace_all(r"\.", "").str.replace(",", ".").cast(pl.Float64)
                )
            else:
                expressions.append(pl.col(col).cast(pl.Float64))

    return df.with_columns(expressions)


def normalize_categoricals(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(pl.col("Categoria IUCN").str.replace("Category ", ""))


def normalize_sentinels(df: pl.DataFrame) -> pl.DataFrame:
    cols_with_sentinel = ["Outros atos legais", "Código WDPA"]
    return df.with_columns([pl.col(c).replace("Sem informação.", None) for c in cols_with_sentinel])


def trim_strings(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns([pl.col(c).str.strip_chars() for c in STR_COLUMNS])


def rename_columns(df: pl.DataFrame) -> pl.DataFrame:
    return df.rename(RENAME_MAP)


def normalize_municipio(s: str | None) -> str | None:
    """Chave de match — lowercase + sem acentos.
    Mesma função aplicada nos dois lados do join (CNUC e seed IBGE)."""
    if s is None:
        return None
    return unidecode(s).lower()


def build_municipios_struct(df: pl.DataFrame) -> pl.DataFrame:
    """Transforma 'Municípios Abrangidos' (string com separador ' - ') em
    ARRAY[STRUCT(nome, sigla_uf, nome_norm)].
    UCs marinhas (sem município) ficam com lista vazia ou null."""
    return df.with_columns(
        pl.col("Municípios Abrangidos")
        .str.split(" - ")
        .list.eval(
            pl.struct(
                nome=pl.element().str.strip_chars().str.replace(r"\s*\([A-Z]{2}\)\s*$", ""),
                sigla_uf=pl.element().str.extract(r"\(([A-Z]{2})\)\s*$"),
                nome_norm=pl.element()
                .str.strip_chars()
                .str.replace(r"\s*\([A-Z]{2}\)\s*$", "")
                .map_elements(normalize_municipio, return_dtype=pl.String),
            )
        )
    )


def reorder_columns(df: pl.DataFrame) -> pl.DataFrame:
    return df.select(ORDERED_COLUMNS)


def transform(df: pl.DataFrame) -> Path:

    ROOT = Path(__file__).resolve().parents[1]

    STAGING_PATH = (
        ROOT
        / "data"
        / "staging"
        / "br_mma_unidades_conservacao"
        / "unidade_conservacao"
        / "unidade_conservacao.parquet"
    )

    validate_schema(df)
    check_duplicates_uc_codes(df)
    df_dropped_cols = drop_columns(df)
    df_no_nulls_or_empty_rows = drop_null_or_empty_rows(df_dropped_cols)
    df_uc_casted_cols = cast_columns(df_no_nulls_or_empty_rows)
    df_trimmed = trim_strings(df_uc_casted_cols)
    df_sentinels_normalized = normalize_sentinels(df_trimmed)
    df_categoricals_normalized = normalize_categoricals(df_sentinels_normalized)
    df_municipios_struct_build = build_municipios_struct(df_categoricals_normalized)
    df_renamed_columns = rename_columns(df_municipios_struct_build)
    df_reordered_columns = reorder_columns(df_renamed_columns)

    STAGING_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_reordered_columns.write_parquet(STAGING_PATH)

    return STAGING_PATH
