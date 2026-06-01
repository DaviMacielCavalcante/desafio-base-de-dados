from botocore.exceptions import ClientError, ConnectionClosedError, EndpointConnectionError
from prefect import get_run_logger

from pipelines.utils.client import get_s3_client


def ensure_bucket(s3, bucket: str, endpoint) -> None:
    """Cria o bucket se não existir. Distingue 'já existe' de 'MinIO fora do ar'."""
    logger = get_run_logger()
    try:
        s3.head_bucket(Bucket=bucket)
        logger.info(f"Bucket '{bucket}' já existe")
    except (EndpointConnectionError, ConnectionClosedError) as e:
        raise ConnectionError(
            f"MinIO inalcançável em {endpoint}. Rode `make up` e confira `docker port minio`."
        ) from e
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchBucket"):
            s3.create_bucket(Bucket=bucket)
            logger.info(f"Bucket '{bucket}' criado")
        else:
            raise


def upload(df_path, bucket, key) -> str:

    logger = get_run_logger()

    s3 = get_s3_client()
    endpoint = s3.meta.endpoint_url

    ensure_bucket(s3, bucket, endpoint)

    try:
        s3.upload_file(Filename=str(df_path), Bucket=bucket, Key=key)
        logger.info(f"Upload para s3://{bucket}/{key}")
    except (EndpointConnectionError, ConnectionClosedError) as e:
        raise ConnectionError(f"MinIO inalcançável em {endpoint}. Rode `make up`.") from e
    except ClientError as e:
        raise RuntimeError(f"Falha no upload pro MinIO: {e}") from e

    s3.head_object(Bucket=bucket, Key=key)
    logger.info(f"Confirmado: Arquivo em s3://{bucket}/{key}")

    return f"s3://{bucket}/{key}"


def promote_data(key, source_bucket, destiny_bucket):

    logger = get_run_logger()

    s3 = get_s3_client()
    endpoint = s3.meta.endpoint_url

    ensure_bucket(s3=s3, bucket=destiny_bucket, endpoint=endpoint)

    s3.copy_object(CopySource={"Bucket": source_bucket, "Key": key}, Bucket=destiny_bucket, Key=key)
    logger.info(f"Promovido s3://{source_bucket}/{key} -> s3://{destiny_bucket}/{key}")
