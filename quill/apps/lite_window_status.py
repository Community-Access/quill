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
* **Heading** -- which heading the caret is in, in either kind of document.
* **Encoding** and **Line endings** -- the two facts that decide whether a file
  round-trips byte-for-byte, which for a Notepad replacement is most of the job,
  and which are invisible everywhere else in the app.
* **Saved** -- whether anything is unsaved.

The counting is QUILL's too: :func:`~quill.core.metrics.compute_document_stats`
and :func:`~quill.core.marks.line_column_for_position`, the same functions the
editor's own bar uses, so the two products cannot disagree about what a word is.

The row **wraps** rather than stretches. It used to be a horizontal box sizer in
which Message was the only cell with a proportion -- so Message was the only cell
that grew, and the only one squeezed when twelve cells did not fit a narrow
window. wxMSW ellipsises a button label wider than its button, and JAWS's
Insert+Page Down reads the bottom line of the window off the screen, so what was
cut off on screen was what it read. A :class:`wx.WrapSizer` flows the row onto a
second line instead: the bar gets taller on a narrow window and nothing clips at
any width. The one text with no natural ceiling -- the message itself -- is
capped in the label and read in full by Enter on the cell.

The one performance rule is QUILL's as well. Counting words is O(document) and a
refresh per keystroke is several full scans per keypress, so refreshes are
**coalesced** through a restarting ``wx.CallLater``: a held arrow key costs one
refresh after the caret stops, not one per repeat.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import wx

from quill.core.heading_levels import heading_level_at
from quill.core.list_structure import list_context_at
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

#: The message cell is the one whose text has no natural ceiling.
_MESSAGE = "message"

#: How many characters of a status message the *label* shows. The message cell
#: is the only one whose text is unbounded -- a path, an OS error, a sentence --
#: and a button label wider than its button is ellipsised by wxMSW, which is
#: what JAWS's Insert+Page Down then reads off the screen. Capped here and read
#: in full by Enter on the cell (and by the F6 landing announcement), which is
#: the trade the fixed cells never have to make: Position and Encoding say two
#: facts nothing else in the app will tell you, so they are never shortened.
_MESSAGE_LABEL_CHARS = 90

#: The margin each cell button is added with, and the slack left under the last
#: row when the bar's height is measured.
_CELL_GAP = 2

#: A height no wrapped row can reach, used to lay the cells out at a known width
#: so their real extent can be measured. ``wx.WrapSizer.CalcMin`` reports one
#: row whatever it is told (``InformFirstDirection`` returns False and changes
#: nothing), so the wrapped height has to come from an actual layout pass.
_REFLOW_PROBE_HEIGHT = 10_000


def _clip_message(message: str) -> str:
    """*message* shortened to what a status button can show without ellipsising.

    Cut at the last space inside the budget so a half-word is never left
    dangling, and mark the cut so the label does not read as the whole message.
    The full text is still one Enter away on the cell.
    """
    if len(message) <= _MESSAGE_LABEL_CHARS:
        return message
    head = message[:_MESSAGE_LABEL_CHARS].rstrip()
    space = head.rfind(" ")
    if space > _MESSAGE_LABEL_CHARS // 2:
        head = head[:space]
    return f"{head.rstrip()}..."


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
        "What kind of document this is: plain text, Markdown, HTML or rich "
        "text. It decides what Bold writes, what the heading keys write, which "
        "of the two tag pickers the Insert menu offers, and whether the cursor "
        "can tell you what list you are in. Press Enter to ring on to the next "
        "kind; press Control Alt F6 to go straight to one.",
    ),
    StatusCell(
        "heading",
        "Heading",
        "The heading the cursor is inside -- the point-size ladder in a rich "
        "text document, the Markdown hashes in a plain one. "
        "Press Enter for the list of every heading.",
    ),
    StatusCell(
        "list",
        "List",
        "The list the cursor is inside, how many items it has at this level, "
        "and how far down you are -- the three facts a screen reader gives you "
        "about a list on a web page and cannot give you about one in an editor. "
        "It reads 'Not in a list' when you are not. Press Enter to stop or "
        "resume announcing lists as you move.",
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
        # A wrapping row, not a stretching one. With a horizontal box sizer the
        # Message cell was the only cell with a proportion, so it was the only
        # cell that *grew* -- and the only one that got squeezed when twelve
        # cells did not fit the window. wxMSW ellipsises a button label wider
        # than its button, and JAWS's Insert+Page Down reads the bottom line of
        # the window off the screen, so the text cut off on screen was the text
        # it read. Wrapping costs a taller bar when the window is narrow and
        # clips nothing at any width.
        # No EXTEND_LAST_ON_EACH_LINE: a cell stretched to fill its row is
        # a button whose width says nothing about its text, which is the
        # habit that made Message the only cell that could be squeezed.
        sizer = wx.WrapSizer(wx.HORIZONTAL, wx.REMOVE_LEADING_SPACES)
        self._status_buttons: dict[str, wx.Button] = {}
        for cell in CELLS:
            button = wx.Button(self.status_panel, label=cell.label, style=wx.BU_EXACTFIT)
            button.SetName(cell.label)
            button.SetHelpText(cell.help_text)
            button.Bind(wx.EVT_BUTTON, lambda _e, key=cell.key: self._activate_status_cell(key))
            button.Bind(wx.EVT_KEY_DOWN, lambda e, key=cell.key: self._on_status_key(e, key))
            button.Bind(wx.EVT_SET_FOCUS, lambda e, key=cell.key: self._on_status_focus(e, key))
            sizer.Add(button, 0, wx.ALL, _CELL_GAP)
            self._status_buttons[cell.key] = button
        self.status_panel.SetSizer(sizer)
        self.status_panel.Bind(wx.EVT_SIZE, self._on_status_panel_size)

    # -- height ------------------------------------------------------------- #

    def _on_status_panel_size(self, event: wx.SizeEvent) -> None:
        """Re-measure the wrapped row whenever the window's width changes."""
        event.Skip()
        self._reflow_status_bar()

    def _reflow_status_bar(self) -> None:
        """Give the panel the height its cells actually need at this width.

        A ``wx.WrapSizer`` inside a panel cannot tell the frame's sizer how tall
        it wants to be -- ``InformFirstDirection`` does not cross the window
        boundary and ``CalcMin`` always answers one row -- so the height is
        measured from a real layout at the current width and pushed back as the
        panel's minimum. The frame is re-laid out only when that number moves,
        which is what keeps this out of a size-event loop.
        """
        panel = getattr(self, "status_panel", None)
        if panel is None or not panel.IsShown():
            return
        sizer = panel.GetSizer()
        if sizer is None or not self._status_buttons:
            return
        width = panel.GetClientSize().width
        if width <= 1:
            return
        try:
            sizer.SetDimension(0, 0, width, _REFLOW_PROBE_HEIGHT)
            height = (
                max(
                    button.GetPosition().y + button.GetSize().height
                    for button in self._status_buttons.values()
                )
                + _CELL_GAP
            )
        except RuntimeError:
            return  # a window mid-teardown
        if panel.GetMinSize().height == height:
            return
        panel.SetMinSize((-1, height))
        self.Layout()

    def apply_status_bar_visibility(self) -> None:
        """Show or hide the whole bar to match the setting.

        Hidden means *gone*, not empty: the panel leaves the sizer's calculation
        so the editor takes the rows back, and a hidden button is not in the tab
        ring, so Shift+Tab out of the document cannot land in a bar nobody asked
        for. Coming back marks the cells stale, because nothing was refreshing
        them while they were away.
        """
        visible = bool(getattr(self.app.settings, "show_status_bar", True))
        if self.status_panel.IsShown() == visible:
            return
        self.status_panel.Show(visible)
        self.Layout()
        if visible:
            self._reflow_status_bar()
            self._touch_status()

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
        if not self.status_panel.IsShown():
            # Counting words for a bar nobody can see is a full document scan
            # per keystroke spent on nothing. The cells are marked stale again
            # when the bar comes back.
            return
        self._status_dirty = False
        try:
            values = self._cell_values()
            for key, text in values.items():
                self._status_buttons[key].SetLabel(text)
            self.status_panel.Layout()
        except (RuntimeError, KeyError):
            return  # a window mid-teardown; there is nothing left to update
        # A label that grew can need a row the bar does not have yet.
        self._reflow_status_bar()

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
            _MESSAGE: _clip_message(self._status_message) or "Ready",
            "position": f"Line {line:,}, column {column:,} of {max(1, stats.lines):,}",
            "words": f"{stats.words:,} words",
            "characters": f"{stats.characters:,} characters",
            "selection": selection,
            "typing_mode": "Overwrite" if getattr(self, "_overwrite_mode", False) else "Insert",
            # QUILL's own wording for the same cell, so the two products do not
            # describe one mode two ways.
            "tab_mode": "Tab char" if getattr(self, "_tab_inserts_literal", True) else "Indent",
            "format": self.document_kind_label(),
            "heading": self._heading_text(),
            "list": self._list_text(text),
            "encoding": encoding_name(self.encoding),
            "line_endings": newline_name(self.newline),
            "saved": "Modified" if self.modified else "Saved",
        }

    def _heading_text(self) -> str:
        """Which heading the caret is in, in either kind of document.

        Rich text asks the control's Text Object Model about the point-size
        ladder; plain text reads the Markdown hashes off the line, through the
        same :func:`~quill.core.heading_levels.heading_level_at` the caret cue
        and Alt+Shift+Right use. The cell used to read "Not in rich text" in a
        plain document, which was wrong twice over: those documents have real
        headings, and pressing Enter on the cell opens a working list of them.

        One call, on the coalesced refresh rather than per keystroke. A failure
        reads as "Body text", never as the bar stopping.
        """
        if self.editor.mode != RICH:
            level = heading_level_at(self.control.GetValue(), self.control.GetInsertionPoint())
        else:
            level = self.editor.heading_level_at_caret()
        return f"Heading {level}" if level else "Body text"

    def _list_text(self, text: str) -> str:
        """Which list the caret is in, or "Not in a list".

        The cell says one thing the spoken cue deliberately does not: **which
        item you are on**. Saying "item 4 of 9" aloud on every arrow press would
        be the over-announcement GATE-13 is about, and never being able to find
        out is its own problem -- somebody halfway through reordering a list of
        nine has an entirely reasonable question and nothing to ask. A cell
        answers it on demand and costs nothing until it is read.

        One scan, on the coalesced refresh rather than per keystroke, over the
        text the rest of the bar has already been handed. A failure reads as
        "Not in a list", never as the bar stopping.
        """
        surface = self.markup_surface()
        if surface is None:
            return "Not in a list"
        try:
            context = list_context_at(text, self.control.GetInsertionPoint(), markup_kind=surface)
        except Exception:  # noqa: BLE001 - a status cell must never break typing
            return "Not in a list"
        if context is None:
            return "Not in a list"
        where = f"{context.label}, {context.index} of {context.size}"
        return where if context.depth <= 1 else f"{where}, level {context.depth}"

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
        """What this cell *says*, which is not always what its label shows.

        The Message cell's label is clipped to what fits a button; the reading
        is the whole message, so Enter on the cell and the F6 landing both give
        the full wording of an error rather than the first ninety characters of
        it.
        """
        if key == _MESSAGE and self._status_message:
            return self._status_message
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
        elif code in {wx.WXK_ESCAPE, wx.WXK_F6}:
            # F6 as well as Escape, and for the reason F6 got you here: a key
            # that takes you somewhere should take you back. Shift+F6 is the
            # same journey backwards and lands in the same place. A listener who
            # pressed F6 to check a line number and pressed it again to get on
            # with their sentence should not find that the second press did
            # nothing at all.
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
    "format": "cmd_switch_document_kind",
    "heading": "cmd_list_headings",
    # Enter on List toggles the cue rather than opening anything, because there
    # is nothing to open: the cell has already said where you are, and the only
    # thing left to decide about a list is whether you want to keep hearing
    # about it.
    "list": "cmd_toggle_list_announcements",
    "encoding": "cmd_file_format",
    "line_endings": "cmd_file_format",
    "saved": "cmd_save",
}
