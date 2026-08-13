"""Build the command that shows a file in the desktop's file manager.

Four surfaces grew their own copy of this (the editor's Reveal in Explorer,
the app shell's "Open folder" after an update, Audio Studio, and the Radio
recordings list), and **two of the four were wrong in the same way**::

    subprocess.Popen(["explorer", "/select,", str(path)])   # wrong
    subprocess.Popen(["explorer", f"/select,{path}"])       # right

Windows Explorer parses ``/select,`` and the path as a *single* argument. Split
across two, Explorer sees a switch it cannot interpret, ignores it, and opens
the Documents folder instead -- so the feature appears to work (a window
opens) while doing something else entirely. That is exactly the failure shape
worth having one tested implementation of, especially for a screen-reader
user, who gets no visual cue that the wrong folder just opened.

Pure: this builds the argv and nothing else, so the quoting rule is testable
without launching anything. Callers hand the result to ``subprocess.Popen``.
The Windows branch is the one that matters; macOS ``open -R`` and the Linux
fallback take the path as an ordinary separate argument.

wx-free, strict-typed.
"""

from __future__ import annotations

import posixpath
import sys
from pathlib import Path


def reveal_command(path: Path | str, *, platform: str | None = None) -> list[str]:
    """The argv that reveals *path* in the platform's file manager.

    *platform* defaults to :data:`sys.platform` and exists so the tests can
    state all three branches on one machine. The path is used as text rather
    than re-parsed through :class:`~pathlib.Path`, because ``Path`` uses the
    *running* machine's flavour: a POSIX path handed to the macOS branch on a
    Windows box would come back with backslashes in it.

    On Windows the file is *selected* inside its folder. On macOS ``open -R``
    does the same. Elsewhere there is no portable "select this file" verb, so
    the containing folder is opened with ``xdg-open`` -- the honest
    approximation rather than a switch that silently does nothing.
    """
    target = str(path)
    system = sys.platform if platform is None else platform
    if system.startswith("win"):
        # One argument. The comma binds the path to the switch; a space
        # between them makes Explorer drop the switch and open Documents.
        return ["explorer", f"/select,{target}"]
    if system == "darwin":
        return ["open", "-R", target]
    folder = posixpath.dirname(target)
    return ["xdg-open", folder or target]


__all__ = ["reveal_command"]
