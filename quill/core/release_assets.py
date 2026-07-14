"""On-demand fetch of redistributable runtime components from QUILL's own GitHub
release assets — the controlled, pinned, SHA-256-verified store (PRD 10.2.4).

Components QUILL is licensed to redistribute are uploaded to a Community-Access
release tag and pinned here by SHA-256. The app can download + verify + unpack one
on demand (e.g. to recover a missing offline speech engine), as a **supplement**
to the installer bundling — capability never depends on a download succeeding, so
the bundled copy remains the default and this is the recovery/optional path.

Reliability (PRD 10.2.3): pinned URL + SHA-256 (moving refs / placeholder hashes
refused), HTTPS enforced, retry-with-backoff and **resumable** download (HTTP
Range), atomic verified install (download to a temp dir, verify, then copy in),
and a clean error on any failure so the caller can degrade gracefully.

GATE-9 / network-egress: the only outbound call site is ``_download_resumable``;
it runs on an explicit user action and is blocked in Safe Mode. No ``wx`` imports.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
import time
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from quill.core.error_codes import CodedError

# (fraction 0.0-1.0, human message) — same shape as the speech ProgressCallback.
ProgressCallback = Callable[[float, str], None]

# Assets live on a dedicated, not-latest release tag so asset churn never touches
# the product release or the autoupdate feed (the tag does not match ``v*``).
_RELEASE_BASE = "https://github.com/Community-Access/quill/releases/download"

_CHUNK = 1024 * 1024


class ReleaseAssetError(CodedError):
    """A redistributable component could not be fetched/verified/installed."""

    code = "QUILL-RELEASE-ASSET-FAILED"


class DownloadCancelled(ReleaseAssetError):
    """The user cancelled the download. Never retried; surfaced to the caller."""


@dataclass(frozen=True, slots=True)
class ReleaseAsset:
    """One pinned, SHA-256-verified component hosted on a QUILL release tag."""

    component: str
    tag: str
    filename: str
    sha256: str
    expect_member: str = ""  # a file the unpacked archive must contain
    license: str = ""
    # Upstream version of the bundled content. Recorded so a future update check
    # can notice a newer pinned version and offer it to the user (PRD 10.2.x).
    version: str = ""

    @property
    def url(self) -> str:
        return f"{_RELEASE_BASE}/{self.tag}/{self.filename}"


# Pinned manifest. Add an entry only for a component we are licensed to
# redistribute (e.g. MIT). Each is verified by SHA-256 before use, so the host is
# never blindly trusted. License-unclear components (DECtalk, eSpeak GPL) are NOT
# listed until redistribution is cleared (PRD 10.2.4 open questions).
ASSETS: dict[str, ReleaseAsset] = {
    "whispercpp": ReleaseAsset(
        component="whispercpp",
        tag="assets-v1",
        filename="whisper-bin-x64.zip",
        sha256="7d8be46ecd31828e1eb7a2ecdd0d6b314feafd82163038ab6092594b0a063539",
        expect_member="whisper-cli.exe",
        license="MIT (ggml-org/whisper.cpp v1.9.1)",
        version="v1.9.1",
    ),
    "kokoro": ReleaseAsset(
        component="kokoro",
        tag="assets-v1",
        filename="kokoro-models.zip",
        sha256="c272fd63e98eb18970b14cf1f0ff83becf84d6d874344a37bc52d697e8ddd6c0",
        expect_member="kokoro-v1.0.int8.onnx",
        license="Apache-2.0 (kokoro-onnx model-files-v1.0); already redistributed by QUILL",
        version="model-files-v1.0",
    ),
    # Vosk (Apache-2.0): the optional very-low-resource offline STT engine, hosted
    # as a pip wheel (it bundles libvosk). Unlike the other assets it is a wheel, so
    # it is fetched via fetch_file() (no unpack) and handed to `pip install --no-index`
    # (see engine_install.install_vosk). The Windows wheel is the self-hosted primary;
    # non-Windows falls back to PyPI. This is a byte-identical re-publish of the upstream
    # PyPI wheel (same SHA-256), so `pip install --no-index` of our copy equals a PyPI
    # install. To bump the version, upload the new wheel to assets-v1 and update
    # filename/sha256/version here.
    "vosk": ReleaseAsset(
        component="vosk",
        tag="assets-v1",
        filename="vosk-0.3.45-py3-none-win_amd64.whl",
        sha256="6994ddc68556c7e5730c3b6f6bad13320e3519b13ce3ed2aa25a86724e7c10ac",
        license="Apache-2.0 (alphacep/vosk-api); byte-identical re-publish of the PyPI wheel",
        version="0.3.45",
    ),
    # Braille pack (footprint unbundle): liblouis runtime (lou_translate.exe +
    # liblouis.dll), UEB/BRF translation tables, and brf_profiles.json. ~68 MB
    # uncompressed (highly compressible tables), so it is fetched on demand
    # instead of bundled. A byte-identical re-publish of QUILL's own liblouis
    # pack (LGPL-3.0/GPL-3.0; source and licenses ship inside the zip). Extracted
    # into the app-data braille dir and found by quill.core.braille_pack.
    "braille": ReleaseAsset(
        component="braille",
        tag="assets-v1",
        filename="braille-pack.zip",
        sha256="1f7ce36f0b9bd0564e83d88f7585fb843ff221b8c93d66f5bb90431235c378a4",
        expect_member="lou_translate.exe",
        license="LGPL-3.0/GPL-3.0 (liblouis); QUILL braille pack",
        version="quill-braille-pack",
    ),
    # libmpv (the mpv playback library): the Audio Studio player's optional
    # high-fidelity backend (gapless, exact seeking). Stable-anchored: the
    # shinchiro 2025-12-28 weekly (mpv git a58dd8a), the first prebuilt
    # published after the v0.41.0 stable tag — upstream publishes no DLL of
    # the exact tag, so this is the closest stable artifact (v0.41.0 + one
    # week of post-release fixes; DLL byte-identical to the upstream asset).
    # mpv is GPLv2+; the prebuilt is effectively GPLv3, so the zip ships the
    # GPL texts, mpv's Copyright, and a corresponding-source offer
    # (README-SOURCE.txt) — same posture as the GPL liblouis pack. Never
    # bundled; loaded via ctypes only when the user installs it.
    "libmpv": ReleaseAsset(
        component="libmpv",
        tag="assets-v1",
        filename="libmpv-pack.zip",
        sha256="637c9a3db848f0cb156edf2d869bf5f658ce399f98f1e31b57bda8e2f2c0db9f",
        expect_member="libmpv-2.dll",
        license="GPLv3 (mpv GPLv2+; shinchiro mpv-winbuild prebuilt); source offer in zip",
        version="mpv v0.41.0-era (git a58dd8a, 2025-12-28 weekly)",
    ),
    # Optional Hunspell spell-check dictionaries (PRD 10.2.4). English (en_US) is
    # always bundled inside pyenchant; these add other languages on demand. Each
    # zip holds <lang>.dic/.aff plus the upstream license/readme, byte-pinned to a
    # LibreOffice/dictionaries commit. Discovered at runtime via ENCHANT_CONFIG_DIR
    # (see quill/core/spellcheck.py). The GPL/LGPL/MPL terms permit redistribution
    # with a source offer; the upstream README/LICENSE ships inside each zip.
    "spell-es_ES": ReleaseAsset(
        component="spell-es_ES",
        tag="assets-v1",
        filename="spell-es_ES.zip",
        sha256="8e3a64262d4fc59d5328e6864e24004c5b5559fe9889061c3c7927169b27343c",
        expect_member="es_ES.dic",
        license="GPL-3.0/LGPL-3.0/MPL-2.0 (LibreOffice es_ES / RLA-ES)",
        version="libreoffice-dictionaries 93d537d",
    ),
    "spell-fr_FR": ReleaseAsset(
        component="spell-fr_FR",
        tag="assets-v1",
        filename="spell-fr_FR.zip",
        sha256="012e2cda35ed75b767e77be07d1ac902fb99fc02bbfc2655978baa690c0ad07f",
        expect_member="fr_FR.dic",
        license="MPL-2.0/GPL-3.0/LGPL-3.0 (LibreOffice fr_FR / Dicollecte)",
        version="libreoffice-dictionaries 93d537d",
    ),
    # MathCAT (real math speech, docs/planning/math.md step 3): daisy/MathCATForC
    # publishes prebuilt Windows DLLs, so no Rust build is needed at all -- just
    # a byte-identical re-publish of their libmathcat_c.dll (64-bit Windows) plus
    # the Rules/ speech data it needs at runtime, repackaged into one zip. Loaded
    # via ctypes only when the user installs it (quill.core.math.mathcat_engine);
    # quill.core.math.navigator's template-based reading is the fallback when it
    # is absent.
    "mathcat": ReleaseAsset(
        component="mathcat",
        tag="assets-v1",
        filename="mathcat-pack.zip",
        sha256="5ce409c8b720978f1994e0f125e26d786519d4d16eec4482d10d9380413273f8",
        expect_member="libmathcat_c.dll",
        license="MIT (daisy/MathCATForC); byte-identical re-publish",
        version="v0.7.6-beta.5",
    ),
    # Piper (rhasspy/piper 2023.11.14-2 Windows AMD64): the neural Read Aloud
    # engine, unbundled from the installer (PRD 10.2.x). A byte-identical
    # re-publish (22,477,236 bytes) of the upstream release, self-hosted here so an
    # upstream outage or removal can't break Piper; piper_install prefers this copy
    # (_maybe_fetch_hosted_piper) and falls back to the rhasspy asset. SHA-256
    # pinned and verified.
    "piper": ReleaseAsset(
        component="piper",
        tag="assets-v1",
        filename="piper_windows_amd64.zip",
        sha256="f3c58906402b24f3a96d92145f58acba6d86c9b5db896d207f78dc80811efcea",
        expect_member="piper/piper.exe",
        license="MIT (rhasspy/piper); byte-identical re-publish of the upstream release",
        version="2023.11.14-2",
    ),
    # -------------------------------------------------------------------
    # git / gh (docs/planning/github.md section 2: bundling git and the
    # GitHub CLI so local-git accessibility (quill.core.local_git) and the
    # gh-CLI bridge (quill.core.github.gh_bridge) work for a user who has
    # never installed either). quill.core.git_binaries.resolve_git/resolve_gh
    # already prefer a system install on PATH first -- these three entries
    # exist purely as the fallback for someone who has neither.
    #
    # git-windows is repackaged from upstream MinGit: the official zip spreads
    # cmd/, mingw64/, etc/, usr/ as separate top-level folders with no common
    # parent, but fetch_component() only copies expect_member's immediate
    # *parent folder* into the target (not the whole archive) -- so the raw
    # MinGit zip would silently drop mingw64/etc/usr, which cmd/git.exe needs
    # at runtime. Fixed by re-zipping the full MinGit tree under one wrapper
    # folder ("git/"). expect_member is deliberately "git/LICENSE.txt" (a
    # file that sits directly inside the wrapper, as siblings of cmd/, etc/,
    # mingw64/, usr/) rather than "git/cmd/git.exe" -- anchoring on git.exe
    # itself would resolve hits[0].parent to the "cmd/" folder and only copy
    # that, reproducing the exact bug this repackaging exists to avoid. The
    # installed layout is therefore <target>/cmd/git.exe with <target>/etc,
    # mingw64, usr as siblings -- see quill.core.git_binaries's
    # _vendor_candidate("git"), which expects the nested "cmd/git.exe" path.
    # gh-windows/gh-macos needed no such restructuring (their expect_member's
    # parent folder already contains nothing else).
    "git-windows": ReleaseAsset(
        component="git-windows",
        tag="assets-v1",
        filename="git-windows-pack.zip",
        sha256="bb601200c17139b63b7665d75a85dd2d1ac989119a468c92e972554f4b74a62e",
        expect_member="git/LICENSE.txt",
        license="GPL-2.0 (Git for Windows MinGit; portable, no installer)",
        version="v2.55.0.2",
    ),
    "gh-windows": ReleaseAsset(
        component="gh-windows",
        tag="assets-v1",
        filename="gh-windows-pack.zip",
        sha256="dcc5c3e87454c92eca40923d5a52745dd6949163003bfb8417fb9a77057a340b",
        expect_member="bin/gh.exe",
        license="MIT (cli/cli, the official GitHub CLI)",
        version="v2.96.0",
    ),
    "gh-macos": ReleaseAsset(
        component="gh-macos",
        tag="assets-v1",
        filename="gh-macos-pack.zip",
        sha256="9c1f4d6aa261a09a6f6a11188ee93249d6761d27eff838663d408835a67f245e",
        expect_member="bin/gh",
        license="MIT (cli/cli, the official GitHub CLI)",
        version="v2.96.0",
    ),
}


def is_pinned(asset: ReleaseAsset) -> bool:
    """True only when the asset is safely pinned: a real 64-hex SHA-256 and a URL
    that is not a moving ref (``latest``/``head``/``main``/``master``)."""
    sha = (asset.sha256 or "").strip().lower()
    if len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
        return False
    low = asset.url.lower()
    return not any(seg in low for seg in ("/latest/", "/head/", "/main/", "/master/"))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download_resumable(
    url: str,
    dest: Path,
    progress: ProgressCallback | None,
    *,
    retries: int = 4,
    timeout: float = 60.0,
    should_cancel: Callable[[], bool] | None = None,
    label: str = "Downloading...",
) -> None:
    """Download ``url`` to ``dest`` with retry/backoff, resuming a partial file via
    HTTP Range. HTTPS-only. Raises :class:`ReleaseAssetError` after exhausting retries,
    or :class:`DownloadCancelled` immediately if ``should_cancel`` becomes true.

    GATE-9: this is the module's only network egress; callers gate it on an explicit
    user action and Safe Mode.
    """
    if not url.lower().startswith("https://"):
        raise ReleaseAssetError("Refusing a non-HTTPS download URL.")
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            if should_cancel is not None and should_cancel():
                raise DownloadCancelled("Download cancelled.")
            have = dest.stat().st_size if dest.exists() else 0
            request = urllib.request.Request(url)
            if have:
                request.add_header("Range", f"bytes={have}-")
            with urllib.request.urlopen(request, timeout=timeout) as resp:  # noqa: S310 - HTTPS enforced
                status = getattr(resp, "status", 200)
                # If the server ignored Range (200 not 206), restart from zero.
                append = bool(have) and status == 206
                if not append:
                    have = 0
                total = have + int(resp.headers.get("Content-Length") or 0)
                downloaded = have
                with dest.open("ab" if append else "wb") as out:
                    while True:
                        if should_cancel is not None and should_cancel():
                            raise DownloadCancelled("Download cancelled.")
                        chunk = resp.read(_CHUNK)
                        if not chunk:
                            break
                        out.write(chunk)
                        downloaded += len(chunk)
                        if progress is not None and total > 0:
                            progress(min(downloaded / total, 0.99), label)
            return
        except DownloadCancelled:
            raise  # a cancel is never retried — surface it immediately
        except Exception as exc:  # noqa: BLE001 - retry transient network errors
            last_error = exc
            time.sleep(min(2**attempt, 8))
    raise ReleaseAssetError(f"Download failed after {retries} attempts: {last_error}")


def fetch_component(
    component: str,
    target_dir: Path,
    *,
    progress: ProgressCallback | None = None,
    should_cancel: Callable[[], bool] | None = None,
    label: str = "Downloading...",
) -> Path:
    """Download, verify (SHA-256), and unpack ``component`` into ``target_dir``.

    Atomic: everything happens in a temp dir; the verified files are copied into
    ``target_dir`` only after the checksum passes, so a partial/failed download
    never leaves a half-installed engine. Returns ``target_dir``. Raises
    :class:`ReleaseAssetError` (Safe Mode, unknown/unpinned component, network,
    checksum mismatch, or a malformed archive), or :class:`DownloadCancelled` when
    ``should_cancel`` becomes true, so the caller can degrade cleanly.
    """
    if os.environ.get("QUILL_SAFE_MODE") == "1":
        raise ReleaseAssetError("Downloading components is disabled in Safe Mode.")
    asset = ASSETS.get(component)
    if asset is None:
        raise ReleaseAssetError(f"Unknown component: {component!r}")
    if not is_pinned(asset):
        raise ReleaseAssetError(
            f"Refusing to fetch an unpinned/placeholder asset for {component!r}."
        )

    target = Path(target_dir)
    tmp = Path(tempfile.mkdtemp(prefix="quill-asset-"))
    try:
        archive = tmp / asset.filename
        if progress is not None:
            progress(0.0, label)
        _download_resumable(asset.url, archive, progress, should_cancel=should_cancel, label=label)

        actual = _sha256_file(archive)
        if actual.lower() != asset.sha256.lower():
            raise ReleaseAssetError(
                f"Checksum mismatch for {asset.filename} "
                f"(expected {asset.sha256[:12]}..., got {actual[:12]}...)."
            )

        if progress is not None:
            progress(0.99, "Installing...")
        extract = tmp / "extract"
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(extract)

        source_dir = extract
        if asset.expect_member:
            hits = list(extract.rglob(asset.expect_member))
            if not hits:
                raise ReleaseAssetError(f"{asset.filename} did not contain {asset.expect_member}.")
            source_dir = hits[0].parent

        target.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_dir, target, dirs_exist_ok=True)
        if progress is not None:
            progress(1.0, "Done.")
        return target
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def fetch_file(
    component: str,
    dest_dir: Path,
    *,
    progress: ProgressCallback | None = None,
    should_cancel: Callable[[], bool] | None = None,
    label: str = "Downloading...",
) -> Path:
    """Download + SHA-256 verify a single-file ``component`` **without** unpacking.

    For assets installed by another tool rather than extracted — a Python wheel
    handed to ``pip install --no-index``, say. Returns the verified file's path
    inside ``dest_dir``. Same pinning, Safe-Mode, checksum, atomic-temp, and
    resumable-download guarantees as :func:`fetch_component`.
    """
    if os.environ.get("QUILL_SAFE_MODE") == "1":
        raise ReleaseAssetError("Downloading components is disabled in Safe Mode.")
    asset = ASSETS.get(component)
    if asset is None:
        raise ReleaseAssetError(f"Unknown component: {component!r}")
    if not is_pinned(asset):
        raise ReleaseAssetError(
            f"Refusing to fetch an unpinned/placeholder asset for {component!r}."
        )

    dest = Path(dest_dir)
    tmp = Path(tempfile.mkdtemp(prefix="quill-asset-"))
    try:
        archive = tmp / asset.filename
        if progress is not None:
            progress(0.0, label)
        _download_resumable(asset.url, archive, progress, should_cancel=should_cancel, label=label)

        actual = _sha256_file(archive)
        if actual.lower() != asset.sha256.lower():
            raise ReleaseAssetError(
                f"Checksum mismatch for {asset.filename} "
                f"(expected {asset.sha256[:12]}..., got {actual[:12]}...)."
            )

        dest.mkdir(parents=True, exist_ok=True)
        final = dest / asset.filename
        shutil.copy2(archive, final)
        if progress is not None:
            progress(1.0, "Done.")
        return final
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
