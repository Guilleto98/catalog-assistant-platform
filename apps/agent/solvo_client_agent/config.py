"""Central configuration for the catalog agent."""

from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path

from dotenv import load_dotenv

from .platform.policies import SessionPolicy


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


@dataclass(frozen=True)
class Settings:
    model: str
    catalog_api_base_url: str
    catalog_api_timeout_seconds: float
    attachment_storage_path: Path
    intake_database_path: Path
    attachment_max_size_bytes: int
    attachment_allowed_extensions: frozenset[str]
    attachment_allowed_mime_types: frozenset[str]
    spreadsheet_max_cells: int
    pdf_max_characters: int
    transcription_model: str
    document_extraction_model: str
    domain_scope_enabled: bool
    domain_scope_model: str
    domain_scope_timeout_seconds: float
    application_database_path: Path | None = None
    adk_database_path: Path | None = None
    auth_session_ttl: int = SessionPolicy.DEFAULT_TTL_SECONDS
    auth_cookie_secure: bool = False
    frontend_origin: str = "http://localhost:4200"
    legacy_intake_enabled: bool = False


@lru_cache
def get_settings() -> Settings:
    agent_root = Path(__file__).resolve().parents[1]
    def local_path(name: str, fallback: Path) -> Path:
        configured = Path(os.getenv(name, str(fallback)))
        return (configured if configured.is_absolute() else agent_root / configured).resolve()

    return Settings(
        application_database_path=local_path("APPLICATION_DATABASE_PATH", agent_root / "var" / "application.db"),
        adk_database_path=local_path("ADK_DATABASE_PATH", agent_root / "var" / "adk_sessions.db"),
        auth_session_ttl=int(os.getenv("AUTH_SESSION_TTL", str(SessionPolicy.DEFAULT_TTL_SECONDS))),
        auth_cookie_secure=os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true",
        frontend_origin=os.getenv("FRONTEND_ORIGIN", "http://localhost:4200"),
        legacy_intake_enabled=os.getenv("LEGACY_INTAKE_ENABLED", "false").lower() == "true",
        model=os.getenv("AGENT_MODEL", "openai/gpt-6-luna"),
        catalog_api_base_url=os.getenv(
            "CATALOG_API_BASE_URL", "http://localhost:3000/api/v1"
        ).rstrip("/"),
        catalog_api_timeout_seconds=float(
            os.getenv("CATALOG_API_TIMEOUT_SECONDS", "10")
        ),
        attachment_storage_path=local_path(
            "ATTACHMENT_STORAGE_PATH", agent_root / "var" / "attachments"
        ),
        intake_database_path=local_path(
            "INTAKE_DATABASE_PATH", agent_root / "var" / "intake.db"
        ),
        attachment_max_size_bytes=int(
            os.getenv("ATTACHMENT_MAX_SIZE_BYTES", str(25 * 1024 * 1024))
        ),
        attachment_allowed_extensions=frozenset(
            item.strip().lower()
            for item in os.getenv(
                "ATTACHMENT_ALLOWED_EXTENSIONS", ".webm,.mp3,.mp4,.m4a,.wav,.pdf,.xlsx"
            ).split(",")
            if item.strip()
        ),
        attachment_allowed_mime_types=frozenset(
            item.strip().lower()
            for item in os.getenv(
                "ATTACHMENT_ALLOWED_MIME_TYPES",
                "audio/webm,audio/mpeg,audio/mp4,audio/wav,application/pdf,"
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ).split(",")
            if item.strip()
        ),
        spreadsheet_max_cells=int(os.getenv("SPREADSHEET_MAX_CELLS", "10000")),
        pdf_max_characters=int(os.getenv("PDF_MAX_CHARACTERS", "200000")),
        transcription_model=os.getenv("TRANSCRIPTION_MODEL", "gpt-transcribe"),
        document_extraction_model=os.getenv(
            "DOCUMENT_EXTRACTION_MODEL", "gpt-6-luna"
        ),
        domain_scope_enabled=os.getenv("DOMAIN_SCOPE_ENABLED", "true").lower()
        in {"1", "true", "yes", "on"},
        domain_scope_model=os.getenv(
            "DOMAIN_SCOPE_MODEL",
            "gpt-4.1-mini",
        ),
        domain_scope_timeout_seconds=float(
            os.getenv("DOMAIN_SCOPE_TIMEOUT_SECONDS", "8")
        ),
    )
