"""Where the GitHub Copilot CLI runtime comes from, and what it may inherit.

The Copilot SDK (``github-copilot-sdk``, import ``copilot``) does not contain
the agent runtime; it drives the Copilot CLI over JSON-RPC and, left alone,
downloads that CLI on first use. QUILL bundles everything (owner's rule,
2026-09-27), so the CLI ships at ``tools\\copilot\\copilot.exe`` in the shared
runtime and is found exactly the way :mod:`quill.core.js_runtime` finds deno:
``QUILL_APP_ROOT`` first (what the launcher exports), then the folder of the
running interpreter. Never ``PATH``: a ``copilot`` somewhere on the host is not
one QUILL shipped or verified.

Until a build carries the exe, :func:`find_copilot_cli` returns None and the
SDK keeps its own behaviour. ``COPILOT_CLI_PATH`` is honoured as a developer
override, the same variable the SDK itself reads.

:data:`COPILOT_EXE_SHA256` is the build pin of the staged exe, mirroring
:mod:`quill.core.ai.codex_binary`: :func:`cli_path_for_launch` refuses a
bundled binary that is not byte-for-byte the one this release staged, rather
than launching it or letting the SDK fetch another. The exe is GitHub's,
shipped unmodified as its licence requires, and never re-signed, which keeps
the hash true after a signed build. ``scripts/fetch_build_deps.py`` imports
these constants rather than restating them, so the build-time and launch-time
checks cannot drift apart.

The child's environment is :func:`copilot_child_env`: the harness-scrubbed
copy of QUILL's environment (no GitHub or cloud tokens -- the token travels as
the SDK's explicit ``github_token`` argument instead) plus
``COPILOT_SKIP_CLI_DOWNLOAD=1`` whenever QUILL names the binary, so nothing
downloads behind a bundled build's back.

wx-free, strict-typed.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from quill.core.ai.codex_binary import file_sha256
from quill.core.ai.harness_credentials import scrubbed_child_env
from quill.core.error_codes import CodedError

__all__ = [
    "COPILOT_CLI_VERSION",
    "COPILOT_EXE_SHA256",
    "CopilotCliUnverified",
    "copilot_cli_matches_pin",
    "cli_path_for_launch",
    "COPILOT_EXE",
    "CLI_PATH_ENV",
    "SKIP_DOWNLOAD_ENV",
    "copilot_search_dirs",
    "find_copilot_cli",
    "resolve_cli_path",
    "copilot_child_env",
]

#: The pinned ``github/copilot-cli`` release this build ships.
COPILOT_CLI_VERSION = "1.0.105"

#: SHA-256 of ``copilot.exe`` for :data:`COPILOT_CLI_VERSION` (win32-x64), the
#: one file in ``copilot-win32-x64.zip``. Pinned 2026-10-31; bump with the
#: version and the zip hash in ``scripts/fetch_build_deps.py``.
COPILOT_EXE_SHA256 = "ab6d710d551c137c766a6c8ef6ee2e7779c106870c96b9a91a91fa17b9748624"

#: The executable's basename inside ``tools/copilot``.
COPILOT_EXE = "copilot.exe" if os.name == "nt" else "copilot"

#: The SDK's own override for the CLI binary; a developer escape hatch here.
CLI_PATH_ENV = "COPILOT_CLI_PATH"

#: Set to ``1`` to stop the SDK downloading a CLI of its own.
SKIP_DOWNLOAD_ENV = "COPILOT_SKIP_CLI_DOWNLOAD"


def copilot_search_dirs() -> list[Path]:
    """Where a bundled Copilot CLI may live, in the order they are tried."""
    dirs: list[Path] = []
    app_root = os.environ.get("QUILL_APP_ROOT", "").strip()
    if app_root:
        dirs.append(Path(app_root) / "tools" / "copilot")
    exe_dir = Path(sys.executable).parent / "tools" / "copilot"
    if exe_dir not in dirs:
        dirs.append(exe_dir)
    return dirs


def find_copilot_cli() -> Path | None:
    """The bundled Copilot CLI, or None when this build carries none."""
    for directory in copilot_search_dirs():
        candidate = directory / COPILOT_EXE
        if candidate.is_file():
            return candidate
    return None


class CopilotCliUnverified(CodedError):
    """The bundled Copilot CLI is not the binary this release pinned."""

    code = "QUILL-AI-COPILOT-CLI-UNVERIFIED"
    user_hint = "Reinstall the QuillVille runtime to restore GitHub Copilot."


# (path, size, mtime_ns, pin) -> verdict: hashing ~170 MB once per launch of the
# session is enough; a replaced file changes size or mtime and is re-hashed.
_PIN_CACHE: dict[tuple[str, int, int, str], bool] = {}


def copilot_cli_matches_pin(path: Path) -> bool:
    """True when *path* is exactly the Copilot CLI this build pinned.

    False for a missing or unreadable file as well as for a different one: the
    caller's answer is the same either way -- do not launch it.
    """
    try:
        stat = path.stat()
        key = (str(path), stat.st_size, stat.st_mtime_ns, COPILOT_EXE_SHA256)
        if key not in _PIN_CACHE:
            _PIN_CACHE[key] = file_sha256(path) == COPILOT_EXE_SHA256
        return _PIN_CACHE[key]
    except OSError:
        return False


def cli_path_for_launch() -> Path | None:
    """The CLI to launch, verified: the developer override, else the pinned bundle.

    The ``COPILOT_CLI_PATH`` override is a developer's own binary and is not
    held to the pin. A bundled exe that fails the pin raises
    :class:`CopilotCliUnverified` -- returning None would let the SDK download
    a CLI of its own, which is worse than not starting. None means the build
    carries no CLI at all.
    """
    override = os.environ.get(CLI_PATH_ENV, "").strip()
    if override and Path(override).is_file():
        return Path(override)
    bundled = find_copilot_cli()
    if bundled is None:
        return None
    if not copilot_cli_matches_pin(bundled):
        raise CopilotCliUnverified(
            f"The bundled GitHub Copilot runtime at {bundled} is not the one this "
            f"release ships (version {COPILOT_CLI_VERSION})."
        )
    return bundled


def resolve_cli_path() -> Path | None:
    """The CLI QUILL should launch: the developer override, else the bundled one.

    ``COPILOT_CLI_PATH`` wins only when it names a file that exists; a stale
    value falls through to the bundled lookup rather than failing the launch.
    """
    override = os.environ.get(CLI_PATH_ENV, "").strip()
    if override and Path(override).is_file():
        return Path(override)
    return find_copilot_cli()


def copilot_child_env(cli_path: Path | None) -> dict[str, str]:
    """The environment the Copilot CLI child is started with.

    Never carries a GitHub token (see :func:`scrubbed_child_env`). When QUILL
    names the binary, the download is switched off and the path is pinned, so
    the SDK cannot swap in a CLI of its own.
    """
    env = scrubbed_child_env()
    if cli_path is not None:
        env[SKIP_DOWNLOAD_ENV] = "1"
        env[CLI_PATH_ENV] = str(cli_path)
    return env
