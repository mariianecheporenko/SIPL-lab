"""Lark parser and parse-tree-to-AST transformer for SIPL."""

from __future__ import annotations

import re
from importlib import resources

from lark import Lark, Transformer, Tree, v_args
from lark.exceptions import UnexpectedEOF, UnexpectedInput
from lark.lexer import PatternStr

from .ast import (
    Arithmetic,
    Assign,
    BooleanNot,
    BooleanOr,
    Compare,
    If,
    Number,
    Program,
    Seq,
    Skip,
    SourceSpan,
    Variable,
    While,
)
from .errors import Diagnostic, SiplSyntaxError

# The grammar is package data, so it is found both in a source checkout and in
# an installed wheel (never via a path relative to the repository root).
GRAMMAR_TEXT: str = (
    (resources.files(__package__) / "grammar" / "sipl.lark").read_text(encoding="utf-8")
)


def span_from_meta(meta) -> SourceSpan | None:
    """Convert Lark's ``meta`` (filled by ``propagate_positions``) to a SourceSpan."""
    if getattr(meta, "empty", True):
        return None
    return SourceSpan(
        meta.line,
        meta.column,
        meta.end_line,
        meta.end_column,
        meta.start_pos,
        meta.end_pos,
    )


def _join(first: SourceSpan | None, second: SourceSpan | None) -> SourceSpan | None:
    if first is None or second is None:
        return None
    return first.merge(second)


@v_args(meta=True)
class SIPLTransformer(Transformer):
    """Convert Lark's parse tree into typed SIPL dataclasses.

    Every node gets the span of the source text it was built from.  A
    ``begin ... end`` block is transparent: it yields the inner statement
    together with that statement's own span.
    """

    def start(self, meta, items):
        return Program(items[0], span=span_from_meta(meta))

    def sequence(self, meta, items):
        result = items[0]
        for statement in items[1:]:
            result = Seq(result, statement, span=_join(result.span, statement.span))
        return result

    def assignment(self, meta, items):
        name, expression = items
        return Assign(str(name), expression, span=span_from_meta(meta))

    def if_statement(self, meta, items):
        condition, then_branch, else_branch = items
        return If(condition, then_branch, else_branch, span=span_from_meta(meta))

    def while_statement(self, meta, items):
        condition, body = items
        return While(condition, body, span=span_from_meta(meta))

    def block(self, meta, items):
        return items[0]

    def skip_statement(self, meta, _items):
        return Skip(span=span_from_meta(meta))

    def number(self, meta, items):
        return Number(int(items[0]), span=span_from_meta(meta))

    def variable(self, meta, items):
        return Variable(str(items[0]), span=span_from_meta(meta))

    def add(self, meta, items):
        return Arithmetic("+", items[0], items[1], span=span_from_meta(meta))

    def subtract(self, meta, items):
        return Arithmetic("-", items[0], items[1], span=span_from_meta(meta))

    def multiply(self, meta, items):
        return Arithmetic("*", items[0], items[1], span=span_from_meta(meta))

    def equal(self, meta, items):
        return Compare("=", items[0], items[1], span=span_from_meta(meta))

    def greater(self, meta, items):
        return Compare(">", items[0], items[1], span=span_from_meta(meta))

    def boolean_or_op(self, meta, items):
        return BooleanOr(items[0], items[1], span=span_from_meta(meta))

    def boolean_not(self, meta, items):
        return BooleanNot(items[0], span=span_from_meta(meta))


_parser = Lark(
    GRAMMAR_TEXT,
    parser="lalr",
    start="start",
    propagate_positions=True,
)

# Human-readable names for terminals, used in syntax-error messages.
_PATTERN_LABELS = {"NAME": "variable name", "INTEGER": "integer", "WS": "whitespace"}
_TERMINAL_LABELS: dict[str, str] = {"$END": "end of input"}
for _terminal in _parser.terminals:
    if isinstance(_terminal.pattern, PatternStr):
        _label = repr(_terminal.pattern.value)
    elif _terminal.name.startswith("_"):  # keyword written as /word\b/
        _label = repr(_terminal.pattern.value.replace("\\b", ""))
    else:
        _label = _PATTERN_LABELS.get(_terminal.name, _terminal.name)
    _TERMINAL_LABELS[_terminal.name] = _label

_FOUND_RE = re.compile(r"\w+|\S")


def _position(source: str, offset: int) -> tuple[int, int]:
    """Return the 1-based (line, column) of a 0-based character offset."""
    line = source.count("\n", 0, offset) + 1
    column = offset - (source.rfind("\n", 0, offset) + 1) + 1
    return line, column


def to_syntax_error(exc: UnexpectedInput, source: str) -> SiplSyntaxError:
    """Turn a Lark parse failure into a SiplSyntaxError with an exact SourceSpan."""
    token = getattr(exc, "token", None)
    at_eof = isinstance(exc, UnexpectedEOF) or getattr(token, "type", None) == "$END"
    offset = getattr(exc, "pos_in_stream", None)
    if at_eof or offset is None or offset < 0:
        offset = len(source)

    match = _FOUND_RE.match(source, offset)
    found = match.group() if match else None
    end = offset + len(found) if found else offset

    # ``accepts`` (LALR, exact) > ``allowed`` (lexer) > ``expected`` (may over-report).
    names = (
        getattr(exc, "accepts", None)
        or getattr(exc, "allowed", None)
        or getattr(exc, "expected", None)
        or ()
    )
    expected = sorted({_TERMINAL_LABELS.get(name, name) for name in names})

    subject = f"unexpected {found!r}" if found else "unexpected end of input"
    message = subject[0].upper() + subject[1:]
    if expected:
        message += f"; expected {', '.join(expected)}"

    start_line, start_column = _position(source, offset)
    end_line, end_column = _position(source, end)
    span = SourceSpan(start_line, start_column, end_line, end_column, offset, end)
    code = "SYNTAX_UNEXPECTED_EOF" if found is None else "SYNTAX_UNEXPECTED_TOKEN"
    return SiplSyntaxError(Diagnostic(code, message, span))


def _lark_tree(source: str) -> Tree:
    try:
        return _parser.parse(source)
    except UnexpectedInput as exc:
        raise to_syntax_error(exc, source) from exc


def parse(source: str) -> Program:
    """Parse SIPL source and return its :class:`Program` AST.

    Raises :class:`~sipl.errors.SiplSyntaxError` with a diagnostic
    (line, column, span, message) if the source is not a valid program.
    """
    return SIPLTransformer().transform(_lark_tree(source))


parse_program = parse
