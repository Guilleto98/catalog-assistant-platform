import os

import pytest

from solvo_client_agent.clients import CatalogApiClient


pytestmark = pytest.mark.integration


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.getenv("RUN_CATALOG_INTEGRATION") != "1",
    reason="set RUN_CATALOG_INTEGRATION=1 with the Catalog API running",
)
async def test_known_bife_ancho_china_benchmark():
    client = CatalogApiClient(
        os.getenv("CATALOG_API_BASE_URL", "http://localhost:3000/api/v1")
    )
    result = await client.search_articles(
        filters=[
            {"field": "producto_destino.corte", "operator": "eq", "value": "BIFE_ANCHO"},
            {"field": "producto_destino.mercado", "operator": "eq", "value": "CHINA"},
        ],
        page_size=50,
    )
    assert [item["codigo"] for item in result["items"]] == ["900001"]


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.getenv("RUN_CATALOG_INTEGRATION") != "1",
    reason="set RUN_CATALOG_INTEGRATION=1 with the Catalog API running",
)
async def test_complete_catalog_capabilities_and_eligibility_boundary():
    client = CatalogApiClient(os.getenv("CATALOG_API_BASE_URL", "http://localhost:3000/api/v1"))
    by_reference = await client.find_similar_articles(
        reference_code="900001",
        required={
            "producto_destino.mercado": "CHINA",
            "producto_destino.temperatura": "CONGELADO",
        },
    )
    assert by_reference["eligibleCandidates"][0]["codigo"] == "900006"
    rejected = next(item for item in by_reference["ineligibleCandidates"] if item["codigo"] == "900004")
    assert rejected["similarityScore"] == 90
    assert rejected["eligibility"] == "INELIGIBLE"
    by_features = await client.find_similar_articles(features={"identificacion.especie": "BOVINO"}, limit=1)
    assert by_features["eligibleCandidates"][0]["codigo"] == "900001"
    sheet = await client.get_technical_sheet(codigo="900001")
    assert sheet["fichaId"] == "FT-DEMO-900001"
    fields = await client.get_filterable_fields()
    market = next(item for item in fields if item["path"] == "producto_destino.mercado")
    assert market["usedForSimilarity"] is True
    assert market["canBeRequired"] is True
