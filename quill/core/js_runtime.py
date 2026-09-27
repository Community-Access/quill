"""The JavaScript runtime yt-dlp uses to solve YouTube's challenges.

YouTube guards its stream addresses with a signature and an "n" challenge
written in JavaScript. yt-dlp solves them with the ``yt-dlp-ejs`` scripts
(pyproject's ``youtube`` group) run by an external JavaScript runtime; without
one, formats go missing or play throttled. QUILL bundles **deno** for that --
``tools\\deno\\deno.exe`` in the shared runtime and in every portable that plays
YouTube -- so nothing downloads on first use (owner's rule, 2026-09-27).

The lookup mirrors :func:`quill.ui.audio.mpv_engine.find_libmpv`:
``QUILL_APP_ROOT`` first (what the launcher exports), then the folder of the
running interpreter (the runtime or the portable bundle -- an app started
straight through ``QuillVilleRuntime.exe`` has no launcher to export
``QUILL_APP_ROOT``). Never ``PATH``: a deno somewhere on the host is not one
QUILL shipped or verified.

yt-dlp's ``remote_components`` stays at its default (none), so the solver
scripts come only from the bundled ``yt-dlp-ejs`` package and yt-dlp never
fetches code from npm or GitHub.

wx-free, strict-typed.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

#: The executable's basename inside ``tools/deno``.
DENO_EXE = "deno.exe" if os.name == "nt" else "deno"


def deno_search_dirs() -> list[Path]:
    """Where a bundled deno may live, in the order they are tried."""
    dirs: list[Path] = []
    app_root = os.environ.get("QUILL_APP_ROOT", "").strip()
    if app_root:
        dirs.append(Path(app_root) / "tools" / "deno")
    exe_dir = Path(sys.executable).parent / "tools" / "deno"
    if exe_dir not in dirs:
        dirs.append(exe_dir)
    return dirs


def find_deno() -> Path | None:
    """The bundled deno executable, or None when this build carries none."""
    for directory in deno_search_dirs():
        candidate = directory / DENO_EXE
        if candidate.is_file():
            return candidate
    return None


def yt_dlp_js_options() -> dict[str, object]:
    """``YoutubeDL`` options that point yt-dlp at the bundled deno.

    Empty when no deno is bundled, which leaves yt-dlp's own defaults alone.
    ``remote_components`` is deliberately never set: no downloads.
    """
    deno = find_deno()
    if deno is None:
        return {}
    return {"js_runtimes": {"deno": {"path": str(deno)}}}
