"""Clipboard: plain paste, numbered slots, a collector, and a history.

The system clipboard holds one thing. Everything here exists because that is one
fewer than people need, and because "hold on, let me go and copy that other bit
again" costs a listener a trip back through a document they cannot glance at.

Four features, each a different answer to the same problem, and all four built on
wx-free QUILL cores that already existed:

* **Paste as Plain Text** (Ctrl+Shift+V). Not a QUILL feature and not in
  WordPad either -- just the thing everybody expects and nobody has in a rich
  text editor. Pasting a web page into a document should be able to bring the
  words without the web page.
* **Copy Tray** (:class:`quill.core.copy_tray.CopyTray`). Twelve *numbered*
  slots that survive a restart. Copy to slot 3, paste from slot 3 an hour later.
  The same shape as the bookmarks, for the same reason: a number is a handle a
  person can hold.
* **The collector** (:func:`quill.core.clipboard_collector.append_collected`).
  Gathering: each copy is added to one growing buffer with a divider between,
  and pasted as a block when you are done. What you want when assembling five
  quotes out of a long document.
* **The clip library** (:class:`quill.core.clip_library.ClipLibrary`). The
  automatic tier under all of it: a rolling history of the last two hundred
  things copied, searchable, with the ones worth keeping marked as favourites.
  You do not have to have decided in advance that a copy mattered.

The tray and the library live in QuillLite's own data folder, like everything
else it stores.
"""

from __future__ import annotations

from typing import Any

import wx

from quill.apps.lite_dialogs import choose_from_rows
from quill.core.clipboard_collector import DEFAULT_DIVIDER, append_collected
from quill.core.fragment import Fragment

__all__ = ["DocumentClipboardMixin"]

#: How much of a slot or a clip is shown in a chooser row.
_PREVIEW_CHARS = 60


class DocumentClipboardMixin:
    """Paste-plain, the Copy Tray, the collector and the clip library."""

    # ------------------------------------------------------------------ #
    # The system clipboard
    # ------------------------------------------------------------------ #

    def _clipboard_text(self) -> str:
        """Whatever text is on the system clipboard, or "" -- never raises.

        The Windows clipboard is a shared, single-owner OS resource: opening it
        is a cross-process synchronisation point that can block behind a
        clipboard manager or a screen reader's own polling, and it can simply
        refuse. Every read here is guarded because a failed read must degrade to
        "nothing to paste", never to an error dialog.
        """
        data = wx.TextDataObject()
        try:
            if not wx.TheClipboard.Open():
                return ""
            try:
                got = wx.TheClipboard.GetData(data)
            finally:
                wx.TheClipboard.Close()
        except Exception:  # noqa: BLE001 - a clipboard read must never raise
            return ""
        return str(data.GetText()) if got else ""

    def _set_clipboard_text(self, text: str) -> bool:
        try:
            if not wx.TheClipboard.Open():
                return False
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(text))
            finally:
                wx.TheClipboard.Close()
        except Exception:  # noqa: BLE001
            return False
        return True

    def _selected_text(self) -> str:
        start, end = self.control.GetSelection()
        return str(self.control.GetValue()[start:end]) if end > start else ""

    def _insert(self, text: str) -> None:
        """Put *text* in at the caret, replacing the selection, as one undo step."""
        if not text:
            return
        start, end = self.control.GetSelection()
        if end > start:
            self.control.Replace(start, end, text)
        else:
            self.control.WriteText(text)
        self._set_modified(True)
        self._touch_status()

    def cmd_paste_plain(self) -> None:
        """Paste the clipboard's text with none of its formatting."""
        text = self._clipboard_text()
        if not text:
            self._announce("The clipboard has no text")
            return
        self._insert(text)
        self._announce(f"Pasted {len(text):,} characters as plain text")

    # ------------------------------------------------------------------ #
    # Copy Tray
    # ------------------------------------------------------------------ #

    def cmd_copy_to_tray(self) -> None:
        """Copy the selection into the first free tray slot, or slot 1 when full."""
        text = self._selected_text()
        if not text:
            self._announce("Select something to copy first")
            return
        tray = self.app.copy_tray
        slot = next(
            (n for n in range(1, tray.SLOT_COUNT + 1) if tray.slot(n).is_empty()),
            1,
        )
        tray.copy_to(slot, text)
        self._announce(f"Copied to tray slot {slot}: {tray.slot(slot).preview(40)}")

    def cmd_paste_from_tray(self) -> None:
        """Choose a numbered slot and paste it."""
        tray = self.app.copy_tray
        rows = [
            (n, f"Slot {n}: {tray.slot(n).preview(_PREVIEW_CHARS)}")
            for n in range(1, tray.SLOT_COUNT + 1)
            if not tray.slot(n).is_empty()
        ]
        if not rows:
            self._announce("The copy tray is empty. Control Shift 0 copies into it.")
            return
        chosen = choose_from_rows(
            self,
            title="Copy Tray",
            label="&Slots you have copied into:",
            help_text="Choose a slot and press Enter to paste it into your document.",
            rows=rows,
        )
        if chosen is None:
            self.control.SetFocus()
            return
        self._insert(tray.slot(int(chosen)).text)
        self.control.SetFocus()
        self._announce(f"Pasted tray slot {chosen}")

    def cmd_clear_copy_tray(self) -> None:
        self.app.copy_tray.clear_all()
        self._announce("Copy tray cleared")

    # ------------------------------------------------------------------ #
    # The collector
    # ------------------------------------------------------------------ #

    def cmd_collect_selection(self) -> None:
        """Add the selection to the collector, keeping what is already there."""
        text = self._selected_text()
        if not text:
            self._announce("Select something to collect first")
            return
        self.app.collected = append_collected(self.app.collected, text, divider=DEFAULT_DIVIDER)
        pieces = self.app.collected.count(DEFAULT_DIVIDER) + 1
        self._announce(f"Collected {pieces} piece{'s' if pieces != 1 else ''}")

    def cmd_paste_collected(self) -> None:
        """Paste everything collected so far, in the order it was collected."""
        if not self.app.collected:
            self._announce("Nothing collected yet")
            return
        self._insert(self.app.collected)
        self._announce(f"Pasted {len(self.app.collected):,} collected characters")

    def cmd_clear_collected(self) -> None:
        self.app.collected = ""
        self._announce("Collector cleared")

    # ------------------------------------------------------------------ #
    # The clip library
    # ------------------------------------------------------------------ #

    def cmd_remember_clip(self) -> None:
        """Keep the selection in the library deliberately, not just by copying."""
        text = self._selected_text()
        if not text:
            self._announce("Select something to keep first")
            return
        if self.app.clip_library.remember(Fragment(markup=text, source="QuillLite")):
            self._announce("Kept in the clip library")
        else:
            self._announce("That is already in the clip library")

    def cmd_paste_clip(self) -> None:
        """Choose from everything copied recently and paste it."""
        entries = self.app.clip_library.all_entries()
        if not entries:
            self._announce("The clip library is empty")
            return
        rows = [
            (index, f"{'Favourite: ' if entry.favorite else ''}{entry.preview(_PREVIEW_CHARS)}")
            for index, entry in entries
        ]
        chosen = choose_from_rows(
            self,
            title="Clip Library",
            label="&Recently copied:",
            help_text=(
                "Everything copied recently, newest first. A star marks a favourite. "
                "Choose one and press Enter to paste it."
            ),
            rows=rows,
        )
        if chosen is None:
            self.control.SetFocus()
            return
        self._insert(self.app.clip_library.entry(int(chosen)).fragment.markup)
        self.control.SetFocus()
        self._announce("Pasted from the clip library")

    def _remember_copy(self, text: str) -> None:
        """Called after a Copy or Cut, so the library fills without being asked.

        The automatic tier: you do not have to have decided in advance that a
        copy mattered. Failures are swallowed -- a clip library that cannot
        write must not be able to break Ctrl+C.
        """
        library: Any = getattr(self.app, "clip_library", None)
        if library is None or not text.strip():
            return
        try:
            library.remember(Fragment(markup=text, source="QuillLite"))
        except Exception:  # noqa: BLE001 - remembering is never worth an error
            pass
