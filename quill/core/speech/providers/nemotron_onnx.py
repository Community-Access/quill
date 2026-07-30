"""Nemotron ONNX speech-to-text provider (NVIDIA Nemotron Speech Streaming EN).

An optional, offline, English dictation engine built on **sherpa-onnx** — the
same runtime VS Code uses for its on-device Nemotron dictation. The underlying
model is NVIDIA's 600M Cache-Aware FastConformer-RNNT streaming transducer,
consumed here as a prebuilt int8 ONNX bundle (encoder / decoder / joiner /
tokens). It runs **torch-free on the CPU** (onnxruntime under sherpa-onnx), so it
fits QUILL's offline, no-GPU-required posture and never pulls in PyTorch/CUDA.

Design rules mirror the other optional engines (see ``vosk.py``):

- Lazy: ``sherpa_onnx`` is imported only inside methods; ``is_available`` only
  *locates* the module (``find_spec``) so an uninstalled engine never affects
  startup or the engine chooser.
- Safe: the model download runs only on an explicit user action, is blocked in
  Safe Mode, and is fetched SHA-256-verified from QUILL's own assets-v1 release
  via :mod:`quill.core.speech.model_mirrors` (no third-party host, no unpinned
  artifact). English models only; ``requires_network`` is False.
- Honest: failures raise :class:`SpeechError` with clear, speakable messages;
  until the mirror asset is hosted+pinned the model reports as unavailable
  rather than trying to fetch an unverifiable file.

The provider surfaces the batch ``transcribe_file`` contract only. Nemotron is a
streaming model, but QUILL's dictation flow already captures to a WAV and
transcribes the whole file; true partial/streaming transcripts would require
extending the provider Protocol and the dictation state machine and are out of
scope here.

The pure helpers :func:`resolve_model_files` and :func:`result_from_text` are
unit-tested directly (no onnxruntime needed).
"""

from __future__ import annotations

import os
import shutil
import wave
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quill.core.speech import catalog, model_mirrors, models
from quill.core.speech.provider import (
    InstalledSpeechModel,
    ProgressCallback,
    ProviderInstallStatus,
    SizeEstimate,
    SpeechError,
    SpeechModelInfo,
    TranscriptionRequest,
    TranscriptionResult,
    TranscriptionSegment,
)

PROVIDER_ID = "nemotron"

# sherpa-onnx wants 16 kHz mono 16-bit PCM, same as Vosk/whisper.cpp.
_TARGET_SAMPLE_RATE = 16000
# Feature dim for the FastConformer front-end (80-dim log-mel).
_FEATURE_DIM = 80
# Seconds of trailing silence fed after the audio so the streaming decoder
# flushes its final tokens (cache-aware models emit on a lookahead).
_TAIL_PADDING_SECONDS = 0.5


# --------------------------------------------------------------------------- #
# Pure helpers (unit-tested directly)
# --------------------------------------------------------------------------- #


def _pick(files: list[Path], stem: str) -> Path | None:
    """Choose the model file whose name starts with *stem*, preferring int8.

    A sherpa-onnx Nemotron package ships e.g. ``encoder.onnx`` plus an
    ``encoder.int8.onnx`` quantized twin; we prefer the smaller int8 graph.
    """
    candidates = [f for f in files if f.name.startswith(stem) and f.suffix == ".onnx"]
    if not candidates:
        return None
    int8 = [f for f in candidates if "int8" in f.name]
    return sorted(int8 or candidates, key=lambda f: f.name)[0]


def resolve_model_files(model_dir: Path) -> dict[str, Path] | None:
    """Locate the encoder/decoder/joiner/tokens a sherpa-onnx transducer needs.

    A Nemotron package extracts either directly into *model_dir* or into a single
    nested folder; accept either. Returns a dict with keys ``encoder``,
    ``decoder``, ``joiner``, ``tokens`` when all are present, else ``None`` (so
    an incomplete/partial install reads as "not installed" rather than crashing).
    """
    if not model_dir.is_dir():
        return None
    roots = [model_dir, *(p for p in sorted(model_dir.iterdir()) if p.is_dir())]
    for root in roots:
        try:
            entries = list(root.iterdir())
        except OSError:
            continue
        onnx = [f for f in entries if f.is_file()]
        encoder = _pick(onnx, "encoder")
        decoder = _pick(onnx, "decoder")
        joiner = _pick(onnx, "joiner")
        tokens = next((f for f in entries if f.name == "tokens.txt"), None)
        if encoder and decoder and joiner and tokens:
            return {"encoder": encoder, "decoder": decoder, "joiner": joiner, "tokens": tokens}
    return None


def result_from_text(
    text: str, duration_seconds: float | None
) -> tuple[str, tuple[TranscriptionSegment, ...]]:
    """Map a sherpa-onnx transcript string to full text + a single segment.

    sherpa-onnx greedy decoding yields one transcript for the file; we surface it
    as one segment spanning the audio (Nemotron here does not attribute speakers,
    so ``speaker`` is empty). Empty text yields no segments.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return "", ()
    end = float(duration_seconds) if duration_seconds and duration_seconds > 0 else 0.0
    return cleaned, (TranscriptionSegment(0.0, end, cleaned),)


def _model_dir(model_id: str) -> Path:
    return models.models_root() / PROVIDER_ID / model_id


# --------------------------------------------------------------------------- #
# Provider
# --------------------------------------------------------------------------- #


class NemotronOnnxProvider:
    """Optional offline English provider on sherpa-onnx (NVIDIA Nemotron). CPU-only."""

    id = PROVIDER_ID
    display_name = "Nemotron (offline, English, NVIDIA)"
    description = (
        "Local, private English transcription using NVIDIA's Nemotron streaming "
        "model via sherpa-onnx. CPU-only, no GPU or torch. No audio leaves your "
        "computer."
    )
    requires_network = False

    def __init__(self) -> None:
        self._recognizer: Any = None
        self._loaded_model_id: str | None = None

    # -- availability ----------------------------------------------------- #

    def is_available(self) -> bool:
        import importlib.util

        try:
            return importlib.util.find_spec("sherpa_onnx") is not None
        except Exception:  # noqa: BLE001 - any probing failure means unavailable
            return False

    def get_install_status(self) -> ProviderInstallStatus:
        if not self.is_available():
            return ProviderInstallStatus(
                installed=False,
                detail="sherpa-onnx is not installed. Install QUILL's optional 'nemotron' engine.",
            )
        return ProviderInstallStatus(installed=True, detail="CPU")

    # -- models ----------------------------------------------------------- #

    def list_supported_models(self) -> list[SpeechModelInfo]:
        return list(catalog.NEMOTRON_MODELS)

    def list_installed_models(self) -> list[InstalledSpeechModel]:
        return [m for m in models.load_installed_models() if m.provider_id == PROVIDER_ID]

    def estimate_model_size(self, model_id: str) -> SizeEstimate:
        info = catalog.nemotron_model_by_id(model_id)
        size = info.approximate_size_mb if info else 0
        return SizeEstimate(download_mb=size, on_disk_mb=size)

    def download_model(
        self, model_id: str, progress: ProgressCallback | None = None
    ) -> InstalledSpeechModel:
        if os.environ.get("QUILL_SAFE_MODE") == "1":
            raise SpeechError("Downloading speech models is disabled in Safe Mode.")
        info = catalog.nemotron_model_by_id(model_id)
        if info is None:
            raise SpeechError(f"No download is available for the '{model_id}' model.")
        # GATE-9 / network-egress: the ONLY outbound call is the SHA-verified
        # assets-v1 mirror fetch (reviewed via release_assets). A model with no
        # pinned mirror yet (placeholder SHA) is not fetchable, so we fail clean
        # rather than reach an unverifiable third-party host.
        asset = model_mirrors.mirror_for(PROVIDER_ID, model_id)
        if asset is None:
            raise SpeechError(
                "The Nemotron model is not yet available for download in this build. "
                "Please check for a QUILL update."
            )
        target = _model_dir(model_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            model_mirrors.fetch_mirror_archive(
                asset, target, progress=progress, label=f"Downloading {info.display_name}..."
            )
        except Exception as exc:  # noqa: BLE001 - clean up partial state, speakable message
            shutil.rmtree(target, ignore_errors=True)
            raise SpeechError(f"The model download failed: {exc}") from exc
        if resolve_model_files(target) is None:
            shutil.rmtree(target, ignore_errors=True)
            raise SpeechError("The downloaded model was incomplete. Please try again.")
        installed = InstalledSpeechModel(
            id=model_id,
            display_name=info.display_name,
            path=target,
            size_mb=info.approximate_size_mb,
            provider_id=PROVIDER_ID,
            sha256=asset.sha256,
            installed_at=datetime.now(UTC).replace(microsecond=0).isoformat(),
        )
        models.record_installed_model(installed)
        return installed

    def remove_model(self, model_id: str) -> None:
        target = _model_dir(model_id)
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
        models.remove_installed_model(model_id, PROVIDER_ID)

    # -- transcription ---------------------------------------------------- #

    def _ensure_recognizer(self, model_id: str) -> Any:
        if self._recognizer is not None and self._loaded_model_id == model_id:
            return self._recognizer
        files = resolve_model_files(_model_dir(model_id))
        if files is None:
            raise SpeechError(
                f"The '{model_id}' Nemotron model is not installed. "
                "Download it from Manage Speech Models first."
            )
        try:
            import sherpa_onnx  # type: ignore[import-not-found,import-untyped]

            threads = max(1, min(4, (os.cpu_count() or 2) - 1))
            self._recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
                tokens=str(files["tokens"]),
                encoder=str(files["encoder"]),
                decoder=str(files["decoder"]),
                joiner=str(files["joiner"]),
                num_threads=threads,
                sample_rate=_TARGET_SAMPLE_RATE,
                feature_dim=_FEATURE_DIM,
                decoding_method="greedy_search",
                provider="cpu",
            )
        except Exception as exc:  # noqa: BLE001 - surface a clean, speakable message
            raise SpeechError(f"Could not load the Nemotron model: {exc}") from exc
        self._loaded_model_id = model_id
        return self._recognizer

    def _prepare_audio(
        self, source: Path, tmp_dir: Path, progress: ProgressCallback | None
    ) -> Path:
        """Return a 16 kHz mono WAV path (transcoded via ffmpeg when needed)."""
        from quill.core.speech import ffmpeg as ffmpeg_tools

        if ffmpeg_tools.ffmpeg_available():
            try:
                return ffmpeg_tools.transcode_to_wav(source, out_dir=tmp_dir, progress=progress)
            except ffmpeg_tools.TranscodeError as exc:
                raise SpeechError(f"Could not prepare the audio for transcription: {exc}") from exc
        if source.suffix.lower() != ".wav":
            raise SpeechError(
                f"This audio format ({source.suffix or 'unknown'}) needs ffmpeg to convert "
                f"it first. {ffmpeg_tools.INSTALL_HINT} Or provide a 16 kHz mono WAV file."
            )
        return source

    def transcribe_file(
        self, request: TranscriptionRequest, progress: ProgressCallback | None = None
    ) -> TranscriptionResult:
        if not request.source_path.is_file():
            raise SpeechError(f"The audio file was not found: {request.source_path}")
        warnings: list[str] = []
        if request.diarize:
            warnings.append("Nemotron does not label speakers; speaker turns were skipped.")
        if request.language and request.language.lower() not in ("en", "english"):
            warnings.append("This Nemotron model is English; the language request was ignored.")
        recognizer = self._ensure_recognizer(request.model_id)
        if progress is not None:
            progress(0.1, "Transcribing...")
        import tempfile

        with tempfile.TemporaryDirectory(prefix="quill-nemotron-") as tmp:
            audio = self._prepare_audio(request.source_path, Path(tmp), progress)
            text, duration = _recognize(recognizer, audio, progress)
        full_text, segments = result_from_text(text, duration)
        if progress is not None:
            progress(1.0, "Done.")
        return TranscriptionResult(
            full_text=full_text,
            segments=segments,
            provider_id=PROVIDER_ID,
            model_id=request.model_id,
            language="en",
            duration_seconds=duration,
            warnings=tuple(warnings),
        )

    def cancel(self) -> None:
        return None

    def unload(self) -> None:
        self._recognizer = None
        self._loaded_model_id = None


def _read_wav_samples(audio: Path) -> tuple[Any, float]:
    """Read a 16 kHz mono 16-bit WAV into a float32 [-1, 1] numpy array + duration."""
    import numpy as np  # type: ignore[import]

    try:
        wf = wave.open(str(audio), "rb")
    except Exception as exc:  # noqa: BLE001
        raise SpeechError(f"Could not read the prepared audio: {exc}") from exc
    with wf:
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2:
            raise SpeechError("Nemotron needs 16 kHz mono 16-bit WAV audio.")
        sample_rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
    samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    duration = (len(samples) / sample_rate) if sample_rate else 0.0
    return samples, duration


def _recognize(
    recognizer: Any, audio: Path, progress: ProgressCallback | None
) -> tuple[str, float]:
    """Feed a whole WAV through the streaming recognizer and return (text, duration)."""
    import numpy as np  # type: ignore[import]

    samples, duration = _read_wav_samples(audio)
    stream = recognizer.create_stream()
    stream.accept_waveform(_TARGET_SAMPLE_RATE, samples)
    # Flush the decoder with trailing silence so the final tokens are emitted.
    tail = np.zeros(int(_TAIL_PADDING_SECONDS * _TARGET_SAMPLE_RATE), dtype=np.float32)
    stream.accept_waveform(_TARGET_SAMPLE_RATE, tail)
    stream.input_finished()
    while recognizer.is_ready(stream):
        recognizer.decode_stream(stream)
        if progress is not None:
            progress(0.6, "Transcribing...")
    result = recognizer.get_result(stream)
    text = result.text if hasattr(result, "text") else str(result)
    return text, duration
