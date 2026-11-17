"""Nodes for the SIPL abstract syntax tree."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any, Protocol, TypeAlias


@dataclass(frozen=True)
class SourceSpan:
    
    start_line: int
    start_column: int
    end_line: int
    end_column: int
    start_offset: int
    end_offset: int

    def merge(self, other: SourceSpan) -> SourceSpan:
        """Return the span from the start of ``self`` to the end of ``other``."""
        return SourceSpan(
            self.start_line, self.start_column,
            other.end_line, other.end_column,
            self.start_offset, other.end_offset,
        )

    def to_dict(self) -> dict[str, int]:
        return {
            "start_line": self.start_line,
            "start_column": self.start_column,
            "end_line": self.end_line,
            "end_column": self.end_column,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
        }



class Visitor(Protocol):
    def visit_program(self, node: Program) -> object: ...
    def visit_assign(self, node: Assign) -> object: ...
    def visit_seq(self, node: Seq) -> object: ...
    def visit_if(self, node: If) -> object: ...
    def visit_while(self, node: While) -> object: ...
    def visit_skip(self, node: Skip) -> object: ...
    def visit_number(self, node: Number) -> object: ...
    def visit_variable(self, node: Variable) -> object: ...
    def visit_arithmetic(self, node: Arithmetic) -> object: ...
    def visit_compare(self, node: Compare) -> object: ...
    def visit_boolean_or(self, node: BooleanOr) -> object: ...
    def visit_boolean_not(self, node: BooleanNot) -> object: ...


@dataclass(frozen=True)
class Node:
    
    span: SourceSpan | None = field(default=None, kw_only=True, compare=False, repr=False)

    def accept(self, visitor: Visitor) -> object:
        names = {"BooleanOr": "boolean_or", "BooleanNot": "boolean_not"}
        method_name = names.get(self.__class__.__name__, self.__class__.__name__.lower())
        return getattr(visitor, f"visit_{method_name}")(self)

    def to_dict(self, *, include_spans: bool = True) -> dict[str, Any]:
        """Serialise the node to JSON-compatible data with a ``type`` discriminator."""
        data: dict[str, Any] = {"type": type(self).__name__}
        for item in fields(self):
            if item.name == "span":
                continue
            value = getattr(self, item.name)
            if isinstance(value, Node):
                value = value.to_dict(include_spans=include_spans)
            data[item.name] = value
        if include_spans and self.span is not None:
            data["span"] = self.span.to_dict()
        return data


class Expression(Node):
    pass


class BooleanExpression(Node):
    pass


class Statement(Node):
    pass


@dataclass(frozen=True)
class Program(Node):
    body: Statement


@dataclass(frozen=True)
class Assign(Statement):
    name: str
    expression: Expression


@dataclass(frozen=True)
class Seq(Statement):
    first: Statement
    second: Statement


@dataclass(frozen=True)
class If(Statement):
    condition: BooleanExpression
    then_branch: Statement
    else_branch: Statement


@dataclass(frozen=True)
class While(Statement):
    condition: BooleanExpression
    body: Statement


@dataclass(frozen=True)
class Skip(Statement):
    pass


@dataclass(frozen=True)
class Number(Expression):
    value: int


@dataclass(frozen=True)
class Variable(Expression):
    name: str


@dataclass(frozen=True)
class Arithmetic(Expression):
    operator: str
    left: Expression
    right: Expression


@dataclass(frozen=True)
class Compare(BooleanExpression):
    operator: str
    left: Expression
    right: Expression


@dataclass(frozen=True)
class BooleanOr(BooleanExpression):
    left: BooleanExpression
    right: BooleanExpression


@dataclass(frozen=True)
class BooleanNot(BooleanExpression):
    operand: BooleanExpression


ArithmeticExpression: TypeAlias = Number | Variable | Arithmetic
BooleanExpr: TypeAlias = Compare | BooleanOr | BooleanNot

BinOp = Arithmetic
