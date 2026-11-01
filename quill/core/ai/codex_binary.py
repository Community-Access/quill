"""The bundled OpenAI Codex app-server: where it lives, and the hash it must have.

Codex's agent engine runs as a child process, ``codex-app-server.exe``, which
ships once in the shared QuillVille runtime at ``tools\\codex`` (codex.md
section 9, decisions 1 and 8) -- staged at build time by
``scripts/fetch_build_deps.py --only codex`` and copied in by
``scripts/StageMediaTools.ps1``. Nothing downloads it at run time.

The lookup mirrors :func:`quill.core.js_runtime.find_deno`: ``QUILL_APP_ROOT``
first (what the launcher exports), then the folder of the running interpreter
(an app started straight through ``QuillVilleRuntime.exe`` has no launcher to
export ``QUILL_APP_ROOT``). Never ``PATH``: a codex somewhere on the host is
not one QUILL shipped or verified.

:data:`CODEX_APP_SERVER_SHA256` is the build pin of the unpacked exe, so a
caller can refuse to launch a binary that is not byte-for-byte the one this
release staged (:func:`codex_app_server_matches_pin`). The exe is OpenAI's,
Authenticode-signed by OpenAI and shipped unmodified; ``scripts/code_signing.py``
never re-signs it, which is what keeps this hash true after a signed build.
``scripts/fetch_build_deps.py`` imports these constants rather than restating
them, so the build-time and launch-time checks cannot drift apart.

wx-free, strict-typed.
"""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

#: The pinned ``openai/codex`` release (a ``rust-v*`` tag) this build ships.
CODEX_VERSION = "0.166.0"

#: SHA-256 of the unpacked ``codex-app-server.exe`` for :data:`CODEX_VERSION`
#: (x86_64-pc-windows-msvc). Pinned 2026-10-31: the GitHub release's own digest
#: for the bare ``.exe`` asset and the exe unpacked from the ``.exe.zip`` asset
#: agreed on it.
CODEX_APP_SERVER_SHA256 = "c08bfa333d7bbbeffef2cafe7522600df9cc380d08086ab57e6081ee0c4818f9"

#: The executable's basename inside ``tools/codex``.
CODEX_APP_SERVER_EXE = "codex-app-server.exe" if os.name == "nt" else "codex-app-server"

_CHUNK = 1024 * 1024


def codex_search_dirs() -> list[Path]:
    """Where a bundled app-server may live, in the order they are tried."""
    dirs: list[Path] = []
    app_root = os.environ.get("QUILL_APP_ROOT", "").strip()
    if app_root:
        dirs.append(Path(app_root) / "tools" / "codex")
    exe_dir = Path(sys.executable).parent / "tools" / "codex"
    if exe_dir not in dirs:
        dirs.append(exe_dir)
    return dirs


def find_codex_app_server() -> Path | None:
    """The bundled Codex app-server executable, or None when this build has none."""
    for directory in codex_search_dirs():
        candidate = directory / CODEX_APP_SERVER_EXE
        if candidate.is_file():
            return candidate
    return None


def file_sha256(path: Path) -> str:
    """Lower-case hex SHA-256 of *path*, read in chunks (the exe is ~280 MB)."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def codex_app_server_matches_pin(path: Path) -> bool:
    """True when *path* is exactly the app-server this build pinned.

    False for a missing or unreadable file as well as for a different one: the
    caller's answer is the same either way -- do not launch it.
    """
    try:
        return file_sha256(path) == CODEX_APP_SERVER_SHA256
    except OSError:
        return False
