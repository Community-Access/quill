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

``deno`` is the JavaScript runtime yt-dlp needs to solve YouTube's signature
and "n" challenges (with the ``yt-dlp-ejs`` scripts from pyproject's
``youtube`` group). It ships in ``tools/deno`` of the shared runtime and every
portable that plays YouTube, so nothing downloads on first use (owner's rule,
2026-09-27). QUILL never downloads deno at run time, so unlike ffmpeg/libmpv its
pin lives here rather than in a runtime module: the official
github.com/denoland/deno release zip, and the MIT licence text from the same
tag, both SHA-256-pinned.

``copilot`` is the GitHub Copilot CLI, the runtime the Copilot SDK drives as a
child process over JSON-RPC (codex.md sections 2B.2, 9 and 10A.12). It ships
once in the shared runtime at ``tools/copilot``, so the SDK never downloads it
(``COPILOT_CLI_PATH`` + ``COPILOT_SKIP_CLI_DOWNLOAD=1``). The standalone
``copilot-win32-x64.zip`` build holds exactly one file, ``copilot.exe`` (a
self-contained exe: no Node, no supporting files), signed by GitHub, Inc.
Its pin was checked against the release's ``SHA256SUMS.txt``, the GitHub API
asset digest and a local download, which all agreed. **Licence:** the GitHub
Copilot CLI License is proprietary. It permits redistributing the Software only
unmodified, only as part of an application that provides material
functionality beyond it (never standalone), and only with a copy of the licence
included and GitHub's notices retained. So ``copilot.exe`` is never re-signed
or altered (``scripts/code_signing.py`` skips ``tools/copilot``), and the
licence text from the same tag ships beside it as ``COPILOT-CLI-LICENSE.txt``.

``codex`` is the OpenAI Codex app-server, the agent engine of codex.md sections
2 and 5, shipped once in the shared runtime at ``tools/codex`` (decisions 1 and
8). The zipped release asset is fetched (92 MB rather than 284 MB); it holds
exactly one file, the exe, which is staged as ``codex-app-server.exe`` and must
also match the unpacked-exe pin in :mod:`quill.core.ai.codex_binary` -- the
same constant the app checks before every launch. Signed by OpenAI OpCo, LLC
and never re-signed. Apache-2.0: ``LICENSE`` and ``NOTICE`` from the same tag
ship beside it as ``CODEX-LICENSE.txt`` and ``CODEX-NOTICE.txt``.

Usage::

    python scripts/fetch_build_deps.py                 # fetch whatever is missing
    python scripts/fetch_build_deps.py --force         # re-fetch even if present
    python scripts/fetch_build_deps.py --verify-only   # report, download nothing
    python scripts/fetch_build_deps.py --print-paths   # machine-readable NAME=DIR
    python scripts/fetch_build_deps.py --only ffmpeg   # one component
    python scripts/fetch_build_deps.py --only piper    # the preview-generation engine
    python scripts/fetch_build_deps.py --only deno     # YouTube's JS challenge solver
    python scripts/fetch_build_deps.py --only copilot  # the GitHub Copilot CLI runtime
    python scripts/fetch_build_deps.py --only codex    # the OpenAI Codex app-server

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

from quill.core.ai.codex_binary import (  # noqa: E402
    CODEX_APP_SERVER_SHA256,
    CODEX_VERSION,
)
from quill.core.ai.copilot_runtime import (  # noqa: E402
    COPILOT_CLI_VERSION,
    COPILOT_EXE_SHA256,
)
from quill.core.release_assets import (  # noqa: E402
    ASSETS,
    ReleaseAssetError,
    download_verified,
    fetch_component,
)
from quill.core.speech.ffmpeg_install import (  # noqa: E402
    FFMPEG_NOTICE_FILES,
    FFMPEG_PINNED_VERSION,
    _extract_ffmpeg_from_zip,
    ffmpeg_download_source,
    write_license_notices,
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
DENO_DIR_NAME = "deno"
DENO_SENTINEL = "deno.exe"

#: Deno for Windows x64, pinned and verified 2026-09-27: the GitHub release
#: asset digest, the release's own ``.zip.sha256sum`` file and a local
#: download all agreed on this hash. Bump all three constants together.
DENO_VERSION = "2.9.7"
DENO_URL = (
    f"https://github.com/denoland/deno/releases/download/v{DENO_VERSION}/"
    "deno-x86_64-pc-windows-msvc.zip"
)
DENO_SHA256 = "a0c3101b4158d1dfb7d6a78a7bf0f3de80c96bb423c152beec8beb22786f2238"
#: Deno's MIT licence, from the same tag; shipped beside deno.exe.
DENO_LICENSE_URL = f"https://raw.githubusercontent.com/denoland/deno/v{DENO_VERSION}/LICENSE.md"
DENO_LICENSE_SHA256 = "f62497fffecc0852960c8d3e6934b9db86d16396e9b604072e923892cae3a588"
DENO_LICENSE_NAME = "DENO-LICENSE.txt"

COPILOT_DIR_NAME = "copilot"
COPILOT_SENTINEL = "copilot.exe"
#: GitHub Copilot CLI for Windows x64, pinned 2026-10-31: SHA256SUMS.txt, the
#: GitHub API asset digest and a local download agreed on the zip's hash.
#: The version and the unpacked-exe pin live in quill.core.ai.copilot_runtime,
#: which checks the same hash before every launch; bump them there together
#: with the zip and licence hashes here.
COPILOT_VERSION = COPILOT_CLI_VERSION
COPILOT_URL = (
    f"https://github.com/github/copilot-cli/releases/download/v{COPILOT_VERSION}/"
    "copilot-win32-x64.zip"
)
COPILOT_SHA256 = "34e16e9cf47de0e1534920171d6f39fa246638bddbb6ece820870b382bcc061a"
#: The one file in the zip, as staged (172,637,984 bytes for 1.0.105), is held
#: to COPILOT_EXE_SHA256, imported above from quill.core.ai.copilot_runtime.
#: The GitHub Copilot CLI License (proprietary; see the module docstring), from
#: the same tag; shipped beside copilot.exe, as the licence requires.
COPILOT_LICENSE_URL = (
    f"https://raw.githubusercontent.com/github/copilot-cli/v{COPILOT_VERSION}/LICENSE.md"
)
COPILOT_LICENSE_SHA256 = "c694e2d9b3f3bb40704ca9bdc823dc90269999ab4c013dfd8a52c407046074b4"
COPILOT_LICENSE_NAME = "COPILOT-CLI-LICENSE.txt"

CODEX_DIR_NAME = "codex"
CODEX_SENTINEL = "codex-app-server.exe"
#: OpenAI Codex app-server for Windows x64, the zipped asset of the pinned
#: ``rust-v`` tag (the version and the unpacked-exe hash live in
#: quill.core.ai.codex_binary). Pinned 2026-10-31: the GitHub asset digest and
#: a local download agreed on the zip's hash.
CODEX_ARCHIVE_MEMBER = "codex-app-server-x86_64-pc-windows-msvc.exe"
CODEX_URL = (
    f"https://github.com/openai/codex/releases/download/rust-v{CODEX_VERSION}/"
    f"{CODEX_ARCHIVE_MEMBER}.zip"
)
CODEX_SHA256 = "edbdd3d5c74ea5437eb13254131de56d855a95a6bc18c139ecce7e95338e4d63"
#: Apache-2.0 LICENSE and the NOTICE file, from the same tag.
CODEX_LICENSE_URL = f"https://raw.githubusercontent.com/openai/codex/rust-v{CODEX_VERSION}/LICENSE"
CODEX_LICENSE_SHA256 = "d17f227e4df5da1600391338865ce0f3055211760a36688f816941d58232d8dc"
CODEX_LICENSE_NAME = "CODEX-LICENSE.txt"
CODEX_NOTICE_URL = f"https://raw.githubusercontent.com/openai/codex/rust-v{CODEX_VERSION}/NOTICE"
CODEX_NOTICE_SHA256 = "9d71575ecfd9a843fc1677b0efb08053c6ba9fd686a0de1a6f5382fd3c220915"
CODEX_NOTICE_NAME = "CODEX-NOTICE.txt"

COMPONENTS = ("ffmpeg", "libmpv", "piper", "deno", "copilot", "codex")

#: component -> (cache subdirectory, the file that proves it is really staged).
_LAYOUT: dict[str, tuple[str, str]] = {
    "ffmpeg": (FFMPEG_DIR_NAME, FFMPEG_SENTINEL),
    "libmpv": (LIBMPV_DIR_NAME, LIBMPV_SENTINEL),
    "piper": (PIPER_DIR_NAME, PIPER_SENTINEL),
    "deno": (DENO_DIR_NAME, DENO_SENTINEL),
    "copilot": (COPILOT_DIR_NAME, COPILOT_SENTINEL),
    "codex": (CODEX_DIR_NAME, CODEX_SENTINEL),
}

#: component -> the licence/notice files that must sit beside its exe.
_LICENCE_FILES: dict[str, tuple[str, ...]] = {
    "deno": (DENO_LICENSE_NAME,),
    "copilot": (COPILOT_LICENSE_NAME,),
    "codex": (CODEX_LICENSE_NAME, CODEX_NOTICE_NAME),
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


def is_complete(component: str) -> bool:
    """True when *component* is staged together with the licence it ships with."""
    if not is_staged(component):
        return False
    if component == "ffmpeg":
        return ffmpeg_notices_staged(component_dir("ffmpeg"))
    names = _LICENCE_FILES.get(component, ())
    return all((component_dir(component) / name).is_file() for name in names)


def _progress(fraction: float, message: str) -> None:
    # One line per 10% so a long download shows life in a build log without
    # flooding it (build logs are read by humans, and by screen readers).
    pct = int(fraction * 100)
    if pct % 10 == 0:
        print(f"    {pct:3d}%  {message}", flush=True)


def ffmpeg_notices_staged(directory: Path) -> bool:
    """True when every FFmpeg notice file sits in *directory*."""
    return all((directory / name).is_file() for name in FFMPEG_NOTICE_FILES)


def fetch_ffmpeg(*, force: bool = False) -> Path:
    """Stage ffmpeg.exe + ffprobe.exe and FFmpeg's licence into the cache.

    Uses :func:`ffmpeg_download_source`, so this is byte-for-byte the archive
    QUILL's own on-demand ffmpeg install would fetch and verify. The pinned
    build is GPLv3 (``--enable-gpl --enable-version3``; ``ffmpeg -L`` says so),
    so its licence and source offer are staged beside the binaries the same way
    Deno's licence is -- except that FFmpeg's texts are in the package
    (``quill/data/notices/ffmpeg``), so no second download is needed for them,
    and a cache staged before this existed is completed without re-fetching.
    """
    dest = component_dir("ffmpeg")
    if is_staged("ffmpeg") and not force:
        if not ffmpeg_notices_staged(dest):
            write_license_notices(dest)
            print(f"  ffmpeg {FFMPEG_PINNED_VERSION}: added its licence notices at {dest}")
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
        write_license_notices(dest)
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


def fetch_deno(*, force: bool = False) -> Path:
    """Stage deno.exe and its licence text into the cache; return the directory.

    The zip holds exactly one file, ``deno.exe``; anything else in it is
    refused rather than extracted, so a changed upstream layout fails the build
    instead of shipping something unreviewed.
    """
    import zipfile

    dest = component_dir("deno")
    if is_staged("deno") and (dest / DENO_LICENSE_NAME).is_file() and not force:
        print(f"  deno {DENO_VERSION}: already staged at {dest}")
        return dest

    print(f"  deno {DENO_VERSION}: downloading (SHA-256 pinned)...")
    dest.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="quill-build-dep-"))
    try:
        archive = tmp / "deno.zip"
        download_verified(DENO_URL, archive, sha256=DENO_SHA256, progress=_progress)
        with zipfile.ZipFile(archive) as zf:
            names = zf.namelist()
            if names != [DENO_SENTINEL]:
                raise ReleaseAssetError(f"Unexpected deno archive layout: {names!r}")
            (dest / DENO_SENTINEL).write_bytes(zf.read(DENO_SENTINEL))
        download_verified(DENO_LICENSE_URL, dest / DENO_LICENSE_NAME, sha256=DENO_LICENSE_SHA256)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"  deno {DENO_VERSION}: staged at {dest}")
    return dest


def _fetch_single_exe_zip(
    component: str,
    *,
    version: str,
    url: str,
    sha256: str,
    member: str,
    exe_sha256: str,
    licences: tuple[tuple[str, str, str], ...],
    force: bool,
) -> Path:
    """Stage one vendor exe from a one-file zip, plus its licence texts.

    The zip must hold exactly *member*; anything else is refused rather than
    extracted, so a changed upstream layout fails the build instead of shipping
    something unreviewed. The unpacked exe must also hash to *exe_sha256*, and
    is written under a ``.part`` name until it does, so an interrupted or
    mismatched stage never leaves a sentinel behind. *licences* is
    ``(url, sha256, staged name)`` per file.
    """
    import hashlib
    import zipfile

    dest = component_dir(component)
    sentinel = _sentinel(component)
    if is_complete(component) and not force:
        print(f"  {component} {version}: already staged at {dest}")
        return dest

    print(f"  {component} {version}: downloading (SHA-256 pinned)...")
    dest.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="quill-build-dep-"))
    try:
        archive = tmp / f"{component}.zip"
        download_verified(url, archive, sha256=sha256, progress=_progress)
        with zipfile.ZipFile(archive) as zf:
            names = zf.namelist()
            if names != [member]:
                raise ReleaseAssetError(f"Unexpected {component} archive layout: {names!r}")
            part = dest / f"{sentinel}.part"
            digest = hashlib.sha256()
            with zf.open(member) as src, part.open("wb") as out:
                for chunk in iter(lambda: src.read(1024 * 1024), b""):
                    digest.update(chunk)
                    out.write(chunk)
            if digest.hexdigest() != exe_sha256:
                part.unlink(missing_ok=True)
                raise ReleaseAssetError(
                    f"{component}: unpacked {member} does not match its pinned SHA-256 "
                    f"(got {digest.hexdigest()}, expected {exe_sha256})."
                )
            os.replace(part, dest / sentinel)
        for licence_url, licence_sha, name in licences:
            download_verified(licence_url, dest / name, sha256=licence_sha)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"  {component} {version}: staged at {dest}")
    return dest


def fetch_copilot(*, force: bool = False) -> Path:
    """Stage copilot.exe and the GitHub Copilot CLI License; return the directory."""
    return _fetch_single_exe_zip(
        "copilot",
        version=COPILOT_VERSION,
        url=COPILOT_URL,
        sha256=COPILOT_SHA256,
        member=COPILOT_SENTINEL,
        exe_sha256=COPILOT_EXE_SHA256,
        licences=((COPILOT_LICENSE_URL, COPILOT_LICENSE_SHA256, COPILOT_LICENSE_NAME),),
        force=force,
    )


def fetch_codex(*, force: bool = False) -> Path:
    """Stage codex-app-server.exe, its Apache-2.0 licence and NOTICE; return the directory."""
    return _fetch_single_exe_zip(
        "codex",
        version=CODEX_VERSION,
        url=CODEX_URL,
        sha256=CODEX_SHA256,
        member=CODEX_ARCHIVE_MEMBER,
        exe_sha256=CODEX_APP_SERVER_SHA256,
        licences=(
            (CODEX_LICENSE_URL, CODEX_LICENSE_SHA256, CODEX_LICENSE_NAME),
            (CODEX_NOTICE_URL, CODEX_NOTICE_SHA256, CODEX_NOTICE_NAME),
        ),
        force=force,
    )


def fetch_all(components: tuple[str, ...], *, force: bool = False) -> dict[str, Path]:
    staged: dict[str, Path] = {}
    for component in components:
        if component == "ffmpeg":
            staged[component] = fetch_ffmpeg(force=force)
        elif component == "libmpv":
            staged[component] = fetch_libmpv(force=force)
        elif component == "piper":
            staged[component] = fetch_piper(force=force)
        elif component == "deno":
            staged[component] = fetch_deno(force=force)
        elif component == "copilot":
            staged[component] = fetch_copilot(force=force)
        elif component == "codex":
            staged[component] = fetch_codex(force=force)
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
        missing = [c for c in components if not is_complete(c)]
        for component in components:
            state = "staged" if is_complete(component) else "MISSING"
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
