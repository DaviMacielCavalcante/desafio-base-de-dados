import logging
import os
from pathlib import Path

import polars as pl
import requests

DEFAULT_SOURCE_URL = (
    "https://dados.mma.gov.br/dataset/"
    "44b6dc8a-dc82-4a84-8d95-1b0da7c85dac/resource/"
    "bab6d474-d38d-457c-9092-755f23ebdc76/download/"
    "cnuc_2026_03_atualizado.csv"
)
RAW_PATH = Path("data/raw/cnuc_2026_03_atualizado.csv")

logger = logging.getLogger(__name__)


def _ensure_raw_csv() -> Path:
    if RAW_PATH.exists():
        return RAW_PATH

    url = os.environ.get("SOURCE_URL") or DEFAULT_SOURCE_URL
    if "REPLACE_ME" in url:
        url = DEFAULT_SOURCE_URL
    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Baixando CSV bruto de %s -> %s", url, RAW_PATH)

    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with RAW_PATH.open("wb") as f:
            for chunk in r.iter_content(chunk_size=64 * 1024):
                f.write(chunk)

    return RAW_PATH


def get_data() -> pl.DataFrame:
    path = _ensure_raw_csv()

    df = pl.read_csv(
        str(path),
        encoding="iso-8859-1",
        separator=";",
        infer_schema_length=10_000,
        decimal_comma=True,
        schema_overrides={"ID_UC": pl.Utf8, "Código UC": pl.Utf8, "Código WDPA": pl.Utf8},
    )

    return df
