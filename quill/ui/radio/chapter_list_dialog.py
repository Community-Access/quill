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

Chapters reach this dialog three ways and it says which: the uploader's own,
captured during the resolve; the file's chapter frames, for a recording or a
downloaded episode; or a list QUILL Cast worked out earlier and left in the
shared cache. Radio never works any out itself -- see
:mod:`quill.core.radio.chapter_lookup`.

**Preview, where there is a local file.** Playing forward from a mark tells you
what the section is about; it does not tell you whether the mark is in the right
*place*. So Preview plays a few seconds either side of the boundary, through its
own player, and **your place in what you were listening to does not move** --
which is the only reason checking a mark is cheap enough that anybody does it.
Streams have no file to cut, so the buttons are simply absent rather than
present and inert.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from quill.ui.dialog_contract import apply_modal_ids
from quill.ui.radio.bounded_playback_ui import describe_chapter

#: How much is played either side of a mark. Ten seconds is long enough to hear
#: the turn and short enough that checking six marks is not a chore.
PREVIEW_SECONDS = 10


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
        transport_host: object | None = None,
        audio_path: Path | None = None,
        source_label: str = "published by the uploader",
    ) -> None:
        import wx

        self._wx = wx
        self._transport_host = transport_host
        self._source_label = source_label
        self._preview: Any = None
        if audio_path is not None and audio_path.is_file():
            from quill.ui.media.chapter_preview import ChapterPreviewPlayer

            player = ChapterPreviewPlayer(audio_path)
            self._preview = player if player.is_available else None
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
            label=f"{count} chapter{'' if count == 1 else 's'}, {self._source_label}.",
        )
        root.Add(summary, 0, wx.ALL, 8)

        label = wx.StaticText(panel, label="&Chapters:")
        root.Add(label, 0, wx.LEFT, 8)
        self._list = wx.ListBox(panel, choices=self._labels(), style=wx.LB_SINGLE)
        self._list.SetName("Chapters in this video")
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        hint_text = "Press Enter or Go To to jump. The list stays open so you can keep exploring."
        if self._preview is not None:
            hint_text += (
                f" Preview plays {PREVIEW_SECONDS} seconds either side of a mark "
                "without moving your place."
            )
        hint = wx.StaticText(panel, label=hint_text)
        root.Add(hint, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        row = wx.BoxSizer(wx.HORIZONTAL)
        self._go_btn = wx.Button(panel, label="&Go To")
        row.Add(self._go_btn, 0, wx.RIGHT, 6)
        if self._preview is not None:
            self._preview_btn = wx.Button(panel, label="&Preview This Mark")
            self._preview_btn.SetName(
                f"Play {PREVIEW_SECONDS} seconds either side of the selected mark, "
                "then stop. Your place is not changed."
            )
            stop_btn = wx.Button(panel, label="&Stop Preview")
            row.Add(self._preview_btn, 0, wx.RIGHT, 6)
            row.Add(stop_btn, 0, wx.RIGHT, 6)
            self._preview_btn.Bind(wx.EVT_BUTTON, lambda _e: self._preview_mark())
            stop_btn.Bind(wx.EVT_BUTTON, lambda _e: self._stop_preview())
        close_btn = wx.Button(panel, wx.ID_CLOSE, label="C&lose")
        row.Add(close_btn, 0, wx.RIGHT, 6)
        root.Add(row, 0, wx.ALL, 8)

        apply_modal_ids(
            self.dialog,
            affirmative_id=close_btn.GetId(),
            escape_id=close_btn.GetId(),
        )
        # The transport keyboard, when the surface that opened this one knows
        # about the player. It was installed in the browse tree and nowhere
        # else, so every other Radio dialog was a window where the keys that
        # work everywhere stopped working.
        if self._transport_host is not None:
            from quill.ui.radio import transport_keys

            transport_keys.install(self.dialog, self._transport_host, wx=wx)

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

    def _preview_mark(self) -> None:
        """Hear the moment either side of the selected mark. Never moves the player."""
        index = self._list.GetSelection()
        if index < 0 or self._preview is None:
            return
        start_ms = int(getattr(self._chapters[index], "start_ms", 0) or 0)
        span = PREVIEW_SECONDS * 1000
        self._preview.play_range(max(0, start_ms - span), start_ms + span)
        title = str(getattr(self._chapters[index], "title", "") or "").strip()
        self._announce(f"Previewing {title or 'this mark'}.")

    def _stop_preview(self) -> None:
        if self._preview is None:
            return
        self._preview.stop()
        self._announce("Preview stopped.")

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
            # A preview still playing after the window closed would be a sound
            # with no visible source and no way to stop it.
            if self._preview is not None:
                self._preview.close()
            self.dialog.Destroy()
