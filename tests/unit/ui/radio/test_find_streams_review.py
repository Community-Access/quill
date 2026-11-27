"""The accessibility review of #2007, item by item (B-1, S-1 to S-7, N-2, N-3).

The fixtures come from test_find_streams_dialog; pytest injects them by name.
"""

# ruff: noqa: F811

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.radio.link_finder import PageScanResult
from quill.ui.radio.link_finder_dialog import LinkFinderDialog
from tests.unit.ui.radio.test_find_streams_dialog import (  # noqa: F401 - fixtures
    _Controller,
    _rows,
    _scan,
    d,
    prompt,
)

wx = pytest.importorskip("wx")


def test_b1_a_failed_scan_is_said_after_focus_settles(d: Any) -> None:
    _scan(d, _rows())
    d.events.clear()
    d.dlg._url_ctrl.ChangeValue("https://gone.example/")
    d.dlg._on_scan(None)
    d.dlg._task_manager.pending.pop()["on_failure"](None, RuntimeError("boom"))
    assert d.events[:2] == ["after", "say:Could not scan that page."]
    assert d.dlg._status.GetLabel() == "Could not scan that page."


def test_b1_a_scan_with_no_rows_is_said_after_focus_settles(d: Any) -> None:
    d.dlg._url_ctrl.ChangeValue("https://a.example/")
    d.dlg._on_scan(None)
    result = PageScanResult("T", "", [], checked=True, left_out=2, not_public=1)
    d.events.clear()
    d.dlg._task_manager.pending.pop()["on_success"](None, result)
    assert d.events[0] == "after"
    assert d.said[-1].startswith("Found 3 links on that page: 2 were not audio, and 1 is on")


def test_s1_the_scans_left_out_status_stays_after_its_sentence(d: Any) -> None:
    d.dlg._url_ctrl.ChangeValue("https://a.example/")
    d.dlg._on_scan(None)
    result = PageScanResult("T", "", _rows(), checked=True, left_out=3, not_public=2)
    d.dlg._task_manager.pending.pop()["on_success"](None, result)
    assert d.dlg._status.GetLabel().endswith(
        "Left out 3 links that were not audio or no longer there, and 2 on your own network."
    )
    assert "Left out" not in d.said[-1]


def test_s1_other_sentences_go_in_the_status_line_too(d: Any) -> None:
    _scan(d, _rows())
    d.dlg._choose_order("name")
    assert d.dlg._status.GetLabel() == "Sorted by name, A to Z."


def test_s3_select_all_and_find_update_the_buttons_once(
    d: Any, monkeypatch: Any, prompt: Any
) -> None:
    _scan(d, _rows())
    runs: list[int] = []
    real = d.dlg._enable_row_buttons
    monkeypatch.setattr(d.dlg, "_enable_row_buttons", lambda: (runs.append(1), real()))
    d.dlg._select_all()
    assert len(runs) == 1
    assert d.dlg._add_btn.GetLabel() == "Add 4 to &Favorites"
    runs.clear()
    prompt.value = "mike"
    d.dlg._find()
    assert len(runs) == 1
    assert [c.url for c in d.dlg._list.selected_candidates()] == ["https://a.example/mike"]


def test_s3_find_deselects_only_the_selected_rows(d: Any, monkeypatch: Any) -> None:
    _scan(d, _rows())
    d.dlg._results.Select(1, True)  # rows 0 and 1 are selected
    calls: list[tuple[int, bool]] = []
    real = d.dlg._results.Select

    def select(row: int, on: bool = True) -> None:
        calls.append((row, on))
        real(row, on)

    monkeypatch.setattr(d.dlg._results, "Select", select)
    d.dlg._list.go_to(2)
    assert calls == [(0, False), (1, False), (2, True)]


def test_s4_a_refill_from_the_list_steps_off_it_first(d: Any, monkeypatch: Any) -> None:
    _scan(d, _rows())
    order: list[str] = []
    monkeypatch.setattr(wx.Window, "FindFocus", staticmethod(lambda: d.dlg._results))
    monkeypatch.setattr(d.dlg._sort_btn, "SetFocus", lambda: order.append("sort button"))
    monkeypatch.setattr(d.dlg.dialog, "Freeze", lambda: order.append("freeze"))
    monkeypatch.setattr(d.dlg.dialog, "Thaw", lambda: order.append("thaw"))
    monkeypatch.setattr(d.dlg._results, "SetFocus", lambda: order.append("focus list"))
    d.dlg._choose_order("bitrate")
    assert order == ["sort button", "freeze", "thaw", "focus list"]


def test_s5_scan_this_streams_server_waits_for_the_menu_to_close(
    d: Any, monkeypatch: Any, wx_call_after: Any
) -> None:
    queued: list[Any] = []
    wx_call_after(lambda fn, *a, **k: queued.append(fn))
    monkeypatch.setattr(d.dlg, "_scan_server", lambda: pytest.fail("ran inside the menu"))
    d.dlg._run("server")
    assert len(queued) == 1


def test_s6_enter_on_another_row_tests_that_row(d: Any) -> None:
    _scan(d, _rows())
    played = d.host._radio_controller.played
    d.dlg._results.Focus(0)
    d.dlg._on_test(None)
    d.dlg._results.Focus(1)
    d.dlg._on_test(None)  # Enter on another row
    assert [s.stream_url for s in played] == ["https://a.example/zulu", "https://a.example/alpha"]
    assert d.said[-1] == "Testing Alpha FM."
    d.dlg._on_test(None)  # Enter on the same row stops
    assert d.said[-1] == "Test stopped."
    d.dlg._on_test(None)
    d.dlg._results.Focus(2)
    d.dlg._on_test(None, from_button=True)  # the button stops, whatever the row
    assert d.said[-1] == "Test stopped."


def test_s7_the_list_help_teaches_its_keys(wx_session_app: Any) -> None:
    from quill.ui.app_context_help import ensure_help_provider

    ensure_help_provider(wx)
    frame = wx.Frame(None)
    host = SimpleNamespace(
        frame=frame,
        _radio_controller=_Controller(),
        _task_manager=None,
        _safe_mode=False,
        _announce=lambda *a, **k: None,
    )
    dlg = LinkFinderDialog(host)
    try:
        assert dlg._results.GetHelpText() == (
            "The stream links found on the page, live streams first. Enter tests the "
            "focused link, or plays several selected audio files in the order shown. "
            "Select several with Shift and the arrow keys, or press Ctrl+A "
            "for every row shown; to pick rows far apart, filter the list first, then "
            "press Ctrl+A. Add to Favorites, Save as Playlist (Ctrl+S) and Copy (Ctrl+C) "
            "then act on all of them. Ctrl+F finds a row, F3 and Shift+F3 find the next "
            "and previous, Ctrl+Shift+O plays a random stream from the rows shown, and the "
            "Applications key opens the list's menu."
        )
        # The keys show in the context menu only, never on the buttons.
        assert dlg._test_btn.GetLabel() == "&Test"
        assert dlg._save_btn.GetLabel() == "Save as Play&list..."
    finally:
        dlg._still_timer.Stop()
        dlg.dialog.Destroy()
        frame.Destroy()


def test_n2_the_listener_order_is_reset_when_it_cannot_apply(d: Any) -> None:
    rows = _rows()
    rows[0].listeners = 5
    _scan(d, rows)
    d.dlg._choose_order("listeners")
    _scan(d, _rows())
    assert d.dlg._state.order == "scan"


def test_n3_a_repeat_and_a_refused_filter_are_said_after(d: Any) -> None:
    _scan(d, _rows())
    d.events.clear()
    d.dlg._choose_order("scan")
    assert d.events == ["after", "say:Back in scan order."]
    d.events.clear()
    d.dlg._choose_filter(fmt="HLS")
    assert d.events == ["after", "say:No links are HLS streams, so the list is unchanged."]
