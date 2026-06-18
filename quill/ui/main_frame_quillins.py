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

import threading
from pathlib import Path
from typing import Any

from quill.core.quillins import (
    ExtensionManifest,
    SnippetContext,
    SnippetGalleryEntry,
    build_registry,
    expand_snippet,
)
from quill.core.quillins.host import ExtensionHost
from quill.core.quillins.loader import (
    discover_bundled_extensions,
    discover_extensions,
    install_extension,
    is_event_enabled,
    load_enabled_bundled_manifests,
    load_enabled_manifests,
    remove_extension,
    set_enabled,
    set_event_enabled,
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

    def _append_quillin_menu_items(
        self,
        menu: object,
        parent_title: str,
        *,
        prepend_separator: bool = True,
    ) -> None:
        """Append bundled/third-party Quillin commands whose menu home is ``parent_title``.

        This is what lets a Quillin's ``menus`` contribution land in its declared
        conventional home (Insert, Format, Search, ...) or in a conventional
        submenu (e.g. "Date and Time") instead of only the flat Tools > Quillins
        backstop list, so a converted built-in keeps the menu placement recorded
        in ``menus.md``. Each item is bound to run through the same
        capability/consent-gated path as any other Quillin command.

        ``prepend_separator`` defaults to True and prepends a separator before
        the first appended item — which is what the top-level callers want
        (a Quillin block visually separate from the host's own items). Submenu
        callers pass ``prepend_separator=False`` so the first item lands at the
        top of the submenu without a leading separator.
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
                if prepend_separator:
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
        # quillin_id -> (manifest, directory) for Quillins with document_events.
        self._quillin_event_index: dict[str, tuple[ExtensionManifest, Path]] = {}
        # extension (".csv") -> [(manifest, directory, handler_name)] for file_types.
        self._quillin_file_type_index: dict[str, list[tuple[ExtensionManifest, Path, str]]] = {}
        # quillin_id -> list of live wx.Timer objects (Part 1 schedule).
        self._quillin_timers: dict[str, list[Any]] = {}
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

        # Stop any timers from a previous load before rebuilding the indices, so
        # a reload/disable never leaves an orphaned wx.Timer firing.
        for quillin_id in list(getattr(self, "_quillin_timers", {})):
            self._stop_quillin_timers(quillin_id)

        self._quillin_index = {}
        self._bundled_command_ids = set()
        self._quillin_registry = None
        self._quillin_event_index = {}
        self._quillin_file_type_index = {}
        self._quillin_timers = {}

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
                # Index document-event subscriptions for runtime dispatch.
                if manifest.contributes.document_events:
                    self._quillin_event_index[manifest.id] = (manifest, entry.directory)
                # Index file-type handlers by extension for open-time dispatch.
                for file_type in manifest.contributes.file_types:
                    for extension in file_type.extensions:
                        self._quillin_file_type_index.setdefault(extension, []).append((
                            manifest,
                            entry.directory,
                            file_type.handler,
                        ))
                # Start background timers (skipped in Safe Mode).
                if manifest.contributes.schedule and not self._safe_mode:
                    self._start_quillin_timers(manifest, entry.directory)

        # Fire quillin.enabled for any Quillin that subscribes to it, so live
        # lifecycle events match the contract (Journal Stamp / Status Scribe).
        for quillin_id, (manifest, directory) in self._quillin_event_index.items():
            for entry_dict in manifest.contributes.document_events:
                if not isinstance(entry_dict, dict):
                    continue
                if entry_dict.get("event") != "quillin.enabled":
                    continue
                self._fire_quillin_lifecycle_event(
                    "quillin.enabled", quillin_id, manifest, directory
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

    # -- document/timer event dispatch (Part 0/1/2) --------------------------
    def fire_quillin_event(self, event_name: str, context: dict) -> None:
        """Fire ``event_name`` to all subscribed Quillins. Non-blocking.

        Each matched handler runs in its own daemon thread so a slow or faulty
        Quillin can never block the editor. Honours per-event enable state and
        the optional ``filter_extensions`` guard.
        """

        index = getattr(self, "_quillin_event_index", None)
        if not index:
            return
        for quillin_id, (manifest, directory) in list(index.items()):
            for entry in manifest.contributes.document_events:
                if not isinstance(entry, dict):
                    continue
                if entry.get("event") != event_name:
                    continue
                handler = entry.get("handler")
                if not isinstance(handler, str) or not handler:
                    continue
                if not is_event_enabled(quillin_id, event_name):
                    continue
                filter_extensions = entry.get("filter_extensions")
                if isinstance(filter_extensions, list) and filter_extensions:
                    if context.get("extension", "") not in filter_extensions:
                        continue
                self._run_quillin_event_handler_async(manifest, directory, handler, context)

    def _fire_quillin_lifecycle_event(
        self,
        event_name: str,
        quillin_id: str,
        manifest: ExtensionManifest,
        directory: Path,
    ) -> None:
        """Fire a single Quillin-lifecycle event (e.g. quillin.enabled) to one Quillin."""

        for entry in manifest.contributes.document_events:
            if not isinstance(entry, dict):
                continue
            if entry.get("event") != event_name:
                continue
            handler = entry.get("handler")
            if not isinstance(handler, str) or not handler:
                continue
            if not is_event_enabled(quillin_id, event_name):
                continue
            self._run_quillin_event_handler_async(manifest, directory, handler, {})

    def _run_quillin_event_handler_async(
        self, manifest: ExtensionManifest, directory: Path, handler_name: str, context: dict
    ) -> None:
        """Invoke a Quillin event handler in a daemon thread.

        Storage is acquired before the thread starts (the dict is shared, but
        the thread only reads/writes its own string-valued entries, which is
        safe). Errors are marshalled back onto the UI thread.
        """

        if not hasattr(self, "_quillin_storage_data"):
            self._quillin_storage_data = {}
        storage = self._quillin_storage_data.setdefault(manifest.id, {})
        wx = self._wx

        def _worker() -> None:
            services = _EditorHostServices(self)
            host = ExtensionHost(
                manifest, directory, services, consent=self._quillin_consent, storage=storage
            )
            try:
                host.start()
                host.load()
                host.invoke_event(handler_name, dict(context))
            except Exception as error:  # never crash; report on the UI thread
                call_after = getattr(wx, "CallAfter", None)
                if callable(call_after):
                    call_after(self._set_status, f"Quillin event error: {error}")
            finally:
                host.close()

        thread = threading.Thread(  # GATE-40-OK: ad-hoc one-shot Quillin event/timer dispatch
            target=_worker, daemon=True
        )
        # A daemon thread is required so a slow out-of-process worker never blocks
        # the UI; no cancellation is needed because the worker is killed when its
        # ExtensionHost closes and the thread is daemonic (abandoned on shutdown).
        thread.start()

    def fire_quillin_file_type_event(self, path: Path) -> None:
        """Fire registered file-type handlers for ``path`` (a specialized open)."""

        index = getattr(self, "_quillin_file_type_index", None)
        if not index:
            return
        extension = path.suffix.lower()
        handlers = index.get(extension)
        if not handlers:
            return
        context = {
            "file_path": str(path),
            "extension": extension,
            "filename": path.name,
        }
        for manifest, directory, handler_name in list(handlers):
            self._run_quillin_event_handler_async(manifest, directory, handler_name, context)

    # -- background timers (Part 1) ------------------------------------------
    def _start_quillin_timers(self, manifest: ExtensionManifest, directory: Path) -> None:
        """Create and start one wx.Timer per schedule entry for this Quillin."""

        wx = self._wx
        timer_cls = getattr(wx, "Timer", None)
        if timer_cls is None:
            return
        timers: list[Any] = []
        for sched in manifest.contributes.schedule:
            timer = timer_cls(self.frame)
            self.frame.Bind(
                wx.EVT_TIMER,
                lambda _e, m=manifest, d=directory, s=sched: self._on_quillin_timer(m, d, s),
                timer,
            )
            timer.Start(int(sched.interval_seconds) * 1000)
            timers.append(timer)
        if timers:
            self._quillin_timers[manifest.id] = timers

    def _stop_quillin_timers(self, quillin_id: str) -> None:
        """Stop and forget all timers for a Quillin (disable/remove/reload)."""

        timers = self._quillin_timers.pop(quillin_id, [])
        for timer in timers:
            stop = getattr(timer, "Stop", None)
            if callable(stop):
                stop()

    def _on_quillin_timer(self, manifest: ExtensionManifest, directory: Path, sched: Any) -> None:
        """A schedule timer fired: run its handler in a background thread."""

        context = {"timer_id": sched.id, "interval_seconds": sched.interval_seconds}
        self._run_quillin_event_handler_async(manifest, directory, sched.handler, context)

    # -- snippet gallery (Part 3) --------------------------------------------
    def collect_snippet_gallery(self) -> list[tuple[str, str, SnippetGalleryEntry]]:
        """Return [(quillin_name, quillin_id, entry)] for all gallery snippets."""

        result: list[tuple[str, str, SnippetGalleryEntry]] = []
        bundled = load_enabled_bundled_manifests(self.features)
        third_party = load_enabled_manifests(self.features)
        for manifest in [*bundled, *third_party]:
            for entry in manifest.contributes.snippet_gallery:
                result.append((manifest.name, manifest.id, entry))
        return result

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

    # -- Intent profile Quillin configuration --------------------------------
    def apply_intent_quillin_profile(
        self,
        intent_id: str,
        *,
        wants_ai: bool = False,
        wants_braille: bool = False,
        wants_automation: bool = False,
    ) -> None:
        """Enable/disable bundled Quillins to match the chosen intent profile.

        Called by ``run_startup_wizard`` after the dialog closes so that the
        full MainFrame context (quillin index, reload callback) is available.
        """
        from quill.core.onboarding_profiles import get_intent_profile

        intent = get_intent_profile(intent_id)
        quillins_on = set(intent.quillins_on)
        quillins_off = set(intent.quillins_off)

        # Apply extras that override the base profile
        if wants_ai:
            quillins_on.update({
                "com.quill.bundled.ai-writing-prompts",
                "com.quill.bundled.ai-writing-skills",
            })
            quillins_off.discard("com.quill.bundled.ai-writing-prompts")
            quillins_off.discard("com.quill.bundled.ai-writing-skills")
        if wants_automation:
            quillins_on.add("com.quill.smartinsert")
            quillins_off.discard("com.quill.smartinsert")
        if wants_braille:
            quillins_on.add("com.quill.brftools")
            quillins_off.discard("com.quill.brftools")

        for quillin_id in quillins_on:
            try:
                set_enabled(quillin_id, True)
            except Exception:
                pass
        for quillin_id in quillins_off:
            try:
                set_enabled(quillin_id, False)
            except Exception:
                pass

        # Reload contributions so menus and commands reflect new state
        try:
            self._register_quillin_contributions()
        except Exception:
            pass

    # -- Quillin preferences -------------------------------------------------
    def _pref_manifests(self) -> list[Any]:
        """Return enabled manifests that declare ``contributes.preferences``."""
        return [
            item.manifest
            for item in self._installed_quillins()
            if item.manifest is not None and item.manifest.contributes.preferences
        ]

    def open_quillin_preferences(self, manifest: Any) -> None:
        from quill.ui.quillin_prefs_dialog import build_quillin_pref_dialog

        build_quillin_pref_dialog(self.frame, manifest, announce_fn=self._announce)

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
        events_button = wx.Button(dialog, label="Configure &Events...")
        reload_button = wx.Button(dialog, label="&Reload")
        remove_button = wx.Button(dialog, label="Re&move...")
        install_button = wx.Button(dialog, label="&Install from Folder...")
        close_button = wx.Button(dialog, id=wx.ID_OK, label="&Close")

        actions = wx.BoxSizer(wx.HORIZONTAL)
        for button in (
            enable_button,
            disable_button,
            events_button,
            reload_button,
            remove_button,
            install_button,
        ):
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
            has_events = (
                has_item
                and item is not None
                and item.manifest is not None
                and bool(item.manifest.contributes.document_events)
            )
            events_button.Enable(has_events)
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

            from quill.ui.dialog_contract import show_message_box

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
                show_message_box(
                    f"Install failed: {exc}",
                    "Install Quillin",
                    wx.OK | wx.ICON_ERROR,
                    dialog,
                    announce=self._announce,
                )

        def on_configure_events(_event: object) -> None:
            item = selected_extension()
            if item is None or item.manifest is None:
                return
            doc_events = item.manifest.contributes.document_events
            if not doc_events:
                return
            self._open_event_toggle_dialog(dialog, item.id, doc_events)
            refresh_details()

        chooser.Bind(wx.EVT_LISTBOX, on_select)
        enable_button.Bind(wx.EVT_BUTTON, on_enable)
        disable_button.Bind(wx.EVT_BUTTON, on_disable)
        events_button.Bind(wx.EVT_BUTTON, on_configure_events)
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

    def _open_event_toggle_dialog(
        self, parent: Any, extension_id: str, doc_events: tuple[object, ...]
    ) -> None:
        """Show a dialog listing each document event with an on/off checkbox."""

        wx = self._wx
        edlg = wx.Dialog(
            parent,
            title=f"Configure Events — {extension_id}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        body = wx.BoxSizer(wx.VERTICAL)
        body.Add(
            wx.StaticText(
                edlg,
                label=(
                    "Check events you want active for this Quillin. "
                    "Uncheck to stop an event from firing."
                ),
            ),
            0,
            wx.ALL | wx.EXPAND,
            8,
        )

        checks: list[tuple[str, Any]] = []
        for entry in doc_events:
            if not isinstance(entry, dict):
                continue
            event_name = str(entry.get("event", ""))
            title = str(entry.get("title", event_name))
            desc = str(entry.get("description", ""))
            label = f"{title} ({event_name})"
            if desc:
                label += f"\n  {desc}"
            cb = wx.CheckBox(edlg, label=label)
            cb.SetName(f"event_{event_name}")
            cb.SetValue(is_event_enabled(extension_id, event_name))
            body.Add(cb, 0, wx.ALL | wx.EXPAND, 4)
            checks.append((event_name, cb))

        button_sizer = wx.StdDialogButtonSizer()
        ok_button = wx.Button(edlg, id=wx.ID_OK, label="&Save")
        cancel_button = wx.Button(edlg, id=wx.ID_CANCEL, label="&Cancel")
        button_sizer.AddButton(ok_button)
        button_sizer.AddButton(cancel_button)
        button_sizer.Realize()
        body.Add(button_sizer, 0, wx.EXPAND | wx.ALL, 8)

        edlg.SetSizerAndFit(body)
        if hasattr(edlg, "CentreOnParent"):
            edlg.CentreOnParent()

        from quill.ui.dialog_contract import apply_modal_ids

        apply_modal_ids(edlg, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        try:
            result = self._show_modal_dialog(edlg, f"Configure Events — {extension_id}")
        finally:
            if result == wx.ID_OK:
                for event_name, cb in checks:
                    set_event_enabled(extension_id, event_name, bool(cb.GetValue()))
            edlg.Destroy()

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
            if manifest.categories:
                lines.append(f"Categories: {', '.join(manifest.categories)}")
            if manifest.min_quill_version:
                lines.append(f"Min QUILL version: {manifest.min_quill_version}")
            caps = ", ".join(manifest.capabilities) if manifest.capabilities else "(none)"
            lines.append(f"Capabilities: {caps}")
            if manifest.net_allowed_hosts:
                lines.append(f"Net allowed hosts: {', '.join(manifest.net_allowed_hosts)}")
            lines.append(f"Type: {'Python handler' if manifest.is_layer_two else 'snippet only'}")
            command_ids = ", ".join(c.id for c in manifest.contributes.commands) or "(none)"
            lines.append(f"Commands: {command_ids}")
            doc_events = manifest.contributes.document_events
            if doc_events:
                lines.append("Events:")
                for evt in doc_events:
                    if not isinstance(evt, dict):
                        continue
                    event_name = str(evt.get("event", ""))
                    title = str(evt.get("title", event_name))
                    active = is_event_enabled(item.id, event_name)
                    lines.append(f"  {title} ({event_name}): {'on' if active else 'off'}")
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
