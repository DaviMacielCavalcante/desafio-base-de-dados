from prefect_dbt import PrefectDbtRunner, PrefectDbtSettings

def get_runner():

    settings = PrefectDbtSettings(project_dir="dbt", profiles_dir="dbt")
    
    runner = PrefectDbtRunner(settings=settings)
    
    return runner