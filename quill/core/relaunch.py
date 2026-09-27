"""Build the command line that restarts QUILL with the same arguments.

Under ``python -m quill`` -- the dev launcher and the installed ``quill.exe``
(a VERSIONINFO-stamped pythonw.exe invoked as ``quill.exe -m quill``) --
``sys.argv[0]`` is the full path to ``quill/__main__.py``. Re-spawning
``[sys.executable, *sys.argv]`` therefore runs that file as a *script*, which
puts the package directory itself at ``sys.path[0]``; there ``quill/platform``
shadows the stdlib ``platform`` module and the relaunched process crashes
during menu construction. Always relaunch via ``-m quill`` instead.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence


def build_relaunch_command(
    executable: str,
    argv: Sequence[str],
    *,
    frozen: bool | None = None,
    module: str = "quill",
) -> list[str]:
    """Return the argv list that restarts the app with the same arguments.

    ``argv[0]`` (the ``__main__.py`` path, or the executable in a frozen
    build) is never forwarded -- the relaunched process must not receive it
    as a document to open.

    *module* is the app to bring back (``quill``, ``quill.apps.radio``). A
    frozen executable that is only an interpreter -- the shared
    ``QuillVilleRuntime.exe`` every QuillVille app runs on -- needs it too:
    run with the arguments alone it is not an app (2026-09-27).
    """
    from quill.core.app_command import is_generic_interpreter

    if frozen is None:
        frozen = bool(getattr(sys, "frozen", False))
    if frozen and not is_generic_interpreter(executable):
        return [executable, *argv[1:]]
    return [executable, "-m", module, *argv[1:]]
