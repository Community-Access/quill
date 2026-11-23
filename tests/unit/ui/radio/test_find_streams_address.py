"""The Website address box remembers sites that found a live stream.

Nothing is spoken when it changes, the list is never refilled under an open
dropdown, and arrowing through the closed box never starts a scan.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.radio.history import RadioHistory
from quill.core.radio.link_finder import PageScanResult, PageStreamCandidate
from quill.ui.radio.link_finder_dialog import LinkFinderDialog

wx = pytest.importorskip("wx")


class _Tasks:
    def __init__(self) -> None:
        self.pending: list[dict[str, Any]] = []

    def submit(self, name: str, func: Any, **kwargs: Any) -> None:
        self.pending.append({"func": func, **kwargs})


@pytest.fixture
def d(wx_session_app: Any, wx_call_after: Any) -> Any:
    wx_call_after()
    frame = wx.Frame(None)
    said: list[str] = []
    saves: list[tuple[str, ...]] = []
    history = RadioHistory()
    history.recent_websites = ("https://old.example/",)
    host = SimpleNamespace(
        frame=frame,
        _radio_controller=SimpleNamespace(play_station=lambda s: None, stop=lambda: None),
        _task_manager=None,
        _safe_mode=False,
        _announce=lambda text, **_k: said.append(text),
        _radio_history=history,
        _save_radio_history=lambda: saves.append(history.recent_websites),
    )
    dlg = LinkFinderDialog(host)
    dlg._task_manager = _Tasks()
    yield SimpleNamespace(dlg=dlg, said=said, saves=saves, history=history)
    dlg._still_timer.Stop()
    dlg.dialog.Destroy()
    frame.Destroy()


def _scan(d: Any, url: str, *checks: str) -> None:
    d.dlg._url_ctrl.ChangeValue(url)
    d.dlg._on_scan(None)
    rows = [
        PageStreamCandidate(f"https://s.example/{n}", "audio tag", check=c)
        for n, c in enumerate(checks)
    ]
    d.dlg._task_manager.pending.pop()["on_success"](
        None, PageScanResult("T", "", rows, checked=True)
    )


def _rows(d: Any) -> list[str]:
    box = d.dlg._url_ctrl
    return [box.GetString(i) for i in range(box.GetCount())]


def test_the_box_offers_the_remembered_sites(d: Any) -> None:
    assert isinstance(d.dlg._url_ctrl, wx.ComboBox)
    assert _rows(d) == ["https://old.example/"]


def test_a_site_with_a_live_stream_is_remembered_first(d: Any) -> None:
    _scan(d, "kxyz.example", "live", "not checked")
    assert _rows(d) == ["https://kxyz.example", "https://old.example/"]
    assert d.history.recent_websites == ("https://kxyz.example", "https://old.example/")
    assert d.saves == [d.history.recent_websites]
    assert d.dlg._url_ctrl.GetValue() == "kxyz.example"  # what was typed stays
    assert not any("remember" in s.lower() for s in d.said)  # nothing extra is said


def test_a_site_with_no_live_stream_is_not_remembered(d: Any) -> None:
    _scan(d, "dead.example", "not checked", "file")
    assert _rows(d) == ["https://old.example/"]
    assert d.saves == []


def test_an_address_with_a_query_is_never_remembered(d: Any) -> None:
    _scan(d, "https://kxyz.example/player?session=secret", "live")
    assert _rows(d) == ["https://old.example/"]


def test_the_list_never_changes_while_it_is_dropped_down(d: Any) -> None:
    d.dlg._address._on_dropdown(SimpleNamespace(Skip=lambda: None))
    _scan(d, "kxyz.example", "live")
    assert _rows(d) == ["https://old.example/"]
    d.dlg._address._on_closeup(SimpleNamespace(Skip=lambda: None))
    assert _rows(d) == ["https://kxyz.example", "https://old.example/"]


def test_choosing_a_row_never_starts_a_scan(d: Any) -> None:
    event = wx.CommandEvent(wx.wxEVT_COMBOBOX, d.dlg._url_ctrl.GetId())
    event.SetEventObject(d.dlg._url_ctrl)
    d.dlg._url_ctrl.GetEventHandler().ProcessEvent(event)
    assert d.dlg._task_manager.pending == []
