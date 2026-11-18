# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-11-18

### Added
- **Formal Grammar (`CORE-01`)**: LALR(1) EBNF grammar for SIPL (`src/sipl/grammar/sipl.lark`) strictly adhering to the course BNF specification (`begin ... end`, `:=`, `;`, `if ... then ... else ...`, `while ... do ...`, `skip`, `~`, `\/`, `=`, `>`, `+`, `-`, `*`). Added multi-token syntax support for boolean disjunction (`\/` canonical, with `|` and `∨` supported as synonyms).
- **Typed AST & Diagnostics (`CORE-02`)**: Immutable dataclass AST nodes (`src/sipl/ast.py`) with source position ranges (`SourceSpan`), double-dispatch visitor protocol, and structured syntax error diagnostics (`src/sipl/errors.py`).
- **Interpreter (`CORE-03`)**: Visitor-based program evaluator (`src/sipl/interpreter.py`) with variable state environments, unassigned variable protection (`NameError`), eager evaluation of boolean operands, and step-limit protection against infinite loops (`ExecutionLimitError`).
- **Execution Trace (`CORE-04`)**: Event-driven execution trace model (`src/sipl/trace.py`) emitting before/after statement transitions, variable modifications with old/new values, condition evaluations, and program completion.
- **Unified CLI (`CORE-05`)**: Command-line interface with subcommands `check`, `parse`, `run`, `trace`, and `visualize`. Standardized `--json` flag across all subcommands, exact CLI exit codes (0 = success, 1 = syntax error, 2 = runtime error, 3 = step limit exceeded), and formal JSON schema (`docs/json-schema.json`).
- **Conformance Suite (`CORE-06`)**: Implementation-independent conformance test runner (`conformance/run_conformance.py`) verifying AST representations, state transitions, and syntax/runtime error classification according to `conformance/cases.json`.
- **Parse Tree Visualization (`VIS-01`)**: Concrete syntax tree generation (`src/sipl/parse_tree.py`) with export support for ASCII text trees, Graphviz DOT, SVG, and JSON.
- **AST Visualization & Interactive Comparison (`VIS-02`)**: Standalone AST rendering and side-by-side interactive HTML visualizer with cross-tree element linking and synchronized source code highlighting.
- **CI & Release Engineering (`REL-01`, `REL-02`)**: GitHub Actions CI workflow for linting (`ruff`), type-checking (`mypy`), automated unit and integration tests (`pytest` with 96% coverage), clean-environment wheel installation, and release notes tracking.
