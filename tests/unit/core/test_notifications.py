from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.notifications import (
    add_notice,
    add_notification,
    clear_notifications,
    load_notifications,
    save_notifications,
    update_notice,
)


def test_add_notification_persists_entry(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    entries = add_notification("Update available", "update")
    assert len(entries) == 1
    assert entries[0].message == "Update available"
    assert entries[0].category == "update"


def test_notifications_round_trip_and_clear(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    add_notification("One")
    add_notification("Two")
    loaded = load_notifications()
    assert [entry.message for entry in loaded] == ["One", "Two"]
    save_notifications(loaded, limit=1)
    trimmed = load_notifications()
    assert [entry.message for entry in trimmed] == ["Two"]
    clear_notifications()
    assert load_notifications() == []


def test_update_notice_keeps_its_identity_and_timestamp(tmp_path: Path) -> None:
    path = tmp_path / "notifications.json"
    notice = add_notice(
        app="QUILL",
        title="Transcription queued",
        body="Waiting",
        category="progress",
        path=path,
    )[0]

    assert update_notice(
        notice.id,
        title="Transcription complete",
        body="Ready to open",
        target="dictation-transcript:0123456789abcdef0123456789abcdef",
        category="success",
        path=path,
    )
    updated = load_notifications(path=path)[0]
    assert updated.id == notice.id
    assert updated.timestamp == notice.timestamp
    assert updated.title == "Transcription complete"
    assert updated.body == "Ready to open"
    assert updated.message == "Transcription complete -- Ready to open"
    assert updated.target == "dictation-transcript:0123456789abcdef0123456789abcdef"
    assert updated.category == "success"


def test_update_notice_returns_false_after_the_notice_was_cleared(tmp_path: Path) -> None:
    path = tmp_path / "notifications.json"
    notice = add_notice(app="QUILL", title="Queued", path=path)[0]
    clear_notifications(path=path)

    assert not update_notice(notice.id, title="Complete", path=path)
