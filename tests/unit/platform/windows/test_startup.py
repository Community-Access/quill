"""Tests for the Windows autostart Run-key helper.

Never touches the real registry -- ``winreg`` is monkeypatched with an
in-memory fake, since writing a real ``Quill`` Run-key entry would actually
change what launches at the next login on whatever machine runs this suite.
"""

from __future__ import annotations

import pytest

import quill.platform.windows.startup as startup


class _FakeKeyHandle:
    def __init__(self, store: dict[str, str]) -> None:
        self._store = store

    def __enter__(self) -> _FakeKeyHandle:
        return self

    def __exit__(self, *args: object) -> None:
        return None


class _FakeWinreg:
    """A minimal in-memory stand-in for the pieces of ``winreg`` this module uses."""

    HKEY_CURRENT_USER = object()
    KEY_SET_VALUE = 0x0002
    REG_SZ = 1

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.opened_for_write = False

    def OpenKey(self, _hive: object, _path: str, *args: object) -> _FakeKeyHandle:
        if len(args) >= 2 and args[1] == self.KEY_SET_VALUE:
            self.opened_for_write = True
        return _FakeKeyHandle(self.store)

    def QueryValueEx(self, _key: _FakeKeyHandle, name: str) -> tuple[str, int]:
        if name not in self.store:
            raise FileNotFoundError(name)
        return self.store[name], self.REG_SZ

    def SetValueEx(
        self, _key: _FakeKeyHandle, name: str, _reserved: int, _kind: int, value: str
    ) -> None:
        self.store[name] = value

    def DeleteValue(self, _key: _FakeKeyHandle, name: str) -> None:
        if name not in self.store:
            raise FileNotFoundError(name)
        del self.store[name]


@pytest.fixture
def fake_winreg(monkeypatch: pytest.MonkeyPatch) -> _FakeWinreg:
    fake = _FakeWinreg()
    monkeypatch.setattr(startup, "winreg", fake)
    monkeypatch.setattr(startup.sys, "platform", "win32")
    return fake


def test_is_windows_false_when_winreg_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(startup, "winreg", None)
    assert startup.is_windows() is False


def test_is_windows_false_on_non_windows_platform(
    fake_winreg: _FakeWinreg, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(startup.sys, "platform", "darwin")
    assert startup.is_windows() is False


def test_is_windows_true_when_winreg_present_and_platform_is_win32(
    fake_winreg: _FakeWinreg,
) -> None:
    assert startup.is_windows() is True


def test_launch_command_quotes_executable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(startup.sys, "executable", r"C:\Program Files\Quill\quill.exe")
    assert startup.launch_command() == '"C:\\Program Files\\Quill\\quill.exe"'


def test_is_launch_at_startup_enabled_false_when_no_entry(fake_winreg: _FakeWinreg) -> None:
    assert startup.is_launch_at_startup_enabled() is False


def test_set_launch_at_startup_true_then_query_reports_enabled(fake_winreg: _FakeWinreg) -> None:
    startup.set_launch_at_startup(True)
    assert fake_winreg.opened_for_write is True
    assert "Quill" in fake_winreg.store
    assert startup.is_launch_at_startup_enabled() is True


def test_set_launch_at_startup_false_removes_entry(fake_winreg: _FakeWinreg) -> None:
    startup.set_launch_at_startup(True)
    startup.set_launch_at_startup(False)
    assert "Quill" not in fake_winreg.store
    assert startup.is_launch_at_startup_enabled() is False


def test_set_launch_at_startup_false_when_no_entry_is_a_noop(fake_winreg: _FakeWinreg) -> None:
    startup.set_launch_at_startup(False)  # no raise
    assert "Quill" not in fake_winreg.store


def test_set_launch_at_startup_is_a_noop_on_non_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(startup, "winreg", None)
    startup.set_launch_at_startup(True)  # no raise, nothing to assert on -- just must not crash


def test_set_launch_at_startup_swallows_registry_errors(fake_winreg: _FakeWinreg) -> None:
    def _boom(*_a: object, **_k: object) -> None:
        raise OSError("access denied")

    fake_winreg.OpenKey = _boom  # type: ignore[method-assign]
    startup.set_launch_at_startup(True)  # no raise
