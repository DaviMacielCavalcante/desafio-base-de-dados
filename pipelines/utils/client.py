import os

import boto3
from botocore.config import Config


def get_s3_client():
    """Factory para o client S3-compatível apontado ao MinIO.

    Lê endpoint e credenciais do ``.env`` (``MINIO_ENDPOINT``,
    ``MINIO_ROOT_USER``, ``MINIO_ROOT_PASSWORD``) e força
    *path-style addressing* (necessário no MinIO, que não suporta
    o ``virtual-hosted-style`` do S3 nativo).

    Returns
    -------
    botocore.client.S3
        Client pronto para chamadas como ``upload_file``,
        ``copy_object``, ``head_bucket``.
    """
    MINIO_USER = os.getenv("MINIO_ROOT_USER")
    MINIO_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD")

    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")

    s3 = boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_USER,
        aws_secret_access_key=MINIO_PASSWORD,
        config=Config(s3={"addressing_style": "path"}),
    )

    return s3
