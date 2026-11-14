"""Visitor-based evaluator for SIPL programs."""

from __future__ import annotations

from typing import Any

try:
    from .ast import (
        Arithmetic,
        BooleanNot,
        BooleanOr,
        Compare,
        Program,
        Assign,
        Seq,
        If,
        While,
        Skip,
        Number,
        Variable,
        Node,
    )
except ImportError:
    from ast import (
        Arithmetic,
        BooleanNot,
        BooleanOr,
        Compare,
        Program,
        Assign,
        Seq,
        If,
        While,
        Skip,
        Number,
        Variable,
        Node,
    )


class ExecutionLimitError(RuntimeError):
    """Raised when program execution exceeds the maximum allowed steps."""


class Interpreter:
    """Execute SIPL AST nodes with step limit protection and execution trace."""

    def __init__(self, *, trace: bool = True, max_steps: int = 10000) -> None:
        self.state: dict[str, int] = {}
        self.trace = trace
        self.max_steps = max_steps
        self.steps = 0
        self.trace_events: list[dict[str, Any]] = []

    def _record_step(self, event: str) -> None:
        self.steps += 1
        if self.steps > self.max_steps:
            raise ExecutionLimitError(
                f"Execution exceeded maximum limit of {self.max_steps} steps"
            )
        entry = {"step": self.steps, "event": event, "state": self.state.copy()}
        self.trace_events.append(entry)
        if self.trace:
            print(entry)

    def visit(self, node: Node) -> Any:
        return node.accept(self)

    def execute(self, program: Program) -> dict[str, int]:
        self.visit(program)
        self._record_step("finished")
        return self.state

    def visit_program(self, node: Program) -> None:
        self.visit(node.body)

    def visit_assign(self, node: Assign) -> None:
        self._record_step(f"before_assign:{node.name}")
        self.state[node.name] = self.visit(node.expression)
        self._record_step(f"after_assign:{node.name}")

    def visit_seq(self, node: Seq) -> None:
        self.visit(node.first)
        self.visit(node.second)

    def visit_if(self, node: If) -> None:
        cond = self.visit(node.condition)
        self._record_step(f"if_condition:{cond}")
        branch = node.then_branch if cond else node.else_branch
        self.visit(branch)

    def visit_while(self, node: While) -> None:
        while True:
            cond = self.visit(node.condition)
            self._record_step(f"while_condition:{cond}")
            if not cond:
                break
            self.visit(node.body)

    def visit_skip(self, _node: Skip) -> None:
        self._record_step("skip")

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
        return self.visit(node.left) or self.visit(node.right)

    def visit_boolean_not(self, node: BooleanNot) -> bool:
        return not self.visit(node.operand)


def interpret(
    program: Program, *, trace: bool = True, max_steps: int = 10000
) -> dict[str, int]:
    """Execute a program using a new interpreter and return its final state."""
    return Interpreter(trace=trace, max_steps=max_steps).execute(program)