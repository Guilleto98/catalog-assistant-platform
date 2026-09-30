"""Similarity tool supporting direct and reviewed-draft modes."""

from functools import lru_cache
from typing import Any

from google.adk.tools import ToolContext

from ..clients import CatalogApiError, get_catalog_api_client
from ..config import get_settings
from ..domain.errors import IntakeError
from ..repositories import DraftRepository
from ..services import DraftService, DraftSimilarityMapper, FieldMetadataService
from ..state import CONVERSATION_ID, CURRENT_REQUEST_DRAFT_ID, LAST_SIMILARITY
from ._result import failure, invalid, success


@lru_cache
def _draft_service() -> DraftService:
    return DraftService(DraftRepository(get_settings().intake_database_path))


@lru_cache
def _metadata_service() -> FieldMetadataService:
    return FieldMetadataService(get_catalog_api_client())


async def find_similar_articles(
    tool_context: ToolContext,
    reference_code: str | None = None,
    features: dict[str, Any] | None = None,
    required: dict[str, Any] | None = None,
    use_current_draft: bool = False,
    include_proposed: bool = False,
    limit: int = 10,
) -> dict[str, Any]:
    """Find similar articles while preserving API eligibility decisions.

    Choose exactly one mode: reference_code, explicit features, or
    use_current_draft=true. Required values are hard eligibility conditions;
    similarity score never overrides INELIGIBLE. For a reviewed document request,
    use_current_draft=true so deterministic code maps its fields. Set
    include_proposed=true only when the user explicitly accepts unconfirmed data.
    """
    modes = int(bool(reference_code)) + int(features is not None) + int(use_current_draft)
    if modes != 1:
        return invalid("Elegí exactamente un modo: reference_code, features o borrador actual.")
    if not isinstance(limit, int) or not 1 <= limit <= 10:
        return invalid("limit debe ser un entero entre 1 y 10.")
    if include_proposed and not use_current_draft:
        return invalid("include_proposed sólo aplica al borrador actual.")
    mapping_payload: dict[str, Any] | None = None
    draft_id: str | None = None
    try:
        if use_current_draft:
            conversation_id = tool_context.state.get(CONVERSATION_ID)
            draft_id = tool_context.state.get(CURRENT_REQUEST_DRAFT_ID)
            if not isinstance(conversation_id, str) or not isinstance(draft_id, str):
                return invalid("No hay un borrador asociado a esta conversación.")
            from ..platform.context import intake_drafts
            service = intake_drafts.get() or _draft_service()
            draft = service.get(draft_id, conversation_id)
            mapping = DraftSimilarityMapper().map(
                draft, await _metadata_service().fields(),
                include_proposed=include_proposed,
            )
            mapping_payload = mapping.model_dump(mode="json", by_alias=True)
            if not mapping.features:
                return {
                    "ok": False,
                    "error": {
                        "code": "NO_USABLE_SIMILARITY_CRITERIA",
                        "message": "El borrador no contiene criterios activos utilizables para similitud.",
                        "retryable": False,
                        "category": "validation",
                        "details": mapping_payload,
                    },
                }
            request = {"features": mapping.features, "required": mapping.required, "limit": limit}
        else:
            request = {
                "reference_code": reference_code,
                "features": features,
                "required": required or {},
                "limit": limit,
            }
        data = await get_catalog_api_client().find_similar_articles(**request)
    except CatalogApiError as error:
        return failure(error)
    except IntakeError as error:
        return {"ok": False, "error": {"code": error.code, "message": error.message}}
    eligible = [str(item["codigo"]) for item in data.get("eligibleCandidates", [])]
    ineligible = [str(item["codigo"]) for item in data.get("ineligibleCandidates", [])]
    mode = "draft" if use_current_draft else "reference" if reference_code else "features"
    tool_context.state[LAST_SIMILARITY] = {
        "mode": mode,
        "draft_id": draft_id,
        "reference_code": reference_code,
        "eligible_codes": eligible,
        "ineligible_codes": ineligible,
    }
    response: dict[str, Any] = {"result": data}
    if mapping_payload is not None:
        response["draftMapping"] = mapping_payload
    return success(response)
