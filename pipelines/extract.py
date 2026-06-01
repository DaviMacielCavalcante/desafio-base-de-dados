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
    """Garante que o CSV bruto está em ``data/raw/``.

    Se o arquivo já existe, retorna o caminho direto (cache local).
    Caso contrário, baixa de ``SOURCE_URL`` (env var) ou do default
    embutido — o snapshot CNUC de março/2026 publicado pelo MMA. A
    sentinela ``REPLACE_ME`` no valor da env var também dispara o
    fallback (cobre ``.env``s antigos copiados do scaffold sem
    preenchimento).

    Returns
    -------
    Path
        Caminho do CSV bruto pronto para leitura.

    Raises
    ------
    requests.HTTPError
        Se o servidor responder com status >= 400 no GET.
    """
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
    """Lê o CSV bruto do CNUC como DataFrame Polars.

    Dispara download lazy via :func:`_ensure_raw_csv` caso o arquivo
    não esteja em ``data/raw/``. O CSV é encoding ``iso-8859-1``,
    separador ``;`` e usa vírgula como decimal (padrão brasileiro);
    códigos com zero à esquerda (``ID_UC``, ``Código UC``,
    ``Código WDPA``) são lidos como ``Utf8`` para preservar o dígito.

    Returns
    -------
    pl.DataFrame
        Linhas do snapshot CNUC sem nenhum tratamento aplicado.
    """
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
