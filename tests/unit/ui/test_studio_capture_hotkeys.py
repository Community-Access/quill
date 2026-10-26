"""Studio reuses global registration without taking another app's default keys."""

from types import SimpleNamespace

from quill.apps.studio_capture_hotkeys import StudioCaptureHotkeysMixin


class Host(StudioCaptureHotkeysMixin):
    def __init__(self, bindings, succeeds=True):
        self._safe_mode = False
        self.settings = SimpleNamespace(global_hotkeys=bindings)
        self.messages = []
        self.registered = []
        self.frame = SimpleNamespace(
            RegisterHotKey=lambda *args: self.registered.append(args) is None and succeeds,
            UnregisterHotKey=lambda _key: True,
        )
        self._wx = SimpleNamespace(NewIdRef=lambda: 100 + len(self.registered))

    def _parse_keybinding(self, binding):
        return (7, ord("S"))

    def _set_status(self, message):
        self.messages.append(message)


def test_no_global_capture_is_registered_by_default():
    host = Host({})
    host._reload_global_hotkeys()
    assert not host.registered


def test_only_capture_commands_can_be_bound():
    host = Host({
        "studio.capture_active": "Ctrl+Alt+S",
        "file.save": "Ctrl+S",
        "view.toggle_window_to_tray": "Ctrl+Alt+Shift+Q",
    })
    assert host._global_hotkey_bindings() == {"studio.capture_active": "Ctrl+Alt+S"}


def test_collision_is_reported_and_not_treated_as_registered():
    host = Host({"studio.capture_desktop": "Ctrl+Alt+S"}, succeeds=False)
    host._reload_global_hotkeys()
    assert not host._global_hotkey_map
    assert "already in use" in host.messages[-1]


def test_successful_registration_dispatches_without_restoring_studio():
    host = Host({"studio.capture_active": "Ctrl+Alt+S"})
    host._reload_global_hotkeys()
    calls = []
    host.commands = SimpleNamespace(run=lambda command: calls.append(command))
    hotkey_id = next(iter(host._global_hotkey_map))
    host._on_global_hotkey(SimpleNamespace(GetId=lambda: hotkey_id))
    assert calls == ["studio.capture_active"]


def test_safe_mode_registers_nothing():
    host = Host({"studio.capture_active": "Ctrl+Alt+S"})
    host._safe_mode = True
    host._reload_global_hotkeys()
    assert not host.registered
