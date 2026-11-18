"""Tests for concrete parse tree, VisNode renderers, and `sipl visualize` CLI."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from sipl.cli import main as cli_main
from sipl.errors import SiplSyntaxError
from sipl.parse_tree import parse_concrete
from sipl.parser import parse
from sipl.visualization import (
    from_ast,
    from_parse_tree,
    render_dot,
    render_html,
    render_svg,
    render_text,
)

SAMPLE_SOURCE = "begin\n  X := 2 + 3 * 4;\n  if X > 10 then Y := 1 else skip\nend"


def test_concrete_tree_tokens_reconstruct_source_and_spans():
    tree = parse_concrete(SAMPLE_SOURCE)
    tokens = list(tree.tokens())
    assert len(tokens) > 0

    for tok in tokens:
        assert tok.span is not None
        assert SAMPLE_SOURCE[tok.span.start_offset : tok.span.end_offset] == tok.text

    # Reconstruct non-whitespace source from leaf tokens
    reconstructed = "".join(tok.text or "" for tok in tokens)
    expected_compact = "".join(SAMPLE_SOURCE.split())
    assert reconstructed == expected_compact


def test_concrete_tree_preserves_uncollapsed_rule_chains_and_punctuation():
    source = "begin X := 1; Y := 2 end"
    tree = parse_concrete(source)
    symbols = [node.symbol for node in tree.walk()]

    # Uncollapsed derivation chain must be present
    for expected_rule in ("start", "statement", "sequence", "simple", "assignment"):
        assert expected_rule in symbols

    # Punctuation and keywords must be retained as terminals
    terminals = {node.text for node in tree.tokens()}
    assert {"begin", ":=", ";", "end"}.issubset(terminals)


def test_parent_spans_cover_children():
    tree = parse_concrete(SAMPLE_SOURCE)
    for node in tree.walk():
        if node.children and node.span is not None:
            child_spans = [c.span for c in node.children if c.span is not None]
            assert child_spans
            assert node.span.start_offset <= min(s.start_offset for s in child_spans)
            assert node.span.end_offset >= max(s.end_offset for s in child_spans)


def test_concrete_parser_raises_same_syntax_errors_as_ast_parser():
    bad_source = "begin X := 1; end"
    with pytest.raises(SiplSyntaxError):
        parse(bad_source)
    with pytest.raises(SiplSyntaxError):
        parse_concrete(bad_source)


def test_parse_node_to_dict_schema():
    tree = parse_concrete("begin X := 7 end")
    data = tree.to_dict()
    assert data["type"] == "nonterminal"
    assert data["symbol"] == "start"
    assert data["span"] is not None
    assert len(data["children"]) == 3
    assert data["children"][0]["type"] == "terminal"
    assert data["children"][0]["text"] == "begin"


def test_render_text_includes_roles_and_spans():
    program = parse("begin X := 42 end")
    vis = from_ast(program)
    output = render_text(vis, show_spans=True)
    assert "Program" in output
    assert "body: Assign X" in output
    assert "[1:1-1:18]" in output


def test_render_dot_node_and_edge_counts():
    program = parse(SAMPLE_SOURCE)
    vis = from_ast(program)
    all_nodes = list(vis.walk())
    dot = render_dot(vis)

    assert dot.startswith("digraph sipl_tree {")
    assert dot.endswith("}")
    # Each node emits one `[label=...]` declaration, and a tree with N nodes has N-1 edges
    node_lines = [line for line in dot.splitlines() if " [label=" in line and "->" not in line]
    edge_lines = [line for line in dot.splitlines() if "->" in line]
    assert len(node_lines) == len(all_nodes)
    assert len(edge_lines) == len(all_nodes) - 1


def test_render_svg_is_valid_xml_with_source_offsets():
    concrete = parse_concrete(SAMPLE_SOURCE)
    vis = from_parse_tree(concrete)
    svg_text = render_svg(vis, source=SAMPLE_SOURCE)

    root = ET.fromstring(svg_text)
    assert root.tag.endswith("svg")
    node_groups = [el for el in root.iter() if el.tag.endswith("g") and "data-s" in el.attrib]
    assert len(node_groups) == sum(1 for _ in vis.walk())
    for g in node_groups:
        assert "data-e" in g.attrib


def test_render_html_links_parse_tree_and_ast_fragments():
    concrete = parse_concrete(SAMPLE_SOURCE)
    program = parse(SAMPLE_SOURCE)
    html_page = render_html(
        SAMPLE_SOURCE,
        from_parse_tree(concrete),
        from_ast(program),
        title="parity.sipl",
    )
    assert "<!DOCTYPE html>" in html_page
    assert 'id="parse-panel"' in html_page
    assert 'id="ast-panel"' in html_page
    assert "data-s=" in html_page


def test_cli_visualize_combinations_and_errors(tmp_path: Path, capsys):
    src_file = tmp_path / "prog.sipl"
    src_file.write_text("begin X := 1 + 2 end", encoding="utf-8")

    # 1. Default parse -> text
    assert cli_main(["visualize", str(src_file)]) == 0
    assert "start" in capsys.readouterr().out

    # 2. AST -> JSON written to file
    ast_json_out = tmp_path / "ast.json"
    assert (
        cli_main(["visualize", str(src_file), "--kind", "ast", "--format", "json", "-o", str(ast_json_out)])
        == 0
    )
    capsys.readouterr()
    parsed_json = json.loads(ast_json_out.read_text(encoding="utf-8"))
    assert parsed_json["type"] == "Program"

    # 3. Parse -> SVG written to file
    svg_out = tmp_path / "parse.svg"
    assert (
        cli_main(["visualize", str(src_file), "--kind", "parse", "--format", "svg", "-o", str(svg_out)])
        == 0
    )
    capsys.readouterr()
    assert svg_out.read_text(encoding="utf-8").startswith("<svg")

    # 4. Compare -> default HTML
    html_out = tmp_path / "compare.html"
    assert cli_main(["visualize", str(src_file), "--kind", "compare", "-o", str(html_out)]) == 0
    capsys.readouterr()
    assert "<!DOCTYPE html>" in html_out.read_text(encoding="utf-8")

    # 5. Invalid combination (parse + html) returns exit code 1
    assert cli_main(["visualize", str(src_file), "--kind", "parse", "--format", "html"]) == 1
    capsys.readouterr()
