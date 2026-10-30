"""Studio capture allowlist over QUILL's shared system-wide hotkey service."""

from __future__ import annotations

from quill.ui.main_frame_hotkeys import GlobalHotkeysMixin

SCREENSHOT_HOTKEY_COMMANDS = (
    ("studio.capture_active", "Studio: Screenshot the active window", False),
    ("studio.capture_desktop", "Studio: Screenshot the full desktop", False),
    ("studio.capture_selected", "Studio: Screenshot the last selected target", False),
    ("studio.cancel_capture", "Studio: Cancel pending screenshot", False),
)

#: Record a Demonstration (Studio PRD REC-013): opt-in with no defaults, since
#: focus is in the demonstrated program while recording and only a
#: system-wide key reaches Studio from there.
RECORDING_HOTKEY_COMMANDS = (
    ("studio.record_demo", "Studio: Record a demonstration, or stop and save", False),
    ("studio.record_pause", "Studio: Pause or resume the recording", False),
    ("studio.record_marker", "Studio: Add a recording marker", False),
    ("studio.record_mute", "Studio: Mute or unmute the microphone in the recording", False),
    ("studio.record_status", "Studio: Say the recording status", False),
    ("studio.record_emergency_stop", "Studio: Emergency stop and save", False),
    ("studio.broadcast_mute", "Studio: Mute everything public in the live broadcast", False),
    ("studio.broadcast_stop", "Studio: Stop the live broadcast", False),
)

CAPTURE_HOTKEY_COMMANDS = SCREENSHOT_HOTKEY_COMMANDS + RECORDING_HOTKEY_COMMANDS


class StudioCaptureHotkeysMixin(GlobalHotkeysMixin):
    def _init_capture_hotkeys(self):
        self.frame.Bind(self._wx.EVT_HOTKEY, self._on_global_hotkey)
        self._reload_global_hotkeys()

    def _global_hotkey_safe_commands(self):
        return CAPTURE_HOTKEY_COMMANDS

    def _global_hotkey_bindings(self):
        allowed = {entry[0] for entry in CAPTURE_HOTKEY_COMMANDS}
        # No inherited editor/show-hide default: every capture key is opt-in.
        return {
            key: value.strip()
            for key, value in self.settings.global_hotkeys.items()
            if key in allowed and isinstance(value, str) and value.strip()
        }

    def open_capture_hotkeys(self):
        from quill.core.settings import load_settings, save_settings
        from quill.ui.global_hotkeys_dialog import GlobalHotkeysDialog

        settings = load_settings()
        dialog = GlobalHotkeysDialog(
            self.frame,
            commands=CAPTURE_HOTKEY_COMMANDS,
            current=settings.global_hotkeys,
            show_modal_fn=self._show_modal_dialog,
            announce_cb=self._announce,
        )
        updated = dialog.show()
        if updated is None:
            return
        # Preserve unrelated apps' bindings, including changes made while open.
        fresh = load_settings()
        for command_id, _title, _needs_window in CAPTURE_HOTKEY_COMMANDS:
            fresh.global_hotkeys.pop(command_id, None)
            if updated.get(command_id):
                fresh.global_hotkeys[command_id] = updated[command_id]
        save_settings(fresh)
        self.settings = fresh
        self._reload_global_hotkeys()
        registered = set(getattr(self, "_global_hotkey_map", {}).values())
        missing = set(self._global_hotkey_bindings()) - registered
        if self._safe_mode:
            self._announce("Capture hotkeys saved; global hotkeys are disabled in Safe Mode.")
        elif missing:
            self._announce(
                "Capture hotkeys saved, but some could not register. "
                "Another app may own them. Review the status bar and choose other keys."
            )
        else:
            self._announce(f"Capture global hotkeys saved; {len(registered)} registered.")
