"""What ``MpvRadioEngine.load`` must reset before every station.

mpv's client is one long-lived object for the whole session, and several of the
things Quill Radio sets on it are **options**, not properties of the file that
happens to be loaded. An option nobody clears leaks from one station into the
next, and every one of those leaks is silent.

This is the test that was missing when the worst of them shipped: showing the
picture for a YouTube video sets ``audio-files`` to that video's separate audio
stream (YouTube serves picture and sound apart), and nothing ever cleared it --
so the next video played with the *previous* video's sound. "It is like it is
caching whatever the last video was that worked" (2026-08-23), which is exactly
what it was doing.

No wx and no libmpv: ``load`` is called against a stub client, which is all it
needs to state its contract.
"""

from __future__ import annotations

from typing import Any

from quill.ui.radio.mpv_radio_engine import MpvRadioEngine


class _Client:
    def __init__(self) -> None:
        self.props: dict[str, str] = {}
        self.commands: list[tuple[Any, ...]] = []

    def set_str(self, name: str, value: str) -> None:
        self.props[name] = value

    def command(self, *args: Any) -> None:
        self.commands.append(args)


class _Timer:
    def __init__(self) -> None:
        self.started = 0

    def Start(self, _ms: int) -> None:  # noqa: N802 - wx's own casing
        self.started += 1


def _engine() -> MpvRadioEngine:
    engine = MpvRadioEngine.__new__(MpvRadioEngine)
    engine._mpv = _Client()  # type: ignore[attr-defined]
    engine._timer = _Timer()  # type: ignore[attr-defined]
    engine._volume = 70  # type: ignore[attr-defined]
    return engine


def test_a_load_clears_the_external_audio_track() -> None:
    """The bug: a second video played the first one's sound.

    ``audio-files`` is client-wide, so the video whose picture was last shown
    kept supplying the audio for everything loaded afterwards -- and when
    YouTube's addresses expired a few hours later it would have supplied
    nothing at all.
    """
    engine = _engine()
    engine._mpv.set_str("audio-files", "https://previous-video/audio")  # type: ignore[attr-defined]

    assert engine.load("https://next-video/stream") is True

    assert engine._mpv.props["audio-files"] == ""  # type: ignore[attr-defined]


def test_a_load_still_resets_the_other_leaky_options() -> None:
    """Speed and referrer were already cleared per load, for the same reason."""
    engine = _engine()
    engine.load("https://stream/one")

    props = engine._mpv.props  # type: ignore[attr-defined]
    assert props["speed"] == "1.00"
    assert props["pause"] == "no"
    assert props["volume"] == "70"
    assert "referrer" in props


def test_a_load_hands_the_url_to_mpv_and_starts_polling() -> None:
    engine = _engine()
    engine.load("https://stream/one")

    assert engine._mpv.commands == [("loadfile", "https://stream/one", "replace")]  # type: ignore[attr-defined]
    assert engine._timer.started == 1  # type: ignore[attr-defined]
    assert engine._bounded is False  # every load starts live-shaped
