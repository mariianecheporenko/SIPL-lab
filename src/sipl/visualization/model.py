"""A small tree model shared by all renderers."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, fields

from ..ast import BooleanExpression, Expression, Node, Program, SourceSpan, Statement
from ..parse_tree import ParseNode

_NAMED_TOKENS = {"NAME", "INTEGER"}


@dataclass(frozen=True)
class VisNode:
    label: str
    kind: str  # nonterminal | terminal | program | statement | expression | condition
    span: SourceSpan | None = None
    role: str | None = None  # name of the AST field that holds this child
    children: tuple[VisNode, ...] = ()

    def walk(self) -> Iterator[VisNode]:
        yield self
        for child in self.children:
            yield from child.walk()


def from_parse_tree(node: ParseNode) -> VisNode:
    if node.is_terminal:
        label = f"{node.symbol} {node.text}" if node.symbol in _NAMED_TOKENS else repr(node.text)
        return VisNode(label, "terminal", node.span)
    return VisNode(
        node.symbol,
        "nonterminal",
        node.span,
        children=tuple(from_parse_tree(child) for child in node.children),
    )


def _ast_kind(node: Node) -> str:
    if isinstance(node, Program):
        return "program"
    if isinstance(node, Statement):
        return "statement"
    if isinstance(node, Expression):
        return "expression"
    if isinstance(node, BooleanExpression):
        return "condition"
    return "nonterminal"


def from_ast(node: Node, role: str | None = None) -> VisNode:
    scalars: list[str] = []
    children: list[VisNode] = []
    for item in fields(node):
        if item.name == "span":
            continue
        value = getattr(node, item.name)
        if isinstance(value, Node):
            children.append(from_ast(value, item.name))
        else:
            scalars.append(str(value))
    label = " ".join([type(node).__name__, *scalars])
    return VisNode(label, _ast_kind(node), node.span, role, tuple(children))
