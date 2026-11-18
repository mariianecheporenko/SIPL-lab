"""Visitor-based evaluator for SIPL programs."""

from __future__ import annotations

import json
from typing import Callable

from .ast import (
    Arithmetic,
    Assign,
    BooleanNot,
    BooleanOr,
    Compare,
    If,
    Node,
    Number,
    Program,
    Seq,
    Skip,
    Variable,
    While,
)
from .trace import EventKind, TraceEvent


class ExecutionLimitError(RuntimeError):
    """Raised when program execution exceeds the maximum allowed steps."""


class Interpreter:


    def __init__(
        self,
        *,
        trace: bool = False,
        max_steps: int = 10000,
        listener: Callable[[TraceEvent], None] | None = None,
    ) -> None:
        self.state: dict[str, int] = {}
        self.trace = trace
        self.max_steps = max_steps
        self.listener = listener
        self.steps = 0
        self.trace_events: list[TraceEvent] = []

    def _emit(
        self,
        kind: EventKind,
        node: Node | None,
        *,
        statement: str | None = None,
        variable: str | None = None,
        old_value: int | None = None,
        new_value: int | None = None,
        result: bool | None = None,
    ) -> None:
        self.steps += 1
        if self.steps > self.max_steps:
            raise ExecutionLimitError(
                f"Execution exceeded maximum limit of {self.max_steps} steps"
            )
        if statement is None and node is not None:
            statement = type(node).__name__
        event = TraceEvent(
            step=self.steps,
            kind=kind,
            statement=statement,
            span=node.span if node is not None else None,
            state=self.state.copy(),
            variable=variable,
            old_value=old_value,
            new_value=new_value,
            result=result,
        )
        self.trace_events.append(event)
        if self.listener is not None:
            self.listener(event)
        if self.trace:
            print(json.dumps(event.to_dict()))

    def visit(self, node: Node):
        return node.accept(self)

    def execute(self, program: Program) -> dict[str, int]:
        self.state = {}
        self.steps = 0
        self.trace_events = []
        self.visit(program)
        self._emit(EventKind.FINISHED, program)
        return self.state

    def visit_program(self, node: Program) -> None:
        self.visit(node.body)

    def visit_assign(self, node: Assign) -> None:
        self._emit(EventKind.BEFORE_STATEMENT, node)
        value = self.visit(node.expression)
        old_value = self.state.get(node.name)
        self.state[node.name] = value
        self._emit(
            EventKind.VARIABLE_CHANGED,
            node,
            variable=node.name,
            old_value=old_value,
            new_value=value,
        )
        self._emit(EventKind.AFTER_STATEMENT, node)

    def visit_seq(self, node: Seq) -> None:
        self.visit(node.first)
        self.visit(node.second)

    def visit_if(self, node: If) -> None:
        self._emit(EventKind.BEFORE_STATEMENT, node)
        cond = self.visit(node.condition)
        self._emit(
            EventKind.CONDITION_EVALUATED, node.condition, statement="If", result=cond
        )
        self.visit(node.then_branch if cond else node.else_branch)
        self._emit(EventKind.AFTER_STATEMENT, node)

    def visit_while(self, node: While) -> None:
        self._emit(EventKind.BEFORE_STATEMENT, node)
        while True:
            cond = self.visit(node.condition)
            self._emit(
                EventKind.CONDITION_EVALUATED,
                node.condition,
                statement="While",
                result=cond,
            )
            if not cond:
                break
            self.visit(node.body)
        self._emit(EventKind.AFTER_STATEMENT, node)

    def visit_skip(self, node: Skip) -> None:
        self._emit(EventKind.BEFORE_STATEMENT, node)
        self._emit(EventKind.AFTER_STATEMENT, node)

    def visit_number(self, node: Number) -> int:
        return node.value

    def visit_variable(self, node: Variable) -> int:
        try:
            return self.state[node.name]
        except KeyError as exc:
            raise NameError(f"SIPL variable {node.name!r} has not been assigned") from exc

    def visit_arithmetic(self, node: Arithmetic) -> int:
        left = self.visit(node.left)
        right = self.visit(node.right)
        if node.operator == "+":
            return left + right
        if node.operator == "-":
            return left - right
        if node.operator == "*":
            return left * right
        raise ValueError(f"Unknown arithmetic operator: {node.operator}")

    def visit_compare(self, node: Compare) -> bool:
        left = self.visit(node.left)
        right = self.visit(node.right)
        if node.operator == "=":
            return left == right
        if node.operator == ">":
            return left > right
        raise ValueError(f"Unknown comparison operator: {node.operator}")

    def visit_boolean_or(self, node: BooleanOr) -> bool:
        left = self.visit(node.left)
        right = self.visit(node.right)
        return left or right

    def visit_boolean_not(self, node: BooleanNot) -> bool:
        return not self.visit(node.operand)


def interpret(
    program: Program, *, trace: bool = False, max_steps: int = 10000
) -> dict[str, int]:
    """Execute a program using a new interpreter and return its final state."""
    return Interpreter(trace=trace, max_steps=max_steps).execute(program)
