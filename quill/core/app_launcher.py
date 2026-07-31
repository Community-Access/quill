"""Launch a sibling QUILL app in its own window and process.

QUILL, Quill Radio, and Quill Weather are separate apps that can reach each
other: Radio can open Weather, Weather can open Radio, and QUILL can open either
-- each in its own window, with its own system-tray icon. Because every app is a
single-instance (``core.ipc``), launching one that is already running simply
brings it to the front instead of opening a second copy.

``build_launch_argv`` is the pure, tested piece: from source it runs
``python -m quill.apps.<app>``; a frozen build runs the sibling's own ``.exe``
sitting next to the current one (and reports it cannot when that exe is not
installed, so the caller can say so instead of failing silently).
``launch_app`` is the thin, best-effort spawn -- detached so the child outlives
the launcher, and never raising.
"""

from __future__ import annotations

import sys
from pathlib import Path

#: app key -> (module for ``-m`` from source, candidate frozen exe basenames).
_APPS: dict[str, tuple[str, tuple[str, ...]]] = {
    "quill": ("quill", ("QUILL.exe", "Quill.exe", "quill.exe")),
    "radio": ("quill.apps.radio", ("QuillRadio.exe", "Quill Radio.exe")),
    "weather": ("quill.apps.weather", ("QuillWeather.exe", "Quill Weather.exe")),
    "cast": ("quill.apps.podcasts", ("QuillCast.exe", "QUILLCast.exe", "Quill Cast.exe")),
    "studio": ("quill.apps.studio", ("QuillStudio.exe", "Quill Studio.exe")),
    "converter": (
        "quill.apps.converter",
        ("QuillConverter.exe", "Quill Converter.exe"),
    ),
}

#: app key -> the folder name each app's portable bundle unpacks to. Portable
#: siblings live as adjacent folders under a shared parent (…/QuillRadio/,
#: …/QuillWeather/), so a sibling's exe is found one level over, not only in the
#: current app's own folder. Installed builds usually co-locate, so both the
#: same-folder and the adjacent-folder layouts are searched.
_PORTABLE_DIRNAMES: dict[str, str] = {
    "quill": "QUILL",
    "radio": "QuillRadio",
    "weather": "QuillWeather",
    "cast": "QuillCast",
    "studio": "QuillStudio",
    "converter": "QuillConverter",
}


def portable_sibling_dirname(app_key: str) -> str | None:
    """The adjacent folder name a portable ``app_key`` bundle unpacks to."""
    return _PORTABLE_DIRNAMES.get(app_key)


#: Friendly names, for menu labels and announcements.
APP_NAMES: dict[str, str] = {
    "quill": "QUILL",
    "radio": "Quill Radio",
    "weather": "Quill Weather",
    "cast": "Quill Cast",
    "studio": "Audio Studio",
    "converter": "Quill Converter",
}


def app_name(app_key: str) -> str:
    return APP_NAMES.get(app_key, app_key)


def build_launch_argv(app_key: str) -> list[str] | None:
    """The argv that launches sibling ``app_key`` in its own process, or None
    when it cannot be launched (unknown key, or a frozen build whose sibling
    ``.exe`` is not installed next to this one)."""
    entry = _APPS.get(app_key)
    if entry is None:
        return None
    module, exe_names = entry
    if getattr(sys, "frozen", False):
        here = Path(sys.executable).resolve().parent
        # 1) Same folder as the current app (co-located / shared-folder install).
        # 2) An adjacent folder under the shared parent (the portable layout,
        #    …/QuillRadio/ next to …/QuillWeather/).
        search_dirs = [here]
        sibling_dir = _PORTABLE_DIRNAMES.get(app_key)
        if sibling_dir:
            search_dirs.append(here.parent / sibling_dir)
        for folder in search_dirs:
            for name in exe_names:
                candidate = folder / name
                if candidate.exists():
                    return [str(candidate)]
        return None  # sibling app is not installed alongside this one
    return [sys.executable, "-m", module]


def launch_app(app_key: str, *, extra_args: tuple[str, ...] = ()) -> bool:
    """Spawn sibling ``app_key`` detached (best-effort). True if a launch was
    started, False when it could not be (see :func:`build_launch_argv`). Never
    raises -- a failed launch must not disturb the app the user is in."""
    argv = build_launch_argv(app_key)
    if argv is None:
        return False
    argv = [*argv, *extra_args]
    import subprocess

    try:
        creationflags = 0
        if sys.platform.startswith("win"):
            # Detach so the child keeps running if the launcher exits, and give
            # it its own process group (no shared console window).
            creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
                subprocess, "CREATE_NEW_PROCESS_GROUP", 0
            )
        subprocess.Popen(argv, close_fds=True, creationflags=creationflags)  # noqa: S603
        return True
    except Exception:  # noqa: BLE001 - a launch failure never disrupts the caller
        return False
