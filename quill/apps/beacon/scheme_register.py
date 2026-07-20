"""OS registration for the ``quillsync://`` custom URL scheme (PRD 45.5).

The app already handles a ``quillsync://verify?...`` link passed as ``argv`` (see
``quill.apps.beacon.app.run``). What was missing was telling the OS to launch the app
when such a link is activated. This module registers and unregisters the scheme
per platform:

- **Windows**: writes ``HKCU\\Software\\Classes\\quillsync`` (URL Protocol) and a
  ``shell\\open\\command`` that runs the app with the URL as ``%1``. HKCU needs
  no admin rights.
- **Linux**: writes a ``.desktop`` handler under
  ``~/.local/share/applications`` and sets it as the default for the
  ``x-scheme-handler/quillsync`` mime type (best-effort ``xdg-mime``).
- **macOS**: registration is done via the app bundle ``Info.plist``
  (``CFBundleURLTypes``) at build time; there is no reliable runtime path, so
  this module returns a note instead of pretending to register.

This is installer-adjacent code: it ships in the repo so an installer, the user,
or a setup wizard can call it. It never runs at app startup by default (that
would be a surprising system change). Every function is fail-safe: it returns a
JSON-able dict and never raises.

CLI::

    python -m quill.apps.beacon.scheme_register register [--command "..."]
    python -m quill.apps.beacon.scheme_register unregister
    python -m quill.apps.beacon.scheme_register status
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

SCHEME = "quillsync"


def default_command() -> str:
    """Return the default launch command with a ``%1`` placeholder for the URL.

    Frozen build: the executable itself. Source: the Python interpreter plus the
    repo ``launcher.py``. Either can be overridden with an explicit ``--command``.
    """
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" "%1"'
    # Source: python <repo>/launcher.py "%1".
    here = Path(__file__).resolve().parent.parent  # repo root
    launcher = here / "launcher.py"
    if launcher.exists():
        return f'"{sys.executable}" "{launcher}" "%1"'
    # Last resort: run the package's gui entry by module path.
    return f'"{sys.executable}" "{here / "launcher.py"}" "%1"'


# -- Windows -----------------------------------------------------------------


def _win_register(command: str) -> dict:
    import winreg  # local import so tests can inject a fake via sys.modules

    root = winreg.HKEY_CURRENT_USER
    base = f"Software\\Classes\\{SCHEME}"
    try:
        with winreg.CreateKeyEx(root, base, 0, winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
        with winreg.CreateKeyEx(root, base + "\\shell\\open\\command", 0, winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key, None, 0, winreg.REG_SZ, command)
    except OSError as exc:
        return {"error": f"registry write failed: {exc}"}
    return {"ok": True, "platform": "windows", "key": f"HKCU\\{base}", "command": command}


def _win_delete_tree(root, path: str, winreg) -> None:
    """Delete a registry key and all its subkeys (DeleteKey is leaf-only)."""
    try:
        with winreg.OpenKeyEx(root, path, 0, winreg.KEY_READ) as key:
            while True:
                try:
                    sub = winreg.EnumKey(key, 0)
                except OSError:
                    break
                _win_delete_tree(root, path + "\\" + sub, winreg)
        winreg.DeleteKey(root, path)
    except FileNotFoundError:
        pass


def _win_unregister() -> dict:
    import winreg

    root = winreg.HKEY_CURRENT_USER
    base = f"Software\\Classes\\{SCHEME}"
    try:
        _win_delete_tree(root, base, winreg)
    except OSError as exc:
        return {"error": f"registry delete failed: {exc}"}
    return {"ok": True, "platform": "windows", "key": f"HKCU\\{base}"}


def _win_status() -> dict:
    import winreg

    root = winreg.HKEY_CURRENT_USER
    base = f"Software\\Classes\\{SCHEME}"
    cmd_path = base + "\\shell\\open\\command"
    try:
        with winreg.OpenKeyEx(root, cmd_path, 0, winreg.KEY_READ) as key:
            value, _type = winreg.QueryValueEx(key, None)
        return {"registered": True, "platform": "windows", "command": value}
    except FileNotFoundError:
        return {"registered": False, "platform": "windows"}


# -- Linux -------------------------------------------------------------------


def _linux_desktop_path() -> Path:
    return Path(os.path.expanduser("~/.local/share/applications/quillsync-handler.desktop"))


def _linux_register(command: str) -> dict:
    path = _linux_desktop_path()
    # Use %u on Linux (the URL); accept %1 too.
    exec_line = command.replace("%1", "%u")
    content = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=QuillBeacon\n"
        "Comment=QuillBeacon quillsync:// handler\n"
        f"Exec={exec_line}\n"
        "Terminal=false\n"
        "NoDisplay=true\n"
        "MimeType=x-scheme-handler/quillsync;\n"
    )
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except OSError as exc:
        return {"error": f"desktop file write failed: {exc}"}
    # Best-effort: set as default handler.
    import subprocess

    try:
        subprocess.run(
            ["xdg-mime", "default", "quillsync-handler.desktop", "x-scheme-handler/quillsync"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass  # xdg-mime not present; the .desktop file still exists
    return {"ok": True, "platform": "linux", "path": str(path), "command": exec_line}


def _linux_unregister() -> dict:
    path = _linux_desktop_path()
    try:
        if path.exists():
            path.unlink()
        else:
            return {"error": "not registered"}
    except OSError as exc:
        return {"error": f"desktop file remove failed: {exc}"}
    return {"ok": True, "platform": "linux", "path": str(path)}


def _linux_status() -> dict:
    path = _linux_desktop_path()
    return {"registered": path.exists(), "platform": "linux", "path": str(path)}


# -- macOS -------------------------------------------------------------------


def _macos_note() -> dict:
    return {
        "error": "macOS scheme registration is done via the app bundle "
        "Info.plist (CFBundleURLTypes) at build time; there is no "
        "reliable runtime registration. Add an entry for the "
        "quillsync URL scheme to the bundle's Info.plist.",
        "platform": "macos",
    }


# -- public API --------------------------------------------------------------


def register(command: str | None = None) -> dict:
    """Register the quillsync:// scheme on the current platform."""
    cmd = command or default_command()
    if sys.platform.startswith("win"):
        return _win_register(cmd)
    if sys.platform.startswith("linux"):
        return _linux_register(cmd)
    if sys.platform == "darwin":
        return _macos_note()
    return {"error": f"unsupported platform: {sys.platform}"}


def unregister() -> dict:
    """Remove the quillsync:// scheme registration."""
    if sys.platform.startswith("win"):
        return _win_unregister()
    if sys.platform.startswith("linux"):
        return _linux_unregister()
    if sys.platform == "darwin":
        return _macos_note()
    return {"error": f"unsupported platform: {sys.platform}"}


def status() -> dict:
    """Report whether the scheme is registered on the current platform."""
    if sys.platform.startswith("win"):
        return _win_status()
    if sys.platform.startswith("linux"):
        return _linux_status()
    if sys.platform == "darwin":
        return {
            "registered": False,
            "platform": "macos",
            "note": "checked via the app bundle Info.plist at build time",
        }
    return {"registered": False, "error": f"unsupported platform: {sys.platform}"}


# -- CLI ---------------------------------------------------------------------


def _cli(argv: list[str]) -> int:
    args = argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    action = args[0]
    command = None
    if "--command" in args:
        i = args.index("--command")
        if i + 1 < len(args):
            command = args[i + 1]
    if action == "register":
        print(register(command))
        return 0
    if action == "unregister":
        print(unregister())
        return 0
    if action == "status":
        print(status())
        return 0
    print(f"unknown action: {action}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv))
