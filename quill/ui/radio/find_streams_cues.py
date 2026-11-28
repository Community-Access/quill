"""Sounds and names while Find Streams scans (wx).

A mixin for :class:`quill.ui.radio.link_finder_dialog.LinkFinderDialog`, kept
apart under GATE-11. The rules are :mod:`quill.core.radio.search_cues`:

* a soft cue every two seconds while a scan runs, from a repeating timer the
  window owns and stops the moment the scan ends or the window closes;
* the name a stream reports while it is checked, shown in the status line and
  spoken at most once every two seconds; and
* the cue that goes with how a scan ended (nothing found, or could not finish).

One switch, ``find_streams_sounds`` in Preferences, turns the three cues off. It
never turns off a sentence.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio import search_cues as cues
from quill.core.sound_events import SoundEvent

#: The three cues this window can post: the working cue from the timer, and the
#: other two as the answer to how a scan ended (``outcome_cue``).
CUES = (
    SoundEvent.RADIO_SEARCH_WORKING,
    SoundEvent.RADIO_SEARCH_EMPTY,
    SoundEvent.RADIO_SEARCH_FAILED,
)


class CuesMixin:
    """The Find Streams window's sounds and live titles."""

    def _init_cues(self) -> None:
        from quill.ui.surface_lifetime import stop_timer_on_destroy

        wx = self._wx
        self._titles = cues.TitleAnnouncer()
        self._cue_timer = wx.Timer(self.dialog)
        self.dialog.Bind(wx.EVT_TIMER, self._on_cue_timer, self._cue_timer)
        stop_timer_on_destroy(self.dialog, self._cue_timer)

    def _cues_on(self) -> bool:
        history = getattr(self._host, "_radio_history", None)
        return bool(getattr(history, "find_streams_sounds", True))

    def _start_cues(self) -> None:
        self._titles.reset()
        if self._cues_on():
            self._cue_timer.Start(cues.CUE_INTERVAL_MS)

    def _stop_cues(self) -> None:
        self._cue_timer.Stop()

    def _on_cue_timer(self, _event: object) -> None:
        # The result and this timer can both be queued: only while still true.
        if self._scanning and self._cues_on():
            self._post_cue(SoundEvent.RADIO_SEARCH_WORKING)

    @staticmethod
    def _post_cue(event: Any) -> None:
        try:
            from quill.ui.companion_cues import post_cue

            post_cue(event)
        except Exception:  # noqa: BLE001 - no sound stack is never a failed scan
            return

    def _on_checked(self, _url: str, verdict: Any) -> None:
        """A link's check finished (a worker thread): hand its name to the window."""
        name = getattr(verdict, "name", "")
        if name:
            self._wx.CallAfter(self._show_title, name)

    def _show_title(self, name: str) -> None:
        if not self._scanning:
            return  # the scan ended while this was queued
        sentence, speak = self._titles.report(name)
        if not sentence:
            return
        self._status.SetLabel(sentence)
        if speak:
            self._announce(sentence)

    def _outcome_sound(self, *, failed: bool, found: int) -> str:
        return cues.outcome_cue(failed=failed, found=found, enabled=self._cues_on())
