"""Vision Prompt Manager dialog — enable/disable built-in styles, manage custom prompts.

Opened from Settings > AI > "Image Prompt Styles…".  Provides a list of all
built-in and custom prompt styles with a read-only preview pane, enable/disable
toggle for built-ins, and Add/Edit/Delete for custom prompts.  Changes are
written to settings on Close (no Cancel — following the pattern of other Quill
settings panels).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import wx

from quill.core.ai.vision_prompts import (
    BUILTIN_PROMPT_STYLES,
    BUILTIN_STYLE_IDS,
)
from quill.core.settings import save_settings
from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog

if TYPE_CHECKING:
    from quill.core.settings import Settings


class VisionPromptManagerDialog:
    """Manage built-in and custom image description prompt styles."""

    def __init__(self, parent: object, settings: Settings) -> None:
        self._settings = settings
        self._disabled: set[str] = set(settings.vision_disabled_builtin_styles)
        self._custom: list[dict] = list(settings.vision_custom_prompts)

        self.dialog = wx.Dialog(
            parent,
            title="Manage Image Prompts",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize((720, 560))
        self.dialog.SetName("Manage Image Prompts")

        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)

        # Instructions
        intro = wx.StaticText(
            panel,
            label=(
                "Enable or disable built-in description styles, and add your own "
                "custom prompts. Select a style to preview its full prompt text."
            ),
        )
        intro.Wrap(680)
        root.Add(intro, 0, wx.EXPAND | wx.ALL, 10)

        # List of styles
        list_label = wx.StaticText(panel, label="&Prompt styles:")
        root.Add(list_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)

        self._listbox = wx.ListBox(panel, style=wx.LB_SINGLE)
        self._listbox.SetName("Prompt style list")
        root.Add(self._listbox, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        # Preview pane
        preview_label = wx.StaticText(panel, label="Prompt &text (read-only):")
        root.Add(preview_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)

        self._preview = wx.TextCtrl(
            panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY,
            size=(-1, 120),
        )
        self._preview.SetName("Prompt text preview")
        root.Add(self._preview, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Buttons row
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self._btn_toggle = wx.Button(panel, label="&Disable")
        self._btn_toggle.SetName("Toggle enable/disable")
        self._btn_toggle.Bind(wx.EVT_BUTTON, self._on_toggle)
        btn_sizer.Add(self._btn_toggle, 0, wx.RIGHT, 6)

        self._btn_add = wx.Button(panel, label="&Add…")
        self._btn_add.SetName("Add custom prompt")
        self._btn_add.Bind(wx.EVT_BUTTON, self._on_add)
        btn_sizer.Add(self._btn_add, 0, wx.RIGHT, 6)

        self._btn_edit = wx.Button(panel, label="&Edit…")
        self._btn_edit.SetName("Edit custom prompt")
        self._btn_edit.Bind(wx.EVT_BUTTON, self._on_edit)
        btn_sizer.Add(self._btn_edit, 0, wx.RIGHT, 6)

        self._btn_delete = wx.Button(panel, label="De&lete")
        self._btn_delete.SetName("Delete custom prompt")
        self._btn_delete.Bind(wx.EVT_BUTTON, self._on_delete)
        btn_sizer.Add(self._btn_delete, 0, wx.RIGHT, 6)

        btn_sizer.AddStretchSpacer()

        close_btn = wx.Button(panel, id=wx.ID_CLOSE, label="&Close")
        close_btn.SetName("Close")
        close_btn.Bind(wx.EVT_BUTTON, self._on_close)
        btn_sizer.Add(close_btn, 0)

        root.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizerAndFit(outer)

        apply_modal_ids(self.dialog, affirmative_id=wx.ID_CLOSE, escape_id=wx.ID_CLOSE)

        self.dialog.Bind(
            wx.EVT_CHAR_HOOK,
            lambda e: self._on_close(None) if e.GetKeyCode() == wx.WXK_ESCAPE else e.Skip(),
        )

        # Populate the list
        self._rebuild_list()
        self._listbox.Bind(wx.EVT_LISTBOX, self._on_selection_changed)
        if self._listbox.GetCount() > 0:
            self._listbox.SetSelection(0)
            self._update_preview(0)
        self._update_button_states()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _all_entries(self) -> list[dict]:
        """Return the merged list of built-in + custom entries for display."""
        entries: list[dict] = []
        for style in BUILTIN_PROMPT_STYLES:
            sid = style["id"]
            entries.append({
                "id": sid,
                "title": style["title"],
                "prompt": style["prompt"],
                "kind": "builtin",
                "disabled": sid in self._disabled,
            })
        for entry in self._custom:
            entries.append({
                "id": entry.get("id", ""),
                "title": entry.get("title", entry.get("id", "")),
                "prompt": entry.get("prompt", ""),
                "kind": "custom",
                "disabled": False,
            })
        return entries

    def _rebuild_list(self) -> None:
        """Rebuild the listbox from current state."""
        self._listbox.Clear()
        for entry in self._all_entries():
            label = entry["title"]
            if entry["kind"] == "builtin" and entry["disabled"]:
                label = f"[hidden] {label}"
            self._listbox.Append(label)

    def _update_preview(self, index: int) -> None:
        """Update the preview pane for the entry at *index*."""
        entries = self._all_entries()
        if 0 <= index < len(entries):
            self._preview.SetValue(entries[index]["prompt"])
        else:
            self._preview.SetValue("")

    def _update_button_states(self) -> None:
        """Enable/disable buttons based on the current selection."""
        sel = self._listbox.GetSelection()
        if sel < 0:
            self._btn_toggle.Disable()
            self._btn_edit.Disable()
            self._btn_delete.Disable()
            return

        entries = self._all_entries()
        if sel >= len(entries):
            return
        entry = entries[sel]

        if entry["kind"] == "builtin":
            self._btn_toggle.Enable()
            self._btn_toggle.SetLabel("&Enable" if entry["disabled"] else "&Disable")
            self._btn_edit.Disable()
            self._btn_delete.Disable()
        else:
            self._btn_toggle.Disable()
            self._btn_toggle.SetLabel("&Disable")
            self._btn_edit.Enable()
            self._btn_delete.Enable()

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_selection_changed(self, _event: wx.CommandEvent) -> None:
        sel = self._listbox.GetSelection()
        self._update_preview(sel)
        self._update_button_states()

    def _on_toggle(self, _event: wx.CommandEvent) -> None:
        sel = self._listbox.GetSelection()
        entries = self._all_entries()
        if sel < 0 or sel >= len(entries):
            return
        entry = entries[sel]
        if entry["kind"] != "builtin":
            return
        sid = entry["id"]
        if sid in self._disabled:
            self._disabled.discard(sid)
        else:
            self._disabled.add(sid)
        self._rebuild_list()
        # Try to keep the same item selected
        if sel < self._listbox.GetCount():
            self._listbox.SetSelection(sel)
        self._update_preview(self._listbox.GetSelection())
        self._update_button_states()

    def _on_add(self, _event: wx.CommandEvent) -> None:
        result = self._show_prompt_editor("Add Custom Prompt", "", "")
        if result is None:
            return
        new_id, new_title, new_prompt = result
        self._custom.append({"id": new_id, "title": new_title, "prompt": new_prompt})
        self._rebuild_list()
        # Select the newly added item
        last = self._listbox.GetCount() - 1
        if last >= 0:
            self._listbox.SetSelection(last)
            self._update_preview(last)
        self._update_button_states()

    def _on_edit(self, _event: wx.CommandEvent) -> None:
        sel = self._listbox.GetSelection()
        entries = self._all_entries()
        if sel < 0 or sel >= len(entries):
            return
        entry = entries[sel]
        if entry["kind"] != "custom":
            return
        # Find the custom entry index
        custom_idx = None
        for i, c in enumerate(self._custom):
            if c.get("id") == entry["id"]:
                custom_idx = i
                break
        if custom_idx is None:
            return
        result = self._show_prompt_editor(
            "Edit Custom Prompt",
            entry["title"],
            entry["prompt"],
            exclude_id=entry["id"],
        )
        if result is None:
            return
        new_id, new_title, new_prompt = result
        self._custom[custom_idx] = {"id": new_id, "title": new_title, "prompt": new_prompt}
        self._rebuild_list()
        if sel < self._listbox.GetCount():
            self._listbox.SetSelection(sel)
            self._update_preview(sel)
        self._update_button_states()

    def _on_delete(self, _event: wx.CommandEvent) -> None:
        sel = self._listbox.GetSelection()
        entries = self._all_entries()
        if sel < 0 or sel >= len(entries):
            return
        entry = entries[sel]
        if entry["kind"] != "custom":
            return
        # Confirm
        dlg = wx.MessageDialog(
            self.dialog,
            f'Delete the custom prompt "{entry["title"]}"?',
            "Delete Custom Prompt",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
        )
        dlg.SetName("Delete custom prompt confirmation")
        result = show_modal_dialog(dlg, "Delete Custom Prompt")
        dlg.Destroy()
        if result != wx.ID_YES:
            return
        # Remove from custom list
        self._custom = [c for c in self._custom if c.get("id") != entry["id"]]
        self._rebuild_list()
        new_sel = min(sel, self._listbox.GetCount() - 1)
        if new_sel >= 0:
            self._listbox.SetSelection(new_sel)
            self._update_preview(new_sel)
        self._update_button_states()

    def _on_close(self, _event: object) -> None:
        """Write changes to settings and close."""
        self._settings.vision_disabled_builtin_styles = sorted(self._disabled)
        self._settings.vision_custom_prompts = self._custom
        # Reset the default style if it is no longer reachable: a built-in was
        # disabled, a custom prompt was deleted, or a custom prompt's title was
        # edited (which regenerates its ID).
        current_default = self._settings.vision_default_prompt_style
        surviving_custom_ids = {e.get("id", "") for e in self._custom}
        if current_default in self._disabled or (
            current_default not in BUILTIN_STYLE_IDS and current_default not in surviving_custom_ids
        ):
            self._settings.vision_default_prompt_style = "accessibility"
        save_settings(self._settings)
        self.dialog.EndModal(wx.ID_CLOSE)

    # ------------------------------------------------------------------
    # Sub-dialog: prompt text editor
    # ------------------------------------------------------------------

    def _show_prompt_editor(
        self, title: str, initial_title: str, initial_prompt: str, *, exclude_id: str = ""
    ) -> tuple[str, str, str] | None:
        """Show a sub-dialog for editing a custom prompt's title and text.

        Returns ``(id, title, prompt)`` or ``None`` if cancelled.
        """
        dlg = wx.Dialog(
            self.dialog,
            title=title,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        dlg.SetSize((500, 400))
        dlg.SetName(title)

        panel = wx.Panel(dlg)
        root = wx.BoxSizer(wx.VERTICAL)

        # Title field
        root.Add(
            wx.StaticText(panel, label="Style &title:"),
            0,
            wx.LEFT | wx.RIGHT | wx.TOP,
            10,
        )
        title_ctrl = wx.TextCtrl(panel, value=initial_title)
        title_ctrl.SetName("Style title")
        root.Add(title_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Prompt text field
        root.Add(
            wx.StaticText(panel, label="&Prompt text:"),
            0,
            wx.LEFT | wx.RIGHT | wx.TOP,
            10,
        )
        prompt_ctrl = wx.TextCtrl(
            panel,
            value=initial_prompt,
            style=wx.TE_MULTILINE,
        )
        prompt_ctrl.SetName("Prompt text")
        prompt_ctrl.SetMinSize((460, 200))
        root.Add(prompt_ctrl, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        ok_btn = wx.Button(panel, id=wx.ID_OK, label="&OK")
        ok_btn.SetDefault()
        cancel_btn = wx.Button(panel, id=wx.ID_CANCEL, label="&Cancel")
        btn_sizer.Add(ok_btn, 0, wx.RIGHT, 6)
        btn_sizer.Add(cancel_btn, 0)
        root.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        dlg.SetSizerAndFit(outer)

        apply_modal_ids(dlg, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)

        if show_modal_dialog(dlg, title) != wx.ID_OK:
            dlg.Destroy()
            return None

        new_title = title_ctrl.GetValue().strip()
        new_prompt = prompt_ctrl.GetValue().strip()
        dlg.Destroy()

        if not new_title or not new_prompt:
            return None

        # Generate a stable ID from the title
        new_id = re.sub(r"[^a-z0-9]+", "-", new_title.lower()).strip("-")
        if not new_id:
            new_id = "custom-prompt"
        # Avoid collision with built-in IDs
        if new_id in BUILTIN_STYLE_IDS:
            new_id = f"custom-{new_id}"
        # Avoid collision with existing custom prompt IDs (excluding the entry
        # being edited, if any)
        existing_custom_ids = {e.get("id", "") for e in self._custom if e.get("id") != exclude_id}
        if new_id in existing_custom_ids:
            suffix = 2
            base_id = new_id
            while f"{base_id}-{suffix}" in existing_custom_ids:
                suffix += 1
            new_id = f"{base_id}-{suffix}"

        return new_id, new_title, new_prompt

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show_modal(self) -> None:
        """Show the dialog modally.  Changes are saved on Close."""
        self.dialog.CentreOnParent()
        try:
            show_modal_dialog(
                self.dialog,
                "Manage Image Prompts",
            )
        finally:
            self.dialog.Destroy()


__all__ = ["VisionPromptManagerDialog"]
