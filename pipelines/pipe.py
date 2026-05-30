from pipelines.extract import get_data
from botocore.config import Config
from pipelines.transform import transform
from pipelines.load import upload
import os
import boto3

def main() -> None:
    STAGING_KEY = "staging/br_mma_unidades_conservacao/unidade_conservacao/unidade_conservacao.parquet"
    
    MINIO_USER = os.getenv("MINIO_ROOT_USER")
    MINIO_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD")
    
    MINIO_BUCKET_DEV = os.getenv("MINIO_BUCKET_DEV")
    MINIO_BUCKET_PROD = os.getenv("MINIO_BUCKET_PROD")
    
    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
    
    df =  get_data()
    
    df_path = transform(df)
    
    s3 = boto3.client(
            "s3",
            endpoint_url=MINIO_ENDPOINT,
            aws_access_key_id=MINIO_USER,
            aws_secret_access_key=MINIO_PASSWORD,
            config=Config(
                s3={"addressing_style": "path"}
            )
        )
    
    df_uploaded_path = upload(s3, df_path=df_path, key=STAGING_KEY, bucket=MINIO_BUCKET_DEV, endpoint=MINIO_ENDPOINT)
    
    print(df_uploaded_path)   


if __name__ == "__main__":
    main()
