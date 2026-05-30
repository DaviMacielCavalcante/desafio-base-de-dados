{{ config(alias='unidade_conservacao') }}

SELECT * EXCLUDE (
    area_amazonia, area_caatinga, area_cerrado,
    area_mata_atlantica, area_pampa, area_pantanal
)
FROM {{ source('br_mma_unidades_conservacao_staging', 'unidade_conservacao') }}

