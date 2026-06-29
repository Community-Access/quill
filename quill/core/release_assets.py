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

# (fraction 0.0-1.0, human message) — same shape as the speech ProgressCallback.
ProgressCallback = Callable[[float, str], None]

# Assets live on a dedicated, not-latest release tag so asset churn never touches
# the product release or the autoupdate feed (the tag does not match ``v*``).
_RELEASE_BASE = "https://github.com/Community-Access/quill/releases/download"

_CHUNK = 1024 * 1024


class ReleaseAssetError(Exception):
    """A redistributable component could not be fetched/verified/installed."""


@dataclass(frozen=True, slots=True)
class ReleaseAsset:
    """One pinned, SHA-256-verified component hosted on a QUILL release tag."""

    component: str
    tag: str
    filename: str
    sha256: str
    expect_member: str = ""  # a file the unpacked archive must contain
    license: str = ""

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
) -> None:
    """Download ``url`` to ``dest`` with retry/backoff, resuming a partial file via
    HTTP Range. HTTPS-only. Raises :class:`ReleaseAssetError` after exhausting retries.

    GATE-9: this is the module's only network egress; callers gate it on an explicit
    user action and Safe Mode.
    """
    if not url.lower().startswith("https://"):
        raise ReleaseAssetError("Refusing a non-HTTPS download URL.")
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
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
                        chunk = resp.read(_CHUNK)
                        if not chunk:
                            break
                        out.write(chunk)
                        downloaded += len(chunk)
                        if progress is not None and total > 0:
                            progress(
                                min(downloaded / total, 0.99),
                                "Downloading offline speech engine...",
                            )
            return
        except Exception as exc:  # noqa: BLE001 - retry transient network errors
            last_error = exc
            time.sleep(min(2**attempt, 8))
    raise ReleaseAssetError(f"Download failed after {retries} attempts: {last_error}")


def fetch_component(
    component: str, target_dir: Path, *, progress: ProgressCallback | None = None
) -> Path:
    """Download, verify (SHA-256), and unpack ``component`` into ``target_dir``.

    Atomic: everything happens in a temp dir; the verified files are copied into
    ``target_dir`` only after the checksum passes, so a partial/failed download
    never leaves a half-installed engine. Returns ``target_dir``. Raises
    :class:`ReleaseAssetError` (Safe Mode, unknown/unpinned component, network,
    checksum mismatch, or a malformed archive) so the caller can degrade cleanly.
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
            progress(0.0, "Downloading offline speech engine...")
        _download_resumable(asset.url, archive, progress)

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
