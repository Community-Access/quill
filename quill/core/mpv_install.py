"""On-demand download of libmpv, the mpv playback engine.

**Why this module exists.** libmpv ships inside every full installer and
portable zip, so for most listeners it is simply there. Two editions cannot
carry it: the thin ``-Lite`` installer downloads the base shared runtime, which
holds no media tools at all (ffmpeg + libmpv are 306 MB, and four of the seven
QuillVille apps never call them), and a Companion stick has no runtime of its
own either. For those, "it ships inside the installer" was the only answer the
apps had -- which is not an answer, it is a description of somebody else's
install.

The asset itself was never the missing piece. ``libmpv-pack.zip`` has been
pinned by SHA-256 on QUILL's own ``assets-v1`` release for as long as the
build has been reproducible (:mod:`quill.core.release_assets`), because the
*build* fetches it from there -- ``scripts/fetch_build_deps.py --only libmpv``
is what stages the DLL the installers bundle. What was missing was any route
from the running app to that same verified zip, so Quill Radio told listeners
libmpv "is not downloadable on its own" while its own build downloaded it
routinely. This module is that route, and it deliberately reuses the build's
pin rather than introducing a second URL or hash that could drift.

The pack is unpacked whole, not reduced to the DLL: mpv is GPLv2+ and the
prebuilt is effectively GPLv3, so the GPL texts, mpv's Copyright file and the
corresponding-source offer (``README-SOURCE.txt``) are part of the compliance
posture and must land beside the library. Same rule the build follows.

Safety mirrors :mod:`quill.core.speech.ffmpeg_install`: HTTPS-only through the
shared verified-download core, SHA-256 checked before anything is copied into
place, blocked in Safe Mode, and only ever on an explicit user action. wx-free.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from pathlib import Path

from quill.core.error_codes import CodedError

ProgressCallback = Callable[[float, str], None]

#: The component key in :data:`quill.core.release_assets.ASSETS`. One key, used
#: by the runtime downloader and ``scripts/fetch_build_deps.py`` alike.
COMPONENT = "libmpv"

#: What the pack unpacks to; the file whose presence means "installed".
DLL_NAME = "libmpv-2.dll"

#: Roughly what the listener is agreeing to download, for the spoken warning.
APPROXIMATE_SIZE_MB = 46


class MpvInstallError(CodedError):
    """Raised when the optional libmpv download or unpacking fails."""

    code = "QUILL-MEDIA-MPV-INSTALL"


def mpv_install_supported() -> bool:
    """True where QUILL can download a managed libmpv (Windows only).

    The pinned pack is a Windows build. On macOS the player stays on its own
    backend; there is no point offering a download that cannot run.
    """
    return sys.platform == "win32"


def managed_mpv_dir() -> Path:
    """The folder a downloaded libmpv is installed into.

    THE definition, deliberately. ``quill.ui.audio.mpv_engine.mpv_pack_dir``
    defers to this one: a downloader that wrote somewhere the resolver does not
    look would install successfully and change nothing, which is the worst
    shape a bug can take -- it reports success.
    """
    from quill.core.speech.engine_install import engine_packs_dir

    return engine_packs_dir() / "mpv"


def mpv_installed() -> bool:
    """True when a downloaded libmpv is present in the managed folder.

    Narrower than ``mpv_engine.find_libmpv()`` on purpose: that answers "can
    the app use mpv from anywhere?" (bundled, overridden, or downloaded), while
    this answers "is there anything here for an uninstall to remove?".
    """
    try:
        return (managed_mpv_dir() / DLL_NAME).is_file()
    except Exception:  # noqa: BLE001 - no app data dir in odd harnesses
        return False


def install_mpv(
    progress: ProgressCallback | None = None,
    *,
    dest_dir: Path | None = None,
) -> Path:
    """Download and unpack libmpv, returning the path to ``libmpv-2.dll``.

    Raises :class:`MpvInstallError` for Safe Mode, an unsupported platform, a
    network failure, a checksum mismatch or a malformed archive.

    No cache to invalidate afterwards, and that is deliberate rather than
    lucky: ``mpv_engine.find_libmpv`` walks its candidates on every call, so
    the engine becomes usable the moment this returns, with no restart.
    """
    if os.environ.get("QUILL_SAFE_MODE") == "1":
        raise MpvInstallError("Downloading the mpv engine is disabled in Safe Mode.")
    if not mpv_install_supported():
        raise MpvInstallError(
            "Automatic mpv download is Windows-only. On macOS install mpv with "
            "Homebrew (brew install mpv) and point QUILL_LIBMPV at its library."
        )
    dest = Path(dest_dir) if dest_dir is not None else managed_mpv_dir()
    dest.mkdir(parents=True, exist_ok=True)

    from quill.core import release_assets

    try:
        # Verified, atomic and SHA-pinned in the shared core: nothing lands in
        # *dest* unless the checksum passed, so a failed download can never
        # leave a half-written DLL for ctypes to load.
        release_assets.fetch_component(
            COMPONENT,
            dest,
            progress=progress,
            label="Downloading the mpv playback engine...",
        )
    except release_assets.ReleaseAssetError as exc:
        raise MpvInstallError(str(exc)) from exc

    dll = dest / DLL_NAME
    if not dll.is_file():
        raise MpvInstallError(f"{DLL_NAME} was not found in the downloaded mpv pack.")
    if progress is not None:
        progress(1.0, "Done.")
    return dll
