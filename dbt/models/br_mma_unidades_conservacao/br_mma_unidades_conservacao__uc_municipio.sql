{{ config(alias='uc_municipio') }}

WITH municipios_explodidos AS (
    SELECT
        id_uc,
        unnest(municipios_abrangidos) AS municipio 
    FROM {{ source('br_mma_unidades_conservacao_staging', 'unidade_conservacao') }}
)

SELECT
    me.id_uc,
    m.id_municipio
FROM municipios_explodidos AS me 
JOIN {{ ref('municipio') }} AS m
    ON m.sigla_uf = me.municipio.sigla_uf
    AND LOWER(strip_accents(m.nome)) = me.municipio.nome_norm