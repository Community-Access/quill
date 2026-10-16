"""QUILL Transcribe's tested-programs table matches the harness's results (D-4)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[3]


def _script():
    spec = importlib.util.spec_from_file_location(
        "build_transcribe_compatibility", _REPO / "scripts" / "build_transcribe_compatibility.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_user_guide_table_is_current() -> None:
    assert not _script().stale(), "run: python scripts/build_transcribe_compatibility.py"


def test_every_harness_target_has_a_row() -> None:
    keys = [row["key"] for row in _script().load()["programs"]]
    assert keys == ["notepad", "wordpad", "word", "outlook", "edge", "chrome", "firefox", "vscode"]


def test_every_row_cites_a_check_date_and_a_review_date() -> None:
    script = _script()
    for row in script.load()["programs"]:
        assert row.get("date"), row["key"]
        assert script._review_by(row["date"]) != "-", row["key"]


@pytest.mark.parametrize(
    ("row", "label"),
    [
        ({"status": "tested", "phrases_sent": 20, "phrases_exact": 19}, "Supported"),
        ({"status": "tested", "phrases_sent": 20, "phrases_exact": 18}, "Best effort"),
        ({"status": "tested", "phrases_sent": 20, "phrases_exact": 10}, "Best effort"),
        ({"status": "tested", "phrases_sent": 20, "phrases_exact": 9}, "Unsupported"),
        # Never "unsupported" for want of a test: not installed, skipped for
        # safety, or a run that stopped early are all untested.
        ({"status": "untested", "reason": "not installed"}, "Untested"),
        ({"status": "skipped", "reason": "already running"}, "Untested"),
        (
            {"status": "tested", "phrases_sent": 4, "phrases_exact": 0, "incomplete": "x"},
            "Untested",
        ),
        ({"status": "tested", "phrases_sent": 0, "phrases_exact": 0}, "Untested"),
    ],
)
def test_classification(row: dict, label: str) -> None:
    assert _script().classify(row) == label


def test_an_interrupted_run_shows_no_count_and_no_reason_in_the_guide() -> None:
    script = _script()
    row = {
        "key": "notepad",
        "program": "Notepad",
        "date": "2026-10-15",
        "status": "tested",
        "phrases_sent": 4,
        "phrases_exact": 0,
        "incomplete": "another window came to the front (msedge.exe)",
    }
    table = script.render({"phrases": ["a"], "programs": [row]})
    assert "| Notepad | - | Untested | - | 2026-10-15 | 2027-01-13 |" in table
    assert "msedge" not in table


def test_the_table_replaces_only_what_is_between_the_markers() -> None:
    script = _script()
    guide = f"before\n{script.START}\nold\n{script.END}\nafter\n"
    assert script.apply(guide, "new\n") == f"before\n{script.START}\nnew\n{script.END}\nafter\n"
    with pytest.raises(ValueError):
        script.apply("no markers here", "new\n")
