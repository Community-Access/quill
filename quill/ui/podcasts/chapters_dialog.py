"""Podcasts > (selected episode) > Chapters... -- browse and jump to an
episode's chapter markers (Podcasting 2.0 JSON chapters)."""

from __future__ import annotations

from collections.abc import Callable

from quill.core.podcasts.chapters import PodcastChapter
from quill.ui.dialog_contract import apply_modal_ids


def _format_timestamp(start_ms: int) -> str:
    total_seconds = start_ms // 1000
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


class ChaptersDialog:
    """Returns the selected chapter's start time in ms, or ``None`` on Cancel."""

    def __init__(
        self,
        parent: object,
        *,
        episode_title: str,
        chapters: list[PodcastChapter],
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._chapters = chapters
        self._announce = announce_cb or (lambda _m: None)
        self._result: int | None = None

        self.dialog = wx.Dialog(
            parent,
            title=f"Chapters -- {episode_title}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize((480, 420))
        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(wx.StaticText(self.dialog, label="&Chapters"), 0, wx.LEFT | wx.TOP, 10)
        self._list = wx.ListBox(self.dialog)
        self._list.SetName("Chapters for this episode; select one and press Jump to go there")
        for chapter in chapters:
            self._list.Append(f"{_format_timestamp(chapter.start_ms)} -- {chapter.title}")
        if chapters:
            self._list.SetSelection(0)
        root.Add(self._list, 1, wx.EXPAND | wx.ALL, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        jump_btn = wx.Button(self.dialog, wx.ID_OK, "&Jump To Chapter")
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Close")
        btn_row.AddStretchSpacer()
        btn_row.Add(jump_btn, 0, wx.RIGHT, 6)
        btn_row.Add(close_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)

        self._list.Bind(wx.EVT_LISTBOX_DCLICK, self._on_jump)
        jump_btn.Bind(wx.EVT_BUTTON, self._on_jump)

    def show(self) -> int | None:
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._wx.ID_OK,
            affirmative_label="Jump To Chapter",
            cancel_id=self._wx.ID_CANCEL,
            escape_id=self._wx.ID_CANCEL,
        )
        from quill.ui.dialog_contract import show_modal_dialog

        try:
            answer = show_modal_dialog(self.dialog, "Chapters", announce=self._announce)
            return self._result if answer == self._wx.ID_OK else None
        finally:
            self.dialog.Destroy()

    def _on_jump(self, _event: object) -> None:
        index = self._list.GetSelection()
        if 0 <= index < len(self._chapters):
            self._result = self._chapters[index].start_ms
            self.dialog.EndModal(self._wx.ID_OK)
