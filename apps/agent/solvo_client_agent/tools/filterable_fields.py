"""Catalog metadata tool with a bounded process-local cache."""

from functools import lru_cache
from typing import Any

from ..clients import CatalogApiError, get_catalog_api_client
from ..services import FieldMetadataService
from ._result import failure, success


@lru_cache
def _metadata_service() -> FieldMetadataService:
    return FieldMetadataService(get_catalog_api_client())


async def get_filterable_fields() -> dict[str, Any]:
    """List authoritative filter, similarity and required-field metadata.

    Use when an exact field path, allowed value, operator, similarity support or
    required-field support is uncertain. Never infer enum values absent here.
    """
    try:
        fields = await _metadata_service().fields()
    except CatalogApiError as error:
        return failure(error)
    return success({"fields": fields})
