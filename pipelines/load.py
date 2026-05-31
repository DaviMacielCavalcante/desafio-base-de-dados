from botocore.exceptions import ClientError, EndpointConnectionError, ConnectionClosedError
from pipelines.utils.client import get_s3_client
import os 

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

    
def upload(df_path, bucket, key) -> str:
        
    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")    
        
    s3 = get_s3_client()    
        
    ensure_bucket(s3, bucket, MINIO_ENDPOINT)

    try:
        s3.upload_file(Filename=str(df_path), Bucket=bucket, Key=key)
        print(f"Upload para s3://{bucket}/{key}")
    except (EndpointConnectionError, ConnectionClosedError) as e:
        raise ConnectionError(
            f"MinIO inalcançável em {MINIO_ENDPOINT}. Rode `make up`."
        ) from e
    except ClientError as e:
        raise RuntimeError(f"Falha no upload pro MinIO: {e}") from e

    s3.head_object(Bucket=bucket, Key=key)
    print(f"Confirmado: Arquivo em s3://{bucket}/{key}")
    
    return f"s3://{bucket}/{key}"

def promote_data(key, source_bucket, destiny_bucket):
    
    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")    
    
    s3 = get_s3_client()
    
    ensure_bucket(s3=s3, bucket=destiny_bucket, endpoint=MINIO_ENDPOINT)
    
    s3.copy_object(
        CopySource={'Bucket': source_bucket, 'Key': key},
        Bucket=destiny_bucket,
        Key=key
    )