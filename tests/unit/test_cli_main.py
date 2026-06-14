from __future__ import annotations

from pathlib import Path

import pytest

from quill import __main__ as entry
from quill import __version__


def test_parse_cli_arguments_sets_known_flags() -> None:
    parsed = entry._parse_cli_arguments([
        "--safe-mode",
        "--reset-profile",
        "--diagnostics",
        "--new-window",
        "--wait",
        "--line",
        "12",
        "--column",
        "4",
        "demo.txt",
    ])

    assert parsed.safe_mode is True
    assert parsed.reset_profile is True
    assert parsed.diagnostics is True
    assert parsed.new_window is True
    assert parsed.wait is True
    assert parsed.line == 12
    assert parsed.column == 4
    assert parsed.paths == ["demo.txt"]


def test_parse_cli_arguments_help_exits_cleanly() -> None:
    with pytest.raises(SystemExit) as info:
        entry._parse_cli_arguments(["--help"])
    assert info.value.code == 0


def test_launch_configuration_applies_line_and_column_to_first_file(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("a", encoding="utf-8")
    second.write_text("b", encoding="utf-8")

    parsed = entry._parse_cli_arguments([
        str(first),
        str(second),
        "--line",
        "20",
        "--column",
        "6",
    ])
    requests, safe_mode, reset_profile, diagnostics_mode, force_new_window, wait = (
        entry._launch_configuration(parsed)
    )

    assert safe_mode is False
    assert reset_profile is False
    assert diagnostics_mode is False
    assert force_new_window is False
    assert wait is False
    assert len(requests) == 2
    assert requests[0].path == first.resolve()
    assert requests[0].line == 20
    assert requests[0].column == 6
    assert requests[1].path == second.resolve()
    assert requests[1].line is None
    assert requests[1].column is None


def test_main_version_prints_and_exits(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(entry.sys, "argv", ["quill", "--version"])

    result = entry.main()

    captured = capsys.readouterr()
    assert result == 0
    assert captured.out.strip() == __version__


# ---------------------------------------------------------------------------
# --goto parsing (#192)
# ---------------------------------------------------------------------------


def test_parse_goto_path_only(tmp_path: Path) -> None:
    f = tmp_path / "notes.txt"
    f.write_text("hi", encoding="utf-8")
    path, line, col = entry._parse_goto(str(f))
    assert path == f
    assert line is None
    assert col is None


def test_parse_goto_path_and_line(tmp_path: Path) -> None:
    f = tmp_path / "main.kt"
    f.write_text("fun main() {}", encoding="utf-8")
    path, line, col = entry._parse_goto(f"{f}:42")
    assert path == f
    assert line == 42
    assert col is None


def test_parse_goto_path_line_and_col(tmp_path: Path) -> None:
    f = tmp_path / "main.kt"
    f.write_text("fun main() {}", encoding="utf-8")
    path, line, col = entry._parse_goto(f"{f}:10:5")
    assert path == f
    assert line == 10
    assert col == 5


def test_parse_goto_nonexistent_file_returns_nones() -> None:
    path, line, col = entry._parse_goto("/does/not/exist.txt:5:2")
    assert path is None
    assert line is None
    assert col is None


def test_launch_configuration_goto_builds_request(tmp_path: Path) -> None:
    f = tmp_path / "main.go"
    f.write_text("package main", encoding="utf-8")
    parsed = entry._parse_cli_arguments(["--goto", f"{f}:7:3"])
    requests, *_ = entry._launch_configuration(parsed)
    assert len(requests) == 1
    assert requests[0].path == f.resolve()
    assert requests[0].line == 7
    assert requests[0].column == 3
    assert requests[0].action == "open"


# ---------------------------------------------------------------------------
# --diff parsing (#192)
# ---------------------------------------------------------------------------


def test_parse_cli_arguments_diff_flag_captured() -> None:
    parsed = entry._parse_cli_arguments(["--diff", "old.kt", "new.kt"])
    assert parsed.diff == ["old.kt", "new.kt"]


def test_launch_configuration_diff_builds_compare_request(tmp_path: Path) -> None:
    left = tmp_path / "old.kt"
    right = tmp_path / "new.kt"
    left.write_text("val x = 1", encoding="utf-8")
    right.write_text("val x = 2", encoding="utf-8")
    parsed = entry._parse_cli_arguments(["--diff", str(left), str(right)])
    requests, *_ = entry._launch_configuration(parsed)
    assert len(requests) == 1
    req = requests[0]
    assert req.path == left.resolve()
    assert req.diff_with == right.resolve()
    assert req.action == "compare"


def test_launch_configuration_diff_missing_file_ignored(tmp_path: Path) -> None:
    left = tmp_path / "old.kt"
    left.write_text("val x = 1", encoding="utf-8")
    missing = tmp_path / "missing.kt"
    parsed = entry._parse_cli_arguments(["--diff", str(left), str(missing)])
    requests, *_ = entry._launch_configuration(parsed)
    assert len(requests) == 0
