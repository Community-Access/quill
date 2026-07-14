"""macOS file-type association support.

On macOS, document associations are declared in the app bundle's
``Info.plist`` (``CFBundleDocumentTypes``) at packaging time rather than
registered at runtime (the Windows registry model). This module produces the
``CFBundleDocumentTypes`` structure for packaging and offers a best-effort
runtime association via ``duti`` when present. It mirrors the public surface of
``quill.platform.windows.shell_integration`` so call sites can be platform-neutral.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # noqa: I001 - deferred to avoid a circular import at runtime
    from quill.platform.shell_integration import ShellIntegrationStatus

APP_DISPLAY_NAME = "Quill"
BUNDLE_IDENTIFIER = "org.communityaccess.quill"

TEXT_EXTENSIONS = ("txt",)
MARKUP_EXTENSIONS = ("md", "markdown", "mdx")
HTML_EXTENSIONS = ("html", "htm", "xhtml")


@dataclass(frozen=True, slots=True)
class ShellIntegrationEntry:
    """A human-readable description of one association (has ``.path`` like the
    Windows plan entries, so shared UI code can summarize it)."""

    path: str


def launcher_command() -> str:
    """Best-effort command used to open a document with Quill on macOS."""
    return f'open -a "{APP_DISPLAY_NAME}"'


def document_types_plist() -> list[dict[str, object]]:
    """CFBundleDocumentTypes entries to embed in the .app Info.plist."""
    return [
        _doc_type("Plain Text Document", TEXT_EXTENSIONS, "public.plain-text"),
        _doc_type("Markdown Document", MARKUP_EXTENSIONS, "net.daringfireball.markdown"),
        _doc_type("HTML Document", HTML_EXTENSIONS, "public.html"),
    ]


def build_shell_integration_plan(command: str | None = None) -> list[ShellIntegrationEntry]:
    """Describe the document associations (parallels the Windows registry plan)."""
    _ = command  # associations are declared by the bundle, not a command
    return [
        ShellIntegrationEntry(
            path=f"Plain Text Document ({', '.join('.' + e for e in TEXT_EXTENSIONS)})"
        ),
        ShellIntegrationEntry(
            path=f"Markdown Document ({', '.join('.' + e for e in MARKUP_EXTENSIONS)})"
        ),
        ShellIntegrationEntry(
            path=f"HTML Document ({', '.join('.' + e for e in HTML_EXTENSIONS)})"
        ),
    ]


def install_shell_integration(command: str | None = None) -> ShellIntegrationStatus:
    """Best-effort runtime association via ``duti`` (optional, non-raising).

    The primary mechanism is the app's Info.plist; this only helps when Quill
    is already installed as a bundle and ``duti`` is available. Returns a
    :class:`ShellIntegrationStatus` so the caller can tell the user *why* nothing
    happened when ``duti`` is missing (#8) instead of reporting a false success.
    """
    from quill.platform.shell_integration import (  # noqa: I001 - deferred to avoid a circular import (neutral re-exports this module)
        ShellIntegrationStatus,
    )

    _ = command
    if sys.platform != "darwin":
        return ShellIntegrationStatus(False, "File associations are only set on macOS.")
    # #74: force-register the bundle with LaunchServices so its Info.plist
    # CFBundleDocumentTypes take effect immediately (no re-login), independent
    # of whether duti is available below.
    refreshed = refresh_launch_services()
    if shutil.which("duti") is None:
        suffix = (
            " LaunchServices was refreshed so the bundle's Info.plist associations apply now."
            if refreshed
            else ""
        )
        return ShellIntegrationStatus(
            False,
            "duti (the file-association helper) is not installed, so the runtime "
            "Open-with associations were not set. Install it with `brew install duti`. "
            "The app bundle's Info.plist associations still apply once Quill is "
            "installed as a .app." + suffix,
        )
    for extension in TEXT_EXTENSIONS + MARKUP_EXTENSIONS + HTML_EXTENSIONS:
        subprocess.run(
            ["duti", "-s", BUNDLE_IDENTIFIER, f".{extension}", "all"],
            check=False,
            capture_output=True,
            text=True,
        )
    suffix = " LaunchServices was also refreshed." if refreshed else ""
    return ShellIntegrationStatus(
        True,
        "Set per-user Open-with associations for Quill via duti." + suffix,
    )


def remove_shell_integration() -> None:
    # Associations are owned by the bundle; nothing to unregister at runtime.
    return None


def _doc_type(name: str, extensions: tuple[str, ...], content_type: str) -> dict[str, object]:
    return {
        "CFBundleTypeName": name,
        "CFBundleTypeRole": "Editor",
        "LSItemContentTypes": [content_type],
        "CFBundleTypeExtensions": list(extensions),
    }


def _app_path() -> Path | None:
    """Return the enclosing ``Quill.app`` bundle path, or ``None`` out of a bundle.

    Used to run ``lsregister`` (so LaunchServices picks up the bundle's
    ``CFBundleDocumentTypes`` without a re-login) and to give callers a Dock
    surface. Returns ``None`` for a from-source run (``python -m quill``),
    where there is no ``.app`` container.

    Two probes, either sufficient: NSBundle's ``mainBundle`` (the authoritative
    source inside a py2app bundle, checked against our own bundle identifier so
    a from-source run inside Python.app is not mistaken for the Quill bundle),
    and a walk up from ``sys.executable`` to the first ``.app`` ancestor (the
    py2app layout is ``Quill.app/Contents/MacOS/Quill``).
    """
    try:
        import AppKit  # type: ignore[import-not-found]
    except ImportError:
        AppKit = None  # type: ignore[assignment]
    if AppKit is not None:
        bundle = AppKit.NSBundle.mainBundle()
        if bundle is not None and bundle.bundleIdentifier() == BUNDLE_IDENTIFIER:
            p = bundle.bundlePath()
            if p and str(p).endswith(".app"):
                return Path(str(p))
    p = Path(sys.executable).resolve()
    for parent in [p, *p.parents]:
        if parent.suffix == ".app":
            return parent
    return None


# ``lsregister`` is not on ``$PATH`` and (unlike most platform tools) not
# reachable via ``xcrun``; reach it through its well-known CoreServices path.
# This path has been stable across macOS releases; if it ever moves, the
# ``exists()`` guard below turns the refresh into a no-op rather than a crash.
_LSREGISTER = Path(
    "/System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/"
    "LaunchServices.framework/Versions/A/Support/lsregister"
)


def refresh_launch_services(app_path: Path | None = None) -> bool:
    """Force-register the app with LaunchServices so its ``Info.plist`` document
    types take effect without a re-login (#74). Returns ``True`` if ``lsregister``
    ran successfully; ``False`` (non-raising) off-mac, out-of-bundle, or if the
    tool is unavailable.
    """
    if sys.platform != "darwin":
        return False
    path = app_path if app_path is not None else _app_path()
    if path is None or not path.exists():
        return False
    if not _LSREGISTER.exists():
        return False
    result = subprocess.run(
        [str(_LSREGISTER), "-f", str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0
