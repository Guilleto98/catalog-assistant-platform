"""Explicit application-record to public DTO boundary."""
from sqlalchemy import select
from . import contracts as c
from .models import Message, Organization, Conversation
from .repository import serialize


def current_user(db, user):
    org = db.get(Organization, user.organization_id) if user.organization_id else None
    return c.CurrentUserDto(id=user.id, email=user.email, role=user.role,
        organization=c.OrganizationView(id=org.id, name=org.name) if org else None)


def conversation(db, item):
    latest = db.scalar(select(Message).where(Message.conversation_id == item.id,
        Message.content_text.is_not(None)).order_by(Message.created_at.desc(), Message.id.desc()))
    return c.ConversationSummaryDto(id=item.id, title=item.title, status=item.status,
        preview=latest.content_text[:160] if latest else None,
        createdAt=item.created_at, updatedAt=item.updated_at, lastMessageAt=item.last_message_at)


def admin_run(db, item):
    owner = db.get(Conversation, item.conversation_id)
    return c.AdminAgentRunDto(**serialize(item), user_id=owner.owner_user_id, organization_id=owner.organization_id)
