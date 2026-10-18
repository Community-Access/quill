"""Keep the test suite's voice, message boxes and sound inside the test process.

**Why this exists (Jeff, 2026-10-17).** Agents ran the suite on a machine with
JAWS running, and JAWS read the tests out loud: "Radio settings could not be
saved", "the mpv playback engine is missing ... playing through Windows Media",
and more. Nothing stopped it. A test that builds a real window builds a real
``AnnouncementEngine``, which asks Prism and accessible_output2 for the live
screen reader -- and on a developer's machine there is one. Every
``self._announce(...)`` a test provoked was then spoken to whoever was sitting
at the computer, and CI, which has no screen reader, could never notice.

**Two layers.**

*Recorders* sit where the app's own code chooses an output, so the app keeps
working exactly as it does on CI (no reader, nothing live) and what it would
have said is kept in :data:`SPOKEN` / :data:`SOUNDS` for a test to read:

- Prism and accessible_output2 report no live reader (``prism_bridge``'s
  ``import_module`` refuses ``prism``/``prismatoid``; the accessible_output2
  speaker is absent), and ``_screen_reader_active`` answers False -- the
  answer CI gets.
- The SAPI self-voice is a recording voice, so the announcement worker still
  runs and still drains, and nothing reaches the sound card.
- The Narrator UIA notification finds no window to raise from.
- ``winsound`` records instead of playing; waveOut has no device.
- The modern Windows Media engine is unavailable, and the classic one is an
  inert stand-in (``wx.media.MediaCtrl`` hosts the real Windows Media Player
  control, which also access-violates deep into a long run -- the reason
  ``tests/unit/ui`` already stubbed it).
- A source checkout's staged libmpv (``build/deps/mpv``) is not there, so a
  test behaves the same in the main checkout as in a worktree or on CI.

*Tripwires* sit on the real thing behind them: creating a SAPI voice, loading
a libmpv DLL that exists on disk, and ``wx.MessageBox`` (a real one blocks the
run and is read aloud). Reaching one fails the test that did it, by name, at
its teardown -- a teardown failure rather than only an exception, because the
code under test usually swallows exceptions from exactly these calls.

**machine_global tests are left alone**: they exist to drive the real
devices, and each gets the originals back for its own duration.

Installed once per process from ``tests/conftest.py``.
"""

from __future__ import annotations

import importlib
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

#: Everything the app would have said aloud since the process started (SAPI
#: self-voice path). Tests read it through :func:`spoken_during`.
SPOKEN: list[str] = []
#: Every sound the app asked ``winsound`` to play.
SOUNDS: list[str] = []
#: Real outputs reached by the running test; drained at its teardown.
VIOLATIONS: list[str] = []

#: ``(module, attribute, original, replacement)`` for everything installed.
_INSTALLED: list[tuple[Any, str, Any, Any]] = []


class RecordingVoice:
    """A SAPI ``SpVoice`` stand-in: what it is asked to say goes to SPOKEN."""

    def Speak(self, message: str, flags: int = 0) -> int:  # noqa: N802 - SAPI's name
        _ = flags
        SPOKEN.append(str(message))
        return 0


class InertMediaEngine:
    """Protocol-complete stand-in for the classic Windows Media engine.

    Accepts every call and plays nothing, so a window that builds a player
    gets one and no test reaches the Windows Media Player control.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        self.loads: list[str] = []
        self.closed = False

    def load(self, source: str) -> bool:
        self.loads.append(source)
        return True

    def play(self) -> None:
        pass

    def pause(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True

    def seek(self, ms: int, *, resume: bool | None = None) -> None:
        pass

    def seek_ms(self, position: int) -> None:
        pass

    def position_ms(self) -> int:
        return 0

    def length_ms(self) -> int:
        return 0

    def is_playing(self) -> bool:
        return False

    def set_volume(self, percent: int) -> None:
        pass

    def set_rate(self, rate: float) -> None:
        pass

    def set_audio_device(self, name: str) -> None:
        pass


def _culprit() -> str:
    return os.environ.get("PYTEST_CURRENT_TEST", "a test")


def _trip(what: str) -> None:
    VIOLATIONS.append(f"{_culprit()} reached {what}")


def _patch(module: Any, name: str, replacement: Any) -> None:
    original = getattr(module, name)
    setattr(module, name, replacement)
    _INSTALLED.append((module, name, original, replacement))


def _optional(module_name: str) -> Any | None:
    try:
        return importlib.import_module(module_name)
    except Exception:  # noqa: BLE001 - not this platform, or not installed
        return None


def install() -> None:
    """Put the recorders and tripwires in place for this process. Idempotent."""
    if _INSTALLED:
        return
    _install_speech()
    _install_message_box()
    _install_audio()


def _install_speech() -> None:
    prism_bridge = _optional("quill.platform.windows.prism_bridge")
    if prism_bridge is not None:
        real_import = prism_bridge.import_module

        def import_without_live_readers(name: str, *args: Any, **kwargs: Any) -> Any:
            if name in ("prism", "prismatoid"):
                raise ImportError(f"{name} is never loaded by the test suite")
            return real_import(name, *args, **kwargs)

        _patch(prism_bridge, "import_module", import_without_live_readers)
        _patch(prism_bridge, "_ao2_speaker_singleton", lambda: None)
        _patch(prism_bridge, "_screen_reader_active", lambda: False)
        _patch(prism_bridge, "_build_tts_voice", RecordingVoice)
        drop_real_voice()
    narrator = _optional("quill.platform.windows.narrator_announce")
    if narrator is not None:
        _patch(narrator, "_own_top_level_hwnd", lambda: 0)
    sapi5 = _optional("quill.platform.windows.sapi5")
    if sapi5 is not None:

        def create_voice_refused() -> Any:
            _trip("a real SAPI voice (quill.platform.windows.sapi5.create_voice)")
            raise RuntimeError("the test suite never creates a real SAPI voice")

        _patch(sapi5, "create_voice", create_voice_refused)


def _install_message_box() -> None:
    wx = _optional("wx")
    if wx is None or not callable(getattr(wx, "MessageBox", None)):
        return

    def message_box_refused(message: str = "", caption: str = "", *args: Any, **kwargs: Any) -> int:
        _trip(f"a real wx.MessageBox ({caption!r}: {str(message)[:80]!r})")
        return int(getattr(wx, "CANCEL", 16))

    _patch(wx, "MessageBox", message_box_refused)


def _install_audio() -> None:
    winsound = _optional("winsound")
    if winsound is not None:

        def play_sound(sound: Any, flags: int = 0) -> None:
            SOUNDS.append("" if sound is None else str(sound)[:120])

        _patch(winsound, "PlaySound", play_sound)
        _patch(winsound, "Beep", lambda _frequency, _duration: SOUNDS.append("beep"))
        _patch(winsound, "MessageBeep", lambda _kind=0: SOUNDS.append("message beep"))
    wave_out = _optional("quill.platform.windows.wave_out")
    if wave_out is not None:
        _patch(wave_out, "_winmm", lambda: None)
    winrt_engine = _optional("quill.ui.audio.winrt_engine")
    if winrt_engine is not None:
        _patch(winrt_engine, "winrt_media_available", lambda: False)
    audio_engine = _optional("quill.ui.audio.audio_engine")
    if audio_engine is not None:
        _patch(audio_engine, "WxMediaEngine", InertMediaEngine)
    source_tools = _optional("quill.core.source_tools")
    if source_tools is not None:
        _patch(source_tools, "staged_tool_dir", lambda _name: None)
    mpv_engine = _optional("quill.ui.audio.mpv_engine")
    if mpv_engine is not None:
        client = mpv_engine._MpvClient
        real_init = client.__init__

        def guarded_init(self: Any, dll_path: Path) -> None:
            if Path(dll_path).is_file():
                _trip(f"the real libmpv ({dll_path})")
                raise OSError("the test suite never loads a real libmpv")
            real_init(self, dll_path)

        _patch(client, "__init__", guarded_init)


def drop_real_voice() -> None:
    """Forget a SAPI voice a machine_global test left cached on the worker."""
    prism_bridge = _optional("quill.platform.windows.prism_bridge")
    if prism_bridge is not None and not isinstance(prism_bridge._tts_voice, RecordingVoice):
        prism_bridge._tts_voice = None


def restore_originals(monkeypatch: pytest.MonkeyPatch) -> None:
    """Give a machine_global test the real outputs for its own duration."""
    for module, name, original, _replacement in _INSTALLED:
        monkeypatch.setattr(module, name, original)


def take_violations() -> list[str]:
    found = list(VIOLATIONS)
    VIOLATIONS.clear()
    return found


@contextmanager
def spoken_during() -> Iterator[list[str]]:
    """``with spoken_during() as said:`` -- what the app said inside the block."""
    start = len(SPOKEN)
    said: list[str] = []
    try:
        yield said
    finally:
        said.extend(SPOKEN[start:])


def flush_speech() -> None:
    """Let the announcement worker finish what it was handed."""
    prism_bridge = _optional("quill.platform.windows.prism_bridge")
    if prism_bridge is not None:
        prism_bridge.flush_tts_for_tests()


__all__ = [
    "SOUNDS",
    "SPOKEN",
    "VIOLATIONS",
    "InertMediaEngine",
    "RecordingVoice",
    "drop_real_voice",
    "flush_speech",
    "install",
    "restore_originals",
    "spoken_during",
    "take_violations",
]
