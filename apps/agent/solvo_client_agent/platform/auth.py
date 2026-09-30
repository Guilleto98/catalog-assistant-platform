"""Opaque sessions and Argon2id password authentication."""

from __future__ import annotations

from datetime import timedelta
import hashlib
import secrets
from typing import TYPE_CHECKING

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy import select

from ..domain.errors import IntakeError
from .models import AuthSession, Organization, User, now
from .policies import AccountRole, AccountStatus, AuditEventType, RequestLimits
from .repository import audit

if TYPE_CHECKING:
    from .database import Database
    from ..config import Settings


COOKIE = "solvo_session"
hasher = PasswordHasher()
_dummy_hash = hasher.hash(secrets.token_urlsafe(32))


def token_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class AuthService:
    def __init__(self, database: Database, settings: Settings) -> None:
        self.database = database
        self.settings = settings

    def create_organization(self, name: str, slug: str) -> Organization:
        with self.database.session.begin() as db:
            item = Organization(name=name, slug=slug)
            db.add(item)
        return item

    def create_user(
        self,
        email: str,
        password: str,
        role: AccountRole,
        organization_id: str | None = None,
        catalog_demo_user_id: str | None = None,
    ) -> User:
        if role not in {AccountRole.CLIENT_USER, AccountRole.INTERNAL_ADMIN}:
            raise ValueError("Invalid role")
        if len(password) < RequestLimits.PASSWORD_MIN_CHARACTERS:
            raise ValueError(
                f"La contraseña debe tener al menos {RequestLimits.PASSWORD_MIN_CHARACTERS} caracteres."
            )
        with self.database.session.begin() as db:
            if role == AccountRole.CLIENT_USER and (
                not organization_id or not db.get(Organization, organization_id)
            ):
                raise ValueError("Un cliente necesita una organización válida.")
            item = User(email=email.strip().lower(), password_hash=hasher.hash(password),
                        role=role, organization_id=organization_id,
                        catalog_demo_user_id=catalog_demo_user_id)
            db.add(item)
        return item

    def login(self, email: str, password: str, request_id: str) -> tuple[str, User]:
        with self.database.session.begin() as db:
            user = db.scalar(select(User).where(User.email == email.strip().lower()))
            valid = False
            try:
                valid = hasher.verify(user.password_hash if user else _dummy_hash, password)
            except (VerificationError, InvalidHashError):
                pass
            org = db.get(Organization, user.organization_id) if user and user.organization_id else None
            allowed = (
                valid
                and user
                and user.status == AccountStatus.ACTIVE
                and (org is None or org.status == AccountStatus.ACTIVE)
            )
            if not allowed:
                audit(db, AuditEventType.AUTH_LOGIN_FAILED, request_id=request_id,
                      metadata={"reason": "unknown_email" if user is None else
                                "disabled_identity" if valid else "invalid_password"})
            else:
                if hasher.check_needs_rehash(user.password_hash):
                    user.password_hash = hasher.hash(password)
                raw = secrets.token_urlsafe(32)
                session = AuthSession(user_id=user.id, token_hash=token_hash(raw),
                                      expires_at=now() + timedelta(seconds=self.settings.auth_session_ttl))
                db.add(session)
                user.last_login_at = now()
                audit(db, AuditEventType.AUTH_LOGIN_SUCCEEDED, user=user, request_id=request_id)
                return raw, user
        raise IntakeError("INVALID_CREDENTIALS", "Credenciales inválidas.", 401)

    def authenticate(self, raw: str | None) -> User:
        if not raw:
            raise IntakeError("AUTH_REQUIRED", "Se requiere iniciar sesión.", 401)
        with self.database.session.begin() as db:
            session = db.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash(raw)))
            if not session or session.revoked_at:
                raise IntakeError("AUTH_REQUIRED", "Se requiere iniciar sesión.", 401)
            if session.expires_at <= now():
                raise IntakeError("SESSION_EXPIRED", "La sesión expiró.", 401)
            user = db.get(User, session.user_id)
            if not user or user.status != AccountStatus.ACTIVE:
                raise IntakeError("USER_DISABLED", "El usuario no está habilitado.", 403)
            org = db.get(Organization, user.organization_id) if user.organization_id else None
            if org and org.status != AccountStatus.ACTIVE:
                raise IntakeError("ORGANIZATION_DISABLED", "La organización no está habilitada.", 403)
            session.last_seen_at = now()
            return user

    def logout(self, raw: str, user: User, request_id: str) -> None:
        with self.database.session.begin() as db:
            session = db.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash(raw)))
            if session:
                session.revoked_at = now()
            audit(db, AuditEventType.AUTH_LOGOUT, user=user, request_id=request_id)
