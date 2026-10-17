"""Emergency save when the screen reader dies, for QUILL Lite.

QUILL has had this since 2026-08 (``quill/ui/main_frame_sr_watchdog.py``); QUILL
Lite did not, so a reader that crashed mid-sentence left a blind writer with an
editor they could no longer hear and unsaved work that only the next autosave
tick -- up to several minutes away -- would have copied aside. QUILL Lite may
never be behind QUILL on protecting work any more than it may be ahead of it,
so this is the same protection, through the same wx-free core
(:mod:`quill.core.sr_watchdog`): the same two-strikes rule, the same 30-second
cadence, and the same sentences. Only the parts that are genuinely QUILL Lite's
live here -- its timer, its recovery copies, and its voice.

**What happens.** Every 30 seconds the running screen reader is detected. Two
misses in a row (so a routine restart of the reader, which misses one, never
fires it) mean the reader has gone. Then, in this order:

1. every document window with unsaved changes writes its recovery copy at once
   -- the same copy the autosave timer makes, and the one QUILL Lite offers
   back at the next start if it never closes cleanly;
2. the outcome is written to the status bar of the active window, and handed to
   the voice, which says it if any screen reader is still running.

When a reader comes back, QUILL Lite says so ("NVDA is running again."), after
telling its voice to look for the reader afresh rather than waiting for its
own 30-second cache.

**What it never does.** It never closes QUILL Lite, and it never self-voices.
QUILL Lite has no voice of its own by design (``lite_voice.py``), so with no
reader at all the status bar is where the explanation waits.

No setting turns this on or off, in either editor: it only ever writes recovery
copies that a clean exit throws away, and it says nothing until a reader has
actually died.
"""

from __future__ import annotations

import sys
from typing import Any

from quill.core.sr_watchdog import (
    CHECK_INTERVAL_SECONDS,
    SrWatchdog,
    died_message,
    recovered_message,
)

__all__ = ["LiteSrWatchdogMixin"]


class LiteSrWatchdogMixin:
    """Mixed into :class:`quill.apps.lite.QuillLiteApp`.

    Expects ``frames``, ``active_frame``, ``voice`` and ``shutting_down`` on
    the app -- all of which it has from ``__init__``.
    """

    frames: list[Any]
    active_frame: Any
    voice: Any
    shutting_down: bool

    def _start_sr_watchdog(self) -> None:
        """Begin the liveness cadence. Windows only: the probe is Win32."""
        if not sys.platform.startswith("win"):
            return
        if getattr(self, "_sr_watchdog", None) is not None:
            return
        self._sr_watchdog = SrWatchdog(self._sr_watchdog_probe)
        self._schedule_sr_watchdog_check()

    def _sr_watchdog_probe(self) -> str:
        from quill.platform.windows.sr_detect import detect_screen_reader

        detection = detect_screen_reader()
        return detection.name if detection.detected else ""

    def _schedule_sr_watchdog_check(self) -> None:
        import wx

        self._sr_watchdog_call = wx.CallLater(
            CHECK_INTERVAL_SECONDS * 1000, self._on_sr_watchdog_tick
        )

    def _stop_sr_watchdog(self) -> None:
        """Stop the cadence; safe to call more than once, and before it started."""
        call = getattr(self, "_sr_watchdog_call", None)
        self._sr_watchdog_call = None
        if call is not None:
            try:
                call.Stop()
            except Exception:  # noqa: BLE001 - a timer already gone is a stopped one
                pass

    def _on_sr_watchdog_tick(self) -> None:
        if self.shutting_down:
            return
        try:
            event = self._sr_watchdog.check()
            if event.kind == "died":
                self._on_screen_reader_died(event.reader_name)
            elif event.kind == "recovered":
                self._on_screen_reader_recovered(event.reader_name)
        except RuntimeError:
            return  # the app is going away; stop rescheduling
        except Exception:  # noqa: BLE001 - the watchdog must never take QUILL Lite down
            pass
        if not self.shutting_down:
            self._schedule_sr_watchdog_check()

    def _on_screen_reader_died(self, reader_name: str) -> None:
        """The environment collapsed: copy every unsaved document aside, then explain."""
        flushed = self._sr_emergency_flush()
        self._sr_tell(died_message("QUILL Lite", reader_name, flushed))

    def _on_screen_reader_recovered(self, reader_name: str) -> None:
        reprobe = getattr(self.voice, "reprobe", None)
        if callable(reprobe):
            reprobe()  # the voice's 30 s cache would otherwise still say "none"
        self._sr_tell(recovered_message(reader_name))

    def _sr_emergency_flush(self) -> int:
        """Write every modified window's recovery copy now; how many were written.

        Best-effort by the autosave contract: one window failing must not stop
        the others, and nothing here may raise. A window with no unsaved
        changes has nothing to protect and is not counted.
        """
        flushed = 0
        for frame in list(self.frames):
            try:
                if not getattr(frame, "modified", False):
                    continue
                frame._write_recovery_copy()
                if getattr(frame, "_slot", None) is not None:
                    flushed += 1
            except Exception:  # noqa: BLE001 - one window must not stop the rest
                continue
        return flushed

    def _sr_tell(self, message: str) -> None:
        """Status bar of the active window, and the voice if anything can hear it."""
        frame = self.active_frame or (self.frames[0] if self.frames else None)
        announce = getattr(frame, "_announce", None)
        if callable(announce):
            announce(message)  # speaks, and leaves it in the status bar
            return
        self.voice.speak(message)
