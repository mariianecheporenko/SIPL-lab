"""Concrete syntax (derivation) tree of a SIPL program (VIS-01)."""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from lark import Lark, Token, Tree
from lark.exceptions import UnexpectedInput

from .ast import SourceSpan
from .parser import GRAMMAR_TEXT, span_from_meta, to_syntax_error


@dataclass(frozen=True)
class ParseNode:
    """A node of the derivation tree: a rule application or a token."""

    symbol: str
    span: SourceSpan | None = None
    text: str | None = None  # lexeme for tokens, None for rule applications
    children: tuple[ParseNode, ...] = ()

    @property
    def is_terminal(self) -> bool:
        return self.text is not None

    def walk(self) -> Iterator[ParseNode]:
        """Pre-order traversal of this node and all its descendants."""
        yield self
        for child in self.children:
            yield from child.walk()

    def tokens(self) -> Iterator[ParseNode]:
        """The leaves (tokens) from left to right."""
        return (node for node in self.walk() if node.is_terminal)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "terminal" if self.is_terminal else "nonterminal",
            "symbol": self.symbol,
            "text": self.text,
            "span": self.span.to_dict() if self.span is not None else None,
            "children": [child.to_dict() for child in self.children],
        }


def concrete_grammar(grammar_text: str) -> str:
    """Derive the derivation-tree grammar from the AST grammar text."""
    lines = []
    for line in grammar_text.splitlines():
        if not line.lstrip().startswith("//"):
            line = re.sub(r"^\?", "", line)
            line = re.sub(r"\s*->\s*\w+", "", line)
        lines.append(line)
    return "\n".join(lines) + "\n"


_cst_parser = Lark(
    concrete_grammar(GRAMMAR_TEXT),
    parser="lalr",
    start="start",
    propagate_positions=True,
    keep_all_tokens=True,
)


def _convert(item: Tree | Token) -> ParseNode:
    if isinstance(item, Token):
        span = SourceSpan(
            int(item.line or 0),
            int(item.column or 0),
            int(item.end_line or 0),
            int(item.end_column or 0),
            int(item.start_pos or 0),
            int(item.end_pos or 0),
        )
        return ParseNode(item.type.lstrip("_"), span, str(item))
    return ParseNode(
        str(item.data),
        span_from_meta(item.meta),
        None,
        tuple(_convert(child) for child in item.children),
    )


def parse_concrete(source: str) -> ParseNode:
    """Return the derivation tree of ``source`` (raises SiplSyntaxError if invalid)."""
    try:
        tree = _cst_parser.parse(source)
    except UnexpectedInput as exc:
        raise to_syntax_error(exc, source) from exc
    return _convert(tree)
