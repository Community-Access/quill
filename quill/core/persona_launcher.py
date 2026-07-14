"""Launch commands and shortcuts for Work Personas (#896).

``build_launch_argv`` is pure and platform-agnostic -- the thing under test.
``write_launch_shortcut`` is the one function that touches disk/COM, and it
degrades gracefully: a genuine Windows ``.lnk`` when ``pywin32`` is available,
a plain ``.bat`` launcher otherwise. Either way a persona is reachable without
QUILL already running, which is the actual requirement -- the file format is
an implementation detail.
"""

from __future__ import annotations

import sys
from pathlib import Path

__all__ = ["build_launch_argv", "write_launch_shortcut"]


def build_launch_argv(persona_name: str) -> list[str]:
    """The argv that launches QUILL directly into *persona_name*.

    Frozen builds (``quill.exe``) run ``sys.executable`` directly; running
    from source needs ``-m quill`` so Python resolves the package.
    """
    if getattr(sys, "frozen", False):
        return [sys.executable, "--persona", persona_name]
    return [sys.executable, "-m", "quill", "--persona", persona_name]


def _write_bat_shortcut(persona_name: str, target_dir: Path) -> Path:
    argv = build_launch_argv(persona_name)
    quoted = " ".join(f'"{part}"' if " " in part else part for part in argv)
    safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in persona_name).strip()
    path = target_dir / f"QUILL - {safe_name}.bat"
    path.write_text(f'@echo off\r\nstart "" {quoted}\r\n', encoding="utf-8")
    return path


def _write_command_shortcut(persona_name: str, target_dir: Path) -> Path:
    """Write a macOS-launchable ``.command`` file for *persona_name* (#38).

    Finder runs ``.command`` files in Terminal (unlike ``.sh``, which opens
    in a text editor), so a double-click launches the persona -- but only
    when the file has a shell shebang and the executable bit set.
    """
    import os

    argv = build_launch_argv(persona_name)
    quoted = " ".join(f'"{part}"' if " " in part else part for part in argv)
    safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in persona_name).strip()
    path = target_dir / f"QUILL - {safe_name}.command"
    path.write_text(f"#!/bin/sh\nexec {quoted}\n", encoding="utf-8")
    os.chmod(path, 0o755)
    return path


def write_launch_shortcut(persona_name: str, target_dir: Path) -> Path:
    """Write a launcher for *persona_name* into *target_dir*, returning its path.

    On macOS a double-clickable ``.command`` shell script (Finder runs it in
    Terminal). On Windows, tries a real ``.lnk`` (via ``pywin32``'s
    ``WScript.Shell`` COM object, the standard way to build one); any failure
    -- not on Windows, ``pywin32`` missing, COM unavailable -- falls back to a
    ``.bat`` file that runs the exact same command. Never raises: a persona is
    always left with *some* double-clickable launcher.
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    if sys.platform == "darwin":
        return _write_command_shortcut(persona_name, target_dir)
    try:
        import win32com.client  # type: ignore[import-untyped]

        argv = build_launch_argv(persona_name)
        safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in persona_name).strip()
        lnk_path = target_dir / f"QUILL - {safe_name}.lnk"
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(str(lnk_path))
        shortcut.TargetPath = argv[0]
        shortcut.Arguments = " ".join(f'"{part}"' for part in argv[1:])
        shortcut.Description = f"Launch QUILL with the {persona_name} persona"
        shortcut.Save()
        return lnk_path
    except Exception:  # noqa: BLE001 - any COM/pywin32 failure falls back to .bat
        return _write_bat_shortcut(persona_name, target_dir)
