"""Clear Recent Searches... and the rest of the review of #2008 (S-1, N-1).

The command clears the station searches and the websites Radio remembers,
after one question naming only the lists that have entries, with No as the
default; with nothing to clear it says so; an open Find Stations box is
emptied and keeps its text.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.radio.history import RadioHistory
from quill.core.radio.link_finder import PageScanResult, PageStreamCandidate
from quill.core.radio.search_history import SearchQuery
from quill.ui.radio import clear_recent

wx = pytest.importorskip("wx")


def _host(history: RadioHistory) -> Any:
    said: list[str] = []
    saved: list[int] = []
    return SimpleNamespace(
        _radio_history=history,
        _announce=lambda text, **_k: said.append(text),
        _save_radio_history=lambda: saved.append(1),
        said=said,
        saved=saved,
    )


def _history(searches: int, websites: int) -> RadioHistory:
    history = RadioHistory()
    history.recent_searches = tuple(SearchQuery(name=f"q{n}") for n in range(searches))
    history.recent_websites = tuple(f"https://s{n}.example/" for n in range(websites))
    return history


def test_the_question_names_only_the_lists_with_entries() -> None:
    assert clear_recent.confirm_text(15, 10) == (
        "Clear 15 recent station searches and 10 recent websites? "
        "No station or favorite is removed."
    )
    assert clear_recent.confirm_text(0, 1) == (
        "Clear 1 recent website? No station or favorite is removed."
    )
    assert clear_recent.confirm_text(1, 0) == (
        "Clear 1 recent station search? No station or favorite is removed."
    )


def test_yes_clears_both_and_says_so_once(monkeypatch: pytest.MonkeyPatch) -> None:
    asked: list[str] = []
    monkeypatch.setattr(
        clear_recent, "_confirm", lambda host, wx_, text: asked.append(text) or True
    )
    host = _host(_history(15, 10))
    clear_recent.clear_recent_searches(host)
    assert asked == [clear_recent.confirm_text(15, 10)]
    assert host._radio_history.recent_searches == ()
    assert host._radio_history.recent_websites == ()
    assert host.saved == [1]
    assert host.said == ["Cleared 15 recent searches and 10 recent websites."]


def test_no_keeps_everything(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(clear_recent, "_confirm", lambda *a: False)
    host = _host(_history(2, 1))
    clear_recent.clear_recent_searches(host)
    assert len(host._radio_history.recent_searches) == 2
    assert host.said == [] and host.saved == []


def test_nothing_to_clear_says_so_and_asks_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(clear_recent, "_confirm", lambda *a: pytest.fail("asked"))
    host = _host(_history(0, 0))
    clear_recent.clear_recent_searches(host)
    assert host.said == ["There are no recent searches or websites to clear."]


def test_the_question_defaults_to_no(monkeypatch: pytest.MonkeyPatch, wx_session_app: Any) -> None:
    made: list[tuple[str, str, int]] = []

    class _Dialog:
        def __init__(self, parent: Any, message: str, title: str, style: int) -> None:
            made.append((message, title, style))

        def Destroy(self) -> None:  # noqa: N802
            pass

    monkeypatch.setattr(wx, "MessageDialog", _Dialog)
    monkeypatch.setattr("quill.ui.dialog_contract.show_modal_dialog", lambda d, label: wx.ID_NO)
    assert clear_recent._confirm(SimpleNamespace(frame=None), wx, "Clear?") is False
    message, title, style = made[0]
    assert title == "Clear Recent Searches"
    assert style & wx.NO_DEFAULT and style & wx.YES_NO


def test_an_open_find_stations_box_is_emptied_and_keeps_its_text(
    monkeypatch: pytest.MonkeyPatch, wx_session_app: Any
) -> None:
    from quill.ui.radio.search_recents import RecentSearchesMixin

    frame = wx.Frame(None)
    try:
        box = wx.ComboBox(frame, choices=[])

        class _FindStations(RecentSearchesMixin):
            def __init__(self) -> None:
                self._name_ctrl = box
                self._recent_searches = (SearchQuery(name="jazz"),)

        dialog = _FindStations()
        dialog._fill_recent_searches()
        assert box.GetCount() == 1
        box.ChangeValue("bluegrass")
        monkeypatch.setattr(clear_recent, "_confirm", lambda *a: True)
        clear_recent.clear_recent_searches(_host(_history(1, 0)))
        assert box.GetCount() == 0
        assert box.GetValue() == "bluegrass"
    finally:
        frame.Destroy()


def test_the_menu_items(wx_session_app: Any) -> None:
    assert clear_recent.LABEL == "C&lear Recent Searches...\tCtrl+Alt+Shift+Backspace"
    assert clear_recent.QUILL_LABEL == "Clear Rece&nt Searches..."
    entry = wx.AcceleratorEntry()
    assert entry.FromString(clear_recent.LABEL)  # wx can bind the key


# -- the review of #2008: S-1 and N-1 ------------------------------------------------


def _dialog_host(history: RadioHistory) -> Any:
    frame = wx.Frame(None)
    return SimpleNamespace(
        frame=frame,
        _radio_controller=SimpleNamespace(play_station=lambda s: None, stop=lambda: None),
        _task_manager=None,
        _safe_mode=False,
        _announce=lambda *a, **k: None,
        _radio_history=history,
        _save_radio_history=lambda: None,
    )


def test_s1_the_list_is_refilled_before_the_site_is_remembered(
    monkeypatch: pytest.MonkeyPatch, wx_session_app: Any, wx_call_after: Any
) -> None:
    from quill.ui.radio.link_finder_dialog import LinkFinderDialog

    wx_call_after()
    host = _dialog_host(RadioHistory())
    dlg = LinkFinderDialog(host)
    try:
        order: list[str] = []
        real_refill, real_remember = dlg._refill, dlg._address.remember
        monkeypatch.setattr(
            dlg, "_refill", lambda *a, **k: (order.append("refill"), real_refill(*a, **k))
        )
        monkeypatch.setattr(
            dlg._address, "remember", lambda *a: (order.append("remember"), real_remember(*a))
        )
        rows = [PageStreamCandidate("https://s.example/live", "audio tag", check="live")]
        dlg._page_url = "https://s.example/"
        dlg._on_scan_done(PageScanResult("T", "", rows, checked=True), None)
        assert order == ["refill", "remember"]
    finally:
        dlg._still_timer.Stop()
        dlg.dialog.Destroy()
        host.frame.Destroy()


def test_n1_the_address_help_says_when_the_list_fills(wx_session_app: Any) -> None:
    from quill.ui.app_context_help import ensure_help_provider
    from quill.ui.radio.link_finder_dialog import LinkFinderDialog

    ensure_help_provider(wx)
    host = _dialog_host(RadioHistory())
    dlg = LinkFinderDialog(host)
    try:
        assert dlg._url_ctrl.GetHelpText().endswith(
            "The list is empty until a scan finds a live stream."
        )
    finally:
        dlg._still_timer.Stop()
        dlg.dialog.Destroy()
        host.frame.Destroy()
