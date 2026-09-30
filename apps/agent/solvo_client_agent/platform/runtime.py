"""Official ADK sessions and observable tool callbacks."""

import re
import time
import logging

from google.adk.apps import App
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from sqlalchemy import select

from ..domain.models import DraftReviewAction
from .database import private_path
from .models import ToolExecution, now
from .policies import AuditEventType, RuntimeAuditPolicy, ToolExecutionStatus
from .repository import audit

logger = logging.getLogger(__name__)


SENSITIVE = re.compile(r"password|secret|authorization|api.?key|token|cookie|prompt|reasoning|scratchpad|bytes|raw.?content", re.I)


def redact(value, depth=0):
    if depth > RuntimeAuditPolicy.MAX_REDACTION_DEPTH:
        return "[TRUNCATED]"
    if isinstance(value, dict):
        return {str(k): "[REDACTED]" if SENSITIVE.search(str(k)) else redact(v, depth + 1)
                for k, v in list(value.items())[:RuntimeAuditPolicy.MAX_REDACTED_COLLECTION_ITEMS]}
    if isinstance(value, list):
        return [redact(v, depth + 1) for v in value[:RuntimeAuditPolicy.MAX_REDACTED_COLLECTION_ITEMS]]
    if isinstance(value, str):
        value = re.sub(r"sk-[A-Za-z0-9_-]+|Bearer\s+\S+", "[REDACTED]", value)
        return value[:RuntimeAuditPolicy.MAX_REDACTED_TEXT_CHARACTERS]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return "[REDACTED]"


def result_summary(name, result):
    if not result.get("ok", True):
        return {"ok": False, "errorCode": result.get("error", {}).get("code", "TOOL_FAILED")}
    data = result.get("data", {})
    if name in {"get_request_draft", "update_request_draft", "review_request_draft"}:
        return {"draftId": data.get("id"), "status": data.get("status"), "fieldCount": len(data.get("fields", []))}
    if name == "find_similar_articles":
        data = data.get("result", data)
        return {"eligibleCount": len(data.get("eligibleCandidates", [])),
                "ineligibleCount": len(data.get("ineligibleCandidates", [])),
                "eligibleCodes": [v.get("codigo") for v in data.get("eligibleCandidates", [])],
                "ineligibleCodes": [v.get("codigo") for v in data.get("ineligibleCandidates", [])]}
    if "items" in data:
        return {"count": len(data["items"]), "codes": [v.get("codigo", v.get("id")) for v in data["items"]],
                "pagination": data.get("pagination")}
    if "comparedCodes" in data:
        return {"comparedCodes": data["comparedCodes"], "differentFieldsCount": data.get("differentFieldsCount")}
    if "fields" in data:
        return {"fieldCount": len(data["fields"])}
    if "identificacion" in data:
        return {"codigo": data["identificacion"].get("codigo")}
    return redact({k: data[k] for k in ("id", "name", "fichaId", "articuloCodigo", "deleted") if k in data})
    

class PrivateDatabaseSessionService(DatabaseSessionService):
    """Filter private reasoning at the public persistence boundary."""

    async def append_event(self, session, event):
        safe = event.model_copy(deep=True)
        if safe.content:
            safe.content.parts = [p.model_copy(update={"thought_signature": None})
                                  for p in safe.content.parts or [] if not p.thought]
        return await super().append_event(session, safe)


class ToolAuditPlugin(BasePlugin):
    def __init__(self, database, run_id, user, request_id, conversation_id):
        super().__init__(name="product_tool_audit")
        self.database, self.run_id, self.user = database, run_id, user
        self.request_id, self.conversation_id = request_id, conversation_id
        self.active = {}
        self.sequence = 0
        self.ui_events = []
        self.presenter_latency_ms = 0.0

    async def before_tool_callback(self, *, tool, tool_args, tool_context):
        self.sequence += 1
        with self.database.session.begin() as db:
            row = ToolExecution(agent_run_id=self.run_id, sequence=self.sequence,
                                tool_name=tool.name, arguments_json=redact(tool_args))
            db.add(row)
            db.flush()
            self.active[tool_context.function_call_id] = (row.id, time.perf_counter())

    def finish(self, tool_context, summary, failed):
        entry = self.active.pop(tool_context.function_call_id, None)
        if not entry:
            return
        with self.database.session.begin() as db:
            row = db.get(ToolExecution, entry[0])
            row.completed_at = now()
            row.duration_ms = (time.perf_counter() - entry[1]) * 1000
            row.status = ToolExecutionStatus.FAILED if failed else ToolExecutionStatus.COMPLETED
            row.error_code = summary.get("errorCode")
            row.result_summary_json = summary
            logger.info("tool_execution request_id=%s conversation_id=%s agent_run_id=%s tool_name=%s status=%s duration_ms=%.1f",
                        self.request_id, self.conversation_id, self.run_id, row.tool_name, row.status, row.duration_ms)
            audit(db, AuditEventType.TOOL_EXECUTED, user=self.user, request_id=self.request_id,
                  conversation_id=self.conversation_id, agent_run_id=self.run_id,
                  entity_type="ToolExecution", entity_id=row.id,
                  metadata={"toolName": row.tool_name, "status": row.status})
            if row.tool_name in {"update_request_draft", "review_request_draft"} and not failed:
                audit(db, AuditEventType.REQUEST_DRAFT_UPDATED, user=self.user, request_id=self.request_id,
                      conversation_id=self.conversation_id, agent_run_id=self.run_id,
                      entity_id=summary.get("draftId"), entity_type="ArticleRequestDraft")

    async def after_tool_callback(self, *, tool, tool_args, tool_context, result):
        from .presenters import present
        started = time.perf_counter()
        self.ui_events.extend((tool.name, kind, payload) for kind, payload in
                              present(tool.name, result, tool_args, tool_context.state))
        self.presenter_latency_ms += (time.perf_counter() - started) * 1000
        summary = result_summary(tool.name, result)
        self.finish(tool_context, summary, not result.get("ok", True))
        if (
            tool.name in {"update_request_draft", "review_request_draft"}
            and result.get("ok")
            and tool_args.get("action") == DraftReviewAction.CONFIRM
        ):
            with self.database.session.begin() as db:
                audit(db, AuditEventType.REQUEST_DRAFT_CONFIRMED, user=self.user, request_id=self.request_id,
                      conversation_id=self.conversation_id, agent_run_id=self.run_id,
                      entity_id=summary.get("draftId"), entity_type="ArticleRequestDraft")

    async def on_tool_error_callback(self, *, tool, tool_args, tool_context, error):
        self.finish(tool_context, {"errorCode": "TOOL_EXECUTION_FAILED"}, True)


class AgentRuntime:
    app_name = "solvo_client_product"

    def __init__(self, path, agent=None):
        private_path(path)
        self.sessions = PrivateDatabaseSessionService(db_url=f"sqlite+aiosqlite:///{path}")
        self.agent = agent

    async def create_session(self, user_id, conversation_id):
        session = await self.sessions.create_session(
            app_name=self.app_name, user_id=f"app:{user_id}", state={"conversation_id": conversation_id})
        return session.id

    async def execute(self, user, conversation, text, plugin):
        from google.genai import types
        from ..agent import root_agent
        forbidden = {"create_article", "clone_article", "preview_mutation", "confirm_mutation"}
        if any(getattr(tool, "__name__", getattr(tool, "name", "")) in forbidden
               for tool in (self.agent or root_agent).tools):
            raise RuntimeError("Mutations require security review of FAIL_OPEN first")
        runner = Runner(app=App(name=self.app_name, root_agent=self.agent or root_agent,
                                plugins=[plugin]), session_service=self.sessions)
        answer = []
        invocation_id = None
        input_tokens = output_tokens = None
        async for event in runner.run_async(user_id=f"app:{user.id}", session_id=conversation.adk_session_id,
                new_message=types.Content(role="user", parts=[types.Part(text=text)])):
            invocation_id = event.invocation_id
            if event.error_code:
                raise RuntimeError("Agent returned error")
            if event.is_final_response() and event.content:
                answer = [p.text for p in event.content.parts or [] if p.text and not p.thought]
            if event.usage_metadata and not event.partial:
                usage = event.usage_metadata
                if usage.prompt_token_count is not None:
                    input_tokens = (input_tokens or 0) + usage.prompt_token_count
                if usage.candidates_token_count is not None:
                    output_tokens = (output_tokens or 0) + usage.candidates_token_count
        if not answer:
            raise RuntimeError("No assistant response")
        session = await self.sessions.get_session(app_name=self.app_name, user_id=f"app:{user.id}",
                                                   session_id=conversation.adk_session_id)
        return {"text": "\n".join(answer), "state": session.state, "invocation_id": invocation_id,
                "input_tokens": input_tokens, "output_tokens": output_tokens}

    async def close(self):
        await self.sessions.close()
