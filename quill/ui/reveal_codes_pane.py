"""Reveal Codes pane — the wx view + caret-sync controller.

A WordPerfect-style Reveal Codes surface, screen-reader-first. It docks below the
editor and shows the active document as a stream of bracketed code tokens and
visible text (see ``quill/core/reveal_codes.py`` for the wx-free token model and
``quill/core/reveal_nav.py`` for the caret model). Two presentations share the same
token stream:

* **Flowed** — the interactive, "magical" surface and the default: a read-only
  ``wx.TextCtrl`` rendering the codes inline within the running text
  (``[Bold On]Hello[Bold Off]``). The pane *owns* navigation here — Left/Right walk
  one character through text but step over a whole ``[Bold On]`` atomically,
  Ctrl+Left/Right move by word, Up/Down move by logical line — and the pane is the
  *sole* speaker (it consumes the arrow keys so the screen reader does not also
  narrate the caret move; see ``_on_flow_key``). This is what stops JAWS and NVDA
  from announcing differently and stops "Reveal Codes" from being repeated on every
  keypress. Pressing **F2** on a text run bounded by a formatting pair restricts the
  caret to that run for full editing.
* **Structured** — a read-only ``wx.ListBox``, one navigable item per token. The
  screen reader reads each item itself, so the pane stays quiet to avoid double
  speech.

The pane keeps its caret in sync with the editor's: moving here moves the editor
caret to the matching markup offset, and the editor's caret selects the matching
position here. All wx lives in this module; the token logic and caret math are the
pure ``core.reveal_codes`` / ``core.reveal_nav`` functions.
"""

from __future__ import annotations

from typing import Any

from quill.core.reveal_codes import (
    CodeToken,
    TokenKind,
    build_code_stream,
    describe_token,
)
from quill.core.reveal_nav import (
    EditableRegion,
    FlowView,
    announce_cell,
    build_flow_view,
    cell_at_flow_offset,
    cell_for_markup_offset,
    enclosing_region,
    line_end,
    line_home,
    move_char,
    move_line,
    move_word,
    region_source,
    splice_region,
)


def _item_label(token: CodeToken) -> str:
    """The text shown for a token in the structured list."""
    if token.kind is TokenKind.TEXT:
        return token.label
    return f"[{token.label}]"


class RevealCodesPane:
    """The Reveal Codes panel and its bidirectional caret-sync controller.

    *host* is the MainFrame; the pane uses ``host.editor`` (the active control),
    ``host._announce`` for speech, ``host.settings`` for the view/verbosity, and
    ``host._reveal_move_editor_caret(offset)`` to drive the editor caret without
    re-entrancy.
    """

    def __init__(self, wx: Any, parent: Any, host: Any) -> None:
        self._wx = wx
        self._host = host
        self._tokens: list[CodeToken] = []
        self._flow_view: FlowView = build_flow_view([])
        self._caret = 0  # index into the flow view's nav cells
        self._syncing = False  # guard against editor<->pane feedback loops
        self._entered = False  # has the region name been announced this visit?
        self._edit_region: EditableRegion | None = None  # active F2 edit, if any
        self._edit_original = ""  # region source at edit start, to detect changes

        self.panel = wx.Panel(parent)
        self.panel.SetName("Reveal Codes")
        sizer = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(self.panel, label="Reveal Codes")
        sizer.Add(label, 0, wx.LEFT | wx.TOP, 4)

        self._list = wx.ListBox(self.panel, style=wx.LB_SINGLE | wx.LB_NEEDED_SB)
        self._list.SetName("Reveal Codes list")
        sizer.Add(self._list, 1, wx.EXPAND | wx.ALL, 2)

        self._flow = wx.TextCtrl(
            self.panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP | wx.TE_PROCESS_ENTER,
        )
        self._flow.SetName("Reveal Codes (flowed)")
        sizer.Add(self._flow, 1, wx.EXPAND | wx.ALL, 2)

        self.panel.SetSizer(sizer)
        self._list.Bind(wx.EVT_LISTBOX, self._on_list_select)
        self._flow.Bind(wx.EVT_KEY_DOWN, self._on_flow_key)
        self._flow.Bind(wx.EVT_LEFT_UP, self._on_flow_click)
        self._flow.Bind(wx.EVT_SET_FOCUS, self._on_flow_focus)
        self._flow.Bind(wx.EVT_KILL_FOCUS, self._on_flow_blur)
        self._apply_view_mode()

    # -- view mode -------------------------------------------------------- #
    def _view_mode(self) -> str:
        mode = getattr(self._host.settings, "reveal_codes_view", "flowed")
        return "structured" if mode == "structured" else "flowed"

    def _apply_view_mode(self) -> None:
        flowed = self._view_mode() == "flowed"
        self._list.Show(not flowed)
        self._flow.Show(flowed)
        self.panel.Layout()

    def set_view(self, mode: str) -> None:
        self._host.settings.reveal_codes_view = "structured" if mode == "structured" else "flowed"
        self._apply_view_mode()
        self.rebuild()

    def _verbosity(self) -> str:
        return getattr(self._host.settings, "reveal_codes_verbosity", "balanced")

    def _announce(self, phrase: str) -> None:
        """Speak a bare phrase through the host's single announcement channel.

        No "Reveal Codes:" prefix — the region name is spoken once on entry
        (:meth:`focus`); after that each move speaks only itself, so arrowing does
        not repeat "Reveal Codes" on every keypress."""
        if phrase:
            self._host._announce(phrase)

    # -- population ------------------------------------------------------- #
    def rebuild(self) -> None:
        """Rebuild the token stream from the active editor and repopulate."""
        if self._edit_region is not None:
            # Do not yank the view out from under an in-progress F2 edit.
            return
        markup = self._editor_value()
        self._tokens = build_code_stream(markup)
        self._flow_view = build_flow_view(self._tokens)
        if self._view_mode() == "flowed":
            self._flow.ChangeValue(self._flow_view.text)
        else:
            self._list.Set([_item_label(token) for token in self._tokens])
        self.sync_from_editor()

    def _editor_value(self) -> str:
        editor = getattr(self._host, "editor", None)
        if editor is None:
            return ""
        try:
            return str(editor.GetValue())
        except Exception:  # noqa: BLE001 - some surfaces lack GetValue
            return ""

    # -- editor -> pane --------------------------------------------------- #
    def sync_from_editor(self) -> None:
        """Move the pane caret to match the editor's current caret offset."""
        if self._syncing or self._edit_region is not None:
            return
        editor = getattr(self._host, "editor", None)
        if editor is None:
            return
        try:
            offset = editor.GetInsertionPoint()
        except Exception:  # noqa: BLE001
            return
        self._syncing = True
        try:
            if self._view_mode() == "flowed":
                if self._flow_view.cells:
                    self._caret = cell_for_markup_offset(self._flow_view.cells, offset)
                    self._place_flow_caret()
            else:
                from quill.core.reveal_codes import token_at_markup_offset

                index = token_at_markup_offset(self._tokens, offset)
                if 0 <= index < self._list.GetCount():
                    self._list.SetSelection(index)
        finally:
            self._syncing = False

    def _place_flow_caret(self) -> None:
        """Put the visible caret at the current nav cell (no speech)."""
        cells = self._flow_view.cells
        if not cells:
            return
        self._caret = max(0, min(self._caret, len(cells) - 1))
        target = cells[self._caret].flow_start
        try:
            self._flow.SetInsertionPoint(min(target, self._flow.GetLastPosition()))
        except Exception:  # noqa: BLE001
            pass

    def _drive_editor_from_caret(self) -> None:
        """Move the editor caret to the current nav cell's markup offset."""
        cells = self._flow_view.cells
        if not cells:
            return
        cell = cells[max(0, min(self._caret, len(cells) - 1))]
        self._syncing = True
        try:
            self._host._reveal_move_editor_caret(cell.markup_offset)
        finally:
            self._syncing = False

    # -- flowed navigation (the interactive surface) ---------------------- #
    def _on_flow_focus(self, event: Any) -> None:
        event.Skip()

    def _on_flow_blur(self, event: Any) -> None:
        event.Skip()
        # Leaving the pane commits any open edit and re-arms the entry announcement.
        if self._edit_region is not None:
            self._commit_region_edit(announce=False)
        self._entered = False

    def _on_flow_click(self, event: Any) -> None:
        event.Skip()
        if self._syncing or self._view_mode() != "flowed" or self._edit_region is not None:
            return
        cells = self._flow_view.cells
        if not cells:
            return
        pos = self._flow.GetInsertionPoint()
        self._caret = cell_at_flow_offset(cells, pos)
        self._drive_editor_from_caret()
        self._announce(announce_cell(self._tokens, cells, self._caret, self._verbosity()))

    def _on_flow_key(self, event: Any) -> None:
        wx = self._wx
        key = event.GetKeyCode()

        if self._edit_region is not None:
            # In F2 edit mode the control is a normal editable field; we only claim
            # Enter (commit) and Escape (cancel) and let every other key edit.
            if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
                self._commit_region_edit()
                return
            if key == wx.WXK_ESCAPE:
                self._cancel_region_edit()
                return
            event.Skip()
            return

        if self._view_mode() != "flowed":
            event.Skip()
            return

        if key == wx.WXK_F2:
            self._begin_region_edit()
            return

        cells = self._flow_view.cells
        if not cells:
            event.Skip()
            return

        ctrl = event.ControlDown()
        handled = True
        if key == wx.WXK_LEFT:
            self._caret = (
                move_word(cells, self._caret, -1) if ctrl else move_char(cells, self._caret, -1)
            )
        elif key == wx.WXK_RIGHT:
            self._caret = (
                move_word(cells, self._caret, +1) if ctrl else move_char(cells, self._caret, +1)
            )
        elif key == wx.WXK_UP:
            self._caret = move_line(cells, self._caret, -1)
        elif key == wx.WXK_DOWN:
            self._caret = move_line(cells, self._caret, +1)
        elif key == wx.WXK_HOME:
            self._caret = 0 if ctrl else line_home(cells, self._caret)
        elif key == wx.WXK_END:
            self._caret = len(cells) - 1 if ctrl else line_end(cells, self._caret)
        else:
            handled = False

        if not handled:
            event.Skip()
            return

        # We consume the key (no event.Skip) so the caret moves under our control,
        # then move both the flowed caret and the editor caret to the new cell.
        # The flowed control is a real text control, so the screen reader narrates
        # the caret move itself for plain text — character, word, and line, at the
        # right granularity. We therefore speak ONLY when the caret lands on a code,
        # where the raw "[Bold On]" bracket text is not what we want heard; that is
        # the single voice for codes and avoids the double-speak the SR + our own
        # announcement produced on every character move.
        self._place_flow_caret()
        self._drive_editor_from_caret()
        if cells[self._caret].is_code:
            self._announce(announce_cell(self._tokens, cells, self._caret, self._verbosity()))

    # -- F2 region editing ------------------------------------------------ #
    def _begin_region_edit(self) -> None:
        cells = self._flow_view.cells
        if not cells:
            return
        cell = cells[max(0, min(self._caret, len(cells) - 1))]
        region = enclosing_region(self._tokens, cell.token_index)
        if region is None:
            self._announce("Not inside a formatting code. Move onto text between codes to edit.")
            return
        source = region_source(self._editor_value(), region)
        self._edit_region = region
        self._edit_original = source
        # Show the whole region's source and let the caret roam it freely — that is
        # the "restrict the cursor to that region" the request asks for. A region
        # carrying a tab or a nested code edits as one unit; nested codes appear as
        # their markup and are spliced straight back on commit.
        self._flow.SetEditable(True)
        self._flow.ChangeValue(source)
        self._flow.SetInsertionPointEnd()
        self._announce(
            f"Editing {region.on_label.lower()} region. "
            f"Type to edit. Enter to apply, Escape to cancel."
        )

    def _commit_region_edit(self, *, announce: bool = True) -> None:
        region = self._edit_region
        if region is None:
            return
        new_text = str(self._flow.GetValue())
        original = self._edit_original
        self._end_region_edit()
        editor = getattr(self._host, "editor", None)
        if editor is not None and new_text != original:
            try:
                markup = str(editor.GetValue())
                editor.SetValue(splice_region(markup, region, new_text))
                editor.SetInsertionPoint(region.markup_start + len(new_text))
            except Exception:  # noqa: BLE001
                pass
        self.rebuild()
        if announce:
            self._announce(f"Applied. {region.on_label} region is now {new_text!r}.")

    def _cancel_region_edit(self) -> None:
        region = self._edit_region
        self._end_region_edit()
        self.rebuild()
        if region is not None:
            self._announce("Edit cancelled.")

    def _end_region_edit(self) -> None:
        """Restore the read-only flowed view after an edit ends (commit or cancel)."""
        self._edit_region = None
        try:
            self._flow.SetEditable(False)
        except Exception:  # noqa: BLE001
            pass

    # -- structured navigation -------------------------------------------- #
    def _on_list_select(self, event: Any) -> None:
        if self._syncing:
            return
        index = self._list.GetSelection()
        if not 0 <= index < len(self._tokens):
            return
        token = self._tokens[index]
        self._syncing = True
        try:
            self._host._reveal_move_editor_caret(token.markup_start)
        finally:
            self._syncing = False
        # The ListBox item is read by the screen reader itself; we only mirror the
        # rich phrase to the status bar *silently* so there is no second voice.
        phrase = describe_token(self._tokens, index, self._verbosity())
        self._host._set_status_quiet(f"Reveal Codes: {phrase}")

    # -- in-pane "next/previous code" commands ---------------------------- #
    def _current_token_index(self) -> int:
        if self._view_mode() == "flowed":
            cells = self._flow_view.cells
            if cells:
                return cells[max(0, min(self._caret, len(cells) - 1))].token_index
            return 0
        return self._list.GetSelection()

    def _select_token(self, token_index: int) -> None:
        if not 0 <= token_index < len(self._tokens):
            return
        if self._view_mode() == "flowed":
            cells = self._flow_view.cells
            for i, cell in enumerate(cells):
                if cell.token_index == token_index:
                    self._caret = i
                    break
            self._place_flow_caret()
            self._drive_editor_from_caret()
            self._announce(announce_cell(self._tokens, cells, self._caret, self._verbosity()))
        else:
            self._list.SetSelection(token_index)
            self._on_list_select(None)

    def next_code(self) -> None:
        start = self._current_token_index()
        for i in range(start + 1, len(self._tokens)):
            if self._tokens[i].is_code:
                self._select_token(i)
                return
        self._host._set_status("Reveal Codes: no further code.")

    def previous_code(self) -> None:
        start = self._current_token_index()
        for i in range(start - 1, -1, -1):
            if self._tokens[i].is_code:
                self._select_token(i)
                return
        self._host._set_status("Reveal Codes: no earlier code.")

    def go_to_pair(self) -> None:
        index = self._current_token_index()
        if 0 <= index < len(self._tokens) and self._tokens[index].pair_index is not None:
            self._select_token(self._tokens[index].pair_index)
        else:
            self._host._set_status("Reveal Codes: not a paired code.")

    # -- focus ------------------------------------------------------------ #
    def focus(self) -> None:
        """Move focus into the pane, landing on the editor's current position.

        Announces the region name **once** per visit; subsequent arrow moves speak
        only the character/code/line, never "Reveal Codes" again."""
        self.sync_from_editor()
        flowed = self._view_mode() == "flowed"
        target = self._flow if flowed else self._list
        try:
            target.SetFocus()
        except Exception:  # noqa: BLE001
            pass
        if not self._entered:
            self._entered = True
            if flowed and self._flow_view.cells:
                here = announce_cell(
                    self._tokens, self._flow_view.cells, self._caret, self._verbosity()
                )
                self._announce(f"Reveal Codes. {here}" if here else "Reveal Codes.")
            else:
                self._announce("Reveal Codes.")

    def has_focus(self) -> bool:
        try:
            focused = self._wx.Window.FindFocus()
        except Exception:  # noqa: BLE001
            return False
        win = focused
        while win is not None:
            if win is self.panel:
                return True
            getp = getattr(win, "GetParent", None)
            win = getp() if callable(getp) else None
        return False
