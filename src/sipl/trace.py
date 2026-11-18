"""Structured execution events for SIPL (CORE-04)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .ast import SourceSpan


class EventKind(str, Enum):
    """Kinds of events emitted by the interpreter."""

    BEFORE_STATEMENT = "before_statement"
    AFTER_STATEMENT = "after_statement"
    VARIABLE_CHANGED = "variable_changed"
    CONDITION_EVALUATED = "condition_evaluated"
    FINISHED = "finished"


@dataclass(frozen=True)
class TraceEvent:
    """A single event in the execution trace of a SIPL program."""
    step: int
    kind: EventKind
    statement: str | None
    span: SourceSpan | None
    state: dict[str, int]
    variable: str | None = None
    old_value: int | None = None
    new_value: int | None = None
    result: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "event": self.kind.value,
            "statement": self.statement,
            "span": self.span.to_dict() if self.span is not None else None,
            "variable": self.variable,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "result": self.result,
            "state": dict(self.state),
        }