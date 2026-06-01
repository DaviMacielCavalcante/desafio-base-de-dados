from prefect_dbt import PrefectDbtRunner, PrefectDbtSettings


def get_runner():
    """Factory para o ``PrefectDbtRunner`` apontando ao subprojeto dbt.

    Aponta tanto ``project_dir`` quanto ``profiles_dir`` para o
    diretório ``dbt/`` na raiz do repo — onde vivem ``dbt_project.yml``
    e ``profiles.yml`` (que lê env vars do ``.env``).

    Returns
    -------
    PrefectDbtRunner
        Runner com integração nativa ao Prefect (status flow ↔ status dbt).
    """
    settings = PrefectDbtSettings(project_dir="dbt", profiles_dir="dbt")

    runner = PrefectDbtRunner(settings=settings)

    return runner
