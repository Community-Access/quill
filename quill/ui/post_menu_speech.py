"""Speak a menu command's outcome after the menu has closed (UX-013).

Choosing a menu item closes the menu, and the screen reader then says where
focus landed. A sentence the command speaks at once is spoken *under* that,
and the focus speech cuts it off: TG Drop Deck's "Recording started" was lost
this way (its ``CHANGELOG.md`` lines 40-55). QUILL had no shared way to wait
for this -- the editor returns focus after a menu closes, and a few windows
speak after a fixed ``CallLater`` -- so this is it.

:class:`PostMenuSpeech` watches a frame's (and any popup menu's) open and close
events. A sentence raised while a menu is open, or within :data:`SETTLE_MS` of
one closing, is held and spoken once the menu has been closed that long; any
other sentence is spoken at once, so a global hotkey or a background result
is never delayed. Only the speaking waits: the caller still writes the status
bar at once. Held sentences are spoken in order.

The announcement itself still goes through the app's announcement service
(the callable handed to :meth:`say`), so it is brailled as well (GATE-BRAILLE).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from quill.stability.wx_dispatch import call_later_safely

#: How long after a menu closes the screen reader is still saying where focus
#: went. The same order as the 400 ms other QUILL windows already wait after a
#: dialog closes before speaking (``quill/ui/lineups/rule_edit_dialog.py``).
SETTLE_MS = 400
#: A menu that reported opening and never closing (a lost close event) stops
#: holding speech after this long, so nothing is held for ever.
STUCK_OPEN_S = 5.0


class PostMenuSpeech:
    """Hold a menu command's sentence until the menu has closed and settled."""

    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.monotonic,
        schedule: Callable[[int, Callable[[], None]], Any] | None = None,
    ) -> None:
        self._clock = clock
        self._schedule = schedule
        self._depth = 0
        self._opened_at = float("-inf")
        self._closed_at = float("-inf")
        self._held: list[Callable[[], None]] = []
        self._timer: Any = None

    # -- watching menus -------------------------------------------------------------

    def watch(self, handler: Any) -> None:
        """Follow the menus of *handler*: a frame, or a popup ``wx.Menu``."""
        import wx

        handler.Bind(wx.EVT_MENU_OPEN, self._opened)
        handler.Bind(wx.EVT_MENU_CLOSE, self._closed)

    def menu_opened(self) -> None:
        self._depth += 1
        self._opened_at = self._clock()

    def menu_closed(self) -> None:
        self._depth = max(0, self._depth - 1)
        self._closed_at = self._clock()

    def _opened(self, event: Any) -> None:
        self.menu_opened()
        event.Skip()

    def _closed(self, event: Any) -> None:
        self.menu_closed()
        event.Skip()

    # -- speaking ---------------------------------------------------------------------

    def wait_ms(self) -> int:
        """How much longer a sentence raised now must wait; 0 means speak now."""
        now = self._clock()
        if self._depth > 0 and now - self._opened_at < STUCK_OPEN_S:
            return SETTLE_MS
        left = SETTLE_MS - (now - self._closed_at) * 1000  # -inf before any menu closed
        return int(left) if left > 0 else 0

    def say(self, speak: Callable[[], None]) -> bool:
        """Run *speak* now, or once the menu has settled. True when it was held."""
        wait = self.wait_ms()
        if wait <= 0 and not self._held:
            speak()
            return False
        self._held.append(speak)
        self._arm(max(1, wait))
        return True

    def _arm(self, wait: int) -> None:
        timer = self._timer
        if timer is not None and bool(getattr(timer, "IsRunning", lambda: False)()):
            return
        schedule = self._schedule or self._default_schedule
        self._timer = schedule(wait, self._flush)

    @staticmethod
    def _default_schedule(wait: int, flush: Callable[[], None]) -> Any:
        return call_later_safely(wait, flush, name="Speaking after the menu closed")

    def _flush(self) -> None:
        self._timer = None
        wait = self.wait_ms()
        if wait > 0:  # another menu opened meanwhile: wait for that one too
            self._arm(wait)
            return
        held, self._held = self._held, []
        for speak in held:
            speak()


class SettledSpeechMixin:
    """For a window host with ``_announce`` and ``_set_status_quiet``.

    The host calls ``self._post_menu_speech_for().watch(...)`` on its frame
    (and any popup menu) when it builds its menus, then speaks a menu
    command's outcome with :meth:`_announce_settled`.
    """

    def _post_menu_speech_for(self) -> PostMenuSpeech:
        speech = getattr(self, "_post_menu_speech", None)
        if speech is None:
            speech = PostMenuSpeech()
            self._post_menu_speech = speech
        return speech

    def _announce_settled(self, sentence: str, *, status: str = "") -> None:
        """A start or stop sentence, spoken once a menu has closed (UX-013).

        The status bar shows *status* (or the sentence) at once; only the
        speech waits, and only when a menu has just closed. Keep *sentence*
        state first ("Recording started") and free of paths: a path goes in
        *status*, where it can be read at leisure.
        """
        host: Any = self
        host._set_status_quiet(status or sentence)

        def speak() -> None:
            host._announce(sentence)
            if status:
                host._set_status_quiet(status)

        speech = getattr(self, "_post_menu_speech", None)
        if speech is None:
            speak()
        else:
            speech.say(speak)
