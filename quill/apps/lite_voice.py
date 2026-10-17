"""QUILL Lite's one speech channel: a running screen reader, and nothing else.

Split out of :mod:`quill.apps.lite` under GATE-11, and it stands on its own
anyway -- everything here is about *how* a sentence reaches a listener, while
``lite.py`` is the application object.
"""

from __future__ import annotations

import time
from typing import Any

__all__ = ["ScreenReaderVoice"]


class ScreenReaderVoice:
    """Announcements, through a running screen reader and nowhere else.

    QUILL Lite has **no self-voicing fallback** -- no SAPI, no synthesized voice
    of its own -- and that is a decision rather than an omission. A second voice
    talking over NVDA or JAWS is worse than silence, and a listener who has no
    screen reader running is not the person this editor is for; for them the
    same messages are in the status bar, which is where the window puts them.

    The delivery itself is QUILL's, not a private copy: the family's
    :class:`~quill.platform.windows.prism_bridge.AnnouncementEngine` reaches
    NVDA and JAWS through Prism or accessible_output2 and Narrator through a UIA
    notification. The one thing added here is the guard -- nothing is handed to
    the engine unless a reader is actually running, which is what keeps its SAPI
    fallback from ever being reached.

    **Braille goes through QUILL's burst coalescer** (2026-10-16). The engine
    used to write every announcement to the braille display inline, straight
    after speaking it, so a dictation preview or a run of status changes
    replaced the display faster than a finger could read cell one. QUILL has
    collapsed such bursts since 2026-08 with
    :class:`~quill.ui.announce_wiring.CoalescingBrailleWriter`; QUILL Lite now
    uses the same object rather than a copy. The engine's inline braille is
    switched off the moment the engine is built, and every braille write --
    the mirror of a spoken message and :meth:`braille` alike -- goes through
    one coalescer, so the first message of a quiet moment still appears at
    once and a burst lands as its newest message. Speech is untouched: it is
    spoken exactly when it was before, and only the braille is coalesced.
    """

    #: How long a screen-reader detection is trusted before re-probing. A reader
    #: started mid-session is picked up within this; enumerating processes on
    #: every announcement would not be.
    _PROBE_INTERVAL_SECONDS = 30.0

    def __init__(self) -> None:
        self._engine: Any | None = None
        self._reader_present = False
        self._probed_at = 0.0
        #: Shortest gap between two spoken messages, in milliseconds. Zero is no
        #: throttle, which is the default and what QUILL Lite has always done.
        #: Set from ``settings.announcement_throttle_ms`` when the app starts and
        #: whenever Preferences is saved.
        self.throttle_ms = 0
        self._spoke_at = 0.0
        #: The one braille writer for the whole app: QUILL's burst coalescer
        #: over :meth:`_write_braille`. Built with the engine.
        self._braille_out: Any | None = None

    def _reader_running(self) -> bool:

        now = time.monotonic()
        if now - self._probed_at < self._PROBE_INTERVAL_SECONDS and self._probed_at:
            return self._reader_present
        self._probed_at = now
        try:
            from quill.platform.windows.sr_detect import detect_screen_reader

            self._reader_present = detect_screen_reader().detected
        except Exception:  # noqa: BLE001 - detection must never break an announcement
            self._reader_present = False
        return self._reader_present

    def reprobe(self) -> None:
        """Look for a screen reader afresh on the next message.

        For the screen-reader watchdog (``lite_sr_watchdog.py``): when a reader
        comes back, the first thing to say is that it has, and the 30-second
        detection cache would otherwise still be answering "none".
        """
        self._probed_at = 0.0

    def speak(self, message: str, *, interrupt: bool = True) -> None:
        """Say *message* if a screen reader is listening. Never raises.

        ``interrupt=False`` is for a cue that accompanies the reader rather
        than replacing it -- see :mod:`quill.apps.lite_window_headings`.
        """
        text = (message or "").strip()
        if not text or not self._reader_running():
            return
        # The throttle, which QUILL has had and QUILL Lite did not (bad.md A5). A
        # key held down that announces on every repeat floods the reader, and
        # the only remedy a listener had was to turn speech off. Dropped here
        # rather than at the call sites, because the status bar is written
        # before this is reached: the throttle takes the speech and never the
        # record, so nothing is lost that cannot be read back.
        if self.throttle_ms > 0:
            now = time.monotonic()
            if (now - self._spoke_at) * 1000.0 < self.throttle_ms:
                return
            self._spoke_at = now
        try:
            engine = self._ensure_engine()
            spoken = engine.announce(text, force_speech=interrupt)
        except Exception:  # noqa: BLE001 - the status bar still carries the message
            self._engine = None
            return
        # The braille mirror, after the speech and only when the speech went
        # out -- the order and the condition the engine's own inline braille
        # had, now through the coalescer.
        if not spoken:
            self._braille_writer()(text)

    def braille(self, message: str) -> None:
        """Write *message* to a braille display only -- dictation's live preview.
        Never spoken, and never raises."""
        text = (message or "").strip()
        if not text or not self._reader_running():
            return
        try:
            self._ensure_engine()
            self._braille_writer()(text)
        except Exception:  # noqa: BLE001 - the status bar still carries it
            pass

    def _ensure_engine(self) -> Any:
        """The engine, built on first use with its inline braille switched off.

        Off because braille is written here, through the coalescer: left on,
        every message would reach the display twice, once uncoalesced.
        """
        if self._engine is None:
            from quill.platform.windows.prism_bridge import AnnouncementEngine

            # "prism" rather than "auto": auto is allowed to self-voice.
            engine = AnnouncementEngine("prism")
            engine.set_braille_enabled(False)
            self._engine = engine
        return self._engine

    def _braille_writer(self) -> Any:
        """The shared coalescer, made once (QUILL's own class, not a copy)."""
        if self._braille_out is None:
            from quill.ui.announce_wiring import CoalescingBrailleWriter

            self._braille_out = CoalescingBrailleWriter(self._write_braille)
        return self._braille_out

    def _write_braille(self, text: str) -> str:
        """One real write to the display; never raises. A display unplugged
        mid-sentence must not take the next announcement with it."""
        braille = getattr(self._engine, "braille", None)
        if not callable(braille):
            return ""
        try:
            return str(braille(text) or "")
        except Exception:  # noqa: BLE001 - the status bar still carries it
            return ""

    def backend_name(self) -> str:
        """What is serving speech right now, for the ``--check`` diagnostic."""
        if not self._reader_running():
            return "none (no screen reader running)"
        self.speak("")  # builds the engine without saying anything
        state = getattr(self._engine, "state", None)
        return str(state().backend_name) if callable(state) else "unknown"
