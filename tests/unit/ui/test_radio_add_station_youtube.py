"""Add Custom Station recognizes a YouTube link (#1268).

The dialog stays network-free: it recognizes the link, takes the one-time
consent, and saves the tidy *page* URL. Resolving it to a stream happens later,
at play or record time, because YouTube's stream addresses expire.
"""

from __future__ import annotations

import pytest
import wx

from quill.ui.radio.add_station_dialog import AddStationDialog


@pytest.fixture(scope="module", autouse=True)
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


class _StubController:
    def __init__(self) -> None:
        self.played: list[object] = []

    def play_station(self, station: object) -> None:
        self.played.append(station)


def _dialog(frame: wx.Frame, *, consent: bool | None) -> AddStationDialog:
    consent_cb = None if consent is None else (lambda: consent)
    return AddStationDialog(
        frame,
        controller=_StubController(),
        youtube_consent_cb=consent_cb,
    )


def _fill(dialog: AddStationDialog, *, name: str, url: str) -> None:
    dialog._name_ctrl.ChangeValue(name)
    dialog._url_ctrl.ChangeValue(url)


def test_a_youtube_link_is_saved_as_its_canonical_page_url(wx_app) -> None:
    frame = wx.Frame(None)
    dialog = _dialog(frame, consent=True)
    try:
        _fill(
            dialog,
            name="NASA Live",
            url="https://youtu.be/dQw4w9WgXcQ?t=42&si=tracking",
        )

        station = dialog._build_station()

        assert station is not None
        # The durable link, without the playlist/timestamp/tracking noise.
        assert station.stream_url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert station.source == "YouTube"
    finally:
        dialog.dialog.Destroy()
        frame.Destroy()


def test_declining_the_consent_refuses_the_station(wx_app) -> None:
    frame = wx.Frame(None)
    dialog = _dialog(frame, consent=False)
    try:
        _fill(dialog, name="NASA Live", url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        assert dialog._build_station() is None
        assert "consent" in dialog._status.GetLabel().lower()
    finally:
        dialog.dialog.Destroy()
        frame.Destroy()


def test_without_a_consent_hook_a_youtube_link_is_refused_not_saved_raw(wx_app) -> None:
    # A host that never wired YouTube support must not end up with a station
    # whose "stream" is an HTML page.
    frame = wx.Frame(None)
    dialog = _dialog(frame, consent=None)
    try:
        _fill(dialog, name="NASA Live", url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        assert dialog._build_station() is None
    finally:
        dialog.dialog.Destroy()
        frame.Destroy()


def test_an_ordinary_stream_link_never_asks_for_youtube_consent(wx_app) -> None:
    frame = wx.Frame(None)
    asked: list[bool] = []

    def consent() -> bool:
        asked.append(True)
        return True

    dialog = AddStationDialog(frame, controller=_StubController(), youtube_consent_cb=consent)
    try:
        _fill(dialog, name="Normal", url="http://example.test/live.mp3")

        station = dialog._build_station()

        assert station is not None
        assert station.source == ""
        assert asked == []
    finally:
        dialog.dialog.Destroy()
        frame.Destroy()
