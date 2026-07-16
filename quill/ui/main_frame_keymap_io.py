"""Keyboard packs, keymap sharing, and factory resets for MainFrame (CQ-1).

``KeymapIoMixin`` owns keyboard-pack selection, keymap and keyboard-pack file
import/export, the Share dialogs (export/back up and import/restore settings
packages), recommended-keymap migration (apply, surface the notice, undo),
keymap reset, and reset-all-to-factory-defaults with the shortcut reload that
follows. Extracted verbatim from ``main_frame.py``; runs on ``MainFrame``
(``self``).
"""

from __future__ import annotations

from pathlib import Path

from quill import __version__
from quill.core.commands import CommandRegistry
from quill.core.keymap import (
    DEFAULT_KEYMAP,
    KEYBOARD_PACK_CUSTOM,
    KEYBOARD_PACK_DEFAULT,
    KQP_EXTENSION,
    build_keymap_for_pack,
    export_keyboard_pack,
    export_keymap,
    import_keyboard_pack,
    import_keymap,
    keyboard_pack_description,
    reset_keymap,
    save_keymap,
)
from quill.core.settings import save_settings
from quill.ui.dialog_contract import (
    apply_modal_ids,
    set_accessible_name,
)


class KeymapIoMixin:
    def _set_keyboard_pack(self, pack_name: str) -> None:
        self.settings.keyboard_pack = pack_name
        save_settings(self.settings)

    def _mark_keyboard_pack_custom(self) -> None:
        if self.settings.keyboard_pack == KEYBOARD_PACK_CUSTOM:
            return
        self._set_keyboard_pack(KEYBOARD_PACK_CUSTOM)

    def apply_keyboard_pack(self, pack_name: str) -> None:
        if pack_name == KEYBOARD_PACK_CUSTOM:
            self._set_status("Custom layouts are created from manual keymap edits")
            return
        self.keymap = build_keymap_for_pack(pack_name)
        save_keymap(self.keymap)
        self._set_keyboard_pack(pack_name)
        self._reload_shortcuts_from_keymap()
        self._set_status(f"Keyboard pack changed to {pack_name}")

    def export_keymap_file(self) -> None:
        wx = self._wx
        with wx.FileDialog(
            self.frame,
            "Export keymap",
            wildcard="JSON files (*.json)|*.json|All files (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Export keymap") != wx.ID_OK:
                return
            target = Path(dialog.GetPath())
        export_keymap(target, self.keymap)
        self._set_status(f"Exported keymap to {target.name}")

    def open_share_export_dialog(self) -> None:
        """SHARE-1: Export and back up settings, features, and customizations.

        Profile mode produces a privacy-clean package that never includes
        machine-specific paths or secrets; backup mode keeps everything for the
        person's own use.
        """
        from quill.core.share_package import (
            KIND_BACKUP,
            KIND_PROFILE,
            PackageError,
            extension_for_kind,
        )
        from quill.ui.share_dialogs import build_export_document, gather_export_offers, write_export

        wx = self._wx
        offers = gather_export_offers(self.settings, self.features)
        if not offers:
            self._set_status("Nothing available to export")
            return
        dialog = wx.Dialog(self.frame, title="Export and Back Up", size=(560, 460))
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                dialog,
                label=(
                    "Share a profile to give someone your setup without personal "
                    "paths or secrets, or back up everything for yourself."
                ),
            ),
            0,
            wx.ALL | wx.EXPAND,
            8,
        )
        kind_choice = wx.RadioBox(
            dialog,
            label="What to create",
            choices=["Share a profile (privacy-clean)", "Back up everything"],
            majorDimension=1,
            style=wx.RA_SPECIFY_COLS,
        )
        root.Add(kind_choice, 0, wx.ALL | wx.EXPAND, 8)
        root.Add(wx.StaticText(dialog, label="&Name:"), 0, wx.LEFT | wx.RIGHT, 8)
        name_field = wx.TextCtrl(dialog, value="My QUILL setup")
        set_accessible_name(name_field, "Name")
        root.Add(name_field, 0, wx.ALL | wx.EXPAND, 8)
        root.Add(
            wx.StaticText(dialog, label="Include these sections:"),
            0,
            wx.LEFT | wx.RIGHT,
            8,
        )
        chooser = wx.CheckListBox(  # A11Y-SR-1-OK: export picker; pending CheckBox conversion
            dialog,
            choices=[f"{offer.title} - {offer.summary}" for offer in offers],
        )
        set_accessible_name(chooser, "Include these sections")
        for index in range(len(offers)):
            chooser.Check(index, True)
        root.Add(chooser, 1, wx.ALL | wx.EXPAND, 8)
        buttons = dialog.CreateButtonSizer(wx.OK | wx.CANCEL)
        if buttons is not None:
            ok_button = dialog.FindWindowById(wx.ID_OK)
            if ok_button is not None:
                ok_button.SetDefault()
        if buttons is not None:
            root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        dialog.SetSizerAndFit(root)

        def sync_private(_event: object = None) -> None:
            profile_mode = kind_choice.GetSelection() == 0
            for index, offer in enumerate(offers):
                if offer.private:
                    if profile_mode:
                        chooser.Check(index, False)
                    chooser.Enable(index, not profile_mode)

        kind_choice.Bind(wx.EVT_RADIOBOX, sync_private)
        sync_private()

        if self._show_modal_dialog(dialog, "Export and Back Up") != wx.ID_OK:
            self._set_status("Export cancelled")
            return
        profile_mode = kind_choice.GetSelection() == 0
        kind = KIND_PROFILE if profile_mode else KIND_BACKUP
        selected_ids = [
            offers[index].id for index in range(len(offers)) if chooser.IsChecked(index)
        ]
        name = name_field.GetValue().strip() or "My QUILL setup"
        if not selected_ids:
            self._set_status("Select at least one section to export")
            return
        try:
            document = build_export_document(
                kind=kind,
                name=name,
                source_version=__version__,
                selected_ids=selected_ids,
                offers=offers,
            )
        except (ValueError, PackageError) as exc:
            self._show_error_with_hint(
                str(exc),
                "Export",
                "Check that all selected sections are valid and that QUILL has permission "
                "to read the source data. If the error persists, try exporting fewer sections.",
            )
            self._set_status("Export failed")
            return
        extension = extension_for_kind(kind)
        label = "profile" if profile_mode else "backup"
        wildcard = f"QUILL {label} (*{extension})|*{extension}|All files (*.*)|*.*"
        with wx.FileDialog(
            self.frame,
            "Save export",
            wildcard=wildcard,
            defaultFile=f"{name}{extension}",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as file_dialog:
            if self._show_modal_dialog(file_dialog, "Save export") != wx.ID_OK:
                self._set_status("Export cancelled")
                return
            target = Path(file_dialog.GetPath())
        try:
            write_export(document, target)
        except OSError as exc:
            self._show_error_with_hint(
                str(exc),
                "Export",
                "Verify the destination folder is writable and that no other application "
                "has the file open. Check available disk space.",
            )
            self._set_status("Export failed")
            return
        self._set_status(f"Saved {label} with {len(selected_ids)} section(s) to {target.name}")

    def open_share_import_dialog(self) -> None:
        """SHARE-2: Import a profile or restore a backup, with preview and undo.

        Feature changes are snapshotted and rolled back automatically if any
        section fails to apply, so a bad file never leaves the app half-changed.
        """
        from quill.core.share_package import PackageError, package_summary
        from quill.ui.share_dialogs import apply_import, importable_sections, read_import

        wx = self._wx
        with wx.FileDialog(
            self.frame,
            "Open profile or backup",
            wildcard=(
                "QUILL profile or backup (*.quillprofile;*.quillbackup)"
                "|*.quillprofile;*.quillbackup|All files (*.*)|*.*"
            ),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as file_dialog:
            if self._show_modal_dialog(file_dialog, "Open profile or backup") != wx.ID_OK:
                self._set_status("Import cancelled")
                return
            source = Path(file_dialog.GetPath())
        try:
            package = read_import(source)
        except (PackageError, OSError, ValueError) as exc:
            self._show_error_with_hint(
                str(exc),
                "Import",
                "Check that the file is a valid QUILL profile or backup (*.quillprofile or "
                "*.quillbackup). If the file came from a different QUILL version, export a "
                "fresh copy and try again.",
            )
            self._set_status("Import failed")
            return
        sections = importable_sections(package)
        if not sections:
            self._show_message_box(
                "This file has no sections QUILL can import.",
                "Import",
                wx.ICON_INFORMATION | wx.OK,
            )
            self._set_status("Nothing to import")
            return
        dialog = wx.Dialog(self.frame, title="Import and Restore", size=(580, 480))
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                dialog,
                label="Review what this file contains, then choose what to apply.",
            ),
            0,
            wx.ALL | wx.EXPAND,
            8,
        )
        preview = wx.TextCtrl(
            dialog,
            value=package_summary(package),
            style=wx.TE_MULTILINE | wx.TE_READONLY,
        )
        set_accessible_name(preview, "File contents")
        root.Add(preview, 1, wx.ALL | wx.EXPAND, 8)
        root.Add(wx.StaticText(dialog, label="Apply these sections:"), 0, wx.LEFT | wx.RIGHT, 8)
        chooser = wx.CheckListBox(  # A11Y-SR-1-OK: import picker; pending CheckBox conversion
            dialog,
            choices=[f"{title} - {summary}" for _id, title, summary in sections],
        )
        set_accessible_name(chooser, "Apply these sections")
        for index in range(len(sections)):
            chooser.Check(index, True)
        root.Add(chooser, 1, wx.ALL | wx.EXPAND, 8)
        buttons = dialog.CreateButtonSizer(wx.OK | wx.CANCEL)
        if buttons is not None:
            ok_button = dialog.FindWindowById(wx.ID_OK)
            if ok_button is not None:
                ok_button.SetDefault()
        if buttons is not None:
            root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        dialog.SetSizerAndFit(root)
        if self._show_modal_dialog(dialog, "Import and Restore") != wx.ID_OK:
            self._set_status("Import cancelled")
            return
        selected_ids = [
            sections[index][0] for index in range(len(sections)) if chooser.IsChecked(index)
        ]
        if not selected_ids:
            self._set_status("Select at least one section to import")
            return
        try:
            outcome = apply_import(package, selected_ids, self.settings, self.features)
        except (PackageError, ValueError) as exc:
            self._show_error_with_hint(
                str(exc),
                "Import",
                "The import was rolled back; no changes were applied. "
                "Try importing individual sections one at a time to identify "
                "the problematic entry.",
            )
            self._set_status("Import failed; no changes were applied")
            return
        applied = len(outcome.applied)
        if outcome.settings is not None:
            self.settings = outcome.settings
            self._settings_dialog_apply_refresh(f"Imported {applied} section(s)")
        else:
            self._build_menu()
            self._set_status(f"Imported {applied} section(s)")
        notes = list(package.warnings) + list(outcome.warnings)
        if notes:
            self._show_message_box("\n".join(notes), "Import notes", wx.ICON_INFORMATION | wx.OK)

    def import_keymap_file(self) -> None:
        wx = self._wx
        with wx.FileDialog(
            self.frame,
            "Import keymap",
            wildcard="JSON files (*.json)|*.json|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Import keymap") != wx.ID_OK:
                return
            source = Path(dialog.GetPath())
        self.keymap = import_keymap(source)
        self._mark_keyboard_pack_custom()
        self._reload_shortcuts_from_keymap()
        self._set_status(f"Imported keymap from {source.name}")

    def export_keyboard_pack_file(self) -> None:
        wx = self._wx
        pack_name = self.settings.keyboard_pack
        pack_desc = keyboard_pack_description(pack_name)

        # Collect name and description via a simple dialog before the file picker.
        dlg = wx.Dialog(self.frame, title="Export Keyboard Pack", size=(480, 220))
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(wx.StaticText(dlg, label="Pack &name:"), 0, wx.ALL, 8)
        name_ctrl = wx.TextCtrl(dlg, value=pack_name)
        set_accessible_name(name_ctrl, "Pack name")
        root.Add(name_ctrl, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 8)
        root.Add(
            wx.StaticText(dlg, label="&Description (optional):"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8
        )
        desc_ctrl = wx.TextCtrl(dlg, value=pack_desc if pack_desc else "")
        set_accessible_name(desc_ctrl, "Description, optional")
        root.Add(desc_ctrl, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 8)
        buttons = dlg.CreateButtonSizer(wx.OK | wx.CANCEL)
        if buttons is not None:
            root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        apply_modal_ids(dlg, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        dlg.SetSizer(root)

        if self._show_modal_dialog(dlg, "Export Keyboard Pack") != wx.ID_OK:
            return
        name = name_ctrl.GetValue().strip() or pack_name
        description = desc_ctrl.GetValue().strip()

        default_file = name.replace(" ", "-").lower() + KQP_EXTENSION
        with wx.FileDialog(
            self.frame,
            "Export keyboard pack",
            defaultFile=default_file,
            wildcard=self.KQP_WILDCARD,
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as file_dlg:
            if self._show_modal_dialog(file_dlg, "Export keyboard pack") != wx.ID_OK:
                return
            target = Path(file_dlg.GetPath())
        if target.suffix.lower() != KQP_EXTENSION:
            target = target.with_suffix(KQP_EXTENSION)
        export_keyboard_pack(target, self.keymap, name=name, description=description)
        self._set_status(f"Exported keyboard pack to {target.name}")

    def import_keyboard_pack_file(self) -> None:
        wx = self._wx
        with wx.FileDialog(
            self.frame,
            "Import keyboard pack",
            wildcard=self.KQP_WILDCARD,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Import keyboard pack") != wx.ID_OK:
                return
            source = Path(dialog.GetPath())
        try:
            name, description, merged = import_keyboard_pack(source)
        except ValueError as exc:
            self._show_message_box(str(exc), "Import Failed", wx.ICON_ERROR | wx.OK)
            return
        self.keymap = merged
        self._mark_keyboard_pack_custom()
        self._reload_shortcuts_from_keymap()
        summary = f"Imported keyboard pack: {name}"
        if description:
            summary += f". {description}"
        self._set_status(summary)

    def _apply_recommended_keymap_updates(self) -> None:
        """Force-once important default changes (e.g. Find -> Ctrl+F) at startup.

        Honors the user's opt-out (``settings.apply_recommended_keymap_updates``)
        and applies each registered update at most once, recording applied ids in
        ``settings.applied_recommended_updates`` so a binding is never re-forced
        and the user stays free to rebind afterward. See
        ``quill.core.recommended_updates``.
        """
        from quill.core.recommended_updates import (
            RECOMMENDED_KEYMAP_UPDATES,
            RECOMMENDED_SETTINGS_UPDATES,
            apply_recommended_keymap_updates,
            apply_recommended_settings_updates,
        )
        from quill.core.settings import save_settings as _save_settings

        enabled = getattr(self.settings, "apply_recommended_keymap_updates", True)
        already = set(getattr(self.settings, "applied_recommended_updates", []))

        # Keymap updates (e.g. Find -> Ctrl+F).
        updated_keymap, keymap_newly = apply_recommended_keymap_updates(
            self.keymap,
            already,
            enabled=enabled,
            valid_command_ids=frozenset(DEFAULT_KEYMAP),
        )
        # Settings updates: force a changed settings default once (the settings
        # analog, so a changed default reaches already-upgraded users too).
        settings_newly = apply_recommended_settings_updates(
            lambda field, value: setattr(self.settings, field, value),
            already | keymap_newly,
            enabled=enabled,
            valid_fields=frozenset(self.settings.__dataclass_fields__),
        )
        newly = keymap_newly | settings_newly
        if not newly:
            return
        # Capture the prior bindings (self.keymap still holds them) so the
        # migration notice can offer a one-click Undo of the shortcut change, and
        # collect human reasons from both kinds of update for the notice.
        applied_keymap = [u for u in RECOMMENDED_KEYMAP_UPDATES if u.id in keymap_newly]
        applied_settings = [u for u in RECOMMENDED_SETTINGS_UPDATES if u.id in settings_newly]
        self._recommended_update_undo = {
            u.command_id: self.keymap.get(u.command_id, "") for u in applied_keymap
        }
        self._recommended_update_summaries = [u.reason for u in applied_keymap] + [
            u.reason for u in applied_settings
        ]
        self.keymap = updated_keymap
        self.settings.applied_recommended_updates = sorted(already | newly)
        try:
            save_keymap(self.keymap)
            _save_settings(self.settings)
        except OSError:
            # Best-effort: a locked/read-only data dir must not break startup;
            # the update is in memory and will retry on the next launch.
            self._report_startup_task_failure("recommended updates")

    def _surface_migration_notice(self) -> None:
        """Tell the user, once, that QUILL migrated their settings/shortcuts.

        Gated by the ``migration_notice`` setting (silent / announce / prompt).
        A backup was already taken during the migration regardless of this
        choice; "prompt" additionally offers a one-click Undo of any recommended
        shortcut change.
        """
        from quill.core.migration_backup import pop_recent_migrations
        from quill.core.settings_migration import pop_retired_settings_keys

        migrated_stores = pop_recent_migrations()
        retired_keys = pop_retired_settings_keys()
        if retired_keys:
            # The QuillRichEdit promotion: old surface overrides were dropped on
            # load; write the cleaned delta back so the file matches what loaded.
            save_settings(self.settings)
        shortcut_summaries = list(getattr(self, "_recommended_update_summaries", []))
        if not migrated_stores and not shortcut_summaries and not retired_keys:
            return
        mode = getattr(self.settings, "migration_notice", "announce")
        if mode == "silent":
            return
        parts: list[str] = []
        if migrated_stores:
            parts.append("QUILL updated your saved settings for this version. A backup was saved.")
        if retired_keys:
            parts.append(
                "Your editor settings were simplified; the braille fix is now on "
                "by default under Preferences > Braille."
            )
        parts.extend(shortcut_summaries)
        message = " ".join(parts)
        can_undo = bool(getattr(self, "_recommended_update_undo", None))
        if mode == "prompt":
            self._prompt_migration_summary(message, can_undo=can_undo)
        else:  # "announce"
            self._announce_result(message)

    def _prompt_migration_summary(self, message: str, *, can_undo: bool) -> None:
        wx = self._wx
        if can_undo:
            dialog = wx.MessageDialog(
                self.frame,
                message + "\n\nUndo the shortcut change?",
                "QUILL Updated",
                wx.YES_NO | wx.ICON_INFORMATION,
            )
            dialog.SetYesNoLabels("Undo shortcut change", "Keep")
            apply_modal_ids(dialog, affirmative_id=wx.ID_YES, escape_id=wx.ID_NO)
            result = self._show_modal_dialog(dialog, "QUILL Updated")
            dialog.Destroy()
            if result == wx.ID_YES:
                self.undo_recommended_keymap_updates()
            return
        dialog = wx.MessageDialog(self.frame, message, "QUILL Updated", wx.OK | wx.ICON_INFORMATION)
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_OK)
        self._show_modal_dialog(dialog, "QUILL Updated")
        dialog.Destroy()

    def undo_recommended_keymap_updates(self) -> None:
        """Restore the bindings a recommended update changed this launch.

        The update ids stay recorded as applied, so QUILL will not re-apply the
        change on the next launch -- the user's restored choice sticks.
        """
        undo = getattr(self, "_recommended_update_undo", None)
        if not undo:
            self._set_status("Nothing to undo")
            return
        for command_id, binding in undo.items():
            if binding:
                self.keymap[command_id] = binding
            else:
                self.keymap.pop(command_id, None)
        self._recommended_update_undo = {}
        self._recommended_update_summaries = []
        try:
            save_keymap(self.keymap)
        except OSError:
            pass
        self._reload_shortcuts_from_keymap()
        self._announce_result("Restored your previous keyboard shortcuts.")

    def reset_keymap_defaults(self) -> None:
        wx = self._wx
        result = self._show_message_box(
            "Reset all keybindings to defaults?",
            "Reset Keymap",
            wx.ICON_WARNING | wx.YES_NO | wx.NO_DEFAULT,
        )
        if result != wx.YES:
            self._set_status("Reset keymap cancelled")
            return
        self.keymap = reset_keymap()
        self._set_keyboard_pack(KEYBOARD_PACK_DEFAULT)
        self._reload_shortcuts_from_keymap()
        self._set_status("Reset keymap to defaults")

    def reset_all_to_factory_defaults(self) -> None:
        """Reset settings, shortcuts, menus, and the feature profile at once.

        One warning covers everything. Each subsystem is reset to the exact same
        factory state its own dedicated reset would produce, and persists. User
        documents, autosaves, backups, and recovery data are never touched.
        """
        wx = self._wx
        result = self._show_message_box(
            "Reset EVERYTHING to factory defaults?\n\n"
            "This resets all settings, keyboard shortcuts, menu customizations, "
            "and your feature profile to their originals. Your documents are not "
            "affected. This cannot be undone.",
            "Reset Everything to Factory Defaults",
            wx.ICON_WARNING | wx.YES_NO | wx.NO_DEFAULT,
        )
        if result != wx.YES:
            self._set_status("Reset everything cancelled")
            return
        from quill.core.settings_registry import reset_all as _reset_settings

        # Settings (persisted by _settings_dialog_apply_refresh below).
        self.settings = _reset_settings()
        # Keyboard shortcuts (reset_keymap persists the empty delta).
        self.keymap = reset_keymap()
        self._set_keyboard_pack(KEYBOARD_PACK_DEFAULT)
        # Menus: a fresh customization IS the factory layout (an empty delta).
        try:
            from quill.core.menu_customization import (
                MenuCustomization,
                save_menu_customization,
            )

            factory_menus = MenuCustomization()
            save_menu_customization(factory_menus)
            self._menu_customization = factory_menus
        except Exception:
            self._report_startup_task_failure("reset menu customization")
        # Feature profile back to the default (Essential), overrides cleared.
        try:
            self.features.reset_to_essential_profile()
        except Exception:
            self._report_startup_task_failure("reset feature profile")
        # Rebuild commands + menus from the restored keymap/menus, then persist
        # settings and refresh all settings-derived UI state.
        self._reload_shortcuts_from_keymap()
        self._settings_dialog_apply_refresh("Reset everything to factory defaults")

    def _reload_shortcuts_from_keymap(self) -> None:
        self.commands = CommandRegistry()
        self._build_commands()
        self._build_menu()
        self._apply_accelerators()
        self._reload_global_hotkeys()
