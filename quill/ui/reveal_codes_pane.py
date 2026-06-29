"""Reveal Codes pane — the wx view + caret-sync controller.

A WordPerfect-style Reveal Codes surface, screen-reader-first. It docks below the
editor and shows the active document as a stream of bracketed code tokens and
visible text (see ``quill/core/reveal_codes.py`` for the wx-free model). Two
presentations share the same token stream:

* **Structured** — a read-only ``wx.ListBox``: one navigable, individually-announced
  item per token. The most accessible mode and the default.
* **Flowed** — a read-only ``wx.TextCtrl`` rendering the codes inline within the
  running text (``[Bold On]Hello[Bold Off]``), the closest match to the classic
  visual/braille Reveal Codes screen.

The pane keeps its caret in sync with the editor's: moving here moves the editor
caret to the matching markup offset, and the editor's caret position selects the
matching token here. All wx lives in this module; the token logic and offset math
are the pure ``core.reveal_codes`` functions.
"""

from __future__ import annotations

from typing import Any

from quill.core.reveal_codes import (
    CodeToken,
    TokenKind,
    build_code_stream,
    describe_token,
    token_at_markup_offset,
)

_CODE_KINDS = {
    TokenKind.FORMAT_ON,
    TokenKind.FORMAT_OFF,
    TokenKind.BLOCK,
    TokenKind.STRUCTURE,
    TokenKind.INVISIBLE,
}


def _item_label(token: CodeToken) -> str:
    """The text shown for a token in the structured list."""
    if token.kind is TokenKind.TEXT:
        return token.label
    return f"[{token.label}]"


def _flowed_text(tokens: list[CodeToken]) -> str:
    """The inline rendering: codes as bracketed tokens within the running text."""
    parts: list[str] = []
    for token in tokens:
        if token.kind is TokenKind.TEXT:
            parts.append(token.label)
        elif token.kind is TokenKind.STRUCTURE and token.label.endswith("Hard Return"):
            parts.append("[¶]\n")
        else:
            parts.append(f"[{token.label}]")
    return "".join(parts)


class RevealCodesPane:
    """The Reveal Codes panel and its bidirectional caret-sync controller.

    *host* is the MainFrame; the pane uses ``host.editor`` (the active control),
    ``host._announce`` / ``host._set_status`` for speech, ``host.settings`` for the
    view/verbosity, and ``host._reveal_move_editor_caret(offset)`` to drive the
    editor caret without re-entrancy.
    """

    def __init__(self, wx: Any, parent: Any, host: Any) -> None:
        self._wx = wx
        self._host = host
        self._tokens: list[CodeToken] = []
        self._syncing = False  # guard against editor<->pane feedback loops

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
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP,
        )
        self._flow.SetName("Reveal Codes (flowed)")
        sizer.Add(self._flow, 1, wx.EXPAND | wx.ALL, 2)

        self.panel.SetSizer(sizer)
        self._list.Bind(wx.EVT_LISTBOX, self._on_list_select)
        self._flow.Bind(wx.EVT_KEY_UP, self._on_flow_caret)
        self._flow.Bind(wx.EVT_LEFT_UP, self._on_flow_caret)
        self._apply_view_mode()

    # -- view mode -------------------------------------------------------- #
    def _view_mode(self) -> str:
        mode = getattr(self._host.settings, "reveal_codes_view", "structured")
        return "flowed" if mode == "flowed" else "structured"

    def _apply_view_mode(self) -> None:
        flowed = self._view_mode() == "flowed"
        self._list.Show(not flowed)
        self._flow.Show(flowed)
        self.panel.Layout()

    def set_view(self, mode: str) -> None:
        self._host.settings.reveal_codes_view = "flowed" if mode == "flowed" else "structured"
        self._apply_view_mode()
        self.rebuild()

    # -- population ------------------------------------------------------- #
    def rebuild(self) -> None:
        """Rebuild the token stream from the active editor and repopulate."""
        markup = ""
        editor = getattr(self._host, "editor", None)
        if editor is not None:
            try:
                markup = editor.GetValue()
            except Exception:  # noqa: BLE001 - some surfaces lack GetValue
                markup = ""
        self._tokens = build_code_stream(markup)
        if self._view_mode() == "flowed":
            self._flow.ChangeValue(_flowed_text(self._tokens))
        else:
            self._list.Set([_item_label(token) for token in self._tokens])
        self.sync_from_editor()

    # -- editor -> pane --------------------------------------------------- #
    def sync_from_editor(self) -> None:
        """Highlight the token matching the editor's current caret offset."""
        if self._syncing or not self._tokens:
            return
        editor = getattr(self._host, "editor", None)
        if editor is None:
            return
        try:
            offset = editor.GetInsertionPoint()
        except Exception:  # noqa: BLE001
            return
        index = token_at_markup_offset(self._tokens, offset)
        self._syncing = True
        try:
            if self._view_mode() == "flowed":
                token = self._tokens[index]
                # Place the flowed caret near the token's start (visible offset is a
                # reasonable proxy in the flowed rendering).
                self._flow.SetInsertionPoint(min(token.visible_start, self._flow.GetLastPosition()))
            else:
                if 0 <= index < self._list.GetCount():
                    self._list.SetSelection(index)
        finally:
            self._syncing = False

    # -- pane -> editor --------------------------------------------------- #
    def _on_list_select(self, event: Any) -> None:
        if self._syncing:
            return
        index = self._list.GetSelection()
        self._goto_token(index)

    def _on_flow_caret(self, event: Any) -> None:
        event.Skip()
        if self._syncing or self._view_mode() != "flowed":
            return
        pos = self._flow.GetInsertionPoint()
        # Map the flowed caret (visible-ish offset) to the nearest token.
        index = 0
        for i, token in enumerate(self._tokens):
            if token.visible_start <= pos:
                index = i
            else:
                break
        self._goto_token(index, announce=False)

    def _goto_token(self, index: int, *, announce: bool = True) -> None:
        if not 0 <= index < len(self._tokens):
            return
        token = self._tokens[index]
        self._syncing = True
        try:
            self._host._reveal_move_editor_caret(token.markup_start)
        finally:
            self._syncing = False
        if announce:
            verbosity = getattr(self._host.settings, "reveal_codes_verbosity", "balanced")
            phrase = describe_token(self._tokens, index, verbosity)
            self._host._set_status(f"Reveal Codes: {phrase}")

    # -- in-pane navigation commands -------------------------------------- #
    def _selected_index(self) -> int:
        if self._view_mode() == "flowed":
            pos = self._flow.GetInsertionPoint()
            index = 0
            for i, token in enumerate(self._tokens):
                if token.visible_start <= pos:
                    index = i
                else:
                    break
            return index
        return self._list.GetSelection()

    def _select_index(self, index: int) -> None:
        if not 0 <= index < len(self._tokens):
            return
        if self._view_mode() == "flowed":
            self._flow.SetInsertionPoint(
                min(self._tokens[index].visible_start, self._flow.GetLastPosition())
            )
        else:
            self._list.SetSelection(index)
        self._goto_token(index)

    def next_code(self) -> None:
        start = self._selected_index()
        for i in range(start + 1, len(self._tokens)):
            if self._tokens[i].is_code:
                self._select_index(i)
                return
        self._host._set_status("Reveal Codes: no further code.")

    def previous_code(self) -> None:
        start = self._selected_index()
        for i in range(start - 1, -1, -1):
            if self._tokens[i].is_code:
                self._select_index(i)
                return
        self._host._set_status("Reveal Codes: no earlier code.")

    def go_to_pair(self) -> None:
        index = self._selected_index()
        if 0 <= index < len(self._tokens) and self._tokens[index].pair_index is not None:
            self._select_index(self._tokens[index].pair_index)
        else:
            self._host._set_status("Reveal Codes: not a paired code.")

    # -- focus ------------------------------------------------------------ #
    def focus(self) -> None:
        """Move focus into the pane, landing on the editor's current token."""
        self.sync_from_editor()
        target = self._flow if self._view_mode() == "flowed" else self._list
        try:
            target.SetFocus()
        except Exception:  # noqa: BLE001
            pass

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
