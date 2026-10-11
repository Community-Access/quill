"""QUILL Cast's per-user Windows startup entry."""

from __future__ import annotations

import sys
from pathlib import Path

from quill.platform.windows import cast_startup


def test_launch_command_uses_cast_launcher_or_module(monkeypatch, tmp_path: Path) -> None:
    runtime = tmp_path / "Runtime" / "QuillVilleRuntime.exe"
    monkeypatch.setattr(sys, "executable", str(runtime))
    monkeypatch.delenv("QUILL_LAUNCHER_DIR", raising=False)
    assert cast_startup.launch_command() == f'"{runtime}" -m quill.apps.podcasts'

    launcher = tmp_path / cast_startup.LAUNCHER_NAME
    launcher.write_bytes(b"MZ")
    monkeypatch.setenv("QUILL_LAUNCHER_DIR", str(tmp_path))
    assert cast_startup.launch_command() == f'"{launcher}"'


def test_cast_has_a_distinct_startup_value_name() -> None:
    from quill.platform.windows import radio_startup
    from quill.platform.windows import startup as quill_startup

    names = {cast_startup._VALUE_NAME, radio_startup._VALUE_NAME, quill_startup._VALUE_NAME}
    assert len(names) == 3
    assert cast_startup._VALUE_NAME == "QuillCast"


def test_portable_copy_never_writes_the_run_key(monkeypatch, tmp_path: Path) -> None:
    class Registry:
        HKEY_CURRENT_USER = object()
        KEY_SET_VALUE = 2
        REG_SZ = 1

        def OpenKey(self, *_args):
            raise AssertionError("portable startup must not open the registry")

    monkeypatch.setattr(cast_startup, "winreg", Registry())
    monkeypatch.setattr(cast_startup.sys, "platform", "win32")
    monkeypatch.setattr("quill.core.paths.portable_bundle_root", lambda: tmp_path)

    cast_startup.set_launch_at_startup(True)

    assert cast_startup.is_launch_at_startup_enabled() is False
    assert cast_startup.PORTABLE_REFUSAL.startswith("A portable copy")


def test_installed_copy_writes_its_named_value(monkeypatch, tmp_path: Path) -> None:
    writes: list[tuple[object, ...]] = []

    class Key:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    class Registry:
        HKEY_CURRENT_USER = object()
        KEY_SET_VALUE = 2
        REG_SZ = 1

        @staticmethod
        def OpenKey(*_args):
            return Key()

        @staticmethod
        def SetValueEx(*args):
            writes.append(args)

    monkeypatch.setattr(cast_startup, "winreg", Registry())
    monkeypatch.setattr(cast_startup.sys, "platform", "win32")
    monkeypatch.setattr("quill.core.paths.portable_bundle_root", lambda: None)
    monkeypatch.setattr(
        cast_startup,
        "launch_command",
        lambda: f'"{tmp_path / "QuillCast.exe"}"',
    )

    cast_startup.set_launch_at_startup(True)

    assert len(writes) == 1
    assert writes[0][1:] == (
        cast_startup._VALUE_NAME,
        0,
        Registry.REG_SZ,
        f'"{tmp_path / "QuillCast.exe"}"',
    )
