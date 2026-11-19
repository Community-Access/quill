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

``copilot`` is the native runtime library used by Microsoft Copilot SDK 2.0.
The SDK can download its runtime automatically, but QUILL stages only the
verified ``runtime.node`` in the shared runtime at ``tools/copilot``; no CLI
executable, wrapper, shell, plugins, search tools, or SDK cache is shipped.
At build time the SDK's pinned runtime downloader verifies the official
release checksum, and QUILL checks the library's SHA-256 again before staging.
At run time the app verifies the same pin and points the SDK at that library,
so a missing or changed file fails clearly without a download or PATH fallback.
**Licence:** the native library remains covered by GitHub's Copilot CLI
redistribution licence. The unchanged library and the licence text ship
together; the runtime file is vendor-signed and is never re-signed.

``codex`` is the OpenAI Codex app-server, the agent engine of codex.md sections
2 and 5, shipped once in the shared runtime at ``tools/codex`` (decisions 1 and
8). The zipped release asset is fetched (92 MB rather than 284 MB); it holds
exactly one file, the exe, which is staged as ``codex-app-server.exe`` and must
also match the unpacked-exe pin in :mod:`quill.core.ai.codex_binary` -- the
same constant the app checks before every launch. Signed by OpenAI OpCo, LLC
and never re-signed. Apache-2.0: ``LICENSE`` and ``NOTICE`` from the same tag
ship beside it as ``CODEX-LICENSE.txt`` and ``CODEX-NOTICE.txt``.

``phonon`` is Gradium's Phonon 31m English text-to-speech model with its 37
English voices (phonon-voices-prd.md section 6), shipped once in the shared runtime at
``phonon-models/en`` so Read Aloud and Studio narration never download it. Both
Hugging Face repos are pinned to a commit and every file to a SHA-256 in
``scripts/phonon_model_pins.json``. Apache-2.0, and neither repo carries a
LICENSE file, so the model card travels beside the weights as
``MODEL-CARD.md``: it is the licence statement. The voice catalogue is
filtered to the English voices this model speaks.

``nodejs``, ``language-servers`` and ``ripgrep`` are IntelliSense layer 4
(docs/design/intellisense.md): the official Node 24 LTS, the VS Code HTML,
CSS, JSON and Markdown servers with typescript-language-server, TypeScript and
Pyright installed by ``npm ci --ignore-scripts`` from a committed lock, and
ripgrep. Their pins, licences and reasons are in
:mod:`scripts.fetch_language_servers`. All three ship in every shared runtime.

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
    python scripts/fetch_build_deps.py --only phonon   # Phonon 31m voices for Read Aloud
    python scripts/fetch_build_deps.py --only nodejs --only language-servers --only ripgrep
    # Playground CLI, PHP.wasm and WordPress core for the Practice Site:
    python scripts/fetch_build_deps.py --only wp-playground-cli

The cache lives under ``build/deps/`` (already gitignored) unless
``QUILL_BUILD_DEPS_DIR`` overrides it. Re-running is cheap: a component whose
expected file is already present is skipped, so a build script may call this
unconditionally.
"""

from __future__ import annotations

import argparse
import json
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
    COPILOT_RUNTIME_NODE_SHA256,
    COPILOT_RUNTIME_PLATFORM,
    COPILOT_RUNTIME_VERSION,
    copilot_runtime_matches_pin,
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
from quill.core.wordpress.workbench_practice import (  # noqa: E402
    PLAYGROUND_CLI_VERSION,
    PRACTICE_PHP_VERSION,
    PRACTICE_WORDPRESS_VERSION,
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
COPILOT_SENTINEL = "runtime.node"
COPILOT_RUNTIME_NODE = "runtime.node"
COPILOT_VERSION = COPILOT_RUNTIME_VERSION
COPILOT_PLATFORM = COPILOT_RUNTIME_PLATFORM
COPILOT_LICENSE_SHA256 = "b9680937e10425bf19862908856c16ed274e6b81a1368bd62be7a757eab21628"
COPILOT_LICENSE_SOURCE = (
    _REPO_ROOT / "quill" / "data" / "third_party" / "licenses" / "GitHub-Copilot-CLI-License.txt"
)
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

PHONON_DIR_NAME = "phonon-31m-en"
PHONON_SENTINEL = "model.q8.gguf"
PHONON_MODEL_REPO = "gradium/phonon-31m-en"
PHONON_MODEL_REVISION = "8c64b55ec301728e2d1695bfea87a08a267d0c2d"
PHONON_VOICES_REPO = "gradium/phonon-voices"
PHONON_VOICES_REVISION = "da6c9ec0d47be8df5c87c730a3aa97187f3229c3"
PHONON_PINS = Path(__file__).with_name("phonon_model_pins.json")
PHONON_LICENSE_NAME = "MODEL-CARD.md"

COMPONENTS = (
    "ffmpeg",
    "libmpv",
    "piper",
    "deno",
    "copilot",
    "codex",
    "phonon",
    "nodejs",
    "language-servers",
    "ripgrep",
    "wp-playground-cli",
)

#: component -> (cache subdirectory, the file that proves it is really staged).
_LAYOUT: dict[str, tuple[str, str]] = {
    "ffmpeg": (FFMPEG_DIR_NAME, FFMPEG_SENTINEL),
    "libmpv": (LIBMPV_DIR_NAME, LIBMPV_SENTINEL),
    "piper": (PIPER_DIR_NAME, PIPER_SENTINEL),
    "deno": (DENO_DIR_NAME, DENO_SENTINEL),
    "copilot": (COPILOT_DIR_NAME, COPILOT_SENTINEL),
    "codex": (CODEX_DIR_NAME, CODEX_SENTINEL),
    "phonon": (PHONON_DIR_NAME, PHONON_SENTINEL),
    "nodejs": ("nodejs", "node.exe"),
    "language-servers": ("language-servers", "LANGUAGE-SERVERS-LICENSES.txt"),
    "ripgrep": ("ripgrep", "rg.exe"),
    "wp-playground-cli": ("wp-playground-cli", "PLAYGROUND-LICENSES.txt"),
}

#: component -> the licence/notice files that must sit beside its exe.
_LICENCE_FILES: dict[str, tuple[str, ...]] = {
    "deno": (DENO_LICENSE_NAME,),
    "copilot": (COPILOT_LICENSE_NAME,),
    "codex": (CODEX_LICENSE_NAME, CODEX_NOTICE_NAME),
    "phonon": (PHONON_LICENSE_NAME, "voices.jsonl"),
    "nodejs": ("NODE-LICENSE.txt",),
    "ripgrep": ("COPYING", "LICENSE-MIT", "UNLICENSE"),
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
    if component == "copilot" and not copilot_runtime_staged(component_dir("copilot")):
        return False
    if component == "wp-playground-cli" and not _playground_cli_pin_is_staged():
        return False
    names = _LICENCE_FILES.get(component, ())
    return all((component_dir(component) / name).is_file() for name in names)


def _playground_cli_pin_is_staged() -> bool:
    """The cache is complete only when its CLI, PHP and WordPress pins match."""
    source_package = _REPO_ROOT / "scripts" / "wp_playground" / "package.json"
    staged = component_dir("wp-playground-cli")
    try:
        source = json.loads(source_package.read_text(encoding="utf-8"))
        expected = source.get("dependencies", {}).get("@wp-playground/cli")
        pruned_version = (
            (staged / ".quill-playground-pruned-v1").read_text(encoding="utf-8").strip()
        )
        lock = json.loads((staged / "package-lock.json").read_text(encoding="utf-8"))
        resolved = lock.get("packages", {}).get("node_modules/@wp-playground/cli", {})
        package = json.loads(
            (staged / "node_modules" / "@wp-playground" / "cli" / "package.json").read_text(
                encoding="utf-8"
            )
        )
        php_root = staged / "node_modules" / "@php-wasm"
        keep_php = f"node-{PRACTICE_PHP_VERSION.replace('.', '-')}"
        php_packages = {
            path.name
            for path in php_root.iterdir()
            if path.is_dir()
            and path.name.startswith("node-")
            and path.name[5:].replace("-", "").isdigit()
        }
    except (OSError, TypeError, ValueError):
        return False
    wordpress_archive = staged / f"wordpress-{PRACTICE_WORDPRESS_VERSION}.zip"
    return (
        bool(expected)
        and pruned_version == PLAYGROUND_CLI_VERSION
        and resolved.get("version") == expected
        and package.get("version") == expected
        and php_packages == {keep_php}
        and (php_root / keep_php / "package.json").is_file()
        and (
            staged / "node_modules" / "@wp-playground" / "cli" / "sqlite-database-integration.zip"
        ).is_file()
        and wordpress_archive.is_file()
    )


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


def _sdk_copilot_runtime_path(*, force: bool = False) -> Path:
    """Provision the SDK-pinned runtime via its checksum-verifying downloader."""
    try:
        from copilot._cli_download import ensure_runtime_wrapper
        from copilot._cli_version import CLI_VERSION, get_runtime_platform
    except ImportError as exc:
        raise ReleaseAssetError(
            "The microsoft-copilot-sdk build dependency is required to stage Copilot."
        ) from exc

    if CLI_VERSION != COPILOT_RUNTIME_VERSION:
        raise ReleaseAssetError(
            f"Copilot SDK runtime version {CLI_VERSION!r} does not match the pinned "
            f"version {COPILOT_RUNTIME_VERSION}."
        )
    if get_runtime_platform() != COPILOT_PLATFORM:
        raise ReleaseAssetError(
            f"Copilot runtime platform {get_runtime_platform()!r} does not match "
            f"the pinned platform {COPILOT_PLATFORM!r}."
        )

    wrapper = Path(ensure_runtime_wrapper(force=force))
    runtime = wrapper.with_name(COPILOT_RUNTIME_NODE)
    if not copilot_runtime_matches_pin(runtime):
        raise ReleaseAssetError(f"Copilot SDK runtime {runtime} does not match its pinned SHA-256.")
    return runtime


def _copilot_license_matches_pin(path: Path) -> bool:
    import hashlib

    try:
        return hashlib.sha256(path.read_bytes()).hexdigest() == COPILOT_LICENSE_SHA256
    except OSError:
        return False


def copilot_runtime_staged(directory: Path) -> bool:
    """True when only the pinned native runtime and its required licence are staged."""
    runtime = directory / COPILOT_RUNTIME_NODE
    license_path = directory / COPILOT_LICENSE_NAME
    try:
        names = {path.name for path in directory.iterdir()}
    except OSError:
        return False
    expected = {COPILOT_RUNTIME_NODE, COPILOT_LICENSE_NAME}
    return (
        names == expected
        and runtime.is_file()
        and license_path.is_file()
        and copilot_runtime_matches_pin(runtime)
        and _copilot_license_matches_pin(license_path)
    )


def fetch_copilot(*, force: bool = False) -> Path:
    """Stage only the SDK's pinned native runtime library and its licence."""
    dest = component_dir("copilot")
    if is_complete("copilot") and not force:
        print(f"  copilot runtime {COPILOT_VERSION}: already staged at {dest}")
        return dest

    runtime = _sdk_copilot_runtime_path(force=force)
    if not _copilot_license_matches_pin(COPILOT_LICENSE_SOURCE):
        raise ReleaseAssetError(
            f"Copilot runtime licence {COPILOT_LICENSE_SOURCE} does not match its pinned SHA-256."
        )

    dest.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".copilot-staging-", dir=dest.parent))
    try:
        shutil.copyfile(runtime, staging / COPILOT_RUNTIME_NODE)
        shutil.copyfile(COPILOT_LICENSE_SOURCE, staging / COPILOT_LICENSE_NAME)
        if not copilot_runtime_matches_pin(staging / COPILOT_RUNTIME_NODE):
            raise ReleaseAssetError(
                f"The staged Copilot runtime does not match its pinned SHA-256 "
                f"({COPILOT_RUNTIME_NODE_SHA256})."
            )
        if not _copilot_license_matches_pin(staging / COPILOT_LICENSE_NAME):
            raise ReleaseAssetError("The staged Copilot runtime licence failed its pin check.")
        if dest.exists():
            shutil.rmtree(dest)
        os.replace(staging, dest)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    print(f"  copilot runtime {COPILOT_VERSION}: staged at {dest}")
    return dest


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


def _hf_url(repo: str, revision: str, name: str) -> str:
    return f"https://huggingface.co/{repo}/resolve/{revision}/{name}"


def fetch_phonon(*, force: bool = False) -> Path:
    """Stage Phonon 31m English and its English voices; return the directory.

    Plain HTTPS from the pinned commits, every file checked against
    ``phonon_model_pins.json`` -- no Hugging Face client, no token. The
    catalogue is rewritten to the English entries only, after its own hash is
    checked, so ``voices.jsonl`` lists exactly the voice files staged beside it.
    """
    import json

    dest = component_dir("phonon")
    if is_complete("phonon") and not force:
        print(f"  phonon 31m: already staged at {dest}")
        return dest

    pins = json.loads(PHONON_PINS.read_text(encoding="utf-8"))
    print("  phonon 31m: downloading model and English voices (SHA-256 pinned)...")
    tmp = Path(tempfile.mkdtemp(prefix="quill-build-dep-"))
    try:
        stage = tmp / PHONON_DIR_NAME
        (stage / "voices").mkdir(parents=True)
        for name, sha in pins["model"].items():
            target = PHONON_LICENSE_NAME if name == "README.md" else name
            download_verified(
                _hf_url(PHONON_MODEL_REPO, PHONON_MODEL_REVISION, name),
                stage / target,
                sha256=sha,
                progress=_progress if name.endswith(".gguf") else None,
            )
        catalogue = tmp / "voices-all.jsonl"
        download_verified(
            _hf_url(PHONON_VOICES_REPO, PHONON_VOICES_REVISION, "voices.jsonl"),
            catalogue,
            sha256=pins["voices.jsonl"],
        )
        voices = pins["voices"]
        kept: list[str] = []
        for line in catalogue.read_text(encoding="utf-8").splitlines():
            if line.strip() and json.loads(line).get("filename") in voices:
                kept.append(line)
        if len(kept) != len(voices):
            raise ReleaseAssetError(
                f"Phonon catalogue lists {len(kept)} of the {len(voices)} pinned voices"
            )
        for name, sha in voices.items():
            download_verified(
                _hf_url(PHONON_VOICES_REPO, PHONON_VOICES_REVISION, name),
                stage / name,
                sha256=sha,
            )
        (stage / "voices.jsonl").write_bytes(("\n".join(kept) + "\n").encode("utf-8"))
        if dest.exists():
            shutil.rmtree(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(stage), str(dest))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"  phonon 31m: staged at {dest}")
    return dest


def _fetch_layer4(component: str, *, force: bool = False) -> Path:
    """Node, the language servers or ripgrep (scripts/fetch_language_servers.py)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import fetch_language_servers as layer4

    dest = component_dir(component)
    if is_complete(component) and not force:
        print(f"  {component}: already staged at {dest}")
        return dest
    print(f"  {component}: staging (SHA-256 or lockfile pinned)...")
    npm = deps_root() / "nodejs-npm"
    needs_npm = component in ("language-servers", "wp-playground-cli")
    if component == "nodejs" or (needs_npm and not npm.is_dir()):
        layer4.fetch_nodejs(component_dir("nodejs"), npm, progress=_progress)
    if component == "language-servers":
        layer4.fetch_language_servers(dest, component_dir("nodejs") / "node.exe", npm)
    if component == "ripgrep":
        layer4.fetch_ripgrep(dest, progress=_progress)
    if component == "wp-playground-cli":
        layer4.fetch_wp_playground(dest, component_dir("nodejs") / "node.exe", npm)
    print(f"  {component}: staged at {dest}")
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
        elif component == "deno":
            staged[component] = fetch_deno(force=force)
        elif component == "copilot":
            staged[component] = fetch_copilot(force=force)
        elif component == "codex":
            staged[component] = fetch_codex(force=force)
        elif component == "phonon":
            staged[component] = fetch_phonon(force=force)
        elif component in ("nodejs", "language-servers", "ripgrep", "wp-playground-cli"):
            staged[component] = _fetch_layer4(component, force=force)
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
