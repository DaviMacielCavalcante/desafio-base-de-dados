"""Testes unitários das funções puras de pipelines/transform.py.

Cobrem só as transformações que carregam lógica (split, regex, cast, normalização
e os guard-rails que levantam erro). O `transform()` completo não é testado aqui:
ele escreve parquet em disco — IO foge do escopo de teste unitário.
"""

import polars as pl
import pytest

from pipelines.transform import (
    REQUIRED_COLUMNS,
    build_municipios_struct,
    cast_columns,
    check_duplicates_uc_codes,
    normalize_categoricals,
    normalize_municipio,
    normalize_sentinels,
    validate_schema,
)


def _municipios(values: list[str | None]) -> pl.DataFrame:
    """DF mínimo com só a coluna que build_municipios_struct consome."""
    return pl.DataFrame(
        {"Municípios Abrangidos": values},
        schema={"Municípios Abrangidos": pl.String},
    )


class TestBuildMunicipiosStruct:
    """Split por ' - ' + extração de (UF) + nome normalizado."""

    def test_municipio_unico_separa_uf_do_nome(self):
        """'Abaetetuba (PA)' vira um struct com nome sem o sufixo '(PA)'."""
        out = build_municipios_struct(_municipios(["Abaetetuba (PA)"]))
        assert out["Municípios Abrangidos"].to_list() == [
            [{"nome": "Abaetetuba", "sigla_uf": "PA", "nome_norm": "abaetetuba"}]
        ]

    def test_multi_municipio_split_por_separador(self):
        """Separador ' - ' quebra a string em uma lista de structs."""
        out = build_municipios_struct(_municipios(["Altamira (PA) - São Félix do Xingu (PA)"]))
        result = out["Municípios Abrangidos"].to_list()[0]
        assert [m["nome"] for m in result] == ["Altamira", "São Félix do Xingu"]
        assert [m["sigla_uf"] for m in result] == ["PA", "PA"]

    def test_nome_norm_remove_acento_e_caixa(self):
        """nome_norm aplica unidecode + lower (chave de match com o IBGE)."""
        out = build_municipios_struct(_municipios(["São Félix do Xingu (PA)"]))
        assert out["Municípios Abrangidos"].to_list()[0][0]["nome_norm"] == ("sao felix do xingu")

    def test_hifen_interno_no_nome_nao_quebra(self):
        """Hífen colado (sem espaços) não é confundido com o separador ' - '."""
        out = build_municipios_struct(_municipios(["Pau-Brasil (BA)"]))
        result = out["Municípios Abrangidos"].to_list()[0]
        assert len(result) == 1
        assert result[0]["nome"] == "Pau-Brasil"

    def test_uc_marinha_null_vira_null(self):
        """UC sem município (valor null) não quebra e permanece null."""
        out = build_municipios_struct(_municipios([None]))
        assert out["Municípios Abrangidos"].to_list() == [None]


class TestCastColumns:
    """Sim/Não -> 1/0 e floats no formato brasileiro."""

    def test_sim_nao_vira_inteiro(self):
        """Coluna textual em INT_COLUMNS mapeia Sim->1 / Não->0 como Int64."""
        df = pl.DataFrame({"Plano de Manejo": ["Sim", "Não"]})
        out = cast_columns(df)
        assert out["Plano de Manejo"].dtype == pl.Int64
        assert out["Plano de Manejo"].to_list() == [1, 0]

    def test_float_formato_brasileiro(self):
        """'1.234,56' (ponto de milhar, vírgula decimal) vira 1234.56 Float64."""
        df = pl.DataFrame({"Área soma biomas": ["1.234,56"]})
        out = cast_columns(df)
        assert out["Área soma biomas"].dtype == pl.Float64
        assert out["Área soma biomas"].to_list() == [1234.56]

    def test_inteiro_numerico_apenas_faz_cast(self):
        """Coluna já numérica em INT_COLUMNS só recebe cast para Int64."""
        df = pl.DataFrame({"PI": [1, 0]})
        out = cast_columns(df)
        assert out["PI"].dtype == pl.Int64
        assert out["PI"].to_list() == [1, 0]


class TestNormalizeMunicipio:
    """Função pura: chave de match (lower + sem acento)."""

    def test_none_retorna_none(self):
        assert normalize_municipio(None) is None

    def test_remove_acento_e_caixa(self):
        assert normalize_municipio("São Paulo") == "sao paulo"

    def test_maiuscula_vira_minuscula(self):
        assert normalize_municipio("BRASÍLIA") == "brasilia"


class TestNormalizeSentinels:
    """'Sem informação.' vira null nas colunas com sentinela."""

    def test_sentinela_vira_null(self):
        df = pl.DataFrame(
            {
                "Outros atos legais": ["Sem informação.", "Lei 123"],
                "Código WDPA": ["Sem informação.", "555"],
            }
        )
        out = normalize_sentinels(df)
        assert out["Outros atos legais"].to_list() == [None, "Lei 123"]
        assert out["Código WDPA"].to_list() == [None, "555"]


class TestNormalizeCategoricals:
    """Categoria IUCN perde o prefixo 'Category '."""

    def test_remove_prefixo_category(self):
        df = pl.DataFrame({"Categoria IUCN": ["Category II", "Category V"]})
        out = normalize_categoricals(df)
        assert out["Categoria IUCN"].to_list() == ["II", "V"]


class TestValidateSchema:
    """Guard-rail: aborta se faltar coluna obrigatória."""

    def test_coluna_faltando_levanta_erro(self):
        df = pl.DataFrame({"Código UC": ["1"]})  # faltam as demais obrigatórias
        with pytest.raises(ValueError, match="Colunas não encontradas"):
            validate_schema(df)

    def test_schema_completo_nao_levanta(self):
        df = pl.DataFrame({col: [None] for col in REQUIRED_COLUMNS})
        validate_schema(df)  # não deve levantar


class TestCheckDuplicatesUcCodes:
    """Guard-rail: aborta se houver Código UC duplicado."""

    def test_duplicado_levanta_erro(self):
        df = pl.DataFrame({"Código UC": ["1", "1", "2"]})
        with pytest.raises(ValueError, match="Duplicated data found"):
            check_duplicates_uc_codes(df)

    def test_codigos_unicos_nao_levanta(self):
        df = pl.DataFrame({"Código UC": ["1", "2", "3"]})
        check_duplicates_uc_codes(df)  # não deve levantar
