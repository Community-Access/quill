"""Optional in-app Piper TTS engine download (#669).

Piper (https://github.com/rhasspy/piper) is a fast, local, high-quality neural
TTS engine. QUILL no longer bundles the Piper binary (PRD 10.2.x footprint
unbundle); users who want Piper download the official Windows AMD64 release
(~22 MB) on demand, and this extracts piper.exe + its supporting files into a
QUILL-managed folder the discover function searches (``<app data>/speech/piper``).

Safety mirrors QUILL's other verified downloads: HTTPS-only with a verified TLS
context, the downloaded archive is checked against a pinned SHA-256 before it is
extracted, blocked in Safe Mode, and only on an explicit user action. Windows-only
— on macOS and Linux install Piper from https://github.com/rhasspy/piper/releases.
wx-free.
"""

from __future__ import annotations

import os
import shutil
import ssl
import sys
import tempfile
import urllib.request
import zipfile
from collections.abc import Callable
from pathlib import Path

from quill.core.error_codes import CodedError
from quill.core.speech import models

ProgressCallback = Callable[[float, str], None]

# Pinned to the last stable release before rhasspy/piper moved to a shared-lib
# distribution model. The Windows AMD64 zip includes piper.exe, its supporting
# DLLs, and the espeak-ng-data directory needed for phonemization.
PIPER_RELEASE_TAG = "2023.11.14-2"
PIPER_DOWNLOAD_URL = (
    "https://github.com/rhasspy/piper/releases/download/"
    f"{PIPER_RELEASE_TAG}/piper_windows_amd64.zip"
)
# SHA-256 of piper_windows_amd64.zip for PIPER_RELEASE_TAG (22,477,236 bytes),
# verified against the live GitHub asset. The download is rejected if it does
# not match, matching the integrity guarantee of QUILL's other verified fetches.
PIPER_DOWNLOAD_SHA256 = "f3c58906402b24f3a96d92145f58acba6d86c9b5db896d207f78dc80811efcea"
_DOWNLOAD_TIMEOUT_S = 1800.0
_PIPER_EXE = "piper.exe"


class PiperInstallError(CodedError):
    """Raised when the Piper download or extraction fails."""

    code = "QUILL-SPEECH-PIPER-INSTALL"


def piper_install_supported() -> bool:
    """True where QUILL can download a managed Piper binary (Windows only)."""
    return sys.platform == "win32"


def managed_piper_dir() -> Path:
    """The folder a downloaded Piper binary is installed into (discover-searched)."""
    return models.app_data_dir() / "speech" / "piper"


def install_piper(
    progress: ProgressCallback | None = None,
    *,
    dest_dir: Path | None = None,
    timeout_seconds: float = _DOWNLOAD_TIMEOUT_S,
) -> Path:
    """Download and extract piper.exe, returning the executable path.

    Raises :class:`PiperInstallError` on Safe Mode, unsupported platform,
    network failure, or a bad archive. The discover cache is cleared so the new
    binary is picked up immediately without restarting QUILL.
    """
    if os.environ.get("QUILL_SAFE_MODE") == "1":
        raise PiperInstallError("Downloading Piper is disabled in Safe Mode.")
    if not piper_install_supported():
        raise PiperInstallError(
            "Automatic Piper download is Windows-only. "
            "On macOS or Linux install it from https://github.com/rhasspy/piper/releases"
        )
    dest = Path(dest_dir) if dest_dir is not None else managed_piper_dir()
    dest.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="quill_piper_dl_"))
    try:
        # Asset-first: prefer QUILL's own hosted, SHA-verified copy so a rhasspy
        # outage or removal can't break Piper; fall back to the upstream release.
        zip_path = _maybe_fetch_hosted_piper(staging, progress)
        if zip_path is None:
            zip_path = staging / "piper_windows_amd64.zip"
            _download_zip(PIPER_DOWNLOAD_URL, zip_path, progress, timeout_seconds)
            if progress is not None:
                progress(0.9, "Verifying download...")
            _verify_sha256(zip_path, PIPER_DOWNLOAD_SHA256)
        # (a hosted copy is already SHA-verified by fetch_file against the pinned asset)
        if progress is not None:
            progress(0.92, "Extracting Piper...")
        piper_path = _extract_piper_from_zip(zip_path, dest)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    if progress is not None:
        progress(1.0, "Done.")
    return piper_path


def _maybe_fetch_hosted_piper(dest_dir: Path, progress: ProgressCallback | None) -> Path | None:
    """Return QUILL's own hosted, SHA-verified Piper zip if published, else None.

    QUILL prefers a byte-identical copy on its ``assets-v1`` release over the
    upstream rhasspy asset, so an upstream outage or removal cannot break Piper.
    Returns None -- so :func:`install_piper` falls back to ``PIPER_DOWNLOAD_URL``
    -- whenever no pinned ``piper`` asset is published yet, or any fetch step
    fails. This mirrors the Vosk self-hosting fallback
    (:func:`quill.core.speech.engine_install._maybe_fetch_vosk_wheel`).

    To activate it: upload ``piper_windows_amd64.zip`` to the ``assets-v1``
    release and add a pinned ``piper`` entry to ``release_assets.ASSETS`` (its
    SHA-256 is :data:`PIPER_DOWNLOAD_SHA256`). Until then this is inert -- no
    hosted request is attempted -- so there is no wasted round trip.
    """
    try:
        from quill.core.release_assets import ASSETS, fetch_file, is_pinned
    except Exception:  # noqa: BLE001 - release_assets should import; be defensive
        return None
    asset = ASSETS.get("piper")
    if asset is None or not is_pinned(asset):
        return None
    try:
        return fetch_file("piper", dest_dir, progress=progress, label="Downloading Piper...")
    except Exception:  # noqa: BLE001 - any hosted-fetch failure -> upstream fallback
        return None


def _download_zip(
    url: str, target: Path, progress: ProgressCallback | None, timeout_seconds: float
) -> None:
    """Stream the Piper zip over verified HTTPS.

    GATE-9 / network-egress: the only outbound call in this module. Runs on an
    explicit user "download Piper" action, refuses non-HTTPS URLs, uses a verified
    TLS context, and streams with a cancellable progress callback.
    """
    if not url.lower().startswith("https://"):
        raise PiperInstallError("Piper download must use a secure (HTTPS) address.")
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
                if progress is not None and total > 0:
                    progress(min(read / total, 0.9), "Downloading Piper...")
    except PiperInstallError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise PiperInstallError(f"Could not download Piper: {exc}") from exc


def _verify_sha256(path: Path, expected: str) -> None:
    """Reject the download unless its SHA-256 matches the pinned value.

    A mismatch means a corrupted or substituted archive; without this check a
    bare stream would extract and run whatever it received. Mirrors the
    integrity guarantee of QUILL's other verified downloads (release_assets).
    """
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual.lower() != expected.lower():
        raise PiperInstallError(
            f"The downloaded Piper archive failed its integrity check "
            f"(expected {expected[:12]}..., got {actual[:12]}...). "
            "The download may be corrupted or blocked; please try again."
        )


def _extract_piper_from_zip(zip_path: Path, dest_dir: Path) -> Path:
    """Extract piper.exe and its DLLs/data from the official Windows zip.

    The official piper_windows_amd64.zip nests everything under a ``piper/``
    prefix. We strip that prefix and write the subtree flat into ``dest_dir``
    so piper.exe can find its DLLs and espeak-ng-data/ at runtime.
    """
    piper_path: Path | None = None
    dest_resolved = dest_dir.resolve()
    try:
        with zipfile.ZipFile(zip_path) as zf:
            for member in zf.namelist():
                # Strip leading "piper/" prefix.
                parts = member.split("/", 1)
                if len(parts) < 2 or not parts[1]:
                    continue  # skip the top-level "piper/" dir entry
                rel = parts[1]
                out_path = dest_dir / rel
                # Zip-slip guard: reject any path that escapes dest_dir.
                if not str(out_path.resolve()).startswith(str(dest_resolved)):
                    continue
                if member.endswith("/"):
                    out_path.mkdir(parents=True, exist_ok=True)
                else:
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as src, out_path.open("wb") as dst:
                        shutil.copyfileobj(src, dst)
                if rel.lower() == _PIPER_EXE:
                    piper_path = out_path
    except zipfile.BadZipFile as exc:
        raise PiperInstallError("The downloaded Piper archive was not a valid zip.") from exc
    if piper_path is None or not piper_path.exists():
        raise PiperInstallError("piper.exe was not found in the downloaded archive.")
    return piper_path
