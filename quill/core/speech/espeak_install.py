"""Optional in-app eSpeak-NG TTS engine download (#669).

eSpeak-NG is available as a Windows x64 MSI from GitHub. For users who want it,
this downloads the official MSI and extracts it **admin-free** using
``msiexec /a`` (Windows administrative-install mode), which unpacks all package
files into a target folder without touching the system registry or requiring
elevation. The resulting ``espeak-ng.exe`` + ``espeak-ng-data/`` directory are
immediately usable; ``discover_espeak_executable()`` picks them up from the
managed folder without a restart.

Safety mirrors the Piper download path: HTTPS-only with a verified TLS context,
blocked in Safe Mode, on an explicit user action only. Windows-only. wx-free.
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

from quill.core.speech import models

ProgressCallback = Callable[[float, str], None]

# Pinned to 1.52.0, the latest stable Windows release.
# The MSI bundles espeak-ng.exe, libespeak-ng.dll, and the full espeak-ng-data
# language/voice directory (~40 MB), so no follow-on download is needed.
#
# Hosted on QUILL's own "assets-v1" GitHub release rather than the upstream
# espeak-ng release: the byte-identical MSI is re-published there so the
# on-demand download has a single, controlled, SHA-pinned acquisition point
# (matching the bundled-build pin in scripts/build_windows_distribution.py).
ESPEAK_RELEASE_TAG = "1.52.0"
ESPEAK_DOWNLOAD_URL = (
    "https://github.com/Community-Access/quill/releases/download/assets-v1/espeak-ng.msi"
)
# SHA-256 of the pinned espeak-ng.msi, verified before extraction (SEC-6).
# Matches ESPEAK_PINNED_SHA256 in scripts/build_windows_distribution.py.
ESPEAK_DOWNLOAD_SHA256 = "7f673c709ea5dd579d3b5ebb98688cc575328a6ab7438d2bc405b88cedaeafb9"
_DOWNLOAD_TIMEOUT_S = 1800.0


class EspeakInstallError(Exception):
    """Raised when the eSpeak-NG download or extraction fails."""


def espeak_install_supported() -> bool:
    """True where QUILL can download a managed eSpeak-NG binary (Windows only)."""
    return sys.platform == "win32"


def managed_espeak_dir() -> Path:
    """The folder a downloaded eSpeak-NG is extracted into (discover-searched)."""
    return models.app_data_dir() / "speech" / "espeak-ng"


def install_espeak(
    progress_fn: ProgressCallback | None = None,
    *,
    dest_dir: Path | None = None,
    timeout_seconds: float = _DOWNLOAD_TIMEOUT_S,
) -> Path:
    """Download and extract eSpeak-NG, returning the espeak-ng.exe path.

    Uses ``msiexec /a`` (admin-free extraction) so no elevation prompt appears.
    Raises :class:`EspeakInstallError` on Safe Mode, unsupported platform,
    network failure, or extraction failure.

    Parameters
    ----------
    progress_fn:
        Optional ``(float, str) -> None`` callback; float is 0-1.
    dest_dir:
        Override the extraction target (defaults to :func:`managed_espeak_dir`).
    timeout_seconds:
        Total network + extraction timeout.
    """
    if os.environ.get("QUILL_SAFE_MODE") == "1":
        raise EspeakInstallError("Downloading eSpeak-NG is disabled in Safe Mode.")
    if not espeak_install_supported():
        raise EspeakInstallError(
            "Automatic eSpeak-NG download is Windows-only. "
            "On macOS install it with Homebrew (brew install espeak-ng); "
            "on Linux use your package manager (apt/dnf/pacman)."
        )

    dest = Path(dest_dir) if dest_dir is not None else managed_espeak_dir()
    dest.mkdir(parents=True, exist_ok=True)

    fd, raw = tempfile.mkstemp(prefix="quill_espeak_", suffix=".msi")
    os.close(fd)
    tmp_msi = Path(raw)
    try:
        _download_msi(ESPEAK_DOWNLOAD_URL, tmp_msi, progress_fn, timeout_seconds)
        _verify_msi_sha256(tmp_msi)
        if progress_fn is not None:
            progress_fn(0.9, "Extracting eSpeak-NG (this may take a moment)...")
        _extract_msi(tmp_msi, dest)
    finally:
        tmp_msi.unlink(missing_ok=True)

    exe = _find_espeak_exe(dest)
    if progress_fn is not None:
        progress_fn(1.0, "Done.")
    return exe


def _verify_msi_sha256(path: Path) -> None:
    """Verify the downloaded MSI against the pinned SHA-256 (SEC-6).

    Raises :class:`EspeakInstallError` (and leaves the caller to discard the
    file) if the digest does not match, so a corrupted or substituted download
    never reaches ``msiexec``.
    """
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual.lower() != ESPEAK_DOWNLOAD_SHA256.lower():
        raise EspeakInstallError(
            "Downloaded eSpeak-NG failed its integrity check and was discarded.\n"
            f"  expected: {ESPEAK_DOWNLOAD_SHA256}\n"
            f"  got:      {actual}"
        )


def _download_msi(
    url: str,
    target: Path,
    progress_fn: ProgressCallback | None,
    timeout_seconds: float,
) -> None:
    """Stream the eSpeak-NG MSI over verified HTTPS.

    GATE-9 / network-egress: the only outbound call in this module. Runs on an
    explicit user "download eSpeak-NG" action, refuses non-HTTPS URLs, and uses a
    verified TLS context.
    """
    if not url.lower().startswith("https://"):
        raise EspeakInstallError("eSpeak-NG download must use a secure (HTTPS) address.")
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
                    progress_fn(min(read / total, 0.85), "Downloading eSpeak-NG...")
    except EspeakInstallError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise EspeakInstallError(f"Could not download eSpeak-NG: {exc}") from exc


def _extract_msi(msi_path: Path, dest_dir: Path) -> None:
    """Extract the MSI content to dest_dir via ``msiexec /a`` (no elevation).

    Administrative-install mode unpacks all installer files into TARGETDIR
    without modifying the registry. TARGETDIR must end with a backslash per
    msiexec requirements.
    """
    # msiexec requires an absolute path ending with a backslash for TARGETDIR.
    target = str(dest_dir.resolve()).rstrip("\\") + "\\"
    try:
        result = subprocess.run(
            [
                "msiexec",
                "/a",
                str(msi_path.resolve()),
                "/qn",  # quiet, no UI
                f"TARGETDIR={target}",
            ],
            capture_output=True,
            timeout=300,
            check=False,
        )
    except FileNotFoundError as exc:
        raise EspeakInstallError("msiexec not found — this feature requires Windows.") from exc
    except subprocess.TimeoutExpired as exc:
        raise EspeakInstallError("eSpeak-NG extraction timed out.") from exc
    # msiexec exit 0 = success; 3010 = success, reboot suggested (rare for /a).
    if result.returncode not in (0, 3010):
        detail = (result.stderr or result.stdout or b"").decode(errors="replace").strip()
        raise EspeakInstallError(f"msiexec extraction failed (exit {result.returncode}). {detail}")


def _find_espeak_exe(search_root: Path) -> Path:
    """Find espeak-ng.exe anywhere under search_root after MSI extraction.

    The exact subdirectory produced by msiexec /a varies by MSI configuration,
    so we search recursively rather than hard-coding a path.
    """
    for candidate in sorted(search_root.rglob("espeak-ng.exe")):
        return candidate.resolve()
    raise EspeakInstallError(
        "espeak-ng.exe was not found after extraction. "
        "The downloaded MSI may be a different version — "
        f"see {ESPEAK_DOWNLOAD_URL}"
    )
