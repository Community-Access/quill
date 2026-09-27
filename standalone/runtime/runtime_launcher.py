"""Entry point for the shared QuillVille Runtime bundle.

The shared runtime is ONE PyInstaller onedir (CPython + wxPython + the shared
``quill`` and ``quill_social`` packages) reused by every QuillVille app. Each
app is a thin launcher that runs this bundle's ``QuillVilleRuntime.exe`` with
the app's own entry module, exactly like ``python -m <module>``:

    QuillVilleRuntime.exe -m quill.apps.radio
    QuillVilleRuntime.exe -m quill.apps.podcasts
    QuillVilleRuntime.exe -m quill_social

So one Python install serves them all; installing a second app reuses this
runtime instead of shipping another copy (see the installer program spec).

**A windowed process has no console** (2026-09-27). PyInstaller's windowed
bootloader leaves ``sys.stdout`` and ``sys.stderr`` as ``None``, so the first
thing anywhere in the process that writes to either -- this file's own usage
message included -- raised "'NoneType' object has no attribute 'write'" and
PyInstaller's "Unhandled exception in script" box replaced the app. A listener
reported exactly that on a fresh install. Both streams now point at os.devnull
before anything runs, an unhandled exception is written to a crash file the
listener can send to support, and a launch with no module is explained in a
message box instead of a traceback.
"""

from __future__ import annotations

import os
import runpy
import sys
import traceback
from datetime import datetime

_USAGE = (
    "QuillVilleRuntime.exe is the shared engine the QuillVille apps run on; it "
    "is not an app of its own. Start Quill Radio, QUILL Lite or another app "
    "from its own shortcut in the Start menu."
)


def _ensure_streams() -> None:
    """Give a windowed process somewhere harmless to write."""
    for name in ("stdout", "stderr"):
        if getattr(sys, name, None) is None:
            setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))  # noqa: SIM115


def _crash_file() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    folder = os.path.join(base, "QuillVille", "Runtime", "crash-reports")
    os.makedirs(folder, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return os.path.join(folder, f"crash-{stamp}.txt")


def _record_crash(module: str) -> str:
    """Write the traceback where support can ask for it. Returns the path, or ""."""
    try:
        path = _crash_file()
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(f"module: {module}\nargv: {sys.argv!r}\n\n")
            handle.write(traceback.format_exc())
        return path
    except OSError:
        return ""


def _tell(text: str, title: str = "QuillVille Runtime") -> None:
    """A message box on Windows (there is no console to print to); else stderr."""
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(None, text, title, 0x40)  # MB_ICONINFORMATION
            return
        except Exception:  # noqa: BLE001 - fall through to the stream
            pass
    sys.stderr.write(text + "\n")


def _looks_like_module(text: str) -> bool:
    return (
        bool(text)
        and not text.startswith("-")
        and all(part.isidentifier() for part in text.split("."))
    )


def main() -> int:
    _ensure_streams()
    argv = sys.argv[1:]
    if len(argv) >= 2 and argv[0] == "-m":
        module, rest = argv[1], argv[2:]
    elif argv and _looks_like_module(argv[0]):
        # A relaunch built from ``sys.argv`` arrives as "<module> args..." --
        # run_module below reshapes argv that way -- so honour it rather than
        # refusing a restart the app asked for.
        module, rest = argv[0], argv[1:]
    else:
        _tell(_USAGE)
        return 2
    # Started without an app launcher -- a taskbar pin Windows made from the
    # running process targets this exe directly -- nothing exported the app
    # root, and every "bundled beside the runtime" lookup (libmpv, ffmpeg)
    # missed. The launcher sets it to this same folder, so default to that.
    if getattr(sys, "frozen", False):
        os.environ.setdefault("QUILL_APP_ROOT", os.path.dirname(os.path.abspath(sys.executable)))
    # Re-shape argv so the target module sees itself as __main__ with its own
    # arguments, just as `python -m module ...` would.
    sys.argv = [module, *rest]
    try:
        runpy.run_module(module, run_name="__main__", alter_sys=True)
    except SystemExit:
        raise
    except BaseException:
        path = _record_crash(module)
        where = f"\n\nDetails were saved to:\n{path}" if path else ""
        _tell(
            "The app stopped because of an unexpected error. Please send the details "
            "to support@community-access.org (Help > Get Help from Support, "
            f"Ctrl+Alt+F2, once it opens again).{where}",
            title="QuillVille app error",
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
