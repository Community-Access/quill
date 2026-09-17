"""QuillLite's one speech channel: a running screen reader, and nothing else.

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

    QuillLite has **no self-voicing fallback** -- no SAPI, no synthesized voice
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
        #: throttle, which is the default and what QuillLite has always done.
        #: Set from ``settings.announcement_throttle_ms`` when the app starts and
        #: whenever Preferences is saved.
        self.throttle_ms = 0
        self._spoke_at = 0.0

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

    def speak(self, message: str, *, interrupt: bool = True) -> None:
        """Say *message* if a screen reader is listening. Never raises.

        ``interrupt=False`` is for a cue that accompanies the reader rather
        than replacing it -- see :mod:`quill.apps.lite_window_headings`.
        """
        text = (message or "").strip()
        if not text or not self._reader_running():
            return
        # The throttle, which QUILL has had and QuillLite did not (bad.md A5). A
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
            if self._engine is None:
                from quill.platform.windows.prism_bridge import AnnouncementEngine

                # "prism" rather than "auto": auto is allowed to self-voice.
                self._engine = AnnouncementEngine("prism")
            self._engine.announce(text, force_speech=interrupt)
        except Exception:  # noqa: BLE001 - the status bar still carries the message
            self._engine = None

    def backend_name(self) -> str:
        """What is serving speech right now, for the ``--check`` diagnostic."""
        if not self._reader_running():
            return "none (no screen reader running)"
        self.speak("")  # builds the engine without saying anything
        state = getattr(self._engine, "state", None)
        return str(state().backend_name) if callable(state) else "unknown"
