"""Paid smoke test for structured document intake. No catalog writes occur."""

import asyncio

from solvo_client_agent.clients import get_catalog_api_client
from solvo_client_agent.config import get_settings
from solvo_client_agent.services import DocumentExtractionService, OpenAIStructuredExtractor


async def main() -> None:
    metadata = await get_catalog_api_client().get_filterable_fields()
    service = DocumentExtractionService(
        OpenAIStructuredExtractor(get_settings().document_extraction_model)
    )
    fields = await service.extract_fields(
        "att_smoke",
        "SPREADSHEET",
        [
            {"sheet": "Pedido", "cell": "A1", "value": "Corte"},
            {"sheet": "Pedido", "cell": "B1", "value": "Bife ancho"},
            {"sheet": "Pedido", "cell": "A2", "value": "Mercado obligatorio"},
            {"sheet": "Pedido", "cell": "B2", "value": "Brasil"},
            {"sheet": "Pedido", "cell": "A3", "value": "Envase preferido"},
            {"sheet": "Pedido", "cell": "B3", "value": "Vacío"},
        ],
        metadata,
    )
    print(
        [
            {
                "field": item.field,
                "value": item.normalized_value,
                "required": item.required,
                "cell": item.source.cell,
            }
            for item in fields
        ]
    )


if __name__ == "__main__":
    asyncio.run(main())
