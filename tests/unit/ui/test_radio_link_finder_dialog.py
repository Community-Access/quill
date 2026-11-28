"""Find Streams from a Website: the checked list, said once and kept still.

The accessibility review of the live check (2026-11-21) asked for: Scan never
disabled (a press during a scan is answered), every outcome spoken once, the
rows and what Test and Use act on being one list in one order, a distinct
sentence when every link proved not to be audio, and a "still scanning" notice
that can never fire once the scan is over.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.radio.link_finder import PageScanResult, PageStreamCandidate
from quill.ui.radio.link_finder_dialog import STILL_SCANNING, LinkFinderDialog


@pytest.fixture(autouse=True)
def _last_results_in_tmp(tmp_path, monkeypatch):
    """Find Streams saves its last results on close: keep them out of the real profile."""
    monkeypatch.setattr("quill.ui.radio.find_streams_last._directory", lambda: tmp_path)


class _Tasks:
    """Holds the scan until the test delivers it, like a slow network."""

    def __init__(self) -> None:
        self.pending: list[dict[str, Any]] = []

    def submit(self, name: str, func: Any, **kwargs: Any) -> None:
        self.pending.append({"func": func, **kwargs})


class _Controller:
    def __init__(self) -> None:
        self.played: list[Any] = []

    def play_station(self, station: Any) -> None:
        self.played.append(station)

    def stop(self) -> None:
        pass


@pytest.fixture
def dialog(wx_session_app: Any, wx_call_after: Any) -> Any:
    import wx

    wx_call_after()  # the result sentence follows the focus change, inline here
    frame = wx.Frame(None)
    said: list[str] = []
    used: list[Any] = []
    tasks = _Tasks()
    controller = _Controller()
    host = SimpleNamespace(
        frame=frame,
        _radio_controller=controller,
        _task_manager=None,
        _safe_mode=False,
        _announce=lambda text, **_k: said.append(text),
        _radio_open_add_custom=used.append,
    )
    dlg = LinkFinderDialog(host)
    # Bypass the lifetime wrapper: deliver straight to the dialog.
    dlg._task_manager = tasks
    yield SimpleNamespace(dlg=dlg, said=said, used=used, tasks=tasks, controller=controller)
    dlg._still_timer.Stop()
    dlg.dialog.Destroy()
    frame.Destroy()


def _scan(d: Any, url: str = "kxyz.example.org") -> None:
    d.dlg._url_ctrl.SetValue(url)
    d.dlg._on_scan(None)


def _deliver(d: Any, result: Any = None, error: BaseException | None = None) -> None:
    task = d.tasks.pending.pop()
    if error is not None:
        task["on_failure"](None, error)
    else:
        task["on_success"](None, result)


def _checked(*candidates: PageStreamCandidate, left_out: int = 0) -> PageScanResult:
    return PageScanResult("KXYZ", "", list(candidates), checked=True, left_out=left_out)


def _cand(url: str, check: str, **fields: Any) -> PageStreamCandidate:
    candidate = PageStreamCandidate(url=url, reason="audio tag", check=check)
    for name, value in fields.items():
        setattr(candidate, name, value)
    return candidate


def test_scan_stays_enabled_and_a_second_press_is_answered(dialog: Any) -> None:
    _scan(dialog)
    assert dialog.dlg._scan_btn.IsEnabled()
    assert dialog.said == []  # starting is shown, not said
    dialog.dlg._on_scan(None)
    assert dialog.said == [STILL_SCANNING]
    assert len(dialog.tasks.pending) == 1  # no second scan started


def test_the_scan_asks_for_the_live_check(dialog: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    asked: list[dict[str, Any]] = []
    from quill.core.radio import link_finder
    from quill.core.radio.link_finder import PageScanResult

    def fake_scan(url: str, **k: Any) -> PageScanResult:
        asked.append(k)
        return PageScanResult("", "", [], checked=True)

    monkeypatch.setattr(link_finder, "scan_page_for_streams", fake_scan)
    _scan(dialog)
    dialog.tasks.pending[0]["func"]()
    assert len(asked) == 1 and asked[0]["check_live"] is True and asked[0]["safe_mode"] is False
    assert callable(asked[0]["on_checked"])  # the window hears each name as it is checked


def test_the_result_is_said_once_and_rows_lead_with_the_verdict(dialog: Any) -> None:
    _scan(dialog)
    _deliver(
        dialog,
        _checked(
            _cand(
                "https://s.example/live", "live", stream_name="KXYZ", codec="MP3", bitrate_kbps=128
            ),
            _cand("https://s.example/slow", "not checked", check_note="it took too long to answer"),
            left_out=2,
        ),
    )
    assert dialog.said == ["Found 1 live stream and 1 link not checked."]
    assert "Left out 2 links" in dialog.dlg._status.GetLabel()
    results = dialog.dlg._results
    assert results.GetItemText(0, 0) == "Live: KXYZ, MP3, 128 kbps"
    assert results.GetItemText(0, 1) == "https://s.example/live"
    assert results.GetItemText(1, 0) == "Not checked: slow on s.example, it took too long to answer"


def test_the_sentence_names_the_scans_own_limit(dialog: Any) -> None:
    _scan(dialog)
    result = _checked(
        _cand("https://s.example/live", "live", stream_name="KXYZ"),
        _cand(
            "https://s.example/more",
            "not checked",
            check_note="there were too many links to check them all",
        ),
    )
    result.check_limit = 48
    _deliver(dialog, result)
    assert dialog.said == [
        "Found 1 live stream and 1 link not checked, because one scan checks at most 48 links."
    ]


def test_test_and_use_act_on_the_row_the_listener_chose(dialog: Any) -> None:
    # The scan sorted live first, which is not page order; the list and what
    # the buttons act on must be the same sorted list.
    _scan(dialog)
    _deliver(
        dialog,
        _checked(
            _cand("https://s.example/live", "live", stream_name="KXYZ Live", codec="AAC"),
            _cand("https://s.example/first-on-page", "not checked"),
        ),
    )
    dialog.dlg._results.Focus(1)
    dialog.dlg._on_use(None)
    assert dialog.used[-1].stream_url == "https://s.example/first-on-page"
    dialog.dlg._results.Focus(0)
    dialog.dlg._on_use(None)
    assert dialog.used[-1].stream_url == "https://s.example/live"
    assert dialog.used[-1].name == "KXYZ Live"
    assert dialog.used[-1].codec == "AAC"


def test_every_link_not_audio_has_its_own_spoken_result(dialog: Any) -> None:
    _scan(dialog)
    _deliver(dialog, _checked(left_out=3))
    assert dialog.said == ["Found 3 links on that page, but none of them were audio."]


def test_a_failure_is_spoken(dialog: Any) -> None:
    _scan(dialog)
    _deliver(dialog, error=RuntimeError("Could not reach that page"))
    assert len(dialog.said) == 1 and dialog.said[0].startswith("Could not scan that page")
    assert not dialog.dlg._scanning


def test_an_empty_address_is_spoken(dialog: Any) -> None:
    _scan(dialog, url="")
    assert dialog.said == ["Type a website address or a station name first."]


def test_the_still_scanning_notice_is_silent_once_the_scan_is_over(dialog: Any) -> None:
    _scan(dialog)
    assert dialog.dlg._still_timer.IsRunning()
    dialog.dlg._on_still_scanning(None)
    assert dialog.said == [STILL_SCANNING]
    _deliver(dialog, _checked(_cand("https://s.example/live", "live")))
    assert not dialog.dlg._still_timer.IsRunning()
    dialog.dlg._on_still_scanning(None)  # a tick queued behind the result
    assert dialog.said == [STILL_SCANNING, "Found 1 live stream."]


def test_a_press_during_the_scan_spends_the_timed_notice(dialog: Any) -> None:
    _scan(dialog)
    dialog.dlg._on_scan(None)  # the listener asks at, say, six seconds
    assert not dialog.dlg._still_timer.IsRunning()
    assert dialog.said == [STILL_SCANNING]


def test_a_none_result_is_said_without_saying_none(dialog: Any) -> None:
    _scan(dialog)
    _deliver(dialog, None)
    assert dialog.said == ["Could not scan that page."]


def test_focus_on_use_moves_to_the_list_before_use_is_disabled(
    dialog: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    import wx

    _scan(dialog)
    _deliver(dialog, _checked(_cand("https://s.example/old", "live")))
    moved: list[str] = []
    monkeypatch.setattr(wx.Window, "FindFocus", staticmethod(lambda: dialog.dlg._use_btn))
    monkeypatch.setattr(dialog.dlg._results, "SetFocus", lambda: moved.append("list"))
    _scan(dialog)
    _deliver(dialog, error=RuntimeError("boom"))
    assert moved == ["list"]
    assert not dialog.dlg._use_btn.IsEnabled()


def test_the_safe_mode_refusal_is_spoken(dialog: Any) -> None:
    dialog.dlg._safe_mode = True
    _scan(dialog)
    assert dialog.said == ["Finding stream links is disabled in Safe Mode."]
