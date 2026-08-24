"""Saying it once, and remembering that you did (list.md 5.3).

The pure half is covered in ``tests/unit/core/podcasts/test_cast_media_health``.
This is the half with a machine and a listener in it: when the notice is
spoken, when it is *not* spoken, and where the "already said" mark lives.

The rule the whole design turns on is that a healthy install is silent. A
launch that reports all-is-well every time is a launch nobody can listen past,
and it teaches people to talk over the one launch that had something to say.
"""

from __future__ import annotations

from typing import Any

from quill.core.podcasts.media_health import CastMediaHealth
from quill.ui.podcasts import media_preflight


class _History:
    def __init__(self, signature: str = "") -> None:
        self.media_notice_signature = signature


class _Host:
    """Everything the preflight is allowed to ask for, and nothing else."""

    def __init__(self, signature: str = "") -> None:
        self._podcast_history = _History(signature)
        self.said: list[str] = []
        self.saves = 0

    def _announce(self, message: str) -> None:
        self.said.append(message)

    def _save_podcast_history(self) -> None:
        self.saves += 1


def _with_health(monkeypatch: Any, ffmpeg: bool) -> None:
    monkeypatch.setattr(media_preflight, "current_health", lambda: CastMediaHealth(ffmpeg=ffmpeg))


def test_a_healthy_install_is_silent(monkeypatch: Any) -> None:
    _with_health(monkeypatch, True)
    host = _Host()

    media_preflight.surface_media_health_startup(host)

    assert host.said == []


def test_a_missing_tool_is_named_once(monkeypatch: Any) -> None:
    _with_health(monkeypatch, False)
    host = _Host()

    media_preflight.surface_media_health_startup(host)

    assert len(host.said) == 1
    assert "FFmpeg is missing" in host.said[0]


def test_the_same_state_is_not_repeated_on_the_next_launch(monkeypatch: Any) -> None:
    """Told once is a courtesy; told every launch is noise somebody learns to
    talk over -- and then misses the launch that mattered."""
    _with_health(monkeypatch, False)
    host = _Host()

    media_preflight.surface_media_health_startup(host)
    media_preflight.surface_media_health_startup(host)

    assert len(host.said) == 1


def test_a_repair_clears_the_mark_so_a_later_loss_is_news_again(monkeypatch: Any) -> None:
    """Why the mark is a signature and not a "we told them" flag."""
    host = _Host()
    _with_health(monkeypatch, False)
    media_preflight.surface_media_health_startup(host)

    _with_health(monkeypatch, True)
    media_preflight.surface_media_health_startup(host)
    assert host._podcast_history.media_notice_signature == ""

    _with_health(monkeypatch, False)
    media_preflight.surface_media_health_startup(host)

    assert len(host.said) == 2


def test_the_mark_is_written_through_the_hosts_own_saver(monkeypatch: Any) -> None:
    """The history file is one the rest of the app is holding too, and two
    writers is how a setting disappears."""
    _with_health(monkeypatch, False)
    host = _Host()

    media_preflight.surface_media_health_startup(host)

    assert host.saves == 1
    assert host._podcast_history.media_notice_signature == "ffmpeg=0"


def test_a_host_that_cannot_remember_still_gets_told(monkeypatch: Any) -> None:
    """A courtesy must degrade to being said too often, never to silence."""
    _with_health(monkeypatch, False)

    class _Bare:
        def __init__(self) -> None:
            self.said: list[str] = []

        def _announce(self, message: str) -> None:
            self.said.append(message)

    host = _Bare()
    media_preflight.surface_media_health_startup(host)

    assert len(host.said) == 1


def test_a_probe_that_explodes_does_not_break_the_launch(monkeypatch: Any) -> None:
    """A courtesy that can take a launch down is not a courtesy."""

    def _boom() -> CastMediaHealth:
        raise RuntimeError("no ffmpeg here")

    monkeypatch.setattr(media_preflight, "current_health", _boom)
    host = _Host()

    media_preflight.surface_media_health_startup(host)  # must not raise

    assert host.said == []


def test_asking_answers_even_on_a_healthy_machine(monkeypatch: Any) -> None:
    _with_health(monkeypatch, True)

    assert "installed" in media_preflight.readout()


def test_the_probe_asks_the_same_question_the_features_ask() -> None:
    """A health report that probed differently from the code it describes
    would eventually describe a machine nobody has, and be believed.

    ``ffmpeg_available`` is what ``core.podcasts.audio_processing`` and the
    chapter analysers resolve through, so it is what the report asks.
    """
    from pathlib import Path

    source = Path(media_preflight.__file__).read_text(encoding="utf-8")

    assert "ffmpeg_available" in source
