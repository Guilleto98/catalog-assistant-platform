"""Thin authenticated HTTP routes; application behavior lives in services."""

from datetime import datetime
from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response, Security
from fastapi.security import APIKeyCookie

from . import contracts as c
from .auth import COOKIE
from .models import User
from .policies import RequestLimits
from .requests import LoginRequest, SendMessageRequest

ERROR_HTTP_STATUSES = (
    HTTPStatus.BAD_REQUEST,
    HTTPStatus.UNAUTHORIZED,
    HTTPStatus.FORBIDDEN,
    HTTPStatus.NOT_FOUND,
    HTTPStatus.CONFLICT,
    HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
    HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
    HTTPStatus.UNPROCESSABLE_ENTITY,
    HTTPStatus.INTERNAL_SERVER_ERROR,
    HTTPStatus.BAD_GATEWAY,
    HTTPStatus.SERVICE_UNAVAILABLE,
)
ERROR_RESPONSES = {status: {"model": c.ApiError} for status in ERROR_HTTP_STATUSES}
cookie_scheme = APIKeyCookie(name=COOKIE, auto_error=False, scheme_name="CookieSession")

Page = Annotated[int, Query(ge=RequestLimits.PAGE_INDEX_ORIGIN)]
PageSize = Annotated[
    int,
    Query(
        ge=RequestLimits.PAGE_INDEX_ORIGIN,
        le=RequestLimits.MAX_PAGE_SIZE,
    ),
]


def authenticated(
    request: Request,
    token: str | None = Security(cookie_scheme),
) -> User:
    return request.app.state.platform.authenticate(token)


def internal_admin(
    request: Request,
    user: User = Depends(authenticated),
) -> User:
    return request.app.state.platform.require_internal_admin(user)


def require_conversation_access(
    conversation_id: str,
    request: Request,
    user: User = Depends(authenticated),
) -> User:
    return request.app.state.platform.require_conversation_access(user, conversation_id)


def require_active_conversation(
    conversation_id: str,
    request: Request,
    user: User = Depends(authenticated),
) -> User:
    return request.app.state.platform.require_active_conversation(user, conversation_id)


def router() -> APIRouter:
    routes = APIRouter(responses=ERROR_RESPONSES)

    @routes.post("/auth/login", tags=["auth"], response_model=c.CurrentUserDto)
    async def login(
        body: LoginRequest,
        request: Request,
        response: Response,
    ) -> c.CurrentUserDto:
        platform = request.app.state.platform
        raw, user = platform.auth.login(body.email, body.password, request.state.request_id)
        response.set_cookie(
            COOKIE,
            raw,
            max_age=platform.settings.auth_session_ttl,
            httponly=True,
            secure=platform.settings.auth_cookie_secure,
            samesite="lax",
            path="/",
        )
        response.headers["Cache-Control"] = "no-store"
        return platform.current_user(user)

    @routes.post("/auth/logout", tags=["auth"], response_model=c.OkDto)
    async def logout(
        request: Request,
        response: Response,
        user: User = Depends(authenticated),
    ) -> c.OkDto:
        platform = request.app.state.platform
        platform.auth.logout(
            request.cookies[COOKIE], user, request.state.request_id
        )
        response.delete_cookie(
            COOKIE,
            path="/",
            httponly=True,
            secure=platform.settings.auth_cookie_secure,
            samesite="lax",
        )
        return c.OkDto()

    @routes.get("/auth/me", tags=["auth"], response_model=c.CurrentUserDto)
    async def me(
        request: Request,
        user: User = Depends(authenticated),
    ) -> c.CurrentUserDto:
        return request.app.state.platform.current_user(user)

    @routes.get(
        "/saved-filters", tags=["saved-filters"], response_model=c.SavedFilterListPayload
    )
    async def saved_filters(
        request: Request,
        user: User = Depends(authenticated),
    ) -> c.SavedFilterListPayload:
        return await request.app.state.platform.saved_filters(user)

    @routes.post(
        "/conversations",
        status_code=HTTPStatus.CREATED,
        tags=["conversations"],
        response_model=c.ConversationSummaryDto,
    )
    async def create_conversation(
        request: Request,
        user: User = Depends(authenticated),
    ) -> c.ConversationSummaryDto:
        return await request.app.state.platform.create_conversation(
            user, request.state.request_id
        )

    @routes.get(
        "/conversations",
        tags=["conversations"],
        response_model=c.PageDto[c.ConversationSummaryDto],
    )
    async def conversations(
        request: Request,
        page: Page = RequestLimits.PAGE_INDEX_ORIGIN,
        pageSize: PageSize = RequestLimits.DEFAULT_PAGE_SIZE,
        user: User = Depends(authenticated),
    ) -> c.PageDto[c.ConversationSummaryDto]:
        return request.app.state.platform.list_conversations(user, page, pageSize)

    @routes.get(
        "/conversations/{conversation_id}",
        tags=["conversations"],
        response_model=c.ConversationSummaryDto,
    )
    async def conversation(
        conversation_id: str,
        request: Request,
        user: User = Depends(require_conversation_access),
    ) -> c.ConversationSummaryDto:
        return request.app.state.platform.get_conversation(user, conversation_id)

    @routes.get(
        "/conversations/{conversation_id}/messages",
        tags=["messages"],
        response_model=c.PageDto[c.MessageDto],
    )
    async def messages(
        conversation_id: str,
        request: Request,
        page: Page = RequestLimits.PAGE_INDEX_ORIGIN,
        pageSize: PageSize = RequestLimits.DEFAULT_PAGE_SIZE,
        user: User = Depends(require_conversation_access),
    ) -> c.PageDto[c.MessageDto]:
        return request.app.state.platform.list_messages(
            user, conversation_id, page, pageSize
        )

    @routes.post(
        "/conversations/{conversation_id}/messages",
        tags=["messages"],
        response_model=c.SendMessageResponse,
    )
    async def send_message(
        conversation_id: str,
        body: SendMessageRequest,
        request: Request,
        user: User = Depends(require_conversation_access),
    ) -> c.SendMessageResponse:
        return await request.app.state.platform.send_message(
            user, conversation_id, body, request.state.request_id
        )

    @routes.post(
        "/conversations/{conversation_id}/archive",
        tags=["conversations"],
        response_model=c.ConversationSummaryDto,
    )
    async def archive_conversation(
        conversation_id: str,
        request: Request,
        user: User = Depends(require_conversation_access),
    ) -> c.ConversationSummaryDto:
        return request.app.state.platform.archive_conversation(
            user, conversation_id, request.state.request_id
        )

    @routes.get(
        "/admin/organizations",
        tags=["admin"],
        response_model=c.PageDto[c.AdminOrganizationDto],
    )
    async def organizations(
        request: Request,
        page: Page = RequestLimits.PAGE_INDEX_ORIGIN,
        pageSize: PageSize = RequestLimits.DEFAULT_PAGE_SIZE,
        status: str | None = None,
        _user: User = Depends(internal_admin),
    ) -> c.PageDto[c.AdminOrganizationDto]:
        return request.app.state.platform.admin.list_organizations(page, pageSize, status)

    @routes.get("/admin/users", tags=["admin"], response_model=c.PageDto[c.AdminUserDto])
    async def users(
        request: Request,
        page: Page = RequestLimits.PAGE_INDEX_ORIGIN,
        pageSize: PageSize = RequestLimits.DEFAULT_PAGE_SIZE,
        organizationId: str | None = None,
        status: str | None = None,
        _user: User = Depends(internal_admin),
    ) -> c.PageDto[c.AdminUserDto]:
        return request.app.state.platform.admin.list_users(
            page, pageSize, organizationId, status
        )

    @routes.get(
        "/admin/conversations",
        tags=["admin"],
        response_model=c.PageDto[c.AdminConversationDto],
    )
    async def admin_conversations(
        request: Request,
        page: Page = RequestLimits.PAGE_INDEX_ORIGIN,
        pageSize: PageSize = RequestLimits.DEFAULT_PAGE_SIZE,
        organizationId: str | None = None,
        userId: str | None = None,
        status: str | None = None,
        _user: User = Depends(internal_admin),
    ) -> c.PageDto[c.AdminConversationDto]:
        return request.app.state.platform.admin.list_conversations(
            page, pageSize, organizationId, userId, status
        )

    @routes.get(
        "/admin/conversations/{conversation_id}",
        tags=["admin"],
        response_model=c.AdminConversationDetailDto,
    )
    async def admin_conversation(
        conversation_id: str,
        request: Request,
        user: User = Depends(internal_admin),
    ) -> c.AdminConversationDetailDto:
        return request.app.state.platform.admin.get_conversation(
            user, conversation_id, request.state.request_id
        )

    @routes.get("/admin/runs", tags=["admin"], response_model=c.PageDto[c.AdminAgentRunDto])
    async def runs(
        request: Request,
        page: Page = RequestLimits.PAGE_INDEX_ORIGIN,
        pageSize: PageSize = RequestLimits.DEFAULT_PAGE_SIZE,
        conversationId: str | None = None,
        status: str | None = None,
        scopeDecision: str | None = None,
        errorCode: str | None = None,
        toolName: str | None = None,
        organizationId: str | None = None,
        userId: str | None = None,
        dateFrom: datetime | None = None,
        dateTo: datetime | None = None,
        _user: User = Depends(internal_admin),
    ) -> c.PageDto[c.AdminAgentRunDto]:
        return request.app.state.platform.admin.list_runs(
            page,
            pageSize,
            conversation_id=conversationId,
            status=status,
            scope_decision=scopeDecision,
            error_code=errorCode,
            tool_name=toolName,
            organization_id=organizationId,
            user_id=userId,
            date_from=dateFrom,
            date_to=dateTo,
        )

    @routes.get("/admin/runs/{run_id}", tags=["admin"], response_model=c.AdminRunDetailDto)
    async def run_detail(
        run_id: str,
        request: Request,
        user: User = Depends(internal_admin),
    ) -> c.AdminRunDetailDto:
        return request.app.state.platform.admin.get_run(
            user, run_id, request.state.request_id
        )

    @routes.get(
        "/admin/audit-events",
        tags=["admin"],
        response_model=c.PageDto[c.AdminAuditEventDto],
    )
    async def audit_events(
        request: Request,
        page: Page = RequestLimits.PAGE_INDEX_ORIGIN,
        pageSize: PageSize = RequestLimits.DEFAULT_PAGE_SIZE,
        organizationId: str | None = None,
        conversationId: str | None = None,
        userId: str | None = None,
        eventType: str | None = None,
        dateFrom: datetime | None = None,
        dateTo: datetime | None = None,
        _user: User = Depends(internal_admin),
    ) -> c.PageDto[c.AdminAuditEventDto]:
        return request.app.state.platform.admin.list_audit_events(
            page,
            pageSize,
            organization_id=organizationId,
            conversation_id=conversationId,
            user_id=userId,
            event_type=eventType,
            date_from=dateFrom,
            date_to=dateTo,
        )

    return routes
