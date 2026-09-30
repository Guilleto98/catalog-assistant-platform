"""Small process-local cache for the Catalog API field contract."""

import asyncio
import time
from typing import Any

from ..clients import CatalogApiClient


class FieldMetadataService:
    def __init__(self, client: CatalogApiClient, ttl_seconds: float = 300) -> None:
        self.client = client
        self.ttl_seconds = ttl_seconds
        self._fields: list[dict[str, Any]] | None = None
        self._expires_at = 0.0
        self._lock = asyncio.Lock()

    async def fields(self) -> list[dict[str, Any]]:
        now = time.monotonic()
        if self._fields is not None and now < self._expires_at:
            return self._fields
        async with self._lock:
            now = time.monotonic()
            if self._fields is None or now >= self._expires_at:
                self._fields = await self.client.get_filterable_fields()
                self._expires_at = now + self.ttl_seconds
        return self._fields
