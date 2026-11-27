"""The Find Streams results list and its details field (wx).

A multi-select report list whose rows come from
:mod:`quill.core.radio.find_streams_view`, and a read-only details field that
follows the focused row. Kept out of ``link_finder_dialog.py`` so the dialog
stays a coordinator (GATE-11).

**The list changes only when the listener asks** (FUX-04, FUX-06). A refill
keeps focus and selection by stream address, so a sort or a filter leaves you
on the same stream when it is still shown, and on the first row when it is
not. The refill happens frozen, in one pass, and says nothing itself: the
dialog says the one sentence afterwards, with ``wx.CallAfter``, so the
screen reader reads the focused row first and the sentence is not cut off.

**The details field speaks nothing.** It is updated with ``ChangeValue`` as
focus moves, one fact per line (Name, Status, Format, Listeners, Link, Server,
Found by), and is in the Tab order to be read when wanted.

The Applications key or Shift+F10 opens the context menu, placed at the
focused row, and never on an empty list. The dialog's key hook owns Ctrl+A,
Ctrl+C, Ctrl+F, F3, Shift+F3 and Ctrl+S, in the list only. Space and Ctrl+Space keep their native
meaning; Ctrl+Up and Ctrl+Down belong to the volume, so rows far apart are
picked with Shift+arrows, Ctrl+A, or a filter and then Ctrl+A.

Several rows at once and the details pane are ideas from Andre Louis's
StreamSift (https://github.com/OnjLouis/StreamSift), written in QUILL's own
code.
"""

from __future__ import annotations

import urllib.parse
from collections.abc import Callable, Sequence
from typing import Any

from quill.core.radio import find_streams_view as view
from quill.core.radio.page_links import PageStreamCandidate
from quill.ui.dpi import dip
from quill.ui.spoken_name import set_spoken_name

__all__ = ["FindStreamsList", "details_text"]


def _status(candidate: PageStreamCandidate) -> str:
    if candidate.check == "live":
        return "Live stream"
    if candidate.check == "file":
        return "Audio file, not a live stream"
    note = candidate.check_note or "no answer"
    return f"Not checked: {note}"


def details_text(candidate: PageStreamCandidate) -> str:
    """The details field for one row: one fact per line."""
    parts = urllib.parse.urlsplit(candidate.url)
    name = candidate.stream_name or (candidate.label if candidate.label_is_name else "")
    fmt = candidate.codec or "Unknown"
    if candidate.bitrate_kbps:
        fmt = f"{fmt}, {candidate.bitrate_kbps} kbps"
    lines = [
        f"Name: {name or 'No name given'}",
        f"Status: {_status(candidate)}",
        f"Format: {fmt}",
    ]
    if candidate.listeners is not None:
        lines.append(f"Listeners: {candidate.listeners:,}")
    lines.append(f"Link: {candidate.url}")
    if parts.netloc:
        lines.append(f"Server: {parts.scheme}://{parts.netloc}")
    lines.append(f"Found by: {candidate.reason}")
    return "\n".join(lines)


class FindStreamsList:
    """The list, what it shows, and which rows the actions act on."""

    def __init__(
        self,
        parent: Any,
        wx: Any,
        sizer: Any,
        *,
        on_context_menu: Callable[[], None],
    ) -> None:
        self._wx = wx
        self._on_context_menu = on_context_menu
        self._candidates: list[PageStreamCandidate] = []
        self._shown: list[int] = []
        #: True while Select All or Find changes many rows at once: the dialog's
        #: selection handler skips its work then, and runs it once afterwards.
        self.quiet = False

        sizer.Add(wx.StaticText(parent, label="St&reams found"), 0, wx.LEFT | wx.TOP, 10)
        self.ctrl = wx.ListCtrl(parent, style=wx.LC_REPORT | wx.BORDER_SIMPLE)
        set_spoken_name(self.ctrl, "Streams found")
        self.ctrl.SetHelpText(
            "The stream links found on the page, live streams first. Enter tests the "
            "focused link. Select several with Shift and the arrow keys, or press Ctrl+A "
            "for every row shown; to pick rows far apart, filter the list first, then "
            "press Ctrl+A. Add to Favorites, Save as Playlist (Ctrl+S) and Copy (Ctrl+C) "
            "then act on all of them. Ctrl+F finds a row, F3 and Shift+F3 find the next "
            "and previous, Ctrl+Shift+O plays a random stream from the rows shown, and the "
            "Applications key opens the list's menu."
        )
        # The verdict first: it is what a screen reader reads first, and in
        # JAWS's first-column mode the only thing it reads.
        self.ctrl.InsertColumn(0, "Stream", width=dip(self.ctrl, 280))
        self.ctrl.InsertColumn(1, "Link", width=dip(self.ctrl, 300))
        self.ctrl.InsertColumn(2, "Found by", width=dip(self.ctrl, 140))
        sizer.Add(self.ctrl, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

        sizer.Add(wx.StaticText(parent, label="Stream &details"), 0, wx.LEFT | wx.TOP, 10)
        self.details = wx.TextCtrl(parent, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP)
        set_spoken_name(self.details, "Stream details")
        self.details.SetHelpText(
            "What QUILL knows about the focused stream, one fact per line: its name, "
            "whether it is live, its format, listeners, link, server, and how it was found. "
            "Read only."
        )
        self.details.SetMinSize((-1, dip(self.details, 90)))
        sizer.Add(self.details, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

        self.ctrl.Bind(wx.EVT_LIST_ITEM_FOCUSED, self._on_focused)
        self.ctrl.Bind(wx.EVT_CONTEXT_MENU, self._on_menu_key)

    # -- what is shown ---------------------------------------------------------

    @property
    def shown(self) -> list[int]:
        return list(self._shown)

    def __len__(self) -> int:
        return len(self._shown)

    def fill(
        self,
        candidates: Sequence[PageStreamCandidate],
        rows: Sequence[str],
        shown: Sequence[int],
        *,
        keep: str = "",
        keep_selected: bool = True,
    ) -> None:
        """Refill in one frozen pass, keeping focus and selection by address.

        *keep* is the focused stream's address; when it is no longer shown,
        focus goes to the first row. Nothing is spoken here.
        """
        selected = {c.url for c in self.selected_candidates()} if keep_selected else set()
        self._candidates = list(candidates)
        self._shown = list(shown)
        self.ctrl.Freeze()
        try:
            self.ctrl.DeleteAllItems()
            for row, index in enumerate(self._shown):
                candidate = self._candidates[index]
                self.ctrl.InsertItem(row, rows[index])
                self.ctrl.SetItem(row, 1, candidate.url)
                self.ctrl.SetItem(row, 2, candidate.reason)
            focus = 0
            for row, index in enumerate(self._shown):
                url = self._candidates[index].url
                if url == keep:
                    focus = row
                if url in selected:
                    self.ctrl.Select(row, True)
            if self._shown:
                if not selected & {self._candidates[i].url for i in self._shown}:
                    self.ctrl.Select(focus, True)
                self.ctrl.Focus(focus)
                self.ctrl.EnsureVisible(focus)
        finally:
            self.ctrl.Thaw()
        self._show_details()

    def clear(self) -> None:
        self.fill([], [], [])

    # -- which rows ------------------------------------------------------------

    def focused_position(self) -> int:
        row = int(self.ctrl.GetFocusedItem())
        return row if 0 <= row < len(self._shown) else -1

    def focused(self) -> PageStreamCandidate | None:
        row = self.focused_position()
        return self._candidates[self._shown[row]] if row >= 0 else None

    def selected_candidates(self) -> list[PageStreamCandidate]:
        out = []
        row = int(self.ctrl.GetFirstSelected())
        while 0 <= row < len(self._shown):
            out.append(self._candidates[self._shown[row]])
            row = int(self.ctrl.GetNextSelected(row))
        return out

    def targets(self) -> list[PageStreamCandidate]:
        """What Add, Save and Copy act on: the selection, or the focused row."""
        chosen = self.selected_candidates()
        if chosen:
            return chosen
        focused = self.focused()
        return [focused] if focused is not None else []

    def go_to(self, position: int) -> None:
        """Select and focus one shown row (Find), nothing else selected.

        Only the rows that are selected are deselected, quietly, so a long
        list does not send an event per row."""
        self.quiet = True
        try:
            selected = []
            row = int(self.ctrl.GetFirstSelected())
            while row >= 0:
                selected.append(row)
                row = int(self.ctrl.GetNextSelected(row))
            for row in selected:
                if row != position:
                    self.ctrl.Select(row, False)
            self.ctrl.Select(position, True)
            self.ctrl.Focus(position)
            self.ctrl.EnsureVisible(position)
        finally:
            self.quiet = False
        self._show_details()

    def select_all(self) -> bool:
        """Select every row shown, quietly; True when they all already were."""
        count = self.ctrl.GetItemCount()
        already = count > 0 and self.ctrl.GetSelectedItemCount() == count
        if already:
            return True
        self.quiet = True
        try:
            for row in range(count):
                self.ctrl.Select(row, True)
        finally:
            self.quiet = False
        return already

    def focused_rect(self) -> Any:
        """Where the context menu goes: the focused row, else the list's top."""
        wx = self._wx
        row = self.focused_position()
        if row >= 0:
            rect = self.ctrl.GetItemRect(row)
            return wx.Point(rect.x + dip(self.ctrl, 24), rect.y + rect.height // 2)
        return wx.Point(dip(self.ctrl, 24), dip(self.ctrl, 24))

    # -- events ----------------------------------------------------------------

    def _show_details(self) -> None:
        focused = self.focused()
        self.details.ChangeValue(details_text(focused) if focused is not None else "")

    def _on_focused(self, event: Any) -> None:
        self._show_details()
        event.Skip()

    def _on_menu_key(self, _event: Any) -> None:
        if self._shown:
            self._on_context_menu()


def view_rows(candidates: Sequence[PageStreamCandidate]) -> list[str]:
    """Each candidate's row text, made distinct (by candidate index)."""
    return view.distinct_rows(candidates)
