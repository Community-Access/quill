"""Optional in-app ffmpeg download for offline speech (#617 follow-up).

QUILL does not bundle ffmpeg (it is GPL/LGPL). For users who would rather not run
``winget install Gyan.FFmpeg`` by hand, this downloads a pinned **Gyan.dev
"essentials" Windows build** on an explicit action and extracts ``ffmpeg.exe`` +
``ffprobe.exe`` into the QUILL-managed tools folder the resolver already searches
(``<app data>/tools/ffmpeg``).

The build is re-hosted on QUILL's own ``assets-v1`` release and pinned by
SHA-256 -- the same self-hosted, verified model used for the eSpeak-NG (GPL) MSI
-- so the download does not depend on a third-party host and cannot be swapped
under us. As GPL/LGPL software, the corresponding source is available upstream
(ffmpeg.org, and the Gyan.dev build page); the mirrored asset is byte-identical
to that official build.

Safety mirrors the model-download path: HTTPS-only with a verified TLS context,
blocked in Safe Mode, on an explicit user action only. Windows-only — on macOS
and Linux the system package manager is the right tool. wx-free.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import zipfile
from collections.abc import Callable
from pathlib import Path

from quill.core.error_codes import CodedError
from quill.core.speech import models

ProgressCallback = Callable[[float, str], None]

# Official Gyan.dev "essentials" Windows build (the download ffmpeg.org links to).
# The named URL 303-redirects to the current versioned zip; urllib follows it.
FFMPEG_DOWNLOAD_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

# Pinned mirror on QUILL's own assets-v1 release. This auto-activates the moment
# a real 64-hex SHA-256 is filled in below: QUILL then fetches the byte-pinned
# zip from assets-v1 (SHA-verified, self-hosted, no moving upstream), exactly
# like the eSpeak-NG and Tesseract installers. Until then FFMPEG_PINNED_SHA256 is
# empty and QUILL keeps using the moving Gyan.dev URL above (retry/resume/HTTPS
# via the shared core, but unpinned).
#
# To activate (one-time, no code change beyond these three constants):
#   1. Download the exact Gyan "essentials" zip you want to pin.
#   2. Upload it to the assets-v1 release; note the asset's filename.
#   3. Set FFMPEG_PINNED_FILENAME to that name, FFMPEG_PINNED_VERSION to the
#      ffmpeg version, and FFMPEG_PINNED_SHA256 to the file's SHA-256.
FFMPEG_PINNED_VERSION = "8.1.2"
FFMPEG_PINNED_FILENAME = "ffmpeg-8.1.2-essentials_build.zip"
FFMPEG_PINNED_SHA256 = "db580001caa24ac104c8cb856cd113a87b0a443f7bdf47d8c12b1d740584a2ec"
_ASSETS_V1_BASE = "https://github.com/Community-Access/quill/releases/download/assets-v1/"

_DOWNLOAD_TIMEOUT_S = 1800.0
_WANTED = ("ffmpeg.exe", "ffprobe.exe")


def _is_real_sha256(value: str) -> bool:
    """True for a genuine 64-hex SHA-256 (not a blank/placeholder)."""
    digest = value.strip().lower()
    return len(digest) == 64 and all(c in "0123456789abcdef" for c in digest)


def ffmpeg_download_source() -> tuple[str, str]:
    """Return ``(url, sha256)`` for the ffmpeg zip download.

    Prefers the pinned assets-v1 mirror once :data:`FFMPEG_PINNED_SHA256` is a
    real digest (byte-verified, self-hosted). Until the mirror is uploaded it
    returns the moving Gyan.dev upstream URL with an empty SHA -- unpinned, but
    still retry/resume/HTTPS via the shared download core.
    """
    if FFMPEG_PINNED_FILENAME and _is_real_sha256(FFMPEG_PINNED_SHA256):
        return _ASSETS_V1_BASE + FFMPEG_PINNED_FILENAME, FFMPEG_PINNED_SHA256
    return FFMPEG_DOWNLOAD_URL, ""


class FFmpegInstallError(CodedError):
    """Raised when the optional ffmpeg download or extraction fails."""

    code = "QUILL-SPEECH-FFMPEG-INSTALL"


def ffmpeg_install_supported() -> bool:
    """True where QUILL can download a managed ffmpeg (Windows only)."""
    return sys.platform == "win32"


def managed_ffmpeg_dir() -> Path:
    """The folder a downloaded ffmpeg is installed into (resolver-searched)."""
    return models.app_data_dir() / "tools" / "ffmpeg"


def install_ffmpeg(
    progress: ProgressCallback | None = None,
    *,
    dest_dir: Path | None = None,
    timeout_seconds: float = _DOWNLOAD_TIMEOUT_S,
) -> Path:
    """Download and extract ffmpeg/ffprobe, returning the ffmpeg.exe path.

    Raises :class:`FFmpegInstallError` (Safe Mode, unsupported platform, network,
    or a bad archive). The resolver cache is cleared so the new binary is picked
    up immediately.
    """
    if os.environ.get("QUILL_SAFE_MODE") == "1":
        raise FFmpegInstallError("Downloading ffmpeg is disabled in Safe Mode.")
    if not ffmpeg_install_supported():
        raise FFmpegInstallError(
            "Automatic ffmpeg download is Windows-only. On macOS install it with "
            "Homebrew (brew install ffmpeg); on Linux use your package manager."
        )
    dest = Path(dest_dir) if dest_dir is not None else managed_ffmpeg_dir()
    dest.mkdir(parents=True, exist_ok=True)
    from quill.core import release_assets

    fd, raw = tempfile.mkstemp(prefix="quill_ffmpeg_", suffix=".zip")
    os.close(fd)
    tmp_zip = Path(raw)
    try:
        try:
            # Pinned assets-v1 mirror (SHA-verified) once uploaded; the moving
            # Gyan.dev upstream (unpinned) until then. Either way it runs through
            # the shared core: retry/resume/mirror-fallback + HTTPS enforcement.
            url, sha256 = ffmpeg_download_source()
            release_assets.download_verified(
                url,
                tmp_zip,
                sha256=sha256,
                progress=progress,
                timeout=timeout_seconds,
                label="Downloading ffmpeg...",
            )
        except release_assets.ReleaseAssetError as exc:
            raise FFmpegInstallError(str(exc)) from exc
        if progress is not None:
            progress(0.95, "Extracting ffmpeg...")
        ffmpeg_path = _extract_ffmpeg_from_zip(tmp_zip, dest)
    finally:
        tmp_zip.unlink(missing_ok=True)
    _clear_resolver_cache()
    if progress is not None:
        progress(1.0, "Done.")
    return ffmpeg_path


def _clear_resolver_cache() -> None:
    try:
        from quill.core.speech import ffmpeg as ffmpeg_tools

        ffmpeg_tools.find_ffmpeg.cache_clear()
        ffmpeg_tools.find_ffprobe.cache_clear()
    except Exception:  # noqa: BLE001 - cache clearing is best-effort
        pass


def _extract_ffmpeg_from_zip(zip_path: Path, dest_dir: Path) -> Path:
    """Extract ffmpeg.exe + ffprobe.exe (flattened) from an official build zip.

    Pure and unit-tested: official builds nest the binaries under
    ``<build>/bin/``, so we match on the basename and write them flat into
    ``dest_dir``. Returns the ffmpeg.exe path; raises if it is missing.
    """
    extracted: dict[str, Path] = {}
    try:
        with zipfile.ZipFile(zip_path) as zf:
            for member in zf.namelist():
                base = member.rsplit("/", 1)[-1].lower()
                if base in _WANTED and base not in extracted:
                    out_path = dest_dir / base
                    with zf.open(member) as src, out_path.open("wb") as dst:
                        shutil.copyfileobj(src, dst)
                    extracted[base] = out_path
    except zipfile.BadZipFile as exc:
        raise FFmpegInstallError("The downloaded ffmpeg archive was not a valid zip.") from exc
    if "ffmpeg.exe" not in extracted:
        raise FFmpegInstallError("ffmpeg.exe was not found in the downloaded archive.")
    return extracted["ffmpeg.exe"]
