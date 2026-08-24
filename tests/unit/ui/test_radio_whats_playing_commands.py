"""Copy What's Playing / Review and Copy always finish the job (#1282).

Reported: with a station playing, both commands "do nothing except return to
the main window"; with nothing playing they speak a sensible message. The cause
was that a *missing* track title was treated as "nothing is playing", and the
fallback was an asynchronous fetch whose failure path was silent.

These drive the wx-free command helpers against a stub host, so they assert the
behaviour a listener experiences without needing a window or a network.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio.models import RadioStation
from quill.ui.radio.now_playing_commands import (
    NO_TITLE_MESSAGE,
    NOTHING_PLAYING_MESSAGE,
    copy_whats_playing,
    show_whats_playing_details,
)


class _State:
    def __init__(self, station: RadioStation | None) -> None:
        self.station = station


class _Controller:
    def __init__(self, station: RadioStation | None) -> None:
        self.state = _State(station)


class _Host:
    """The slice of the radio host these commands touch."""

    def __init__(
        self,
        *,
        station: RadioStation | None,
        cached_title: str = "",
        fetched_title: str = "",
        copy_ok: bool = True,
    ) -> None:
        self._radio_controller = _Controller(station)
        self._cached = cached_title
        self._fetched = fetched_title
        self._copy_ok = copy_ok
        self.announcements: list[str] = []
        self.copied: list[str] = []
        self.dialogs: list[tuple[str, str]] = []
        self.transport_hosts: list[object] = []
        self.frame = object()

    # -- the host surface the commands use --------------------------------
    def _radio_now_playing_text(self) -> str:
        return self._cached

    def _radio_fetch_track_title(self, *, on_resolved=None, announce_result: bool = False) -> None:
        # Stands in for the off-thread ICY read: the answer lands, then the
        # waiting command runs. A stream with no title resolves to "".
        self._cached = self._fetched
        if on_resolved is not None:
            on_resolved()

    def _announce(self, message: str) -> None:
        self.announcements.append(message)

    def _copy_to_clipboard(self, text: str) -> bool:
        if not self._copy_ok:
            return False
        self.copied.append(text)
        return True

    def _show_modal_dialog(self, *_args: Any, **_kwargs: Any) -> int:
        return 0


def _station() -> RadioStation:
    return RadioStation(name="WQXR", stream_url="http://example.test/live")


def _install_fake_dialog(monkeypatch, host: _Host) -> None:
    class _FakeDialog:
        def __init__(
            self,
            _parent,
            text,
            _show,
            _copy,
            _announce,
            *,
            title="Now Playing",
            transport_host=None,
            windows=None,
        ):
            # transport_host carries the shared transport keyboard into this
            # window; the real dialog installs it, and the double records that
            # it was handed one at all.
            host.dialogs.append((title, text))
            host.transport_hosts.append(transport_host)

        def show(self) -> None:
            pass

    monkeypatch.setattr("quill.ui.radio.now_playing_dialog.NowPlayingDialog", _FakeDialog)


# -- Copy What's Playing -------------------------------------------------------


def test_copy_uses_the_cached_title_when_there_is_one() -> None:
    host = _Host(station=_station(), cached_title="YOUR SONG by Elton John")

    copy_whats_playing(host)

    assert host.copied == ["YOUR SONG by Elton John"]
    assert any("Copied" in message for message in host.announcements)


def test_copy_fetches_the_title_first_instead_of_claiming_nothing_is_playing() -> None:
    # The reported case: a station is playing but no title has been read yet.
    host = _Host(station=_station(), cached_title="", fetched_title="A Song by A Band")

    copy_whats_playing(host)

    assert host.copied == ["A Song by A Band"]
    assert NOTHING_PLAYING_MESSAGE not in host.announcements


def test_copy_says_so_when_the_stream_carries_no_titles() -> None:
    host = _Host(station=_station(), cached_title="", fetched_title="")

    copy_whats_playing(host)

    assert host.copied == []
    assert NO_TITLE_MESSAGE in host.announcements


def test_copy_reports_a_clipboard_failure() -> None:
    host = _Host(station=_station(), cached_title="A Song", copy_ok=False)

    copy_whats_playing(host)

    assert any("Could not copy" in message for message in host.announcements)


def test_copy_with_nothing_playing_says_nothing_is_playing() -> None:
    host = _Host(station=None)

    copy_whats_playing(host)

    assert host.announcements == [NOTHING_PLAYING_MESSAGE]
    assert host.copied == []


# -- What's Playing - Review and Copy ------------------------------------------


def test_review_window_opens_with_the_track(monkeypatch) -> None:
    host = _Host(station=_station(), cached_title="A Song by A Band")
    _install_fake_dialog(monkeypatch, host)

    show_whats_playing_details(host)

    assert len(host.dialogs) == 1
    title, text = host.dialogs[0]
    assert "WQXR" in title
    assert text == "A Song by A Band"


def test_review_window_opens_after_fetching_a_missing_title(monkeypatch) -> None:
    # This is the exact reported failure: previously it silently degraded to a
    # speak-only path and no window ever appeared.
    host = _Host(station=_station(), cached_title="", fetched_title="A Song by A Band")
    _install_fake_dialog(monkeypatch, host)

    show_whats_playing_details(host)

    assert [text for _title, text in host.dialogs] == ["A Song by A Band"]


def test_review_window_still_opens_when_the_stream_has_no_titles(monkeypatch) -> None:
    # A listener who asked to review what is playing gets a window they can
    # arrow through, naming the station, rather than silence.
    host = _Host(station=_station(), cached_title="", fetched_title="")
    _install_fake_dialog(monkeypatch, host)

    show_whats_playing_details(host)

    assert len(host.dialogs) == 1
    _title, text = host.dialogs[0]
    assert "WQXR" in text
    assert NO_TITLE_MESSAGE in text


def test_review_with_nothing_playing_says_nothing_is_playing(monkeypatch) -> None:
    host = _Host(station=None)
    _install_fake_dialog(monkeypatch, host)

    show_whats_playing_details(host)

    assert host.dialogs == []
    assert host.announcements == [NOTHING_PLAYING_MESSAGE]
