"""Review Chapters: check every worked-out mark, and fix the ones that are wrong.

An inferred chapter list is a **claim**, and until now there was no way to check
one. A sighted listener glances at a waveform and sees where the quiet is; this
dialog is the equivalent, and it is the reason offering inferred chapters is
defensible at all.

Three things it has to do, and they are all the same thing:

* **Play the mark, not the chapter.** Preview plays a few seconds *before* the
  boundary and a few seconds *after* it. That is the only way to answer "does the
  programme turn here" -- playing forward from the mark tells you what the
  section is about, not whether the mark is in the right place.
* **Never lose your place.** Preview uses its own player and stops on its own.
  The episode you were listening to is exactly where you left it.
* **Say what each row is.** Position, time, length, title, and how it was arrived
  at, all in the row's own text, because that is the only form some listeners
  will ever receive it in. A list that mixes published marks, worked-out ones and
  your own corrections has to say which is which without a properties dialog.

Editing is deliberately blunt and keyboard-first: rename, retime, nudge, add,
delete. **Nudge is the important one** -- an inferred mark is usually a few
seconds off rather than in the wrong place entirely, and if correcting that costs
more than one keystroke nobody will do it.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.podcasts import chapter_edits
from quill.core.podcasts.chapter_edits import ChapterEditError
from quill.core.podcasts.chapters import PodcastChapter
from quill.ui.dialog_contract import apply_modal_ids

#: How far one nudge moves a mark. Five seconds is about a sentence -- small
#: enough to land on the turn, big enough to be worth a keystroke.
NUDGE_MS = 5_000


class ChapterReviewDialog:
    """Returns the edited chapter list on Save, or ``None`` if nothing was kept."""

    def __init__(
        self,
        parent: object,
        *,
        episode_title: str,
        chapters: list[PodcastChapter],
        total_ms: int,
        preview_seconds: int = 10,
        summary: str = "",
        play_range: Callable[[int, int], None] | None = None,
        stop_preview: Callable[[], None] | None = None,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._total_ms = int(total_ms)
        self._preview_seconds = max(3, int(preview_seconds))
        self._play_range = play_range
        self._stop_preview = stop_preview
        self._announce = announce_cb or (lambda _m: None)
        self._chapters = chapter_edits.normalise(list(chapters), self._total_ms)
        self._result: list[PodcastChapter] | None = None

        self.dialog = wx.Dialog(
            parent,
            title=f"Review Chapters -- {episode_title}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize((640, 520))
        root = wx.BoxSizer(wx.VERTICAL)

        self._summary = wx.StaticText(
            self.dialog, label=summary or chapter_edits.summarise(self._chapters)
        )
        root.Add(self._summary, 0, wx.LEFT | wx.TOP | wx.RIGHT, 10)

        root.Add(wx.StaticText(self.dialog, label="&Chapters:"), 0, wx.LEFT | wx.TOP, 10)
        self._list = wx.ListBox(self.dialog)
        self._list.SetName(
            "Chapters found in this episode. Each row says its position, time, "
            "length, title, and how it was worked out. Press Preview to hear the "
            "moment either side of a mark."
        )
        root.Add(self._list, 1, wx.EXPAND | wx.ALL, 10)

        # Preview first, and it is the default action: the whole point of the
        # dialog is checking, and the thing you do most should be Enter.
        top_row = wx.BoxSizer(wx.HORIZONTAL)
        self._preview_btn = wx.Button(self.dialog, label="&Preview This Mark")
        self._preview_btn.SetName(
            f"Play {self._preview_seconds} seconds either side of the selected "
            "mark, then stop. Your place in the episode is not changed."
        )
        stop_btn = wx.Button(self.dialog, label="&Stop Preview")
        top_row.Add(self._preview_btn, 0, wx.RIGHT, 6)
        top_row.Add(stop_btn, 0, wx.RIGHT, 6)
        root.Add(top_row, 0, wx.LEFT | wx.RIGHT, 10)

        edit_row = wx.BoxSizer(wx.HORIZONTAL)
        rename_btn = wx.Button(self.dialog, label="Re&name...")
        time_btn = wx.Button(self.dialog, label="Set &Time...")
        back_btn = wx.Button(self.dialog, label="Nudge &Earlier")
        fwd_btn = wx.Button(self.dialog, label="Nudge &Later")
        for button in (rename_btn, time_btn, back_btn, fwd_btn):
            edit_row.Add(button, 0, wx.RIGHT, 6)
        root.Add(edit_row, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)

        add_row = wx.BoxSizer(wx.HORIZONTAL)
        add_btn = wx.Button(self.dialog, label="&Add Chapter Here...")
        delete_btn = wx.Button(self.dialog, label="&Delete Chapter")
        add_row.Add(add_btn, 0, wx.RIGHT, 6)
        add_row.Add(delete_btn, 0, wx.RIGHT, 6)
        add_row.AddStretchSpacer()
        save_btn = wx.Button(self.dialog, wx.ID_OK, "Sa&ve Chapters")
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        add_row.Add(save_btn, 0, wx.RIGHT, 6)
        add_row.Add(close_btn)
        root.Add(add_row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)

        self._preview_btn.Bind(wx.EVT_BUTTON, self._on_preview)
        stop_btn.Bind(wx.EVT_BUTTON, self._on_stop)
        rename_btn.Bind(wx.EVT_BUTTON, self._on_rename)
        time_btn.Bind(wx.EVT_BUTTON, self._on_set_time)
        back_btn.Bind(wx.EVT_BUTTON, lambda _e: self._nudge(-NUDGE_MS))
        fwd_btn.Bind(wx.EVT_BUTTON, lambda _e: self._nudge(NUDGE_MS))
        add_btn.Bind(wx.EVT_BUTTON, self._on_add)
        delete_btn.Bind(wx.EVT_BUTTON, self._on_delete)
        save_btn.Bind(wx.EVT_BUTTON, self._on_save)
        self._list.Bind(wx.EVT_LISTBOX_DCLICK, self._on_preview)
        self._list.Bind(wx.EVT_LISTBOX, self._on_select)

        self._refill(select=0)

    # -- list ------------------------------------------------------------- #

    def _refill(self, *, select: int | None = None) -> None:
        keep = self._list.GetSelection() if select is None else select
        self._list.Clear()
        count = len(self._chapters)
        for index, chapter in enumerate(self._chapters):
            self._list.Append(chapter_edits.row_label(chapter, index, count))
        if count:
            self._list.SetSelection(max(0, min(keep if keep is not None else 0, count - 1)))
        self._summary.SetLabel(chapter_edits.summarise(self._chapters))
        for button in (self._preview_btn,):
            button.Enable(bool(count) and self._play_range is not None)

    def _selected(self) -> int:
        index = self._list.GetSelection()
        return index if 0 <= index < len(self._chapters) else -1

    def _on_select(self, _event: object) -> None:
        index = self._selected()
        if index >= 0:
            self._announce(
                chapter_edits.row_label(self._chapters[index], index, len(self._chapters))
            )

    def _apply(self, rows: list[PodcastChapter], index: int, said: str) -> None:
        self._chapters = rows
        self._refill(select=index)
        self._announce(said)

    def _guard(self, action: Callable[[], None]) -> None:
        """Run an edit; a refusal is spoken rather than raised at the listener."""
        try:
            action()
        except ChapterEditError as error:
            self._announce(str(error))

    # -- preview ---------------------------------------------------------- #

    def _on_preview(self, _event: object) -> None:
        index = self._selected()
        if index < 0 or self._play_range is None:
            self._announce("Select a chapter first.")
            return
        chapter = self._chapters[index]
        start, end = chapter_edits.preview_window(
            chapter, total_ms=self._total_ms, lead_seconds=self._preview_seconds
        )
        self._announce(
            f"Playing {self._preview_seconds} seconds either side of "
            f"{chapter_edits.clock(chapter.start_ms)}."
        )
        self._play_range(start, end)

    def _on_stop(self, _event: object) -> None:
        if self._stop_preview is not None:
            self._stop_preview()
        self._announce("Preview stopped.")

    # -- edits ------------------------------------------------------------ #

    def _on_rename(self, _event: object) -> None:
        index = self._selected()
        if index < 0:
            self._announce("Select a chapter first.")
            return
        current = self._chapters[index].title
        with self._wx.TextEntryDialog(
            self.dialog, "Chapter title:", "Rename Chapter", current
        ) as prompt:
            if prompt.ShowModal() != self._wx.ID_OK:
                return
            wanted = prompt.GetValue()
        self._guard(
            lambda: self._apply(
                chapter_edits.retitle(self._chapters, index, wanted, total_ms=self._total_ms),
                index,
                f"Renamed to {' '.join(wanted.split())}.",
            )
        )

    def _on_set_time(self, _event: object) -> None:
        index = self._selected()
        if index < 0:
            self._announce("Select a chapter first.")
            return
        current = chapter_edits.clock(self._chapters[index].start_ms)
        with self._wx.TextEntryDialog(
            self.dialog, "Start time (for example 12:34 or 1:02:03):", "Set Time", current
        ) as prompt:
            if prompt.ShowModal() != self._wx.ID_OK:
                return
            wanted = prompt.GetValue()

        def _run() -> None:
            at_ms = chapter_edits.parse_clock(wanted)
            rows = chapter_edits.retime(self._chapters, index, at_ms, total_ms=self._total_ms)
            landed = next(
                (position for position, c in enumerate(rows) if c.start_ms == at_ms), index
            )
            self._apply(rows, landed, f"Moved to {chapter_edits.clock(at_ms)}.")

        self._guard(_run)

    def _nudge(self, delta_ms: int) -> None:
        index = self._selected()
        if index < 0:
            self._announce("Select a chapter first.")
            return

        def _run() -> None:
            rows = chapter_edits.nudge(self._chapters, index, delta_ms, total_ms=self._total_ms)
            wanted = self._chapters[index].start_ms + delta_ms
            landed = next(
                (position for position, c in enumerate(rows) if c.start_ms == max(0, wanted)),
                index,
            )
            self._apply(rows, landed, chapter_edits.clock(rows[landed].start_ms))

        self._guard(_run)

    def _on_add(self, _event: object) -> None:
        index = self._selected()
        suggested = chapter_edits.clock(self._chapters[index].start_ms if index >= 0 else 0)
        with self._wx.TextEntryDialog(
            self.dialog, "New chapter starts at (for example 12:34):", "Add Chapter", suggested
        ) as prompt:
            if prompt.ShowModal() != self._wx.ID_OK:
                return
            when = prompt.GetValue()
        with self._wx.TextEntryDialog(
            self.dialog, "Chapter title:", "Add Chapter", "New chapter"
        ) as prompt:
            if prompt.ShowModal() != self._wx.ID_OK:
                return
            title = prompt.GetValue()

        def _run() -> None:
            at_ms = chapter_edits.parse_clock(when)
            rows = chapter_edits.insert(self._chapters, at_ms, title, total_ms=self._total_ms)
            landed = next((position for position, c in enumerate(rows) if c.start_ms == at_ms), 0)
            self._apply(rows, landed, f"Added at {chapter_edits.clock(at_ms)}.")

        self._guard(_run)

    def _on_delete(self, _event: object) -> None:
        index = self._selected()
        if index < 0:
            self._announce("Select a chapter first.")
            return
        title = self._chapters[index].title
        self._guard(
            lambda: self._apply(
                chapter_edits.remove(self._chapters, index, total_ms=self._total_ms),
                max(0, index - 1),
                f"Removed {title}.",
            )
        )

    # -- close ------------------------------------------------------------ #

    def _on_save(self, _event: object) -> None:
        self._result = list(self._chapters)
        self.dialog.EndModal(self._wx.ID_OK)

    def show(self) -> list[PodcastChapter] | None:
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._wx.ID_OK,
            affirmative_label="Save Chapters",
            cancel_id=self._wx.ID_CANCEL,
            escape_id=self._wx.ID_CANCEL,
        )
        from quill.ui.dialog_contract import show_modal_dialog

        try:
            answer = show_modal_dialog(self.dialog, "Review Chapters", announce=self._announce)
            return self._result if answer == self._wx.ID_OK else None
        finally:
            if self._stop_preview is not None:
                self._stop_preview()
            self.dialog.Destroy()
