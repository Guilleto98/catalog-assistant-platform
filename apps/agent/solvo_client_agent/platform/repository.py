"""Shared product queries and append-only audit writes."""

from sqlalchemy import func, select

from ..domain.errors import IntakeError
from .models import AuditEvent, Conversation, User


def serialize(record):
    excluded = {"password_hash", "token_hash"}
    return {
        column.name: getattr(record, column.name)
        for column in record.__table__.columns
        if column.name not in excluded
    }


def audit(db, event_type, *, user=None, request_id, conversation_id=None,
          agent_run_id=None, entity_type=None, entity_id=None, metadata=None):
    event = AuditEvent(
        event_type=event_type, actor_type="USER" if user else "SYSTEM",
        actor_user_id=user.id if user else None,
        organization_id=user.organization_id if user else None,
        conversation_id=conversation_id, agent_run_id=agent_run_id,
        entity_type=entity_type, entity_id=entity_id, request_id=request_id,
        metadata_json=metadata or {},
    )
    db.add(event)
    return event


def conversation_access(db, user: User, conversation_id: str, *, admin=False):
    item = db.get(Conversation, conversation_id)
    if item is None or (not admin and (
        item.owner_user_id != user.id or item.organization_id != user.organization_id
    )):
        raise IntakeError("CONVERSATION_NOT_FOUND", "La conversación no existe.", 404)
    return item


def paginate(db, model, conditions, page, page_size, *, ascending=False):
    query = select(model).where(*conditions)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    records = db.scalars(query.order_by(model.created_at if ascending else model.created_at.desc(), model.id)
                         .offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": [serialize(item) for item in records], "page": page,
            "pageSize": page_size, "total": total}
