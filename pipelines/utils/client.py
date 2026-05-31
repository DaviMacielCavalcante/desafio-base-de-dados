import os

import boto3
from botocore.config import Config


def get_s3_client():

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
