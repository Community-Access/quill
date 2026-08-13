"""Abbreviation Manager dialog — create, edit, and organise abbreviations.

Hardened dialog (A11Y-4): exposes show() and close() so callers never call
ShowModal or Destroy directly on the inner wx.Dialog.
"""

from __future__ import annotations

import json

import wx

from quill.core.abbreviations import (
    Abbreviation,
    AbbreviationLibrary,
    save_abbreviation_library,
)
from quill.ui.dialog_contract import apply_modal_ids, show_message_box

#: Stored value -> the words shown in the edit dialog. Ordered, because the
#: choice controls are populated from these and read back by index.
_TRIGGER_LABELS: dict[str, str] = {
    "both": "A space or punctuation",
    "space": "A space only",
    "punctuation": "Punctuation only",
    "manual": "Never — Quick Insert only",
}
_SPEAK_LABELS: dict[str, str] = {
    "silent": "Nothing",
    "name": "The abbreviation",
    "expansion": "The expanded text",
}
_SOUND_LABELS: dict[str, str] = {
    "inherit": "Follow the global setting",
    "on": "Always play",
    "off": "Never play",
}

#: The two pseudo-entries at the top of the category filter.
_ALL_CATEGORIES = "All categories"
_UNCATEGORISED = "Uncategorised"


def _select(control: object, labels: dict[str, str], value: str) -> None:
    keys = list(labels)
    control.SetSelection(keys.index(value) if value in keys else 0)  # type: ignore[attr-defined]


def _selected(control: object, labels: dict[str, str]) -> str:
    keys = list(labels)
    index = int(control.GetSelection())  # type: ignore[attr-defined]
    return keys[index] if 0 <= index < len(keys) else keys[0]


class _AbbreviationEditDialog:
    """Inner dialog for creating or editing a single abbreviation."""

    def __init__(
        self,
        parent: object,
        abbreviation: Abbreviation | None = None,
        categories: list[str] | None = None,
    ) -> None:
        categories = categories or []
        title = "Edit Abbreviation" if abbreviation else "New Abbreviation"
        self.dialog = wx.Dialog(
            parent,
            title=title,
            style=wx.DEFAULT_DIALOG_STYLE,
        )
        self.dialog.SetMinSize(wx.Size(420, 280))

        root = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(cols=2, hgap=8, vgap=6)
        grid.AddGrowableCol(1)

        grid.Add(wx.StaticText(self.dialog, label="&Abbreviation:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._abbr_ctrl = wx.TextCtrl(self.dialog)
        self._abbr_ctrl.SetName("Abbreviation trigger word")
        grid.Add(self._abbr_ctrl, 1, wx.EXPAND)

        grid.Add(wx.StaticText(self.dialog, label="&Expansion:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._exp_ctrl = wx.TextCtrl(
            self.dialog, style=wx.TE_MULTILINE | wx.TE_PROCESS_ENTER, size=(-1, 70)
        )
        self._exp_ctrl.SetName("Expansion text — use ${cursor}, ${date}, ${time}, ${clipboard}")
        grid.Add(self._exp_ctrl, 1, wx.EXPAND)

        grid.Add(wx.StaticText(self.dialog, label="&Description:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._desc_ctrl = wx.TextCtrl(self.dialog)
        self._desc_ctrl.SetName("Optional description")
        grid.Add(self._desc_ctrl, 1, wx.EXPAND)

        grid.Add(wx.StaticText(self.dialog, label="C&ategory:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._category_ctrl = wx.ComboBox(self.dialog, choices=sorted(c for c in categories if c))
        self._category_ctrl.SetName("Category — leave empty for Uncategorised")
        grid.Add(self._category_ctrl, 1, wx.EXPAND)

        grid.Add(wx.StaticText(self.dialog, label="E&xpand after:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._triggers_ctrl = wx.Choice(self.dialog, choices=list(_TRIGGER_LABELS.values()))
        self._triggers_ctrl.SetName("Which characters expand this abbreviation")
        self._triggers_ctrl.SetSelection(0)
        grid.Add(self._triggers_ctrl, 1, wx.EXPAND)

        grid.Add(wx.StaticText(self.dialog, label="S&peak:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._speak_ctrl = wx.Choice(self.dialog, choices=list(_SPEAK_LABELS.values()))
        self._speak_ctrl.SetName("What is spoken when this abbreviation expands")
        self._speak_ctrl.SetSelection(0)
        grid.Add(self._speak_ctrl, 1, wx.EXPAND)

        grid.Add(wx.StaticText(self.dialog, label="Soun&d:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._sound_ctrl = wx.Choice(self.dialog, choices=list(_SOUND_LABELS.values()))
        self._sound_ctrl.SetName("Play a sound when this abbreviation expands")
        self._sound_ctrl.SetSelection(0)
        grid.Add(self._sound_ctrl, 1, wx.EXPAND)

        root.Add(grid, 0, wx.EXPAND | wx.ALL, 10)

        self._case_ctrl = wx.CheckBox(self.dialog, label="&Case sensitive")
        self._space_ctrl = wx.CheckBox(self.dialog, label="Add a trailing space a&fter punctuation")
        self._enabled_ctrl = wx.CheckBox(self.dialog, label="E&nabled")
        self._enabled_ctrl.SetValue(True)
        root.Add(self._case_ctrl, 0, wx.LEFT | wx.BOTTOM, 10)
        root.Add(self._space_ctrl, 0, wx.LEFT | wx.BOTTOM, 10)
        root.Add(self._enabled_ctrl, 0, wx.LEFT | wx.BOTTOM, 10)

        buttons = self.dialog.CreateButtonSizer(wx.OK | wx.CANCEL)
        if buttons is not None:
            ok_btn = self.dialog.FindWindowById(wx.ID_OK)
            if ok_btn is not None:
                ok_btn.SetDefault()
            root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)

        self.dialog.SetSizer(root)
        self.dialog.Layout()

        from quill.ui.dialog_contract import apply_modal_ids

        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)

        if abbreviation is not None:
            self._abbr_ctrl.SetValue(abbreviation.abbreviation)
            self._exp_ctrl.SetValue(abbreviation.expansion)
            self._desc_ctrl.SetValue(abbreviation.description)
            self._case_ctrl.SetValue(abbreviation.case_sensitive)
            self._enabled_ctrl.SetValue(abbreviation.enabled)
            self._category_ctrl.SetValue(abbreviation.category)
            self._space_ctrl.SetValue(abbreviation.trailing_space)
            _select(self._triggers_ctrl, _TRIGGER_LABELS, abbreviation.triggers)
            _select(self._speak_ctrl, _SPEAK_LABELS, abbreviation.speak_mode)
            _select(self._sound_ctrl, _SOUND_LABELS, abbreviation.sound)

        self._abbr_ctrl.SetFocus()

    def show(self) -> int:
        return self.dialog.ShowModal()

    def close(self) -> None:
        self.dialog.Destroy()

    @property
    def trigger_text(self) -> str:
        """The abbreviation as typed (empty means the dialog has nothing to save)."""
        return str(self._abbr_ctrl.GetValue()).strip()

    @property
    def expansion_text(self) -> str:
        return str(self._exp_ctrl.GetValue())

    def apply_to(self, abbreviation: Abbreviation) -> None:
        """Write every field of this dialog onto *abbreviation*."""
        abbreviation.abbreviation = self.trigger_text
        abbreviation.expansion = self.expansion_text
        abbreviation.description = str(self._desc_ctrl.GetValue()).strip()
        abbreviation.case_sensitive = bool(self._case_ctrl.GetValue())
        abbreviation.enabled = bool(self._enabled_ctrl.GetValue())
        abbreviation.category = str(self._category_ctrl.GetValue()).strip()
        abbreviation.trailing_space = bool(self._space_ctrl.GetValue())
        abbreviation.triggers = _selected(self._triggers_ctrl, _TRIGGER_LABELS)
        abbreviation.speak_mode = _selected(self._speak_ctrl, _SPEAK_LABELS)
        abbreviation.sound = _selected(self._sound_ctrl, _SOUND_LABELS)


class AbbreviationManagerDialog:
    """Browse, create, edit, and delete abbreviations."""

    def __init__(self, parent: object, library: AbbreviationLibrary) -> None:
        self._library = library
        self._search_query = ""
        self.dialog = wx.Dialog(
            parent,
            title="Manage Abbreviations",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(wx.Size(620, 440))

        root = wx.BoxSizer(wx.VERTICAL)

        # Search field
        search_row = wx.BoxSizer(wx.HORIZONTAL)
        search_row.Add(
            wx.StaticText(self.dialog, label="&Search:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            4,
        )
        self._search_ctrl = wx.TextCtrl(self.dialog)
        self._search_ctrl.SetName("Search abbreviations")
        search_row.Add(self._search_ctrl, 1, wx.EXPAND)
        search_row.Add(
            wx.StaticText(self.dialog, label="Ca&tegory:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.RIGHT,
            4,
        )
        self._category_filter = wx.Choice(self.dialog, choices=[_ALL_CATEGORIES])
        self._category_filter.SetName("Filter by category")
        self._category_filter.SetSelection(0)
        search_row.Add(self._category_filter, 0)
        root.Add(search_row, 0, wx.EXPAND | wx.ALL, 8)

        self._list = wx.ListCtrl(
            self.dialog,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN,
        )
        self._list.SetName("Abbreviations list")
        self._list.InsertColumn(0, "Abbreviation", width=120)
        self._list.InsertColumn(1, "Expansion", width=260)
        self._list.InsertColumn(2, "On", width=40)
        self._list.InsertColumn(3, "Category", width=110)
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._btn_new = wx.Button(self.dialog, label="&New")
        self._btn_edit = wx.Button(self.dialog, label="&Edit")
        self._btn_delete = wx.Button(self.dialog, label="&Delete")
        self._btn_toggle = wx.Button(self.dialog, label="Enable/Disa&ble")
        self._btn_import = wx.Button(self.dialog, label="&Import...")
        self._btn_export = wx.Button(self.dialog, label="E&xport...")
        btn_close = wx.Button(self.dialog, wx.ID_CANCEL, label="C&lose")
        for btn in (
            self._btn_new,
            self._btn_edit,
            self._btn_delete,
            self._btn_toggle,
            self._btn_import,
            self._btn_export,
        ):
            btn_row.Add(btn, 0, wx.RIGHT, 4)
        btn_row.AddStretchSpacer(1)
        btn_row.Add(btn_close, 0)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 8)

        self.dialog.SetSizer(root)
        self.dialog.Layout()

        apply_modal_ids(self.dialog, cancel_id=wx.ID_CANCEL, cancel_label="Close")

        self._search_ctrl.Bind(wx.EVT_TEXT, self._on_search)
        self._category_filter.Bind(wx.EVT_CHOICE, self._on_search)
        self._btn_new.Bind(wx.EVT_BUTTON, self._on_new)
        self._btn_edit.Bind(wx.EVT_BUTTON, self._on_edit)
        self._btn_delete.Bind(wx.EVT_BUTTON, self._on_delete)
        self._btn_toggle.Bind(wx.EVT_BUTTON, self._on_toggle)
        self._btn_import.Bind(wx.EVT_BUTTON, self._on_import)
        self._btn_export.Bind(wx.EVT_BUTTON, self._on_export)
        self._list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_edit)

        self._refresh_categories()
        self._rebuild_list()
        self._list.SetFocus()

    def show(self) -> int:
        return self.dialog.ShowModal()

    def close(self) -> None:
        self.dialog.Destroy()

    # -- list helpers --

    def _categories(self) -> list[str]:
        return sorted({a.category for a in self._library.abbreviations if a.category})

    def _refresh_categories(self) -> None:
        """Rebuild the filter's choices, keeping the current selection when it
        still exists (adding a category must not silently change the filter)."""
        current = self._selected_category()
        choices = [_ALL_CATEGORIES, _UNCATEGORISED, *self._categories()]
        self._category_filter.Set(choices)
        self._category_filter.SetSelection(choices.index(current) if current in choices else 0)

    def _selected_category(self) -> str:
        index = self._category_filter.GetSelection()
        if index < 0:
            return _ALL_CATEGORIES
        return str(self._category_filter.GetString(index))

    def _visible_abbreviations(self) -> list[Abbreviation]:
        entries = list(self._library.abbreviations)
        category = self._selected_category()
        if category == _UNCATEGORISED:
            entries = [a for a in entries if not a.category]
        elif category != _ALL_CATEGORIES:
            entries = [a for a in entries if a.category == category]
        if not self._search_query:
            return entries
        q = self._search_query.lower()
        return [
            a
            for a in entries
            if q in a.abbreviation.lower() or q in a.expansion.lower() or q in a.description.lower()
        ]

    def _rebuild_list(self) -> None:
        sel = self._list.GetFirstSelected()
        self._list.DeleteAllItems()
        self._visible = self._visible_abbreviations()
        for i, abbr in enumerate(self._visible):
            label = abbr.abbreviation if abbr.enabled else f"{abbr.abbreviation} (disabled)"
            self._list.InsertItem(i, label)
            preview = abbr.expansion.replace("\n", " ")[:60]
            self._list.SetItem(i, 1, preview)
            self._list.SetItem(i, 2, "Y" if abbr.enabled else "N")
            self._list.SetItem(i, 3, abbr.category or _UNCATEGORISED)
        if 0 <= sel < self._list.GetItemCount():
            self._list.Select(sel)
            self._list.EnsureVisible(sel)
        elif self._list.GetItemCount() > 0:
            self._list.Select(0)

    def _selected_index(self) -> int:
        return self._list.GetFirstSelected()

    def _selected_abbreviation(self) -> Abbreviation | None:
        idx = self._selected_index()
        if idx < 0 or idx >= len(self._visible):
            return None
        return self._visible[idx]

    # -- event handlers --

    def _on_search(self, _event: object) -> None:
        self._search_query = self._search_ctrl.GetValue().strip()
        self._rebuild_list()

    def _on_new(self, _event: object) -> None:
        import uuid

        edit_dlg = _AbbreviationEditDialog(self.dialog, categories=self._categories())
        result = edit_dlg.show()
        if result == wx.ID_OK and edit_dlg.trigger_text and edit_dlg.expansion_text:
            new_abbr = Abbreviation(id=str(uuid.uuid4()), abbreviation="", expansion="")
            edit_dlg.apply_to(new_abbr)
            self._library.abbreviations.append(new_abbr)
            self._library.abbreviations.sort(key=lambda a: a.abbreviation.lower())
            save_abbreviation_library(self._library)
            self._refresh_categories()
            self._rebuild_list()
        edit_dlg.close()

    def _on_edit(self, _event: object) -> None:
        abbr = self._selected_abbreviation()
        if abbr is None:
            return
        edit_dlg = _AbbreviationEditDialog(self.dialog, abbr, categories=self._categories())
        result = edit_dlg.show()
        if result == wx.ID_OK and edit_dlg.trigger_text and edit_dlg.expansion_text:
            edit_dlg.apply_to(abbr)
            save_abbreviation_library(self._library)
            self._refresh_categories()
            self._rebuild_list()
        edit_dlg.close()

    def _on_delete(self, _event: object) -> None:
        abbr = self._selected_abbreviation()
        if abbr is None:
            return
        confirm = wx.MessageDialog(
            self.dialog,
            f"Delete abbreviation '{abbr.abbreviation}'?",
            "Delete Abbreviation",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
        )
        result = confirm.ShowModal()
        confirm.Destroy()
        if result == wx.ID_YES:
            self._library.abbreviations = [
                a for a in self._library.abbreviations if a.id != abbr.id
            ]
            save_abbreviation_library(self._library)
            self._rebuild_list()

    def _on_toggle(self, _event: object) -> None:
        abbr = self._selected_abbreviation()
        if abbr is None:
            return
        abbr.enabled = not abbr.enabled
        save_abbreviation_library(self._library)
        self._rebuild_list()

    def _on_import(self, _event: object) -> None:
        dlg = wx.FileDialog(
            self.dialog,
            "Import Abbreviations",
            wildcard="JSON files (*.json)|*.json|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        )
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return
        path = dlg.GetPath()
        dlg.Destroy()
        try:
            raw = json.loads(open(path, encoding="utf-8").read())
            incoming = raw.get("abbreviations", [])
        except Exception as exc:
            show_message_box(
                f"Could not read file: {exc}",
                "Import Failed",
                wx.OK | wx.ICON_ERROR,
                self.dialog,
            )
            return
        existing_ids = {a.id for a in self._library.abbreviations}
        added = 0
        skipped = 0
        for item in incoming:
            if not isinstance(item, dict):
                continue
            if item.get("id") in existing_ids:
                skipped += 1
                continue
            try:
                import uuid

                new_a = Abbreviation(
                    id=str(item.get("id") or uuid.uuid4()),
                    abbreviation=str(item.get("abbreviation", "")),
                    expansion=str(item.get("expansion", "")),
                    case_sensitive=bool(item.get("case_sensitive", False)),
                    enabled=bool(item.get("enabled", True)),
                    description=str(item.get("description", "")),
                )
                if new_a.abbreviation and new_a.expansion:
                    self._library.abbreviations.append(new_a)
                    existing_ids.add(new_a.id)
                    added += 1
            except Exception:  # noqa: BLE001
                skipped += 1
        if added:
            self._library.abbreviations.sort(key=lambda a: a.abbreviation.lower())
            save_abbreviation_library(self._library)
        show_message_box(
            f"Imported {added} abbreviation(s). {skipped} skipped (duplicate IDs).",
            "Import Complete",
            wx.OK | wx.ICON_INFORMATION,
            self.dialog,
        )
        self._rebuild_list()

    def _on_export(self, _event: object) -> None:
        dlg = wx.FileDialog(
            self.dialog,
            "Export Abbreviations",
            defaultFile="abbreviations.json",
            wildcard="JSON files (*.json)|*.json|All files (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return
        path = dlg.GetPath()
        dlg.Destroy()
        try:
            data = {
                "version": self._library.version,
                "abbreviations": [
                    {
                        "id": a.id,
                        "abbreviation": a.abbreviation,
                        "expansion": a.expansion,
                        "case_sensitive": a.case_sensitive,
                        "enabled": a.enabled,
                        "description": a.description,
                    }
                    for a in self._library.abbreviations
                ],
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            show_message_box(
                f"Could not write file: {exc}",
                "Export Failed",
                wx.OK | wx.ICON_ERROR,
                self.dialog,
            )
            return
        show_message_box(
            f"Exported {len(self._library.abbreviations)} abbreviation(s).",
            "Export Complete",
            wx.OK | wx.ICON_INFORMATION,
            self.dialog,
        )
