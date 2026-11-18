"""SourceSpan on every AST node and structured syntax diagnostics."""

import json
from pathlib import Path

import pytest

from sipl.ast import Arithmetic, Assign, Number, Seq, SourceSpan, Variable, While
from sipl.cli import main as cli_main
from sipl.errors import SiplSyntaxError
from sipl.parser import parse


def fragment(source: str, node) -> str:
    assert node.span is not None, f"{type(node).__name__} has no span"
    return source[node.span.start_offset : node.span.end_offset]


def test_spans_cover_exact_source_fragments():
    source = "begin X := 7; Y := X * 2 end"
    program = parse(source)
    assert fragment(source, program) == source

    seq = program.body
    assert isinstance(seq, Seq)
    assert fragment(source, seq) == "X := 7; Y := X * 2"
    assert isinstance(seq.first, Assign) and isinstance(seq.second, Assign)
    assert fragment(source, seq.first) == "X := 7"
    assert fragment(source, seq.first.expression) == "7"
    assert fragment(source, seq.second) == "Y := X * 2"

    product = seq.second.expression
    assert isinstance(product, Arithmetic)
    assert fragment(source, product) == "X * 2"
    assert isinstance(product.left, Variable) and fragment(source, product.left) == "X"
    assert isinstance(product.right, Number) and fragment(source, product.right) == "2"


def test_spans_for_if_and_conditions():
    source = (
        "begin\n"
        "  if 1 > 0 | ~(1 = 1) then skip else Y := 1;\n"
        "  while Y > 0 do begin Y := Y - 1 end\n"
        "end"
    )
    if_stmt = parse(source).body.first
    assert fragment(source, if_stmt).startswith("if 1 > 0")
    assert fragment(source, if_stmt.then_branch) == "skip"
    assert fragment(source, if_stmt.else_branch) == "Y := 1"
    assert fragment(source, if_stmt.condition) == "1 > 0 | ~(1 = 1)"
    assert fragment(source, if_stmt.condition.right) == "~(1 = 1)"


def test_multiline_line_and_column_numbers():
    source = "begin\n  N := 3;\n  while N > 0 do begin\n    N := N - 1\n  end\nend"
    loop = parse(source).body.second
    assert isinstance(loop, While)
    span = loop.span
    assert (span.start_line, span.start_column) == (3, 3)
    assert (span.end_line, span.end_column) == (5, 6)  # end is exclusive


def test_equality_and_hash_ignore_spans():
    compact = parse("begin X := 1 end")
    spaced = parse("begin\n    X := 1\nend")
    assert compact.span != spaced.span
    assert compact == spaced
    assert hash(compact) == hash(spaced)


def test_to_dict_has_type_and_optional_spans():
    program = parse("begin X := 1 end")
    data = program.to_dict()
    assert data["type"] == "Program"
    assert data["body"]["type"] == "Assign"
    assert data["body"]["expression"]["type"] == "Number"
    assert data["body"]["expression"]["span"]["start_offset"] == 11
    json.dumps(data)  # must be JSON-serialisable

    bare = program.to_dict(include_spans=False)
    assert "span" not in bare and "span" not in bare["body"]


@pytest.mark.parametrize(
    "source,line,column,message_part",
    [
        ("X := 1", 1, 1, "Unexpected 'X'"),
        ("begin X := 1; end", 1, 15, "Unexpected 'end'"),
        ("begin X = 1 end", 1, 9, "expected ':='"),
        ("begin X := (1 + 2 end", 1, 19, "expected ')'"),
        ("begin X := 10 / 2 end", 1, 15, "Unexpected '/'"),
        ("begin X := 1", 1, 13, "end of input"),
        ("begin\n  X := 1;\nend", 3, 1, "Unexpected 'end'"),
        ("", 1, 1, "end of input"),
    ],
)
def test_syntax_error_diagnostics(source, line, column, message_part):
    with pytest.raises(SiplSyntaxError) as info:
        parse(source)
    error = info.value
    assert (error.line, error.column) == (line, column)
    assert message_part in error.diagnostic.message
    assert f"line {line}, column {column}" in str(error)
    span = error.diagnostic.span
    assert isinstance(span, SourceSpan)
    assert span.start_offset <= span.end_offset <= len(source)


def test_cli_reports_diagnostic_as_json(tmp_path: Path, capsys):
    bad = tmp_path / "bad.sipl"
    bad.write_text("begin\n  X := 1;\nend", encoding="utf-8")
    assert cli_main(["check", str(bad), "--json"]) == 1
    payload = json.loads(capsys.readouterr().err)
    assert payload["status"] == "error"
    diagnostic = payload["diagnostics"][0]
    assert diagnostic["severity"] == "error"
    assert diagnostic["span"]["start_line"] == 3
    assert diagnostic["span"]["start_column"] == 1