"""Work Persona dialog (#896) — create, edit, delete, launch, or generate a
shortcut for a named persona bundle.

Modeled on ``clip_library_dialog.py``'s list + detail-pane + action-buttons
shape.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import wx

from quill.core.features import PROFILE_DEFINITIONS
from quill.core.keymap import list_keymap_profiles
from quill.core.work_persona import WorkPersona, WorkPersonaStore

_NO_KEYMAP_CHANGE = "(leave keymap unchanged)"


class WorkPersonaDialog:
    """Browse, create, edit, delete, launch, or export a shortcut for a persona."""

    def __init__(
        self,
        parent: object,
        store: WorkPersonaStore,
        announce_cb: Callable[[str], None] | None = None,
        apply_cb: Callable[[WorkPersona], None] | None = None,
    ) -> None:
        self._store = store
        self._announce = announce_cb or (lambda _msg: None)
        self._apply_cb = apply_cb
        self._profile_ids = list(PROFILE_DEFINITIONS.keys())
        self._keymap_choices = [_NO_KEYMAP_CHANGE, *list_keymap_profiles()]
        self._favorite_files: list[str] = []
        self._guard = False

        self.dialog = wx.Dialog(
            parent, title="Work Personas", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize(wx.Size(700, 480))
        root = wx.BoxSizer(wx.VERTICAL)
        body = wx.BoxSizer(wx.HORIZONTAL)

        left = wx.BoxSizer(wx.VERTICAL)
        left.Add(wx.StaticText(self.dialog, label="&Personas"), 0, wx.BOTTOM, 2)
        self._listbox = wx.ListBox(self.dialog, style=wx.LB_SINGLE)
        self._listbox.SetName("Work Personas")
        left.Add(self._listbox, 1, wx.EXPAND)
        left.Add(
            wx.Button(self.dialog, wx.ID_ADD, label="&New Persona"), 0, wx.EXPAND | wx.TOP, 4
        )
        body.Add(left, 1, wx.EXPAND | wx.RIGHT, 8)
        self._btn_new = self.dialog.FindWindow(wx.ID_ADD)

        right = wx.BoxSizer(wx.VERTICAL)
        right.Add(wx.StaticText(self.dialog, label="&Name:"), 0)
        self._name_ctrl = wx.TextCtrl(self.dialog)
        self._name_ctrl.SetName("Persona name")
        right.Add(self._name_ctrl, 0, wx.EXPAND | wx.BOTTOM, 6)

        right.Add(wx.StaticText(self.dialog, label="&Feature profile:"), 0)
        self._profile_choice = wx.Choice(
            self.dialog, choices=[str(PROFILE_DEFINITIONS[p].name) for p in self._profile_ids]
        )
        self._profile_choice.SetName("Feature profile")
        right.Add(self._profile_choice, 0, wx.EXPAND | wx.BOTTOM, 6)

        right.Add(wx.StaticText(self.dialog, label="&Working folder:"), 0)
        folder_row = wx.BoxSizer(wx.HORIZONTAL)
        self._folder_ctrl = wx.TextCtrl(self.dialog)
        self._folder_ctrl.SetName("Working folder")
        folder_row.Add(self._folder_ctrl, 1)
        self._btn_browse = wx.Button(self.dialog, label="&Browse...")
        folder_row.Add(self._btn_browse, 0, wx.LEFT, 4)
        right.Add(folder_row, 0, wx.EXPAND | wx.BOTTOM, 6)

        right.Add(wx.StaticText(self.dialog, label="&Keymap profile:"), 0)
        self._keymap_choice = wx.Choice(self.dialog, choices=self._keymap_choices)
        self._keymap_choice.SetName("Keymap profile")
        self._keymap_choice.SetSelection(0)
        right.Add(self._keymap_choice, 0, wx.EXPAND | wx.BOTTOM, 6)

        right.Add(wx.StaticText(self.dialog, label="F&avorite files:"), 0)
        self._favorites_list = wx.ListBox(self.dialog)
        self._favorites_list.SetName("Favorite files")
        right.Add(self._favorites_list, 1, wx.EXPAND | wx.BOTTOM, 2)
        fav_btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._btn_add_file = wx.Button(self.dialog, label="Add &File...")
        self._btn_remove_file = wx.Button(self.dialog, label="&Remove File")
        fav_btn_row.Add(self._btn_add_file, 0, wx.RIGHT, 4)
        fav_btn_row.Add(self._btn_remove_file, 0)
        right.Add(fav_btn_row, 0, wx.BOTTOM, 6)

        body.Add(right, 2, wx.EXPAND)
        root.Add(body, 1, wx.EXPAND | wx.ALL, 8)

        self._status = wx.StaticText(self.dialog, label="")
        self._status.SetName("Status")
        root.Add(self._status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._btn_save = wx.Button(self.dialog, label="&Save")
        self._btn_delete = wx.Button(self.dialog, label="&Delete")
        self._btn_apply = wx.Button(self.dialog, label="&Apply Now")
        self._btn_shortcut = wx.Button(self.dialog, label="&Generate Shortcut...")
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, label="&Close")
        for btn in (self._btn_save, self._btn_delete, self._btn_apply, self._btn_shortcut):
            btn_row.Add(btn, 0, wx.RIGHT, 4)
        btn_row.AddStretchSpacer(1)
        btn_row.Add(close_btn, 0)
        root.Add(btn_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.dialog.SetSizer(root)
        self.dialog.Layout()

        from quill.ui.dialog_contract import apply_modal_ids

        apply_modal_ids(self.dialog, cancel_id=wx.ID_CANCEL, cancel_label="Close")

        self._listbox.Bind(wx.EVT_LISTBOX, self._on_selection_changed)
        self._btn_new.Bind(wx.EVT_BUTTON, self._on_new)
        self._btn_save.Bind(wx.EVT_BUTTON, self._on_save)
        self._btn_delete.Bind(wx.EVT_BUTTON, self._on_delete)
        self._btn_apply.Bind(wx.EVT_BUTTON, self._on_apply)
        self._btn_shortcut.Bind(wx.EVT_BUTTON, self._on_shortcut)
        self._btn_browse.Bind(wx.EVT_BUTTON, self._on_browse_folder)
        self._btn_add_file.Bind(wx.EVT_BUTTON, self._on_add_file)
        self._btn_remove_file.Bind(wx.EVT_BUTTON, self._on_remove_file)

        self._rebuild_list()
        self._listbox.SetFocus()

    # -- public API --

    def show(self) -> None:
        from quill.ui.dialog_contract import show_modal_dialog

        show_modal_dialog(self.dialog, "Work Personas")

    def close(self) -> None:
        self.dialog.Destroy()

    # -- internal helpers --

    def _set_status(self, message: str) -> None:
        self._status.SetLabel(message)
        self._announce(message)

    def _rebuild_list(self, *, select_name: str = "") -> None:
        self._guard = True
        self._listbox.Clear()
        personas = self._store.all()
        for persona in personas:
            self._listbox.Append(persona.display_label())
        if personas:
            names = [p.name for p in personas]
            index = names.index(select_name) if select_name in names else 0
            self._listbox.SetSelection(index)
            self._load_into_form(personas[index])
        else:
            self._clear_form()
        self._guard = False
        self._update_buttons()

    def _selected_persona(self) -> WorkPersona | None:
        index = self._listbox.GetSelection()
        personas = self._store.all()
        if index == wx.NOT_FOUND or index >= len(personas):
            return None
        return personas[index]

    def _load_into_form(self, persona: WorkPersona) -> None:
        self._name_ctrl.SetValue(persona.name)
        if persona.technical_profile in self._profile_ids:
            self._profile_choice.SetSelection(self._profile_ids.index(persona.technical_profile))
        else:
            self._profile_choice.SetSelection(0)
        self._folder_ctrl.SetValue(persona.working_folder)
        if persona.keymap_profile in self._keymap_choices:
            self._keymap_choice.SetSelection(self._keymap_choices.index(persona.keymap_profile))
        else:
            self._keymap_choice.SetSelection(0)
        self._favorite_files = list(persona.favorite_files)
        self._refresh_favorites_list()

    def _clear_form(self) -> None:
        self._name_ctrl.SetValue("")
        self._profile_choice.SetSelection(0)
        self._folder_ctrl.SetValue("")
        self._keymap_choice.SetSelection(0)
        self._favorite_files = []
        self._refresh_favorites_list()

    def _refresh_favorites_list(self) -> None:
        self._favorites_list.Clear()
        for path in self._favorite_files:
            self._favorites_list.Append(path)

    def _update_buttons(self) -> None:
        has_selection = self._selected_persona() is not None
        self._btn_delete.Enable(has_selection)
        self._btn_apply.Enable(has_selection)
        self._btn_shortcut.Enable(has_selection)

    def _form_to_persona(self) -> WorkPersona | None:
        name = self._name_ctrl.GetValue().strip()
        if not name:
            self._set_status("Enter a name for this persona.")
            return None
        profile_index = self._profile_choice.GetSelection()
        profile_id = (
            self._profile_ids[profile_index] if profile_index != wx.NOT_FOUND else "essential"
        )
        keymap_index = self._keymap_choice.GetSelection()
        keymap = ""
        if keymap_index not in (wx.NOT_FOUND, 0):
            keymap = self._keymap_choices[keymap_index]
        return WorkPersona(
            name=name,
            technical_profile=profile_id,
            working_folder=self._folder_ctrl.GetValue().strip(),
            favorite_files=tuple(self._favorite_files),
            keymap_profile=keymap,
        )

    # -- event handlers --

    def _on_selection_changed(self, _event: object) -> None:
        if self._guard:
            return
        persona = self._selected_persona()
        if persona is not None:
            self._load_into_form(persona)
        self._update_buttons()

    def _on_new(self, _event: object) -> None:
        self._listbox.SetSelection(wx.NOT_FOUND)
        self._clear_form()
        self._name_ctrl.SetFocus()
        self._update_buttons()

    def _on_save(self, _event: object) -> None:
        persona = self._form_to_persona()
        if persona is None:
            return
        existing = self._store.get(persona.name)
        if existing is None:
            self._store.create(persona)
        else:
            self._store.update(persona)
        self._rebuild_list(select_name=persona.name)
        self._set_status(f"Saved persona '{persona.name}'.")

    def _on_delete(self, _event: object) -> None:
        persona = self._selected_persona()
        if persona is None:
            return
        self._store.remove(persona.name)
        self._rebuild_list()
        self._set_status(f"Deleted persona '{persona.name}'.")

    def _on_apply(self, _event: object) -> None:
        persona = self._selected_persona()
        if persona is None or self._apply_cb is None:
            return
        self._apply_cb(persona)

    def _on_shortcut(self, _event: object) -> None:
        persona = self._selected_persona()
        if persona is None:
            return
        from quill.core.persona_launcher import write_launch_shortcut

        with wx.DirDialog(self.dialog, "Choose where to save the shortcut") as pick:
            if pick.ShowModal() != wx.ID_OK:
                return
            target_dir = Path(pick.GetPath())
        path = write_launch_shortcut(persona.name, target_dir)
        self._set_status(f"Shortcut saved to {path}.")

    def _on_browse_folder(self, _event: object) -> None:
        with wx.DirDialog(self.dialog, "Choose the working folder") as pick:
            if pick.ShowModal() == wx.ID_OK:
                self._folder_ctrl.SetValue(pick.GetPath())

    def _on_add_file(self, _event: object) -> None:
        with wx.FileDialog(self.dialog, "Add a favorite file") as pick:
            if pick.ShowModal() == wx.ID_OK:
                self._favorite_files.append(pick.GetPath())
                self._refresh_favorites_list()

    def _on_remove_file(self, _event: object) -> None:
        index = self._favorites_list.GetSelection()
        if index == wx.NOT_FOUND:
            return
        del self._favorite_files[index]
        self._refresh_favorites_list()
