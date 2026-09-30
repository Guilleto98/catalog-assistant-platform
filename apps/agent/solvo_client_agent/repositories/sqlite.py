"""Deterministic local persistence for demo attachments and drafts."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3

from ..domain.errors import IntakeError
from ..domain.models import ArticleRequestDraft, Attachment


def initialize_database(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS attachments (
              id TEXT PRIMARY KEY,
              conversation_id TEXT NOT NULL,
              payload TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS attachments_conversation
              ON attachments(conversation_id);
            CREATE TABLE IF NOT EXISTS drafts (
              id TEXT PRIMARY KEY,
              conversation_id TEXT NOT NULL,
              payload TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS drafts_conversation
              ON drafts(conversation_id);
            """
        )
    os.chmod(path, 0o600)


class _JsonRepository:
    table: str
    model: type[Attachment] | type[ArticleRequestDraft]

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        initialize_database(database_path)

    def save(self, value: Attachment | ArticleRequestDraft):
        payload = value.model_dump_json()
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                f"INSERT INTO {self.table}(id, conversation_id, payload) VALUES (?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET conversation_id=excluded.conversation_id, payload=excluded.payload",
                (value.id, value.conversation_id, payload),
            )
        return value

    def get(self, entity_id: str, conversation_id: str):
        with sqlite3.connect(self.database_path) as connection:
            row = connection.execute(
                f"SELECT conversation_id, payload FROM {self.table} WHERE id = ?",
                (entity_id,),
            ).fetchone()
        label = "ATTACHMENT" if self.table == "attachments" else "DRAFT"
        if row is None:
            raise IntakeError(f"{label}_NOT_FOUND", "El recurso solicitado no existe.", 404)
        if row[0] != conversation_id:
            raise IntakeError("ACCESS_DENIED", "El recurso pertenece a otra conversación.", 403)
        return self.model.model_validate(json.loads(row[1]))


class AttachmentRepository(_JsonRepository):
    table = "attachments"
    model = Attachment


class DraftRepository(_JsonRepository):
    table = "drafts"
    model = ArticleRequestDraft
