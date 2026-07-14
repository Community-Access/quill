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

import hashlib
import os
import ssl
import subprocess
import sys
import tempfile
import urllib.request
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
    fd, raw = tempfile.mkstemp(prefix="quill_tesseract_", suffix=".exe")
    os.close(fd)
    target = Path(raw)
    try:
        _download(TESSERACT_DOWNLOAD_URL, target, progress_fn, timeout_seconds)
        _verify_sha256(target)
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


def _verify_sha256(path: Path) -> None:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual.lower() != TESSERACT_DOWNLOAD_SHA256.lower():
        raise TesseractInstallError(
            "The downloaded OCR engine failed its integrity check and was discarded.\n"
            f"  expected: {TESSERACT_DOWNLOAD_SHA256}\n"
            f"  got:      {actual}"
        )


def _download(
    url: str,
    target: Path,
    progress_fn: ProgressCallback | None,
    timeout_seconds: float,
) -> None:
    """Stream the installer over verified HTTPS.

    GATE-9 / network-egress: the only outbound call in this module. Runs on an
    explicit user "install local OCR engine" action, refuses non-HTTPS URLs,
    and uses a verified TLS context.
    """
    if not url.lower().startswith("https://"):
        raise TesseractInstallError("The OCR engine download must use a secure (HTTPS) address.")
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
                    progress_fn(min(read / total, 0.95), "Downloading the local OCR engine...")
    except TesseractInstallError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise TesseractInstallError(f"Could not download the OCR engine: {exc}") from exc


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
