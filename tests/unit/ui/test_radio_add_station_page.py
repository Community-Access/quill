"""Add Custom Station looks behind a pasted web page (#36).

A station's home page or its "Listen Live" player page is not a stream; handed
to the engine it failed with "source not supported". The dialog now asks the
host's resolver (the Find Streams scan, faked here) for the stream behind it,
puts that in the field, and only then does what the button was pressed for.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
import wx

from quill.core.radio.link_finder import PageStreamCandidate
from quill.ui.radio import add_custom_station
from quill.ui.radio.add_station_dialog import AddStationDialog

_FM_REDIRECT = "https://playerservices.streamtheworld.com/api/livestream-redirect/KKSEFM.mp3"


@pytest.fixture(scope="module", autouse=True)
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


class _StubController:
    def __init__(self) -> None:
        self.played: list[Any] = []

    def play_station(self, station: Any) -> None:
        self.played.append(station)


class _Resolver:
    """Answers immediately, the way the task manager answers on the UI thread."""

    def __init__(self, result: Any = None, error: BaseException | None = None) -> None:
        self.result, self.error = result, error
        self.asked: list[str] = []

    def __call__(self, url: str, done: Any) -> None:
        self.asked.append(url)
        done(self.result, self.error)


def _scan(*urls: str, title: str = "KKSEFM") -> SimpleNamespace:
    return SimpleNamespace(
        page_title=title, candidates=[PageStreamCandidate(u, "recorded") for u in urls]
    )


def _dialog(frame: wx.Frame, resolver: Any) -> tuple[AddStationDialog, _StubController, list]:
    said: list[str] = []
    controller = _StubController()
    dialog = AddStationDialog(
        frame, controller=controller, announce_cb=said.append, resolve_page_cb=resolver
    )
    return dialog, controller, said


def test_a_player_page_is_replaced_by_its_stream_and_then_tested() -> None:
    frame = wx.Frame(None)
    resolver = _Resolver(
        _scan(
            "https://16613.live.streamtheworld.com/KKSEFMAAC",
            "https://18373.live.streamtheworld.com/KKSEFM",
        )
    )
    dialog, controller, said = _dialog(frame, resolver)
    try:
        dialog._url_ctrl.ChangeValue("http://player.listenlive.co/20551")

        dialog._on_test(None)

        assert resolver.asked == ["http://player.listenlive.co/20551"]
        assert dialog._url_ctrl.GetValue() == _FM_REDIRECT
        assert dialog._homepage_ctrl.GetValue() == "http://player.listenlive.co/20551"
        assert dialog._name_ctrl.GetValue() == "KKSEFM"
        assert [s.stream_url for s in controller.played] == [_FM_REDIRECT]
        assert "Found the station's stream behind that web page." in said
    finally:
        dialog.dialog.Destroy()
        frame.Destroy()


def test_a_page_with_two_stations_names_them_and_plays_nothing() -> None:
    frame = wx.Frame(None)
    resolver = _Resolver(
        _scan(
            "https://18373.live.streamtheworld.com/KKSEFM",
            "https://16603.live.streamtheworld.com/KKSEAM",
        )
    )
    dialog, controller, said = _dialog(frame, resolver)
    try:
        dialog._name_ctrl.ChangeValue("Altitude")
        dialog._url_ctrl.ChangeValue("https://www.altitudesportsradio.com/")

        dialog._on_test(None)

        assert controller.played == []
        assert "KKSEFM, KKSEAM" in said[-1]
        assert dialog._url_ctrl.GetValue() == "https://www.altitudesportsradio.com/"
    finally:
        dialog.dialog.Destroy()
        frame.Destroy()


def test_nothing_found_says_so_once_then_uses_the_address_as_typed() -> None:
    frame = wx.Frame(None)
    resolver = _Resolver(_scan())
    dialog, controller, said = _dialog(frame, resolver)
    try:
        dialog._name_ctrl.ChangeValue("Somewhere")
        dialog._url_ctrl.ChangeValue("https://station.example.com/")

        dialog._on_test(None)
        assert controller.played == []
        assert "no stream was found" in said[-1]

        dialog._on_test(None)  # the second press: as typed, not asked again
        assert len(resolver.asked) == 1
        assert [s.stream_url for s in controller.played] == ["https://station.example.com/"]
    finally:
        dialog.dialog.Destroy()
        frame.Destroy()


def test_an_unreachable_page_never_reads_out_the_error_text() -> None:
    frame = wx.Frame(None)
    resolver = _Resolver(error=OSError("[Errno 11001] getaddrinfo failed"))
    dialog, controller, said = _dialog(frame, resolver)
    try:
        dialog._name_ctrl.ChangeValue("Somewhere")
        dialog._url_ctrl.ChangeValue("https://station.example.com/")

        dialog._on_test(None)

        assert controller.played == []
        assert said[-1].startswith("Could not reach that page")
        assert "getaddrinfo" not in said[-1]
    finally:
        dialog.dialog.Destroy()
        frame.Destroy()


def test_a_real_stream_address_is_never_sent_to_the_resolver() -> None:
    frame = wx.Frame(None)
    resolver = _Resolver(_scan())
    dialog, controller, _said = _dialog(frame, resolver)
    try:
        dialog._name_ctrl.ChangeValue("KKSE")
        dialog._url_ctrl.ChangeValue(_FM_REDIRECT)

        dialog._on_test(None)

        assert resolver.asked == []
        assert [s.stream_url for s in controller.played] == [_FM_REDIRECT]
    finally:
        dialog.dialog.Destroy()
        frame.Destroy()


def test_safe_mode_and_a_host_without_a_task_manager_get_no_resolver() -> None:
    assert add_custom_station.page_resolver(SimpleNamespace(_safe_mode=True)) is None
    assert add_custom_station.page_resolver(SimpleNamespace(_safe_mode=False)) is None


def test_the_resolver_runs_the_scan_on_the_task_manager(monkeypatch) -> None:
    import quill.core.radio.link_finder as lf

    submitted: list[str] = []

    class _Tasks:
        def submit(self, name: str, work: Any, *, on_success: Any, on_failure: Any) -> None:
            submitted.append(name)
            on_success(name, work())

    monkeypatch.setattr(lf, "scan_page_for_streams", lambda url: _scan(f"{url}#scanned"))
    resolve = add_custom_station.page_resolver(
        SimpleNamespace(_safe_mode=False, _task_manager=_Tasks())
    )
    got: list[Any] = []
    assert resolve is not None
    resolve("https://station.example.com/", lambda result, error: got.append((result, error)))

    assert submitted == ["radio-add-station-resolve"]
    assert got[0][0].candidates[0].url == "https://station.example.com/#scanned"
    assert got[0][1] is None
