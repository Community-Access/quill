"""Screen-reader death watchdog for MainFrame (16-assessment.md item 10).

Detection used to be a one-shot startup probe; if the reader died mid-session
QUILL never knew. This mixin runs the :class:`~quill.core.sr_watchdog.
SrWatchdog` state machine on a 30-second cadence and applies the collapse
rule: **flush unsaved work first, then act.**

On a confirmed death (two consecutive misses, so a routine JAWS/NVDA restart
never fires it) every open tab is snapshotted through the existing autosave
machinery, then the event is announced — the announcement engine's fallback
chain (another reader, the SAPI self-voice) is exactly what "announce" means
when the primary reader just died — and recorded in Notifications so the user
finds the explanation later. Recovery is announced too, so a reader restart
is never silent either.

The watchdog never closes QUILL: unlike single-reader tools, QUILL works with several
readers and its own self-voice, so the correct response to a dead reader is
"your work is safe, here is what happened", not shutdown.
"""

from __future__ import annotations

import sys

from quill.core.sr_watchdog import CHECK_INTERVAL_SECONDS, SrWatchdog


class SrWatchdogMixin:
    """Mixin for MainFrame: periodic screen-reader liveness checks."""

    def _start_sr_watchdog(self) -> None:
        """Begin the 30 s liveness cadence (Windows only; probe is Win32)."""
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
        wx = self._wx
        self._sr_watchdog_call = wx.CallLater(
            CHECK_INTERVAL_SECONDS * 1000, self._on_sr_watchdog_tick
        )

    def _on_sr_watchdog_tick(self) -> None:
        try:
            event = self._sr_watchdog.check()
            if event.kind == "died":
                self._on_screen_reader_died(event.reader_name)
            elif event.kind == "recovered":
                self._announce(f"{event.reader_name} is running again.")
        except RuntimeError:
            return  # the frame is going away; stop rescheduling
        except Exception:  # noqa: BLE001 - the watchdog must never take QUILL down
            pass
        self._schedule_sr_watchdog_check()

    def _on_screen_reader_died(self, reader_name: str) -> None:
        """The environment collapsed: persist everything, then explain."""
        flushed = self._sr_emergency_flush()
        name = reader_name or "Your screen reader"
        message = (
            f"{name} appears to have stopped. Your work is safe: "
            f"{flushed} document{'s' if flushed != 1 else ''} "
            "snapshotted to autosave. QUILL keeps running; restart your "
            "screen reader when ready."
        )
        # The announcement engine's own fallback chain (another reader, the
        # SAPI self-voice) is what makes announcing after a reader death
        # meaningful rather than ironic.
        self._announce(message)
        record = getattr(self, "_record_notification", None)
        if callable(record):
            record(message, "warning")

    def _sr_emergency_flush(self) -> int:
        """Snapshot every open tab through autosave; returns how many succeeded.

        Best-effort by the autosave contract: a failure on one tab must not
        stop the others, and nothing here may raise. The active tab's editor
        text is synced into its document first so the snapshot carries the
        very latest keystrokes.
        """
        from quill.core.autosave import autosave_document

        try:
            current = self.editor.GetValue()
            if current != self.document.text:
                self.document.set_text(current)
        except Exception:  # noqa: BLE001 - sync is best-effort
            pass
        flushed = 0
        for tab in getattr(self, "_document_tabs", []):
            try:
                autosave_document(tab.document, self.session_id)
                flushed += 1
            except Exception:  # noqa: BLE001 - one tab must not stop the rest
                continue
        return flushed
