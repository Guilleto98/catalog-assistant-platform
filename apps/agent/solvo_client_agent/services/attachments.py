"""Upload validation and attachment lifecycle."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from ..domain.errors import IntakeError
from ..domain.models import Attachment, AttachmentStatus, AttachmentType
from ..repositories import AttachmentRepository
from ..storage import AttachmentStorage


logger = logging.getLogger(__name__)

ALLOWED_UPLOADS: dict[tuple[str, str], AttachmentType] = {
    (".webm", "audio/webm"): AttachmentType.AUDIO,
    (".mp3", "audio/mpeg"): AttachmentType.AUDIO,
    (".mp4", "audio/mp4"): AttachmentType.AUDIO,
    (".m4a", "audio/mp4"): AttachmentType.AUDIO,
    (".wav", "audio/wav"): AttachmentType.AUDIO,
    (".pdf", "application/pdf"): AttachmentType.PDF,
    (
        ".xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ): AttachmentType.SPREADSHEET,
}


class AttachmentService:
    def __init__(
        self,
        storage: AttachmentStorage,
        repository: AttachmentRepository,
        max_size_bytes: int,
        allowed_extensions: frozenset[str] | None = None,
        allowed_mime_types: frozenset[str] | None = None,
    ) -> None:
        self.storage = storage
        self.repository = repository
        self.max_size_bytes = max_size_bytes
        self.allowed_extensions = allowed_extensions or frozenset(
            suffix for suffix, _mime in ALLOWED_UPLOADS
        )
        self.allowed_mime_types = allowed_mime_types or frozenset(
            mime for _suffix, mime in ALLOWED_UPLOADS
        )

    def upload(
        self,
        conversation_id: str,
        original_filename: str,
        mime_type: str,
        source: BinaryIO,
    ) -> Attachment:
        safe_original = Path((original_filename or "").replace("\\", "/")).name
        suffix = Path(safe_original).suffix.lower()
        normalized_mime = mime_type.lower()
        attachment_type = (
            ALLOWED_UPLOADS.get((suffix, normalized_mime))
            if suffix in self.allowed_extensions
            and normalized_mime in self.allowed_mime_types
            else None
        )
        if attachment_type is None:
            raise IntakeError(
                "UNSUPPORTED_ATTACHMENT_TYPE",
                "Tipo de archivo no admitido. Usá audio, PDF o XLSX.",
                415,
            )
        self._validate_signature(source, suffix)
        attachment_id = f"att_{uuid4().hex}"
        internal_filename = f"{attachment_id}{suffix}"
        size = self.storage.write_stream(
            internal_filename, source, self.max_size_bytes
        )
        if size == 0:
            self.storage.delete(internal_filename)
            raise IntakeError("EMPTY_ATTACHMENT", "El archivo está vacío.")
        now = datetime.now(timezone.utc)
        attachment = Attachment(
            id=attachment_id,
            conversation_id=conversation_id,
            filename=internal_filename,
            original_filename=safe_original,
            mime_type=normalized_mime,
            type=attachment_type,
            size_bytes=size,
            status=AttachmentStatus.UPLOADED,
            created_at=now,
            updated_at=now,
        )
        try:
            self.repository.save(attachment)
        except Exception:
            self.storage.delete(internal_filename)
            raise
        logger.info(
            "attachment_uploaded attachment_id=%s conversation_id=%s type=%s size=%s",
            attachment.id,
            conversation_id,
            attachment.type,
            size,
        )
        return attachment

    @staticmethod
    def _validate_signature(source: BinaryIO, suffix: str) -> None:
        try:
            position = source.tell()
            header = source.read(64)
            source.seek(position)
        except (AttributeError, OSError) as exc:
            raise IntakeError(
                "ATTACHMENT_STREAM_INVALID",
                "No se pudo validar el contenido del archivo.",
                422,
            ) from exc
        valid = {
            ".pdf": header.startswith(b"%PDF-"),
            ".xlsx": header.startswith(b"PK\x03\x04"),
            ".wav": header.startswith(b"RIFF") and header[8:12] == b"WAVE",
            ".webm": header.startswith(b"\x1aE\xdf\xa3"),
            ".mp3": header.startswith(b"ID3")
            or (len(header) >= 2 and header[0] == 0xFF and header[1] & 0xE0 == 0xE0),
            ".mp4": len(header) >= 12 and header[4:8] == b"ftyp",
            ".m4a": len(header) >= 12 and header[4:8] == b"ftyp",
        }.get(suffix, False)
        if not valid:
            raise IntakeError(
                "ATTACHMENT_CONTENT_MISMATCH",
                "El contenido del archivo no coincide con su formato declarado.",
                422,
            )

    def get(self, attachment_id: str, conversation_id: str) -> Attachment:
        return self.repository.get(attachment_id, conversation_id)

    def update_status(
        self,
        attachment: Attachment,
        status: AttachmentStatus,
        error: IntakeError | None = None,
    ) -> Attachment:
        updated = attachment.model_copy(
            update={
                "status": status,
                "updated_at": datetime.now(timezone.utc),
                "error_code": error.code if error else None,
                "error_message": error.message if error else None,
            }
        )
        return self.repository.save(updated)
