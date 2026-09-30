"""Single HTTP boundary between the agent and the Catalog API."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import logging
import time
from typing import Any
from urllib.parse import quote

import httpx

from ..config import get_settings


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CatalogApiError(Exception):
    code: str
    message: str
    retryable: bool
    category: str
    status_code: int | None = None

    def __str__(self) -> str:
        return self.message

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
            "category": self.category,
        }


def _camel_key(key: str) -> str:
    if "." in key:
        return key
    head, *tail = key.split("_")
    return head + "".join(part.capitalize() for part in tail)


def _camelize(value: Any) -> Any:
    if isinstance(value, dict):
        return {_camel_key(str(key)): _camelize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_camelize(item) for item in value]
    return value


class CatalogApiClient:
    """Async, timeout-bound client with normalized JSON responses and errors."""

    def __init__(
        self,
        base_url: str,
        timeout_seconds: float = 10,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = httpx.Timeout(timeout_seconds)
        self.transport = transport

    async def search_articles(
        self,
        filters: list[dict[str, Any]] | None = None,
        sort: list[dict[str, Any]] | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/articles/search",
            json={
                "filters": filters or [],
                "sort": sort or [],
                "page": page,
                "page_size": page_size,
            },
        )

    async def get_article(self, codigo: str) -> dict[str, Any]:
        return await self._request("GET", f"/articles/{quote(codigo, safe='')}")

    async def compare_articles(self, codes: list[str]) -> dict[str, Any]:
        return await self._request("POST", "/articles/compare", json={"codes": codes})

    async def find_similar_articles(
        self,
        *,
        reference_code: str | None = None,
        features: dict[str, Any] | None = None,
        required: dict[str, Any] | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"limit": limit}
        if reference_code is not None:
            payload["reference_code"] = reference_code
        if features is not None:
            payload["features"] = features
        if required:
            payload["required"] = required
        return await self._request("POST", "/articles/similar", json=payload)

    async def get_technical_sheet(
        self, *, codigo: str | None = None, ficha_id: str | None = None
    ) -> dict[str, Any]:
        if codigo is not None:
            return await self._request(
                "GET", f"/articles/{quote(codigo, safe='')}/technical-sheet"
            )
        if ficha_id is not None:
            return await self._request(
                "GET", f"/technical-sheets/{quote(ficha_id, safe='')}"
            )
        raise ValueError("codigo or ficha_id is required")

    async def get_filterable_fields(self) -> list[dict[str, Any]]:
        payload = await self._request("GET", "/metadata/filterable-fields")
        fields = payload.get("fields")
        if not isinstance(fields, list):
            raise CatalogApiError(
                "INVALID_UPSTREAM_RESPONSE",
                "El catálogo devolvió metadatos inesperados.",
                False,
                "unexpected_upstream",
            )
        return fields

    async def save_filter(
        self,
        *,
        user_id: str,
        name: str,
        search: dict[str, Any],
        description: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"name": name, "search": search}
        if description is not None:
            payload["description"] = description
        return await self._request(
            "POST", "/saved-filters", json=payload, headers={"X-Demo-User-Id": user_id}
        )

    async def list_saved_filters(self, *, user_id: str) -> list[dict[str, Any]]:
        payload = await self._request(
            "GET", "/saved-filters", headers={"X-Demo-User-Id": user_id}
        )
        if not isinstance(payload, list):
            raise CatalogApiError(
                "INVALID_UPSTREAM_RESPONSE",
                "El catálogo devolvió una lista de filtros inesperada.",
                False,
                "unexpected_upstream",
            )
        return payload

    async def get_saved_filter(self, filter_id: str, *, user_id: str) -> dict[str, Any]:
        return await self._request(
            "GET",
            f"/saved-filters/{quote(filter_id, safe='')}",
            headers={"X-Demo-User-Id": user_id},
        )

    async def execute_saved_filter(
        self, filter_id: str, *, user_id: str
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/saved-filters/{quote(filter_id, safe='')}/execute",
            headers={"X-Demo-User-Id": user_id},
        )

    async def delete_saved_filter(self, filter_id: str, *, user_id: str) -> None:
        await self._request(
            "DELETE",
            f"/saved-filters/{quote(filter_id, safe='')}",
            headers={"X-Demo-User-Id": user_id},
        )

    async def _request(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        started = time.perf_counter()
        status = "error"
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                transport=self.transport,
            ) as client:
                response = await client.request(method, path, json=json, headers=headers)
            status = str(response.status_code)
            if response.is_error:
                self._raise_api_error(response)
            if response.status_code == 204:
                return None
            payload = response.json()
            if not isinstance(payload, (dict, list)):
                raise CatalogApiError(
                    "INVALID_UPSTREAM_RESPONSE",
                    "El catálogo devolvió una respuesta inesperada.",
                    False,
                    "unexpected_upstream",
                    response.status_code,
                )
            return _camelize(payload)
        except CatalogApiError:
            raise
        except httpx.TimeoutException as exc:
            status = "timeout"
            raise CatalogApiError(
                "CATALOG_API_TIMEOUT",
                "La consulta al catálogo excedió el tiempo disponible.",
                True,
                "timeout",
            ) from exc
        except httpx.RequestError as exc:
            status = "unavailable"
            raise CatalogApiError(
                "CATALOG_API_UNAVAILABLE",
                "No se pudo contactar al catálogo en este momento.",
                True,
                "api_unavailable",
            ) from exc
        except (ValueError, TypeError) as exc:
            status = "unexpected"
            raise CatalogApiError(
                "INVALID_UPSTREAM_RESPONSE",
                "El catálogo devolvió una respuesta inesperada.",
                False,
                "unexpected_upstream",
            ) from exc
        finally:
            logger.info(
                "catalog_api method=%s path=%s status=%s duration_ms=%.1f",
                method,
                path,
                status,
                (time.perf_counter() - started) * 1000,
            )

    @staticmethod
    def _raise_api_error(response: httpx.Response) -> None:
        try:
            payload = response.json()
            error = payload.get("error", {}) if isinstance(payload, dict) else {}
        except ValueError:
            error = {}
        code = str(error.get("code") or "CATALOG_API_ERROR")
        raw_message = error.get("message")
        message = (
            str(raw_message)
            if raw_message
            else "El catálogo no pudo completar la consulta."
        )
        if response.status_code == 404:
            category = "not_found"
            retryable = False
        elif response.status_code in {400, 422}:
            category = "validation"
            retryable = False
        elif response.status_code >= 500:
            category = "unexpected_upstream"
            retryable = True
        else:
            category = "api_error"
            retryable = False
        raise CatalogApiError(
            code, message, retryable, category, response.status_code
        )


@lru_cache
def get_catalog_api_client() -> CatalogApiClient:
    settings = get_settings()
    return CatalogApiClient(
        settings.catalog_api_base_url, settings.catalog_api_timeout_seconds
    )
