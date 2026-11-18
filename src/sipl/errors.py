"""Diagnostics and exception types shared by all SIPL tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .ast import SourceSpan


@dataclass(frozen=True)
class Diagnostic:

    code: str
    message: str
    span: SourceSpan
    severity: str = "error"

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "span": self.span.to_dict(),
        }


class SiplError(Exception):

    def __init__(self, diagnostic: Diagnostic) -> None:
        self.diagnostic = diagnostic
        super().__init__(
            f"line {diagnostic.span.start_line}, column {diagnostic.span.start_column}: "
            f"{diagnostic.message}"
        )

    @property
    def line(self) -> int:
        return self.diagnostic.span.start_line

    @property
    def column(self) -> int:
        return self.diagnostic.span.start_column


class SiplSyntaxError(SiplError):
    pass
