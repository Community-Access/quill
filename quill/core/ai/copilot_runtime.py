"""Find and verify the in-process Copilot SDK runtime shipped with QUILL.

The SDK can download its native runtime when it cannot find one. QUILL never
does that at run time: installers stage the pinned ``runtime.node`` beside the
app's tools, and this module verifies it before setting the SDK's runtime-path
environment variable. A missing runtime is an unavailable feature, not a reason
to download code or fall back to an unrelated executable on ``PATH``.

wx-free and strict-typed.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from quill.core.ai.codex_binary import file_sha256
from quill.core.error_codes import CodedError

__all__ = [
    "COPILOT_RUNTIME_VERSION",
    "COPILOT_RUNTIME_PLATFORM",
    "COPILOT_RUNTIME_NODE_SHA256",
    "COPILOT_RUNTIME_NODE",
    "SDK_RUNTIME_PATH_ENV",
    "CopilotRuntimeUnavailable",
    "CopilotRuntimeUnverified",
    "copilot_runtime_search_dirs",
    "find_copilot_runtime",
    "resolve_runtime_path",
    "copilot_runtime_matches_pin",
    "runtime_path_for_launch",
    "prepare_inprocess_runtime",
]

# The native runtime shipped by microsoft-copilot-sdk 2.0.1.
COPILOT_RUNTIME_VERSION = "1.0.114"
COPILOT_RUNTIME_PLATFORM = "win32-x64"
COPILOT_RUNTIME_NODE = "runtime.node"
COPILOT_RUNTIME_NODE_SHA256 = "b31336fb314d9f4c26658e018840a2fc18adaccbf380490fb597a4c3cddb2213"

# The SDK currently resolves its in-process library through this variable. The
# value points to runtime.node itself; no CLI executable or wrapper is needed.
SDK_RUNTIME_PATH_ENV = "COPILOT_CLI_PATH"


class CopilotRuntimeUnavailable(CodedError):
    """The pinned in-process runtime is not installed with this app."""

    code = "QUILL-AI-COPILOT-RUNTIME-UNAVAILABLE"
    user_hint = "Repair or reinstall the QuillVille runtime to enable Copilot."


class CopilotRuntimeUnverified(CodedError):
    """The runtime file does not match the version this app ships."""

    code = "QUILL-AI-COPILOT-RUNTIME-UNVERIFIED"
    user_hint = "Repair or reinstall the QuillVille runtime to restore Copilot."


def copilot_runtime_search_dirs() -> list[Path]:
    """Directories that may contain the app-bundled native runtime."""
    directories: list[Path] = []
    app_root = os.environ.get("QUILL_APP_ROOT", "").strip()
    if app_root:
        directories.append(Path(app_root) / "tools" / "copilot")
    beside_python = Path(sys.executable).parent / "tools" / "copilot"
    if beside_python not in directories:
        directories.append(beside_python)
    return directories


def find_copilot_runtime() -> Path | None:
    """Return a non-empty bundled ``runtime.node``, without consulting ``PATH``."""
    for directory in copilot_runtime_search_dirs():
        runtime = directory / COPILOT_RUNTIME_NODE
        try:
            if runtime.is_file() and runtime.stat().st_size > 0:
                return runtime
        except OSError:
            continue
    return None


def resolve_runtime_path() -> Path | None:
    """Find a runtime file without hashing it, for non-blocking readiness checks."""
    override = os.environ.get(SDK_RUNTIME_PATH_ENV, "").strip()
    if override:
        candidate = Path(override)
        try:
            if candidate.name == COPILOT_RUNTIME_NODE and candidate.is_file():
                return candidate
        except OSError:
            pass
    return find_copilot_runtime()


_PIN_CACHE: dict[tuple[str, int, int, str], bool] = {}


def copilot_runtime_matches_pin(path: Path) -> bool:
    """Whether *path* is the native runtime pinned by this build."""
    try:
        stat = path.stat()
        if not path.is_file() or stat.st_size <= 0:
            return False
        key = (str(path), stat.st_size, stat.st_mtime_ns, COPILOT_RUNTIME_NODE_SHA256)
        if key not in _PIN_CACHE:
            _PIN_CACHE[key] = file_sha256(path) == COPILOT_RUNTIME_NODE_SHA256
        return _PIN_CACHE[key]
    except OSError:
        return False


def runtime_path_for_launch() -> Path:
    """Return the verified runtime or raise a clear, coded availability error."""
    override = os.environ.get(SDK_RUNTIME_PATH_ENV, "").strip()
    if override:
        candidate = Path(override)
        try:
            is_runtime_file = candidate.name == COPILOT_RUNTIME_NODE and candidate.is_file()
        except OSError:
            is_runtime_file = False
        if is_runtime_file:
            if copilot_runtime_matches_pin(candidate):
                return candidate
            raise CopilotRuntimeUnverified(
                f"The Copilot runtime at {candidate} does not match version "
                f"{COPILOT_RUNTIME_VERSION}."
            )

    runtime = find_copilot_runtime()
    if runtime is None:
        raise CopilotRuntimeUnavailable(
            "The in-process Copilot runtime is not installed. Reinstall the "
            "QuillVille runtime; QUILL will not download it automatically."
        )
    if not copilot_runtime_matches_pin(runtime):
        raise CopilotRuntimeUnverified(
            f"The bundled Copilot runtime at {runtime} does not match version "
            f"{COPILOT_RUNTIME_VERSION}."
        )
    return runtime


def prepare_inprocess_runtime() -> Path:
    """Verify the runtime and direct the SDK to it before constructing a client."""
    runtime = runtime_path_for_launch()
    os.environ[SDK_RUNTIME_PATH_ENV] = str(runtime)
    return runtime
