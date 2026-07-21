"""Optional assets-v1 mirrors for the public speech models (HF-removal prep).

whisper.cpp GGML files and Faster Whisper CT2 repos are fetched from Hugging
Face today (the only two ``huggingface_hub`` library call sites in QUILL). To
drop that dependency for the *public* models -- the gated ``pyannote`` diarization
model deliberately stays on Hugging Face -- each model can be re-hosted on QUILL's
own ``assets-v1`` release and pinned by SHA-256 here.

This module is the ONE place that mirror manifest lives. The providers ask
:func:`mirror_for` before touching Hugging Face: a validly-pinned mirror is
fetched (SHA-verified) through the shared download core and, if that fails, the
provider still falls back to Hugging Face. So the cut-over is a **data change**,
not a code change, and it is safe to roll out one model at a time.

Activation (per model, no code change):
  1. Upload the file/archive to the ``assets-v1`` release.
     - whisper.cpp: the single ``ggml-<id>.bin`` (byte-identical to the HF file;
       its SHA-256 is already the one pinned in ``catalog.py``).
     - Faster Whisper: a zip of the CT2 model directory.
  2. Add a :class:`MirrorAsset` entry to ``_MIRRORS`` below (filename + sha256,
     plus ``archive_member`` for a zip so a malformed archive is caught).
An entry with a blank/placeholder SHA is ignored, so half-finished rollouts are
safe. Once every whisper.cpp + Faster Whisper model is mirrored, demote
``huggingface_hub`` from a base dependency to the ``fasterwhisper``/diarization
extra (see ``pyproject.toml`` and ``tests/unit/test_packaging_dependencies.py``).
"""

from __future__ import annotations

import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

# (fraction 0.0-1.0, human message) -- same shape as the speech ProgressCallback.
from quill.core.speech.provider import ProgressCallback

_ASSETS_V1_BASE = "https://github.com/Community-Access/quill/releases/download/assets-v1/"
_DOWNLOAD_TIMEOUT_S = 1800.0


@dataclass(frozen=True, slots=True)
class MirrorAsset:
    """One public speech model re-hosted on the ``assets-v1`` release."""

    filename: str  # the asset's name on the assets-v1 release
    sha256: str  # 64-hex digest of that exact asset
    archive_member: str = ""  # for a zip mirror, a file the unpacked tree must contain


# key -> MirrorAsset. Keys are ``f"{provider_id}:{model_id}"`` --
# e.g. ``"whispercpp:small"``, ``"fasterwhisper:small"``.
#
# Fill in an entry only once its file is live on the assets-v1 release; a
# placeholder/blank SHA is ignored, so a provider keeps using Hugging Face for
# any model not yet mirrored. The whisper.cpp SHAs are byte-identical to the
# catalog.py pins (the mirror is a re-publish of the same GGML file).
#
# large-v3 (~3.1 GB) exceeds GitHub's 2 GiB/file release-asset limit and is NOT
# mirrored; it falls back to Hugging Face / the manual-obtain path.
_MIRRORS: dict[str, MirrorAsset] = {
    "whispercpp:tiny": MirrorAsset(
        "ggml-tiny.bin", "be07e048e1e599ad46341c8d2a135645097a538221678b7acdd1b1919c6e1b21"
    ),
    "whispercpp:base": MirrorAsset(
        "ggml-base.bin", "60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe"
    ),
    "whispercpp:small": MirrorAsset(
        "ggml-small.bin", "1be3a9b2063867b937e64e2ec7483364a79917e157fa98c5d94b5c1fffea987b"
    ),
    "whispercpp:small.en-tdrz": MirrorAsset(
        "ggml-small.en-tdrz.bin",
        "ceac3ec06d1d98ef71aec665283564631055fd6129b79d8e1be4f9cc33cc54b4",
    ),
    "whispercpp:medium": MirrorAsset(
        "ggml-medium.bin", "6c14d5adee5f86394037b4e4e8b59f1673b6cee10e3cf0b11bbdbee79c156208"
    ),
    # Faster Whisper CT2 repos, re-published as a zip of the model directory
    # (model.bin + config/tokenizer/vocabulary). archive_member catches a
    # malformed archive. large-v3 (~3 GB fp16) exceeds the 2 GiB limit -> manual.
    "fasterwhisper:tiny": MirrorAsset(
        "faster-whisper-tiny.zip",
        "282000cdb6f6dca5118b76de274f1dc2a2953f256b0d8becc613cdf943624caa",
        archive_member="model.bin",
    ),
    "fasterwhisper:base": MirrorAsset(
        "faster-whisper-base.zip",
        "e424c5666c734f22b485edd87aad4d2cc630ba0d5d55d27598c786ddc7396fdb",
        archive_member="model.bin",
    ),
    "fasterwhisper:small": MirrorAsset(
        "faster-whisper-small.zip",
        "b5c5ecf5d8e8e92a6ff6cbe9d1ee3d75f95c6b9dc062a26c4ebe5bc2b9380e91",
        archive_member="model.bin",
    ),
    "fasterwhisper:medium": MirrorAsset(
        "faster-whisper-medium.zip",
        "309249ec507d5287b103ff629148dc57f6c18841835913b17c8dfb49fad5c5a4",
        archive_member="model.bin",
    ),
    "fasterwhisper:distil-large-v3": MirrorAsset(
        "faster-whisper-distil-large-v3.zip",
        "a3b581e2c385bcebd11f27ae388e52d72e6a48a4a27fc5b22132149581c28436",
        archive_member="model.bin",
    ),
}


def _is_real_sha256(value: str) -> bool:
    """True for a genuine 64-hex SHA-256, not a blank/placeholder."""
    digest = value.strip().lower()
    return len(digest) == 64 and all(c in "0123456789abcdef" for c in digest)


def mirror_key(provider_id: str, model_id: str) -> str:
    """The manifest key for a model under a provider."""
    return f"{provider_id}:{model_id}"


def mirror_for(provider_id: str, model_id: str) -> MirrorAsset | None:
    """The configured, validly-pinned mirror for a model, or None (use HF)."""
    asset = _MIRRORS.get(mirror_key(provider_id, model_id))
    if asset is None or not asset.filename or not _is_real_sha256(asset.sha256):
        return None
    return asset


def mirror_url(asset: MirrorAsset) -> str:
    """The full assets-v1 HTTPS URL for a mirror asset."""
    return _ASSETS_V1_BASE + asset.filename


def fetch_mirror_file(
    asset: MirrorAsset,
    dest: Path,
    *,
    progress: ProgressCallback | None = None,
    timeout: float = _DOWNLOAD_TIMEOUT_S,
    label: str = "Downloading model...",
) -> Path:
    """Download + SHA-verify a single-file mirror (e.g. a GGML .bin) to *dest*.

    Raises :class:`quill.core.release_assets.ReleaseAssetError` on any failure so
    the caller can fall back to Hugging Face.
    """
    from quill.core.release_assets import download_verified

    return download_verified(
        mirror_url(asset),
        dest,
        sha256=asset.sha256,
        progress=progress,
        timeout=timeout,
        label=label,
    )


def fetch_mirror_archive(
    asset: MirrorAsset,
    target_dir: Path,
    *,
    progress: ProgressCallback | None = None,
    timeout: float = _DOWNLOAD_TIMEOUT_S,
    label: str = "Downloading model...",
) -> Path:
    """Download + SHA-verify a zip mirror and unpack it into *target_dir*.

    Atomic: staged in a temp dir and only copied into ``target_dir`` after the
    checksum passes. Raises :class:`quill.core.release_assets.ReleaseAssetError`
    on a failed download, checksum, or a zip missing ``archive_member``.
    """
    from quill.core.release_assets import ReleaseAssetError, download_verified

    target = Path(target_dir)
    tmp = Path(tempfile.mkdtemp(prefix="quill-mirror-"))
    try:
        archive = tmp / asset.filename
        download_verified(
            mirror_url(asset),
            archive,
            sha256=asset.sha256,
            progress=progress,
            timeout=timeout,
            label=label,
        )
        extract = tmp / "extract"
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(extract)
        source = extract
        if asset.archive_member:
            hits = list(extract.rglob(asset.archive_member))
            if not hits:
                raise ReleaseAssetError(
                    f"{asset.filename} did not contain {asset.archive_member}."
                )
            source = hits[0].parent
        target.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target, dirs_exist_ok=True)
        return target
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
