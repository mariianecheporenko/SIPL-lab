"""Tests for package resources, version metadata, and directory-independent CLI execution."""

from __future__ import annotations

import subprocess
import sys
from importlib import resources
from pathlib import Path

import sipl
from sipl.cli import main as cli_main


def test_grammar_bundled_as_package_resource():
    grammar_file = resources.files("sipl.grammar").joinpath("sipl.lark")
    assert grammar_file.is_file()
    text = grammar_file.read_text(encoding="utf-8")
    assert "start:" in text
    assert "_BEGIN:" in text


def test_version_attribute_is_non_empty_string():
    assert isinstance(sipl.__version__, str)
    assert len(sipl.__version__) > 0


def test_cli_works_from_outside_repository_root(tmp_path: Path, monkeypatch):
    prog = tmp_path / "outside.sipl"
    prog.write_text("begin X := 6 * 7 end", encoding="utf-8")

    # Switch current working directory to tmp_path (outside the repo)
    monkeypatch.chdir(tmp_path)

    assert cli_main(["check", str(prog)]) == 0
    assert cli_main(["run", str(prog)]) == 0


def test_python_m_sipl_entrypoint(tmp_path: Path):
    prog = tmp_path / "mod.sipl"
    prog.write_text("begin X := 9 end", encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, "-m", "sipl", "check", str(prog)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
