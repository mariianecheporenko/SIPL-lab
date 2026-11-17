# Changelog

## [0.1.0] - 2026-11-17

### Added
- Formal Grammar (`CORE-01`): EBNF grammar for SIPL (`grammar/sipl.lark`) strictly aligned with the course BNF specification 
  (`begin ... end`, `:=`, `;`, `if ... then ... else ...`, `while ... do ...`, `skip`, `~`, `\/`, `=`, `>`, `+`, `-`, `*`) 
  and 3 sample programs (`examples/parity.sipl`, `examples/power.sipl`, `examples/div.sipl`).
- Typed AST & Parser (`CORE-02`): Strongly-typed `dataclass` AST nodes (`src/sipl/ast.py`) and 
  Lark transformer (`src/sipl/parser.py`) with syntax error diagnostics.
- Interpreter & Execution Trace (`CORE-03`, `CORE-04`): Visitor-based state evaluator (`src/sipl/interpreter.py`) with infinite-loop protection (`max_steps`) 
  and structured JSON execution trace events (`before_assign`, `after_assign`, `if_condition`, `while_condition`, `skip`, `finished`).
- CLI & Visualization (`CORE-05`, `VIS-01`, `VIS-02`): Command-line interface (`src/sipl/cli.py`) supporting `parse`, `check`, `run`, `trace`, 
  and `visualize` (Parse Tree export to Text/DOT/PNG and side-by-side Parse Tree vs AST HTML comparison).
- Conformance & Test Suite (`CORE-06`, `REL-01`, `REL-02`): Automated pytest suite (positive/negative cases), implementation-independent conformance test suite (`conformance/`), 
  GitHub Actions CI workflow, and project task specification (`docs/PLAN.md`).