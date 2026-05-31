import polars as pl


def get_data() -> pl.DataFrame:

    df = pl.read_csv(
        "data/raw/cnuc_2026_03_atualizado.csv",
        encoding="iso-8859-1",
        separator=";",
        infer_schema_length=10_000,
        decimal_comma=True,
        schema_overrides={"ID_UC": pl.Utf8, "Código UC": pl.Utf8, "Código WDPA": pl.Utf8},
    )

    return df
