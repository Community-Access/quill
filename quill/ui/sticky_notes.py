from __future__ import annotations

import html
import json

from quill.core.sticky_notes import (
    StickyNote,
    delete_sticky_note,
    load_sticky_notes,
    save_sticky_note,
)
from quill.ui.dialog_contract import (
    apply_modal_ids,
    set_accessible_name,
    show_message_box,
    show_modal_dialog,
)

_SR_DETECTED: bool | None = None


def _is_sr_active() -> bool:
    global _SR_DETECTED
    if _SR_DETECTED is None:
        try:
            from quill.platform.sr_detect import detect_screen_reader

            _SR_DETECTED = detect_screen_reader().detected
        except Exception:  # noqa: BLE001
            _SR_DETECTED = False
    return bool(_SR_DETECTED)


class StickyNoteEditorDialog:
    """Title + body editor for a sticky note.

    Rendered as a web form on the shared ``AccessibleWebView`` (the same
    accessible WebView the Ask Quill chat uses), so focus lands on the Title
    field and screen readers get real labelled fields. Falls back to native wx
    text fields if the WebView backend is unavailable. The note model keeps
    "first non-empty line is the title", so Title + Body are recombined into a
    single body string on save.
    """

    def __init__(self, parent: object, note: StickyNote | None = None) -> None:
        import wx

        self._wx = wx
        self._note = note
        self._result: str | None = None
        self._native_title = None
        self._native_body = None

        title_value, _, body_value = (note.body if note is not None else "").partition("\n")

        self.dialog = wx.Dialog(
            parent,
            title="New Sticky Note" if note is None else "Edit Sticky Note",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize((720, 560))
        sizer = wx.BoxSizer(wx.VERTICAL)

        self._webview = None
        if not _is_sr_active():
            try:
                from wx_accessible_webview import AccessibleWebView

                self._webview = AccessibleWebView(
                    self.dialog,
                    title="Sticky Note Editor",
                    handler_name="awv",
                    on_message=self._on_message,
                    on_close=self._cancel,
                    escape_to_close=True,
                    initial_html=self._form_html(title_value, body_value),
                )
            except Exception:  # noqa: BLE001
                self._webview = None

        if self._webview is not None and self._webview.using_webview:
            sizer.Add(self._webview.control, 1, wx.EXPAND)
        else:
            self._build_native_fallback(sizer, title_value, body_value)
        self.dialog.SetSizer(sizer)
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)

    def show_modal_and_get_body(self) -> str | None:
        self.dialog.CentreOnParent()
        if self._native_title is not None:
            self._wx.CallAfter(self._native_title.SetFocus)
        try:
            result = show_modal_dialog(self.dialog, "Sticky Note Editor")
            if result != self._wx.ID_OK:
                return None
            if self._native_title is not None:
                return self._combine(self._native_title.GetValue(), self._native_body.GetValue())
            return self._result
        finally:
            self.dialog.Destroy()

    # -- web form ----------------------------------------------------------

    def _form_html(self, title_value: str, body_value: str) -> str:
        title_attr = html.escape(title_value, quote=True)
        body_text = html.escape(body_value)
        return (
            "<h1>Sticky note</h1>"
            "<p><label for='note-title'>Title</label><br>"
            f"<input id='note-title' type='text' value=\"{title_attr}\" "
            "style='width:100%;font-size:1rem;padding:6px'></p>"
            "<p><label for='note-body'>Note</label><br>"
            "<textarea id='note-body' rows='14' "
            f"style='width:100%;font-size:1rem;padding:6px'>{body_text}</textarea></p>"
            "<p><button type='button' id='note-save'>Save</button> "
            "<button type='button' id='note-cancel'>Cancel</button></p>"
            "<script>(function(){"
            "function post(o){if(window.awv&&window.awv.postMessage)"
            "{window.awv.postMessage(JSON.stringify(o));}}"
            "var t=document.getElementById('note-title'),"
            "b=document.getElementById('note-body');"
            "document.getElementById('note-save').addEventListener('click',function(){"
            "post({type:'save',title:t.value,body:b.value});});"
            "document.getElementById('note-cancel').addEventListener('click',function(){"
            "post({type:'cancel'});});"
            "setTimeout(function(){if(t){t.focus();t.select();}},60);"
            "})();</script>"
        )

    def _on_message(self, data: object) -> None:
        payload = data
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:  # noqa: BLE001
                return
        if not isinstance(payload, dict):
            return
        kind = payload.get("type")
        if kind == "save":
            self._result = self._combine(
                str(payload.get("title", "")),
                str(payload.get("body", "")),
            )
            self.dialog.EndModal(self._wx.ID_OK)
        elif kind in ("cancel", "close"):
            self.dialog.EndModal(self._wx.ID_CANCEL)

    def _cancel(self) -> None:
        self.dialog.EndModal(self._wx.ID_CANCEL)

    @staticmethod
    def _combine(title: str, body: str) -> str:
        title = title.strip()
        body = body.rstrip()
        if title and body:
            return f"{title}\n{body}"
        return title or body

    # -- native fallback ---------------------------------------------------

    def _build_native_fallback(self, sizer: object, title_value: str, body_value: str) -> None:
        wx = self._wx
        sizer.Add(
            wx.StaticText(self.dialog, label="Title"),
            0,
            wx.LEFT | wx.RIGHT | wx.TOP,
            8,
        )
        self._native_title = wx.TextCtrl(self.dialog, value=title_value)
        self._native_title.SetName("Title")
        sizer.Add(self._native_title, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        sizer.Add(wx.StaticText(self.dialog, label="Note"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        # No TE_PROCESS_TAB: a note is prose, so Tab must move focus to the buttons
        # rather than insert a tab character (keyboard-trap fix).
        self._native_body = wx.TextCtrl(self.dialog, value=body_value, style=wx.TE_MULTILINE)
        self._native_body.SetName("Note")
        sizer.Add(self._native_body, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        buttons = self.dialog.CreateButtonSizer(wx.OK | wx.CANCEL)
        if buttons is not None:
            # FindWindowById is a Window method, not a sizer method (buttons are
            # children of the dialog) — calling it on the sizer crashes on
            # Windows with AttributeError.
            ok_button = self.dialog.FindWindowById(wx.ID_OK)
            if ok_button is not None:
                ok_button.SetLabel("Save")
            sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)


class StickyNotesVaultDialog:
    def __init__(self, parent: object) -> None:
        import wx

        self._wx = wx
        self.dialog = wx.Dialog(
            parent,
            title="Quill Notes Vault",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize((900, 620))
        self._notes: list[StickyNote] = []

        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                self.dialog,
                label=(
                    "Manage global sticky notes. Delete removes the selected note. "
                    "Ctrl+C copies it."
                ),
            ),
            0,
            wx.EXPAND | wx.ALL,
            8,
        )
        self.list = wx.ListCtrl(
            self.dialog,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SIMPLE,
        )
        set_accessible_name(self.list, "Sticky notes")
        self.list.AppendColumn("Title", width=260)
        self.list.AppendColumn("Updated", width=180)
        self.list.AppendColumn("Preview", width=420)
        root.Add(self.list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.preview = wx.TextCtrl(
            self.dialog,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.BORDER_SIMPLE,
            size=(-1, 140),
        )
        set_accessible_name(self.preview, "Note preview")
        root.Add(self.preview, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.new_button = wx.Button(self.dialog, label="New")
        self.edit_button = wx.Button(self.dialog, label="Edit")
        self.copy_button = wx.Button(self.dialog, label="Copy")
        self.delete_button = wx.Button(self.dialog, label="Delete")
        self.close_button = wx.Button(self.dialog, id=wx.ID_OK, label="Close")
        for control in (
            self.new_button,
            self.edit_button,
            self.copy_button,
            self.delete_button,
            self.close_button,
        ):
            buttons.Add(control, 0, wx.RIGHT, 8)
        buttons.AddStretchSpacer(1)
        root.Add(buttons, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        self.dialog.SetSizer(root)

        self.new_button.Bind(wx.EVT_BUTTON, lambda _e: self._create_note())
        self.edit_button.Bind(wx.EVT_BUTTON, lambda _e: self._edit_selected())
        self.copy_button.Bind(wx.EVT_BUTTON, lambda _e: self._copy_selected())
        self.delete_button.Bind(wx.EVT_BUTTON, lambda _e: self._delete_selected())
        self.close_button.Bind(wx.EVT_BUTTON, lambda _e: self.dialog.EndModal(wx.ID_OK))
        self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_selection_changed)
        self.list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, lambda _e: self._edit_selected())
        self.list.Bind(wx.EVT_CONTEXT_MENU, self._on_context_menu)
        self.dialog.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_OK)
        self._refresh()

    def show_modal(self) -> None:
        self.dialog.CentreOnParent()
        try:
            show_modal_dialog(self.dialog, "Quill Notes Vault")
        finally:
            self.dialog.Destroy()

    def _refresh(self, select_note_id: str | None = None) -> None:
        wx = self._wx
        self._notes = load_sticky_notes()
        self.list.DeleteAllItems()
        selected_index = 0
        for index, note in enumerate(self._notes):
            item = self.list.InsertItem(index, note.title)
            self.list.SetItem(item, 1, note.updated_at.replace("T", " ")[:19])
            preview = note.body.splitlines()[1] if len(note.body.splitlines()) > 1 else note.body
            self.list.SetItem(item, 2, preview[:120])
            if select_note_id is not None and note.id == select_note_id:
                selected_index = index
        if self._notes:
            self.list.SetItemState(
                selected_index,
                wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED,
                wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED,
            )
            self.list.EnsureVisible(selected_index)
        self._update_preview()

    def _selected_note(self) -> StickyNote | None:
        index = self.list.GetFirstSelected()
        if index == -1 or index >= len(self._notes):
            return None
        return self._notes[index]

    def _update_preview(self) -> None:
        note = self._selected_note()
        if note is None:
            self.preview.SetValue("No sticky note selected.")
            return
        self.preview.SetValue(
            f"Title: {note.title}\nCreated: {note.created_at}\n"
            f"Updated: {note.updated_at}\n\n{note.body}"
        )

    def _on_selection_changed(self, _event: object) -> None:
        self._update_preview()

    def _on_char_hook(self, event: object) -> None:
        key_code = event.GetKeyCode()
        if key_code == self._wx.WXK_DELETE:
            self._delete_selected()
            return
        if key_code in (self._wx.WXK_RETURN, self._wx.WXK_NUMPAD_ENTER):
            self._edit_selected()
            return
        if key_code == ord("C") and event.ControlDown():
            self._copy_selected()
            return
        if key_code == self._wx.WXK_F10 and event.ShiftDown():
            self._show_context_menu()
            return
        if key_code == getattr(self._wx, "WXK_MENU", -1):
            self._show_context_menu()
            return
        event.Skip()

    def _on_context_menu(self, event: object) -> None:
        self._show_context_menu()

    def _show_context_menu(self) -> None:
        menu = self._wx.Menu()
        new_id = self._wx.NewIdRef()
        edit_id = self._wx.NewIdRef()
        copy_id = self._wx.NewIdRef()
        delete_id = self._wx.NewIdRef()
        menu.Append(new_id, "New Sticky Note")
        menu.Append(edit_id, "Edit Sticky Note")
        menu.Append(copy_id, "Copy Sticky Note")
        menu.Append(delete_id, "Delete Sticky Note")
        menu.Bind(self._wx.EVT_MENU, lambda _e: self._create_note(), id=new_id)
        menu.Bind(self._wx.EVT_MENU, lambda _e: self._edit_selected(), id=edit_id)
        menu.Bind(self._wx.EVT_MENU, lambda _e: self._copy_selected(), id=copy_id)
        menu.Bind(self._wx.EVT_MENU, lambda _e: self._delete_selected(), id=delete_id)
        self.list.PopupMenu(menu)
        menu.Destroy()

    def _create_note(self) -> None:
        editor = StickyNoteEditorDialog(self.dialog)
        body = editor.show_modal_and_get_body()
        if body is None:
            return
        note = save_sticky_note(body)
        self._refresh(select_note_id=note.id)

    def _edit_selected(self) -> None:
        note = self._selected_note()
        if note is None:
            return
        editor = StickyNoteEditorDialog(self.dialog, note=note)
        body = editor.show_modal_and_get_body()
        if body is None:
            return
        updated = save_sticky_note(body, note_id=note.id)
        self._refresh(select_note_id=updated.id)

    def _copy_selected(self) -> None:
        note = self._selected_note()
        if note is None:
            return
        clipboard = self._wx.TheClipboard
        if not clipboard.Open():
            return
        try:
            clipboard.SetData(self._wx.TextDataObject(note.body))
        finally:
            clipboard.Close()

    def _delete_selected(self) -> None:
        note = self._selected_note()
        if note is None:
            return
        if (
            show_message_box(
                f'Delete sticky note "{note.title}"?',
                "Delete Sticky Note",
                self._wx.ICON_WARNING | self._wx.YES_NO | self._wx.NO_DEFAULT,
                self.dialog,
            )
            != self._wx.YES
        ):
            return
        if delete_sticky_note(note.id):
            self._refresh()
