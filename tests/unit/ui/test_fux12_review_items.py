"""FUX-12: Beacon's sync conflicts and Studio's AI titles show what they replace.

A Beacon conflict shows both versions, and their differences, before Use
Local / Use Remote / Use Merged. Studio's proposed chapter titles open in the
shared review, one check box for each title it would change, and only the
checked titles go into the list.
"""

from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip("wx")

import wx  # noqa: E402

from quill.core.ai.diff_review import build_item_review  # noqa: E402
from quill.core.github import review_preferences  # noqa: E402


@pytest.fixture
def frame(wx_session_app, tmp_path, monkeypatch):
    monkeypatch.setattr(review_preferences, "app_data_dir", lambda: tmp_path)
    made = wx.Frame(None)
    yield made
    made.Destroy()


# -- the item review --------------------------------------------------------------


def test_each_changed_item_is_its_own_change_even_side_by_side() -> None:
    review = build_item_review(
        ["Track 01", "Track 02", "Track 03"], ["Opening", "Track 02", "The Storm"], unit="chapter"
    )
    assert [h.describe() for h in review.hunks] == [
        'Chapter 1: "Track 01" becomes "Opening".',
        'Chapter 3: "Track 03" becomes "The Storm".',
    ]
    assert review.apply({1}) == "Track 01\nTrack 02\nThe Storm"
    assert review.apply(set()) == review.original
    assert review.summary() == "2 chapters would change."
    assert review.hunks[0].detail_lines() == ['Chapter 1: "Track 01" becomes "Opening".']


def test_lists_of_different_lengths_are_refused() -> None:
    with pytest.raises(ValueError):
        build_item_review(["a"], ["a", "b"])


# -- Studio -------------------------------------------------------------------------


def test_only_the_checked_titles_are_taken(frame, monkeypatch) -> None:
    from quill.ui.audio_studio.chapter_title_review import review_titles

    seen: dict[str, Any] = {}

    def show(self: Any) -> None:
        seen["rows"] = [self.hunk_list.GetString(i) for i in range(self.hunk_list.GetCount())]
        self.hunk_list.Check(0, False)  # keep "Track 01"
        self._on_apply_clicked(None)
        self.dialog.Destroy()

    monkeypatch.setattr("quill.ui.ai_diff_review_dialog.DiffReviewDialog.show_modal", show)
    said: list[str] = []
    titles = review_titles(
        frame, ["Track 01", "Track 02"], ["Opening", "  "], said.append
    )  # a blank proposal keeps the title
    assert seen["rows"] == ['Chapter 1: "Track 01" becomes "Opening".']
    assert titles is None  # the only change was unchecked: nothing taken


def test_taken_titles_come_back_in_chapter_order(frame, monkeypatch) -> None:
    from quill.ui.audio_studio.chapter_title_review import review_titles

    def show(self: Any) -> None:
        self.hunk_list.Check(0, False)
        self._on_apply_clicked(None)
        self.dialog.Destroy()

    monkeypatch.setattr("quill.ui.ai_diff_review_dialog.DiffReviewDialog.show_modal", show)
    said: list[str] = []
    titles = review_titles(frame, ["A", "B", "C"], ["X", "B", "Z"], said.append)
    assert titles == ["A", "B", "Z"]
    assert not any(m.startswith("Applied") for m in said)  # the Workbench says it


def test_rejecting_says_the_titles_are_unchanged(frame, monkeypatch) -> None:
    from quill.ui.audio_studio.chapter_title_review import review_titles

    def show(self: Any) -> None:
        self._on_reject_clicked(None)
        self.dialog.Destroy()

    monkeypatch.setattr("quill.ui.ai_diff_review_dialog.DiffReviewDialog.show_modal", show)
    said: list[str] = []
    assert review_titles(frame, ["A", "B"], ["X", "Y"], said.append) is None
    assert said == ["Rejected all changes; the titles are unchanged"]


# -- Beacon -------------------------------------------------------------------------


def _conflict() -> dict[str, Any]:
    """A conflict as sync really writes it (three_way_note's own merge)."""
    from quill.core.sync.merge import three_way_note

    merged, found = three_way_note("milk\neggs", "milk\nbread", entity_id="b1")
    assert found is not None
    return {
        "id": "cf_0",
        "entity_id": "b1",
        "field": "note",
        "local": found.local,
        "remote": found.remote,
        "merged": merged,
        "message": found.message,
        "resolved": False,
    }


def test_a_conflict_reads_both_versions_and_their_difference(frame) -> None:
    from quill.apps.beacon.sync_conflicts import conflict_text

    text = conflict_text(_conflict())
    assert "Removed: eggs" in text and "Added: bread" in text
    assert "This device's version (Use Local):\nmilk\neggs" in text
    assert "The other device's version (Use Remote):\nmilk\nbread" in text
    assert "Kept, marked as removed on this device: eggs" in text
    assert "<<<<<<" not in text


class _Controller:
    def __init__(self) -> None:
        self.conflicts = [_conflict(), dict(_conflict(), id="cf_1", entity_id="b2")]

    def history(self) -> list[dict]:
        return []

    def list_backups(self) -> list[dict]:
        return []

    def list_conflicts(self, *, resolved: bool = False) -> list[dict]:
        return [c for c in self.conflicts if c["resolved"] == resolved]

    def resolve_conflict(self, conflict_id: str, choice: str) -> dict:
        for c in self.conflicts:
            if c["id"] == conflict_id:
                c["resolved"] = True
        return {"ok": True}


def test_sync_history_shows_the_selected_conflict(frame, monkeypatch) -> None:
    from quill.apps.beacon import dialogs

    monkeypatch.setattr(dialogs, "show_message_box", lambda *a, **k: wx.OK)
    dialog = dialogs.SyncHistoryDialog(frame, _Controller())
    try:
        assert dialog.conflict_list.GetSelection() == 0
        assert "The note of b1 was changed" in dialog.conflict_detail.GetValue()
        dialog.conflict_list.SetSelection(1)
        dialog._show_conflict()
        assert "The note of b2 was changed" in dialog.conflict_detail.GetValue()
        dialog._resolve("local")  # resolves b2; b1 is left and shown
        assert "The note of b1 was changed" in dialog.conflict_detail.GetValue()
        assert dialog.r_local.IsEnabled()
        dialog._resolve("local")  # the last one
        assert dialog.conflict_detail.GetValue() == "No conflicts need review."
        assert not dialog.r_local.IsEnabled() and not dialog.r_merged.IsEnabled()
    finally:
        dialog.Destroy()


def test_one_proposed_title_is_told_accept_and_reject(frame, monkeypatch) -> None:
    from quill.ui.audio_studio.chapter_title_review import review_titles

    seen: dict[str, str] = {}

    def show(self: Any) -> None:
        seen["intro"] = self.dialog.GetChildren()[0].GetChildren()[0].GetLabel()
        seen["button"] = self.apply_button.GetLabel()
        self._on_accept_all_clicked(None)
        self.dialog.Destroy()

    monkeypatch.setattr("quill.ui.ai_diff_review_dialog.DiffReviewDialog.show_modal", show)
    assert review_titles(frame, ["A", "B"], ["A", "Y"], lambda _m: None) == ["A", "Y"]
    assert seen["button"] == "Accept"
    assert "Accept puts it in the chapter list" in seen["intro"]
    assert "uncheck" not in seen["intro"]
