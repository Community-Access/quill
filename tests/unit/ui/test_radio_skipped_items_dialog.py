"""What Was Left Out: the named list behind "N files were left out" (2026-10-04)."""

from __future__ import annotations

import pytest

wx = pytest.importorskip("wx")

from quill.core.skipped_files import REASON_CLOUD_ONLY, REASON_IN_USE, SkippedFile  # noqa: E402
from quill.ui.radio import skipped_items_dialog as sid  # noqa: E402

_ROWS = [SkippedFile("a.mp3", REASON_CLOUD_ONLY), SkippedFile("b.mp3", REASON_IN_USE)]


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def test_the_report_text_names_each_row_and_what_to_do() -> None:
    text = sid.report_text("Backup saved. 2 files were left out.", _ROWS)
    assert f"a.mp3: {REASON_CLOUD_ONLY}" in text
    assert f"b.mp3: {REASON_IN_USE}" in text
    assert "Always keep on this device" in text


def test_the_window_lists_every_row(wx_app, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def _show(dialog, title, **_kw):  # type: ignore[no-untyped-def]
        listbox = next(c for c in dialog.GetChildren() if isinstance(c, wx.ListBox))
        seen["rows"] = [listbox.GetString(i) for i in range(listbox.GetCount())]
        seen["title"] = title
        return wx.ID_CANCEL

    monkeypatch.setattr(sid, "show_modal_dialog", _show)
    sid.show_skipped_items(None, "Two left out.", _ROWS)
    assert seen["title"] == sid.TITLE
    assert seen["rows"] == [f"a.mp3: {REASON_CLOUD_ONLY}", f"b.mp3: {REASON_IN_USE}"]


def test_no_opens_nothing_and_yes_opens_the_list(monkeypatch: pytest.MonkeyPatch) -> None:
    import quill.ui.dialog_contract as contract

    opened: list[str] = []
    monkeypatch.setattr(sid, "show_skipped_items", lambda *_a, **_k: opened.append("list"))
    monkeypatch.setattr(contract, "show_message_box", lambda *_a, **_k: wx.NO)
    sid.offer_skipped_list(None, "Saved.", _ROWS, caption="Back Up Quill Radio")
    assert opened == []
    monkeypatch.setattr(contract, "show_message_box", lambda *_a, **_k: wx.YES)
    sid.offer_skipped_list(None, "Saved.", _ROWS, caption="Back Up Quill Radio")
    assert opened == ["list"]
