from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# A Finder-launched macOS .app bundle gets a minimal default PATH; it does not
# inherit /usr/local/bin or /opt/homebrew/bin the way a login/interactive shell
# does (those are sourced from the user's shell profile). A tool installed via
# a .pkg installer (e.g. pandoc.org's own installer, not Homebrew) or via
# Homebrew itself is then genuinely on disk but invisible to shutil.which().
# Checked only after PATH itself comes up empty.
_MACOS_FALLBACK_DIRS: tuple[str, ...] = (
    "/usr/local/bin",
    "/opt/homebrew/bin",
    "/opt/local/bin",  # MacPorts
)

# Where a standard macOS install puts the LibreOffice launcher (never on PATH).
_MACOS_LIBREOFFICE_APP_DIR = "/Applications/LibreOffice.app/Contents/MacOS"


@dataclass(frozen=True, slots=True)
class ExternalToolDefinition:
    tool_id: str
    name: str
    category: str
    description: str
    capabilities: tuple[str, ...]
    bundled_subpath: str
    executable_names: tuple[str, ...]
    website_url: str
    install_command: str


@dataclass(frozen=True, slots=True)
class ExternalToolStatus:
    definition: ExternalToolDefinition
    installed: bool
    path: str | None
    source: str
    version: str | None

    @property
    def tool_id(self) -> str:
        return self.definition.tool_id

    @property
    def name(self) -> str:
        return self.definition.name


TOOL_DEFINITIONS: tuple[ExternalToolDefinition, ...] = (
    ExternalToolDefinition(
        tool_id="pandoc",
        name="Pandoc",
        category="conversion",
        description=(
            "General-purpose document conversion engine for moving between Word, "
            "Markdown, HTML, EPUB, and many other text-centric formats."
        ),
        capabilities=(
            "Convert Word, Markdown, HTML, EPUB, and more into Quill-readable text",
            "Open Markdown, HTML, and plain-text conversion results as Quill tabs",
            "Prepare documents for downstream GLOW text workflows",
        ),
        bundled_subpath="pandoc/pandoc.exe",
        executable_names=("pandoc.exe", "pandoc"),
        website_url="https://pandoc.org/",
        install_command="winget install --id JohnMacFarlane.Pandoc -e",
    ),
    ExternalToolDefinition(
        tool_id="libreoffice",
        name="LibreOffice",
        category="conversion",
        description=(
            "Optional office conversion helper for legacy and edge-case document imports."
        ),
        capabilities=(
            "Improve compatibility for older office formats",
            "Provide a stronger conversion fallback path for difficult documents",
        ),
        bundled_subpath="libreoffice/program/soffice.exe",
        executable_names=("soffice.exe", "soffice", "libreoffice"),
        website_url="https://www.libreoffice.org/",
        install_command="winget install --id TheDocumentFoundation.LibreOffice -e",
    ),
    ExternalToolDefinition(
        tool_id="tidy_html5",
        name="HTML Tidy",
        category="validation",
        description=(
            "Native HTML validation and cleanup helper for checking and repairing HTML output."
        ),
        capabilities=(
            "Validate HTML before export or handoff",
            "Spot structural HTML issues without a browser dependency",
            "Support future cleanup and repair previews inside Quill",
        ),
        bundled_subpath="tidy-html5/tidy.exe",
        executable_names=("tidy.exe", "tidy"),
        website_url="https://www.html-tidy.org/",
        install_command="winget install --id HTACG.tidy -e",
    ),
    ExternalToolDefinition(
        tool_id="pymarkdownlnt",
        name="PyMarkdown",
        category="validation",
        description=(
            "Python-native Markdown linter for checking heading structure, spacing, "
            "and authoring consistency."
        ),
        capabilities=(
            "Lint Markdown without adding Node.js or Java",
            "Support future Markdown validation and cleanup workflows",
            "Flag authoring issues before Markdown leaves Quill",
        ),
        bundled_subpath="pymarkdownlnt/pymarkdownlnt.exe",
        executable_names=("pymarkdown.exe", "pymarkdownlnt.exe", "pymarkdown"),
        website_url="https://pymarkdown.readthedocs.io/",
        install_command="pip install pymarkdownlnt",
    ),
)


def get_external_tool_statuses() -> list[ExternalToolStatus]:
    return [detect_tool(definition) for definition in TOOL_DEFINITIONS]


def get_external_tool_status(tool_id: str) -> ExternalToolStatus:
    for definition in TOOL_DEFINITIONS:
        if definition.tool_id == tool_id:
            return detect_tool(definition)
    raise KeyError(tool_id)


def detect_tool(definition: ExternalToolDefinition) -> ExternalToolStatus:
    bundled = _bundled_tool_path(definition)
    if bundled is not None:
        return ExternalToolStatus(
            definition=definition,
            installed=True,
            path=str(bundled),
            source="bundled",
            version=_tool_version(bundled),
        )
    managed = _managed_tool_path(definition)
    if managed is not None:
        return ExternalToolStatus(
            definition=definition,
            installed=True,
            path=str(managed),
            source="downloaded",
            version=_tool_version(managed),
        )
    for executable_name in definition.executable_names:
        discovered = shutil.which(executable_name)
        if discovered:
            return ExternalToolStatus(
                definition=definition,
                installed=True,
                path=discovered,
                source="system",
                version=_tool_version(Path(discovered)),
            )
    if sys.platform == "darwin":
        for executable_name in definition.executable_names:
            found = _macos_path_fallback(executable_name)
            if found is not None:
                return ExternalToolStatus(
                    definition=definition,
                    installed=True,
                    path=found,
                    source="system",
                    version=_tool_version(Path(found)),
                )
    return ExternalToolStatus(
        definition=definition,
        installed=False,
        path=None,
        source="missing",
        version=None,
    )


def format_tool_status_report(statuses: list[ExternalToolStatus] | None = None) -> str:
    current_statuses = statuses or get_external_tool_statuses()
    lines = ["External Tools and Format Support", ""]
    for status in current_statuses:
        lines.append(f"## {status.name}")
        lines.append(f"Category: {status.definition.category}")
        lines.append(status.definition.description)
        lines.append("")
        if status.installed:
            lines.append(f"Status: installed via {status.source}")
            if status.path:
                lines.append(f"Path: {status.path}")
            if status.version:
                lines.append(f"Version: {status.version}")
        else:
            lines.append("Status: not installed")
            lines.append(f"Install command: {status.definition.install_command}")
        lines.append("Capabilities:")
        for capability in status.definition.capabilities:
            lines.append(f"- {capability}")
        lines.append(f"Learn more: {status.definition.website_url}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def copyable_install_command(tool_id: str) -> str:
    return get_external_tool_status(tool_id).definition.install_command


def _macos_path_fallback(executable_name: str) -> str | None:
    """Look for *executable_name* in well-known macOS install locations.

    Only meaningful when ``shutil.which`` already came up empty -- see the
    ``_MACOS_FALLBACK_DIRS`` comment for why a real, on-disk install can still
    be invisible to a GUI app's PATH.
    """
    for directory in _MACOS_FALLBACK_DIRS:
        candidate = Path(directory) / executable_name
        if candidate.is_file():
            return str(candidate)
    return None


def libreoffice_executable() -> str | None:
    """Resolve the LibreOffice ``soffice`` launcher, including the standard
    macOS ``.app`` install that is neither on PATH nor in the Homebrew dirs.

    A standard macOS install puts ``soffice`` at
    ``/Applications/LibreOffice.app/Contents/MacOS/soffice`` -- never on PATH --
    so the bare ``"soffice"`` argv used to fail on every standard Mac (#41).
    Returns the executable path, or None when LibreOffice is not installed.
    """
    found = shutil.which("soffice")
    if found:
        return found
    if sys.platform == "darwin":
        for directory in (_MACOS_LIBREOFFICE_APP_DIR, *_MACOS_FALLBACK_DIRS):
            candidate = Path(directory) / "soffice"
            if candidate.is_file():
                return str(candidate)
    return None


def _bundled_tool_path(definition: ExternalToolDefinition) -> Path | None:
    app_root = os.environ.get("QUILL_APP_ROOT", "").strip()
    if app_root:
        candidate = Path(app_root) / "tools" / definition.bundled_subpath
        if candidate.exists():
            return candidate.resolve()
    return None


def _managed_tool_path(definition: ExternalToolDefinition) -> Path | None:
    """A copy fetched on demand into the app-data tools directory.

    Pandoc is no longer bundled (footprint unbundle): the first conversion that
    needs it downloads it here. Other tools have no managed download yet and
    fall through to PATH detection.
    """
    if definition.tool_id != "pandoc":
        return None
    try:
        from quill.core.pandoc_install import managed_pandoc_executable

        managed = managed_pandoc_executable()
    except Exception:  # noqa: BLE001 - resolution must never crash detection
        return None
    return managed.resolve() if managed is not None else None


def _tool_version(executable: Path) -> str | None:
    command = [str(executable), "--version"]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            check=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    output = (completed.stdout or completed.stderr).strip().splitlines()
    return output[0].strip() if output else None
