"""Copy Sections: mark pieces of a recording, and collect them into one file.

The window behind **Copy Sections...** in Audio Studio. Trimming one piece out of
a file has worked for a long time; what this adds is the part that makes it
usable -- marking while you listen, hearing what you marked *before* committing
to it, and adding a second and a third piece to the same output.

That collecting is the feature. Pulling four quotes out of a two-hour interview
is not four trims and a stitch; it is one task, and every editor that offers
"trim" without "and another one" makes you do the stitching yourself.

The shape is deliberately the one Quill already uses for this kind of work: a
list where **every row is a whole sentence** rather than a set of columns, plain
buttons with real labels, and nothing that requires a pointer. There is no
waveform, and its absence is not an apology -- a waveform is a picture of the
audio for people who can see it, and the same job is done here by listening to
the marked range, which is the more reliable check for everybody.

Three rules, and the first is the point:

* **The source file is never modified.** Marks are numbers; saving writes
  somewhere else. There is no destructive edit, so there is nothing to undo.
* **Preview before you keep it.** Every marked range can be played back before it
  is added, and every collected section can be played again from the list.
* **Nothing is silent.** Marking, previewing, adding, removing and saving each
  say what happened and where -- in words, never as a pair of numbers.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.audio.sections import (
    SectionCollection,
    SectionMarks,
    describe_marks,
    save_sections,
)
from quill.ui.dialog_contract import apply_modal_ids


class CopySectionsDialog:
    """Mark, preview, collect and save pieces of the playing file."""

    def __init__(
        self,
        parent: Any,
        *,
        source: Path,
        playhead_ms: Callable[[], int],
        play_range: Callable[[int, int], None] | None = None,
        announce: Callable[[str], None] | None = None,
        show_modal_dialog: Callable[[Any, str], int] | None = None,
        work_dir: Path | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._source = source
        self._playhead_ms = playhead_ms
        self._play_range = play_range
        self._announce = announce or (lambda _m: None)
        self._show_modal_dialog = show_modal_dialog
        self._work_dir = work_dir
        self._marks = SectionMarks()
        self._collection = SectionCollection()

        self._dialog = wx.Dialog(
            parent,
            title=f"Copy Sections -- {source.name}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(
            wx.StaticText(
                self._dialog,
                label=(
                    "Play the file and mark where a section starts and ends.\n"
                    "The original is never changed."
                ),
            ),
            0,
            wx.ALL,
            10,
        )

        marks_row = wx.BoxSizer(wx.HORIZONTAL)
        self._mark_start_btn = wx.Button(self._dialog, label="Mark &Start")
        self._mark_end_btn = wx.Button(self._dialog, label="Mark &End")
        self._preview_btn = wx.Button(self._dialog, label="&Preview Marked")
        self._add_btn = wx.Button(self._dialog, label="&Add to List")
        for button in (self._mark_start_btn, self._mark_end_btn, self._preview_btn, self._add_btn):
            marks_row.Add(button, 0, wx.RIGHT, 6)
        root.Add(marks_row, 0, wx.LEFT | wx.RIGHT, 10)

        self._marks_text = wx.StaticText(self._dialog, label=describe_marks(self._marks))
        self._marks_text.SetName("What is marked")
        root.Add(self._marks_text, 0, wx.ALL, 10)

        root.Add(wx.StaticText(self._dialog, label="Sections to sa&ve:"), 0, wx.LEFT | wx.RIGHT, 10)
        self._list = wx.ListBox(self._dialog, choices=[])
        self._list.SetName("Collected sections, in the order they will be saved")
        root.Add(self._list, 1, wx.EXPAND | wx.ALL, 10)

        list_row = wx.BoxSizer(wx.HORIZONTAL)
        self._play_btn = wx.Button(self._dialog, label="P&lay This One")
        self._remove_btn = wx.Button(self._dialog, label="&Remove")
        self._up_btn = wx.Button(self._dialog, label="Move &Up")
        self._down_btn = wx.Button(self._dialog, label="Move &Down")
        for button in (self._play_btn, self._remove_btn, self._up_btn, self._down_btn):
            list_row.Add(button, 0, wx.RIGHT, 6)
        root.Add(list_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._total = wx.StaticText(self._dialog, label=self._collection.describe())
        self._total.SetName("How much is collected")
        root.Add(self._total, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._save_btn = wx.Button(self._dialog, label="Save as &New File...")
        self._append_btn = wx.Button(self._dialog, label="Add to an E&xisting File...")
        buttons.Add(self._save_btn, 0, wx.RIGHT, 6)
        buttons.Add(self._append_btn, 0, wx.RIGHT, 6)
        buttons.Add(wx.Button(self._dialog, wx.ID_CANCEL, "&Close"), 0)
        root.Add(buttons, 0, wx.ALL, 10)

        self._dialog.SetSizer(root)
        self._dialog.SetMinSize((620, 460))
        apply_modal_ids(self._dialog, cancel_id=wx.ID_CANCEL)

        self._mark_start_btn.Bind(wx.EVT_BUTTON, lambda _e: self.mark_start())
        self._mark_end_btn.Bind(wx.EVT_BUTTON, lambda _e: self.mark_end())
        self._preview_btn.Bind(wx.EVT_BUTTON, lambda _e: self.preview())
        self._add_btn.Bind(wx.EVT_BUTTON, lambda _e: self.add_marked())
        self._play_btn.Bind(wx.EVT_BUTTON, lambda _e: self.play_selected())
        self._remove_btn.Bind(wx.EVT_BUTTON, lambda _e: self.remove_selected())
        self._up_btn.Bind(wx.EVT_BUTTON, lambda _e: self.move_selected(-1))
        self._down_btn.Bind(wx.EVT_BUTTON, lambda _e: self.move_selected(1))
        self._save_btn.Bind(wx.EVT_BUTTON, lambda _e: self.save(append=False))
        self._append_btn.Bind(wx.EVT_BUTTON, lambda _e: self.save(append=True))
        self._refresh()

    # -- the window ------------------------------------------------------------

    @property
    def dialog(self) -> Any:
        return self._dialog

    def show(self) -> int:
        try:
            if self._show_modal_dialog is not None:
                return int(self._show_modal_dialog(self._dialog, "Copy Sections"))
            return int(self._dialog.ShowModal())  # dialog_button_contract: exempt
        finally:
            self._dialog.Destroy()

    def _refresh(self) -> None:
        self._marks_text.SetLabel(describe_marks(self._marks))
        selection = self._list.GetSelection()
        self._list.Set([
            self._collection.row_label(i) for i in range(len(self._collection.sections))
        ])
        if 0 <= selection < self._list.GetCount():
            self._list.SetSelection(selection)
        self._total.SetLabel(self._collection.describe())
        has_rows = bool(self._collection.sections)
        for button in (self._save_btn, self._append_btn, self._play_btn, self._remove_btn):
            button.Enable(has_rows)
        self._up_btn.Enable(has_rows)
        self._down_btn.Enable(has_rows)
        self._add_btn.Enable(self._marks.section() is not None)
        self._preview_btn.Enable(self._marks.section() is not None)

    # -- marking ---------------------------------------------------------------

    def mark_start(self) -> None:
        self._marks.mark_start(self._source, int(self._playhead_ms()))
        self._refresh()
        self._announce(describe_marks(self._marks))

    def mark_end(self) -> None:
        self._marks.mark_end(self._source, int(self._playhead_ms()))
        self._refresh()
        self._announce(describe_marks(self._marks))

    def preview(self) -> None:
        """Play exactly what is marked, before it is committed to anything."""
        section = self._marks.section()
        if section is None:
            self._announce(describe_marks(self._marks))
            return
        if self._play_range is None:
            self._announce("Preview is not available here.")
            return
        self._play_range(section.start_ms, section.end_ms)
        self._announce("Playing the marked section.")

    def add_marked(self) -> None:
        section = self._marks.section()
        if section is None:
            self._announce(describe_marks(self._marks))
            return
        self._collection.add(section)
        # The marks clear on purpose: the next thing somebody does is find the
        # next section, and leaving the old marks in place would mean clearing
        # them by hand every single time.
        self._marks.clear()
        self._refresh()
        self._announce(f"Added. {self._collection.describe()}")

    # -- the collected list ----------------------------------------------------

    def play_selected(self) -> None:
        index = self._list.GetSelection()
        if index < 0 or self._play_range is None:
            return
        section = self._collection.sections[index]
        self._play_range(section.start_ms, section.end_ms)
        self._announce(f"Playing section {index + 1}.")

    def remove_selected(self) -> None:
        index = self._list.GetSelection()
        removed = self._collection.remove(index)
        if removed is None:
            return
        self._refresh()
        if self._list.GetCount():
            self._list.SetSelection(min(index, self._list.GetCount() - 1))
        self._announce(f"Removed. {self._collection.describe()}")

    def move_selected(self, delta: int) -> None:
        """Reorder the output. The list is the order the file will be in."""
        index = self._list.GetSelection()
        target = index + delta
        rows = self._collection.sections
        if index < 0 or not (0 <= target < len(rows)):
            self._announce("That section is already at the end of the list.")
            return
        rows[index], rows[target] = rows[target], rows[index]
        self._refresh()
        self._list.SetSelection(target)
        self._announce(f"Moved to position {target + 1}.")

    # -- saving ----------------------------------------------------------------

    def save(self, *, append: bool) -> None:
        """Write the collected sections out, to a new file or onto an existing one."""
        wx = self._wx
        if not self._collection.sections:
            self._announce("Mark a section and add it to the list first.")
            return
        style = wx.FD_OPEN if append else (wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        title = "Add the sections to which file?" if append else "Save the sections as"
        suffix = self._source.suffix or ".mp3"
        with wx.FileDialog(  # dialog_button_contract: exempt
            self._dialog,
            title,
            defaultFile="" if append else f"{self._source.stem} sections{suffix}",
            wildcard=f"Audio (*{suffix})|*{suffix}|All files (*.*)|*.*",
            style=style,
        ) as picker:
            if picker.ShowModal() != wx.ID_OK:
                return
            destination = Path(picker.GetPath())

        work_dir = self._work_dir or destination.parent / ".quill-sections"
        self._announce("Saving...")
        try:
            written = save_sections(self._collection, destination, work_dir=work_dir, append=append)
        except Exception as error:  # noqa: BLE001 - reported, never raised at a listener
            self._announce(f"The sections could not be saved. {error}")
            return
        self._announce(
            f"{len(self._collection.sections)} section"
            f"{'' if len(self._collection.sections) == 1 else 's'} "
            f"{'added to' if append else 'saved as'} {written.name}. "
            "The original file is unchanged."
        )
