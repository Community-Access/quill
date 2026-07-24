"""User-definable system-wide hotkeys (mixin on ``MainFrame``).

Generalizes the single hardcoded sticky-note ``RegisterHotKey`` into a
table the user configures (Tools > Global Hotkeys...), with one hard
safety rule: only commands on :data:`GLOBAL_HOTKEY_SAFE_COMMANDS` can ever
go global. The allowlist is curated for the low-risk, works-without-the-
window cases -- media transport, capture/browse notes, a compose dialog --
and deliberately excludes anything destructive or document-editing:
pressing a global hotkey from another app must never change a document you
cannot see.

Dispatch goes through ``CommandRegistry.run``, so the remote feature kill
switch and feature gating apply to global presses exactly as they do to
menu items and the palette. Commands whose UI needs the window (a dialog)
restore the frame first; pure transport commands act in place, and every
outcome speaks through the announcement engine, so a press from another
app still tells you what happened.

Windows-only by platform reality: ``RegisterHotKey`` has no macOS
equivalent here (same limitation the sticky-note hotkey always had).
"""

from __future__ import annotations

#: (command_id, human label, needs_window). needs_window commands restore
#: the QUILL window before running (they open a dialog); transport commands
#: run wherever you are. THE SAFETY BOUNDARY: nothing off this list can be
#: bound globally, whatever the settings file says.
GLOBAL_HOTKEY_SAFE_COMMANDS: tuple[tuple[str, str, bool], ...] = (
    ("view.toggle_window_to_tray", "Show/Hide QUILL to the tray", False),
    ("tools.sticky_note_capture", "New Sticky Note", True),
    ("notes.sticky_browser", "Sticky Notes Browser", True),
    ("tools.post_to_mastodon", "Post to Mastodon (opens compose; never auto-sends)", True),
    ("radio.play_pause", "Radio: Play/Pause", False),
    ("radio.stop", "Radio: Stop", False),
    ("radio.mute_toggle", "Radio: Mute/Unmute", False),
    ("radio.volume_up", "Radio: Volume Up", False),
    ("radio.volume_down", "Radio: Volume Down", False),
    ("podcasts.play_pause", "Podcasts: Play/Pause", False),
    ("podcasts.stop", "Podcasts: Stop", False),
)

_SAFE_IDS = {command_id for command_id, _label, _needs in GLOBAL_HOTKEY_SAFE_COMMANDS}
_NEEDS_WINDOW = {command_id for command_id, _label, needs in GLOBAL_HOTKEY_SAFE_COMMANDS if needs}


class GlobalHotkeysMixin:
    """Registration, dispatch, and the two new dialogs' entry points."""

    # -- registration -----------------------------------------------------

    def _global_hotkey_bindings(self) -> dict[str, str]:
        """command_id -> binding, allowlist-filtered. The legacy sticky-note
        keymap binding keeps working unless the new table overrides it."""
        configured = dict(getattr(self.settings, "global_hotkeys", {}) or {})
        bindings = {
            command_id: str(binding).strip()
            for command_id, binding in configured.items()
            if command_id in _SAFE_IDS and str(binding).strip()
        }
        if "tools.sticky_note_capture" not in bindings:
            legacy = self._binding_for("tools.sticky_note_capture")
            if legacy and self._parse_keybinding(legacy) is not None:
                bindings["tools.sticky_note_capture"] = legacy
        # A unique default so show/hide-to-tray works out of the box, matching
        # the standalone apps (Radio Ctrl+Alt+Shift+R, Weather ...+W). The user
        # can rebind or clear it in Tools > Global Hotkeys.
        if "view.toggle_window_to_tray" not in bindings:
            bindings["view.toggle_window_to_tray"] = "Ctrl+Alt+Shift+Q"
        return bindings

    def _global_hotkey_wx_id(self, command_id: str) -> int:
        table = getattr(self, "_global_hotkey_ids", None)
        if table is None:
            table = {}
            self._global_hotkey_ids = table
        if command_id not in table:
            table[command_id] = int(self._wx.NewIdRef())
        return table[command_id]

    def _reload_global_hotkeys(self) -> None:
        if self._safe_mode:
            return
        self._unregister_global_hotkeys()
        if not hasattr(self.frame, "RegisterHotKey"):
            # RegisterHotKey is Windows-only; the in-app commands and QUILL-key
            # chords still work everywhere.
            import sys as _sys

            if _sys.platform == "darwin" and self._global_hotkey_bindings():
                self._set_status(
                    "System-wide hotkeys are not available on macOS; the same "
                    "commands still work from the menus and the command palette."
                )
            return
        self._global_hotkey_map: dict[int, str] = {}
        failures: list[str] = []
        for command_id, binding in self._global_hotkey_bindings().items():
            parsed = self._parse_keybinding(binding)
            if parsed is None:
                continue
            flags, key_code = parsed
            hotkey_id = self._global_hotkey_wx_id(command_id)
            try:
                registered = self.frame.RegisterHotKey(hotkey_id, flags, key_code)
            except Exception:  # noqa: BLE001 - a hotkey failure must not break startup
                registered = False
            if registered:
                self._global_hotkey_map[hotkey_id] = command_id
            else:
                failures.append(f"{binding} ({command_id})")
        if failures:
            # Almost always: another app already owns that combination.
            self._set_status(
                "Global hotkey(s) already in use by another app: " + ", ".join(failures)
            )

    def _unregister_global_hotkeys(self) -> None:
        if not hasattr(self.frame, "UnregisterHotKey"):
            return
        for hotkey_id in getattr(self, "_global_hotkey_ids", {}).values():
            try:
                self.frame.UnregisterHotKey(hotkey_id)
            except Exception:  # noqa: BLE001 - best-effort teardown
                pass
        self._global_hotkey_map = {}

    # -- dispatch ---------------------------------------------------------------

    def _on_global_hotkey(self, event: object) -> None:
        command_id = getattr(self, "_global_hotkey_map", {}).get(event.GetId())
        if command_id is None:
            event.Skip()
            return
        if command_id in _NEEDS_WINDOW:
            self._restore_from_tray()
        try:
            self.commands.run(command_id)
        except Exception:  # noqa: BLE001 - a global press must never crash the app
            self._announce("That global hotkey's command could not run.")

    # -- the two dialogs ------------------------------------------------------------

    def open_sticky_notes_browser(self) -> None:
        """Search/arrow/preview/edit sticky notes (globally hotkey-able)."""
        from quill.ui.sticky_notes_browser import StickyNotesBrowserDialog

        dialog = StickyNotesBrowserDialog(
            self.frame,
            on_edit=self._edit_sticky_note_by_id,
            announce_cb=self._announce,
        )
        dialog.show()

    def _edit_sticky_note_by_id(self, note_id: str) -> None:
        from quill.core.sticky_notes import get_sticky_note, save_sticky_note
        from quill.ui.sticky_notes import StickyNoteEditorDialog

        note = get_sticky_note(note_id)
        if note is None:
            self._announce("That note no longer exists.")
            return
        editor = StickyNoteEditorDialog(self.frame, note=note)
        body = editor.show_modal_and_get_body()
        if body is None:
            return
        save_sticky_note(body, note_id=note_id)
        self._announce("Note saved")

    def open_global_hotkeys_manager(self) -> None:
        from quill.core.settings import save_settings
        from quill.ui.global_hotkeys_dialog import GlobalHotkeysDialog

        dialog = GlobalHotkeysDialog(
            self.frame,
            commands=GLOBAL_HOTKEY_SAFE_COMMANDS,
            current=dict(getattr(self.settings, "global_hotkeys", {}) or {}),
            show_modal_fn=self._show_modal_dialog,
            announce_cb=self._announce,
        )
        updated = dialog.show()
        if updated is None:
            return
        self.settings.global_hotkeys = updated
        save_settings(self.settings)
        self._reload_global_hotkeys()
        self._announce("Global hotkeys saved and active")

    def toggle_window_to_tray(self) -> None:
        """Hide QUILL to the tray if it is showing, or bring it back if it is
        hidden -- the show/hide global-hotkey action. Restoring uses the same
        path as the tray icon so state stays consistent."""
        if self.frame.IsShown() and not self.frame.IsIconized():
            self.send_to_tray()
        else:
            self._restore_from_tray()
            self._announce("Quill shown")

    def _register_global_hotkey_commands(self) -> None:
        self.commands.try_register(
            "view.toggle_window_to_tray",
            "Show/Hide Quill to the Tray",
            self.toggle_window_to_tray,
            self._binding_for("view.toggle_window_to_tray"),
            feature_id="core.app",
        )
        self.commands.try_register(
            "notes.sticky_browser",
            "Sticky Notes Browser...",
            self.open_sticky_notes_browser,
            self._binding_for("notes.sticky_browser"),
            feature_id="core.notes",
        )
        self.commands.try_register(
            "tools.global_hotkeys",
            "Global Hotkeys...",
            self.open_global_hotkeys_manager,
            self._binding_for("tools.global_hotkeys"),
            feature_id="core.app",
        )
