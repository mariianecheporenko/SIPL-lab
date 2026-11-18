"""CORE-01: the grammar is unambiguous (LALR) and keywords have word boundaries."""

import pytest

from sipl.ast import Arithmetic, Assign, If, Number, Seq, While
from sipl.errors import SiplSyntaxError
from sipl.parser import _parser, parse


def test_grammar_is_lalr():
    # Lark refuses to build an LALR parser for a grammar with conflicts,
    # so a successful import proves the grammar is unambiguous.
    assert _parser.options.parser == "lalr"


def test_while_body_is_a_single_statement():
    body = parse("begin while 1 > 0 do X := 1; Y := 2 end").body
    assert isinstance(body, Seq)
    assert isinstance(body.first, While)
    assert isinstance(body.first.body, Assign) and body.first.body.name == "X"
    assert isinstance(body.second, Assign) and body.second.name == "Y"


def test_else_branch_is_a_single_statement():
    body = parse("begin if 1 > 0 then X := 1 else Y := 1; Z := 2 end").body
    assert isinstance(body, Seq)
    assert isinstance(body.first, If)
    assert isinstance(body.first.else_branch, Assign) and body.first.else_branch.name == "Y"
    assert body.second.name == "Z"


def test_begin_end_groups_statements_in_bodies():
    loop = parse("begin while 1 > 0 do begin X := 1; Y := 2 end end").body
    assert isinstance(loop, While)
    assert isinstance(loop.body, Seq)


@pytest.mark.parametrize(
    "source",
    [
        "begin X := 1end",
        "begin X := 12ab end",
        "beginX := 1 end",
        "begin X := 1 endX",
        "begin Skip end",
        "begin X := 1; skipp end",
        "begin whileX > 0 do skip end",
        "begin X := 1 if end",
    ],
)
def test_glued_tokens_are_rejected(source):
    with pytest.raises(SiplSyntaxError):
        parse(source)


@pytest.mark.parametrize(
    "source",
    ["begin X:=1;Y:=X+2 end", "begin X := 5-3 end", "begin X := 3 - -2 end", "begin\nskip\nend"],
)
def test_compact_but_valid_programs_parse(source):
    parse(source)


def test_minus_is_subtraction_after_an_operand():
    stmt = parse("begin X := 5 -3 end").body
    assert isinstance(stmt.expression, Arithmetic) and stmt.expression.operator == "-"
    assert stmt.expression.left == Number(5) and stmt.expression.right == Number(3)
