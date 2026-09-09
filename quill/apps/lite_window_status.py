"""QuillLite's status bar: QUILL's focusable cells, at notepad scale.

QUILL's status bar is not a strip of painted text. It is a row of **focusable
cells** (``quill/ui/main_frame_statusbar.py``): F6 lands in it, the arrow keys
and Home/End move between cells, each cell announces its own name and value,
Enter acts on it, and Escape returns to the document. That is the difference
between a status bar a sighted user glances at and one a screen-reader user can
actually read -- and it is why QuillLite builds the same thing rather than
calling ``SetStatusText`` four times.

What is *not* copied is QUILL's configurability. The full editor lets you
reorder and hide thirty-odd cells and has a dialog for doing it; QuillLite has
:data:`CELLS`, twelve of them, fixed. A notepad does not need a status-bar layout
editor, and every cell here is a fact a text editor is actually asked for:

* **Message** -- the last thing that was announced, so speech can be re-read.
* **Position** -- line and column, of how many lines.
* **Words** and **Characters** -- what the document is.
* **Selection** -- how much is selected, the number wanted while selecting.
* **Typing Mode** -- insert or overwrite. The whole reason the feature is
  worth having here: a mode you cannot query is a mode you discover by typing
  over your own work.
* **Tab Mode** -- whether the Tab key types a tab character or indents the
  line. The other invisible mode, and the other one you would otherwise
  discover by pressing the key and listening to what happened.
* **Format** -- plain text or rich text.
* **Heading** -- which heading the caret is in (rich text only).
* **Encoding** and **Line endings** -- the two facts that decide whether a file
  round-trips byte-for-byte, which for a Notepad replacement is most of the job,
  and which are invisible everywhere else in the app.
* **Saved** -- whether anything is unsaved.

The counting is QUILL's too: :func:`~quill.core.metrics.compute_document_stats`
and :func:`~quill.core.marks.line_column_for_position`, the same functions the
editor's own bar uses, so the two products cannot disagree about what a word is.

The one performance rule is QUILL's as well. Counting words is O(document) and a
refresh per keystroke is several full scans per keypress, so refreshes are
**coalesced** through a restarting ``wx.CallLater``: a held arrow key costs one
refresh after the caret stops, not one per repeat.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import wx

from quill.core.lite.textfile import ENCODING_CHOICES, NEWLINE_CHOICES
from quill.core.marks import line_column_for_position
from quill.core.metrics import compute_document_stats
from quill.ui.richedit_editing import RICH

__all__ = ["CELLS", "DocumentStatusMixin", "StatusCell", "encoding_name", "newline_name"]

#: How long caret movement may leave the bar stale. QUILL's own coalescing
#: window (``StatusBarMixin._STATUSBAR_COALESCE_MS``): a tenth of a second is
#: imperceptible, and refreshing synchronously on every caret event was several
#: full-buffer scans per keystroke.
_COALESCE_MS = 90

#: The message cell stretches; the rest take only what they need.
_MESSAGE = "message"


@dataclass(frozen=True, slots=True)
class StatusCell:
    """One cell: its key, the name it announces, and what F1 says about it."""

    key: str
    label: str
    help_text: str


CELLS: tuple[StatusCell, ...] = (
    StatusCell(
        _MESSAGE,
        "Status Message",
        "The last thing QuillLite announced. Speech is gone once it is spoken; "
        "this is where it can be read again.",
    ),
    StatusCell(
        "position",
        "Position",
        "Where the cursor is: line and column, out of how many lines. "
        "Press Enter to go to a line by number.",
    ),
    StatusCell(
        "words",
        "Word Count",
        "How many words the whole document has. A word is a run of characters with "
        "a space or a line break on each side, which is how QUILL counts them too, "
        "so the two products never disagree about the length of the same file.",
    ),
    StatusCell(
        "characters",
        "Character Count",
        "How many characters the whole document has, spaces and line breaks "
        "included. This counts characters as you would read them, not bytes on "
        "disk: an accented letter is one character here whatever the encoding.",
    ),
    StatusCell(
        "selection",
        "Selection",
        "How much text is selected. It reads 'No selection' when there is none.",
    ),
    StatusCell(
        "typing_mode",
        "Typing Mode",
        "Whether typing inserts characters or overwrites the ones already there. "
        "The native editing control keeps this mode and will not report it, so "
        "this cell is the only way to ask. Press Enter to switch.",
    ),
    StatusCell(
        "tab_mode",
        "Tab Mode",
        "What the Tab key does: type a tab character, or indent the whole line. "
        "Shift+Tab outdents either way. Press Enter to switch.",
    ),
    StatusCell(
        "format",
        "Format",
        "Plain text or rich text. Press Enter to switch this document to the other one.",
    ),
    StatusCell(
        "heading",
        "Heading",
        "The heading the cursor is inside, in a rich text document. "
        "Press Enter for the list of every heading.",
    ),
    StatusCell(
        "encoding",
        "Encoding",
        "The character encoding this file was read with and will be written back "
        "with: UTF-8, UTF-8 with a byte order mark, UTF-16, or Windows-1252. "
        "Press Enter to change it.",
    ),
    StatusCell(
        "line_endings",
        "Line Endings",
        "Whether this file uses Windows line endings (CRLF) or Unix ones (LF). "
        "QuillLite writes back whichever it read, so a file does not change shape "
        "just because it was opened. Press Enter to change it.",
    ),
    StatusCell("saved", "Saved State", "Whether this document has unsaved changes."),
)

#: Codec and line-ending names, read from the same table the File Format
#: dialog offers, so the status bar and the chooser can never call the same
#: thing two different things. The one extra entry is what the chooser does
#: not offer: classic-Mac CR, which can be read but is not worth writing.
_ENCODING_NAMES = dict(ENCODING_CHOICES)
_NEWLINE_NAMES = dict(NEWLINE_CHOICES) | {"\r": "CR (classic Mac)"}


def encoding_name(codec: str) -> str:
    """How a codec is named to a person; the raw codec if it is not one of ours."""
    return _ENCODING_NAMES.get(codec, codec)


def newline_name(newline: str) -> str:
    """How a line ending is named to a person."""
    return _NEWLINE_NAMES.get(newline, "Mixed")


class DocumentStatusMixin:
    """The status bar of a :class:`~quill.apps.lite_window.DocumentFrame`.

    Mixed into the window, which supplies ``control``, ``editor``, ``modified``,
    ``encoding``, ``newline`` and ``_announce``.
    """

    # -- construction -------------------------------------------------------- #

    def _init_status_bar(self) -> None:
        """Build the cell row.

        The bar is reached with F6 and left with Escape, exactly as QUILL's is.
        Each cell is a real button, because a button is the one control every
        screen reader reads, focuses and activates without being taught how.
        """
        self._status_message = ""
        self._status_dirty = True
        self._status_refresh_timer: Any = None
        self._active_cell_index = 0
        self._status_entry_pending = False

        self.status_panel = wx.Panel(self)
        self.status_panel.SetName("Status bar")
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._status_buttons: dict[str, wx.Button] = {}
        for cell in CELLS:
            button = wx.Button(self.status_panel, label=cell.label, style=wx.BU_EXACTFIT)
            button.SetName(cell.label)
            button.SetHelpText(cell.help_text)
            button.Bind(wx.EVT_BUTTON, lambda _e, key=cell.key: self._activate_status_cell(key))
            button.Bind(wx.EVT_KEY_DOWN, lambda e, key=cell.key: self._on_status_key(e, key))
            button.Bind(wx.EVT_SET_FOCUS, lambda e, key=cell.key: self._on_status_focus(e, key))
            sizer.Add(button, 1 if cell.key == _MESSAGE else 0, wx.EXPAND | wx.ALL, 2)
            self._status_buttons[cell.key] = button
        self.status_panel.SetSizer(sizer)

    # -- refreshing ---------------------------------------------------------- #

    def _touch_status(self) -> None:
        """Mark the bar stale and schedule one refresh once activity stops."""
        self._status_dirty = True
        self._cancel_status_refresh()
        self._status_refresh_timer = wx.CallLater(_COALESCE_MS, self._refresh_status)

    def _refresh_status(self) -> None:
        """Recompute every cell's text, from one read of the document."""
        self._status_refresh_timer = None
        if not self._status_dirty:
            return
        self._status_dirty = False
        try:
            values = self._cell_values()
            for key, text in values.items():
                self._status_buttons[key].SetLabel(text)
            self.status_panel.Layout()
        except (RuntimeError, KeyError):
            return  # a window mid-teardown; there is nothing left to update

    def _cell_values(self) -> dict[str, str]:
        """Every cell's text. One document scan, not one per cell."""
        text = self.control.GetValue()
        stats = compute_document_stats(text)
        line, column = line_column_for_position(text, self.control.GetInsertionPoint())
        start, end = self.control.GetSelection()
        if end > start:
            selected = compute_document_stats(text[start:end])
            selection = f"{selected.words:,} words, {selected.characters:,} characters selected"
        else:
            selection = "No selection"
        return {
            _MESSAGE: self._status_message or "Ready",
            "position": f"Line {line:,}, column {column:,} of {max(1, stats.lines):,}",
            "words": f"{stats.words:,} words",
            "characters": f"{stats.characters:,} characters",
            "selection": selection,
            "typing_mode": "Overwrite" if getattr(self, "_overwrite_mode", False) else "Insert",
            # QUILL's own wording for the same cell, so the two products do not
            # describe one mode two ways.
            "tab_mode": "Tab char" if getattr(self, "_tab_inserts_literal", True) else "Indent",
            "format": "Rich text" if self.editor.mode == RICH else "Plain text",
            "heading": self._heading_text(),
            "encoding": encoding_name(self.encoding),
            "line_endings": newline_name(self.newline),
            "saved": "Modified" if self.modified else "Saved",
        }

    def _heading_text(self) -> str:
        """Which heading the caret is in. Rich text only, and best effort.

        One Text Object Model call, on the coalesced refresh rather than per
        keystroke. A failure reads as "Body text", never as the bar stopping.
        """
        if self.editor.mode != RICH:
            return "Not in rich text"
        level = self.editor.heading_level_at_caret()
        return f"Heading {level}" if level else "Body text"

    def _set_status_message(self, message: str) -> None:
        """Put a spoken message in the message cell so it can be read back.

        Speech is gone the moment it is spoken. A listener who missed it -- or
        who wants the exact wording of an error -- arrows to this cell and hears
        it again.
        """
        self._status_message = message
        self._touch_status()

    # -- navigation ---------------------------------------------------------- #

    def focus_status_bar(self) -> None:
        """F6: land in the status bar, on the cell last left."""
        self._refresh_status()
        self._status_entry_pending = True
        self._focus_cell(self._active_cell_index)

    def _focus_cell(self, index: int) -> None:
        index = max(0, min(index, len(CELLS) - 1))
        self._active_cell_index = index
        self._status_buttons[CELLS[index].key].SetFocus()

    def _cell_index(self, key: str) -> int:
        for index, cell in enumerate(CELLS):
            if cell.key == key:
                return index
        return 0

    def _on_status_focus(self, event: wx.FocusEvent, key: str) -> None:
        """Name the region once, on arrival, and never again.

        The reader announces the button's own name and value by itself, so this
        adds nothing while arrowing along the row. What it cannot know is that
        the row *is* the status bar -- moving from a text control to a strip of
        buttons is described as "button" and nothing more -- so the region is
        named on the F6 landing and the flag is cleared immediately.
        """
        self._active_cell_index = self._cell_index(key)
        entering = self._status_entry_pending
        self._status_entry_pending = False
        if entering:
            self._announce(f"Status bar, {self._cell_reading(key)}")
        event.Skip()

    def _cell_reading(self, key: str) -> str:
        button = self._status_buttons.get(key)
        value = button.GetLabel() if button is not None else ""
        return str(value) or CELLS[self._cell_index(key)].label

    def _on_status_key(self, event: wx.KeyEvent, key: str) -> None:
        code = event.GetKeyCode()
        index = self._cell_index(key)
        if code == wx.WXK_LEFT:
            self._focus_cell(index - 1)
        elif code == wx.WXK_RIGHT:
            self._focus_cell(index + 1)
        elif code == wx.WXK_HOME:
            self._focus_cell(0)
        elif code == wx.WXK_END:
            self._focus_cell(len(CELLS) - 1)
        elif code == wx.WXK_TAB:
            self._focus_cell(index + (-1 if event.ShiftDown() else 1))
        elif code == wx.WXK_ESCAPE:
            self.control.SetFocus()
        elif code in {wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_SPACE}:
            self._activate_status_cell(key)
        else:
            event.Skip()

    def _activate_status_cell(self, key: str) -> None:
        """Enter on a cell: do what that cell is about, or read it again.

        A cell whose subject has a command runs it -- Position goes to a line,
        Format switches mode, Heading lists the headings, Saved saves. The rest
        are facts with nothing to do, so they repeat themselves, which is a
        better answer than "I pressed Enter and heard nothing".
        """
        handler = _CELL_ACTIONS.get(key)
        if handler is not None:
            getattr(self, handler)()
            return
        self._announce(self._cell_reading(key))

    def _cancel_status_refresh(self) -> None:
        timer = self._status_refresh_timer
        self._status_refresh_timer = None
        if timer is not None:
            try:
                timer.Stop()
            except RuntimeError:
                pass

    def _stop_status_timer(self) -> None:
        """Cancel a pending refresh as the window closes."""
        self._cancel_status_refresh()


#: What Enter does on each cell. Absent means "say it again".
_CELL_ACTIONS: dict[str, str] = {
    "position": "cmd_goto_line",
    "typing_mode": "cmd_toggle_overwrite",
    "tab_mode": "cmd_toggle_tab_mode",
    "format": "cmd_switch_mode",
    "heading": "cmd_list_headings",
    "encoding": "cmd_file_format",
    "line_endings": "cmd_file_format",
    "saved": "cmd_save",
}
