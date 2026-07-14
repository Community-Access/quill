"""Structured List Studio dialog (accessible wx shell over quill.core.lists).

A thin, fully keyboard-operable ``wx.Dialog`` that lets the user build or edit a
list by working with *concepts* — item text, term, definition, checked state —
while ``quill.core.lists`` does the real work of interpreting input and
generating Markdown/HTML source. The dialog never asks the user to type ``-``,
``1.``, ``[ ]``, ``<ul>``, or ``<dl>``; it shows the generated source read-only
as a live preview (PRD §2.1, §23). All list logic lives in core and is unit
tested there, so this module stays a wiring layer.
"""

from __future__ import annotations

from typing import Any

from quill.core.lists import (
    DefinitionEntry,
    DefinitionList,
    FlatList,
    ListItem,
    ListType,
    StructuredListSettings,
    add_child,
    can_indent,
    can_outdent,
    definition_entry_announcement,
    definition_to_flat,
    flat_item_announcement,
    flat_to_definition,
    indent,
    interpret_text_into_definition,
    interpret_text_into_flat,
    list_summary,
    move_subtree,
    outdent,
    render_html,
    render_markdown,
    validate_before_commit,
)
from quill.core.lists.render import DefinitionProfileError, render_definition_with_choice

_TYPE_CHOICES: list[tuple[str, ListType]] = [
    ("Bulleted", ListType.BULLET),
    ("Numbered", ListType.ORDERED),
    ("Checklist", ListType.CHECKLIST),
    ("Definition list", ListType.DEFINITION),
]


class ListStudioDialog:
    """Builds the dialog and exposes the generated source after OK.

    Usage (the caller owns the ``wx.Dialog`` so the accessible show path and
    ``apply_modal_ids`` live together in one scope, matching List Manager)::

        dlg = wx.Dialog(frame, title="Structured List Studio", style=...)
        studio = ListStudioDialog(wx, flat=model, settings=cfg, target_format="markdown")
        studio.populate(dlg)
        apply_modal_ids(dlg, affirmative_id=wx.ID_OK, ...)
        if show_modal(dlg) == wx.ID_OK:
            new_source = studio.result_source

    The caller passes whichever model it has (``flat`` or ``definition``); the
    other is created empty and the user can switch types in the dialog.
    """

    def __init__(
        self,
        wx: Any,
        *,
        flat: FlatList | None = None,
        definition: DefinitionList | None = None,
        settings: StructuredListSettings | None = None,
        target_format: str = "markdown",
        confirm_conversion: Any = None,
        resolve_definition_fallback: Any = None,
    ) -> None:
        self._wx = wx
        self._settings = settings if settings is not None else StructuredListSettings()
        self._flat = flat if flat is not None else FlatList(items=[ListItem("")])
        self._definition = (
            definition if definition is not None else DefinitionList(entries=[DefinitionEntry()])
        )
        self._format = target_format if target_format in {"markdown", "html"} else "markdown"
        self._type: ListType = self._flat.list_type if definition is None else ListType.DEFINITION
        if definition is not None:
            self._type = ListType.DEFINITION
        # ``confirm_conversion(reasons) -> bool`` lets the caller warn (via the
        # hardened MessageBox) before a lossy flat<->definition type switch; when
        # absent the switch proceeds without prompting. See _on_type_changed.
        self._confirm_conversion = confirm_conversion
        # ``resolve_definition_fallback() -> str | None`` resolves the §7.6/§21.3
        # prompt when a Markdown definition list has no configured profile. It
        # returns a choice token (a key of ``DEFINITION_FALLBACK_PROFILES``) or
        # ``None`` to cancel. When absent, the wx prompt below is used.
        self._resolve_definition_fallback = resolve_definition_fallback
        self._suppress = False
        self.result_source: str = ""
        self.dialog: Any = None
        self._outer_sizer: Any = None

    # -- construction ------------------------------------------------------ #

    def populate(self, dlg: Any) -> Any:
        """Build all controls into the caller-owned ``dlg`` (a ``wx.Dialog``)."""
        wx = self._wx
        self.dialog = dlg
        outer = wx.BoxSizer(wx.VERTICAL)

        # Type + format row.
        top = wx.BoxSizer(wx.HORIZONTAL)
        top.Add(wx.StaticText(dlg, label="List &type:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self._type_choice = wx.Choice(dlg, choices=[label for label, _t in _TYPE_CHOICES])
        self._type_choice.SetSelection(self._type_index())
        self._type_choice.Bind(wx.EVT_CHOICE, self._on_type_changed)
        top.Add(self._type_choice, 0, wx.RIGHT, 18)
        top.Add(wx.StaticText(dlg, label="&Format:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self._format_choice = wx.Choice(dlg, choices=["Markdown", "HTML"])
        self._format_choice.SetSelection(0 if self._format == "markdown" else 1)
        self._format_choice.Bind(wx.EVT_CHOICE, self._on_format_changed)
        top.Add(self._format_choice, 0)
        outer.Add(top, 0, wx.ALL, 10)

        # Outline + editor row.
        middle = wx.BoxSizer(wx.HORIZONTAL)
        left = wx.BoxSizer(wx.VERTICAL)
        self._outline_label = wx.StaticText(dlg, label="&Items:")
        left.Add(self._outline_label, 0, wx.BOTTOM, 4)
        self._outline = wx.ListBox(dlg, style=wx.LB_SINGLE)
        self._outline.Bind(wx.EVT_LISTBOX, self._on_outline_select)
        left.Add(self._outline, 1, wx.EXPAND | wx.BOTTOM, 6)
        left.Add(self._build_outline_buttons(dlg), 0, wx.EXPAND)
        middle.Add(left, 1, wx.EXPAND | wx.RIGHT, 12)

        middle.Add(self._build_editor_panel(dlg), 1, wx.EXPAND)
        outer.Add(middle, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        # Source preview.
        outer.Add(
            wx.StaticText(dlg, label="Generated &source (read-only):"),
            0,
            wx.LEFT | wx.TOP,
            10,
        )
        self._preview = wx.TextCtrl(
            dlg, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP, size=(-1, 120)
        )
        outer.Add(self._preview, 0, wx.EXPAND | wx.ALL, 10)

        # The OK/Cancel button sizer and apply_modal_ids are added by the caller
        # (in the same scope as the accessible show path), matching List Manager
        # and the dialog hardening/button contracts. _on_ok captures the source.
        dlg.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)
        self._outer_sizer = outer
        return outer

    def finalize(self) -> None:
        """Lay out the dialog and load initial content (after the caller adds buttons)."""
        self.dialog.SetSizerAndFit(self._outer_sizer)
        self.dialog.SetSize((760, 620))
        self._sync_type_visibility()
        self._reload_outline(select=0)

    def _build_outline_buttons(self, dlg: Any) -> Any:
        wx = self._wx
        outer = wx.BoxSizer(wx.VERTICAL)
        row = wx.BoxSizer(wx.HORIZONTAL)
        self._btn_add = wx.Button(dlg, label="&Add")
        self._btn_remove = wx.Button(dlg, label="&Remove")
        self._btn_up = wx.Button(dlg, label="Move &up")
        self._btn_down = wx.Button(dlg, label="Move &down")
        self._btn_add.Bind(wx.EVT_BUTTON, self._on_add)
        self._btn_remove.Bind(wx.EVT_BUTTON, self._on_remove)
        self._btn_up.Bind(wx.EVT_BUTTON, lambda _e: self._move(-1))
        self._btn_down.Bind(wx.EVT_BUTTON, lambda _e: self._move(1))
        for btn in (self._btn_add, self._btn_remove, self._btn_up, self._btn_down):
            row.Add(btn, 0, wx.RIGHT, 4)
        outer.Add(row, 0, wx.BOTTOM, 4)

        # Nesting row (flat lists only; hidden for definition lists). Indent /
        # Outdent / Add child operate on the selected item's subtree via the
        # wx-free quill.core.lists.nesting ops (PRD Phase 2).
        nest_row = wx.BoxSizer(wx.HORIZONTAL)
        self._btn_indent = wx.Button(dlg, label="&Indent")
        self._btn_outdent = wx.Button(dlg, label="&Outdent")
        self._btn_add_child = wx.Button(dlg, label="Add chil&d")
        self._btn_indent.Bind(wx.EVT_BUTTON, lambda _e: self._on_indent())
        self._btn_outdent.Bind(wx.EVT_BUTTON, lambda _e: self._on_outdent())
        self._btn_add_child.Bind(wx.EVT_BUTTON, lambda _e: self._on_add_child())
        for btn in (self._btn_indent, self._btn_outdent, self._btn_add_child):
            nest_row.Add(btn, 0, wx.RIGHT, 4)
        self._nest_row = nest_row
        outer.Add(nest_row, 0, wx.BOTTOM, 4)

        # Import row: pull text from the clipboard or a file into the current list
        # type; the live source preview below is the "preview" (§17.4–§17.5). The
        # imported list fully replaces the in-dialog model, so Cancel discards it —
        # nothing reaches the document until OK.
        import_row = wx.BoxSizer(wx.HORIZONTAL)
        self._btn_import_clip = wx.Button(dlg, label="Import from clip&board")
        self._btn_import_file = wx.Button(dlg, label="Import from fil&e...")
        self._btn_import_clip.Bind(wx.EVT_BUTTON, lambda _e: self._on_import_clipboard())
        self._btn_import_file.Bind(wx.EVT_BUTTON, lambda _e: self._on_import_file())
        for btn in (self._btn_import_clip, self._btn_import_file):
            import_row.Add(btn, 0, wx.RIGHT, 4)
        outer.Add(import_row, 0)
        return outer

    def _build_editor_panel(self, dlg: Any) -> Any:
        wx = self._wx
        panel = wx.BoxSizer(wx.VERTICAL)

        # Flat editor (item text + checked).
        self._item_label = wx.StaticText(dlg, label="Item te&xt:")
        panel.Add(self._item_label, 0, wx.BOTTOM, 4)
        self._item_text = wx.TextCtrl(dlg, style=wx.TE_MULTILINE)
        self._item_text.Bind(wx.EVT_TEXT, self._on_item_text)
        panel.Add(self._item_text, 1, wx.EXPAND | wx.BOTTOM, 6)
        self._checked_box = wx.CheckBox(dlg, label="Tas&k is complete")
        self._checked_box.Bind(wx.EVT_CHECKBOX, self._on_checked)
        panel.Add(self._checked_box, 0, wx.BOTTOM, 6)

        # Definition editor (term + definition). One term per line lets an entry
        # carry synonyms, which render as multiple <dt> (§15.3).
        self._term_label = wx.StaticText(dlg, label="Te&rms (one per line):")
        panel.Add(self._term_label, 0, wx.BOTTOM, 4)
        self._term_text = wx.TextCtrl(dlg, style=wx.TE_MULTILINE)
        self._term_text.Bind(wx.EVT_TEXT, self._on_term_text)
        panel.Add(self._term_text, 1, wx.EXPAND | wx.BOTTOM, 6)
        self._def_label = wx.StaticText(
            dlg, label="&Definition or description (blank line between several):"
        )
        panel.Add(self._def_label, 0, wx.BOTTOM, 4)
        self._def_text = wx.TextCtrl(dlg, style=wx.TE_MULTILINE)
        self._def_text.Bind(wx.EVT_TEXT, self._on_def_text)
        panel.Add(self._def_text, 1, wx.EXPAND)
        return panel

    # -- state helpers ----------------------------------------------------- #

    def _is_definition(self) -> bool:
        return self._type is ListType.DEFINITION

    def _type_index(self) -> int:
        for index, (_label, list_type) in enumerate(_TYPE_CHOICES):
            if list_type is self._type:
                return index
        return 0

    def _sync_type_visibility(self) -> None:
        definition = self._is_definition()
        for control in (self._term_label, self._term_text, self._def_label, self._def_text):
            control.Show(definition)
        for control in (self._item_label, self._item_text):
            control.Show(not definition)
        self._checked_box.Show(not definition and self._type is ListType.CHECKLIST)
        # Nesting only applies to flat lists; hide the Indent/Outdent/Add-child
        # row entirely for definition lists.
        for control in (self._btn_indent, self._btn_outdent, self._btn_add_child):
            control.Show(not definition)
        self._outline_label.SetLabel("&Entries:" if definition else "&Items:")
        self._refresh_nesting_buttons()
        if self.dialog is not None:
            self.dialog.Layout()

    def _refresh_nesting_buttons(self) -> None:
        """Enable Indent/Outdent for the selection per the structural rules."""
        if self._is_definition():
            return
        index = self._selected_index()
        self._btn_indent.Enable(index >= 0 and can_indent(self._flat.items, index))
        self._btn_outdent.Enable(index >= 0 and can_outdent(self._flat.items, index))
        self._btn_add_child.Enable(index >= 0)

    # -- outline ----------------------------------------------------------- #

    def _reload_outline(self, *, select: int | None = None) -> None:
        self._suppress = True
        try:
            self._outline.Clear()
            if self._is_definition():
                for index in range(len(self._definition.entries)):
                    self._outline.Append(self._entry_label(index))
                count = len(self._definition.entries)
            else:
                for index in range(len(self._flat.items)):
                    self._outline.Append(self._item_label_text(index))
                count = len(self._flat.items)
            if count:
                target = 0 if select is None else max(0, min(select, count - 1))
                self._outline.SetSelection(target)
        finally:
            self._suppress = False
        self._load_selected_into_fields()
        self._refresh_preview()

    def _item_label_text(self, index: int) -> str:
        # A leading indent makes nesting visible at a glance; the announcement
        # itself already carries "level N" for screen readers (announce.py).
        prefix = "    " * max(0, self._flat.items[index].level)
        return prefix + (flat_item_announcement(self._flat, index, self._settings) or "(empty)")

    def _entry_label(self, index: int) -> str:
        return definition_entry_announcement(self._definition, index, self._settings) or "(empty)"

    def _selected_index(self) -> int:
        sel = self._outline.GetSelection()
        return sel if sel is not None and sel >= 0 else -1

    def _load_selected_into_fields(self) -> None:
        index = self._selected_index()
        self._suppress = True
        try:
            if self._is_definition():
                entry = self._definition.entries[index] if index >= 0 else DefinitionEntry()
                self._term_text.SetValue(entry.terms_text())
                self._def_text.SetValue(entry.definitions_text())
            else:
                item = self._flat.items[index] if index >= 0 else ListItem("")
                self._item_text.SetValue(item.text)
                self._checked_box.SetValue(item.checked)
        finally:
            self._suppress = False
        self._refresh_nesting_buttons()

    # -- event handlers ---------------------------------------------------- #

    def _on_type_changed(self, _event: Any) -> None:
        if self._suppress:
            return
        old_type = self._type
        new_type = _TYPE_CHOICES[self._type_choice.GetSelection()][1]
        if new_type is old_type:
            return
        # Crossing the flat<->definition boundary carries content across with a
        # loss check (§19); switches among flat types are lossless (just relabel).
        crossing = (old_type is ListType.DEFINITION) != (new_type is ListType.DEFINITION)
        if crossing and not self._convert_across_boundary(new_type):
            # The user declined a lossy conversion: restore the previous type.
            self._suppress = True
            try:
                self._type_choice.SetSelection(self._type_index())
            finally:
                self._suppress = False
            return
        self._type = new_type
        if not self._is_definition():
            self._flat.list_type = new_type
        self._sync_type_visibility()
        self._reload_outline(select=0)

    def _convert_across_boundary(self, new_type: ListType) -> bool:
        """Convert the current model to ``new_type``'s side. Return False if declined.

        A lossy conversion (dropped checked states, nesting, alternate terms, or
        extra definitions) is offered to ``confirm_conversion`` first; returning
        False leaves both models untouched so the caller can revert the choice.
        """
        if new_type is ListType.DEFINITION:
            converted, loss = flat_to_definition(self._flat)
            if loss.lossy and not self._approve_loss(loss.reasons):
                return False
            self._definition = converted
        else:
            converted, loss = definition_to_flat(self._definition, list_type=new_type)
            if loss.lossy and not self._approve_loss(loss.reasons):
                return False
            self._flat = converted
        return True

    def _approve_loss(self, reasons: list[str]) -> bool:
        """True when the lossy conversion may proceed (no hook = proceed silently)."""
        if self._confirm_conversion is None:
            return True
        return bool(self._confirm_conversion(reasons))

    def _on_format_changed(self, _event: Any) -> None:
        self._format = "markdown" if self._format_choice.GetSelection() == 0 else "html"
        self._refresh_preview()

    def _on_outline_select(self, _event: Any) -> None:
        if self._suppress:
            return
        self._load_selected_into_fields()

    def _on_item_text(self, _event: Any) -> None:
        if self._suppress:
            return
        index = self._selected_index()
        if index >= 0:
            self._flat.items[index].text = self._item_text.GetValue()
            self._update_outline_label(index, self._item_label_text(index))
            self._refresh_preview()

    def _on_checked(self, _event: Any) -> None:
        if self._suppress:
            return
        index = self._selected_index()
        if index >= 0:
            self._flat.items[index].checked = self._checked_box.GetValue()
            self._update_outline_label(index, self._item_label_text(index))
            self._refresh_preview()

    def _on_term_text(self, _event: Any) -> None:
        if self._suppress:
            return
        index = self._selected_index()
        if index >= 0:
            self._definition.entries[index].set_terms_text(self._term_text.GetValue())
            self._update_outline_label(index, self._entry_label(index))
            self._refresh_preview()

    def _on_def_text(self, _event: Any) -> None:
        if self._suppress:
            return
        index = self._selected_index()
        if index >= 0:
            self._definition.entries[index].set_definitions_text(self._def_text.GetValue())
            self._update_outline_label(index, self._entry_label(index))
            self._refresh_preview()

    def _update_outline_label(self, index: int, label: str) -> None:
        self._suppress = True
        try:
            self._outline.SetString(index, label)
        finally:
            self._suppress = False

    def _on_add(self, _event: Any) -> None:
        index = self._selected_index()
        if self._is_definition():
            at = index + 1 if index >= 0 else len(self._definition.entries)
            self._definition.entries.insert(at, DefinitionEntry())
        else:
            at = index + 1 if index >= 0 else len(self._flat.items)
            self._flat.items.insert(at, ListItem(""))
        self._reload_outline(select=at)

    def _on_remove(self, _event: Any) -> None:
        index = self._selected_index()
        if index < 0:
            return
        collection = self._definition.entries if self._is_definition() else self._flat.items
        if len(collection) <= 1:
            collection[0] = DefinitionEntry() if self._is_definition() else ListItem("")
            self._reload_outline(select=0)
            return
        del collection[index]
        self._reload_outline(select=min(index, len(collection) - 1))

    def _move(self, delta: int) -> None:
        index = self._selected_index()
        if index < 0:
            return
        if self._is_definition():
            entries = self._definition.entries
            target = index + delta
            if target < 0 or target >= len(entries):
                return
            entries[index], entries[target] = entries[target], entries[index]
            self._reload_outline(select=target)
            return
        # Flat lists reorder whole subtrees among siblings so a parent never
        # leaves its children behind (PRD Phase 2 — subtree moves).
        new_index = move_subtree(self._flat.items, index, 1 if delta > 0 else -1)
        if new_index != index:
            self._reload_outline(select=new_index)

    def _on_indent(self) -> None:
        index = self._selected_index()
        if index < 0 or self._is_definition():
            return
        if indent(self._flat.items, index):
            self._reload_outline(select=index)

    def _on_outdent(self) -> None:
        index = self._selected_index()
        if index < 0 or self._is_definition():
            return
        if outdent(self._flat.items, index):
            self._reload_outline(select=index)

    def _on_add_child(self) -> None:
        index = self._selected_index()
        if self._is_definition():
            return
        new_index = add_child(self._flat.items, index)
        self._reload_outline(select=new_index)

    # -- import ------------------------------------------------------------ #

    def _on_import_clipboard(self) -> None:
        wx = self._wx
        text = ""
        clipboard = getattr(wx, "TheClipboard", None)
        if clipboard is not None and clipboard.Open():
            try:
                data = wx.TextDataObject()
                if clipboard.GetData(data):
                    text = data.GetText()
            finally:
                clipboard.Close()
        self._import_text(text)

    def _on_import_file(self) -> None:
        wx = self._wx
        with wx.FileDialog(
            self.dialog,
            "Import list from text file",
            wildcard="Text files (*.txt;*.md)|*.txt;*.md|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:  # GATE-42-OK: native wx.FileDialog
                return
            path = dlg.GetPath()
        try:
            from pathlib import Path

            text = Path(path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        self._import_text(text)

    def _import_text(self, text: str) -> None:
        """Replace the current model with one interpreted from imported text.

        Nothing reaches the document until OK, so a replace is safe; the live
        source preview is the interpretation preview (§17.4–§17.5).
        """
        if not text.strip():
            return
        if self._is_definition():
            self._definition = interpret_text_into_definition(text, self._settings)
        else:
            self._flat = interpret_text_into_flat(text, self._settings)
            self._type = self._flat.list_type
            self._type_choice.SetSelection(self._type_index())
        self._sync_type_visibility()
        self._reload_outline(select=0)

    # -- preview + commit -------------------------------------------------- #

    def _current_model(self) -> FlatList | DefinitionList:
        return self._definition if self._is_definition() else self._flat

    def _refresh_preview(self) -> None:
        try:
            source = self._render()
            self._preview.SetValue(source)
        except DefinitionProfileError as exc:
            self._preview.SetValue(f"{exc}\n\nChoose HTML format, or configure a Markdown profile.")

    def _render(self) -> str:
        model = self._current_model()
        if self._format == "html":
            return render_html(model, self._settings)
        return render_markdown(model, self._settings)

    def _on_ok(self, event: Any) -> None:
        source = self._resolve_source()
        if source is None:
            return  # user cancelled the definition-profile prompt; keep the dialog open
        self.result_source = source
        event.Skip()  # let the dialog close with ID_OK

    def _resolve_source(self) -> str | None:
        """The source to commit, or None if a needed profile prompt was cancelled.

        For a Markdown definition list with no configured profile, this asks the
        user how to proceed (§7.6/§21.3) instead of silently emitting HTML.
        """
        try:
            return self._render()
        except DefinitionProfileError:
            prompt = self._resolve_definition_fallback or self._prompt_definition_fallback
            choice = prompt()
            if choice is None:
                return None
            return render_definition_with_choice(self._current_model(), self._settings, choice)

    def _prompt_definition_fallback(self) -> str | None:
        """Ask how to render a definition list with no Markdown profile (§21.3)."""
        from quill.ui.list_studio_prompts import prompt_definition_fallback

        return prompt_definition_fallback(self._wx, self.dialog)

    @property
    def summary(self) -> str:
        return list_summary(self._current_model(), self._settings)

    def validation_issues(self) -> list[str]:
        """Pre-commit issues for the captured result (§26); empty means safe.

        Called by the caller after the dialog returns OK and before the source
        replaces document text, so a non-empty result can leave the document
        unchanged.
        """
        return validate_before_commit(self._current_model(), self.result_source, self._format)
