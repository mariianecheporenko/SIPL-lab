"""Command-line tools for parsing, checking, running, tracing, and visualizing SIPL."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

from lark.tree import pydot__tree_to_png, pydot__tree_to_dot

try:
    from .interpreter import Interpreter
    from .parser import parse, parse_tree
except ImportError:
    from interpreter import Interpreter
    from parser import parse, parse_tree


def _read_source(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Could not read {path}: {exc}") from exc


def cmd_parse(path: Path) -> int:
    program = parse(_read_source(path))
    print(json.dumps(asdict(program), indent=2))
    return 0


def cmd_check(path: Path, as_json: bool = False) -> int:
    parse(_read_source(path))
    if as_json:
        print(json.dumps({"status": "ok", "file": str(path)}))
    else:
        print(f"Syntax OK: {path}")
    return 0


def cmd_run(path: Path, as_json: bool = False, max_steps: int = 10000) -> int:
    program = parse(_read_source(path))
    interpreter = Interpreter(trace=False, max_steps=max_steps)
    final_state = interpreter.execute(program)
    if as_json:
        print(json.dumps({"status": "ok", "final_state": final_state}))
    else:
        print(f"Final state: {final_state}")
    return 0


def cmd_trace(path: Path, max_steps: int = 10000) -> int:
    program = parse(_read_source(path))
    interpreter = Interpreter(trace=False, max_steps=max_steps)
    final_state = interpreter.execute(program)
    output = {
        "status": "ok",
        "final_state": final_state,
        "trace": interpreter.trace_events,
    }
    print(json.dumps(output, indent=2))
    return 0

def cmd_visualize(path: Path) -> int:
    source = _read_source(path)
    tree = parse_tree(source)
    program = parse(source)
    ast_json = json.dumps(asdict(program), indent=2)

    txt_path = path.with_suffix(".tree.txt")
    dot_path = path.with_suffix(".dot")
    image_path = path.with_suffix(".parse_tree.png")
    html_path = path.with_suffix(".compare.html")

    txt_path.write_text(tree.pretty(), encoding="utf-8")
    pydot__tree_to_dot(tree, str(dot_path))
    try:
        pydot__tree_to_png(tree, str(image_path))
    except (ImportError, RuntimeError, OSError):
        pass

    html_content = f"""<!DOCTYPE html>
<html lang="uk">
<head><meta charset="utf-8"><title>SIPL Parse Tree vs AST</title>
<style>body{{font-family:sans-serif;display:flex;gap:20px;padding:20px}}
.box{{flex:1;border:1px solid #ccc;padding:15px;border-radius:8px;background:#f9f9f9}}
pre{{overflow-x:auto;font-size:13px}}</style></head>
<body>
  <div class="box"><h3>Concrete Syntax (Parse Tree)</h3><pre>{tree.pretty()}</pre></div>
  <div class="box"><h3>Abstract Syntax Tree (AST JSON)</h3><pre>{ast_json}</pre></div>
</body></html>"""

    html_path.write_text(html_content, encoding="utf-8")

    print(f"Parse tree text: {txt_path}")
    print(f"Parse tree DOT:  {dot_path}")
    print(f"Parse tree PNG:  {image_path}")
    print(f"HTML comparison: {html_path}")
    print(ast_json)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SIPL Language Toolkit CLI.")
    commands = parser.add_subparsers(dest="command", required=True)

    p_parse = commands.add_parser("parse", help="parse file and output AST as JSON")
    p_parse.add_argument("file", type=Path)
    p_parse.set_defaults(handler=lambda args: cmd_parse(args.file))

    p_check = commands.add_parser("check", help="validate SIPL syntax")
    p_check.add_argument("file", type=Path)
    p_check.add_argument("--json", action="store_true", help="output in JSON format")
    p_check.set_defaults(handler=lambda args: cmd_check(args.file, args.json))

    p_run = commands.add_parser("run", help="execute a SIPL source file")
    p_run.add_argument("file", type=Path)
    p_run.add_argument("--json", action="store_true", help="output in JSON format")
    p_run.add_argument("--max-steps", type=int, default=10000)
    p_run.set_defaults(
        handler=lambda args: cmd_run(args.file, args.json, args.max_steps)
    )

    p_trace = commands.add_parser("trace", help="execute and output full JSON trace")
    p_trace.add_argument("file", type=Path)
    p_trace.add_argument("--max-steps", type=int, default=10000)
    p_trace.set_defaults(handler=lambda args: cmd_trace(args.file, args.max_steps))

    p_vis = commands.add_parser(
        "visualize", help="save parse tree PNG and print AST JSON"
    )
    p_vis.add_argument("file", type=Path)
    p_vis.set_defaults(handler=lambda args: cmd_visualize(args.file))

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())