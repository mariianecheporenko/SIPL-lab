"""Text, DOT, SVG and HTML renderers for :class:`~sipl.visualization.model.VisNode` trees."""

from __future__ import annotations

import html
import json
from string import Template
from xml.sax.saxutils import escape

from ..ast import SourceSpan
from .model import VisNode


def _span_text(span: SourceSpan | None) -> str:
    if span is None:
        return ""
    return f"  [{span.start_line}:{span.start_column}-{span.end_line}:{span.end_column}]"


def render_text(root: VisNode, *, show_spans: bool = True) -> str:
    lines: list[str] = []

    def describe(node: VisNode) -> str:
        head = f"{node.role}: {node.label}" if node.role else node.label
        return head + (_span_text(node.span) if show_spans else "")

    def walk(node: VisNode, prefix: str, is_last: bool) -> None:
        lines.append(prefix + ("`-- " if is_last else "|-- ") + describe(node))
        child_prefix = prefix + ("    " if is_last else "|   ")
        for index, child in enumerate(node.children):
            walk(child, child_prefix, index == len(node.children) - 1)

    lines.append(describe(root))
    for index, child in enumerate(root.children):
        walk(child, "", index == len(root.children) - 1)
    return "\n".join(lines)


# ----------------------------------------------------------------------------
# DOT
# ----------------------------------------------------------------------------

_FILL = {
    "nonterminal": "#e8eefc",
    "terminal": "#fff4d6",
    "program": "#e5e5e5",
    "statement": "#dff3e3",
    "expression": "#fde8e4",
    "condition": "#efe4fa",
}


def dot_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def render_dot(root: VisNode, *, name: str = "sipl_tree") -> str:
    """Graphviz DOT source (render it with ``dot -Tsvg`` if Graphviz is installed)."""
    lines = [
        f"digraph {name} {{",
        '  node [shape=box, style="rounded,filled", fontname="monospace"];',
    ]
    counter = 0

    def add(node: VisNode) -> str:
        nonlocal counter
        node_id = f"n{counter}"
        counter += 1
        fill = _FILL.get(node.kind, "#ffffff")
        lines.append(f'  {node_id} [label="{dot_escape(node.label)}", fillcolor="{fill}"];')
        for child in node.children:
            child_id = add(child)
            attrs = f' [label="{dot_escape(child.role)}"]' if child.role else ""
            lines.append(f"  {node_id} -> {child_id}{attrs};")
        return node_id

    add(root)
    lines.append("}")
    return "\n".join(lines)


# ----------------------------------------------------------------------------
# SVG
# ----------------------------------------------------------------------------

CHAR_W = 7.2
PAD_X = 8
NODE_H = 26
GAP_X = 14
GAP_Y = 40
MARGIN = 16

_SVG_STYLE = """
.edge{stroke:#8a8a8a;stroke-width:1.2;fill:none}
.role{font-size:10px;fill:#555}
.role-bg{fill:#fff}
.node{cursor:pointer}
.node rect{stroke-width:1.2}
.node text{fill:#111}
.k-nonterminal rect{fill:#e8eefc;stroke:#5b7bd5}
.k-terminal rect{fill:#fff4d6;stroke:#c9a227}
.k-program rect{fill:#e5e5e5;stroke:#777}
.k-statement rect{fill:#dff3e3;stroke:#3f9b57}
.k-expression rect{fill:#fde8e4;stroke:#d0634f}
.k-condition rect{fill:#efe4fa;stroke:#8a57c2}
.node.sel rect{stroke:#d40000;stroke-width:3}
""".strip()


def _node_width(label: str) -> float:
    return len(label) * CHAR_W + 2 * PAD_X


def _tooltip(node: VisNode, source: str | None) -> str:
    text = node.label
    if node.span is not None:
        span = node.span
        text += f"\n{span.start_line}:{span.start_column} - {span.end_line}:{span.end_column}"
        if source is not None:
            fragment = " ".join(source[span.start_offset : span.end_offset].split())
            if len(fragment) > 80:
                fragment = fragment[:77] + "..."
            text += f"\n{fragment}"
    return text


def render_svg(root: VisNode, *, source: str | None = None, prefix: str = "n") -> str:
    """Standalone SVG tree.  Each node is a ``<g>`` with ``data-s``/``data-e`` source offsets."""
    widths: dict[int, float] = {}

    def measure(node: VisNode) -> float:
        own = _node_width(node.label)
        total = sum(measure(c) for c in node.children) + GAP_X * max(len(node.children) - 1, 0)
        widths[id(node)] = max(own, total)
        return widths[id(node)]

    positions: dict[int, tuple[float, int]] = {}
    depth_max = 0

    def place(node: VisNode, left: float, depth: int) -> None:
        nonlocal depth_max
        depth_max = max(depth_max, depth)
        width = widths[id(node)]
        positions[id(node)] = (left + width / 2, depth)
        if node.children:
            total = sum(widths[id(c)] for c in node.children) + GAP_X * (len(node.children) - 1)
            x = left + (width - total) / 2
            for child in node.children:
                place(child, x, depth + 1)
                x += widths[id(child)] + GAP_X

    measure(root)
    place(root, MARGIN, 0)
    total_w = widths[id(root)] + 2 * MARGIN
    total_h = depth_max * (NODE_H + GAP_Y) + NODE_H + 2 * MARGIN

    def top(depth: int) -> float:
        return MARGIN + depth * (NODE_H + GAP_Y)

    edges: list[str] = []
    nodes: list[str] = []
    counter = 0

    def draw(node: VisNode) -> None:
        nonlocal counter
        node_id = f"{prefix}{counter}"
        counter += 1
        cx, depth = positions[id(node)]
        w = _node_width(node.label)
        y = top(depth)
        for child in node.children:
            ccx, cdepth = positions[id(child)]
            x1, y1, x2, y2 = cx, y + NODE_H, ccx, top(cdepth)
            edges.append(
                f'<line class="edge" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/>'
                )
            if child.role:
                mx, my = (x1 + x2) / 2, (y1 + y2) / 2
                role_w = len(child.role) * 6 + 6
                edges.append(
                    f'<rect class="role-bg" x="{mx - role_w / 2:.1f}" y="{my - 8:.1f}" '
                    f'width="{role_w:.1f}" height="12"/>'
                    f'<text class="role" x="{mx:.1f}" y="{my + 1.5:.1f}" '
                    f'text-anchor="middle">{escape(child.role)}</text>'
                )
        data = ""
        if node.span is not None:
            data = f' data-s="{node.span.start_offset}" data-e="{node.span.end_offset}"'
        nodes.append(
            f'<g class="node k-{node.kind}" id="{node_id}"{data}>'
            f"<title>{escape(_tooltip(node, source))}</title>"
            f'<rect x="{cx - w / 2:.1f}" y="{y:.1f}" width="{w:.1f}" height="{NODE_H}" rx="5"/>'
            f'<text x="{cx:.1f}" y="{y + NODE_H / 2 + 4:.1f}" '
            f'text-anchor="middle">{escape(node.label)}</text>'
            "</g>"
        )
        for child in node.children:
            draw(child)

    draw(root)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_w:.0f}" height="{total_h:.0f}" '
        f'viewBox="0 0 {total_w:.0f} {total_h:.0f}" font-family="monospace" font-size="12">'
        f"<style>{_SVG_STYLE}</style>"
        f'<rect width="100%" height="100%" fill="#ffffff"/>'
        + "".join(edges)
        + "".join(nodes)
        + "</svg>"
    )


# ----------------------------------------------------------------------------
# HTML (Parse Tree <-> AST, linked to the source text)
# ----------------------------------------------------------------------------

_HTML = Template(
    """<!DOCTYPE html>
<html lang="uk">
<head>
<meta charset="utf-8">
<title>SIPL: $title</title>
<style>
body{font-family:system-ui,sans-serif;margin:16px;background:#fff;color:#111}
h1{font-size:18px;margin:0 0 8px}
h2{font-size:15px;margin:18px 0 6px}
#hint{color:#555;font-size:13px;margin-bottom:8px}
pre#source{background:#f6f6f6;border:1px solid #ddd;border-radius:6px;padding:10px;
margin:0;font-size:14px;overflow:auto}
pre#source mark{background:#ffd54a;outline:1px solid #d49a00}
.panel{border:1px solid #ddd;border-radius:6px;overflow:auto;max-height:70vh}
</style>
</head>
<body>
<h1>$title</h1>
<div id="hint">Наведіть курсор або клацніть на будь-який вузол дерева — відповідний
фрагмент коду підсвітиться, так само як вузли з тим самим фрагментом в іншому дереві.
Клацніть на порожнє місце, щоб скинути вибір.</div>
<h2>Вихідний код</h2>
<pre id="source">$source_html</pre>
<h2>Дерево виводу (конкретний синтаксис): $n_parse вузлів</h2>
<div class="panel" id="parse-panel">$parse_svg</div>
<h2>AST (абстрактний синтаксис): $n_ast вузлів</h2>
<div class="panel" id="ast-panel">$ast_svg</div>
<script id="source-data" type="application/json">$source_json</script>
<script>
(function () {
  var source = JSON.parse(document.getElementById("source-data").textContent);
  var pre = document.getElementById("source");
  var nodes = document.querySelectorAll("g.node[data-s]");
  function show(start, end) {
    pre.textContent = "";
    pre.appendChild(document.createTextNode(source.slice(0, start)));
    var mark = document.createElement("mark");
    mark.textContent = source.slice(start, end);
    pre.appendChild(mark);
    pre.appendChild(document.createTextNode(source.slice(end)));
  }
  function clearSelection() {
    pre.textContent = source;
    nodes.forEach(function (g) { g.classList.remove("sel"); });
  }
  nodes.forEach(function (g) {
    g.addEventListener("click", function (event) {
      event.stopPropagation();
      var start = Number(g.dataset.s), end = Number(g.dataset.e);
      nodes.forEach(function (other) {
        var same =
          Number(other.dataset.s) === start && Number(other.dataset.e) === end;
        other.classList.toggle("sel", same);
      });
      show(start, end);
    });
  });
  document.querySelectorAll(".panel svg").forEach(function (svg) {
    svg.addEventListener("click", clearSelection);
  });
})();
</script>
</body>
</html>
"""
)


def json_for_script(value: object) -> str:
    """JSON that is safe inside an HTML ``<script>`` element."""
    return (
        json.dumps(value)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


def render_html(source: str, parse_root: VisNode, ast_root: VisNode, *, title: str = "SIPL") -> str:
    """Self-contained page: source text, derivation tree and AST, linked by source ranges."""
    return _HTML.substitute(
        title=html.escape(title),
        source_html=html.escape(source),
        source_json=json_for_script(source),
        parse_svg=render_svg(parse_root, source=source, prefix="p"),
        ast_svg=render_svg(ast_root, source=source, prefix="a"),
        n_parse=sum(1 for _ in parse_root.walk()),
        n_ast=sum(1 for _ in ast_root.walk()),
    )
