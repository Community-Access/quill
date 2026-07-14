"""Optional on-demand Pandoc download (footprint unbundle, PRD 10.2.x).

Pandoc is QUILL's document-conversion engine (Word/ODT/EPUB/RTF import and
export). At ~220 MB unpacked it was the single largest bundled component, yet
core plain-text and Markdown editing never touches it — so it is now fetched on
demand the first time a conversion needs it, exactly like the offline speech
engine and OCR engine.

The source is the **official** ``jgm/pandoc`` GitHub release, pinned by version
and SHA-256 (SEC-6). QUILL downloads it over verified HTTPS, checks the digest,
and extracts ``pandoc.exe`` into a managed directory under the app data folder;
:func:`quill.core.external_tools.detect_tool` then finds it there without a
restart. HTTPS-only, blocked in Safe Mode, on an explicit user action only.
wx-free.
"""

from __future__ import annotations

import hashlib
import os
import ssl
import tempfile
import urllib.request
import zipfile
from collections.abc import Callable
from pathlib import Path

from quill.core.error_codes import CodedError
from quill.core.paths import app_data_dir

ProgressCallback = Callable[[float, str], None]

# Pinned to the same official Pandoc Windows build the bundling path used, so
# the download is byte-for-byte the release asset. Keep this in sync with
# scripts/build_windows_distribution.py (PANDOC_PINNED_*).
PANDOC_VERSION = "3.10"
PANDOC_DOWNLOAD_URL = (
    "https://github.com/jgm/pandoc/releases/download/3.10/pandoc-3.10-windows-x86_64.zip"
)
PANDOC_DOWNLOAD_SHA256 = "bb808d00fd58762299d64582a9b4c3e4b106cd929e62c5f19bcdcb496f1e54ae"
#: Approximate download size, for the consent prompt (bytes).
PANDOC_DOWNLOAD_BYTES = 45_000_000
_DOWNLOAD_TIMEOUT_S = 1800.0


class PandocInstallError(CodedError):
    """Raised when the Pandoc download, verification, or extraction fails."""

    code = "QUILL-CONVERT-PANDOC-INSTALL"


def managed_pandoc_dir() -> Path:
    """The app-data directory the downloaded Pandoc is extracted into."""
    return app_data_dir() / "tools" / "pandoc"


def managed_pandoc_executable() -> Path | None:
    """The downloaded ``pandoc.exe`` if present in the managed dir, else None."""
    candidate = managed_pandoc_dir() / "pandoc.exe"
    return candidate if candidate.is_file() else None


def pandoc_install_supported() -> bool:
    """True where QUILL can fetch the managed Windows build (Windows only).

    On macOS/Linux users install Pandoc via their package manager and QUILL
    finds it on PATH; there is no managed download there.
    """
    import sys

    return sys.platform == "win32"


def install_pandoc(
    progress_fn: ProgressCallback | None = None,
    *,
    timeout_seconds: float = _DOWNLOAD_TIMEOUT_S,
) -> Path:
    """Download, verify, and extract Pandoc; return the managed ``pandoc.exe``.

    Raises :class:`PandocInstallError` on Safe Mode, unsupported platform,
    network failure, digest mismatch, or a zip without ``pandoc.exe``.
    """
    if os.environ.get("QUILL_SAFE_MODE") == "1":
        raise PandocInstallError("Downloading Pandoc is disabled in Safe Mode.")
    if not pandoc_install_supported():
        raise PandocInstallError(
            "The managed Pandoc download is Windows-only. On macOS install it "
            "with Homebrew (brew install pandoc); QUILL will find it on PATH."
        )
    fd, raw = tempfile.mkstemp(prefix="quill_pandoc_", suffix=".zip")
    os.close(fd)
    archive = Path(raw)
    try:
        _download(PANDOC_DOWNLOAD_URL, archive, progress_fn, timeout_seconds)
        _verify_sha256(archive)
        executable = _extract_pandoc(archive, progress_fn)
    finally:
        archive.unlink(missing_ok=True)
    if progress_fn is not None:
        progress_fn(1.0, "Pandoc installed.")
    return executable


def _verify_sha256(path: Path) -> None:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual.lower() != PANDOC_DOWNLOAD_SHA256.lower():
        raise PandocInstallError(
            "The downloaded Pandoc archive failed its integrity check and was discarded.\n"
            f"  expected: {PANDOC_DOWNLOAD_SHA256}\n"
            f"  got:      {actual}"
        )


def _extract_pandoc(archive: Path, progress_fn: ProgressCallback | None) -> Path:
    """Extract just ``pandoc.exe`` (and any DLLs beside it) into the managed dir."""
    if progress_fn is not None:
        progress_fn(0.97, "Extracting Pandoc...")
    found: Path | None = None
    with zipfile.ZipFile(archive) as zf:
        # Pre-scan before touching the disk: a malformed archive must not
        # leave behind a fresh managed dir with stray DLLs (#798 review).
        all_names = [Path(i.filename).name for i in zf.infolist() if not i.is_dir()]
        if not any(name.lower() == "pandoc.exe" for name in all_names):
            raise PandocInstallError("The downloaded archive did not contain pandoc.exe.")
        target = managed_pandoc_dir()
        target.mkdir(parents=True, exist_ok=True)
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = Path(info.filename).name
            if not name:
                continue
            # The official zip nests files under pandoc-<version>/; flatten the
            # executable (and any sibling runtime files) into the managed dir.
            lowered = name.lower()
            if lowered == "pandoc.exe" or lowered.endswith(".dll"):
                dest = target / name
                with zf.open(info) as src, dest.open("wb") as out:
                    out.write(src.read())
                if lowered == "pandoc.exe":
                    found = dest
    if found is None:
        raise PandocInstallError("The downloaded archive did not contain pandoc.exe.")
    return found


def _download(
    url: str,
    target: Path,
    progress_fn: ProgressCallback | None,
    timeout_seconds: float,
) -> None:
    """Stream the Pandoc archive over verified HTTPS.

    GATE-9 / network-egress: the only outbound call in this module. Runs on an
    explicit user action, refuses non-HTTPS URLs, and uses a verified TLS
    context.
    """
    if not url.lower().startswith("https://"):
        raise PandocInstallError("The Pandoc download must use a secure (HTTPS) address.")
    context = ssl.create_default_context()
    request = urllib.request.Request(url, headers={"User-Agent": "QUILL"})
    try:
        with (
            urllib.request.urlopen(  # noqa: S310 - HTTPS enforced above
                request, timeout=timeout_seconds, context=context
            ) as response,
            target.open("wb") as out,
        ):
            total = int(response.headers.get("Content-Length", 0) or 0)
            read = 0
            while True:
                chunk = response.read(1 << 16)
                if not chunk:
                    break
                out.write(chunk)
                read += len(chunk)
                if progress_fn is not None and total > 0:
                    progress_fn(min(read / total, 0.95), "Downloading Pandoc...")
    except PandocInstallError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise PandocInstallError(f"Could not download Pandoc: {exc}") from exc


__all__ = [
    "PANDOC_DOWNLOAD_BYTES",
    "PANDOC_DOWNLOAD_SHA256",
    "PANDOC_DOWNLOAD_URL",
    "PANDOC_VERSION",
    "PandocInstallError",
    "install_pandoc",
    "managed_pandoc_dir",
    "managed_pandoc_executable",
    "pandoc_install_supported",
]
