"""Tests for quillsync:// scheme registration (PRD 45.5).

Uses a fake in-memory winreg so no real registry is touched. Linux/macOS paths
are exercised by patching sys.platform and the filesystem.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quill.apps.beacon import scheme_register

# -- fake winreg -------------------------------------------------------------


class _FakeKey:
    def __init__(self, path):
        self.path = path

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeWinreg:
    HKEY_CURRENT_USER = "HKCU"
    KEY_WRITE = 0
    KEY_READ = 0
    REG_SZ = 1
    tree: dict[str, dict] = {}

    @classmethod
    def reset(cls):
        cls.tree = {}

    @staticmethod
    def CreateKeyEx(root, subkey, reserved, access):
        # Create the full path and all intermediate segments.
        parts = subkey.split("\\")
        for i in range(1, len(parts) + 1):
            p = "\\".join(parts[:i])
            FakeWinreg.tree.setdefault(p, {})
        return _FakeKey(subkey)

    @staticmethod
    def SetValueEx(key, name, reserved, type_, value):
        FakeWinreg.tree[key.path][name if name is not None else ""] = value

    @staticmethod
    def OpenKeyEx(root, subkey, reserved, access):
        if subkey not in FakeWinreg.tree:
            raise FileNotFoundError(subkey)
        return _FakeKey(subkey)

    @staticmethod
    def QueryValueEx(key, name):
        name = name if name is not None else ""
        if name not in FakeWinreg.tree.get(key.path, {}):
            raise FileNotFoundError(name)
        return FakeWinreg.tree[key.path][name], FakeWinreg.REG_SZ

    @staticmethod
    def EnumKey(key, index):
        prefix = key.path + "\\" if key.path else ""
        children = []
        for p in FakeWinreg.tree:
            if p.startswith(prefix):
                rest = p[len(prefix) :]
                if rest and "\\" not in rest:
                    children.append(rest)
        children.sort()
        if index >= len(children):
            raise OSError("no more subkeys")
        return children[index]

    @staticmethod
    def DeleteKey(root, subkey):
        if subkey in FakeWinreg.tree:
            del FakeWinreg.tree[subkey]

    @staticmethod
    def CloseKey(key):
        pass


@pytest.fixture
def fake_winreg(monkeypatch):
    FakeWinreg.reset()
    monkeypatch.setitem(sys.modules, "winreg", FakeWinreg)
    monkeypatch.setattr(sys, "platform", "win32")
    yield


# -- default command ---------------------------------------------------------


def test_default_command_has_placeholder():
    cmd = scheme_register.default_command()
    assert "%1" in cmd


def test_default_command_frozen_uses_executable(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", "/x/QuillBeacon.exe", raising=False)
    assert scheme_register.default_command() == '"/x/QuillBeacon.exe" "%1"'


# -- Windows register / status / unregister ----------------------------------


def test_win_register_writes_command(fake_winreg):
    res = scheme_register.register('"C:\\app\\QuillBeacon.exe" "%1"')
    assert res["ok"], res
    assert res["platform"] == "windows"
    # The shell\open\command default value holds the launch command.
    with FakeWinreg.OpenKeyEx(
        FakeWinreg.HKEY_CURRENT_USER,
        "Software\\Classes\\quillsync\\shell\\open\\command",
        0,
        FakeWinreg.KEY_READ,
    ) as key:
        val, _t = FakeWinreg.QueryValueEx(key, None)
    assert val == '"C:\\app\\QuillBeacon.exe" "%1"'
    # URL Protocol marker is set on the scheme key.
    with FakeWinreg.OpenKeyEx(
        FakeWinreg.HKEY_CURRENT_USER, "Software\\Classes\\quillsync", 0, FakeWinreg.KEY_READ
    ) as key:
        FakeWinreg.QueryValueEx(key, "URL Protocol")


def test_win_status_reports_registered(fake_winreg):
    assert scheme_register.status()["registered"] is False
    scheme_register.register('"%1"')
    st = scheme_register.status()
    assert st["registered"] is True
    assert "%1" in st["command"]


def test_win_unregister_removes_keys(fake_winreg):
    scheme_register.register('"%1"')
    assert scheme_register.status()["registered"] is True
    res = scheme_register.unregister()
    assert res["ok"]
    assert scheme_register.status()["registered"] is False


def test_win_unregister_when_not_registered(fake_winreg):
    # Not registered -> unregister still returns ok (idempotent / fail-safe).
    res = scheme_register.unregister()
    assert res["ok"]


# -- Linux -------------------------------------------------------------------


def test_linux_register_writes_desktop_file(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "linux")
    apps = tmp_path / "applications"
    monkeypatch.setattr(
        scheme_register, "_linux_desktop_path", lambda: apps / "quillsync-handler.desktop"
    )
    res = scheme_register.register('"/usr/bin/quill-beacon" "%1"')
    assert res["ok"], res
    assert res["platform"] == "linux"
    content = (apps / "quillsync-handler.desktop").read_text()
    assert "x-scheme-handler/quillsync;" in content
    assert "%u" in content  # %1 translated to %u for Linux


def test_linux_status_and_unregister(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "linux")
    apps = tmp_path / "applications"
    monkeypatch.setattr(
        scheme_register, "_linux_desktop_path", lambda: apps / "quillsync-handler.desktop"
    )
    assert scheme_register.status()["registered"] is False
    scheme_register.register('"%1"')
    assert scheme_register.status()["registered"] is True
    assert scheme_register.unregister()["ok"]
    assert scheme_register.status()["registered"] is False
    # Second unregister is "not registered".
    assert "error" in scheme_register.unregister()


# -- macOS -------------------------------------------------------------------


def test_macos_returns_note(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    res = scheme_register.register()
    assert res["platform"] == "macos"
    assert "error" in res
    assert scheme_register.status()["platform"] == "macos"
