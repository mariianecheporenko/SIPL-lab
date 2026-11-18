"""CORE-04: structured trace events."""

import json
from pathlib import Path

import pytest

from sipl.cli import main as cli_main
from sipl.interpreter import ExecutionLimitError, Interpreter
from sipl.parser import parse
from sipl.trace import EventKind

KEYS = {"step", "event", "statement", "span", "variable",
        "old_value", "new_value", "result", "state"}


def run(source: str, **kwargs) -> Interpreter:
    interpreter = Interpreter(**kwargs)
    interpreter.execute(parse(source))
    return interpreter


def shape(interpreter: Interpreter):
    return [(e.kind.value, e.statement) for e in interpreter.trace_events]


def test_assignment_events():
    events = run("begin X := 5 end").trace_events
    assert shape(run("begin X := 5 end")) == [
        ("before_statement", "Assign"),
        ("variable_changed", "Assign"),
        ("after_statement", "Assign"),
        ("finished", "Program"),
    ]
    before, changed, after, finished = events
    assert before.state == {} and changed.state == {"X": 5}
    assert (changed.variable, changed.old_value, changed.new_value) == ("X", None, 5)
    assert [e.step for e in events] == [1, 2, 3, 4]


def test_variable_changed_reports_old_value():
    changed = [e for e in run("begin X := 1; X := X + 4 end").trace_events
               if e.kind is EventKind.VARIABLE_CHANGED]
    assert [(e.old_value, e.new_value) for e in changed] == [(None, 1), (1, 5)]


def test_if_events_follow_the_taken_branch():
    interpreter = run("begin X := 3; if X > 5 then Y := 1 else Y := 0 end")
    conditions = [e for e in interpreter.trace_events if e.kind is EventKind.CONDITION_EVALUATED]
    assert [(e.statement, e.result) for e in conditions] == [("If", False)]
    changed = [e for e in interpreter.trace_events
               if e.kind is EventKind.VARIABLE_CHANGED and e.variable == "Y"]
    assert [e.new_value for e in changed] == [0]
    assert shape(interpreter)[3:] == [
        ("before_statement", "If"),
        ("condition_evaluated", "If"),
        ("before_statement", "Assign"),
        ("variable_changed", "Assign"),
        ("after_statement", "Assign"),
        ("after_statement", "If"),
        ("finished", "Program"),
    ]


def test_while_emits_condition_per_iteration_and_one_statement_pair():
    interpreter = run("begin N := 2; while N > 0 do N := N - 1 end")
    events = interpreter.trace_events
    results = [e.result for e in events if e.kind is EventKind.CONDITION_EVALUATED]
    assert results == [True, True, False]
    assert sum(e.kind is EventKind.BEFORE_STATEMENT and e.statement == "While" for e in events) == 1
    assert sum(e.kind is EventKind.AFTER_STATEMENT and e.statement == "While" for e in events) == 1


def test_skip_events():
    assert shape(run("begin skip end")) == [
        ("before_statement", "Skip"),
        ("after_statement", "Skip"),
        ("finished", "Program"),
    ]


def test_before_and_after_are_properly_nested():
    source = (
            "begin X := 2; while X > 0 do "
            "begin if X = 1 then skip else X := X - 1; X := X - 1 end end"
        )
    stack = []
    for e in run(source).trace_events:
        if e.kind is EventKind.BEFORE_STATEMENT:
            stack.append(e.statement)
        elif e.kind is EventKind.AFTER_STATEMENT:
            assert stack and stack.pop() == e.statement
    assert stack == []


def test_event_spans_point_to_source_fragments():
    source = "begin X := 3; if X > 5 then Y := 1 else Y := 0 end"

    def text(e):
        return source[e.span.start_offset:e.span.end_offset]

    events = run(source).trace_events
    assert text(events[0]) == "X := 3"
    events = run(source).trace_events
    assert text(events[0]) == "X := 3"
    condition = next(e for e in events if e.kind is EventKind.CONDITION_EVALUATED)
    assert text(condition) == "X > 5"
    assert text(events[-1]) == source  # finished -> whole program


def test_events_are_json_serialisable_with_stable_keys():
    for e in run("begin N := 2; while N > 0 do N := N - 1 end").trace_events:
        data = e.to_dict()
        assert set(data) == KEYS
        json.dumps(data)


def test_listener_receives_every_event():
    seen = []
    interpreter = run("begin X := 1 end", listener=seen.append)
    assert seen == interpreter.trace_events


def test_trace_flag_prints_json_lines(capsys):
    run("begin skip end", trace=True)
    lines = capsys.readouterr().out.strip().splitlines()
    assert [json.loads(line)["event"] for line in lines] == [
        "before_statement", "after_statement", "finished"]


def test_partial_trace_is_kept_when_the_step_limit_is_hit():
    interpreter = Interpreter(max_steps=10)
    with pytest.raises(ExecutionLimitError):
        interpreter.execute(parse("begin while 1 = 1 do skip end"))
    assert len(interpreter.trace_events) == 10


def test_execute_starts_a_fresh_run():
    interpreter = Interpreter()
    program = parse("begin X := 1 end")
    interpreter.execute(program)
    first = len(interpreter.trace_events)
    interpreter.execute(parse("begin Y := 2 end"))
    assert interpreter.state == {"Y": 2}
    assert len(interpreter.trace_events) == first


def test_cli_trace_json_schema(tmp_path: Path, capsys):
    path = tmp_path / "t.sipl"
    path.write_text("begin X := 1; if X = 1 then skip else skip end", encoding="utf-8")
    assert cli_main(["trace", str(path)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok" and payload["final_state"] == {"X": 1}
    assert all(set(e) == KEYS for e in payload["trace"])
    assert payload["trace"][0]["event"] == "before_statement"
    assert payload["trace"][-1]["event"] == "finished"
