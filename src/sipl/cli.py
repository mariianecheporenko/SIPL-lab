"""Command-line interface for the SIPL Language Toolkit."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from . import __version__
from .errors import SiplError, SiplSyntaxError
from .interpreter import ExecutionLimitError, Interpreter
from .parse_tree import parse_concrete
from .parser import parse
from .visualization import (
    from_ast,
    from_parse_tree,
    render_dot,
    render_html,
    render_svg,
    render_text,
)


def _read_source(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"SIPL source file not found: {path}")
    return path.read_text(encoding="utf-8")


def cmd_check(path: Path, as_json: bool = False) -> int:
    source = _read_source(path)
    parse(source)
    if as_json:
        print(json.dumps({"status": "ok", "file": str(path)}))
    else:
        print(f"OK: {path}")
    return 0


def cmd_parse(path: Path) -> int:
    source = _read_source(path)
    program = parse(source)
    print(json.dumps(program.to_dict(), indent=2))
    return 0


def cmd_run(path: Path, max_steps: int, as_json: bool) -> int:
    source = _read_source(path)
    program = parse(source)
    interpreter = Interpreter(max_steps=max_steps)
    final_state = interpreter.execute(program)

    if as_json:
        print(
            json.dumps(
                {
                    "status": "ok",
                    "final_state": final_state,
                    "steps": interpreter.steps,
                },
                indent=2,
            )
        )
    else:
        print(f"Final state: {final_state}")
    return 0


def cmd_trace(path: Path, max_steps: int) -> int:
    source = _read_source(path)
    program = parse(source)
    interpreter = Interpreter(max_steps=max_steps)
    final_state = interpreter.execute(program)
    events = [
        asdict(ev) if not hasattr(ev, "to_dict") else ev.to_dict()
        for ev in interpreter.trace_events
    ]
    print(
        json.dumps(
            {
                "status": "ok",
                "final_state": final_state,
                "trace": events,
            },
            indent=2,
            default=str,
        )
    )
    return 0


def cmd_visualize(
    path: Path,
    kind: str = "parse",
    fmt: str | None = None,
    output: Path | None = None,
) -> int:
    """Render the derivation tree, the AST, or both side by side."""
    source = _read_source(path)
    fmt = fmt or ("html" if kind == "compare" else "text")

    if kind == "compare":
        concrete = parse_concrete(source)
        program = parse(source)
        parse_vis, ast_vis = from_parse_tree(concrete), from_ast(program)
        if fmt == "html":
            rendered = render_html(source, parse_vis, ast_vis, title=path.name)
        elif fmt == "text":
            rendered = (
                "Parse tree:\n" + render_text(parse_vis) + "\n\nAST:\n" + render_text(ast_vis)
            )
        elif fmt == "json":
            rendered = json.dumps(
                {"parse_tree": concrete.to_dict(), "ast": program.to_dict()}, indent=2
            )
        else:
            raise ValueError("--kind compare supports --format html, text or json")
    else:
        if kind == "parse":
            concrete = parse_concrete(source)
            vis, data = from_parse_tree(concrete), concrete.to_dict()
        else:
            program = parse(source)
            vis, data = from_ast(program), program.to_dict()
        if fmt == "text":
            rendered = render_text(vis)
        elif fmt == "json":
            rendered = json.dumps(data, indent=2)
        elif fmt == "dot":
            rendered = render_dot(vis)
        elif fmt == "svg":
            rendered = render_svg(vis, source=source)
        else:
            raise ValueError("--format html is only available with --kind compare")

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
        print(f"Wrote {output}")
    else:
        print(rendered)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SIPL Language Toolkit CLI.")
    parser.add_argument("--version", action="version", version=f"sipl {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    p_check = commands.add_parser("check", help="validate SIPL syntax")
    p_check.add_argument("file", type=Path)
    p_check.add_argument("--json", action="store_true", dest="as_json")
    p_check.set_defaults(handler=lambda args: cmd_check(args.file, args.as_json))

    p_parse = commands.add_parser("parse", help="print AST as JSON")
    p_parse.add_argument("file", type=Path)
    p_parse.add_argument("--json", action="store_true", dest="as_json")
    p_parse.set_defaults(handler=lambda args: cmd_parse(args.file))

    p_run = commands.add_parser("run", help="execute a SIPL program")
    p_run.add_argument("file", type=Path)
    p_run.add_argument("--max-steps", type=int, default=10_000)
    p_run.add_argument("--json", action="store_true", dest="as_json")
    p_run.set_defaults(handler=lambda args: cmd_run(args.file, args.max_steps, args.as_json))

    p_trace = commands.add_parser("trace", help="execute and print JSON trace events")
    p_trace.add_argument("file", type=Path)
    p_trace.add_argument("--max-steps", type=int, default=10_000)
    p_trace.add_argument("--json", action="store_true", dest="as_json")
    p_trace.set_defaults(handler=lambda args: cmd_trace(args.file, args.max_steps))

    p_vis = commands.add_parser(
        "visualize", help="render the parse tree, the AST, or both (text/json/dot/svg/html)"
    )
    p_vis.add_argument("file", type=Path)
    p_vis.add_argument(
        "--kind",
        choices=["parse", "ast", "compare"],
        default="parse",
        help="parse = derivation tree, ast = abstract syntax tree, compare = both",
    )
    p_vis.add_argument(
        "--format",
        choices=["text", "json", "dot", "svg", "html"],
        default=None,
        help="default: html for --kind compare, text otherwise",
    )
    p_vis.add_argument("-o", "--output", type=Path, help="write to a file instead of stdout")
    p_vis.add_argument("--json", action="store_true", dest="as_json")
    p_vis.set_defaults(
        handler=lambda args: cmd_visualize(
            args.file,
            args.kind,
            "json" if args.as_json else args.format,
            args.output,
        )
    )

    return parser


def _extract_diag(exc: SiplError) -> dict[str, Any]:
    if hasattr(exc.diagnostic, "to_dict"):
        return exc.diagnostic.to_dict()
    if is_dataclass(exc.diagnostic):
        return asdict(exc.diagnostic)
    return {"code": exc.diagnostic.code, "message": exc.diagnostic.message}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except SiplSyntaxError as exc:
        diag = _extract_diag(exc)
        payload = {
            "status": "error",
            "error_kind": "syntax",
            "diagnostics": [diag],
            **diag,
        }
        print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)
        return 1
    except SiplError as exc:
        diag = _extract_diag(exc)
        payload = {
            "status": "error",
            "error_kind": "runtime",
            "diagnostics": [diag],
            **diag,
        }
        print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)
        return 2
    except ExecutionLimitError as exc:
        err_diag = {"code": "E_STEP_LIMIT", "message": str(exc)}
        payload = {
            "status": "error",
            "error_kind": "step_limit",
            "diagnostics": [err_diag],
            **err_diag,
        }
        print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)
        return 3
    except (OSError, ValueError) as exc:
        err_diag = {"code": "E_RUNTIME", "message": str(exc)}
        payload = {
            "status": "error",
            "error_kind": "runtime",
            "diagnostics": [err_diag],
            **err_diag,
        }
        print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
