"""FUX-12 in QUILL: compare change by change, then take only some of it.

Compare (with a file, or with a restore point) can now act on a difference:
Take Changes opens the shared review with the same two texts, and only the
checked differences go in. The ignore-whitespace choice compares again instead
of only flipping its box.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

pytest.importorskip("wx")

import wx  # noqa: E402

from quill.core.compare_service import (  # noqa: E402
    CompareOptions,
    CompareService,
    keep_trailing_whitespace,
)
from quill.core.github import review_preferences  # noqa: E402
from quill.core.restore_points import RestorePoint  # noqa: E402
from quill.ui import compare_take  # noqa: E402
from quill.ui.compare_dialog import TAKE_CHANGES, CompareDialog  # noqa: E402
from quill.ui.main_frame import MainFrame  # noqa: E402


@pytest.fixture
def parent(wx_session_app, tmp_path, monkeypatch):
    monkeypatch.setattr(review_preferences, "app_data_dir", lambda: tmp_path)
    frame = wx.Frame(None)
    yield frame
    frame.Destroy()


def _dialog(parent: Any, left: str, right: str, **kwargs: Any) -> CompareDialog:
    service = CompareService()
    service.compare(left, right, left_label="mine.txt", right_label="theirs.txt")
    return CompareDialog(parent, service, **kwargs)


# -- the service ---------------------------------------------------------------


def test_recompare_keeps_the_texts_and_applies_the_new_options() -> None:
    service = CompareService()
    service.compare("a  \nb\n", "a\nc\n", left_label="L", right_label="R")
    assert service.group_count == 1  # "a  " vs "a" and "b" vs "c" are one run
    service.recompare(CompareOptions(ignore_trailing_whitespace=True))
    assert service.group_count == 1
    assert service.groups[0].left_text == ["b"]
    assert service.left_label == "L" and service.right_text == "a\nc\n"


def test_select_moves_the_cursor_and_refuses_out_of_range() -> None:
    service = CompareService()
    service.compare("a\nb\nc\nd\n", "A\nb\nC\nd\n")
    assert service.select(1) is service.groups[1]
    assert service.current() is service.groups[1]
    assert service.select(5) is None
    assert service.current() is service.groups[1]


# -- the window ---------------------------------------------------------------


def test_ignore_whitespace_compares_again_and_says_the_count(parent, wx_call_after) -> None:
    wx_call_after()
    said: list[str] = []
    dialog = _dialog(parent, "one  \ntwo\n", "one\ntwo\n", announce=said.append, can_take=True)
    try:
        assert dialog._diff_list.GetCount() == 1
        dialog._toggle_whitespace()  # Ctrl+Shift+F8
        assert dialog._ws_check.GetValue() is True
        assert dialog.ignores_trailing_whitespace is True
        assert dialog._diff_list.GetCount() == 0
        assert said == ["Trailing whitespace ignored: 0 differences."]
        assert dialog._detail.GetValue() == "No differences."
        dialog.take_changes()
        assert said[-1] == "No differences to take."
        dialog._ws_check.SetValue(False)
        dialog._recompare(from_box=True)  # the box says its own state
        assert dialog._diff_list.GetCount() == 1
        assert said[-1] == "1 difference."
        assert dialog._status_label.GetLabel() == "Trailing whitespace included: 1 difference."
    finally:
        dialog.dialog.Destroy()


def test_take_changes_closes_with_its_own_result(parent, wx_call_after, monkeypatch) -> None:
    wx_call_after()
    dialog = _dialog(parent, "a\nb\n", "a\nB\n", can_take=True)
    ended: list[int] = []
    monkeypatch.setattr(dialog.dialog, "EndModal", ended.append)
    try:
        assert dialog._btn_take.IsShown()
        dialog.take_changes()
        assert ended == [TAKE_CHANGES]
    finally:
        dialog.dialog.Destroy()


def test_take_changes_is_not_offered_when_the_caller_cannot_take(parent, wx_call_after) -> None:
    wx_call_after()
    dialog = _dialog(parent, "a\nb\n", "a\nB\n")
    try:
        assert not dialog._btn_take.IsShown()
    finally:
        dialog.dialog.Destroy()


# -- taking ----------------------------------------------------------------------


class _Frame:
    """The parts of MainFrame that take_changes reaches."""

    def __init__(self, parent: Any, text: str, *, read_only: bool = False) -> None:
        self.frame = parent
        self.editor = SimpleNamespace(GetValue=lambda: self.text)
        self.text = text
        self.read_only = read_only
        self.said: list[str] = []
        self.replaced: list[str] = []

    def _document_is_read_only(self) -> bool:
        return self.read_only

    def _refuse_edit_if_read_only(self) -> None:
        if self.read_only:
            raise PermissionError("read only")

    def _replace_document_text(self, text: str) -> None:
        self.replaced.append(text)

    def _announce(self, message: str) -> None:
        self.said.append(message)


def test_only_the_checked_differences_are_taken(parent, monkeypatch) -> None:
    host = _Frame(parent, "one\ntwo\nthree\n")
    seen: dict[str, Any] = {}

    def show(self: Any) -> None:
        seen["intro"] = self.dialog.GetChildren()[0].GetChildren()[0].GetLabel()
        seen["count"] = self.hunk_list.GetCount()
        self.hunk_list.Check(1, False)  # keep my "three"
        self._on_apply_clicked(None)
        self.dialog.Destroy()

    monkeypatch.setattr("quill.ui.ai_diff_review_dialog.DiffReviewDialog.show_modal", show)
    compare_take.take_changes(host, "one\ntwo\nthree\n", "one\nTWO\nthree\n4\n", "b.txt")
    assert seen["count"] == 2
    assert seen["intro"].startswith("Each way b.txt differs from your document")
    assert host.replaced == ["one\nTWO\nthree\n"]


def test_nothing_is_taken_when_the_document_changed(parent, monkeypatch) -> None:
    host = _Frame(parent, "edited since\n")
    monkeypatch.setattr(
        "quill.ui.ai_diff_review_dialog.DiffReviewDialog.show_modal",
        lambda self: pytest.fail("the review must not open"),
    )
    compare_take.take_changes(host, "one\n", "two\n", "b.txt")
    assert host.replaced == []
    assert host.said == ["The document changed since the compare, so nothing was taken."]


def test_a_read_only_document_takes_nothing(parent) -> None:
    host = _Frame(parent, "one\n", read_only=True)
    assert compare_take.can_take(host) is False
    with pytest.raises(PermissionError):
        compare_take.take_changes(host, "one\n", "two\n", "b.txt")
    assert host.replaced == []


# -- the entry points ---------------------------------------------------------------


def _main_frame(parent: Any, text: str) -> Any:
    frame = MainFrame.__new__(MainFrame)
    frame.frame = parent
    frame._wx = wx
    frame.editor = SimpleNamespace(GetValue=lambda: text)
    frame.document = SimpleNamespace(name="mine.txt", path=Path("mine.txt"))
    frame._announce = lambda _m: None
    frame._set_status = lambda _m: None
    frame._document_is_read_only = lambda: False
    return frame


def test_compare_hands_take_changes_the_two_texts_it_compared(parent, wx_call_after) -> None:
    posted: list[tuple[Any, tuple[Any, ...], dict[str, Any]]] = []
    wx_call_after(lambda fn, *a, **k: posted.append((fn, a, k)))
    frame = _main_frame(parent, "a\nb\n")
    frame._show_modal_dialog = lambda dialog, _title: TAKE_CHANGES
    frame._run_compare_dialog("a\nb\n", "a\nB\n", left_label="mine.txt", right_label="b.txt")
    # Posted, not called: the closed window's editor focus must settle first.
    takes = [(a, k) for fn, a, k in posted if fn == frame._take_compare_changes]
    assert takes == [(("a\nb\n", "a\nB\n", "b.txt", False), {})]


def test_restore_previous_version_compares_the_chosen_version(
    parent, monkeypatch, wx_call_after
) -> None:
    wx_call_after()
    frame = _main_frame(parent, "now\n")
    point = RestorePoint(
        content_hash="h1",
        saved_at=datetime.now(UTC).isoformat(),
        word_count=1,
        size_bytes=4,
        source="save",
    )
    monkeypatch.setattr(
        "quill.ui.main_frame_restore_points.list_restore_points", lambda _path: [point]
    )
    monkeypatch.setattr(
        "quill.ui.main_frame_restore_points.read_restore_point", lambda _path, _h: "then\n"
    )

    def press_compare(dialog: Any, _title: str) -> int:
        buttons = [c for c in dialog.GetChildren() if isinstance(c, wx.Button)]
        compare = next(b for b in buttons if b.GetLabel() == "Co&mpare...")
        return compare.GetId()

    frame._show_modal_dialog = press_compare
    compared: list[tuple[str, str, str]] = []
    frame._run_compare_dialog = lambda left, right, *, left_label, right_label: compared.append((
        left,
        right,
        right_label,
    ))
    frame.restore_previous_version()
    assert compared == [("now\n", "then\n", compared[0][2])]
    assert compared[0][2].startswith("the version from Today at ")


def test_ignored_trailing_whitespace_is_not_taken_either(parent, monkeypatch) -> None:
    assert keep_trailing_whitespace("a  \nb\n", "a\nB\n") == "a  \nB\n"
    host = _Frame(parent, "one  \ntwo\n")
    seen: list[str] = []

    def show(self: Any) -> None:
        seen.extend(h.describe() for h in self.review.hunks)
        self._on_accept_all_clicked(None)
        self.dialog.Destroy()

    monkeypatch.setattr("quill.ui.ai_diff_review_dialog.DiffReviewDialog.show_modal", show)
    compare_take.take_changes(
        host, "one  \ntwo\n", "one\nTWO\n", "b.txt", ignore_trailing_whitespace=True
    )
    assert len(seen) == 1
    assert host.replaced == ["one  \nTWO\n"]


def test_nothing_left_after_ignoring_whitespace_opens_nothing(parent, monkeypatch) -> None:
    host = _Frame(parent, "one  \n")
    monkeypatch.setattr(
        "quill.ui.ai_diff_review_dialog.DiffReviewDialog.show_modal",
        lambda self: pytest.fail("the review must not open"),
    )
    compare_take.take_changes(host, "one  \n", "one\n", "b.txt", ignore_trailing_whitespace=True)
    assert host.said == ["No differences to take."]


def test_a_single_change_is_told_its_accept_and_reject_buttons() -> None:
    single = compare_take.take_intro("b.txt", single=True)
    assert "Accept" in single and "Apply Checked" not in single
    assert "Apply Checked" in compare_take.take_intro("b.txt")
