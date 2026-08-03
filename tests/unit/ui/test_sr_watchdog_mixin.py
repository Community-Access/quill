"""Screen-reader death: flush first, then explain (16-assessment.md item 10)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import quill.core.autosave as autosave_module
from quill.ui.main_frame_sr_watchdog import SrWatchdogMixin


class _Frame(SrWatchdogMixin):
    def __init__(self) -> None:
        self.session_id = "session-1"
        self.editor = SimpleNamespace(GetValue=lambda: "latest text")
        self.document = _Doc("stale text")
        self._document_tabs = [
            SimpleNamespace(document=self.document),
            SimpleNamespace(document=_Doc("other tab")),
        ]
        self.announced: list[str] = []
        self.notifications: list[tuple[str, str]] = []

    def _announce(self, message: str) -> None:
        self.announced.append(message)

    def _record_notification(self, message: str, category: str = "info") -> None:
        self.notifications.append((message, category))


class _Doc:
    def __init__(self, text: str) -> None:
        self.text = text

    def set_text(self, value: str) -> None:
        self.text = value


def test_death_flushes_every_tab_then_announces(monkeypatch: pytest.MonkeyPatch) -> None:
    saved: list[str] = []
    monkeypatch.setattr(
        autosave_module,
        "autosave_document",
        lambda document, session_id, max_snapshots=10: saved.append(document.text),
    )
    frame = _Frame()

    frame._on_screen_reader_died("JAWS")  # noqa: SLF001

    # The active editor's very latest keystrokes were synced before snapshotting.
    assert saved == ["latest text", "other tab"]
    assert len(frame.announced) == 1
    message = frame.announced[0]
    assert "JAWS appears to have stopped" in message
    assert "2 documents" in message
    assert "keeps running" in message
    assert frame.notifications and frame.notifications[0][1] == "warning"


def test_one_failing_tab_does_not_stop_the_rest(monkeypatch: pytest.MonkeyPatch) -> None:
    saved: list[str] = []

    def flaky(document, session_id, max_snapshots=10):  # noqa: ANN001, ANN202
        if document.text == "latest text":
            raise OSError("disk full")
        saved.append(document.text)

    monkeypatch.setattr(autosave_module, "autosave_document", flaky)
    frame = _Frame()

    frame._on_screen_reader_died("")  # noqa: SLF001

    assert saved == ["other tab"]
    assert "1 document" in frame.announced[0]
    assert "Your screen reader appears to have stopped" in frame.announced[0]
