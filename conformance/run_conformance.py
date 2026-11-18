"""Implementation-independent conformance runner for SIPL (CORE-06)."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


def _strip_spans(node: Any) -> Any:
    """Recursively remove source-span metadata for structural AST comparison."""
    if isinstance(node, dict):
        return {k: _strip_spans(v) for k, v in node.items() if k != "span"}
    if isinstance(node, list):
        return [_strip_spans(item) for item in node]
    return node


def _extract_json_payload(stdout: str, stderr: str) -> dict[str, Any] | None:
    """Extract a JSON object from stdout or stderr."""
    for stream in (stdout, stderr):
        text = stream.strip()
        if not text:
            continue
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            for line in reversed(text.splitlines()):
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    try:
                        parsed = json.loads(line)
                        if isinstance(parsed, dict):
                            return parsed
                    except json.JSONDecodeError:
                        continue
    return None


def _classify_error(stdout: str, stderr: str) -> str:
    """Classify an implementation failure as 'syntax' or 'runtime'."""
    payload = _extract_json_payload(stdout, stderr)
    if payload is not None:
        raw_kind = str(
            payload.get("error_kind")
            or payload.get("kind")
            or payload.get("code")
            or ""
        ).lower()
        if "syntax" in raw_kind or "parse" in raw_kind or "lex" in raw_kind:
            return "syntax"
        if (
            "runtime" in raw_kind
            or "limit" in raw_kind
            or "undefined" in raw_kind
            or "unassigned" in raw_kind
        ):
            return "runtime"

    combined = f"{stdout}\n{stderr}".lower()
    syntax_markers = (
        "syntax",
        "unexpected",
        "expected",
        "parseerror",
        "larkerror",
        "end of input",
    )
    if any(marker in combined for marker in syntax_markers):
        return "syntax"
    return "runtime"


def _run_case(cmd_prefix: list[str], case: dict[str, Any]) -> list[str]:
    """Execute one conformance case and return all collected mismatch messages."""
    errors: list[str] = []
    with tempfile.NamedTemporaryFile(
        "w", suffix=".sipl", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(case["source"])
        tmp_path = Path(tmp.name)

    try:
        # 1. Check AST via `<cmd> visualize <file> --kind ast --format json` or `<cmd> parse <file>`
        if case["expect_valid"] and "expected_ast" in case:
            parse_proc = subprocess.run(
                [*cmd_prefix, "parse", str(tmp_path)],
                capture_output=True,
                text=True,
            )
            if parse_proc.returncode != 0:
                errors.append(
                    f"`parse` exited with code {parse_proc.returncode}: "
                    f"{parse_proc.stderr.strip() or parse_proc.stdout.strip()}"
                )
            else:
                try:
                    raw_ast = json.loads(parse_proc.stdout)
                    actual_ast = _strip_spans(raw_ast)
                    if actual_ast != case["expected_ast"]:
                        errors.append(
                            "AST mismatch:\n"
                            f"  expected: {json.dumps(case['expected_ast'], sort_keys=True)}\n"
                            f"  actual:   {json.dumps(actual_ast, sort_keys=True)}"
                        )
                except json.JSONDecodeError as exc:
                    errors.append(f"`parse` did not return valid JSON: {exc}")

        # 2. Check execution state or error classification via `<cmd> run <file> --json`
        run_cmd = [*cmd_prefix, "run", str(tmp_path), "--json"]
        if "max_steps" in case:
            run_cmd.extend(["--max-steps", str(case["max_steps"])])

        run_proc = subprocess.run(run_cmd, capture_output=True, text=True)

        if case["expect_valid"]:
            if run_proc.returncode != 0:
                errors.append(
                    f"`run` exited with code {run_proc.returncode}: "
                    f"{run_proc.stderr.strip() or run_proc.stdout.strip()}"
                )
            else:
                payload = _extract_json_payload(run_proc.stdout, run_proc.stderr)
                if payload is None:
                    errors.append(
                        f"`run --json` did not output valid JSON: {run_proc.stdout.strip()}"
                    )
                else:
                    actual_state = payload.get("final_state", payload)
                    if actual_state != case["expected_state"]:
                        errors.append(
                            f"State mismatch: expected {case['expected_state']}, got {actual_state}"
                        )
        else:
            if run_proc.returncode == 0:
                errors.append(
                    f"Expected {case.get('error_kind', 'error')} failure, but `run` succeeded"
                )
            elif "error_kind" in case:
                actual_kind = _classify_error(run_proc.stdout, run_proc.stderr)
                if actual_kind != case["error_kind"]:
                    errors.append(
                        f"Error kind mismatch: expected '{case['error_kind']}', got '{actual_kind}'"
                    )
    finally:
        tmp_path.unlink(missing_ok=True)

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run SIPL conformance suite.")
    parser.add_argument(
        "--cmd",
        default=f'"{sys.executable}" -m sipl',
        help='Target implementation command prefix (e.g. --cmd "sipl" or --cmd "python -m sipl")',
    )
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path(__file__).resolve().parent / "cases.json",
        help="Path to conformance cases JSON file",
    )
    args = parser.parse_args(argv)

    cmd_prefix = shlex.split(args.cmd)
    if not cmd_prefix:
        print("Error: --cmd cannot be empty.", file=sys.stderr)
        return 2

    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    passed = 0
    failed = 0

    for case in cases:
        case_id = case.get("id", "<unknown>")
        desc = case.get("description", "")
        case_errors = _run_case(cmd_prefix, case)
        if not case_errors:
            print(f"[PASS] {case_id}: {desc}")
            passed += 1
        else:
            print(f"[FAIL] {case_id}: {desc}")
            for err in case_errors:
                print(f"       - {err}")
            failed += 1

    total = passed + failed
    print(f"\nConformance summary: {passed}/{total} passed, {failed} failed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
