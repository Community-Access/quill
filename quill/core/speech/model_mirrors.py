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
    # Piper voices (rhasspy/piper-voices), re-published per-voice as a zip of
    # the .onnx + .onnx.json. Every catalog voice is mirrored -> no Hugging Face.
    # Only the nine voices QUILL may redistribute (see voice_catalog.PIPER_VOICES).
    "piper:en_GB-cori-high": MirrorAsset(
        "piper-voice-en_GB-cori-high.zip",
        "82df6845776fc8493097ff4b36fb02801c7bd57bacb44a67285a68e959cdec1b",
        archive_member="en_GB-cori-high.onnx",
    ),
    "piper:en_GB-cori-medium": MirrorAsset(
        "piper-voice-en_GB-cori-medium.zip",
        "e804e7720914817496a5e9bdd6f43b4ef65694cc1ff498e19f55d459ed07a506",
        archive_member="en_GB-cori-medium.onnx",
    ),
    "piper:en_US-bryce-medium": MirrorAsset(
        "piper-voice-en_US-bryce-medium.zip",
        "3a4cd2e48b2eebc87c51d85ba520f3de3d27670c7dbfb8264c6063ba110dfd12",
        archive_member="en_US-bryce-medium.onnx",
    ),
    "piper:en_US-john-medium": MirrorAsset(
        "piper-voice-en_US-john-medium.zip",
        "24c436dfe927910627dd2b99163c4b3fa76fae2cc21445c206c7633ce1e8188c",
        archive_member="en_US-john-medium.onnx",
    ),
    "piper:en_US-kristin-medium": MirrorAsset(
        "piper-voice-en_US-kristin-medium.zip",
        "f4cd308996326f9a844fd31d5df475d0145c43781ec9b2252eb24338af150742",
        archive_member="en_US-kristin-medium.onnx",
    ),
    "piper:en_US-libritts-high": MirrorAsset(
        "piper-voice-en_US-libritts-high.zip",
        "400572c6cfa0631e6d0e4631b0b8241e4e714b6271b8069d99b006b87b5315df",
        archive_member="en_US-libritts-high.onnx",
    ),
    "piper:en_US-ljspeech-high": MirrorAsset(
        "piper-voice-en_US-ljspeech-high.zip",
        "d76c4635d175b92b8cdcad8ed4e6bb7731ecfd7e778523e340147ce6bb031b00",
        archive_member="en_US-ljspeech-high.onnx",
    ),
    "piper:en_US-ljspeech-medium": MirrorAsset(
        "piper-voice-en_US-ljspeech-medium.zip",
        "53bcaeaf124725a8e166c6cd9111e75836a0845b7e170e0d80f7a27e54319953",
        archive_member="en_US-ljspeech-medium.onnx",
    ),
    "piper:en_US-norman-medium": MirrorAsset(
        "piper-voice-en_US-norman-medium.zip",
        "3d44a5fbb2b12d92816113e8cfbf4e558adeb21456af6bec121f6c37bb49c1f4",
        archive_member="en_US-norman-medium.onnx",
    ),
    # Nemotron ONNX (NVIDIA Nemotron Speech Streaming EN, int8) for the
    # sherpa-onnx dictation engine: encoder/decoder/joiner .int8.onnx + tokens.txt
    # packaged as one zip (test_wavs removed; a NOTICE.txt records provenance and
    # the NVIDIA Open Model License). Source: the k2-fsa/sherpa-onnx "asr-models"
    # release; repackaged and re-hosted on QUILL's assets-v1 release. Verified
    # end-to-end (the provider transcribes the model's own test clips correctly).
    "nemotron:nemotron-streaming-en-0.6b": MirrorAsset(
        "sherpa-onnx-nemotron-speech-streaming-en-0.6b-int8.zip",
        "1fd10e7d6d5c8d37274eec4942f47447482b374043aae0f72a2eb363030c1132",
        archive_member="tokens.txt",
    ),
    # Parakeet 3 (NVIDIA parakeet-tdt-0.6b-v3, int8) for the sherpa-onnx
    # dictation engine: the multilingual offline transducer dictation prefers
    # once installed. Same packaging discipline as Nemotron above (test_wavs
    # removed; NOTICE.txt records provenance and the CC-BY-4.0 license).
    # Source: the k2-fsa/sherpa-onnx "asr-models" release
    # (sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8.tar.bz2, upstream sha256
    # 5793d0fd397c5778d2cf2126994d58e9d56b1be7c04d13c7a15bb1b4eafb16bf);
    # repackaged and re-hosted on QUILL's assets-v1 release 2026-08-17.
    # The bundle also carries silero_vad.onnx (~0.6 MB, sherpa-onnx's export),
    # so installing Parakeet upgrades the dictation VAD pre-pass from the RMS
    # tier to Silero for free (speech_vad.py resolves it from the model dir).
    "parakeet:parakeet-tdt-0.6b-v3": MirrorAsset(
        "sherpa-onnx-parakeet-tdt-0.6b-v3-int8.zip",
        "7f2419d522a797c26d0da32daaee9aaedf17a6621874e1b2d1f57361fbb13d3b",
        archive_member="tokens.txt",
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
                raise ReleaseAssetError(f"{asset.filename} did not contain {asset.archive_member}.")
            source = hits[0].parent
        target.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target, dirs_exist_ok=True)
        return target
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
