"""Stable domain errors exposed by the intake HTTP boundary."""

from dataclasses import dataclass


@dataclass
class IntakeError(Exception):
    code: str
    message: str
    status_code: int = 400

    def __str__(self) -> str:
        return self.message
