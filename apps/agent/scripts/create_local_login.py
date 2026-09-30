"""Provision one disposable local client login without printing its password."""

import os
from pathlib import Path
import secrets

from sqlalchemy import select

from solvo_client_agent.config import get_settings
from solvo_client_agent.platform.auth import AuthService
from solvo_client_agent.platform.database import Database
from solvo_client_agent.platform.models import User


EMAIL = "demo.local@solvo.test"


def main() -> None:
    settings = get_settings()
    database_path = settings.application_database_path
    if database_path is None:
        raise RuntimeError("Application DB no configurada")
    credentials_path = Path(database_path).parent / "local-login.txt"
    database = Database(database_path)
    try:
        with database.session() as session:
            if session.scalar(select(User).where(User.email == EMAIL)):
                raise RuntimeError("La cuenta de prueba ya existe; no se cambió su contraseña.")
        password = secrets.token_urlsafe(24)
        fd = os.open(credentials_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as destination:
                destination.write(f"Usuario: {EMAIL}\nContraseña: {password}\n")
            auth = AuthService(database, settings)
            organization = auth.create_organization("Pruebas locales", "pruebas-locales")
            auth.create_user(EMAIL, password, "CLIENT_USER", organization.id, "demo-user-01")
        except Exception:
            credentials_path.unlink(missing_ok=True)
            raise
    finally:
        database.close()
    print(f"Cuenta CLIENT_USER creada: {EMAIL}")
    print(f"Contraseña guardada sólo en {credentials_path} (permisos 0600; Git la ignora).")


if __name__ == "__main__":
    main()
