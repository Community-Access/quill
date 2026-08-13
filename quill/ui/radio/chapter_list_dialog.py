"""Jump between a video's published chapters.

The same accessibility shape as the playlist picker: a plain ``wx.ListBox``
whose every row already says everything about that chapter ("2. The problem,
starts at 1 minute"), so a screen reader reads one line instead of the user
arrowing across columns. Times are spelled in words, because a bare
colon-separated number read aloud is ambiguous.

Two details that matter more than they look:

* The chapter currently playing is **selected when the dialog opens** and says
  "playing now" in its own label. Opening a chapter list and landing on row one
  when you are twelve minutes in tells you nothing about where you are.
* The dialog does not close when you jump. Chapter lists are used to *explore*
  -- hearing the start of one section and moving on -- and closing after every
  jump would mean reopening it each time.

These are the uploader's own chapters, captured during the resolve; nothing
here is guessed.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from quill.ui.dialog_contract import apply_modal_ids
from quill.ui.radio.bounded_playback_ui import describe_chapter


class ChapterListDialog:
    """Choose a chapter of the playing video and jump to it."""

    def __init__(
        self,
        parent: object,
        *,
        chapters: Sequence[Any],
        current_index: int,
        show_modal_dialog: Callable,
        announce: Callable[[str], None],
        go_to_chapter: Callable[[int], bool],
    ) -> None:
        import wx

        self._wx = wx
        self._chapters = list(chapters)
        self._current = current_index
        self._announce = announce
        self._go_to_chapter = go_to_chapter
        self._show_modal = show_modal_dialog
        self._title = "Chapters"

        self.dialog = wx.Dialog(
            parent,
            title=self._title,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize(wx.Size(560, 420))
        self._build_ui()

    def _build_ui(self) -> None:
        wx = self._wx
        panel = self.dialog
        root = wx.BoxSizer(wx.VERTICAL)

        count = len(self._chapters)
        summary = wx.StaticText(
            panel,
            label=f"{count} chapter{'' if count == 1 else 's'}, published by the uploader.",
        )
        root.Add(summary, 0, wx.ALL, 8)

        label = wx.StaticText(panel, label="&Chapters:")
        root.Add(label, 0, wx.LEFT, 8)
        self._list = wx.ListBox(panel, choices=self._labels(), style=wx.LB_SINGLE)
        self._list.SetName("Chapters in this video")
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        hint = wx.StaticText(
            panel,
            label="Press Enter or Go To to jump. The list stays open so you can keep exploring.",
        )
        root.Add(hint, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        row = wx.BoxSizer(wx.HORIZONTAL)
        self._go_btn = wx.Button(panel, label="&Go To")
        close_btn = wx.Button(panel, wx.ID_CLOSE, label="C&lose")
        for button in (self._go_btn, close_btn):
            row.Add(button, 0, wx.RIGHT, 6)
        root.Add(row, 0, wx.ALL, 8)

        apply_modal_ids(
            self.dialog,
            affirmative_id=close_btn.GetId(),
            escape_id=close_btn.GetId(),
        )
        self.dialog.SetSizer(root)

        self._go_btn.Bind(wx.EVT_BUTTON, lambda _e: self._jump())
        self._list.Bind(wx.EVT_LISTBOX_DCLICK, lambda _e: self._jump())
        close_btn.Bind(wx.EVT_BUTTON, lambda _e: self.dialog.EndModal(wx.ID_CLOSE))

        # Land on the chapter actually playing, not row one: opening this
        # twelve minutes in and being put at the top says nothing about
        # where you are.
        start = self._current if 0 <= self._current < len(self._chapters) else 0
        if self._chapters:
            self._list.SetSelection(start)
        wx.CallAfter(self._list.SetFocus)

    def _labels(self) -> list[str]:
        return [
            describe_chapter(index, chapter, current=index == self._current)
            for index, chapter in enumerate(self._chapters)
        ]

    def _jump(self) -> None:
        index = self._list.GetSelection()
        if index < 0:
            return
        if not self._go_to_chapter(index):
            self._announce("That chapter could not be played.")
            return
        self._current = index
        # Re-label so "playing now" follows the jump, keeping the list an
        # accurate picture of where playback is.
        selection = self._list.GetSelection()
        self._list.Set(self._labels())
        self._list.SetSelection(selection)
        title = str(getattr(self._chapters[index], "title", "") or "").strip()
        self._announce(f"{title or 'Chapter'}, chapter {index + 1} of {len(self._chapters)}.")

    def show(self) -> None:
        try:
            self._show_modal(self.dialog, self._title)
        finally:
            self.dialog.Destroy()
