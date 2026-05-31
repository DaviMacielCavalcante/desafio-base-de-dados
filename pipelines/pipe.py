from pipelines.extract import get_data
from pipelines.transform import transform
from pipelines.load import upload, promote_data
from pipelines.utils.runner import get_runner
from prefect import flow, task
import os

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
    

@flow
def main() -> None:
    STAGING_KEY = "staging/br_mma_unidades_conservacao/unidade_conservacao/unidade_conservacao.parquet"
    
    MINIO_BUCKET_DEV = os.getenv("MINIO_BUCKET_DEV")
    MINIO_BUCKET_PROD = os.getenv("MINIO_BUCKET_PROD")
    
    df = extract()
    
    df_path = transform_data(df)
    
    upload_data(df_path, STAGING_KEY, MINIO_BUCKET_DEV)
    
    dbt_seed("dev")    
    dbt_run_dev()
    dbt_test_dev()
    
    promote_data_to_prod(key=STAGING_KEY, source_bucket=MINIO_BUCKET_DEV, destiny_bucket=MINIO_BUCKET_PROD)
    
    dbt_seed("prod")
    dbt_run_prod()
    
def serve():
    
    main.serve(name="desafio_uc_bd",interval=60)


if __name__ == "__main__":
    main()
