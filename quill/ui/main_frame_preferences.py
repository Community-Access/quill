"""Preferences and settings dialogs for MainFrame (CQ-1 decomposition).

``PreferencesMixin`` owns the settings surface: the multi-page Preferences
hub, the spec-driven General Preferences dialog (including the experimental
gates wiring and the braille hide-border decision-time warning), GLOW
settings, AI connection preferences, the apply/refresh pass that re-runs UI
side effects after a settings change, the data-location restart flow with
relaunch, the data-migration notice, and the one-time legacy data import
offer. Extracted verbatim from ``main_frame.py``; runs on ``MainFrame``
(``self``). Model-lifecycle timers stay in ``main_frame.py``.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path

from quill.core.browser_preview import (
    available_browser_options,
    browser_choice_label_for_value,
    browser_choice_value_for_label,
)
from quill.core.features import (
    export_feature_profile_file,
    import_feature_profile_file,
)
from quill.core.paths import app_data_dir
from quill.core.settings import Settings, save_settings
from quill.ui.accessible_names import ensure_accessible_names
from quill.ui.dialog_contract import (
    apply_modal_ids,
    focus_primary_control,
    set_accessible_name,
)


class PreferencesMixin:
    def open_preferences(self) -> None:
        """Open the multi-page Preferences hub.

        A single book control hosts one page per settings area. The selector is
        a stock wx book widget so it is keyboard- and screen-reader-accessible
        by construction, with native first-letter type-ahead and arrow-key
        movement, and the first category is selected on open. The selector is a
        left-hand category list (``wx.Listbook``, Edge/Settings style) on every
        platform; macOS does not use ``wx.Toolbook`` because its Cocoa toolbar
        selector requires a per-page bitmap and segfaults without one. Moving
        across categories immediately swaps the content pane -- no intermediate
        "choose then press OK" step -- and each page opens its area with an
        explicit button.
        """
        wx = self._wx
        # (label, description, handler, feature_gate | None) per settings area.
        # Areas whose feature_gate is a disabled feature are hidden so the hub
        # only shows what is actually available in the current profile.
        _all_areas: list[tuple[str, str, Callable[[], None], str | None]] = [
            (
                "General",
                "Appearance, editing, autosave, updates, and the AI master switch.",
                self.open_general_preferences,
                None,
            ),
            (
                "Profiles and Features",
                "Turn optional features on or off and switch between feature profiles.",
                self.open_profiles_and_features_settings,
                None,
            ),
            (
                "Status Bar Layout",
                "Choose which fields appear in the status bar and their order.",
                self.open_status_bar_settings,
                None,
            ),
            (
                "Keymap Editor",
                "Review and change the keyboard shortcuts for every command.",
                self.open_keymap_editor,
                None,
            ),
            (
                "AI Connection",
                "Connect an AI provider, enter your key, and verify the connection.",
                self.open_ai_preferences,
                "future.ai",
            ),
            (
                "Watch Folder Automation",
                "Automate actions when files appear in a folder you watch.",
                self.open_watch_folder_settings,
                "core.watch_folder",
            ),
            (
                "GLOW Accessibility",
                "Quill's built-in accessibility engine and its optional network features.",
                self.open_glow_settings,
                "core.glow",
            ),
            (
                "Install Starter Snippet Packs",
                "Add a set of ready-made text snippets you can insert while writing.",
                self.install_starter_snippet_packs,
                "core.bundled_quillins",
            ),
        ]
        areas = [
            (label, desc, handler)
            for label, desc, handler, gate in _all_areas
            if gate is None or self._feature_enabled(gate)
        ]
        for _pref_m in self._pref_manifests():
            _page = _pref_m.contributes.preferences[0]
            if not isinstance(_page, dict):
                continue
            _title = _page.get("title") or _pref_m.name
            _desc = _page.get("description") or f"Settings for {_pref_m.name}."
            areas.append((
                _title,
                _desc,
                lambda _m=_pref_m: self.open_quillin_preferences(_m),
            ))
        # All platforms use a left-hand category list (wx.Listbook, Edge /
        # Windows Settings style). macOS deliberately does NOT use wx.Toolbook:
        # on Cocoa the Toolbook selector is a native wxToolBar that requires a
        # valid bitmap per tool, and AddPage() below passes no image, so wx
        # null-derefs in wxToolBarTool::UpdateImages() -> wxBitmap::UseAlpha()
        # and segfaults the instant Preferences opens (Cmd+,). Listbook needs no
        # bitmaps, so it keeps a single accessible, screen-reader-tested code
        # path on every platform. Do not restore the Toolbook without giving
        # every page a real wx.ImageList, or the macOS crash returns.
        # The handler chosen by the user; run after the hub closes so only one
        # modal is on screen at a time.
        chosen: dict[str, Callable[[], None] | None] = {"handler": None}

        with wx.Dialog(self.frame, title="Preferences") as dialog:
            outer = wx.BoxSizer(wx.VERTICAL)
            book = wx.Listbook(dialog, style=wx.BK_LEFT)
            book.SetName("Preferences categories")

            def _make_open(handler: Callable[[], None]) -> Callable[[object], None]:
                def _on_open(_event: object) -> None:
                    chosen["handler"] = handler
                    dialog.EndModal(wx.ID_OK)

                return _on_open

            for label, description, handler in areas:
                page = wx.Panel(book, style=wx.TAB_TRAVERSAL)
                page_sizer = wx.BoxSizer(wx.VERTICAL)
                heading = wx.StaticText(page, label=label)
                heading_font = heading.GetFont()
                heading_font.MakeBold()
                heading.SetFont(heading_font)
                page_sizer.Add(heading, 0, wx.ALL, 8)
                intro = wx.StaticText(page, label=description)
                intro.Wrap(420)
                page_sizer.Add(intro, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
                open_btn = wx.Button(page, label=f"&Open {label}...")
                open_btn.SetName(f"Open {label}")
                open_btn.Bind(wx.EVT_BUTTON, _make_open(handler))
                page_sizer.Add(open_btn, 0, wx.ALL, 8)
                page.SetSizer(page_sizer)
                book.AddPage(page, label)

            if book.GetPageCount() > 0:
                book.SetSelection(0)
            outer.Add(book, 1, wx.EXPAND | wx.ALL, 8)

            # Enter on a highlighted category opens it, so keyboard users do not
            # have to Tab to the page's Open button. When a button already holds
            # focus, let the keystroke fall through so it activates that button
            # (or the default Close button) as usual.
            def _on_char_hook(event: object) -> None:
                key = event.GetKeyCode()
                if key == wx.WXK_F1:
                    self.show_help_on_control()
                    return
                if key not in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
                    event.Skip()
                    return
                focused = wx.Window.FindFocus()
                if isinstance(focused, wx.Button):
                    event.Skip()
                    return
                index = book.GetSelection()
                if 0 <= index < len(areas):
                    chosen["handler"] = areas[index][2]
                    dialog.EndModal(wx.ID_OK)
                    return
                event.Skip()

            dialog.Bind(wx.EVT_CHAR_HOOK, _on_char_hook)

            buttons = dialog.CreateButtonSizer(wx.CLOSE)
            if buttons is not None:
                outer.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
            apply_modal_ids(dialog, affirmative_id=wx.ID_CLOSE, escape_id=wx.ID_CLOSE)
            dialog.SetSizerAndFit(outer)
            # Land initial focus on the category selector so arrow keys and
            # first-letter type-ahead work the instant the hub opens. The
            # selector (Listbook list) is not one of the generic preferred-focus
            # classes, so opt out of the heuristic and keep this explicit focus
            # on every platform.
            book.SetFocus()
            dialog._quill_keep_initial_focus = True
            self._show_modal_dialog(dialog, "Preferences")

        handler = chosen["handler"]
        if handler is None:
            self._set_status("Preferences closed")
            return
        handler()

    def open_glow_settings(self) -> None:
        """Open the GLOW accessibility settings (engine toggle + network consent).

        GLOW is enabled by default and runs locally; the optional networked
        features stay off until the user explicitly turns them on here (GLOW-7).
        """
        from quill.ui.web_form import show_web_form

        values = show_web_form(
            self.frame,
            self._wx,
            title="GLOW Accessibility",
            intro=(
                "GLOW is Quill's built-in accessibility engine. It is on by default "
                "and runs entirely on your computer. The optional features below can "
                "use a network connection and are off until you turn them on. Quill "
                "never sends your document anywhere without asking first."
            ),
            fields=[
                {
                    "name": "enabled",
                    "label": "Enable the GLOW accessibility engine",
                    "type": "checkbox",
                    "value": getattr(self.settings, "glow_enabled", True),
                },
                {
                    "name": "ai_alt_text",
                    "label": "Allow optional AI alt-text generation (uses the network)",
                    "type": "checkbox",
                    "value": getattr(self.settings, "glow_ai_alt_text_consent", False),
                },
                {
                    "name": "pii_redaction",
                    "label": "Allow optional PII redaction (uses the network)",
                    "type": "checkbox",
                    "value": getattr(self.settings, "glow_pii_redaction_consent", False),
                },
                {
                    "name": "language_processing",
                    "label": "Allow optional WCAG language processing (uses the network)",
                    "type": "checkbox",
                    "value": getattr(self.settings, "glow_language_processing_consent", False),
                },
            ],
        )
        if values is None:
            self._set_status("GLOW settings cancelled")
            return
        self.settings.glow_enabled = bool(values.get("enabled", True))
        self.settings.glow_ai_alt_text_consent = bool(values.get("ai_alt_text"))
        self.settings.glow_pii_redaction_consent = bool(values.get("pii_redaction"))
        self.settings.glow_language_processing_consent = bool(values.get("language_processing"))
        save_settings(self.settings)
        self._set_status("GLOW settings saved")

    #: Wildcard for exported QUILL settings files (SET-7).
    QSF_WILDCARD = "QUILL settings file (*.qsf)|*.qsf|All files (*.*)|*.*"
    QPF_WILDCARD = "QUILL profile file (*.qpf)|*.qpf|All files (*.*)|*.*"
    KQP_WILDCARD = "Keyboard Quill Pack (*.kqp)|*.kqp|All files (*.*)|*.*"

    def _wire_experimental_gates(self, control_index: object) -> None:
        """Live enable/disable gating for the Experimental tab.

        The master "Enable experimental features" checkbox governs every other
        control on the tab. Disabled wx controls leave the tab order, so with
        the master switch off the whole tab is a single checkbox to a
        screen-reader user — nothing experimental can be reached, focused, or
        accidentally changed. (The editor-surface options that once lived here
        retired when QuillRichEdit became the one editor surface and the
        braille fix moved to the Braille tab.)
        """
        wx = self._wx

        def _control(key: str) -> object | None:
            entry = control_index.get(key)  # type: ignore[union-attr]
            return entry[1] if entry else None

        master = _control("experimental_acknowledged")
        master_children = [
            control
            for control in (
                _control("glow_experimental_enabled"),
                _control("publishing_experimental_enabled"),
                _control("edge_read_aloud_enabled"),
                _control("table_studio_experimental_enabled"),
            )
            if control is not None
        ]

        def _apply(_evt: object = None) -> None:
            master_on = bool(master.GetValue()) if master is not None else True
            for control in master_children:
                control.Enable(master_on)
            if _evt is not None:
                _evt.Skip()

        if master is not None:
            master.Bind(wx.EVT_CHECKBOX, _apply)
        _apply()

    def _settings_dialog_apply_refresh(self, status: str) -> None:
        """Persist ``self.settings`` and re-run every UI side effect.

        Shared by the OK, Reset to Factory Defaults, and Import paths of the
        tabbed Settings dialog so each one leaves the app in a consistent state.
        """
        if self.settings.launch_at_windows_startup and not self.settings.tray_enabled:
            self.settings.tray_enabled = True
        try:
            from quill.platform.windows.startup import set_launch_at_startup

            set_launch_at_startup(self.settings.launch_at_windows_startup)
        except Exception:  # noqa: BLE001 - a settings-apply side effect must never raise
            pass
        save_settings(self.settings)
        self._apply_theme(self.settings.theme)
        self.toggle_spellcheck_as_you_type(self.settings.spellcheck_as_you_type)
        self._autosave_interval = timedelta(
            seconds=int(getattr(self.settings, "autosave_interval_seconds", 30))
        )
        self._apply_ai_menu_enabled()
        self._refresh_ai_status()
        # Re-apply the model-lifecycle policy in case the Performance settings
        # (Low-resource mode / Unload idle models after) changed.
        try:
            from quill.core import lifecycle_service
            from quill.core.speech.service import detect_total_ram_gb

            lifecycle_service.configure(
                low_resource_mode=bool(getattr(self.settings, "low_resource_mode", False)),
                idle_unload_minutes=int(getattr(self.settings, "idle_unload_minutes", 10)),
                total_ram_gb=detect_total_ram_gb(),
            )
            self._start_lifecycle_sweep_timer()
        except Exception:  # noqa: BLE001 - a settings-apply side effect must never raise
            pass
        self._apply_soft_wrap(self.settings.soft_wrap)
        self._rebuild_tab_host(self.settings.show_tab_control)
        self._build_menu()
        self.set_dirty_title_style(self.settings.dirty_title_style)
        self._refresh_title()
        try:
            from quill.ui import sound_manager

            sound_manager.on_settings_changed(self.settings)
        except Exception:  # noqa: BLE001
            pass
        self._set_status(status)

    def _confirm_restart_for_data_location(self, target_dir: object) -> None:
        """Offer to restart now after a data-location change is queued (#615).

        The move itself happens in ``data_location.apply_pending_data_location_migration``
        at the start of the *next* launch (see ``quill.__main__.main``) -- a
        live move is not safe (Settings is loaded once at startup, CopyTray
        caches its path). This dialog only offers a convenient relaunch.
        """
        wx = self._wx
        dialog = wx.MessageDialog(
            self.frame,
            f"QUILL's data will move to:\n{target_dir}\n\nThis takes effect the next time "
            "QUILL starts. Restart now?",
            "Data Location Changed",
            wx.YES_NO | wx.ICON_INFORMATION,
        )
        dialog.SetYesNoLabels("Restart Now", "Later")
        apply_modal_ids(dialog, affirmative_id=wx.ID_YES, escape_id=wx.ID_NO)
        result = self._show_modal_dialog(dialog, "Data Location Changed")
        dialog.Destroy()
        if result == wx.ID_YES:
            self._relaunch_quill()

    def _relaunch_quill(self) -> None:
        """Spawn a new QUILL process with the same arguments, then close this one."""
        import subprocess
        import sys

        from quill.core.relaunch import build_relaunch_command

        try:
            subprocess.Popen(build_relaunch_command(sys.executable, sys.argv))
        except OSError as error:
            self._set_status(f"Could not restart automatically: {error}. Please restart QUILL.")
            return
        self.frame.Close()

    def _surface_data_migration_notice(self) -> None:
        """Announce the one-time data move/import result from a prior launch.

        Covers both the #615 data-location move and the legacy-install import
        (data_location.apply_pending_legacy_import). The notice is consumed
        once, so it is spoken/shown only on the launch that applied the change.
        """
        try:
            from quill.core.data_location import pop_pending_migration_notice

            notice = pop_pending_migration_notice()
        except Exception:
            return
        if notice:
            self._announce_result(notice)

    def _maybe_offer_legacy_data_import(self) -> bool:
        """Offer to import data stranded in a prior install's location.

        Detected when the current (fresh) data dir has no keymap of its own
        but a different, populated QUILL data dir exists -- typically after a
        portable<->installed switch or a lost storage-mode marker on reinstall.

        Returns True when the user accepted and a restart was triggered (the
        caller must stop onboarding -- the app is relaunching to apply the
        import before Settings are read).
        """
        try:
            from quill.core.data_location import (
                decline_legacy_data_import,
                detect_importable_legacy_dir,
                legacy_data_import_declined,
                request_legacy_data_import,
            )

            legacy = detect_importable_legacy_dir()
        except Exception:
            return False
        if legacy is None or legacy_data_import_declined(legacy):
            return False
        wx = self._wx
        dialog = wx.MessageDialog(
            self.frame,
            f"QUILL found data from a previous installation at:\n{legacy}\n\n"
            "Import your settings, keyboard shortcuts, and documents into this "
            "copy of QUILL? QUILL will restart to complete the import.",
            "Import Previous QUILL Data",
            wx.YES_NO | wx.ICON_QUESTION,
        )
        dialog.SetYesNoLabels("Import and Restart", "Not Now")
        apply_modal_ids(dialog, affirmative_id=wx.ID_YES, escape_id=wx.ID_NO)
        result = self._show_modal_dialog(dialog, "Import Previous QUILL Data")
        dialog.Destroy()
        if result == wx.ID_YES:
            try:
                request_legacy_data_import(legacy)
            except OSError as error:
                self._set_status(f"Could not queue the data import: {error}.")
                return False
            self._relaunch_quill()
            return True
        try:
            decline_legacy_data_import(legacy)
        except OSError:
            pass
        return False

    def open_general_preferences(self) -> None:
        from quill.core import settings_registry as registry
        from quill.core.ai.model_manager import load_ai_enabled, save_ai_enabled

        wx = self._wx

        # Readers map each rendered registry key to a callable returning its
        # stored (normalized) value. Index maps key -> (page_index, control) so
        # the search box can jump straight to a matching control.
        readers: dict[str, Callable[[], object]] = {}
        # writers set a rendered control back to a given stored value; used by
        # the per-setting Reset buttons (SET-6) to restore a single default.
        writers: dict[str, Callable[[object], None]] = {}
        _dirty: list[bool] = [False]  # mutable flag shared with _mark_dirty closure
        control_index: dict[str, tuple[int, object]] = {}
        collected: dict[str, object] = {}
        ai_value: bool | None = None
        ext_master_value: bool | None = None
        ext_engine_spec: tuple[str, str, bool] | None = None
        data_location_choice: tuple[str, str] | None = None

        with wx.Dialog(self.frame, title="Settings") as dialog:
            outer = wx.BoxSizer(wx.VERTICAL)

            notebook = wx.Notebook(dialog)
            notebook.SetName("Settings categories")

            def _add_field_row(
                parent_panel, sizer, label: str, control_or_factory, reset=None
            ) -> object:
                row = wx.BoxSizer(wx.HORIZONTAL)
                row.Add(
                    wx.StaticText(parent_panel, label=label),
                    0,
                    wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                    8,
                )
                ctrl = control_or_factory() if callable(control_or_factory) else control_or_factory
                row.Add(ctrl, 1, wx.EXPAND)
                if reset is not None:
                    row.Add(reset, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 8)
                sizer.Add(row, 0, wx.EXPAND | wx.ALL, 6)
                return ctrl

            def _make_control(parent_panel, sizer, spec, page_index: int) -> None:
                current = registry.get_value(self.settings, spec.key)
                # preview_browser is stored as text but is best chosen from the
                # list of installed browsers.
                if spec.key == "preview_browser":

                    def _make_browser_choice(_pp=parent_panel, _sl=spec.label, _cur=str(current)):
                        c = wx.Choice(
                            _pp,
                            choices=[opt.label for opt in available_browser_options()],
                        )
                        c.SetName(_sl)
                        c.SetStringSelection(browser_choice_label_for_value(_cur))
                        return c

                    choice = _add_field_row(parent_panel, sizer, spec.label, _make_browser_choice)
                    readers[spec.key] = lambda c=choice: browser_choice_value_for_label(
                        c.GetStringSelection() or "System default browser"
                    )
                    writers[spec.key] = lambda v, c=choice: c.SetStringSelection(
                        browser_choice_label_for_value(str(v))
                    )
                    control_index[spec.key] = (page_index, choice)
                    choice.Bind(wx.EVT_CHOICE, _mark_dirty)
                    return
                if spec.key == "startup_folder":
                    _folder_text_ref: list = []

                    def _make_folder_row(
                        _pp=parent_panel,
                        _cur=str(current),
                        _sl=spec.label,
                        _ref=_folder_text_ref,
                    ):
                        _t = wx.TextCtrl(_pp)
                        _t.SetValue(_cur)
                        _t.SetName(_sl)
                        _t.SetHint(
                            "e.g. /Users/YourName/Documents (blank = last used)"
                            if sys.platform == "darwin"
                            else "e.g. C:\\Users\\YourName\\Documents (blank = last used)"
                        )
                        _b = wx.Button(_pp, label="Choose Default Folder...")
                        _b.SetName(f"Choose default folder for {_sl}")

                        def _on_browse(_evt, __t=_t, __pp=_pp) -> None:
                            with wx.DirDialog(
                                __pp,
                                "Choose default file-open folder",
                                defaultPath=__t.GetValue().strip(),
                                style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
                            ) as ddlg:
                                if (
                                    self._show_modal_dialog(ddlg, "Default file-open folder")
                                    == wx.ID_OK
                                ):
                                    __t.SetValue(ddlg.GetPath())

                        _b.Bind(wx.EVT_BUTTON, _on_browse)
                        _row = wx.BoxSizer(wx.HORIZONTAL)
                        _row.Add(_t, 1, wx.EXPAND | wx.RIGHT, 8)
                        _row.Add(_b, 0, wx.ALIGN_CENTER_VERTICAL)
                        _ref.append(_t)
                        return _row

                    _add_field_row(parent_panel, sizer, spec.label, _make_folder_row)
                    text = _folder_text_ref[0]
                    readers[spec.key] = lambda c=text: str(c.GetValue())
                    writers[spec.key] = lambda v, c=text: c.SetValue(str(v))
                    control_index[spec.key] = (page_index, text)
                    text.Bind(wx.EVT_TEXT, _mark_dirty)
                    return
                if spec.key in {
                    "quill_key_sound_enter",
                    "quill_key_sound_exit",
                    "quill_key_sound_move",
                    "quill_key_sound_error",
                }:
                    _sound_text_ref: list = []

                    def _make_sound_file_row(
                        _pp=parent_panel,
                        _cur=str(current),
                        _sl=spec.label,
                        _ref=_sound_text_ref,
                    ):
                        _t = wx.TextCtrl(_pp)
                        _t.SetValue(_cur)
                        _t.SetName(_sl)
                        _t.SetHint("blank = default beep")
                        _b = wx.Button(_pp, label="Choose WAV file...")
                        _b.SetName(f"Choose WAV file for {_sl}")
                        _p = wx.Button(_pp, label="Preview")
                        _p.SetName(f"Preview {_sl}")

                        def _on_browse(_evt, __t=_t, __pp=_pp) -> None:
                            with wx.FileDialog(
                                __pp,
                                "Choose a WAV file",
                                wildcard="WAV files (*.wav)|*.wav",
                                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
                            ) as fdlg:
                                if (
                                    self._show_modal_dialog(fdlg, "Choose Browse Mode Sound")
                                    == wx.ID_OK
                                ):
                                    __t.SetValue(fdlg.GetPath())

                        def _on_preview(_evt, __t=_t) -> None:
                            path = __t.GetValue().strip()
                            if path:
                                self._play_preview_asset(Path(path))

                        _b.Bind(wx.EVT_BUTTON, _on_browse)
                        _p.Bind(wx.EVT_BUTTON, _on_preview)
                        _row = wx.BoxSizer(wx.HORIZONTAL)
                        _row.Add(_t, 1, wx.EXPAND | wx.RIGHT, 4)
                        _row.Add(_b, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
                        _row.Add(_p, 0, wx.ALIGN_CENTER_VERTICAL)
                        _ref.append(_t)
                        return _row

                    _add_field_row(parent_panel, sizer, spec.label, _make_sound_file_row)
                    text = _sound_text_ref[0]
                    readers[spec.key] = lambda c=text: str(c.GetValue())
                    writers[spec.key] = lambda v, c=text: c.SetValue(str(v))
                    control_index[spec.key] = (page_index, text)
                    text.Bind(wx.EVT_TEXT, _mark_dirty)
                    return
                if spec.key == "language":

                    def _make_lang_text(_pp=parent_panel, _cur=str(current), _sl=spec.label):
                        t = wx.TextCtrl(_pp)
                        t.SetValue(_cur)
                        t.SetName(_sl)
                        t.SetHint("e.g. en, fr, es (blank = OS language)")
                        return t

                    lang_ctrl = _add_field_row(parent_panel, sizer, spec.label, _make_lang_text)
                    readers[spec.key] = lambda c=lang_ctrl: str(c.GetValue())
                    writers[spec.key] = lambda v, c=lang_ctrl: c.SetValue(str(v))
                    control_index[spec.key] = (page_index, lang_ctrl)
                    lang_ctrl.Bind(wx.EVT_TEXT, _mark_dirty)
                    return

                if spec.key == "abbreviation_expansion_sound_file":
                    _abbr_sound_ref: list = []

                    def _make_abbr_sound_row(
                        _pp=parent_panel,
                        _cur=str(current),
                        _sl=spec.label,
                        _ref=_abbr_sound_ref,
                    ):
                        _t = wx.TextCtrl(_pp)
                        _t.SetValue(_cur)
                        _t.SetName(_sl)
                        _t.SetHint("blank = default system sound")
                        _b = wx.Button(_pp, label="Choose WAV file...")
                        _b.SetName(f"Choose WAV file for {_sl}")
                        _p = wx.Button(_pp, label="Preview")
                        _p.SetName(f"Preview {_sl}")

                        def _on_browse(_evt, __t=_t, __pp=_pp) -> None:
                            with wx.FileDialog(
                                __pp,
                                "Choose abbreviation expansion sound",
                                wildcard="WAV files (*.wav)|*.wav",
                                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
                            ) as fdlg:
                                if (
                                    self._show_modal_dialog(fdlg, "Choose Abbreviation Sound")
                                    == wx.ID_OK
                                ):
                                    __t.SetValue(fdlg.GetPath())

                        def _on_preview(_evt, __t=_t) -> None:
                            path = __t.GetValue().strip()
                            if path:
                                self._play_preview_asset(Path(path))

                        _b.Bind(wx.EVT_BUTTON, _on_browse)
                        _p.Bind(wx.EVT_BUTTON, _on_preview)
                        _row = wx.BoxSizer(wx.HORIZONTAL)
                        _row.Add(_t, 1, wx.EXPAND | wx.RIGHT, 4)
                        _row.Add(_b, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
                        _row.Add(_p, 0, wx.ALIGN_CENTER_VERTICAL)
                        _ref.append(_t)
                        return _row

                    _add_field_row(parent_panel, sizer, spec.label, _make_abbr_sound_row)
                    abbr_text = _abbr_sound_ref[0]
                    readers[spec.key] = lambda c=abbr_text: str(c.GetValue())
                    writers[spec.key] = lambda v, c=abbr_text: c.SetValue(str(v))
                    control_index[spec.key] = (page_index, abbr_text)
                    abbr_text.Bind(wx.EVT_TEXT, _mark_dirty)
                    return

                if spec.key == "sound_pack_path":
                    _sp_ref: list = []

                    def _make_sp_row(
                        _pp=parent_panel,
                        _cur=str(current),
                        _sl=spec.label,
                        _ref=_sp_ref,
                    ):
                        _t = wx.TextCtrl(_pp)
                        _t.SetValue(_cur)
                        _t.SetName(_sl)
                        _t.SetHint("blank = bundled Ink pack")
                        _b = wx.Button(_pp, label="Choose Sound Pack...")
                        _b.SetName(f"Choose sound pack folder or file for {_sl}")

                        def _on_browse(_evt, __t=_t, __pp=_pp) -> None:
                            with wx.DirDialog(
                                __pp,
                                "Choose sound pack folder",
                                defaultPath=__t.GetValue().strip(),
                                style=wx.DD_DEFAULT_STYLE,
                            ) as ddlg:
                                if self._show_modal_dialog(ddlg, "Choose Sound Pack") == wx.ID_OK:
                                    __t.SetValue(ddlg.GetPath())

                        _b.Bind(wx.EVT_BUTTON, _on_browse)
                        _row = wx.BoxSizer(wx.HORIZONTAL)
                        _row.Add(_t, 1, wx.EXPAND | wx.RIGHT, 8)
                        _row.Add(_b, 0, wx.ALIGN_CENTER_VERTICAL)
                        _ref.append(_t)
                        return _row

                    _add_field_row(parent_panel, sizer, spec.label, _make_sp_row)
                    sp_text = _sp_ref[0]
                    readers[spec.key] = lambda c=sp_text: str(c.GetValue())
                    writers[spec.key] = lambda v, c=sp_text: c.SetValue(str(v))
                    control_index[spec.key] = (page_index, sp_text)
                    sp_text.Bind(wx.EVT_TEXT, _mark_dirty)
                    return

                if spec.kind == "bool":
                    cb = wx.CheckBox(parent_panel, label=spec.label)
                    cb.SetValue(bool(current))
                    if spec.description:
                        cb.SetName(f"{spec.label}. {spec.description}")
                    sizer.Add(cb, 0, wx.EXPAND | wx.ALL, 6)
                    readers[spec.key] = lambda c=cb: bool(c.GetValue())
                    writers[spec.key] = lambda v, c=cb: c.SetValue(bool(v))
                    control_index[spec.key] = (page_index, cb)
                    cb.Bind(wx.EVT_CHECKBOX, _mark_dirty)
                    if spec.key == "beta_updates":

                        def _on_beta_toggle(_event: object, _cb=cb) -> None:
                            if _cb.GetValue() and not self._confirm_beta_channel():
                                _cb.SetValue(False)

                        cb.Bind(wx.EVT_CHECKBOX, _on_beta_toggle)
                    if spec.key == "braille_editor_hide_border":
                        # Unchecking breaks braille cell alignment; warn at
                        # decision time and re-check unless the user confirms.
                        def _on_border_toggle(_event: object, _cb=cb) -> None:
                            if not _cb.GetValue() and not self._confirm_show_editor_border():
                                _cb.SetValue(True)

                        cb.Bind(wx.EVT_CHECKBOX, _on_border_toggle)
                    return
                if spec.key == "browse_mode_followon_timeout":
                    # Choice + sibling SpinCtrl: the spin is only enabled
                    # when the user picks "Custom..." so the two controls
                    # behave as one logical row.
                    from quill.core.settings_specs import SETTING_SPECS as _ALL_SPECS

                    custom_spec = next(
                        (s for s in _ALL_SPECS if s.key == "browse_mode_followon_custom_ms"),
                        None,
                    )
                    labels = [label for _value, label in spec.choices]
                    value_for_label = {label: value for value, label in spec.choices}
                    label_for_value = {value: label for value, label in spec.choices}
                    try:
                        custom_current = int(
                            registry.get_value(self.settings, "browse_mode_followon_custom_ms")
                        )
                    except (TypeError, ValueError):
                        custom_current = 4000

                    custom_max = int(getattr(custom_spec, "maximum", 60000) or 60000)
                    custom_min = int(getattr(custom_spec, "minimum", 0) or 0)
                    custom_label = str(getattr(custom_spec, "label", "Custom value (milliseconds)"))
                    custom_choice_label = value_for_label.get("custom", "Custom...")

                    def _make_timeout_row(
                        _pp=parent_panel,
                        _ls=labels,
                        _lv=label_for_value,
                        _cv=str(current),
                        _sl=spec.label,
                        _cmax=custom_max,
                        _cmin=custom_min,
                        _cur=custom_current,
                        _custom_sl=custom_label,
                        _custom_label_value=custom_choice_label,
                    ):
                        c = wx.Choice(_pp, choices=_ls)
                        c.SetName(_sl)
                        c.SetStringSelection(_lv.get(_cv, _ls[0]))
                        spin = wx.SpinCtrl(_pp, min=_cmin, max=_cmax, value=str(_cur))
                        set_accessible_name(spin, _custom_sl)
                        ms_label = wx.StaticText(_pp, label="ms")
                        ms_label.SetName(_custom_sl + " (milliseconds)")
                        # Wire enable/disable of the spin to the chooser.
                        spin.Enable(_lv.get(_cv, _ls[0]) == _custom_label_value)
                        c.Bind(
                            wx.EVT_CHOICE,
                            lambda _evt, _c=c, _s=spin, _custom_label_value=_custom_label_value: (
                                _s.Enable(_c.GetStringSelection() == _custom_label_value)
                            ),
                        )
                        return c, spin, ms_label

                    # Build the row manually — _add_field_row only lays out
                    # one control, but this row needs three (choice, spin,
                    # "ms" label) so the user sees the relationship.
                    row = wx.BoxSizer(wx.HORIZONTAL)
                    row.Add(
                        wx.StaticText(parent_panel, label=spec.label),
                        0,
                        wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                        8,
                    )
                    choice, spin, ms_label = _make_timeout_row()
                    row.Add(choice, 1, wx.EXPAND | wx.RIGHT, 8)
                    row.Add(spin, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
                    row.Add(ms_label, 0, wx.ALIGN_CENTER_VERTICAL)
                    sizer.Add(row, 0, wx.EXPAND | wx.ALL, 6)
                    readers[spec.key] = lambda c=choice, m=value_for_label, d=str(current): m.get(
                        c.GetStringSelection(), d
                    )
                    writers[spec.key] = lambda v, c=choice, m=label_for_value, ls=labels: (
                        c.SetStringSelection(m.get(str(v), ls[0]))
                    )
                    readers["browse_mode_followon_custom_ms"] = lambda s=spin: int(s.GetValue())
                    writers["browse_mode_followon_custom_ms"] = lambda v, s=spin: s.SetValue(int(v))
                    control_index[spec.key] = (page_index, choice)
                    control_index["browse_mode_followon_custom_ms"] = (page_index, spin)
                    choice.Bind(wx.EVT_CHOICE, _mark_dirty)
                    spin.Bind(wx.EVT_SPINCTRL, _mark_dirty)
                    return
                if spec.kind == "choice":
                    labels = [label for _value, label in spec.choices]
                    value_for_label = {label: value for value, label in spec.choices}
                    label_for_value = {value: label for value, label in spec.choices}

                    def _make_choice(
                        _pp=parent_panel,
                        _ls=labels,
                        _lv=label_for_value,
                        _cv=str(current),
                        _sl=spec.label,
                    ):
                        c = wx.Choice(_pp, choices=_ls)
                        c.SetName(_sl)
                        c.SetStringSelection(_lv.get(_cv, _ls[0]))
                        return c

                    choice = _add_field_row(parent_panel, sizer, spec.label, _make_choice)
                    readers[spec.key] = lambda c=choice, m=value_for_label, d=str(current): m.get(
                        c.GetStringSelection(), d
                    )
                    writers[spec.key] = lambda v, c=choice, m=label_for_value, ls=labels: (
                        c.SetStringSelection(m.get(str(v), ls[0]))
                    )
                    control_index[spec.key] = (page_index, choice)
                    choice.Bind(wx.EVT_CHOICE, _mark_dirty)
                    return
                if spec.kind == "int":
                    # #265 follow-up: the custom-ms spec is rendered as a
                    # sibling SpinCtrl of browse_mode_followon_timeout's
                    # chooser above; skip its own row to avoid duplication.
                    if spec.key == "browse_mode_followon_custom_ms":
                        return

                    def _make_spin_int(_pp=parent_panel, _spec=spec, _cur=int(current)):
                        s = wx.SpinCtrl(_pp)
                        if _spec.minimum is not None and _spec.maximum is not None:
                            s.SetRange(int(_spec.minimum), int(_spec.maximum))
                        s.SetValue(_cur)
                        # support#69: VoiceOver reads the inner TextCtrl, not the
                        # composite's Name -- the helper names both (#1012).
                        set_accessible_name(s, _spec.label)
                        return s

                    spin = _add_field_row(parent_panel, sizer, spec.label, _make_spin_int)
                    readers[spec.key] = lambda c=spin: int(c.GetValue())
                    writers[spec.key] = lambda v, c=spin: c.SetValue(int(v))
                    control_index[spec.key] = (page_index, spin)
                    spin.Bind(wx.EVT_SPINCTRL, _mark_dirty)
                    return
                if spec.kind == "float":

                    def _make_spin_float(_pp=parent_panel, _spec=spec, _cur=float(current)):
                        s = wx.SpinCtrlDouble(_pp, inc=0.1)
                        if _spec.minimum is not None and _spec.maximum is not None:
                            s.SetRange(float(_spec.minimum), float(_spec.maximum))
                        s.SetValue(_cur)
                        set_accessible_name(s, _spec.label)
                        return s

                    spin = _add_field_row(parent_panel, sizer, spec.label, _make_spin_float)
                    readers[spec.key] = lambda c=spin: float(c.GetValue())
                    writers[spec.key] = lambda v, c=spin: c.SetValue(float(v))
                    control_index[spec.key] = (page_index, spin)
                    spin.Bind(wx.EVT_SPINCTRLDOUBLE, _mark_dirty)
                    return

                # text
                def _make_text(_pp=parent_panel, _cur=str(current), _sl=spec.label):
                    t = wx.TextCtrl(_pp)
                    t.SetValue(_cur)
                    t.SetName(_sl)
                    return t

                text = _add_field_row(parent_panel, sizer, spec.label, _make_text)
                readers[spec.key] = lambda c=text: str(c.GetValue())
                writers[spec.key] = lambda v, c=text: c.SetValue(str(v))
                control_index[spec.key] = (page_index, text)
                text.Bind(wx.EVT_TEXT, _mark_dirty)

            page_index = 0
            _page_build_fns: list[Callable[[], None]] = []
            _built_pages: set[int] = set()
            _ai_refs: dict[str, object] = {}
            _data_location_refs: dict[str, object] = {}

            def _build_data_location_block(_p: object, _ps: object) -> None:
                # #615: lives outside the Settings/registry mechanism on
                # purpose -- settings.json is itself stored under
                # app_data_dir(), so "where is app_data_dir()" cannot be a
                # Settings field without being circular. storage_mode.py's
                # separate storage-mode.json is the single source of truth;
                # this block only displays it and queues a change via
                # core.data_location (applied on next restart, see the OK
                # handler below).
                from quill.core import storage_mode as _storage_mode
                from quill.core.data_location import resolve_target as _resolve_target
                from quill.core.paths import app_data_dir as _app_data_dir

                _ps.Add(wx.StaticLine(_p), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 6)
                _ps.Add(wx.StaticText(_p, label="Data location"), 0, wx.LEFT | wx.TOP, 6)

                _portable_root = _storage_mode.portable_root_dir()
                _mode_labels = ["In my user profile (recommended)"]
                _mode_values = ["appdata"]
                if _portable_root is not None:
                    _mode_labels.append("Next to QUILL, on this portable drive")
                    _mode_values.append("portable")
                _mode_labels.append("Custom folder")
                _mode_values.append("custom")

                _current_mode = _storage_mode.load_storage_mode() or "appdata"
                if _current_mode not in _mode_values:
                    _current_mode = "appdata"
                _current_custom = _storage_mode.custom_path()

                def _make_mode_choice(_pp=_p):
                    c = wx.Choice(_pp, choices=_mode_labels)
                    c.SetName("Data location")
                    c.SetSelection(_mode_values.index(_current_mode))
                    return c

                mode_choice = _add_field_row(
                    _p, _ps, "Store QUILL's data:", lambda: _make_mode_choice()
                )

                _path_row = wx.BoxSizer(wx.HORIZONTAL)
                _path_display = wx.StaticText(_p, label=str(_current_custom or app_data_dir()))
                _choose_btn = wx.Button(_p, label="Choose Folder...")
                _choose_btn.SetName("Choose custom data folder")
                _path_row.Add(_path_display, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
                _path_row.Add(_choose_btn, 0, wx.ALIGN_CENTER_VERTICAL)
                _ps.Add(_path_row, 0, wx.EXPAND | wx.ALL, 6)

                _custom_holder: list[str] = [str(_current_custom or "")]

                def _apply_enabled_state(_c=mode_choice, _b=_choose_btn) -> None:
                    _b.Enable(_mode_values[_c.GetSelection()] == "custom")

                def _on_choose(_evt: object, _pp=_p) -> None:
                    with wx.DirDialog(
                        _pp,
                        "Choose a folder for QUILL's data",
                        defaultPath=_custom_holder[0],
                        style=wx.DD_DEFAULT_STYLE,
                    ) as ddlg:
                        if self._show_modal_dialog(ddlg, "Choose Data Folder") == wx.ID_OK:
                            _custom_holder[0] = ddlg.GetPath()
                            _path_display.SetLabel(_custom_holder[0])
                            _p.Layout()

                def _on_mode_choice(_e: object) -> None:
                    _apply_enabled_state()
                    _mark_dirty(_e)

                mode_choice.Bind(wx.EVT_CHOICE, _on_mode_choice)
                _choose_btn.Bind(wx.EVT_BUTTON, _on_choose)
                _apply_enabled_state()

                def _read_data_location() -> tuple[str, str]:
                    selected_mode = _mode_values[mode_choice.GetSelection()]
                    return selected_mode, _custom_holder[0]

                _data_location_refs["read"] = _read_data_location
                _data_location_refs["resolve_target"] = _resolve_target
                _data_location_refs["current"] = _app_data_dir()

            def _make_page_builder(
                _p: object,
                _ps: object,
                _pi: int,
                _sp: list,
                _g: object,
                _sa: bool,
                _show_data_location: bool = False,
                _show_mgmt: bool = False,
                _show_experimental: bool = False,
            ) -> Callable[[], None]:
                def _build() -> None:
                    if _g.description:
                        _ps.Add(wx.StaticText(_p, label=_g.description), 0, wx.ALL, 6)
                    if _sa:
                        _ai_cb = wx.CheckBox(_p, label="Use Artificial Intelligence")
                        _ai_cb.SetValue(load_ai_enabled())
                        _ai_cb.SetName(
                            "Use Artificial Intelligence. Master switch for all AI features."
                        )
                        _ps.Add(_ai_cb, 0, wx.ALL, 6)
                        _ai_refs["ai_enabled_cb"] = _ai_cb
                        _hub_btn = wx.Button(_p, label="Open AI Hub...")
                        _hub_btn.SetName(
                            "Open AI Hub to configure providers, models, and API connections"
                        )
                        _ps.Add(_hub_btn, 0, wx.LEFT | wx.BOTTOM, 6)

                        def _on_hub(_evt: object) -> None:
                            self.open_ai_hub()

                        _hub_btn.Bind(wx.EVT_BUTTON, _on_hub)
                        from quill.core.ai.external_engine import (
                            external_engines_enabled,
                            list_engine_ids,
                            load_engine_config,
                        )

                        _ext_cb = wx.CheckBox(_p, label="Allow external engines")
                        _ext_cb.SetValue(external_engines_enabled())
                        _ext_cb.SetName(
                            "Allow external engines. Off by default. Let QUILL drive a "
                            "trusted helper program as a local subprocess."
                        )
                        _ps.Add(_ext_cb, 0, wx.ALL, 6)
                        _ai_refs["ext_master_cb"] = _ext_cb
                        _engine_ids = list_engine_ids()
                        _first_engine = load_engine_config(_engine_ids[0]) if _engine_ids else None
                        _nf = _add_field_row(
                            _p, _ps, "External engine name", lambda pp=_p: wx.TextCtrl(pp)
                        )
                        _nf.SetName("External engine name")
                        _nf.SetValue(_first_engine.engine_id if _first_engine else "")
                        _ai_refs["ext_name_field"] = _nf
                        _cf = _add_field_row(
                            _p, _ps, "External engine command", lambda pp=_p: wx.TextCtrl(pp)
                        )
                        _cf.SetName("External engine command")
                        _cf.SetValue(" ".join(_first_engine.command) if _first_engine else "")
                        _ai_refs["ext_command_field"] = _cf
                        _ef = wx.CheckBox(_p, label="Enable this external engine")
                        _ef.SetValue(bool(_first_engine.enabled) if _first_engine else False)
                        _ps.Add(_ef, 0, wx.ALL, 6)
                        _ai_refs["ext_engine_enabled_cb"] = _ef
                        _ps.Add(wx.StaticLine(_p), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 6)
                        # AI is always a top-level "&AI" menu now (the former
                        # opt-in toggle was retired, 2026-06-27).
                        _ps.Add(
                            wx.StaticText(
                                _p,
                                label="All other AI settings (providers, models, API keys) "
                                "are managed in the AI Hub.",
                            ),
                            0,
                            wx.ALL,
                            6,
                        )
                        _p.Layout()
                        return
                    for spec in _sp:
                        _make_control(_p, _ps, spec, _pi)
                    if _show_experimental:
                        self._wire_experimental_gates(control_index)
                    if _show_data_location:
                        _build_data_location_block(_p, _ps)
                    if _show_mgmt:
                        _ps.Add(wx.StaticLine(_p), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 6)
                        _ps.Add(
                            wx.StaticText(
                                _p,
                                label=(
                                    "Export, import, and reset your settings and feature profiles."
                                ),
                            ),
                            0,
                            wx.ALL,
                            6,
                        )
                        _exp_btn = wx.Button(_p, label="&Export settings...")
                        _imp_btn = wx.Button(_p, label="&Import settings...")
                        _rst_btn = wx.Button(_p, label="&Reset to Factory Defaults")
                        _exp_prf_btn = wx.Button(_p, label="Export &profile...")
                        _imp_prf_btn = wx.Button(_p, label="Import pro&file...")
                        for _mb in [_exp_btn, _imp_btn, _rst_btn, _exp_prf_btn, _imp_prf_btn]:
                            _ps.Add(_mb, 0, wx.ALL, 4)

                        def _on_export(_event: object) -> None:
                            with wx.FileDialog(
                                dialog,
                                "Export settings",
                                wildcard=self.QSF_WILDCARD,
                                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
                            ) as file_dialog:
                                if (
                                    self._show_modal_dialog(file_dialog, "Export settings")
                                    != wx.ID_OK
                                ):
                                    return
                                target = Path(file_dialog.GetPath())
                            if target.suffix.lower() != ".qsf":
                                target = target.with_suffix(".qsf")
                            payload = registry.export_settings(self.settings)
                            target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                            self._set_status(f"Exported settings to {target.name}")

                        def _on_import(_event: object) -> None:
                            with wx.FileDialog(
                                dialog,
                                "Import settings",
                                wildcard=self.QSF_WILDCARD,
                                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
                            ) as file_dialog:
                                if (
                                    self._show_modal_dialog(file_dialog, "Import settings")
                                    != wx.ID_OK
                                ):
                                    return
                                source = Path(file_dialog.GetPath())
                            try:
                                raw = json.loads(source.read_text(encoding="utf-8"))
                            except (OSError, ValueError):
                                self._set_status(f"Could not read settings from {source.name}")
                                return
                            action["mode"] = "import"
                            action["imported"] = registry.import_settings(raw)
                            dialog.EndModal(wx.ID_CANCEL)

                        def _on_reset(_event: object) -> None:
                            result = self._show_message_box(
                                "Reset every setting to its factory default?"
                                " This cannot be undone.",
                                "Reset to Factory Defaults",
                                wx.ICON_WARNING | wx.YES_NO | wx.NO_DEFAULT,
                            )
                            if result != wx.YES:
                                return
                            action["mode"] = "reset"
                            dialog.EndModal(wx.ID_CANCEL)

                        def _on_export_profile(_event: object) -> None:
                            with wx.FileDialog(
                                dialog,
                                "Export profile",
                                wildcard=self.QPF_WILDCARD,
                                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
                            ) as file_dialog:
                                if (
                                    self._show_modal_dialog(file_dialog, "Export profile")
                                    != wx.ID_OK
                                ):
                                    return
                                target = Path(file_dialog.GetPath())
                            if target.suffix.lower() != ".qpf":
                                target = target.with_suffix(".qpf")
                            try:
                                export_feature_profile_file(self.features, target)
                            except OSError:
                                self._set_status(f"Could not write profile to {target.name}")
                                return
                            self._set_status(f"Exported feature profile to {target.name}")

                        def _on_import_profile(_event: object) -> None:
                            with wx.FileDialog(
                                dialog,
                                "Import profile",
                                wildcard=self.QPF_WILDCARD,
                                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
                            ) as file_dialog:
                                if (
                                    self._show_modal_dialog(file_dialog, "Import profile")
                                    != wx.ID_OK
                                ):
                                    return
                                source = Path(file_dialog.GetPath())
                            try:
                                warnings = import_feature_profile_file(self.features, source)
                            except (OSError, ValueError):
                                self._set_status(
                                    f"Could not read a feature profile from {source.name}"
                                )
                                return
                            self._apply_accelerators()
                            self._build_menu()
                            profile_name = self.features.active_profile.name
                            if warnings:
                                self._set_status(
                                    f"Imported profile {profile_name}"
                                    f" ({len(warnings)} item(s) ignored)"
                                )
                            else:
                                self._set_status(f"Imported feature profile {profile_name}")

                        _exp_btn.Bind(wx.EVT_BUTTON, _on_export)
                        _imp_btn.Bind(wx.EVT_BUTTON, _on_import)
                        _rst_btn.Bind(wx.EVT_BUTTON, _on_reset)
                        _exp_prf_btn.Bind(wx.EVT_BUTTON, _on_export_profile)
                        _imp_prf_btn.Bind(wx.EVT_BUTTON, _on_import_profile)
                    _p.Layout()

                return _build

            for group in registry.groups():
                specs = [
                    spec
                    for spec in registry.specs_for_group(group.id)
                    if not spec.feature_id or self._feature_enabled(spec.feature_id)
                ]
                show_ai_master = group.id == "ai"
                show_data_location = group.id == "general"
                show_mgmt = group.id == "admin"
                show_experimental = group.id == "experimental"
                if not specs and not show_ai_master and not show_data_location and not show_mgmt:
                    continue
                _pg = wx.Panel(notebook, style=wx.TAB_TRAVERSAL)
                _pg.SetSizer(wx.BoxSizer(wx.VERTICAL))
                notebook.AddPage(_pg, group.title)
                _page_build_fns.append(
                    _make_page_builder(
                        _pg,
                        _pg.GetSizer(),
                        page_index,
                        specs,
                        group,
                        show_ai_master,
                        show_data_location,
                        show_mgmt,
                        show_experimental,
                    )
                )
                page_index += 1

            outer.Add(notebook, 1, wx.EXPAND | wx.ALL, 8)

            # action carries the post-dialog instruction: "ok" | "cancel" |
            # "import" | "reset"; imported holds the Settings parsed from a file.
            action: dict[str, object] = {"mode": "cancel", "imported": None}

            _ok_btn = wx.Button(dialog, id=wx.ID_OK)
            _cancel_btn = wx.Button(dialog, id=wx.ID_CANCEL)
            _apply_btn = wx.Button(dialog, label="&Apply")
            _apply_btn.SetName("Apply settings without closing")
            _btn_row = wx.BoxSizer(wx.HORIZONTAL)
            _btn_row.AddStretchSpacer(1)
            _btn_row.Add(_ok_btn, 0, wx.RIGHT, 8)
            _btn_row.Add(_cancel_btn, 0, wx.RIGHT, 8)
            _btn_row.Add(_apply_btn, 0)
            outer.Add(_btn_row, 0, wx.EXPAND | wx.ALL, 8)

            _apply_btn.Enable(False)

            def _mark_dirty(_evt: object = None) -> None:
                if not _dirty[0]:
                    _dirty[0] = True
                    _apply_btn.Enable(True)

            def _do_apply() -> None:
                _c = {k: r() for k, r in readers.items()}
                # The braille editor fix only takes full effect on restart; warn if
                # the user changed it so they are not confused that nothing changed.
                _restart_keys = (
                    "braille_editor_system_edit_fix",
                    "braille_editor_hide_border",
                )
                _before = {k: getattr(self.settings, k, None) for k in _restart_keys}
                upd = self.settings
                for k, v in _c.items():
                    upd = registry.set_value(upd, k, v)
                self.settings = upd
                _editor_restart_changed = any(
                    getattr(self.settings, k, None) != _before[k] for k in _restart_keys
                )
                _ai_cb2 = _ai_refs.get("ai_enabled_cb")
                if _ai_cb2 is not None:
                    save_ai_enabled(bool(_ai_cb2.GetValue()))
                    self._sync_ai_enabled_menu(bool(_ai_cb2.GetValue()))
                _ext_cb2 = _ai_refs.get("ext_master_cb")
                if _ext_cb2 is not None:
                    from quill.core.ai.external_engine import (
                        configure_engine,
                        set_external_engines_enabled,
                    )

                    set_external_engines_enabled(bool(_ext_cb2.GetValue()))
                    _nf2 = _ai_refs.get("ext_name_field")
                    _cf2 = _ai_refs.get("ext_command_field")
                    _ef2 = _ai_refs.get("ext_engine_enabled_cb")
                    if _nf2 is not None and _cf2 is not None and str(_nf2.GetValue()).strip():
                        try:
                            configure_engine(
                                str(_nf2.GetValue()),
                                str(_cf2.GetValue()),
                                enabled=bool(_ef2.GetValue()) if _ef2 is not None else False,
                            )
                        except ValueError as _ve:
                            self._set_status(str(_ve))
                self._settings_dialog_apply_refresh("Settings applied")
                if _editor_restart_changed:
                    self._show_message_box(
                        "The braille editor fix settings have changed. Restart QUILL "
                        "so every document uses the new setting; documents you open "
                        "before restarting may still use the previous one.",
                        "Restart to apply",
                        wx.ICON_INFORMATION | wx.OK,
                    )
                    self._announce("Restart QUILL to apply the braille editor fix change.")
                _dirty[0] = False
                _apply_btn.Enable(False)

            def _on_apply(_evt: object) -> None:
                _do_apply()

            _apply_btn.Bind(wx.EVT_BUTTON, _on_apply)

            def _build_page(idx: int) -> None:
                if idx in _built_pages or idx >= len(_page_build_fns):
                    return
                _built_pages.add(idx)
                _page_build_fns[idx]()
                # Pages build lazily, after show_modal_dialog's show-time
                # naming pass, so each new page needs its own pass or its
                # controls read as bare values on macOS (#1012). Guarded: a
                # naming failure must never break switching Settings pages.
                try:
                    ensure_accessible_names(dialog)
                except Exception:  # noqa: BLE001
                    pass

            if _page_build_fns:
                _build_page(0)

            def _on_page_changed(_evt: object) -> None:
                _build_page(notebook.GetSelection())
                # Ctrl+Tab from inside a page lands on the new page's first
                # control; but while ARROWING along the tab strip itself, focus
                # must stay on the tabs so the tab names can be browsed.
                if wx.Window.FindFocus() is not notebook:
                    focus_primary_control(dialog)

            notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, _on_page_changed)

            apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
            dialog.SetSize(wx.Size(720, 580))
            dialog.Layout()

            result = self._show_modal_dialog(dialog, "Settings")
            if result == wx.ID_OK:
                action["mode"] = "ok"
                collected = {key: reader() for key, reader in readers.items()}
                _ai_cb = _ai_refs.get("ai_enabled_cb")
                ai_value = bool(_ai_cb.GetValue()) if _ai_cb is not None else None
                _ext_cb = _ai_refs.get("ext_master_cb")
                ext_master_value = bool(_ext_cb.GetValue()) if _ext_cb is not None else None
                _nf = _ai_refs.get("ext_name_field")
                _cf = _ai_refs.get("ext_command_field")
                _ef = _ai_refs.get("ext_engine_enabled_cb")
                if _nf is not None and _cf is not None:
                    ext_engine_spec = (
                        str(_nf.GetValue()),
                        str(_cf.GetValue()),
                        bool(_ef.GetValue()) if _ef is not None else False,
                    )
                _read_data_location = _data_location_refs.get("read")
                if _read_data_location is not None:
                    data_location_choice = _read_data_location()

        mode = action["mode"]
        if mode == "import":
            imported = action["imported"]
            if isinstance(imported, Settings):
                self.settings = imported
                self._settings_dialog_apply_refresh("Imported settings")
            return
        if mode == "reset":
            self.settings = registry.reset_all()
            self._settings_dialog_apply_refresh("Reset settings to factory defaults")
            return
        if mode != "ok":
            self._set_status("Settings cancelled")
            return

        updated = self.settings
        for key, value in collected.items():
            updated = registry.set_value(updated, key, value)
        self.settings = updated
        if ai_value is not None:
            save_ai_enabled(ai_value)
            self._sync_ai_enabled_menu(ai_value)
        if ext_master_value is not None:
            from quill.core.ai.external_engine import (
                configure_engine,
                set_external_engines_enabled,
            )

            set_external_engines_enabled(ext_master_value)
            if ext_engine_spec is not None and ext_engine_spec[0].strip():
                try:
                    configure_engine(
                        ext_engine_spec[0],
                        ext_engine_spec[1],
                        enabled=ext_engine_spec[2],
                    )
                except ValueError as error:
                    self._set_status(str(error))
        if data_location_choice is not None:
            chosen_mode, chosen_custom = data_location_choice
            resolve_target_fn = _data_location_refs.get("resolve_target")
            current_dir = _data_location_refs.get("current")
            if resolve_target_fn is not None and current_dir is not None:
                custom_arg = (
                    Path(chosen_custom) if chosen_mode == "custom" and chosen_custom else None
                )
                try:
                    target_dir = resolve_target_fn(chosen_mode, custom_arg)
                except ValueError as error:
                    self._set_status(str(error))
                else:
                    if target_dir != current_dir:
                        from quill.core.data_location import request_data_location_change

                        try:
                            request_data_location_change(chosen_mode, custom_arg)
                        except (ValueError, OSError) as error:
                            self._set_status(f"Could not change data location: {error}")
                        else:
                            self._confirm_restart_for_data_location(target_dir)
        self._settings_dialog_apply_refresh("Updated settings")

    def open_ai_preferences(self) -> None:
        from quill.ui.assistant_tools import AssistantConnectionDialog

        dialog = AssistantConnectionDialog(self.frame)
        if dialog.show_modal():
            self._set_ai_menu_status_badge(
                dialog.last_verification_ok,
                dialog.last_verification_message,
            )
            detail = self._compact_ai_status_detail(
                self._plain_language_ai_status_detail(dialog.last_verification_message)
            )
            if dialog.last_verification_ok:
                self._set_status(f"Updated AI connection settings. Ready. {detail}")
            else:
                self._set_status(f"Updated AI connection settings. Needs attention. {detail}")
        else:
            self._set_status("AI connection settings cancelled")

    def _confirm_show_editor_border(self) -> bool:
        """Warning gate before the braille hide-border fix is turned off.

        The visible border pushes braille output out of cell 1 (part of the
        #616 fix), so unchecking the Braille-tab box must be a deliberate,
        informed act — announced at decision time, not discovered at the
        display.
        """
        wx = self._wx
        plain = (
            "Warning: showing the editor border breaks braille cell alignment - "
            "text will no longer start at cell 1 on a braille display.\n\n"
            "Leave the border hidden unless you do not use a braille display.\n\n"
            "Show the editor border anyway?"
        )
        dialog = wx.MessageDialog(
            self.frame,
            plain,
            "Braille cell alignment",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
        )
        if hasattr(dialog, "SetYesNoLabels"):
            dialog.SetYesNoLabels("Show border (breaks braille alignment)", "Keep it hidden")
        try:
            result = self._show_modal_dialog(dialog, "Braille cell alignment")
        finally:
            dialog.Destroy()
        return result == wx.ID_YES
