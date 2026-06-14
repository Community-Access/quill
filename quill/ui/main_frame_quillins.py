"""Quillins surfaces for :class:`MainFrame`: command, menu, runtime, Manager.

This mixin wires the Quillins framework (``quill.core.quillins``) into the
accessible UI:

* registers the ``tools.quillins_manager`` command (palette + Keymap Editor; no
  default binding, opened via the Tools menu);
* builds the **Quillins Manager** dialog — a hardened ``wx.Dialog`` of stock
  controls that lists installed Quillins, shows manifest/capability detail, and
  offers Enable/Disable, Reload, and Remove;
* always loads **bundled** Quillins (Tier C) behind the on-by-default
  ``core.bundled_quillins`` flag, and — when the SEC-8
  ``core.third_party_plugins`` flag is enabled — also loads enabled third-party
  manifests; both register their ``ext.*`` commands and run them — snippet
  commands inline, handler commands through the out-of-process host with a
  capability + consent gate.

SEC-8 (non-negotiable for 1.0): the third-party flag is ``locked_off``, so a
shipping build discovers and runs nothing third-party. Bundled Quillins are a
separate, trusted-author install-tree tier and run regardless. The Manager still
opens and is fully operable; it reports that third-party Quillins are disabled
while bundled Quillins remain listed and runnable. The third-party live runtime
paths below are reachable only when the flag is forced on (tests).

``core``/``io`` stay wx-free; this UI module owns all ``wx`` use, marshalling
editor effects on the UI thread per the host services contract.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.quillins import (
    ExtensionManifest,
    SnippetContext,
    build_registry,
    expand_snippet,
)
from quill.core.quillins.host import ExtensionHost
from quill.core.quillins.loader import (
    discover_bundled_extensions,
    discover_extensions,
    install_extension,
    load_enabled_bundled_manifests,
    load_enabled_manifests,
    remove_extension,
    set_enabled,
)
from quill.core.quillins.registry import ContributionRegistry
from quill.plugins import THIRD_PARTY_PLUGINS_FEATURE
from quill.ui.main_frame_quillins_host import _EditorHostServices

_QUILLINS_MANAGER_COMMAND = "tools.quillins_manager"
_QUILLINS_WIZARD_COMMAND = "tools.quillin_wizard"


class QuillinsMenuMixin:
    """Command, menu, runtime, and Manager wiring for Quillins."""

    # -- menu ----------------------------------------------------------------
    def _build_quillins_menu(self) -> object:
        """Build the Tools > Quillins submenu and bind every item.

        The New Quillin and Manager items are always present. When the SEC-8 flag
        is enabled, every contributed ``ext.*`` command is also listed here so it
        is reachable by keyboard even before per-menu placement; labels show any
        user binding via ``_menu_label``.
        """

        wx = self._wx
        menu = wx.Menu()

        wizard_id = wx.NewIdRef()
        menu.Append(
            wizard_id,
            self._menu_label("&New Quillin...", _QUILLINS_WIZARD_COMMAND),
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_quillin_wizard(), id=wizard_id)

        manager_id = wx.NewIdRef()
        menu.Append(
            manager_id,
            self._menu_label("&Manage Quillins...", _QUILLINS_MANAGER_COMMAND),
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_quillins_manager(), id=manager_id)

        registry = self._quillin_registry
        if registry is not None and registry.commands:
            menu.AppendSeparator()
            for command_id, resolved in sorted(registry.commands.items()):
                item_id = wx.NewIdRef()
                menu.Append(item_id, self._menu_label(resolved.command.title, command_id))
                self.frame.Bind(
                    wx.EVT_MENU,
                    lambda _e, cid=command_id: self.run_quillin_command(cid),
                    id=item_id,
                )
        return menu

    def _append_quillin_menu_items(self, menu: object, parent_title: str) -> None:
        """Append bundled/third-party Quillin commands whose menu home is ``parent_title``.

        This is what lets a Quillin's ``menus`` contribution land in its declared
        conventional home (Insert, Format, Search, ...) instead of only the flat
        Tools > Quillins backstop list, so a converted built-in keeps the menu
        placement recorded in ``menus.md``. Each item is bound to run through the
        same capability/consent-gated path as any other Quillin command.
        """

        registry = getattr(self, "_quillin_registry", None)
        if registry is None:
            return
        wx = self._wx
        appended = False
        for contribution in registry.menus:
            if contribution.parent != parent_title:
                continue
            resolved = registry.commands.get(contribution.command_id)
            if resolved is None:
                continue
            if not appended:
                menu.AppendSeparator()
                appended = True
            item_id = wx.NewIdRef()
            menu.Append(item_id, self._menu_label(resolved.command.title, contribution.command_id))
            self.frame.Bind(
                wx.EVT_MENU,
                lambda _e, cid=contribution.command_id: self.run_quillin_command(cid),
                id=item_id,
            )

    # -- command + runtime registration --------------------------------------
    def _register_quillins_commands(self) -> None:
        self.commands.register(
            _QUILLINS_WIZARD_COMMAND,
            "New Quillin",
            self.open_quillin_wizard,
            self._binding_for(_QUILLINS_WIZARD_COMMAND),
        )
        self.commands.register(
            _QUILLINS_MANAGER_COMMAND,
            "Manage Quillins",
            self.open_quillins_manager,
            self._binding_for(_QUILLINS_MANAGER_COMMAND),
        )
        self._quillin_index: dict[str, tuple[ExtensionManifest, Path]] = {}
        self._bundled_command_ids: set[str] = set()
        self._quillin_registry: ContributionRegistry | None = None
        # H-SAFE-1: when Safe Mode is on, we register the *manager* and
        # *wizard* commands (the local surface) but skip the contribution
        # registration entirely. This is the load-bearing gate that makes
        # ``--safe-mode`` actually safe — without it the banner was a lie
        # and bundled/third-party commands stayed live.
        if self._safe_mode:
            return
        self._register_quillin_contributions()

    def _quillins_enabled(self) -> bool:
        is_enabled = getattr(self.features, "is_enabled", None)
        if not callable(is_enabled):
            return False
        return bool(is_enabled(THIRD_PARTY_PLUGINS_FEATURE))

    def _installed_quillins(self) -> list[Any]:
        """All discovered Quillins: bundled (Tier C) first, then third-party.

        Bundled Quillins ship enabled and are independent of the SEC-8
        third-party lock; third-party entries appear only when that flag is on.
        """

        installed = list(discover_bundled_extensions(self.features))
        installed.extend(discover_extensions(self.features))
        return installed

    def _register_quillin_contributions(self) -> None:
        """Load enabled Quillins and register their commands.

        Bundled Quillins (Tier C) are always loaded behind the on-by-default
        ``core.bundled_quillins`` flag; third-party Quillins are loaded only when
        the SEC-8 ``core.third_party_plugins`` flag is enabled. Both feed the one
        shared registry so their ids collide-detect uniformly.
        """

        self._quillin_index = {}
        self._bundled_command_ids = set()
        self._quillin_registry = None

        installed = {item.id: item for item in self._installed_quillins()}
        bundled_manifests = load_enabled_bundled_manifests(self.features)
        third_party_manifests = load_enabled_manifests(self.features)
        manifests = [*bundled_manifests, *third_party_manifests]
        if not manifests:
            return

        registry = build_registry(manifests, host_keymap=self.keymap)
        self._quillin_registry = registry

        bundled_ids = {manifest.id for manifest in bundled_manifests}
        for manifest in manifests:
            entry = installed.get(manifest.id)
            if entry is not None:
                for command in manifest.contributes.commands:
                    self._quillin_index[command.id] = (manifest, entry.directory)
                    if manifest.id in bundled_ids:
                        self._bundled_command_ids.add(command.id)
                if manifest.contributes.sound_pack:
                    from quill.ui import sound_manager

                    sound_manager.register_quillin_sounds(
                        manifest.id,
                        entry.directory,
                        manifest.contributes.sound_pack,
                        manifest.contributes.sound_events,
                    )

        for command_id, resolved in registry.commands.items():
            binding = next(
                (h.binding for h in registry.hotkeys if h.command_id == command_id), None
            )
            try:
                self.commands.register(
                    command_id,
                    resolved.command.title,
                    lambda cid=command_id: self.run_quillin_command(cid),
                    binding,
                )
            except ValueError:
                # A duplicate id (already registered) must never crash startup.
                continue

    # -- execution -----------------------------------------------------------
    def run_quillin_command(self, command_id: str) -> None:
        """Run a contributed command: snippet inline, handler out-of-process.

        Bundled (Tier C) commands run whenever they are registered; third-party
        commands additionally require the SEC-8 flag to still be on.
        """

        entry = self._quillin_index.get(command_id)
        if entry is None:
            self._announce("Quillin command is unavailable.")
            return
        if command_id not in self._bundled_command_ids and not self._quillins_enabled():
            self._announce("Third-party Quillins are disabled in this build.")
            return
        manifest, directory = entry
        command = next((c for c in manifest.contributes.commands if c.id == command_id), None)
        if command is None:
            return
        if command.is_snippet and command.snippet is not None:
            self._run_quillin_snippet(command.snippet)
            return
        self._run_quillin_handler(manifest, directory, command_id)

    def _run_quillin_snippet(self, body: str) -> None:
        editor = self._frame_editor()
        text = str(editor.GetValue())
        pos = int(editor.GetInsertionPoint())
        context = SnippetContext(
            selection=str(editor.GetStringSelection()),
            clipboard=str(self._read_clipboard_text()),
            filename=self._current_filename(),
            title=self._current_document_title(),
            line_number=str(text.count("\n", 0, pos) + 1),
            word_at_cursor=self._word_at_offset(text, pos),
        )
        expansion = expand_snippet(body, context)
        start, end = editor.GetSelection()
        if start == end:
            editor.WriteText(expansion.text)
        else:
            editor.Replace(start, end, expansion.text)
        self._announce("Quillin snippet inserted.")

    def _run_quillin_handler(
        self, manifest: ExtensionManifest, directory: Path, command_id: str
    ) -> None:
        if not hasattr(self, "_quillin_storage_data"):
            self._quillin_storage_data: dict[str, dict[str, str]] = {}
        storage = self._quillin_storage_data.setdefault(manifest.id, {})
        services = _EditorHostServices(self)
        host = ExtensionHost(
            manifest, directory, services, consent=self._quillin_consent, storage=storage
        )
        try:
            host.start()
            host.load()
            host.invoke(command_id, {})
        except Exception as error:  # surface, never crash the editor
            self._announce(f"Quillin error: {error}")
        finally:
            host.close()

    def _quillin_consent(self, capability: str, detail: str) -> bool:
        wx = self._wx
        from quill.ui.dialog_contract import apply_modal_ids  # local import to avoid cycles

        message = (
            f"A Quillin is requesting the '{capability}' capability for:\n\n{detail}\n\n"
            "Allow this action?"
        )
        dialog = wx.MessageDialog(
            self.frame,
            message,
            "Quillin Permission Request",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
        )
        # H-3-ui: route through the shared modal helper so the region
        # tracker, screen-reader entry/exit announcement, and editor
        # focus return on close are all applied. The consent dialog
        # is the most privacy-sensitive surface in the product, so
        # skipping the contract here is a regression.
        apply_modal_ids(dialog, affirmative_id=wx.ID_YES, escape_id=wx.ID_YES)
        try:
            return bool(self._show_modal_dialog(dialog, "Quillin Permission Request") == wx.ID_YES)
        finally:
            dialog.Destroy()

    # -- Quillin Wizard (in-app manifest builder) ----------------------------
    def open_quillin_wizard(self) -> None:
        from quill.ui.quillin_wizard import open_quillin_wizard

        open_quillin_wizard(
            self.frame,
            self._wx,
            announce=self._announce,
            show_modal=self._show_modal_dialog,
            reload_callback=self._register_quillin_contributions,
            third_party_locked=not self._quillins_enabled(),
        )

    # -- Quillins Manager dialog (hardened custom) ---------------------------
    def open_quillins_manager(self) -> None:
        wx = self._wx
        launcher = self.frame.FindFocus() if hasattr(self.frame, "FindFocus") else None

        installed = self._installed_quillins()
        dialog = wx.Dialog(
            self.frame,
            title="Quillins Manager",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        body = wx.BoxSizer(wx.VERTICAL)

        if self._quillins_enabled():
            intro_text = (
                "Installed Quillins. Choose one to read its details, then Enable, "
                "Disable, Reload, or Remove it."
            )
        else:
            intro_text = (
                "Bundled Quillins ship enabled and run normally. Third-party "
                "Quillins are disabled in this build and are listed for review "
                "only. Choose a Quillin to read its details."
            )
        body.Add(wx.StaticText(dialog, label=intro_text), 0, wx.ALL | wx.EXPAND, 8)

        labels = [self._quillin_list_label(item) for item in installed] or [
            "(no Quillins installed)"
        ]
        chooser = wx.ListBox(dialog, choices=labels)
        chooser.SetName("Installed Quillins")
        if installed:
            chooser.SetSelection(0)
        body.Add(chooser, 1, wx.ALL | wx.EXPAND, 8)

        body.Add(wx.StaticText(dialog, label="&Details"), 0, wx.LEFT | wx.RIGHT, 8)
        details = wx.TextCtrl(dialog, style=wx.TE_MULTILINE | wx.TE_READONLY)
        details.SetName("Quillin details")
        body.Add(details, 1, wx.ALL | wx.EXPAND, 8)

        enable_button = wx.Button(dialog, label="&Enable")
        disable_button = wx.Button(dialog, label="&Disable")
        reload_button = wx.Button(dialog, label="&Reload")
        remove_button = wx.Button(dialog, label="Re&move...")
        install_button = wx.Button(dialog, label="&Install from Folder...")
        close_button = wx.Button(dialog, id=wx.ID_OK, label="&Close")

        actions = wx.BoxSizer(wx.HORIZONTAL)
        for button in (enable_button, disable_button, reload_button, remove_button, install_button):
            actions.Add(button, 0, wx.RIGHT, 6)
        body.Add(actions, 0, wx.ALL, 8)

        button_sizer = wx.StdDialogButtonSizer()
        button_sizer.AddButton(close_button)
        button_sizer.Realize()
        body.Add(button_sizer, 0, wx.EXPAND | wx.ALL, 8)

        dialog.SetSizerAndFit(body)
        dialog.SetSize((640, 560))
        if hasattr(dialog, "CentreOnParent"):
            dialog.CentreOnParent()

        def selected_extension() -> object | None:
            index = chooser.GetSelection()
            if not installed or index < 0 or index >= len(installed):
                return None
            return installed[index]

        def refresh_details() -> None:
            item = selected_extension()
            details.SetValue(self._quillin_detail_text(item))
            has_item = item is not None
            enable_button.Enable(has_item and self._quillins_enabled())
            disable_button.Enable(has_item and self._quillins_enabled())
            reload_button.Enable(has_item)
            remove_button.Enable(has_item)

        def on_select(_event: object) -> None:
            refresh_details()

        def on_enable(_event: object) -> None:
            item = selected_extension()
            if item is None:
                return
            set_enabled(item.id, True)
            self._register_quillin_contributions()
            self._announce(f"Enabled {item.id}.")
            refresh_details()

        def on_disable(_event: object) -> None:
            item = selected_extension()
            if item is None:
                return
            set_enabled(item.id, False)
            self._register_quillin_contributions()
            self._announce(f"Disabled {item.id}.")
            refresh_details()

        def on_reload(_event: object) -> None:
            self._register_quillin_contributions()
            self._announce("Reloaded Quillins from disk.")

        def on_remove(_event: object) -> None:
            item = selected_extension()
            if item is None:
                return
            # Stock wx.MessageDialog synthesizes its own ID_YES / ID_NO
            # buttons at runtime from the YES_NO style flag. The static
            # dialog_button_contract audit cannot see those synthetic
            # buttons, so we mark this call as audited-out via the
            # ``# noqa: dialog_button_contract`` pragma on the next
            # line; the dialog is keyboard-operable end to end because
            # the message dialog's ID_YES / ID_NO buttons are wired
            # automatically. See WCAG 2.1.2 (#124).
            # H-4-ui: route through the shared modal helper so the
            # region tracker, screen-reader entry/exit announcement,
            # and editor focus return on close are all applied.
            # Direct ShowModal() would skip those for this destructive
            # confirm — exactly the bug the dialog contract prevents.
            from quill.ui.dialog_contract import apply_modal_ids

            confirm = wx.MessageDialog(
                dialog,
                f"Remove the Quillin '{item.id}'? This deletes it from disk.",
                "Remove Quillin",
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
            )
            apply_modal_ids(confirm, affirmative_id=wx.ID_YES, escape_id=wx.ID_NO)  # noqa: dialog_button_contract
            try:
                approved = self._show_modal_dialog(confirm, "Remove Quillin") == wx.ID_YES
            finally:
                confirm.Destroy()
            if approved:
                remove_extension(item.id)
                self._register_quillin_contributions()
                self._announce(f"Removed {item.id}.")

        def on_install(_event: object) -> None:
            with wx.DirDialog(
                dialog,
                "Select a Quillin folder to install",
                style=wx.DD_DEFAULT_STYLE,
            ) as ddlg:
                if self._show_modal_dialog(ddlg, "Install Quillin") != wx.ID_OK:
                    return
                src_path = ddlg.GetPath()
            from pathlib import Path

            try:
                ext_id = install_extension(Path(src_path))
                self._register_quillin_contributions()
                installed[:] = list(self._installed_quillins())
                labels = [self._quillin_list_label(item) for item in installed] or [
                    "(no Quillins installed)"
                ]
                chooser.Set(labels)
                if installed:
                    chooser.SetSelection(0)
                refresh_details()
                self._announce(f"Installed {ext_id}.")
            except Exception as exc:
                from quill.ui.dialog_contract import show_message_box

                show_message_box(
                    f"Install failed: {exc}",
                    "Install Quillin",
                    wx.OK | wx.ICON_ERROR,
                    dialog,
                )

        chooser.Bind(wx.EVT_LISTBOX, on_select)
        enable_button.Bind(wx.EVT_BUTTON, on_enable)
        disable_button.Bind(wx.EVT_BUTTON, on_disable)
        reload_button.Bind(wx.EVT_BUTTON, on_reload)
        remove_button.Bind(wx.EVT_BUTTON, on_remove)
        install_button.Bind(wx.EVT_BUTTON, on_install)

        close_button.SetDefault()
        from quill.ui.dialog_contract import apply_modal_ids

        # Use ID_OK (the close button) as the escape id so Escape closes the
        # manager without triggering any of the action buttons (Enable /
        # Disable / Reload / Remove), matching the "no destructive
        # consequence" pattern from the Quillin consent dialog.
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_OK)
        refresh_details()

        call_after = getattr(wx, "CallAfter", None)
        if callable(call_after):
            call_after(chooser.SetFocus)
        else:
            chooser.SetFocus()

        try:
            self._show_modal_dialog(dialog, "Quillins Manager")
        finally:
            dialog.Destroy()
            if launcher is not None and hasattr(launcher, "SetFocus"):
                launcher.SetFocus()

    # -- helpers -------------------------------------------------------------
    def _frame_editor(self) -> Any:
        return self.editor

    def _current_filename(self) -> str:
        document = getattr(self, "document", None)
        path = getattr(document, "path", None)
        if path is None:
            return ""
        return Path(str(path)).name

    def _current_document_title(self) -> str:
        document = getattr(self, "document", None)
        path = getattr(document, "path", None)
        if path is None:
            return ""
        return Path(str(path)).stem

    @staticmethod
    def _word_at_offset(text: str, pos: int) -> str:
        import re as _re

        before = _re.search(r"\w+$", text[:pos])
        after = _re.match(r"\w*", text[pos:])
        return (before.group(0) if before else "") + (after.group(0) if after else "")

    def _quillin_list_label(self, item: Any) -> str:
        name = item.manifest.name if item.manifest is not None else item.id
        if item.errors:
            state = "invalid"
        elif item.enabled:
            state = "enabled"
        else:
            state = "disabled"
        return f"{name} ({state})"

    def _quillin_detail_text(self, item: Any) -> str:
        if item is None:
            return "No Quillin selected."
        lines = [f"Id: {item.id}", f"Folder: {item.directory}"]
        if item.manifest is not None:
            manifest = item.manifest
            lines.append(f"Name: {manifest.name}")
            lines.append(f"Version: {manifest.version}")
            if manifest.author:
                lines.append(f"Author: {manifest.author}")
            if manifest.description:
                lines.append(f"Description: {manifest.description}")
            caps = ", ".join(manifest.capabilities) if manifest.capabilities else "(none)"
            lines.append(f"Capabilities: {caps}")
            lines.append(f"Type: {'Python handler' if manifest.is_layer_two else 'snippet only'}")
            command_ids = ", ".join(c.id for c in manifest.contributes.commands) or "(none)"
            lines.append(f"Commands: {command_ids}")
        lines.append(f"Enabled: {'yes' if item.enabled else 'no'}")
        if item.errors:
            lines.append("")
            lines.append("Problems:")
            lines.extend(f"  - {error}" for error in item.errors)
        return "\n".join(lines)

    def _read_clipboard_text(self) -> str:
        wx = self._wx
        text = ""
        clipboard = getattr(wx, "TheClipboard", None)
        if clipboard is None or not clipboard.Open():
            return text
        try:
            data = wx.TextDataObject()
            if clipboard.GetData(data):
                text = str(data.GetText())
        finally:
            clipboard.Close()
        return text

    def _write_clipboard_text(self, text: str) -> None:
        wx = self._wx
        clipboard = getattr(wx, "TheClipboard", None)
        if clipboard is None or not clipboard.Open():
            return
        try:
            clipboard.SetData(wx.TextDataObject(text))
        finally:
            clipboard.Close()
