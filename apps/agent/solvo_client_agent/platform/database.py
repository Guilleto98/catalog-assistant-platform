"""SQLAlchemy boundary and versioned Alembic upgrades."""

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker


def private_path(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    if not path.exists():
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
    os.chmod(path, 0o600)


class Database:
    def __init__(self, path: Path) -> None:
        private_path(path)
        self.engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False, "timeout": 30})

        @event.listens_for(self.engine, "connect")
        def configure(connection, _record):
            connection.execute("PRAGMA foreign_keys=ON")

        config = Config()
        config.set_main_option("script_location", str(Path(__file__).resolve().parents[2] / "migrations"))
        with self.engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        self.session = sessionmaker(self.engine, expire_on_commit=False)

    def close(self):
        self.engine.dispose()
