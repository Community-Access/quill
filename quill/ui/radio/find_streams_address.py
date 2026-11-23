"""The Find Streams Website address box, which remembers sites that worked (wx).

An editable combo box: type an address as before, or press Alt+Down to choose
one of the last ten that found a live stream
(:mod:`quill.core.radio.recent_websites`). Nothing is spoken when the list
changes, and nothing is scanned until you press Enter or Scan: arrowing
through the closed box only changes the text, as it does in any Windows combo
box.

The list is updated with ``Insert`` and ``Delete`` only, never by refilling it
(which clears the text on Windows), and never while it is dropped down, so a
remembered row cannot move under the listener's arrow (FUX-06). An update that
arrives while it is open waits until it closes.

Remembering addresses that worked is an idea from Andre Louis's StreamSift
(https://github.com/OnjLouis/StreamSift), written in QUILL's own code.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from quill.core.radio import recent_websites
from quill.core.radio.page_links import PageStreamCandidate
from quill.ui.spoken_name import set_spoken_name

__all__ = ["AddressBox"]


class AddressBox:
    """The combo box and the remembered addresses behind it."""

    def __init__(self, parent: Any, wx: Any, host: Any) -> None:
        self._wx = wx
        self._host = host
        history = getattr(host, "_radio_history", None)
        self._history = history
        self._recent: tuple[str, ...] = tuple(getattr(history, "recent_websites", ()) or ())
        self._dropped = False
        self._waiting: tuple[str, ...] | None = None
        self.ctrl = wx.ComboBox(
            parent, choices=list(self._recent), style=wx.CB_DROPDOWN | wx.TE_PROCESS_ENTER
        )
        self.ctrl.SetName("The website address to scan for stream links")
        set_spoken_name(self.ctrl, "Website address")
        self.ctrl.SetHelpText(
            "Type a station's website address, or press Alt+Down to choose one of the "
            "last ten addresses that found a live stream. Press Enter or Scan to scan it. "
            "The list is empty until a scan finds a live stream."
        )
        self.ctrl.Bind(wx.EVT_COMBOBOX_DROPDOWN, self._on_dropdown)
        self.ctrl.Bind(wx.EVT_COMBOBOX_CLOSEUP, self._on_closeup)

    @property
    def recent(self) -> tuple[str, ...]:
        return self._recent

    def remember(self, address: str, candidates: Sequence[PageStreamCandidate]) -> None:
        """Remember *address* when the scan found at least one live stream."""
        if not any(c.check == "live" for c in candidates):
            return
        updated = recent_websites.remember(self._recent, address)
        if updated == self._recent:
            return
        if self._history is not None:
            self._history.recent_websites = updated
            save = getattr(self._host, "_save_radio_history", None)
            if callable(save):
                save()
        if self._dropped:
            self._waiting = updated
        else:
            self._show(updated)

    def _show(self, updated: tuple[str, ...]) -> None:
        """Bring the rows in line with *updated* by deleting and inserting only."""
        text = self.ctrl.GetValue()
        newest = updated[0].rstrip("/").casefold()
        for row in range(self.ctrl.GetCount() - 1, -1, -1):
            if self.ctrl.GetString(row).rstrip("/").casefold() == newest:
                self.ctrl.Delete(row)
        self.ctrl.Insert(updated[0], 0)
        while self.ctrl.GetCount() > len(updated):
            self.ctrl.Delete(self.ctrl.GetCount() - 1)
        self._recent = updated
        if self.ctrl.GetValue() != text:
            self.ctrl.ChangeValue(text)

    def _on_dropdown(self, event: Any) -> None:
        self._dropped = True
        event.Skip()

    def _on_closeup(self, event: Any) -> None:
        self._dropped = False
        if self._waiting is not None:
            waiting, self._waiting = self._waiting, None
            self._wx.CallAfter(self._show, waiting)
        event.Skip()
