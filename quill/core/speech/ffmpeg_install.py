"""Optional in-app ffmpeg download for offline speech (#617 follow-up).

QUILL does not bundle ffmpeg (it is GPL/LGPL). For users who would rather not run
``winget install Gyan.FFmpeg`` by hand, this downloads an **official Gyan.dev
Windows build** on an explicit action and extracts ``ffmpeg.exe`` + ``ffprobe.exe``
into the QUILL-managed tools folder the resolver already searches
(``<app data>/tools/ffmpeg``). The binaries come straight from the third-party
builder that ffmpeg.org links to; QUILL never redistributes them.

Safety mirrors the model-download path: HTTPS-only with a verified TLS context,
blocked in Safe Mode, on an explicit user action only. Windows-only — on macOS
and Linux the system package manager is the right tool. wx-free.
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

# Official Gyan.dev "essentials" Windows build (the download ffmpeg.org links to).
# The named URL 303-redirects to the current versioned zip; urllib follows it.
FFMPEG_DOWNLOAD_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
_DOWNLOAD_TIMEOUT_S = 1800.0
_WANTED = ("ffmpeg.exe", "ffprobe.exe")


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
    fd, raw = tempfile.mkstemp(prefix="quill_ffmpeg_", suffix=".zip")
    os.close(fd)
    tmp_zip = Path(raw)
    try:
        _download_zip(FFMPEG_DOWNLOAD_URL, tmp_zip, progress, timeout_seconds)
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


def _download_zip(
    url: str, target: Path, progress: ProgressCallback | None, timeout_seconds: float
) -> None:
    """Stream the ffmpeg zip over verified HTTPS.

    GATE-9 / network-egress: the only outbound call in this module. It runs on an
    explicit user "download ffmpeg" action, refuses non-HTTPS URLs, and uses a
    verified TLS context. A progress callback that raises (user cancel) aborts.
    """
    if not url.lower().startswith("https://"):
        raise FFmpegInstallError("ffmpeg download must use a secure (HTTPS) address.")
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
                    progress(min(read / total, 0.9), "Downloading ffmpeg...")
    except FFmpegInstallError:
        raise
    except Exception as exc:  # noqa: BLE001 - surface a clean message
        raise FFmpegInstallError(f"Could not download ffmpeg: {exc}") from exc


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
