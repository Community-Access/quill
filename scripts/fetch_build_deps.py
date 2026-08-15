"""Fetch the external binaries a Windows release build needs.

A release build of Quill Radio (and Audio Studio) must ship ffmpeg and libmpv
*bundled* -- recording and the high-fidelity playback backend are not allowed to
depend on whatever happens to be installed on the listener's machine. Until now
the build scripts demanded ``-FfmpegDir`` / ``-LibmpvDir`` pointing at
directories the builder had assembled by hand, and hard-failed otherwise. That
made the build unreproducible: it only worked on a machine that already had
those binaries staged, and nothing recorded *which* binaries were correct.

This script removes that requirement. It downloads exactly the components QUILL
already pins for its own on-demand installs -- the same URLs, the same SHA-256s,
from QUILL's own ``assets-v1`` release -- into a gitignored local cache, and
prints the staged directories for the build scripts to consume.

Nothing new is trusted: the pins live in
:mod:`quill.core.release_assets`, :mod:`quill.core.speech.ffmpeg_install` and
:mod:`quill.core.speech.piper_install`, which are the single source of truth for
both the runtime downloader and this build-time fetcher. There is no second copy
of a URL or a hash to drift.

``piper`` is staged for *tooling*, not for a release payload: QUILL does not
bundle piper.exe (PRD 10.2.x footprint unbundle), but regenerating the bundled
Piper voice previews with ``scripts/gen_voice_previews.py`` needs the engine, and
a hand-staged copy is exactly the unreproducible setup this script exists to
remove. Windows-only, like the runtime install it reuses.

Usage::

    python scripts/fetch_build_deps.py                 # fetch whatever is missing
    python scripts/fetch_build_deps.py --force         # re-fetch even if present
    python scripts/fetch_build_deps.py --verify-only   # report, download nothing
    python scripts/fetch_build_deps.py --print-paths   # machine-readable NAME=DIR
    python scripts/fetch_build_deps.py --only ffmpeg   # one component
    python scripts/fetch_build_deps.py --only piper    # the preview-generation engine

The cache lives under ``build/deps/`` (already gitignored) unless
``QUILL_BUILD_DEPS_DIR`` overrides it. Re-running is cheap: a component whose
expected file is already present is skipped, so a build script may call this
unconditionally.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from quill.core.release_assets import (  # noqa: E402
    ASSETS,
    ReleaseAssetError,
    download_verified,
    fetch_component,
)
from quill.core.speech.ffmpeg_install import (  # noqa: E402
    FFMPEG_PINNED_VERSION,
    _extract_ffmpeg_from_zip,
    ffmpeg_download_source,
)
from quill.core.speech.piper_install import (  # noqa: E402
    PIPER_RELEASE_TAG,
    PiperInstallError,
    install_piper,
    piper_install_supported,
)

#: Subdirectory names the build scripts expect, and the file that proves the
#: component is really staged (not a half-finished download).
FFMPEG_DIR_NAME = "ffmpeg"
FFMPEG_SENTINEL = "ffmpeg.exe"
LIBMPV_DIR_NAME = "mpv"
LIBMPV_SENTINEL = "libmpv-2.dll"
PIPER_DIR_NAME = "piper"
PIPER_SENTINEL = "piper.exe"

COMPONENTS = ("ffmpeg", "libmpv", "piper")

#: component -> (cache subdirectory, the file that proves it is really staged).
_LAYOUT: dict[str, tuple[str, str]] = {
    "ffmpeg": (FFMPEG_DIR_NAME, FFMPEG_SENTINEL),
    "libmpv": (LIBMPV_DIR_NAME, LIBMPV_SENTINEL),
    "piper": (PIPER_DIR_NAME, PIPER_SENTINEL),
}


def deps_root() -> Path:
    """The cache directory, overridable with ``QUILL_BUILD_DEPS_DIR``."""
    override = os.environ.get("QUILL_BUILD_DEPS_DIR", "").strip()
    return Path(override) if override else _REPO_ROOT / "build" / "deps"


def component_dir(component: str) -> Path:
    return deps_root() / _LAYOUT[component][0]


def _sentinel(component: str) -> str:
    return _LAYOUT[component][1]


def is_staged(component: str) -> bool:
    """True when *component* is already usable in the cache."""
    return (component_dir(component) / _sentinel(component)).is_file()


def _progress(fraction: float, message: str) -> None:
    # One line per 10% so a long download shows life in a build log without
    # flooding it (build logs are read by humans, and by screen readers).
    pct = int(fraction * 100)
    if pct % 10 == 0:
        print(f"    {pct:3d}%  {message}", flush=True)


def fetch_ffmpeg(*, force: bool = False) -> Path:
    """Stage ffmpeg.exe + ffprobe.exe into the cache; return their directory.

    Uses :func:`ffmpeg_download_source`, so this is byte-for-byte the archive
    QUILL's own on-demand ffmpeg install would fetch and verify.
    """
    dest = component_dir("ffmpeg")
    if is_staged("ffmpeg") and not force:
        print(f"  ffmpeg {FFMPEG_PINNED_VERSION}: already staged at {dest}")
        return dest

    url, sha256 = ffmpeg_download_source()
    print(f"  ffmpeg {FFMPEG_PINNED_VERSION}: downloading (SHA-256 pinned)...")
    dest.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="quill-build-dep-"))
    try:
        archive = tmp / "ffmpeg.zip"
        download_verified(url, archive, sha256=sha256, progress=_progress)
        _extract_ffmpeg_from_zip(archive, dest)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"  ffmpeg {FFMPEG_PINNED_VERSION}: staged at {dest}")
    return dest


def fetch_libmpv(*, force: bool = False) -> Path:
    """Stage libmpv-2.dll (and its licence/source-offer files) into the cache.

    The licence texts and ``README-SOURCE.txt`` inside the pack are part of the
    GPL compliance posture, so the whole pack is unpacked, not just the DLL.
    """
    dest = component_dir("libmpv")
    asset = ASSETS["libmpv"]
    if is_staged("libmpv") and not force:
        print(f"  libmpv ({asset.version}): already staged at {dest}")
        return dest

    print(f"  libmpv ({asset.version}): downloading (SHA-256 pinned)...")
    dest.mkdir(parents=True, exist_ok=True)
    fetch_component("libmpv", dest, progress=_progress, label="libmpv")
    print(f"  libmpv ({asset.version}): staged at {dest}")
    return dest


def fetch_piper(*, force: bool = False) -> Path:
    """Stage piper.exe (plus its DLLs and espeak-ng-data) into the cache.

    Delegates to :func:`quill.core.speech.piper_install.install_piper`, so this
    is byte-for-byte the archive QUILL's own on-demand Piper install fetches and
    SHA-256-verifies -- the pinned tag and hash are not restated here.
    """
    dest = component_dir("piper")
    if is_staged("piper") and not force:
        print(f"  piper {PIPER_RELEASE_TAG}: already staged at {dest}")
        return dest

    if not piper_install_supported():
        raise ReleaseAssetError(
            "Staging Piper is Windows-only (the pinned release ships a Windows AMD64 zip). "
            "On macOS/Linux install Piper yourself and pass --piper-exe to gen_voice_previews.py."
        )
    print(f"  piper {PIPER_RELEASE_TAG}: downloading (SHA-256 pinned)...")
    try:
        install_piper(_progress, dest_dir=dest)
    except PiperInstallError as exc:
        raise ReleaseAssetError(f"Could not stage Piper: {exc}") from exc
    print(f"  piper {PIPER_RELEASE_TAG}: staged at {dest}")
    return dest


def fetch_all(components: tuple[str, ...], *, force: bool = False) -> dict[str, Path]:
    staged: dict[str, Path] = {}
    for component in components:
        if component == "ffmpeg":
            staged[component] = fetch_ffmpeg(force=force)
        elif component == "libmpv":
            staged[component] = fetch_libmpv(force=force)
        elif component == "piper":
            staged[component] = fetch_piper(force=force)
        else:  # pragma: no cover - argparse constrains the choices
            raise ReleaseAssetError(f"Unknown build dependency: {component!r}")
    return staged


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force", action="store_true", help="Re-download even when already staged."
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Report what is staged and exit non-zero if anything is missing. Downloads nothing.",
    )
    parser.add_argument(
        "--print-paths",
        action="store_true",
        help="Print NAME=DIR lines only, for a build script to consume.",
    )
    parser.add_argument(
        "--only",
        choices=COMPONENTS,
        action="append",
        help="Fetch just this component (repeatable). Defaults to all.",
    )
    args = parser.parse_args(argv)
    components = tuple(args.only) if args.only else COMPONENTS

    if args.verify_only:
        missing = [c for c in components if not is_staged(c)]
        for component in components:
            state = "staged" if is_staged(component) else "MISSING"
            print(f"{component}: {state} ({component_dir(component)})")
        if missing:
            print(
                f"\nMissing: {', '.join(missing)}. Run: python scripts/fetch_build_deps.py",
                file=sys.stderr,
            )
            return 1
        return 0

    if not args.print_paths:
        print(f"Staging build dependencies into {deps_root()}")
    try:
        staged = fetch_all(components, force=args.force)
    except ReleaseAssetError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.print_paths:
        for component, path in staged.items():
            print(f"{component}={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
