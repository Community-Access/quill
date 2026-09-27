"""The command line that starts *this* app again.

Autostart entries, the scheduled-recording wake and the weather check all store
a command that Windows runs later, with none of this process's context. Since
the apps moved onto the shared QuillVille Runtime (2026-08-17) the running
executable is no longer the app: an installed Quill Radio is
``QuillVilleRuntime.exe -m quill.apps.radio``, started by its native launcher
(``QuillRadio.exe``). A command built from ``sys.executable`` alone therefore
named the *runtime* with no module -- which at every login showed the runtime's
"this is not an app" message (before PR #1575, a crash) instead of the app.

The answer, in order of preference:

1. **The app's native launcher**, when this process was started by one: the
   launcher exports ``QUILL_LAUNCHER_DIR``, and its exe survives a runtime
   upgrade that moves the runtime to a new versioned folder.
2. ``"<executable>" -m <module>`` when the executable is an *interpreter* --
   the shared runtime, or a ``python``/``pythonw`` (a dev run or a portable
   bundle) -- because then the executable alone does not name the app.
3. ``"<executable>"`` for a genuine app exe (a onefile build, QUILL's own
   ``quill.exe``), which starts the app when run bare.

Pure: every input can be injected, so the whole decision is unit-testable.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

#: Executables that are an interpreter rather than an app: run bare they do
#: nothing a user wants. ``quill.exe`` is deliberately absent -- it is a stamped
#: pythonw whose sitecustomize starts QUILL on a bare launch.
GENERIC_INTERPRETERS = frozenset({"quillvilleruntime", "python", "pythonw"})


def is_generic_interpreter(executable: str) -> bool:
    """True when *executable* needs ``-m <module>`` to mean an app."""
    stem = Path(executable.strip().strip('"')).stem.lower() if executable else ""
    return stem in GENERIC_INTERPRETERS


def app_argv(
    module: str,
    launcher_name: str | None = None,
    *,
    args: Sequence[str] = (),
    executable: str | None = None,
    environ: Mapping[str, str] | None = None,
    exists: Callable[[Path], bool] | None = None,
) -> list[str]:
    """The argv that starts this app again (see the module docstring)."""
    env = os.environ if environ is None else environ
    exe = sys.executable if executable is None else executable
    is_file = exists if exists is not None else Path.is_file
    launcher_dir = (env.get("QUILL_LAUNCHER_DIR") or "").strip()
    if launcher_name and launcher_dir:
        candidate = Path(launcher_dir) / launcher_name
        try:
            found = bool(is_file(candidate))
        except OSError:
            found = False
        if found:
            return [str(candidate), *args]
    if is_generic_interpreter(exe):
        return [exe, "-m", module, *args]
    return [exe, *args]


def to_command_line(argv: Sequence[str]) -> str:
    """Join *argv* for the Run key or Task Scheduler: the executable is always
    quoted (a path under Program Files has spaces), the rest as Windows
    parses them."""
    if not argv:
        return ""
    head = f'"{argv[0]}"'
    rest = subprocess.list2cmdline(list(argv[1:]))
    return f"{head} {rest}" if rest else head


def app_command(
    module: str,
    launcher_name: str | None = None,
    *,
    args: Sequence[str] = (),
    executable: str | None = None,
    environ: Mapping[str, str] | None = None,
    exists: Callable[[Path], bool] | None = None,
) -> str:
    """:func:`app_argv` as one quoted command line."""
    return to_command_line(
        app_argv(
            module, launcher_name, args=args, executable=executable, environ=environ, exists=exists
        )
    )


def split_command(command: str) -> tuple[str, str]:
    """``(executable, arguments)`` of a stored command line.

    Only the first token matters here, and it is either quoted (everything
    this module writes) or a bare path with no spaces.
    """
    text = (command or "").strip()
    if text.startswith('"'):
        end = text.find('"', 1)
        if end == -1:
            return text[1:], ""
        return text[1:end], text[end + 1 :].strip()
    head, _, tail = text.partition(" ")
    return head, tail.strip()


def should_replace(stored: str, current: str) -> bool:
    """Whether a stored launch command should be rewritten to *current*.

    Rewrites whenever *current* names the launcher or a real app exe. When
    *current* is only the interpreter form (a process started straight from the
    runtime, say by a taskbar pin, knows no launcher), it replaces just a
    stored command that is actually broken -- an interpreter with no ``-m`` --
    and never downgrades a working launcher entry to the runtime's versioned
    path.
    """
    if not stored.strip() or not current.strip() or stored.strip() == current.strip():
        return False
    current_exe, _ = split_command(current)
    if not is_generic_interpreter(current_exe):
        return True
    stored_exe, stored_args = split_command(stored)
    return is_generic_interpreter(stored_exe) and "-m" not in stored_args.split()


__all__ = [
    "GENERIC_INTERPRETERS",
    "app_argv",
    "app_command",
    "is_generic_interpreter",
    "should_replace",
    "split_command",
    "to_command_line",
]
