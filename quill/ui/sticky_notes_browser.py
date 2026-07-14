"""The Sticky Notes browser: search, arrow, preview, edit -- from anywhere.

A fast, keyboard-first way to find one note among many: a search field
filters the list live (title + body, case-insensitive), Down-arrow moves
into the results, Tab lands on a read-only multi-line preview of the
selected note, and Edit opens the full editor. Openable via a system-wide
global hotkey (see main_frame's global-hotkey table), so it works even when
QUILL is minimized to the tray -- the frame is restored first, then the
browser opens.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.sticky_notes import StickyNote, load_sticky_notes
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name


def filter_notes(notes: list[StickyNote], query: str) -> list[StickyNote]:
    """Notes whose title or body contains *query* (case-insensitive);
    an empty query returns everything, newest first (pure, testable)."""
    ordered = sorted(notes, key=lambda n: n.updated_at, reverse=True)
    needle = query.strip().casefold()
    if not needle:
        return ordered
    return [n for n in ordered if needle in n.title.casefold() or needle in n.body.casefold()]


class StickyNotesBrowserDialog:
    """Search + list + preview + Edit/Close; ``show()`` blocks modally."""

    def __init__(
        self,
        parent: object,
        *,
        on_edit: Callable[[str], None] | None = None,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._on_edit = on_edit
        self._announce = announce_cb or (lambda _m: None)
        self._all_notes: list[StickyNote] = load_sticky_notes()
        self._visible: list[StickyNote] = []

        self.dialog = wx.Dialog(
            parent,
            title="Sticky Notes Browser",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize((640, 480))
        root = wx.BoxSizer(wx.VERTICAL)

        search_label = wx.StaticText(self.dialog, label="&Search notes:")
        root.Add(search_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self._search = wx.TextCtrl(self.dialog)
        set_accessible_name(self._search, "Search notes")
        root.Add(self._search, 0, wx.EXPAND | wx.ALL, 8)

        list_label = wx.StaticText(self.dialog, label="&Notes:")
        root.Add(list_label, 0, wx.LEFT | wx.RIGHT, 8)
        self._list = wx.ListBox(self.dialog)
        set_accessible_name(self._list, "Notes matching the search, newest first")
        root.Add(self._list, 1, wx.EXPAND | wx.ALL, 8)

        preview_label = wx.StaticText(self.dialog, label="Note &preview:")
        root.Add(preview_label, 0, wx.LEFT | wx.RIGHT, 8)
        self._preview = wx.TextCtrl(
            self.dialog, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP
        )
        set_accessible_name(self._preview, "Selected note's full text, read-only")
        self._preview.SetMinSize((-1, 140))
        root.Add(self._preview, 1, wx.EXPAND | wx.ALL, 8)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._edit_btn = wx.Button(self.dialog, label="&Edit...")
        set_accessible_name(self._edit_btn, "Edit the selected note")
        close_btn = wx.Button(self.dialog, id=wx.ID_CANCEL, label="&Close")
        buttons.AddStretchSpacer()
        buttons.Add(self._edit_btn, 0, wx.RIGHT, 6)
        buttons.Add(close_btn, 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)

        self.dialog.SetSizer(root)

        self._search.Bind(wx.EVT_TEXT, lambda _e: self._reload())
        self._search.Bind(wx.EVT_KEY_DOWN, self._on_search_key)
        self._list.Bind(wx.EVT_LISTBOX, lambda _e: self._sync_preview())
        self._list.Bind(wx.EVT_LISTBOX_DCLICK, lambda _e: self._edit_selected())
        self._list.Bind(wx.EVT_KEY_DOWN, self._on_list_key)
        self._edit_btn.Bind(wx.EVT_BUTTON, lambda _e: self._edit_selected())

        self._reload()

    # -- data -----------------------------------------------------------------

    def _reload(self) -> None:
        self._visible = filter_notes(self._all_notes, self._search.GetValue())
        self._list.Set([self._label(n) for n in self._visible])
        if self._visible:
            self._list.SetSelection(0)
        self._sync_preview()

    def _label(self, note: StickyNote) -> str:
        date = note.updated_at[:10]
        return f"{note.title} ({date})" if date else note.title

    def _selected_note(self) -> StickyNote | None:
        index = self._list.GetSelection()
        if 0 <= index < len(self._visible):
            return self._visible[index]
        return None

    def _sync_preview(self) -> None:
        note = self._selected_note()
        self._preview.SetValue(note.body if note is not None else "")
        self._edit_btn.Enable(note is not None)

    # -- keys -------------------------------------------------------------------

    def _on_search_key(self, event: object) -> None:
        wx = self._wx
        code = event.GetKeyCode()
        if code == wx.WXK_DOWN and self._visible:
            # Down from the search box lands in the results, EdSharp-style.
            self._list.SetFocus()
            return
        if code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER) and self._visible:
            self._edit_selected()
            return
        event.Skip()

    def _on_list_key(self, event: object) -> None:
        wx = self._wx
        code = event.GetKeyCode()
        if code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self._edit_selected()
            return
        event.Skip()

    # -- actions --------------------------------------------------------------------

    def _edit_selected(self) -> None:
        note = self._selected_note()
        if note is None or self._on_edit is None:
            return
        self.dialog.EndModal(self._wx.ID_OK)
        self._on_edit(note.id)

    # -- lifecycle ------------------------------------------------------------

    def show(self) -> None:
        from quill.ui.dialog_contract import show_modal_dialog

        wx = self._wx
        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, escape_id=wx.ID_CANCEL)
        count = len(self._all_notes)
        self._announce(f"Sticky Notes Browser: {count} note(s). Type to search, Down for results.")
        self._search.SetFocus()
        show_modal_dialog(self.dialog)
        self.dialog.Destroy()
