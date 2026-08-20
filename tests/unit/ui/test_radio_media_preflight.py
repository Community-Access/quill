"""A damaged installation says so once, and a healthy one says nothing.

The gap this closes: ``playback_engine`` defaults to ``"auto"``, and on "auto"
a missing ``libmpv-2.dll`` fell through to Windows Media in total silence. The
one spoken line about it was reachable only by somebody who had gone into
Preferences and named mpv explicitly. Everyone else got a radio that had
quietly lost seven capabilities, and a station that would not play with no
route to the reason.

Driven against a stand-in host, like ``live_reconnect``'s tests: the module
takes a host and touches nothing else, so a real frame would add a window and
prove nothing extra.
"""

from __future__ import annotations

import pytest

from quill.core.radio.media_health import MediaHealth
from quill.ui.radio import media_preflight


class _History:
    def __init__(self, signature: str = "") -> None:
        self.media_notice_signature = signature


class _Host:
    def __init__(self, signature: str = "") -> None:
        self._radio_history = _History(signature)
        self.said: list[str] = []
        self.saves = 0

    def _announce(self, message: str) -> None:
        self.said.append(message)

    def _save_radio_history(self) -> None:
        self.saves += 1


@pytest.fixture
def health(monkeypatch):
    """Pin what the machine 'has' so the test does not depend on this laptop."""

    def _set(*, ffmpeg: bool, mpv: bool) -> None:
        monkeypatch.setattr(
            media_preflight, "current_health", lambda: MediaHealth(ffmpeg=ffmpeg, mpv=mpv)
        )

    return _set


# -- the launch courtesy -------------------------------------------------------


def test_a_healthy_install_says_nothing_at_launch(health) -> None:
    health(ffmpeg=True, mpv=True)
    host = _Host()

    media_preflight.surface_media_health_startup(host)

    assert host.said == []


def test_a_missing_engine_is_named_once_with_what_it_cost(health) -> None:
    health(ffmpeg=True, mpv=False)
    host = _Host()

    media_preflight.surface_media_health_startup(host)

    assert len(host.said) == 1
    assert "mpv playback engine is missing" in host.said[0]
    assert "live pause and rewind" in host.said[0]
    # And a route out, not just bad news.
    assert "reinstalling restores it" in host.said[0]


def test_the_same_shortfall_is_not_announced_on_every_launch(health) -> None:
    health(ffmpeg=True, mpv=False)
    host = _Host()

    media_preflight.surface_media_health_startup(host)
    media_preflight.surface_media_health_startup(host)

    assert len(host.said) == 1
    assert host.saves == 1


def test_losing_a_second_tool_is_news_again(health) -> None:
    # The reason the mark is a signature rather than a "seen" flag.
    health(ffmpeg=True, mpv=False)
    host = _Host()
    media_preflight.surface_media_health_startup(host)

    health(ffmpeg=False, mpv=False)
    media_preflight.surface_media_health_startup(host)

    assert len(host.said) == 2
    assert "Two media tools are missing" in host.said[1]


def test_a_repair_clears_the_mark_so_a_later_loss_is_news(health) -> None:
    health(ffmpeg=True, mpv=False)
    host = _Host()
    media_preflight.surface_media_health_startup(host)

    health(ffmpeg=True, mpv=True)
    media_preflight.surface_media_health_startup(host)
    assert host._radio_history.media_notice_signature == ""

    health(ffmpeg=True, mpv=False)
    media_preflight.surface_media_health_startup(host)
    assert len(host.said) == 2


def test_a_broken_probe_does_not_break_a_launch(monkeypatch) -> None:
    # A courtesy that can take the app down is not a courtesy.
    def _boom() -> MediaHealth:
        raise RuntimeError("no registry today")

    monkeypatch.setattr(media_preflight, "current_health", _boom)
    host = _Host()

    media_preflight.surface_media_health_startup(host)

    assert host.said == []


def test_a_host_with_no_history_is_survivable(health) -> None:
    health(ffmpeg=True, mpv=False)

    class _Bare:
        said: list[str] = []

        def _announce(self, message: str) -> None:
            self.said.append(message)

    bare = _Bare()
    media_preflight.surface_media_health_startup(bare)

    assert len(bare.said) == 1


# -- the station that cannot play at all ---------------------------------------


def test_an_ogg_station_without_mpv_gets_the_real_reason(health) -> None:
    health(ffmpeg=True, mpv=False)

    message = media_preflight.refusal_for("SomaFM", "https://ice.somafm.com/groovesalad.ogg")

    assert "Ogg, Opus or HLS" in message
    assert message.startswith("SomaFM")


def test_an_ogg_station_with_mpv_present_keeps_the_ordinary_error(health) -> None:
    # mpv is here, so whatever went wrong was not this.
    health(ffmpeg=True, mpv=True)

    assert media_preflight.refusal_for("SomaFM", "https://ice.somafm.com/groovesalad.ogg") == ""


def test_an_mp3_station_is_never_blamed_on_the_missing_engine(health) -> None:
    # Sending somebody to reinstall because their station was off the air is
    # worse than the generic error it replaced.
    health(ffmpeg=True, mpv=False)

    assert media_preflight.refusal_for("WQXR", "https://stream.example/wqxr.mp3") == ""


def test_current_health_answers_rather_than_raising(monkeypatch) -> None:
    # Both probes touch the filesystem and one loads a DLL path; neither is
    # allowed to be the thing that fails.
    def _boom() -> bool:
        raise OSError("disk gone")

    monkeypatch.setattr("quill.core.speech.ffmpeg.ffmpeg_available", _boom)
    monkeypatch.setattr("quill.ui.radio.mpv_radio_engine.mpv_output_device_available", _boom)

    result = media_preflight.current_health()

    assert result == MediaHealth(ffmpeg=False, mpv=False)
