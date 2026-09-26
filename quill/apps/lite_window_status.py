"""QUILL Lite's status bar: QUILL's focusable cells, at notepad scale.

QUILL's status bar is not a strip of painted text. It is a row of **focusable
cells** (``quill/ui/main_frame_statusbar.py``): F6 lands in it, the arrow keys
and Home/End move between cells, each cell announces its own name and value,
Enter acts on it, and Escape returns to the document. That is the difference
between a status bar a sighted user glances at and one a screen-reader user can
actually read -- and it is why QUILL Lite builds the same thing rather than
calling ``SetStatusText`` four times.

What is *not* copied is QUILL's configurability. The full editor lets you
reorder and hide thirty-odd cells and has a dialog for doing it; QUILL Lite has
:data:`CELLS`, thirteen of them, fixed. A notepad does not need a status-bar layout
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

The row also has to hold **still**. Nothing clipping is only half of what that
same Insert+Page Down needs: a cell that changes width shoves every cell after
it sideways, and text drawn at one position and then redrawn ninety pixels along
leaves both in the screen model the reader is reading out of. That is what came
back as "Line 1, colu Line 1, c ... No selectio", on a maximised window with room
to spare. So a cell's width is a high-water mark -- it may grow, never shrink
(:func:`_widen_to_label`) -- and a cell whose text has not changed is not written
to at all.

The one performance rule is QUILL's as well. Counting words is O(document) and a
refresh per keystroke is several full scans per keypress, so refreshes are
**coalesced** through a restarting ``wx.CallLater``: a held arrow key costs one
refresh after the caret stops, not one per repeat.
"""

from __future__ import annotations

import time
from typing import Any

import wx

from quill.apps.lite_window_typing import overwrite_now
from quill.core.heading_levels import heading_level_at
from quill.core.list_structure import list_context_at
from quill.core.metrics import compute_document_stats
from quill.core.status_message import (
    IDLE_MESSAGE,
    MESSAGE_TTL_SECONDS,
    StatusMessage,
    current_message,
)
from quill.ui.native_status_bar import (
    native_status_text,
    show_native_status_bar,
    sync_native_status_bar,
)
from quill.ui.richedit_editing import RICH
from quill.ui.status_bar_role import mark_as_status_bar, mark_as_status_cell

__all__ = [
    "CELLS",
    "RICH_ENCODING_CELL",
    "RICH_LINE_ENDINGS_CELL",
    "DocumentStatusMixin",
    "StatusCell",
    "encoding_name",
    "newline_name",
]

# The cells themselves, their labels and their sizing rule live next door: a
# catalogue and a controller grow for different reasons.
from quill.apps.lite_status_cells import (
    _CELL_GAP,
    _COALESCE_MS,
    _MESSAGE,
    _REFLOW_PROBE_HEIGHT,
    CELLS,
    RICH_ENCODING_CELL,
    RICH_LINE_ENDINGS_CELL,
    StatusCell,
    _clip_message,
    _widen_to_label,
    encoding_name,
    native_cell_labels,
    newline_name,
)
from quill.apps.lite_window_dictation import dictation_cell


class DocumentStatusMixin:
    """The status bar of a :class:`~quill.apps.lite_window.DocumentFrame`.

    Mixed into the window, which supplies ``control``, ``editor``, ``modified``,
    ``encoding``, ``newline`` and ``_announce``.
    """

    def _encoding_cell(self) -> str:
        """The Encoding cell, which must not answer for a document that has none.

        ``self.encoding`` is only ever set by the *plain* load path, so opening
        a ``.rtf`` left it at the window's birth defaults and the cell read
        "UTF-8" for every rich document (bad.md F7). Reading a cell aloud and
        being told a fact about a file that is not true of it is worse than the
        cell not existing: File Encoding and Line Endings already refuses in
        rich mode, so the status bar was the only place still claiming it.
        """
        if self.editor.mode == RICH:
            return RICH_ENCODING_CELL
        return encoding_name(self.encoding)

    def _line_endings_cell(self) -> str:
        """The Line Endings cell, on the same rule as :meth:`_encoding_cell`."""
        if self.editor.mode == RICH:
            return RICH_LINE_ENDINGS_CELL
        return newline_name(self.newline)

    # -- construction -------------------------------------------------------- #

    def _init_status_bar(self) -> None:
        """Build the cell row.

        The bar is reached with F6 and left with Escape, exactly as QUILL's is.
        Each cell is a real button, because a button is the one control every
        screen reader reads, focuses and activates without being taught how.
        """
        self._status_message = ""
        #: When the message was set, and what the document's revision was then.
        #: ``None`` means nothing has been said yet, which is not the same as a
        #: message set a long time ago -- see :meth:`_live_status_message`.
        self._status_message_at: float | None = None
        self._status_message_revision = 0
        self._status_expiry_timer: Any = None
        self._status_dirty = True
        self._status_refresh_timer: Any = None
        self._active_cell_index = 0
        self._status_entry_pending = False

        self.status_panel = wx.Panel(self)
        self.status_panel.SetName("Status bar")
        # ...and say so to Windows, which is what makes JAWS's Insert+Page Down
        # find it instead of scraping the bottom line of the screen.
        mark_as_status_bar(wx, self.status_panel)
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
            mark_as_status_cell(wx, button)
            button.SetHelpText(cell.help_text)
            button.Bind(wx.EVT_BUTTON, lambda _e, key=cell.key: self._activate_status_cell(key))
            button.Bind(wx.EVT_KEY_DOWN, lambda e, key=cell.key: self._on_status_key(e, key))
            button.Bind(wx.EVT_SET_FOCUS, lambda e, key=cell.key: self._on_status_focus(e, key))
            _widen_to_label(button)
            sizer.Add(button, 0, wx.ALL, _CELL_GAP)
            self._status_buttons[cell.key] = button
        self.status_panel.SetSizer(sizer)
        self.status_panel.Bind(wx.EVT_SIZE, self._on_status_panel_size)
        # And a real native status bar underneath the row, carrying the same
        # text unclipped. It is the control JAWS's Insert+Page Down actually
        # looks for; see quill/ui/native_status_bar.py for why the role on the
        # panel above was never going to be enough.
        sync_native_status_bar(self, "")

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
        # The native mirror goes with it. A bar the user has turned off must
        # not still answer Insert+Page Down: the setting means "no status bar",
        # not "no status bar unless you ask a different way".
        show_native_status_bar(self, visible)
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
        """Recompute every cell's text, from one read of the document.

        Two things keep the row **still**, which is what a screen reader needs
        from it more than anything else (:func:`_widen_to_label` has the story).

        A cell whose text has not changed is not touched at all -- which is most
        cells on most refreshes. ``SetLabel`` fires a name change through
        MSAA/UIA, and a reader has no use for being told that Encoding was
        renamed to "UTF-8" again after every keystroke.

        A cell whose text *has* changed keeps the width it had unless the new
        text genuinely needs more, so the ninety-pixel swing between "No
        selection" and "1 words, 8 characters selected" moves the nine cells
        after it exactly once instead of on every selection.
        """
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
            widened = False
            values = self._cell_values()
            self._sync_native_status_bar(values)
            for key, text in values.items():
                button = self._status_buttons[key]
                if button.GetLabel() == text:
                    continue
                button.SetLabel(text)
                widened = _widen_to_label(button) or widened
            if widened:
                # Only a cell that grew can have moved the ones after it, and
                # only a move leaves the old text on the screen for JAWS to
                # read back. Repainted explicitly: wxMSW moves the children and
                # does not always erase what they vacated.
                self.status_panel.Layout()
                self.status_panel.Refresh()
        except (RuntimeError, KeyError):
            return  # a window mid-teardown; there is nothing left to update
        # A label that grew can need a row the bar does not have yet.
        self._reflow_status_bar()

    def _cell_values(self) -> dict[str, str]:
        """Every cell's text, off the document mirror rather than the control.

        It said "one document scan, not one per cell" and was three: the counts
        here, the heading cue's own ``GetValue()`` and hashes walk, and the list
        cue's scan -- plus two full marshals out of the native control, on every
        coalesced refresh, which is every pause in typing and every pause in
        arrowing (bad.md V2). The mirror reads once per *edit*, so a refresh
        after a caret move now costs nothing at all, and the counts are memoised
        against the revision the way QUILL's have been since #1346.
        """
        text = self.doc_text.text
        stats = self.doc_text.stats()
        line, column = self.doc_text.line_column(self.control.GetInsertionPoint())
        start, end = self.control.GetSelection()
        if end > start:
            selected = compute_document_stats(text[start:end])
            selection = f"{selected.words:,} words, {selected.characters:,} characters selected"
        else:
            selection = "No selection"
        return {
            _MESSAGE: _clip_message(self._live_status_message()),
            "position": f"Line {line:,}, column {column:,} of {max(1, stats.lines):,}",
            "words": f"{stats.words:,} words",
            "characters": f"{stats.characters:,} characters",
            "selection": selection,
            "typing_mode": "Overwrite" if overwrite_now(self) else "Insert",
            # QUILL's own wording for the same cell, so the two products do not
            # describe one mode two ways.
            "tab_mode": "Tab char" if getattr(self, "_tab_inserts_literal", True) else "Indent",
            "format": self.document_kind_label(),
            "heading": self._heading_text(text),
            "list": self._list_text(text),
            "dictation": dictation_cell(self),
            "encoding": self._encoding_cell(),
            "line_endings": self._line_endings_cell(),
            "saved": "Modified" if self.modified else "Saved",
        }

    def _heading_text(self, text: str) -> str:
        """Which heading the caret is in, in either kind of document.

        Rich text asks the control's Text Object Model about the point-size
        ladder; a **Markdown or HTML** document reads its own markers off the
        line, through the same :func:`~quill.core.heading_levels.heading_level_at`
        the caret cue and Alt+Shift+Right use. The cell used to read "Not in
        rich text" in those documents, which was wrong twice over: they have
        real headings, and pressing Enter on the cell opens a working list.

        A **plain text** document has none, and saying so is the fix for the
        other half of that. ``heading_level_at`` defaults to reading Markdown,
        and this call did not say otherwise -- so a plain document containing a
        line of literal hashes was announced as "Heading 2" when the hashes are
        the text. Reported as the editor being "misleading about markdown when
        in plain text we are not writing markdown, just plain text". The surface
        is passed now, and a plain document reads "Body text" because that is
        all a plain document has.

        One call, on the coalesced refresh rather than per keystroke. A failure
        reads as "Body text", never as the bar stopping.
        """
        if self.editor.mode != RICH:
            level = heading_level_at(
                text,
                self.control.GetInsertionPoint(),
                markup_kind=self.markup_surface() or "",
            )
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

    def _sync_native_status_bar(self, values: dict[str, str]) -> None:
        """Mirror the row onto the native bar, message unclipped and last.

        The label the button shows is cut to what fits a button; the native bar
        is read with ``SB_GETTEXT`` and has no such limit, so it carries the
        whole message. Never raises -- ``sync_native_status_bar`` swallows a
        dead frame, and the visible row is the one that matters.
        """
        native = dict(values)
        native[_MESSAGE] = self._live_status_message()
        sync_native_status_bar(self, native_status_text(native_cell_labels(native)))

    # -- the message cell ---------------------------------------------------- #

    def _document_revision(self) -> int:
        """The document's revision, or 0 for a window that has no mirror yet."""
        try:
            return int(self.doc_text.revision)
        except Exception:  # noqa: BLE001 - a status cell must never break typing
            return 0

    def _live_status_message(self) -> str:
        """The message cell's text *now*, which is not always what was set.

        A message describes a moment, and the moment passes: the next edit
        clears it and so does a minute going by. See
        :mod:`quill.core.status_message` for why, and for the report -- a
        "String not found" that sat in the bar through a page of editing.

        A message set without a timestamp never expires. Nothing in the app
        does that; a test assigning ``_status_message`` directly does, and it
        should get the message it assigned rather than a clock it never set.
        """
        if self._status_message_at is None:
            return self._status_message or IDLE_MESSAGE
        stamped = StatusMessage(
            self._status_message, self._status_message_at, self._status_message_revision
        )
        return current_message(stamped, now=time.monotonic(), revision=self._document_revision())

    def _set_status_message(self, message: str) -> None:
        """Put a spoken message in the message cell so it can be read back.

        Speech is gone the moment it is spoken. A listener who missed it -- or
        who wants the exact wording of an error -- arrows to this cell and hears
        it again.

        Stamped with the clock and the revision, because it is only worth
        reading back for as long as it is still true.
        """
        self._status_message = message
        self._status_message_at = time.monotonic()
        self._status_message_revision = self._document_revision()
        self._arm_message_expiry()
        self._touch_status()

    def _arm_message_expiry(self) -> None:
        """Refresh the bar once the message is due to age out.

        Without this the cell would hold an expired message until something
        else happened to refresh it -- and "nothing else is happening" is
        exactly the case the timeout is for. Silent: the label changes on an
        unfocused control, which is what a reader does not announce (GATE-13).
        """
        timer = self._status_expiry_timer
        self._status_expiry_timer = None
        if timer is not None:
            try:
                timer.Stop()
            except RuntimeError:
                pass
        self._status_expiry_timer = wx.CallLater(
            int(MESSAGE_TTL_SECONDS * 1000) + _COALESCE_MS, self._touch_status
        )

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
        if key == _MESSAGE:
            return self._live_status_message()
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
        timer = self._status_expiry_timer
        self._status_expiry_timer = None
        if timer is not None:
            try:
                timer.Stop()
            except RuntimeError:
                pass


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
    "dictation": "cmd_toggle_dictation",
    "encoding": "cmd_file_format",
    "line_endings": "cmd_file_format",
    "saved": "cmd_save",
}
