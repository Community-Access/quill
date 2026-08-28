"""Quillins surface for the standalone companion apps (Radio, Cast, ...).

``QuillinsAppMixin`` is the app-side counterpart of the editor's
``QuillinsMenuMixin``. Composed into a companion-app frame (which already mixes
in :class:`~quill.ui.app_shell.AppShellFrame`), it:

* builds the ``&Quillins`` menu (Manage Quillins... + every contributed command);
* owns a :class:`~quill.core.quillins.app_host.QuillinAppHost`, wired with the
  app-neutral :class:`~quill.ui.app_quillins_host._AppHostServices`, a consent
  dialog, and Safe-Mode gating (no contribution loads in Safe Mode);
* serves as the host's :class:`~quill.core.quillins.app_host.AppFrameAdapter`,
  registering contributed commands in ``self.commands`` and collecting the menu
  items;
* provides an accessible Quillins Manager (a ``ListBox`` + buttons through the
  shared modal contract -- no checkboxes in a wx list).

``core``/``io`` stay wx-free; this UI module owns the ``wx`` use and marshals
background-thread announcements onto the UI thread.
"""

from __future__ import annotations

from typing import Any

from quill.core.quillins.loader import remove_extension, set_enabled

_QUILLINS_MANAGER_COMMAND = "tools.quillins_manager"


class QuillinsAppMixin:
    """Menu, runtime, and Manager wiring for Quillins in a companion app."""

    # -- setup ---------------------------------------------------------------
    def _init_app_quillins(self, app_id: str) -> None:
        """Create the app host and load contributions (unless Safe Mode)."""

        from quill.core.quillins.app_host import QuillinAppHost
        from quill.ui.app_quillins_host import _AppHostServices

        # (command_id, title) pairs collected during load(), consumed by the menu.
        self._quillin_menu_items: list[tuple[str, str]] = []
        self._app_host = QuillinAppHost(
            app_id=app_id,
            services=_AppHostServices(self),
            consent=self._quillin_consent,
            frame_adapter=self,
            features=self.features,
            keymap=self.keymap,
            safe_mode=self._safe_mode,
        )
        # load() is a no-op in Safe Mode (the host's own choke point), so no
        # command is registered and no contributed provider is populated.
        self._app_host.load()

    # -- AppFrameAdapter protocol (called by QuillinAppHost) -----------------
    def register_command(
        self, command_id: str, title: str, handler: Any, binding: str | None
    ) -> None:
        # try_register never raises on a duplicate id, so a reload is safe.
        self.commands.try_register(command_id, title, handler, binding, feature_id="core.app")

    def add_menu_command(self, command_id: str, title: str) -> None:
        self._quillin_menu_items.append((command_id, title))

    def announce(self, message: str) -> None:
        # Reached from background event/timer threads too, so marshal to the UI.
        call_after = getattr(self._wx, "CallAfter", None)
        if callable(call_after):
            call_after(self._announce, message)
        else:
            self._announce(message)

    # -- menu ----------------------------------------------------------------
    def _build_quillins_menu(self) -> Any:
        """Build the ``&Quillins`` menu: Manage Quillins... + contributed items."""

        wx = self._wx
        menu = wx.Menu()
        manage_id = wx.NewIdRef()
        menu.Append(manage_id, self._menu_label("&Manage Quillins...", _QUILLINS_MANAGER_COMMAND))
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_quillins_manager(), id=manage_id)
        ids: list[object] = [manage_id]

        items = getattr(self, "_quillin_menu_items", [])
        if items:
            menu.AppendSeparator()
            for command_id, title in items:
                item_id = wx.NewIdRef()
                menu.Append(item_id, self._menu_label(title, command_id))
                self.frame.Bind(
                    wx.EVT_MENU,
                    lambda _e, cid=command_id: self._app_host.run_command(cid),
                    id=item_id,
                )
                ids.append(item_id)
        self._keep_menu_ids(*ids)
        return menu

    # -- consent -------------------------------------------------------------
    def _quillin_consent(self, capability: str, detail: str) -> bool:
        wx = self._wx
        from quill.ui.dialog_contract import apply_modal_ids

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
        apply_modal_ids(  # dialog_button_contract: exempt
            dialog, affirmative_id=wx.ID_YES, escape_id=wx.ID_YES
        )
        try:
            return bool(self._show_modal_dialog(dialog, "Quillin Permission Request") == wx.ID_YES)
        finally:
            dialog.Destroy()

    # -- Manager dialog ------------------------------------------------------
    def open_quillins_manager(self) -> None:
        wx = self._wx
        from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name

        launcher = self.frame.FindFocus() if hasattr(self.frame, "FindFocus") else None
        installed = self._app_host.installed()
        third_party_on = self._quillins_third_party_enabled()

        dialog = wx.Dialog(
            self.frame,
            title="Quillins Manager",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        body = wx.BoxSizer(wx.VERTICAL)
        if third_party_on:
            intro = (
                "Installed Quillins for this app. Choose one to read its details, "
                "then Enable, Disable, Reload, or Remove it."
            )
        else:
            intro = (
                "Bundled Quillins ship enabled and run normally. Third-party "
                "Quillins are disabled in this build and are listed for review "
                "only. Choose a Quillin to read its details."
            )
        body.Add(wx.StaticText(dialog, label=intro), 0, wx.ALL | wx.EXPAND, 8)

        labels = [self._quillin_list_label(item) for item in installed] or [
            "(no Quillins installed)"
        ]
        chooser = wx.ListBox(dialog, choices=labels)
        set_accessible_name(chooser, "Installed Quillins")
        if installed:
            chooser.SetSelection(0)
        body.Add(chooser, 1, wx.ALL | wx.EXPAND, 8)

        body.Add(wx.StaticText(dialog, label="De&tails"), 0, wx.LEFT | wx.RIGHT, 8)
        details = wx.TextCtrl(dialog, style=wx.TE_MULTILINE | wx.TE_READONLY)
        set_accessible_name(details, "Quillin details")
        body.Add(details, 1, wx.ALL | wx.EXPAND, 8)

        enable_button = wx.Button(dialog, label="&Enable")
        disable_button = wx.Button(dialog, label="&Disable")
        reload_button = wx.Button(dialog, label="&Reload")
        remove_button = wx.Button(dialog, label="Re&move...")
        close_button = wx.Button(dialog, id=wx.ID_OK, label="&Close")

        actions = wx.BoxSizer(wx.HORIZONTAL)
        for button in (enable_button, disable_button, reload_button, remove_button):
            actions.Add(button, 0, wx.RIGHT, 6)
        body.Add(actions, 0, wx.ALL, 8)

        button_sizer = wx.StdDialogButtonSizer()
        button_sizer.AddButton(close_button)
        button_sizer.Realize()
        body.Add(button_sizer, 0, wx.EXPAND | wx.ALL, 8)

        dialog.SetSizerAndFit(body)
        dialog.SetSize((640, 520))
        if hasattr(dialog, "CentreOnParent"):
            dialog.CentreOnParent()

        def selected() -> object | None:
            index = chooser.GetSelection()
            if not installed or index < 0 or index >= len(installed):
                return None
            return installed[index]

        def refresh() -> None:
            item = selected()
            details.SetValue(self._quillin_detail_text(item))
            has_item = item is not None
            enable_button.Enable(has_item and third_party_on)
            disable_button.Enable(has_item and third_party_on)
            reload_button.Enable(has_item)
            remove_button.Enable(has_item and third_party_on)

        def reload_contributions() -> None:
            self._app_host.load()
            self._reload_quillins_menu()

        def on_enable(_e: object) -> None:
            item = selected()
            if item is None:
                return
            set_enabled(item.id, True)
            reload_contributions()
            self._announce(f"Enabled {item.id}.")
            refresh()

        def on_disable(_e: object) -> None:
            item = selected()
            if item is None:
                return
            set_enabled(item.id, False)
            reload_contributions()
            self._announce(f"Disabled {item.id}.")
            refresh()

        def on_reload(_e: object) -> None:
            reload_contributions()
            self._announce("Reloaded Quillins from disk.")

        def on_remove(_e: object) -> None:
            item = selected()
            if item is None:
                return
            confirm = wx.MessageDialog(
                dialog,
                f"Remove the Quillin '{item.id}'? This deletes it from disk.",
                "Remove Quillin",
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
            )
            apply_modal_ids(  # dialog_button_contract: exempt
                confirm, affirmative_id=wx.ID_YES, escape_id=wx.ID_NO
            )
            try:
                approved = self._show_modal_dialog(confirm, "Remove Quillin") == wx.ID_YES
            finally:
                confirm.Destroy()
            if approved:
                remove_extension(item.id)
                reload_contributions()
                self._announce(f"Removed {item.id}.")

        chooser.Bind(wx.EVT_LISTBOX, lambda _e: refresh())
        enable_button.Bind(wx.EVT_BUTTON, on_enable)
        disable_button.Bind(wx.EVT_BUTTON, on_disable)
        reload_button.Bind(wx.EVT_BUTTON, on_reload)
        remove_button.Bind(wx.EVT_BUTTON, on_remove)

        close_button.SetDefault()
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_OK)
        refresh()
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

    def _reload_quillins_menu(self) -> None:
        """Rebuild the menu bar so contributed items reflect the reload."""

        build = getattr(self, "_build_menu_bar", None)
        if callable(build):
            build()

    # -- helpers -------------------------------------------------------------
    def _quillins_third_party_enabled(self) -> bool:
        is_enabled = getattr(self.features, "is_enabled", None)
        if not callable(is_enabled):
            return False
        from quill.plugins import THIRD_PARTY_PLUGINS_FEATURE

        return bool(is_enabled(THIRD_PARTY_PLUGINS_FEATURE))

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
        manifest = item.manifest
        if manifest is not None:
            lines.append(f"Name: {manifest.name}")
            lines.append(f"Version: {manifest.version}")
            if manifest.author:
                lines.append(f"Author: {manifest.author}")
            if manifest.description:
                lines.append(f"Description: {manifest.description}")
            lines.append(f"Targets: {', '.join(manifest.target_apps)}")
            caps = ", ".join(manifest.capabilities) if manifest.capabilities else "(none)"
            lines.append(f"Capabilities: {caps}")
            command_ids = ", ".join(c.id for c in manifest.contributes.commands) or "(none)"
            lines.append(f"Commands: {command_ids}")
        lines.append(f"Enabled: {'yes' if item.enabled else 'no'}")
        if item.errors:
            lines.append("")
            lines.append("Problems:")
            lines.extend(f"  - {error}" for error in item.errors)
        return "\n".join(lines)
