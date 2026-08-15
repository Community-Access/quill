"""The wx half of hold-to-scan: a key, a timer, and a promise to let go.

:mod:`quill.core.podcasts.scan_hold` owns the policy -- when a scan starts, when
the repeats have stopped long enough to call the key released, and what is said
at each edge. This owns the two things that need wx: reading the held key, and a
timer that notices when the repeats stop.

**Why a timer rather than a key-up handler.** A key-up can be missed outright --
focus moves, a dialog opens, the window is deactivated mid-hold -- and every one
of those would leave playback stuck at four times speed. Auto-repeats that
simply stop arriving cannot fail that way. The key-up is still honoured when it
does arrive, because ending immediately feels better than ending 400 ms late;
the timer is the guarantee underneath it, not the mechanism.

**It also ends on anything else.** Losing focus, the episode finishing, the app
closing -- each calls :meth:`stop`, because the invariant worth protecting is
that nothing can leave a listener at 4x without having said so.
"""

from __future__ import annotations

import time
from typing import Any

from quill.core.podcasts.scan_hold import (
    BEGIN_MESSAGE,
    RELEASE_GRACE_MS,
    SCAN_RATE,
    ScanState,
    begin,
    end,
    end_message,
    keep_alive,
    should_end,
)

#: How often the watchdog looks. Well under the grace window, so the drop back
#: lands within a repeat or two of the key actually coming up.
_POLL_MS = 100


class ScanHoldController:
    """Hold Shift+Right to scan forward; release to drop back.

    *host* supplies ``_podcast_controller`` and ``_announce``; nothing else is
    touched, so the Manager dialog and the standalone app frame both qualify.
    """

    def __init__(self, host: Any, *, parent: Any = None) -> None:
        import wx

        self._wx = wx
        self._host = host
        self._state = ScanState()
        self._timer = wx.Timer(parent if parent is not None else wx.GetApp())
        self._timer.Bind(wx.EVT_TIMER, lambda _e: self._tick())

    @property
    def is_scanning(self) -> bool:
        return self._state.active

    def _now_ms(self) -> int:
        """A monotonic clock in milliseconds.

        ``perf_counter`` rather than a wall clock: the only question asked of
        it is "how long since the last repeat", and a wall clock that steps
        backwards (a clock sync, a timezone change) would answer that with a
        negative number and hold the scan open indefinitely.
        """
        return int(time.perf_counter() * 1000)

    def _controller(self) -> Any:
        return getattr(self._host, "_podcast_controller", None) or getattr(
            self._host, "_controller", None
        )

    def _announce(self, message: str) -> None:
        announce = getattr(self._host, "_announce", None)
        if callable(announce):
            announce(message)

    def handles(self, *, key_code: int, shift: bool, ctrl: bool, alt: bool) -> bool:
        """Whether this key press is the scan gesture.

        Shift+Right, deliberately: plain Right is Skip Forward's fixed jump and
        Ctrl+Right is the app-wide one, so the modifier keeps a gesture that
        *changes speed* clearly apart from two that change position.
        """
        return bool(shift and not ctrl and not alt and key_code == self._wx.WXK_RIGHT)

    def press(self) -> bool:
        """One key-down (or auto-repeat). True when this started the scan."""
        controller = self._controller()
        if controller is None or not controller.is_playing():
            # Nothing is playing, so there is nothing to scan through. Said
            # once rather than silently ignored: a key that does nothing and
            # says nothing is indistinguishable from a broken one.
            if not self._state.active:
                self._announce("Nothing is playing to scan through.")
            return False
        if self._state.active:
            keep_alive(self._state, now_ms=self._now_ms())
            return False
        started = begin(self._state, current_rate=controller.rate, now_ms=self._now_ms())
        if not started:
            return False
        controller.set_rate(SCAN_RATE)
        self._announce(BEGIN_MESSAGE)
        self._timer.Start(_POLL_MS)
        return True

    def release(self) -> bool:
        """A key-up arrived. Ends the scan immediately rather than on the timer."""
        return self.stop()

    def _tick(self) -> None:
        """The watchdog: repeats stopped, so the key is up."""
        if should_end(self._state, now_ms=self._now_ms()):
            self.stop()

    def stop(self) -> bool:
        """End a scan however it ended. Safe to call when none is running."""
        if not self._state.active:
            return False
        rate = end(self._state)
        self._timer.Stop()
        controller = self._controller()
        if controller is not None:
            controller.set_rate(rate)
        self._announce(end_message(rate))
        return True

    def shutdown(self) -> None:
        """Release the timer on the way out, restoring the speed first."""
        self.stop()
        try:
            self._timer.Stop()
        except Exception:  # noqa: BLE001 - a dead timer must never block close
            pass


__all__ = ["RELEASE_GRACE_MS", "SCAN_RATE", "ScanHoldController"]
