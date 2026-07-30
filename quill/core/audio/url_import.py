"""Download the audio from a web URL for the converter (#1255 §4.6, URL import).

The Universal Audio Converter can pull the audio track from a link (YouTube and
the many sites `yt-dlp <https://github.com/yt-dlp/yt-dlp>`_ supports) and hand
the downloaded file to the normal conversion pipeline. yt-dlp is **not** bundled:
it reaches arbitrary media hosts and updates constantly, so it installs on demand
(:func:`quill.core.speech.engine_install.install_yt_dlp`) only after the user
accepts an explicit consent + rights notice at the UI call site.

This module is the wx-free core: validate the URL, and download the *best audio*
stream to a destination folder using yt-dlp as a library (in-process, with a
progress hook), returning the file path so the converter takes over. It never
transcodes here — the converter does that — so the download step needs no ffmpeg.

Safety: refused in Safe Mode; the single network hand-off is constructing
``yt_dlp.YoutubeDL`` in :func:`_default_download`, recorded in the network-egress
audit. The actual download is injectable (``downloader``) so tests never touch
the network.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

from quill.core.error_codes import CodedError

#: ``progress(fraction_0_to_1, message)`` — same shape the engine installs use.
ProgressCallback = Callable[[float, str], None]

#: A downloader: ``(url, dest_dir, progress) -> downloaded Path``. Injectable so
#: the flow is unit-testable without yt-dlp or the network.
Downloader = Callable[[str, Path, "ProgressCallback | None"], Path]


class UrlImportError(CodedError):
    """Raised when importing audio from a URL fails (validation or download)."""

    code = "QUILL-AUDIO-URLIMPORT-DOWNLOAD"


def looks_like_url(text: str) -> bool:
    """A cheap pre-check: an ``http(s)://host`` string (not a local path).

    Deliberately permissive — yt-dlp is the real arbiter of what it can fetch;
    this only keeps the UI from treating a filename or blank box as a URL.
    """
    candidate = (text or "").strip()
    if not (candidate.startswith("http://") or candidate.startswith("https://")):
        return False
    remainder = candidate.split("://", 1)[1]
    return "." in remainder and len(remainder) > 3


def url_import_available() -> bool:
    """True when yt-dlp is installed/importable, so URL import can run now."""
    from quill.core.speech.engine_install import is_yt_dlp_available

    return is_yt_dlp_available()


def download_audio(
    url: str,
    dest_dir: Path,
    *,
    progress: ProgressCallback | None = None,
    downloader: Downloader | None = None,
) -> Path:
    """Download the best audio stream of *url* into *dest_dir* (returns the file).

    Raises :class:`UrlImportError` in Safe Mode, on an unusable URL, if yt-dlp is
    not installed, or if the download produces no file. ``downloader`` is
    injectable for tests; the default uses yt-dlp in-process.
    """
    if os.environ.get("QUILL_SAFE_MODE") == "1":
        raise UrlImportError("Importing audio from a URL is disabled in Safe Mode.")
    if not looks_like_url(url):
        raise UrlImportError(
            "That does not look like a web address. Paste a full http:// or https:// link."
        )

    fetch = downloader or _default_download
    if downloader is None and not url_import_available():
        raise UrlImportError("URL import needs the yt-dlp component, which is not installed yet.")

    dest_dir.mkdir(parents=True, exist_ok=True)
    try:
        result = fetch(url, dest_dir, progress)
    except UrlImportError:
        raise
    except Exception as exc:  # noqa: BLE001 - surface a clean, coded message
        raise UrlImportError(f"Could not download audio from that link: {exc}") from exc

    if not result.exists():
        raise UrlImportError("The download reported success but produced no file.")
    return result


#: An installer: ``(progress) -> None``. Installs yt-dlp on demand. Injectable.
Installer = Callable[["ProgressCallback | None"], None]


def ensure_and_download(
    url: str,
    dest_dir: Path,
    *,
    progress: ProgressCallback | None = None,
    installer: Installer | None = None,
    downloader: Downloader | None = None,
) -> Path:
    """Install yt-dlp if missing, then download *url*'s audio into *dest_dir*.

    The one call the UI runs off-thread once the user has consented: it performs
    the on-demand install (first use only) and the download in sequence, sharing
    one progress callback. Refuses in Safe Mode / on a bad URL via
    :func:`download_audio`. ``installer`` and ``downloader`` are injectable for
    tests; the defaults use :func:`quill.core.speech.engine_install.install_yt_dlp`
    and yt-dlp in-process.
    """
    if os.environ.get("QUILL_SAFE_MODE") == "1":
        raise UrlImportError("Importing audio from a URL is disabled in Safe Mode.")
    if not looks_like_url(url):
        raise UrlImportError(
            "That does not look like a web address. Paste a full http:// or https:// link."
        )
    if not url_import_available():
        install = installer or _default_installer
        try:
            install(progress)
        except UrlImportError:
            raise
        except Exception as exc:  # noqa: BLE001 - surface a clean, coded message
            raise UrlImportError(f"Could not install the yt-dlp component: {exc}") from exc
    return download_audio(url, dest_dir, progress=progress, downloader=downloader)


def _default_installer(progress: ProgressCallback | None) -> None:
    from quill.core.speech.engine_install import install_yt_dlp

    install_yt_dlp(progress=progress)


def _default_download(url: str, dest_dir: Path, progress: ProgressCallback | None) -> Path:
    """Download best-audio with yt-dlp as a library (the reviewed egress site)."""
    import yt_dlp  # imported lazily: installed on demand, absent until then

    captured: dict[str, str] = {}

    def hook(status: dict[str, object]) -> None:
        state = status.get("status")
        if state == "downloading" and progress is not None:
            total = status.get("total_bytes") or status.get("total_bytes_estimate") or 0
            done = status.get("downloaded_bytes") or 0
            fraction = (float(done) / float(total)) if total else 0.0  # type: ignore[arg-type]
            progress(max(0.0, min(1.0, fraction)), "Downloading audio from the link...")
        elif state == "finished":
            name = status.get("filename")
            if isinstance(name, str):
                captured["path"] = name

    options: dict[str, object] = {
        "format": "bestaudio/best",
        "outtmpl": str(dest_dir / "%(title)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [hook],
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        path = captured.get("path") or ydl.prepare_filename(info)
    return Path(path)
