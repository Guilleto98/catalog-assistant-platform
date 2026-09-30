"""Local filesystem storage behind a narrow, replaceable interface."""

from __future__ import annotations

from pathlib import Path
import os
from typing import BinaryIO

from ..domain.errors import IntakeError


class AttachmentStorage:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.root, 0o700)

    def path_for(self, internal_filename: str) -> Path:
        if Path(internal_filename).name != internal_filename:
            raise IntakeError("INVALID_ATTACHMENT_PATH", "Ruta de archivo inválida.")
        path = (self.root / internal_filename).resolve()
        if path.parent != self.root:
            raise IntakeError("INVALID_ATTACHMENT_PATH", "Ruta de archivo inválida.")
        return path

    def write_stream(self, internal_filename: str, source: BinaryIO, max_bytes: int) -> int:
        destination = self.path_for(internal_filename)
        total = 0
        try:
            with destination.open("xb") as target:
                while chunk := source.read(1024 * 1024):
                    total += len(chunk)
                    if total > max_bytes:
                        raise IntakeError(
                            "ATTACHMENT_TOO_LARGE",
                            f"El archivo supera el máximo permitido de {max_bytes} bytes.",
                            413,
                        )
                    target.write(chunk)
            os.chmod(destination, 0o600)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        return total

    def delete(self, internal_filename: str) -> None:
        self.path_for(internal_filename).unlink(missing_ok=True)
