"""Optional local Tesseract OCR engine download (free-first conversion, Tier 2).

The engine is distributed through QUILL's controlled ``assets-v1`` release as a
**byte-identical re-publish of the official UB-Mannheim Windows installer**
(Apache-2.0), pinned by SHA-256 — the same acquisition model as the eSpeak-NG
MSI. QUILL downloads it over verified HTTPS, checks the digest, and then
**launches the official installer visibly** for the user to complete; unlike
the MSI path there is no admin-free extraction mode for NSIS installers, and
QUILL never silently elevates or installs system software behind the user's
back. After installation, :func:`quill.io.tesseract_ocr.discover_tesseract_executable`
finds the engine in its conventional location (or anywhere on ``PATH``)
without a restart.

Safety mirrors the eSpeak-NG path: HTTPS-only with a verified TLS context,
SHA-256 pinned (SEC-6), blocked in Safe Mode, on an explicit user action only.
Windows-only. wx-free.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

from quill.core.error_codes import CodedError

ProgressCallback = Callable[[float, str], None]

# Pinned to the UB-Mannheim 5.4.0 Windows build (Apache-2.0). The installer
# bundles tesseract.exe, its DLLs, and the English + osd traineddata, so no
# follow-on download is needed for the default language.
TESSERACT_VERSION = "5.4.0.20240606"
TESSERACT_DOWNLOAD_URL = (
    "https://github.com/Community-Access/quill/releases/download/assets-v1/"
    "tesseract-ocr-w64-setup-5.4.0.20240606.exe"
)
# SHA-256 of the pinned installer, verified before it is ever executed (SEC-6).
TESSERACT_DOWNLOAD_SHA256 = "c885fff6998e0608ba4bb8ab51436e1c6775c2bafc2559a19b423e18678b60c9"
#: Approximate download size, for the consent prompt (bytes).
TESSERACT_DOWNLOAD_BYTES = 50_175_248
_DOWNLOAD_TIMEOUT_S = 1800.0


class TesseractInstallError(CodedError):
    """Raised when the Tesseract download or launch fails."""

    code = "QUILL-OCR-TESSERACT-INSTALL"


def tesseract_install_supported() -> bool:
    """True where QUILL can download the managed installer (Windows only)."""
    return sys.platform == "win32"


def download_tesseract_installer(
    progress_fn: ProgressCallback | None = None,
    *,
    timeout_seconds: float = _DOWNLOAD_TIMEOUT_S,
) -> Path:
    """Download and SHA-verify the official installer; return its temp path.

    The caller launches it (visibly) with :func:`launch_tesseract_installer`.
    Raises :class:`TesseractInstallError` on Safe Mode, unsupported platform,
    network failure, or digest mismatch (the file is discarded on mismatch).
    """
    if os.environ.get("QUILL_SAFE_MODE") == "1":
        raise TesseractInstallError("Downloading the OCR engine is disabled in Safe Mode.")
    if not tesseract_install_supported():
        raise TesseractInstallError(
            "The managed Tesseract download is Windows-only. "
            "On macOS install it with Homebrew (brew install tesseract); "
            "QUILL will find it on PATH."
        )
    from quill.core import release_assets

    fd, raw = tempfile.mkstemp(prefix="quill_tesseract_", suffix=".exe")
    os.close(fd)
    target = Path(raw)
    try:
        release_assets.download_verified(
            TESSERACT_DOWNLOAD_URL,
            target,
            sha256=TESSERACT_DOWNLOAD_SHA256,
            progress=progress_fn,
            timeout=timeout_seconds,
            label="Downloading the OCR engine...",
        )
    except release_assets.ReleaseAssetError as exc:
        target.unlink(missing_ok=True)
        raise TesseractInstallError(str(exc)) from exc
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    if progress_fn is not None:
        progress_fn(1.0, "Download verified.")
    return target


def launch_tesseract_installer(installer: Path) -> None:
    """Open the verified installer so the user completes it themselves.

    Deliberately interactive: the official installer shows exactly what will
    be installed and where, and any elevation prompt comes from Windows, in
    front of the user — never silently from QUILL.
    """
    if not installer.is_file():
        raise TesseractInstallError("The downloaded installer is missing.")
    try:
        os.startfile(str(installer))  # noqa: S606 - explicit, user-consented launch
    except OSError as exc:
        raise TesseractInstallError(f"Could not open the installer: {exc}") from exc


def tesseract_version_installed(executable: Path) -> str:
    """Best-effort ``tesseract --version`` banner line, or ``""`` on failure."""
    try:
        completed = subprocess.run(
            [str(executable), "--version"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    banner = (completed.stdout or completed.stderr or "").strip().splitlines()
    return banner[0] if banner else ""


__all__ = [
    "TESSERACT_DOWNLOAD_BYTES",
    "TESSERACT_DOWNLOAD_SHA256",
    "TESSERACT_DOWNLOAD_URL",
    "TESSERACT_VERSION",
    "TesseractInstallError",
    "download_tesseract_installer",
    "launch_tesseract_installer",
    "tesseract_install_supported",
    "tesseract_version_installed",
]
