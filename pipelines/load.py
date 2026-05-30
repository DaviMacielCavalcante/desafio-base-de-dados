import os
from botocore.exceptions import ClientError, EndpointConnectionError, ConnectionClosedError

def ensure_bucket(s3, bucket: str, endpoint) -> None:
    """Cria o bucket se não existir. Distingue 'já existe' de 'MinIO fora do ar'."""
    try:
        s3.head_bucket(Bucket=bucket)
        print(f"Bucket '{bucket}' já existe")
    except (EndpointConnectionError, ConnectionClosedError) as e:
        raise ConnectionError(
            f"MinIO inalcançável em {endpoint}. "
            f"Rode `make up` e confira `docker port minio`."
        ) from e
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchBucket"):
            s3.create_bucket(Bucket=bucket)
            print(f"Bucket '{bucket}' criado")
        else:
            raise

    
def upload(s3, df_path, bucket, key, endpoint) -> str:
        
    ensure_bucket(s3, bucket, endpoint)

    try:
        s3.upload_file(Filename=str(df_path), Bucket=bucket, Key=key)
        print(f"Upload para s3://{bucket}/{key}")
    except (EndpointConnectionError, ConnectionClosedError) as e:
        raise ConnectionError(
            f"MinIO inalcançável em {endpoint}. Rode `make up`."
        ) from e
    except ClientError as e:
        raise RuntimeError(f"Falha no upload pro MinIO: {e}") from e

    s3.head_object(Bucket=bucket, Key=key)
    print(f"Confirmado: Arquivo em s3://{bucket}/{key}")
    
    return f"s3://{bucket}/{key}"