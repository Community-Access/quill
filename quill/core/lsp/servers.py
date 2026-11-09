"""The language servers QUILL may start: one frozen allowlist, like CHECKER_TOOLS.

Approved by Jeff on 2026-11-08 (``docs/design/intellisense.md``, decision 4),
for these servers only:

* **Bundled** in the shared runtime, run by the bundled Node
  (``tools/nodejs/node.exe``) from ``tools/language-servers/node_modules``:
  the VS Code HTML, CSS, JSON and Markdown servers
  (``vscode-langservers-extracted``), ``typescript-language-server`` with
  ``typescript``, and Pyright.
* **Only if already installed**, found on the PATH and never downloaded:
  clangd, and PowerShell Editor Services (the ``PowerShellEditorServices``
  module, started by ``pwsh``).

Never Pylance, and never Microsoft's C/C++ extension engine: their licences
allow only Microsoft's own products.

Every server runs with fixed arguments, over standard input and output,
through :func:`quill.stability.safe_subprocess.spawn_subprocess_safely`, with
the document's project folder as its working directory. None of them is
allowed the network: each spec carries the settings that switch off what
would reach out (the JSON server's schema download, TypeScript's automatic
type acquisition), so the network egress audit has no row for them.

Pure resolution, no process is started here. ``tests/unit/core/test_lsp_servers.py``
freezes the table: a new server is a deliberate change there too.
"""

from __future__ import annotations

import os
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "LANGUAGE_SERVERS",
    "ResolvedServer",
    "ServerSpec",
    "bundled_node",
    "language_id_for",
    "language_servers_dir",
    "resolve_server",
    "server_for_path",
    "server_present",
]


@dataclass(frozen=True, slots=True)
class ServerSpec:
    """One allowlisted server: what it serves, and how it is started."""

    #: The name said in the Problems pane and the logs ("JSON server").
    name: str
    #: File extensions it serves, lower case with the dot.
    suffixes: tuple[str, ...]
    #: ``"bundled"`` (a script run by the bundled Node) or ``"installed"``.
    origin: str
    #: For bundled servers: the script, relative to ``tools/language-servers``.
    script: str = ""
    #: For installed servers: the executable's basename, found on the PATH.
    executable: str = ""
    #: Fixed arguments after the script or executable.
    args: tuple[str, ...] = ("--stdio",)
    #: ``initializationOptions`` sent with ``initialize``.
    init_options: dict[str, Any] = field(default_factory=dict)
    #: What ``workspace/configuration`` answers, by section.
    settings: dict[str, Any] = field(default_factory=dict)


#: File extension -> the LSP ``languageId``.
_LANGUAGE_IDS: dict[str, str] = {
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".less": "less",
    ".json": "json",
    ".jsonc": "jsonc",
    ".md": "markdown",
    ".markdown": "markdown",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascriptreact",
    ".ts": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    ".tsx": "typescriptreact",
    ".py": "python",
    ".pyi": "python",
    ".c": "c",
    ".h": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hh": "cpp",
    ".ps1": "powershell",
    ".psm1": "powershell",
    ".psd1": "powershell",
}

_EXTRACTED = "node_modules/vscode-langservers-extracted/bin"

LANGUAGE_SERVERS: tuple[ServerSpec, ...] = (
    ServerSpec(
        "HTML server",
        (".html", ".htm"),
        "bundled",
        script=f"{_EXTRACTED}/vscode-html-language-server",
        init_options={"provideFormatter": False, "embeddedLanguages": {"css": True}},
    ),
    ServerSpec(
        "CSS server",
        (".css", ".scss", ".less"),
        "bundled",
        script=f"{_EXTRACTED}/vscode-css-language-server",
        init_options={"provideFormatter": False},
    ),
    ServerSpec(
        "JSON server",
        (".json", ".jsonc"),
        "bundled",
        script=f"{_EXTRACTED}/vscode-json-language-server",
        # No schema is ever fetched: only a schema already on disk is used.
        init_options={"provideFormatter": False, "handledSchemaProtocols": ["file"]},
        settings={"json": {"schemaDownload": {"enable": False}, "validate": {"enable": True}}},
    ),
    ServerSpec(
        "Markdown server",
        (".md", ".markdown"),
        "bundled",
        script=f"{_EXTRACTED}/vscode-markdown-language-server",
        settings={
            "markdown": {
                "validate": {
                    "enabled": True,
                    "referenceLinks": {"enabled": "warning"},
                    "fragmentLinks": {"enabled": "warning"},
                    "fileLinks": {"enabled": "warning"},
                    # A web link is never followed: no network.
                    "ignoredLinks": ["http://**", "https://**"],
                }
            }
        },
    ),
    ServerSpec(
        "TypeScript server",
        (".js", ".mjs", ".cjs", ".jsx", ".ts", ".mts", ".cts", ".tsx"),
        "bundled",
        script="node_modules/typescript-language-server/lib/cli.mjs",
        init_options={
            # Automatic type acquisition runs npm and reaches the registry.
            "preferences": {"includeCompletionsForModuleExports": True},
            "tsserver": {"path": "node_modules/typescript/lib"},
            "disableAutomaticTypingAcquisition": True,
        },
    ),
    ServerSpec(
        "Pyright",
        (".py", ".pyi"),
        "bundled",
        script="node_modules/pyright/langserver.index.js",
        settings={
            "python": {"analysis": {"autoSearchPaths": True, "diagnosticMode": "openFilesOnly"}}
        },
    ),
    ServerSpec(
        "clangd",
        (".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh"),
        "installed",
        executable="clangd",
        args=("--background-index=false",),
    ),
    ServerSpec(
        "PowerShell Editor Services",
        (".ps1", ".psm1", ".psd1"),
        "installed",
        executable="pwsh",
    ),
)


@dataclass(frozen=True, slots=True)
class ResolvedServer:
    """A server that can start here: its spec and the argv that starts it."""

    spec: ServerSpec
    argv: tuple[str, ...]


def language_id_for(path: Path | str | None) -> str | None:
    """The LSP ``languageId`` for *path*'s extension, or None."""
    if path is None:
        return None
    return _LANGUAGE_IDS.get(Path(path).suffix.lower())


def server_for_path(path: Path | str | None) -> ServerSpec | None:
    """The allowlisted server for *path*, whether or not it is present."""
    if path is None:
        return None
    suffix = Path(path).suffix.lower()
    return next((spec for spec in LANGUAGE_SERVERS if suffix in spec.suffixes), None)


def _tools_dirs(name: str) -> list[Path]:
    dirs: list[Path] = []
    app_root = os.environ.get("QUILL_APP_ROOT", "").strip()
    if app_root:
        dirs.append(Path(app_root) / "tools" / name)
    beside = Path(sys.executable).parent / "tools" / name
    if beside not in dirs:
        dirs.append(beside)
    override = os.environ.get("QUILL_LANGUAGE_SERVERS_DIR", "").strip()
    if override and name == "language-servers":
        dirs.insert(0, Path(override))
    return dirs


def language_servers_dir() -> Path | None:
    """The bundled ``tools/language-servers`` folder, or None in a build without it."""
    for directory in _tools_dirs("language-servers"):
        if (directory / "node_modules").is_dir():
            return directory
    return None


def bundled_node() -> Path | None:
    """The bundled ``tools/nodejs/node.exe``; never the PATH's Node.

    The servers are pinned against this Node (typescript-language-server needs
    22.22.2 or later), so a different Node on the PATH is not a substitute.
    """
    exe = "node.exe" if os.name == "nt" else "node"
    for directory in _tools_dirs("nodejs"):
        if (directory / exe).is_file():
            return directory / exe
    override = os.environ.get("QUILL_LANGUAGE_SERVERS_NODE", "").strip()
    if override and Path(override).is_file():
        return Path(override)
    return None


def _powershell_editor_services() -> Path | None:
    """``Start-EditorServices.ps1`` from an installed PowerShellEditorServices module."""
    for folder in os.environ.get("PSModulePath", "").split(os.pathsep):
        base = Path(folder) / "PowerShellEditorServices"
        if not base.is_dir():
            continue
        for script in sorted(base.rglob("Start-EditorServices.ps1"), reverse=True):
            return script
    return None


def resolve_server(spec: ServerSpec) -> ResolvedServer | None:
    """How to start *spec* here, or None when it is not present."""
    if spec.origin == "bundled":
        node = bundled_node()
        folder = language_servers_dir()
        if node is None or folder is None:
            return None
        script = folder / spec.script
        if not script.is_file():
            return None
        return ResolvedServer(spec, (str(node), str(script), *spec.args))
    found = shutil.which(spec.executable)
    if found is None:
        return None
    if spec.executable == "pwsh":
        start = _powershell_editor_services()
        if start is None:
            return None
        session = Path(os.environ.get("TEMP", ".")) / "quill-pses"
        return ResolvedServer(
            spec,
            (
                found,
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-File",
                str(start),
                "-HostName",
                "QUILL",
                "-HostProfileId",
                "quill",
                "-HostVersion",
                "1.0.0",
                "-BundledModulesPath",
                str(start.parent.parent),
                "-LogPath",
                str(session / "pses.log"),
                "-SessionDetailsPath",
                str(session / "session.json"),
                "-FeatureFlags",
                "@()",
                "-Stdio",
            ),
        )
    return ResolvedServer(spec, (found, *spec.args))


#: How long a "present" or "not found" answer is trusted, in seconds.
PRESENCE_SECONDS = 30.0

#: server name -> (present, when asked). Plain dict reads and writes, which
#: are atomic in CPython; a race only means asking the disk once more.
_PRESENCE: dict[str, tuple[bool, float]] = {}


def server_present(spec: ServerSpec, *, now: float | None = None) -> bool:
    """Whether *spec* can be started here, remembered for :data:`PRESENCE_SECONDS`.

    :func:`resolve_server` looks on disk and on the PATH, and the Problems
    pane asks twice a second in every window; this asks the disk at most
    once in half a minute per server (review 2026-11-09, QUILL Lite 11).
    The Language Servers window still asks :func:`resolve_server` itself, so
    what it shows is never stale.
    """
    now = time.monotonic() if now is None else now
    known = _PRESENCE.get(spec.name)
    if known is not None and now - known[1] < PRESENCE_SECONDS:
        return known[0]
    present = resolve_server(spec) is not None
    _PRESENCE[spec.name] = (present, now)
    return present


def forget_server_presence() -> None:
    """Ask the disk again next time, after the servers' settings change."""
    _PRESENCE.clear()
