"""Where the GitHub Copilot CLI runtime comes from, and what it may inherit.

The Copilot SDK (``github-copilot-sdk``, import ``copilot``) does not contain
the agent runtime; it drives the Copilot CLI over JSON-RPC and, left alone,
downloads that CLI on first use. QUILL bundles everything (owner's rule,
2026-09-27), so the CLI ships in ``tools\\copilot`` of the shared runtime and
is found exactly the way :mod:`quill.core.js_runtime` finds deno:
``QUILL_APP_ROOT`` first (what the launcher exports), then the folder of the
running interpreter. Never ``PATH``: a ``copilot`` somewhere on the host is not
one QUILL shipped or verified.

What ships is not the legacy single-file ``copilot.exe`` from
``copilot-win32-x64.zip`` -- SDK 1.0.28 never runs that. It is the "hostless"
runtime bundle the SDK itself materialises from the release's unified package
``github-copilot-<version>-win32-x64.tgz`` (``_cli_download.py``): the
``copilot-runtime.exe`` wrapper, ``runtime.node`` and the runtime assets, plus
the ``.hostless-runtime-assets-v2`` marker and a ``copilot.exe`` compatibility
alias (a byte copy of the wrapper). ``tools\\copilot`` holds exactly what the
SDK's ``prebuilds\\win32-x64`` cache folder would, so :func:`find_copilot_cli`
answers what the SDK's ``get_cached_cli_path`` would: the alias, and only when
alias, wrapper, ``runtime.node`` and marker are all present and non-empty.

Until a build carries the bundle, :func:`find_copilot_cli` returns None and the
SDK keeps its own behaviour. ``COPILOT_CLI_PATH`` is honoured as a developer
override, the same variable the SDK itself reads.

:data:`COPILOT_WRAPPER_SHA256` and :data:`COPILOT_RUNTIME_NODE_SHA256` are the
build pins of the staged bundle, mirroring :mod:`quill.core.ai.codex_binary`:
:func:`cli_path_for_launch` refuses a bundle whose entrypoint (alias or
wrapper) or ``runtime.node`` is not byte-for-byte what this release staged,
rather than launching it or letting the SDK fetch another. The files are
GitHub's, shipped unmodified as the licence requires, and never re-signed,
which keeps the hashes true after a signed build. ``scripts/fetch_build_deps.py``
imports these constants rather than restating them, so the build-time and
launch-time checks cannot drift apart.

The child's environment is :func:`copilot_child_env`: the harness-scrubbed
copy of QUILL's environment (no GitHub or cloud tokens -- the token travels as
the SDK's explicit ``github_token`` argument instead, which the SDK itself
places in the child as ``COPILOT_SDK_AUTH_TOKEN``) plus the binary's path and
``COPILOT_SKIP_CLI_DOWNLOAD=1`` whenever QUILL names the binary.

How SDK 1.0.28 actually reads those two (``client.py``
``_resolve_runtime_entrypoint``, ``_cli_download.py``): the runtime path is an
explicit ``RuntimeConnection.for_stdio(path=...)`` first, then
``COPILOT_CLI_PATH`` from the client's ``env=`` mapping (not ``os.environ``
when ``env=`` is given), then a download into
``%LOCALAPPDATA%\\github-copilot-sdk``. That download runs inside the
``CopilotClient`` constructor, and ``COPILOT_SKIP_CLI_DOWNLOAD`` (``1``,
``true`` or ``yes``) is read from the *parent's* ``os.environ`` -- so in the
child env it is belt and braces only. What actually prevents a download is
that the pack always passes the verified path.

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
    "COPILOT_RUNTIME_PLATFORM",
    "COPILOT_WRAPPER_SHA256",
    "COPILOT_RUNTIME_NODE_SHA256",
    "CopilotCliUnverified",
    "copilot_bundle_complete",
    "copilot_cli_matches_pin",
    "cli_path_for_launch",
    "COPILOT_EXE",
    "COPILOT_RUNTIME_WRAPPER",
    "COPILOT_RUNTIME_NODE",
    "COPILOT_ASSETS_MARKER",
    "CLI_PATH_ENV",
    "SKIP_DOWNLOAD_ENV",
    "SDK_AUTH_TOKEN_ENV",
    "copilot_search_dirs",
    "find_copilot_cli",
    "resolve_cli_path",
    "copilot_child_env",
]

#: The pinned ``github/copilot-cli`` release this build ships.
COPILOT_CLI_VERSION = "1.0.105"

#: The ``prebuilds`` platform folder of the release package this build ships.
COPILOT_RUNTIME_PLATFORM = "win32-x64"

#: SHA-256 of ``copilot-runtime.exe`` (and so of its ``copilot.exe`` alias) in
#: ``github-copilot-1.0.105-win32-x64.tgz``. Pinned 2026-10-31; bump with the
#: version and the package hash in ``scripts/fetch_build_deps.py``.
COPILOT_WRAPPER_SHA256 = "3ab8441328a44e78e07fa5b095d8498f872d684aa78970bf04849dcc5b0c0e68"

#: SHA-256 of ``runtime.node`` from the same package (the agent runtime proper).
COPILOT_RUNTIME_NODE_SHA256 = "6f5f640903296c8a124131d60ac0d47b200ccc9d6768b3305bce74e5e752e4c9"

#: The entrypoint the SDK's ``get_cached_cli_path`` returns: the compatibility
#: alias, a byte copy of the wrapper.
COPILOT_EXE = "copilot.exe" if os.name == "nt" else "copilot"

#: The out-of-process runtime wrapper the alias copies.
COPILOT_RUNTIME_WRAPPER = "copilot-runtime.exe" if os.name == "nt" else "copilot-runtime"

#: The native runtime library the wrapper loads.
COPILOT_RUNTIME_NODE = "runtime.node"

#: The SDK's marker for a complete hostless bundle (``_HOSTLESS_ASSETS_MARKER``).
COPILOT_ASSETS_MARKER = ".hostless-runtime-assets-v2"

#: The SDK's own override for the CLI binary; a developer escape hatch here.
CLI_PATH_ENV = "COPILOT_CLI_PATH"

#: ``1`` stops the SDK downloading a CLI of its own -- read by the SDK from the
#: parent process environment, not from the child ``env=`` (module docstring).
SKIP_DOWNLOAD_ENV = "COPILOT_SKIP_CLI_DOWNLOAD"

#: Where the SDK puts ``github_token=`` for the child (with ``--auth-token-env``).
SDK_AUTH_TOKEN_ENV = "COPILOT_SDK_AUTH_TOKEN"


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


def copilot_bundle_complete(directory: Path) -> bool:
    """True when *directory* holds a complete hostless runtime bundle.

    The SDK's own test (``get_cached_cli_path``): alias, wrapper,
    ``runtime.node`` and marker are each a non-empty file.
    """
    required = (COPILOT_EXE, COPILOT_RUNTIME_WRAPPER, COPILOT_RUNTIME_NODE, COPILOT_ASSETS_MARKER)
    try:
        return all(
            (directory / name).is_file() and (directory / name).stat().st_size > 0
            for name in required
        )
    except OSError:
        return False


def find_copilot_cli() -> Path | None:
    """The bundled Copilot CLI entrypoint, or None when this build carries none.

    The ``copilot.exe`` alias of a complete bundle -- the path the SDK's
    ``get_cached_cli_path`` would return for the same folder. A half-staged
    folder counts as none.
    """
    for directory in copilot_search_dirs():
        if copilot_bundle_complete(directory):
            return directory / COPILOT_EXE
    return None


class CopilotCliUnverified(CodedError):
    """The bundled Copilot CLI is not the binary this release pinned."""

    code = "QUILL-AI-COPILOT-CLI-UNVERIFIED"
    user_hint = "Reinstall the QuillVille runtime to restore GitHub Copilot."


# (path, size, mtime_ns, pin) -> verdict: hashing ~125 MB of runtime.node once
# per session is enough; a replaced file changes size or mtime and is re-hashed.
_PIN_CACHE: dict[tuple[str, int, int, str], bool] = {}


def _file_matches(path: Path, pin: str) -> bool:
    stat = path.stat()
    key = (str(path), stat.st_size, stat.st_mtime_ns, pin)
    if key not in _PIN_CACHE:
        _PIN_CACHE[key] = file_sha256(path) == pin
    return _PIN_CACHE[key]


def copilot_cli_matches_pin(path: Path) -> bool:
    """True when *path* is the entrypoint of exactly the bundle this build pinned.

    *path* (the alias, or the wrapper itself) must hash to the wrapper pin, and
    the wrapper and ``runtime.node`` beside it to theirs. False for a missing
    or unreadable file as well as for a different one: the caller's answer is
    the same either way -- do not launch it.
    """
    directory = path.parent
    checks = (
        (path, COPILOT_WRAPPER_SHA256),
        (directory / COPILOT_RUNTIME_WRAPPER, COPILOT_WRAPPER_SHA256),
        (directory / COPILOT_RUNTIME_NODE, COPILOT_RUNTIME_NODE_SHA256),
    )
    try:
        return all(_file_matches(file, pin) for file, pin in checks)
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

    Never carries a GitHub token (see :func:`scrubbed_child_env`); the SDK adds
    ``COPILOT_SDK_AUTH_TOKEN`` itself when ``github_token=`` is given. When QUILL
    names the binary, its path is recorded as ``COPILOT_CLI_PATH`` (which the
    SDK does read from this mapping) and the download flag is set.
    """
    env = scrubbed_child_env()
    # The SDK's own token channel; only the SDK may set it, from github_token=.
    env.pop(SDK_AUTH_TOKEN_ENV, None)
    if cli_path is not None:
        env[SKIP_DOWNLOAD_ENV] = "1"
        env[CLI_PATH_ENV] = str(cli_path)
    return env
