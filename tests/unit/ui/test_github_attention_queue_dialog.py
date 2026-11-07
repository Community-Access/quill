"""Attention queue presentation and last-visit lifecycle."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from quill.core.github.attention_queue import GitHubAttentionQueue
from quill.core.github.explore import ExploreRow
from quill.core.github.fetch_results import GitHubFetchResult
from quill.ui import github_explore_dialog


class _Control:
    def __init__(self) -> None:
        self.value = ""
        self.items: list[str] = []
        self.enabled = True
        self.selection = -1

    def Set(self, values: list[str]) -> None:
        self.items = values

    def SetValue(self, value: str) -> None:
        self.value = value

    def SetLabel(self, value: str) -> None:
        self.value = value

    def Enable(self, value: bool) -> None:
        self.enabled = value

    def SetSelection(self, value: int) -> None:
        self.selection = value


def _dialog(monkeypatch) -> github_explore_dialog.GitHubExploreDialog:
    dialog = object.__new__(github_explore_dialog.GitHubExploreDialog)
    dialog._load_token = 1
    dialog.dialog = object()
    dialog._view_key = lambda: "attention"
    dialog._attention_state = None
    dialog._selected_keys = {}
    dialog._include_snoozed = False
    dialog._list = _Control()
    dialog._detail = _Control()
    dialog._open_btn = _Control()
    dialog._use_btn = _Control()
    dialog._queue_options_btn = _Control()
    dialog._status = _Control()
    dialog._announce = lambda _message: None
    dialog._select = lambda _event: None
    monkeypatch.setattr(github_explore_dialog, "dialog_alive", lambda _dialog: True)
    return dialog


def test_partial_queue_load_hides_local_snoozes_and_keeps_previous_visit(
    monkeypatch, tmp_path
) -> None:
    state = GitHubAttentionQueue.load("alice", tmp_path / "queue.json")
    previous_visit = datetime(2026, 11, 5, tzinfo=UTC)
    state.mark_visited(previous_visit)
    snoozed = ExploreRow(
        "Snoozed", "Details", "https://github.com/o/r/issues/1", "o/r", "issue", "1"
    )
    changed = ExploreRow(
        "Changed",
        "Details",
        "https://github.com/o/r/issues/2",
        "o/r",
        "issue",
        "2",
        "2026-11-06T00:00:00+00:00",
    )
    state.snooze(snoozed.url, datetime.now(UTC) + timedelta(days=1))
    dialog = _dialog(monkeypatch)

    dialog._loaded(
        1,
        GitHubFetchResult((snoozed, changed), complete=False, warning="one source failed"),
        "",
        state,
        "attention",
    )

    assert [row.url for row in dialog._rows] == [changed.url]
    assert "Changed since your last visit" in dialog._rows[0].detail
    assert "incomplete" in dialog._status.value
    assert state.last_visit_at == previous_visit.isoformat(timespec="seconds")


def test_complete_queue_load_advances_last_visit(monkeypatch, tmp_path) -> None:
    state = GitHubAttentionQueue.load("alice", tmp_path / "queue.json")
    previous_visit = datetime(2026, 11, 5, tzinfo=UTC)
    state.mark_visited(previous_visit)
    dialog = _dialog(monkeypatch)

    dialog._loaded(
        1,
        GitHubFetchResult((ExploreRow("Issue", "Details", "https://github.com/o/r/issues/2"),)),
        "",
        state,
        "attention",
    )

    assert state.last_visit_at != previous_visit.isoformat(timespec="seconds")
    assert "changed since your last visit" in dialog._status.value
