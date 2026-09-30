"""Administrative bootstrap with passwords read from a hidden interactive prompt."""

import argparse
from getpass import getpass

from ..config import get_settings
from .auth import AuthService
from .database import Database
from .policies import AccountRole, RequestLimits


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    organization = commands.add_parser("create-organization")
    organization.add_argument("--name", required=True)
    organization.add_argument("--slug", required=True)
    user = commands.add_parser("create-user")
    user.add_argument("--email", required=True)
    user.add_argument("--role", choices=[role.value for role in AccountRole], required=True)
    user.add_argument("--organization-id")
    user.add_argument("--catalog-demo-user-id", choices=["demo-user-01", "demo-user-02"])
    args = parser.parse_args()
    settings = get_settings()
    database = Database(settings.application_database_path)
    auth = AuthService(database, settings)
    try:
        if args.command == "create-organization":
            result = auth.create_organization(args.name, args.slug)
        else:
            password = getpass(
                f"Contraseña (mínimo {RequestLimits.PASSWORD_MIN_CHARACTERS} caracteres): "
            )
            if password != getpass("Repetir contraseña: "):
                raise ValueError("Las contraseñas no coinciden.")
            result = auth.create_user(
                args.email,
                password,
                AccountRole(args.role),
                args.organization_id,
                args.catalog_demo_user_id,
            )
        print(f"Creado: {result.id}")
    finally:
        database.close()


if __name__ == "__main__":
    main()
