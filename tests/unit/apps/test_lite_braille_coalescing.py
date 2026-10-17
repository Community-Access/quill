"""QUILL Lite's braille goes through QUILL's burst coalescer (2026-10-16).

Fakes only: no screen reader, no braille display, no wx timer. The coalescer is
handed a fake scheduler whose timer is "running" until the test fires it, which
is exactly the window in which a burst must collapse to its newest message.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.apps.lite_voice import ScreenReaderVoice
from quill.ui.announce_wiring import CoalescingBrailleWriter


class _Timer:
    def __init__(self, fn: Any) -> None:
        self.fn = fn
        self.running = True

    def IsRunning(self) -> bool:  # noqa: N802 - wx timer shape
        return self.running

    def fire(self) -> None:
        self.running = False
        self.fn()


class _Engine:
    """Records what would have been spoken and what reached the display."""

    def __init__(self, *, speech_error: str | None = None) -> None:
        self.spoken: list[tuple[str, bool]] = []
        self.brailled: list[str] = []
        self.braille_enabled: bool | None = None
        self._speech_error = speech_error

    def announce(self, text: str, *, force_speech: bool = False) -> str | None:
        self.spoken.append((text, force_speech))
        return self._speech_error

    def braille(self, text: str) -> str:
        self.brailled.append(text)
        return ""

    def set_braille_enabled(self, enabled: bool) -> None:
        self.braille_enabled = enabled


def _voice(engine: _Engine) -> tuple[ScreenReaderVoice, list[_Timer]]:
    voice = ScreenReaderVoice()
    voice._reader_running = lambda: True  # type: ignore[method-assign]
    voice._engine = engine
    timers: list[_Timer] = []

    def schedule(_delay_ms: int, fn: Any) -> _Timer:
        timer = _Timer(fn)
        timers.append(timer)
        return timer

    voice._braille_out = CoalescingBrailleWriter(voice._write_braille, schedule=schedule)
    return voice, timers


def test_a_burst_is_spoken_in_full_but_brailled_as_its_newest_message() -> None:
    engine = _Engine()
    voice, timers = _voice(engine)

    for message in ("Dictating: hel", "Dictating: hello", "Dictating: hello wor"):
        voice.speak(message)

    # Speech timing is unchanged: every message spoken, at once, in order.
    assert [text for text, _ in engine.spoken] == [
        "Dictating: hel",
        "Dictating: hello",
        "Dictating: hello wor",
    ]
    # The first braille write is immediate (no added latency)...
    assert engine.brailled == ["Dictating: hel"]
    # ...and the rest of the burst settles to its newest message.
    timers[-1].fire()
    assert engine.brailled == ["Dictating: hel", "Dictating: hello wor"]


def test_a_message_after_a_quiet_moment_is_brailled_at_once() -> None:
    engine = _Engine()
    voice, timers = _voice(engine)

    voice.speak("Saved.")
    timers[-1].fire()  # the window closes with nothing pending
    voice.speak("Bold on.")

    assert engine.brailled == ["Saved.", "Bold on."]


def test_braille_only_previews_share_the_same_coalescer() -> None:
    """Dictation's live preview (braille()) and spoken status are one stream on
    the display, so a preview cannot slip in between and flash."""
    engine = _Engine()
    voice, timers = _voice(engine)

    voice.speak("Listening.")
    voice.braille("hello")
    voice.braille("hello there")

    assert engine.spoken == [("Listening.", True)]
    assert engine.brailled == ["Listening."]
    timers[-1].fire()
    assert engine.brailled == ["Listening.", "hello there"]


def test_failed_speech_writes_no_braille() -> None:
    """The order and condition the engine's inline braille had: after speech,
    and only when the speech went out."""
    engine = _Engine(speech_error="Prism announcement failed")
    voice, _timers = _voice(engine)

    voice.speak("Saved.")

    assert engine.brailled == []


def test_the_engine_inline_braille_is_switched_off_when_built(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    built: list[_Engine] = []

    def make(_backend: str) -> _Engine:
        engine = _Engine()
        built.append(engine)
        return engine

    import quill.platform.windows.prism_bridge as bridge

    monkeypatch.setattr(bridge, "AnnouncementEngine", make)
    voice = ScreenReaderVoice()
    voice._reader_running = lambda: True  # type: ignore[method-assign]

    voice.speak("Saved.")

    assert len(built) == 1
    # Off, so the message reaches the display once (through the coalescer),
    # not twice.
    assert built[0].braille_enabled is False
    assert built[0].brailled == ["Saved."]


def test_the_writer_is_quills_class_not_a_copy() -> None:
    voice = ScreenReaderVoice()
    assert isinstance(voice._braille_writer(), CoalescingBrailleWriter)
    assert voice._braille_writer() is voice._braille_writer()


def test_a_throttled_message_reaches_neither_speech_nor_braille() -> None:
    engine = _Engine()
    voice, _timers = _voice(engine)
    voice.throttle_ms = 60_000

    voice.speak("one")
    voice.speak("two")

    assert [text for text, _ in engine.spoken] == ["one"]
    assert engine.brailled == ["one"]


def test_a_display_error_never_raises() -> None:
    engine = _Engine()

    def broken(_text: str) -> str:
        raise OSError("display unplugged")

    engine.braille = broken  # type: ignore[method-assign]
    voice, _timers = _voice(engine)

    voice.speak("Saved.")  # must not raise
    voice.braille("preview")  # nor this

    assert engine.spoken == [("Saved.", True)]


def test_no_reader_means_no_braille_either() -> None:
    engine = _Engine()
    voice, _timers = _voice(engine)
    voice._reader_running = lambda: False  # type: ignore[method-assign]

    voice.speak("Saved.")
    voice.braille("preview")

    assert engine.spoken == []
    assert engine.brailled == []


def test_reprobe_forgets_the_cached_detection() -> None:
    voice = ScreenReaderVoice()
    voice._probed_at = 123.0
    voice._reader_present = False

    voice.reprobe()

    assert voice._probed_at == 0.0
