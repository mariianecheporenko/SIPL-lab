"""Comprehensive positive and negative test suite for SIPL
(CORE-01, CORE-02, CORE-03, CORE-04, CORE-05)."""

from pathlib import Path

import pytest

from sipl.cli import main as cli_main
from sipl.errors import SiplSyntaxError
from sipl.interpreter import ExecutionLimitError, Interpreter
from sipl.parser import parse

# 10 POSITIVE TESTS

@pytest.mark.parametrize(
    "source,expected_state",
    [
        # 1. Skip statement
        ("begin skip end", {}),
        # 2. Simple assignment & negative numbers
        ("begin X := -42 end", {"X": -42}),
        # 3. Operator precedence (* over + and -)
        ("begin X := 2 + 3 * 4 - 1 end", {"X": 13}),
        # 4. Parentheses override precedence
        ("begin X := (2 + 3) * (4 - 1) end", {"X": 15}),
        # 5. If-then-else true branch
        ("begin X := 5; if X = 5 then Y := 1 else Y := 0 end", {"X": 5, "Y": 1}),
        # 6. If-then-else false branch
        ("begin X := 3; if X > 5 then Y := 1 else Y := 0 end", {"X": 3, "Y": 0}),
        # 7. Boolean operators (or '\/', '|', '∨', not '~')
        (
            r"begin X := 1; if ~(X = 2) \/ (X > 10) then Y := 100 else Y := 0 end",
            {"X": 1, "Y": 100},
        ),
        # 8. Nested begin/end blocks
        ("begin begin X := 10 end; begin Y := X + 5 end end", {"X": 10, "Y": 15}),
        # 9. Factorial calculation (5! = 120)
        (
            """
            begin
                N := 5;
                R := 1;
                while N > 0 do begin
                    R := R * N;
                    N := N - 1
                end
            end
            """,
            {"N": 0, "R": 120},
        ),
        # 10. Power calculation (2^4 = 16)
        (
            """
            begin
                X := 2;
                Y := 4;
                R := 1;
                while Y > 0 do begin
                    R := R * X;
                    Y := Y - 1
                end
            end
            """,
            {"X": 2, "Y": 0, "R": 16},
        ),
    ],
)
def test_positive_programs(source: str, expected_state: dict[str, int]):
    program = parse(source)
    interpreter = Interpreter(trace=False)
    assert interpreter.execute(program) == expected_state
    assert len(interpreter.trace_events) > 0


# 10 NEGATIVE TESTS

@pytest.mark.parametrize(
    "invalid_source",
    [
        "X := 1",
        "begin end",
        "begin X := 1; end",
        "begin x := 1 end",
        "begin X = 1 end",
        "begin if 1 = 1 then X := 1 end",
        "begin while 1 = 1 skip end",
        "begin X := (1 + 2 end",
        "begin X := 10 / 2 end",
        "begin if 1 then skip else skip end",
    ],
)
def test_negative_syntax_errors(invalid_source: str):
    with pytest.raises(SiplSyntaxError):
        parse(invalid_source)


def test_runtime_infinite_loop_protection():
    source = "begin while 1 = 1 do skip end"
    program = parse(source)
    interpreter = Interpreter(trace=False, max_steps=50)
    with pytest.raises(ExecutionLimitError):
        interpreter.execute(program)


def test_runtime_unassigned_variable():
    source = "begin X := Y + 1 end"
    program = parse(source)
    interpreter = Interpreter(trace=False)
    with pytest.raises(NameError):
        interpreter.execute(program)


def test_cli_commands(tmp_path: Path):
    sipl_file = tmp_path / "sample.sipl"
    sipl_file.write_text("begin X := 7; Y := X * 2 end", encoding="utf-8")

    assert cli_main(["check", str(sipl_file), "--json"]) == 0
    assert cli_main(["parse", str(sipl_file)]) == 0
    assert cli_main(["run", str(sipl_file), "--json"]) == 0
    assert cli_main(["trace", str(sipl_file)]) == 0
