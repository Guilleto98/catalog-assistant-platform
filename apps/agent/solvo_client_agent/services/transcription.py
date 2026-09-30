"""Audio transcription using OpenAI's purpose-built transcription API."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from openai import AsyncOpenAI

from ..domain.errors import IntakeError


class Transcriber(Protocol):
    async def transcribe(self, path: Path) -> str: ...


class OpenAITranscriptionService:
    def __init__(self, model: str, client: AsyncOpenAI | None = None) -> None:
        self.model = model
        self.client = client

    async def transcribe(self, path: Path) -> str:
        try:
            with path.open("rb") as audio:
                client = self.client or AsyncOpenAI()
                result = await client.audio.transcriptions.create(
                    model=self.model,
                    file=audio,
                    response_format="text",
                )
        except Exception as exc:
            raise IntakeError(
                "TRANSCRIPTION_FAILED",
                "No se pudo transcribir el audio.",
                502,
            ) from exc
        text = result if isinstance(result, str) else getattr(result, "text", "")
        if not text or not str(text).strip():
            raise IntakeError("EMPTY_TRANSCRIPTION", "El audio no produjo texto.", 422)
        return str(text).strip()
