"""The List Speech Templates editor (both Workbenches: Tools > List Speech Templates).

Choose a kind of list, pick the usual wording, a preset (Brief, Balanced,
Detailed) or a saved template, then arrange the fields it says: Add, Remove,
Move Up and Move Down (Alt+Up and Alt+Down on the list too), a separator, field
labels on or off, and what to say for an empty field. The sample row below is
spoken exactly as the real rows will be, and Hear Preview says it aloud.

Nothing here needs a mouse and nothing is announced that the screen reader
already says: each action says one sentence about its outcome. The rules live
in :mod:`quill.core.list_speech.editor_state`; this file only draws them.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import Any

from quill.core.list_speech import editor_state as es
from quill.core.list_speech.catalog import LIST_TYPES
from quill.core.list_speech.store import load_library, save_library
from quill.core.list_speech.template import SEPARATOR_CHOICES
from quill.ui.dialog_contract import apply_modal_ids, bind_close_button, show_modal_dialog
from quill.ui.dpi import dip_size
from quill.ui.list_speech_transfer import export_to_file, import_from_file

__all__ = ["ListSpeechDialog", "show_list_speech_editor"]

_CUSTOM_SEPARATOR = "Custom"


class ListSpeechDialog:
    def __init__(
        self,
        parent: object,
        *,
        list_type: str = "",
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _message: None)
        library, notice = load_library()
        start_type = list_type if any(t.id == list_type for t in LIST_TYPES) else LIST_TYPES[0].id
        self._state = es.start(library, start_type)
        self._sources: list[str] = []
        self._building = False
        self.dialog = wx.Dialog(
            parent,
            title="List Speech Templates",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(dip_size(self.dialog, 520, 560))
        self._build(wx)
        self._refresh()
        if notice:
            self._say(notice)

    # -- layout --------------------------------------------------------------------

    def _build(self, wx: Any) -> None:
        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)

        def labelled(text: str, make: Callable[[], Any]) -> Any:
            # The label is created first so it precedes its control in tab and
            # reading order (A11Y-Z-ORDER).
            root.Add(wx.StaticText(panel, label=text), 0, wx.LEFT | wx.TOP, 8)
            control = make()
            root.Add(control, 0, wx.EXPAND | wx.ALL, 6)
            return control

        self._types = labelled(
            "&List:", lambda: wx.Choice(panel, choices=[t.title for t in LIST_TYPES])
        )
        self._types.SetName("List type")
        self._types.SetHelpText("Which kind of list these choices are for.")
        self._source = labelled("&Template:", lambda: wx.Choice(panel, choices=[]))
        self._source.SetName("Template")
        self._source.SetHelpText(
            "The usual wording, a built-in preset (Brief, Balanced or Detailed) or a template "
            "you saved. Changing the fields below turns it into a custom template."
        )

        self._fields = labelled("Fields in spoken &order:", lambda: wx.ListBox(panel, choices=[]))
        self._fields.SetName("Fields in spoken order")
        self._fields.SetHelpText(
            "The fields a row says, first to last. Alt+Up and Alt+Down move the selected field, "
            "and Delete removes it."
        )
        moves = wx.BoxSizer(wx.HORIZONTAL)
        self._up = self._button(panel, "Move &Up", "Moves the selected field earlier in the row.")
        self._down = self._button(panel, "Move &Down", "Moves the selected field later.")
        self._remove = self._button(panel, "&Remove", "Takes the selected field out of the row.")
        for button in (self._up, self._down, self._remove):
            moves.Add(button, 0, wx.RIGHT, 6)
        root.Add(moves, 0, wx.LEFT | wx.BOTTOM, 8)

        self._picker = labelled("Choose &field:", lambda: wx.Choice(panel, choices=[]))
        self._picker.SetName("Field to add")
        self._picker.SetHelpText("A field this list offers that the row does not say yet.")
        self._add = self._button(panel, "&Add", "Adds the chosen field at the end of the row.")
        root.Add(self._add, 0, wx.LEFT | wx.BOTTOM, 8)

        names = [name for _text, name in SEPARATOR_CHOICES]
        self._separator = labelled(
            "Separator (&between fields):",
            lambda: wx.Choice(panel, choices=[*names, _CUSTOM_SEPARATOR]),
        )
        self._separator.SetName("Separator")
        self._separator.SetHelpText("What is said between one field and the next.")
        self._labels = wx.CheckBox(panel, label="Say field la&bels")
        self._labels.SetHelpText("Introduces a value with its name, such as author or updated.")
        self._omit = wx.CheckBox(panel, label="Leave out &empty fields")
        self._omit.SetHelpText("Skips a field that has no value. Off speaks the text below.")
        root.Add(self._labels, 0, wx.LEFT | wx.TOP, 8)
        root.Add(self._omit, 0, wx.LEFT | wx.TOP, 8)
        self._fallback = labelled("Empty-field te&xt:", lambda: wx.TextCtrl(panel))
        self._fallback.SetName("Text for an empty field")
        self._fallback.SetHelpText("Said in place of an empty field when empty fields are kept.")

        self._preview = labelled(
            "Sample row &preview:",
            lambda: wx.TextCtrl(
                panel,
                style=wx.TE_MULTILINE | wx.TE_READONLY,
                size=wx.Size(-1, self.dialog.FromDIP(60)),
            ),
        )
        self._preview.SetName("Sample row preview")
        self._preview.SetHelpText("A sample row exactly as this template would say it.")
        self._hear = self._button(panel, "&Hear Preview", "Says the sample row aloud.")
        root.Add(self._hear, 0, wx.LEFT | wx.BOTTOM, 8)

        self._note = wx.StaticText(panel, label="")
        self._note.SetName("Template notice")
        root.Add(self._note, 0, wx.EXPAND | wx.ALL, 8)

        actions = wx.BoxSizer(wx.HORIZONTAL)
        self._save = self._button(panel, "Sa&ve As...", "Saves these choices under a name.")
        self._rename = self._button(panel, "Re&name...", "Renames the saved template.")
        self._delete = self._button(panel, "Delete Te&mplate", "Deletes the saved template.")
        self._import = self._button(
            panel, "&Import...", "Adds templates from a file. Asks before replacing any."
        )
        self._export = self._button(
            panel, "E&xport...", "Saves all your templates to a file to share or keep."
        )
        for button in (self._save, self._rename, self._delete, self._import, self._export):
            actions.Add(button, 0, wx.RIGHT, 6)
        root.Add(actions, 0, wx.LEFT | wx.BOTTOM, 8)
        use = wx.BoxSizer(wx.HORIZONTAL)
        self._use = self._button(panel, "&Use for This List", "Speaks this list's rows this way.")
        self._similar = self._button(
            panel, "Use for &Similar Lists", "Uses it for every list that reads alike."
        )
        use.Add(self._use, 0, wx.RIGHT, 6)
        use.Add(self._similar, 0, wx.RIGHT, 6)
        use.AddStretchSpacer()
        close = wx.Button(panel, wx.ID_CANCEL, "Close")
        close.SetHelpText("Closes this window. Saved templates and choices are already kept.")
        use.Add(close)
        root.Add(use, 0, wx.EXPAND | wx.ALL, 8)
        self._status = wx.StaticText(panel, label="")
        self._status.SetName("List speech status")
        root.Add(self._status, 0, wx.EXPAND | wx.ALL, 8)

        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)
        self.dialog.SetSize(dip_size(self.dialog, 580, 700))
        self._bind(wx, close)

    def _button(self, panel: Any, label: str, help_text: str) -> Any:
        button = self._wx.Button(panel, label=label)
        button.SetHelpText(help_text)
        return button

    def _bind(self, wx: Any, close: Any) -> None:
        self._types.Bind(wx.EVT_CHOICE, self._on_type)
        self._source.Bind(wx.EVT_CHOICE, self._on_source)
        self._up.Bind(wx.EVT_BUTTON, lambda _e: self._move(-1))
        self._down.Bind(wx.EVT_BUTTON, lambda _e: self._move(1))
        self._remove.Bind(wx.EVT_BUTTON, lambda _e: self._remove_field())
        self._add.Bind(wx.EVT_BUTTON, lambda _e: self._add_field())
        self._separator.Bind(wx.EVT_CHOICE, self._on_separator)
        self._labels.Bind(wx.EVT_CHECKBOX, self._on_labels)
        self._omit.Bind(wx.EVT_CHECKBOX, self._on_omit)
        self._fallback.Bind(wx.EVT_TEXT, self._on_fallback)
        self._hear.Bind(wx.EVT_BUTTON, lambda _e: self._announce(self._preview.GetValue()))
        self._save.Bind(wx.EVT_BUTTON, lambda _e: self._save_as())
        self._rename.Bind(wx.EVT_BUTTON, lambda _e: self._rename_saved())
        self._delete.Bind(wx.EVT_BUTTON, lambda _e: self._delete_saved())
        self._import.Bind(wx.EVT_BUTTON, lambda _e: self._import_file())
        self._export.Bind(wx.EVT_BUTTON, lambda _e: self._export_file())
        self._use.Bind(wx.EVT_BUTTON, lambda _e: self._use_it(False))
        self._similar.Bind(wx.EVT_BUTTON, lambda _e: self._use_it(True))
        self._fields.Bind(wx.EVT_KEY_DOWN, self._on_fields_key)
        bind_close_button(self.dialog, close, modeless=False)

    # -- showing -------------------------------------------------------------------

    def show(self) -> None:
        wx = self._wx
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_CANCEL,
            affirmative_label="Close",
            cancel_id=wx.ID_CANCEL,
            cancel_label="Close",
            escape_id=wx.ID_CANCEL,
        )
        try:
            show_modal_dialog(self.dialog, self.dialog.GetTitle(), announce=self._announce)
        finally:
            self.dialog.Destroy()

    def _say(self, message: str) -> None:
        self._status.SetLabel(message)
        self._announce(message)

    # -- drawing the state ---------------------------------------------------------

    def _refresh(self, select: int = -1) -> None:
        state = self._state
        self._building = True
        try:
            self._types.SetSelection([t.id for t in LIST_TYPES].index(state.list_type))
            choices = es.source_choices(state)
            self._sources = [ref for ref, _title in choices]
            self._source.Set([title for _ref, title in choices])
            self._source.SetSelection(self._sources.index(state.source))
            kind = state.kind
            self._fields.Set([
                f.title if (f := kind.field(i)) else f"{i} (not offered)"
                for i in state.draft.fields
            ])
            if state.draft.fields:
                self._fields.SetSelection(min(max(select, 0), len(state.draft.fields) - 1))
            spare = [f for f in kind.fields if f.id not in state.draft.fields]
            self._spare = [f.id for f in spare]
            self._picker.Set([f.title for f in spare])
            if spare:
                self._picker.SetSelection(0)
            self._set_separator(state.draft.separator)
            self._labels.SetValue(state.draft.labels)
            self._omit.SetValue(state.draft.omit_empty)
            if self._fallback.GetValue() != state.draft.fallback:
                self._fallback.ChangeValue(state.draft.fallback)
            self._preview.SetValue(es.preview(state))
            self._note.SetLabel(es.unavailable_note(state))
        finally:
            self._building = False
        saved = state.source.startswith("user:")
        self._rename.Enable(saved)
        self._delete.Enable(saved)
        self._add.Enable(bool(self._spare))

    def _set_separator(self, text: str) -> None:
        known = [value for value, _name in SEPARATOR_CHOICES]
        self._separator.SetSelection(known.index(text) if text in known else len(known))

    def _selected_field(self) -> int:
        return int(self._fields.GetSelection())

    # -- events --------------------------------------------------------------------

    def _on_type(self, _event: object) -> None:
        if self._building:
            return
        chosen = LIST_TYPES[self._types.GetSelection()].id
        self._state = es.start(self._state.library, chosen)
        self._refresh()
        self._say(f"{self._state.kind.title}.")

    def _on_source(self, _event: object) -> None:
        if self._building:
            return
        ref = self._sources[self._source.GetSelection()]
        self._state, message = es.choose_source(self._state, ref)
        self._refresh()
        self._say(message)

    def _add_field(self) -> None:
        index = self._picker.GetSelection()
        if not 0 <= index < len(self._spare):
            self._say("Every field is already in the row.")
            return
        self._state, message = es.add_field(self._state, self._spare[index])
        self._refresh(len(self._state.draft.fields) - 1)
        self._say(message)

    def _remove_field(self) -> None:
        index = self._selected_field()
        self._state, message = es.remove_field(self._state, index)
        self._refresh(index)
        self._say(message)

    def _move(self, delta: int) -> None:
        self._state, index, message = es.move(self._state, self._selected_field(), delta)
        self._refresh(index)
        self._fields.SetFocus()
        self._say(message)

    def _on_fields_key(self, event: Any) -> None:
        wx = self._wx
        code = event.GetKeyCode()
        if event.AltDown() and code in (wx.WXK_UP, wx.WXK_DOWN):
            self._move(-1 if code == wx.WXK_UP else 1)
        elif code == wx.WXK_DELETE:
            self._remove_field()
        else:
            event.Skip()

    def _on_separator(self, _event: object) -> None:
        if self._building:
            return
        index = self._separator.GetSelection()
        if index >= len(SEPARATOR_CHOICES):
            return
        self._state, message = es.set_separator(self._state, SEPARATOR_CHOICES[index][0])
        self._refresh(self._selected_field())
        self._say(message)

    def _on_labels(self, _event: object) -> None:
        if not self._building:
            self._state, message = es.set_labels(self._state, self._labels.GetValue())
            self._refresh(self._selected_field())
            self._say(message)

    def _on_omit(self, _event: object) -> None:
        if not self._building:
            self._state, message = es.set_omit_empty(self._state, self._omit.GetValue())
            self._refresh(self._selected_field())
            self._say(message)

    def _on_fallback(self, _event: object) -> None:
        if not self._building:
            self._state, _message = es.set_fallback(self._state, self._fallback.GetValue())
            self._preview.SetValue(es.preview(self._state))

    # -- saving --------------------------------------------------------------------

    def _ask_name(self, title: str, default: str) -> str | None:
        wx = self._wx
        with wx.TextEntryDialog(self.dialog, "Template &name:", title, default) as ask:
            if show_modal_dialog(ask, title, announce=self._announce) != wx.ID_OK:
                return None
            return str(ask.GetValue())

    def _commit(self) -> None:
        save_library(self._state.library)

    def _save_as(self) -> None:
        name = self._ask_name(
            "Save Template",
            "" if self._state.draft.name == es.DRAFT_NAME else self._state.draft.name,
        )
        if name is None:
            return
        self._state, message = es.save_draft(self._state, name)
        self._commit()
        self._refresh()
        self._say(message)

    def _rename_saved(self) -> None:
        name = self._ask_name("Rename Template", self._state.draft.name)
        if name is None:
            return
        self._state, message = es.rename_saved(self._state, name)
        self._commit()
        self._refresh()
        self._say(message)

    def _delete_saved(self) -> None:
        self._state, message = es.delete_saved(self._state)
        self._commit()
        self._refresh()
        self._say(message)

    def _import_file(self) -> None:
        library, message = import_from_file(
            self._wx, self.dialog, self._state.library, self._announce
        )
        if library is not self._state.library:
            self._state = replace(self._state, library=library)
            self._commit()
            self._refresh(self._selected_field())
        if message:
            self._say(message)

    def _export_file(self) -> None:
        message = export_to_file(self._wx, self.dialog, self._state.library, self._announce)
        if message:
            self._say(message)

    def _use_it(self, similar: bool) -> None:
        self._state, message = es.assign_current(self._state, similar)
        self._commit()
        self._refresh(self._selected_field())
        self._say(message)


def show_list_speech_editor(
    parent: object, *, list_type: str = "", announce: Callable[[str], None] | None = None
) -> None:
    """Open the editor modally, on *list_type* when it is one of the known lists."""
    ListSpeechDialog(parent, list_type=list_type, announce_cb=announce).show()
