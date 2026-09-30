"""Deterministic PDF and XLSX parsing with source locations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from pypdf import PdfReader

from ..domain.errors import IntakeError


class PdfParser:
    def __init__(self, max_characters: int) -> None:
        self.max_characters = max_characters

    def parse(self, path: Path) -> list[dict[str, Any]]:
        try:
            reader = PdfReader(path)
            pages = [
                {"page": index, "text": (page.extract_text() or "").strip()}
                for index, page in enumerate(reader.pages, start=1)
            ]
        except Exception as exc:
            raise IntakeError("PDF_PARSE_FAILED", "No se pudo leer el PDF.", 422) from exc
        if not any(page["text"] for page in pages):
            raise IntakeError(
                "PDF_REQUIRES_OCR",
                "El PDF no contiene texto extraíble; esta etapa no incluye OCR.",
                422,
            )
        total = sum(len(page["text"]) for page in pages)
        if total > self.max_characters:
            raise IntakeError(
                "PDF_CONTENT_LIMIT_EXCEEDED",
                "El PDF contiene más texto del límite configurado.",
                413,
            )
        return pages


class SpreadsheetParser:
    def __init__(self, max_cells: int) -> None:
        self.max_cells = max_cells

    def parse(self, path: Path) -> list[dict[str, Any]]:
        try:
            workbook = load_workbook(path, read_only=True, data_only=True)
            cells: list[dict[str, Any]] = []
            for sheet in workbook.worksheets:
                for row in sheet.iter_rows():
                    for cell in row:
                        if cell.value is None or str(cell.value).strip() == "":
                            continue
                        cells.append(
                            {
                                "sheet": sheet.title,
                                "cell": cell.coordinate,
                                "value": cell.value,
                            }
                        )
                        if len(cells) > self.max_cells:
                            raise IntakeError(
                                "SPREADSHEET_CELL_LIMIT_EXCEEDED",
                                "La planilla supera el límite de celdas no vacías.",
                                413,
                            )
            workbook.close()
        except IntakeError:
            raise
        except Exception as exc:
            raise IntakeError(
                "SPREADSHEET_PARSE_FAILED", "No se pudo leer la planilla.", 422
            ) from exc
        if not cells:
            raise IntakeError("EMPTY_SPREADSHEET", "La planilla no contiene datos.", 422)
        return cells
