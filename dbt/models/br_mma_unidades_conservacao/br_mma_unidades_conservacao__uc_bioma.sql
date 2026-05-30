{{ config(alias='uc_bioma') }}

with unpivoted as (
    select id_uc, bioma_col, area_ha
    from {{ source('br_mma_unidades_conservacao_staging', 'unidade_conservacao') }}
    unpivot (
        area_ha for bioma_col in (
            area_amazonia, area_caatinga, area_cerrado,
            area_mata_atlantica, area_pampa, area_pantanal
        )
    )
    where area_ha > 0
)

select
    id_uc,
    case bioma_col
        when 'area_amazonia'      then 'Amazônia'
        when 'area_caatinga'      then 'Caatinga'
        when 'area_cerrado'       then 'Cerrado'
        when 'area_mata_atlantica' then 'Mata Atlântica'
        when 'area_pampa'         then 'Pampa'
        when 'area_pantanal'      then 'Pantanal'
    end as bioma,
    area_ha
from unpivoted
