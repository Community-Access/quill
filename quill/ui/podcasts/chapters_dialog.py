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
        source_label: str = "",
        skip_state: object = None,
    ) -> None:
        import wx

        self._wx = wx
        self._chapters = chapters
        self._announce = announce_cb or (lambda _m: None)
        self._result: int | None = None
        #: The playing episode's ChapterSkipState, when this dialog was opened
        #: for the episode that is actually playing. None means marking is not
        #: on offer -- there is nothing to skip past in an episode you are not
        #: listening to, and a mark that quietly applied later would be worse
        #: than no mark at all.
        self._skip_state = skip_state

        self.dialog = wx.Dialog(
            parent,
            title=f"Chapters -- {episode_title}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize((480, 420))
        root = wx.BoxSizer(wx.VERTICAL)

        # Where the chapters came from is part of the label, not a footnote:
        # marks read out of the show notes must never be mistaken for the
        # publisher's own.
        heading = f"&Chapters -- {source_label}" if source_label else "&Chapters"
        root.Add(wx.StaticText(self.dialog, label=heading), 0, wx.LEFT | wx.TOP, 10)
        self._list = wx.ListBox(self.dialog)
        self._list.SetName(
            f"Chapters for this episode ({source_label}); select one and press Jump to go there"
            if source_label
            else "Chapters for this episode; select one and press Jump to go there"
        )
        self._refill()
        if chapters:
            self._list.SetSelection(0)
        root.Add(self._list, 1, wx.EXPAND | wx.ALL, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        jump_btn = wx.Button(self.dialog, wx.ID_OK, "&Jump To Chapter")
        self._skip_btn = wx.Button(self.dialog, label="&Skip This Chapter")
        self._skip_btn.SetName(
            "Mark the selected chapter to be skipped. Playback jumps past it and "
            "says so. Marks last for this listening session only."
        )
        self._skip_btn.Enable(skip_state is not None and bool(chapters))
        clear_btn = wx.Button(self.dialog, label="Skip &Nothing")
        clear_btn.SetName("Unmark every chapter")
        clear_btn.Enable(skip_state is not None and bool(chapters))
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Close")
        btn_row.Add(self._skip_btn, 0, wx.RIGHT, 6)
        btn_row.Add(clear_btn, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(jump_btn, 0, wx.RIGHT, 6)
        btn_row.Add(close_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)

        self._list.Bind(wx.EVT_LISTBOX_DCLICK, self._on_jump)
        self._list.Bind(wx.EVT_LISTBOX, lambda _e: self._sync_skip_button())
        jump_btn.Bind(wx.EVT_BUTTON, self._on_jump)
        self._skip_btn.Bind(wx.EVT_BUTTON, self._on_toggle_skip)
        clear_btn.Bind(wx.EVT_BUTTON, self._on_clear_skips)
        self._sync_skip_button()

    def _is_skipped(self, index: int) -> bool:
        return self._skip_state is not None and index in self._skip_state.skipped

    def _refill(self) -> None:
        """Rebuild the list; a skipped chapter says so in its own label.

        In its label, not by colour or an icon: "skipped" has to survive being
        read aloud, which is the only form some listeners will ever get it in.
        """
        selection = self._list.GetSelection()
        self._list.Clear()
        for index, chapter in enumerate(self._chapters):
            suffix = " -- skipped" if self._is_skipped(index) else ""
            self._list.Append(f"{_format_timestamp(chapter.start_ms)} -- {chapter.title}{suffix}")
        if 0 <= selection < self._list.GetCount():
            self._list.SetSelection(selection)

    def _sync_skip_button(self) -> None:
        index = self._list.GetSelection()
        if self._skip_state is None or not (0 <= index < len(self._chapters)):
            return
        self._skip_btn.SetLabel(
            "Stop &Skipping This Chapter" if self._is_skipped(index) else "&Skip This Chapter"
        )

    def _on_toggle_skip(self, _event: object) -> None:
        index = self._list.GetSelection()
        if self._skip_state is None or not (0 <= index < len(self._chapters)):
            return
        now_skipped = self._skip_state.toggle(index)
        title = self._chapters[index].title
        self._refill()
        self._sync_skip_button()
        self._announce(f"Skipping {title}" if now_skipped else f"No longer skipping {title}")

    def _on_clear_skips(self, _event: object) -> None:
        if self._skip_state is None:
            return
        self._skip_state.clear()
        self._refill()
        self._sync_skip_button()
        self._announce("No chapters are being skipped")

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
