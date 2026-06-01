import json
import os
from datetime import UTC, datetime
from pathlib import Path

from duckdb import connect
from prefect import flow, get_run_logger, task
from prefect.artifacts import create_markdown_artifact

from pipelines.extract import get_data
from pipelines.load import promote_data, upload
from pipelines.transform import transform
from pipelines.utils.runner import get_runner


@task
def extract():
    return get_data()


@task
def transform_data(data):
    return transform(data)


@task
def upload_data(df_path, key, bucket):
    return upload(df_path=df_path, key=key, bucket=bucket)


@task
def dbt_seed(target):
    runner = get_runner()

    runner.invoke(["seed", "--target", target])


@task
def dbt_run_dev():
    runner = get_runner()

    runner.invoke(["run", "--target", "dev"])


@task
def dbt_test_dev():
    runner = get_runner()

    runner.invoke(["test", "--target", "dev"])


@task
def promote_data_to_prod(key, source_bucket, destiny_bucket):

    promote_data(key=key, source_bucket=source_bucket, destiny_bucket=destiny_bucket)


@task
def dbt_run_prod():
    runner = get_runner()

    runner.invoke(["run", "--target", "prod"])


@task
def write_metadata():

    logger = get_run_logger()

    db_path = os.getenv("DUCKDB_PATH_PROD")

    conn = connect(db_path)
    schema = os.getenv("DBT_DATASET_PROD")

    try:
        row = conn.execute(
            f"SELECT max(ano_ato_legal_mais_recente), count(*) FROM {schema}.unidade_conservacao"
        ).fetchone()

    finally:
        conn.close()

    metadata = {
        "dataset_id": "br_mma_unidades_conservacao",
        "table_id": "unidade_conservacao",
        "max_date": row[0],
        "n_rows": row[1],
        "updated_at": datetime.now(UTC).isoformat(),
    }

    out = Path("data/metadata/br_mma_unidades_conservacao.json")

    out.parent.mkdir(parents=True, exist_ok=True)

    out.write_text(json.dumps(metadata, indent=2, ensure_ascii=False))

    logger.info(f"Metadata escrita: max_date={metadata['max_date']}, linhas={metadata['n_rows']}")

    create_markdown_artifact(
        key="metadata-unidade-conservacao",
        markdown=(
            f"# Metadata — unidade_conservacao\n\n"
            f"- **max_date** (ano do ato legal mais recente): {metadata['max_date']}\n"
            f"- **linhas**: {metadata['n_rows']}\n"
            f"- **atualizado em**: {metadata['updated_at']}\n"
        ),
    )


@flow
def main() -> None:
    STAGING_KEY = (
        "staging/br_mma_unidades_conservacao/unidade_conservacao/unidade_conservacao.parquet"
    )

    MINIO_BUCKET_DEV = os.getenv("MINIO_BUCKET_DEV")
    MINIO_BUCKET_PROD = os.getenv("MINIO_BUCKET_PROD")

    df = extract()

    df_path = transform_data(df)

    upload_data(df_path, STAGING_KEY, MINIO_BUCKET_DEV)

    dbt_seed("dev")
    dbt_run_dev()
    dbt_test_dev()

    promote_data_to_prod(
        key=STAGING_KEY, source_bucket=MINIO_BUCKET_DEV, destiny_bucket=MINIO_BUCKET_PROD
    )

    dbt_seed("prod")
    dbt_run_prod()
    write_metadata()


def serve():

    main.serve(name="desafio_uc_bd", interval=360)


if __name__ == "__main__":
    main()
