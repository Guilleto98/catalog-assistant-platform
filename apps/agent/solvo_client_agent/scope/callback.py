"""Google ADK 2.10 before-model callback for semantic domain scope."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from ..config import Settings
from ..state.keys import (
    CURRENT_REQUEST_DRAFT_ID,
    CURRENT_SEARCH,
    DOMAIN_SCOPE_DECISION,
    DOMAIN_SCOPE_LATENCY_MS,
    DOMAIN_SCOPE_REASON,
    DOMAIN_SCOPE_ROOT_SKIPPED,
    LAST_ARTICLE_CODE,
    LAST_SEARCH_CODES,
)
from .guard import DomainScopeGuard, OpenAIDomainScopeClassifier
from .models import (
    DomainScopeDecision,
    DomainScopeInput,
    DomainScopeRequestKind,
)
from .policies import ScopePolicy


logger = logging.getLogger(__name__)

OUT_OF_SCOPE_RESPONSE = (
    "Estoy especializado en artículos de catálogo, fichas técnicas y "
    "especificaciones relacionadas. Si querés, puedo ayudarte con una consulta "
    "dentro de ese ámbito."
)
AMBIGUOUS_RESPONSE = (
    "Claro. ¿Qué necesitás revisar del artículo, ficha técnica o especificación?"
)
INTERNAL_CONFIGURATION_RESPONSE = (
    "No puedo mostrar instrucciones o configuración internas. Sí puedo explicarte "
    "qué tipo de tareas puedo realizar sobre artículos y fichas técnicas."
)


def _text(
    content: types.Content | None,
    limit: int = ScopePolicy.MAX_LATEST_MESSAGE_CHARACTERS,
) -> str:
    if content is None:
        return ""
    value = " ".join(
        part.text.strip()
        for part in content.parts or []
        if getattr(part, "text", None) and part.text.strip()
    )
    return value[:limit]


def _recent_context(callback_context: CallbackContext) -> list[str]:
    recent: list[str] = []
    for event in reversed(callback_context.session.events):
        content = getattr(event, "content", None)
        role = getattr(content, "role", None)
        if role not in {"user", "model"}:
            continue
        value = _text(content, ScopePolicy.MAX_RECENT_MESSAGE_CHARACTERS)
        if value:
            recent.append(f"{role}: {value}")
        if len(recent) == ScopePolicy.MAX_RECENT_MESSAGES:
            break
    return list(reversed(recent))


def _state_summary(state: Any) -> dict[str, str | bool | int | None]:
    current_search = state.get(CURRENT_SEARCH)
    last_codes = state.get(LAST_SEARCH_CODES)
    return {
        "current_search_active": bool(current_search),
        "last_search_result_count": len(last_codes) if isinstance(last_codes, list) else 0,
        "last_article_code": state.get(LAST_ARTICLE_CODE),
        "request_draft_active": bool(state.get(CURRENT_REQUEST_DRAFT_ID)),
    }


def _response(text: str, decision: str) -> LlmResponse:
    return LlmResponse(
        content=types.Content(role="model", parts=[types.Part(text=text)]),
        customMetadata={"domain_scope_decision": decision, "root_agent_skipped": True},
    )


class DomainScopeCallback:
    def __init__(self, settings: Settings, guard: DomainScopeGuard | None = None) -> None:
        self.enabled = settings.domain_scope_enabled
        self.guard = guard or DomainScopeGuard(
            OpenAIDomainScopeClassifier(
                settings.domain_scope_model, settings.domain_scope_timeout_seconds
            )
        )
        self._completed_invocations: dict[str, None] = {}

    async def __call__(
        self, callback_context: CallbackContext, llm_request: LlmRequest
    ) -> LlmResponse | None:
        if not self.enabled or callback_context.invocation_id in self._completed_invocations:
            return None
        self._completed_invocations[callback_context.invocation_id] = None
        if len(self._completed_invocations) > ScopePolicy.MAX_TRACKED_INVOCATIONS:
            self._completed_invocations.pop(next(iter(self._completed_invocations)))
        latest = _text(callback_context.user_content)
        if not latest:
            return None
        started = time.perf_counter()
        try:
            result = await self.guard.decide(
                DomainScopeInput(
                    latest_message=latest,
                    recent_context=_recent_context(callback_context),
                    state_summary=_state_summary(callback_context.state),
                )
            )
        except Exception as error:
            latency = round((time.perf_counter() - started) * 1000, 1)
            callback_context.state[DOMAIN_SCOPE_DECISION] = "FAIL_OPEN"
            callback_context.state[DOMAIN_SCOPE_REASON] = type(error).__name__
            callback_context.state[DOMAIN_SCOPE_LATENCY_MS] = latency
            callback_context.state[DOMAIN_SCOPE_ROOT_SKIPPED] = False
            logger.warning(
                "domain_scope %s",
                json.dumps(
                    {
                        "conversationId": callback_context.session.id,
                        "decision": "FAIL_OPEN",
                        "reason": type(error).__name__,
                        "latencyMs": latency,
                    }
                ),
            )
            return None

        latency = round((time.perf_counter() - started) * 1000, 1)
        skip = result.request_kind != DomainScopeRequestKind.MIXED and (
            result.decision
            in {DomainScopeDecision.OUT_OF_SCOPE, DomainScopeDecision.AMBIGUOUS}
        )
        callback_context.state[DOMAIN_SCOPE_DECISION] = result.decision.value
        callback_context.state[DOMAIN_SCOPE_REASON] = result.reason
        callback_context.state[DOMAIN_SCOPE_LATENCY_MS] = latency
        callback_context.state[DOMAIN_SCOPE_ROOT_SKIPPED] = skip
        logger.info(
            "domain_scope %s",
            json.dumps(
                {
                    "conversationId": callback_context.session.id,
                    "decision": result.decision.value,
                    "reason": result.reason,
                    "latencyMs": latency,
                },
                ensure_ascii=False,
            ),
        )
        if result.request_kind == DomainScopeRequestKind.INTERNAL_CONFIGURATION:
            callback_context.state[DOMAIN_SCOPE_ROOT_SKIPPED] = True
            return _response(INTERNAL_CONFIGURATION_RESPONSE, result.decision.value)
        if result.request_kind == DomainScopeRequestKind.MIXED:
            llm_request.append_instructions(
                [
                    "La solicitud es mixta: atendé sólo la parte relacionada con "
                    "artículos/fichas y redirigí brevemente la parte externa."
                ]
            )
            return None
        if result.decision == DomainScopeDecision.OUT_OF_SCOPE:
            return _response(OUT_OF_SCOPE_RESPONSE, result.decision.value)
        if result.decision == DomainScopeDecision.AMBIGUOUS:
            return _response(AMBIGUOUS_RESPONSE, result.decision.value)
        return None
