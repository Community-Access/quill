"""ActivityLog persistence, bounding, redaction, and last-undoable lookup."""

from __future__ import annotations

from pathlib import Path

from quill.core.ai.activity_log import ActivityEntry, ActivityLog


def _log(tmp_path: Path) -> ActivityLog:
    return ActivityLog(tmp_path / "activity.json")


def test_append_and_read_roundtrip(tmp_path: Path) -> None:
    log = _log(tmp_path)
    log.append(
        ActivityEntry.now(
            kind="tool_call_completed",
            agent_id="writing-companion",
            harness="native",
            summary="Rewrote selection.",
            detail={"category": "modify_selection"},
        )
    )
    entries = log.all()
    assert len(entries) == 1
    assert entries[0].kind == "tool_call_completed"
    assert entries[0].detail["category"] == "modify_selection"


def test_missing_file_reads_empty(tmp_path: Path) -> None:
    assert _log(tmp_path).all() == []


def test_corrupt_file_reads_empty(tmp_path: Path) -> None:
    path = tmp_path / "activity.json"
    path.write_text("not json", encoding="utf-8")
    assert ActivityLog(path).all() == []


def test_bounding_trims_head(tmp_path: Path) -> None:
    log = ActivityLog(tmp_path / "activity.json", max_entries=3)
    for i in range(5):
        log.append(
            ActivityEntry.now(
                kind="tool_call_completed",
                agent_id=f"a{i}",
                harness="native",
                summary=f"step {i}",
            )
        )
    entries = log.all()
    assert len(entries) == 3
    assert [e.agent_id for e in entries] == ["a2", "a3", "a4"]


def test_summary_is_redacted(tmp_path: Path) -> None:
    log = _log(tmp_path)
    secret = "sk-ABCDEF0123456789ABCDEF0123456789ABCDEF01"
    log.append(
        ActivityEntry.now(
            kind="warning",
            agent_id="x",
            harness="native",
            summary=f"token {secret} used",
        )
    )
    stored = log.all()[0].summary
    assert secret not in stored


def test_recent_returns_tail(tmp_path: Path) -> None:
    log = _log(tmp_path)
    for i in range(10):
        log.append(ActivityEntry.now(kind="x", agent_id=f"a{i}", harness="native", summary=str(i)))
    recent = log.recent(3)
    assert [e.agent_id for e in recent] == ["a7", "a8", "a9"]
    assert log.recent(0) == []


def test_last_undoable_finds_most_recent_change(tmp_path: Path) -> None:
    log = _log(tmp_path)
    log.append(
        ActivityEntry.now(
            kind="patch_applied",
            agent_id="a",
            harness="native",
            summary="applied",
            undo_label="Rewrite selection",
        )
    )
    log.append(
        ActivityEntry.now(
            kind="tool_call_completed", agent_id="b", harness="native", summary="read"
        )
    )
    last = log.last_undoable()
    assert last is not None
    assert last.undo_label == "Rewrite selection"


def test_last_undoable_none_when_no_changes(tmp_path: Path) -> None:
    log = _log(tmp_path)
    log.append(ActivityEntry.now(kind="warning", agent_id="a", harness="native", summary="hi"))
    assert log.last_undoable() is None
