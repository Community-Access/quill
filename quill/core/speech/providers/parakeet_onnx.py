"""Parakeet 3 ONNX speech-to-text provider (NVIDIA parakeet-tdt-0.6b-v3).

The multilingual sibling of :mod:`nemotron_onnx`, and the engine QUILL now
*prefers* for dictation when its model is installed (see
``service.preferred_dictation_provider_id``). The underlying model is NVIDIA's
600M Token-and-Duration Transducer, third generation: **25 European languages
with automatic language detection**, consumed as a prebuilt int8 ONNX bundle
(encoder / decoder / joiner / tokens) through **sherpa-onnx**. It runs
**torch-free on the CPU** — no GPU, no PyTorch/CUDA — so it fits QUILL's
offline posture exactly as Nemotron does.

Why prefer it over whisper.cpp for dictation (2026-08-17, studied against the
Handy project's production experience at D:\\code\\handy):

- **No silence hallucination.** Whisper decodes language-model-shaped text even
  from silence ("thank you", phantom subtitles); a transducer emits tokens only
  for audio evidence. For dictation — short utterances, frequent silence — this
  is the reliability difference a user actually hears.
- **No GPU crash class.** Handy's tracker documents whisper.cpp crashing on
  specific Windows/Linux GPU configurations. sherpa-onnx here is CPU-only by
  construction, which trades peak speed for uniform behaviour on every machine.
- **Auto language detection** across its 25 languages, where whisper.cpp needs
  the language chosen or guessed.

whisper.cpp remains the *default* engine (``service.DEFAULT_PROVIDER_ID``):
it ships with QUILL and works before any large download, whereas Parakeet is a
~640 MB opt-in model. The preference ladder only promotes Parakeet after the
user has installed it — an explicit, reversible choice, never a surprise
download. An explicitly chosen engine (``settings.speech_provider``) always
wins over the ladder.

Design rules are identical to ``nemotron_onnx.py`` (lazy import; Safe Mode
gated; SHA-256-pinned assets-v1 mirror only; honest ``SpeechError`` failures)
— the bundle layout is the same, so the file-resolution helpers are imported
from there rather than duplicated. The one behavioural difference: this is an
**offline (batch) transducer**, decoded via ``OfflineRecognizer``, which is
precisely the shape QUILL's dictation flow wants (capture a WAV, transcribe the
file). The streaming protocol in :mod:`quill.core.speech.streaming` is the
committed/tentative contract a future streaming Parakeet/Nemotron build will
adopt.
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
from quill.core.speech.providers.nemotron_onnx import resolve_model_files

PROVIDER_ID = "parakeet"

# sherpa-onnx wants 16 kHz mono 16-bit PCM, same as Nemotron/Vosk/whisper.cpp.
_TARGET_SAMPLE_RATE = 16000


def result_from_text(
    text: str, duration_seconds: float | None
) -> tuple[str, tuple[TranscriptionSegment, ...]]:
    """Map a sherpa-onnx transcript string to full text + a single segment (pure)."""
    cleaned = (text or "").strip()
    if not cleaned:
        return "", ()
    end = float(duration_seconds) if duration_seconds and duration_seconds > 0 else 0.0
    return cleaned, (TranscriptionSegment(0.0, end, cleaned),)


def _model_dir(model_id: str) -> Path:
    return models.models_root() / PROVIDER_ID / model_id


class ParakeetOnnxProvider:
    """Optional offline multilingual provider on sherpa-onnx (NVIDIA Parakeet 3)."""

    id = PROVIDER_ID
    display_name = "Parakeet 3 (offline, 25 languages, NVIDIA)"
    description = (
        "Local, private transcription in 25 languages with automatic language "
        "detection, using NVIDIA's Parakeet 3 model via sherpa-onnx. CPU-only, "
        "no GPU or torch. Unlike Whisper, it never invents text from silence. "
        "No audio leaves your computer."
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
        return list(catalog.PARAKEET_MODELS)

    def list_installed_models(self) -> list[InstalledSpeechModel]:
        return [m for m in models.load_installed_models() if m.provider_id == PROVIDER_ID]

    def estimate_model_size(self, model_id: str) -> SizeEstimate:
        info = catalog.parakeet_model_by_id(model_id)
        size = info.approximate_size_mb if info else 0
        return SizeEstimate(download_mb=size, on_disk_mb=size)

    def download_model(
        self, model_id: str, progress: ProgressCallback | None = None
    ) -> InstalledSpeechModel:
        if os.environ.get("QUILL_SAFE_MODE") == "1":
            raise SpeechError("Downloading speech models is disabled in Safe Mode.")
        info = catalog.parakeet_model_by_id(model_id)
        if info is None:
            raise SpeechError(f"No download is available for the '{model_id}' model.")
        # GATE-9 / network-egress: the ONLY outbound call is the SHA-verified
        # assets-v1 mirror fetch, exactly as for Nemotron.
        asset = model_mirrors.mirror_for(PROVIDER_ID, model_id)
        if asset is None:
            raise SpeechError(
                "The Parakeet 3 model is not yet available for download in this build. "
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

    def warm(self, model_id: str) -> None:
        """Load the model ahead of the first dictation (prewarm hook)."""
        self._ensure_recognizer(model_id)

    def _ensure_recognizer(self, model_id: str) -> Any:
        if self._recognizer is not None and self._loaded_model_id == model_id:
            return self._recognizer
        files = resolve_model_files(_model_dir(model_id))
        if files is None:
            raise SpeechError(
                f"The '{model_id}' Parakeet model is not installed. "
                "Download it from Manage Speech Models first."
            )
        try:
            import sherpa_onnx  # type: ignore[import-not-found,import-untyped]

            threads = max(1, min(4, (os.cpu_count() or 2) - 1))
            # Parakeet TDT is an *offline* NeMo transducer: whole-utterance
            # decode, unlike Nemotron's cache-aware OnlineRecognizer.
            self._recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
                tokens=str(files["tokens"]),
                encoder=str(files["encoder"]),
                decoder=str(files["decoder"]),
                joiner=str(files["joiner"]),
                num_threads=threads,
                sample_rate=_TARGET_SAMPLE_RATE,
                feature_dim=80,
                decoding_method="greedy_search",
                model_type="nemo_transducer",
                provider="cpu",
            )
        except Exception as exc:  # noqa: BLE001 - surface a clean, speakable message
            raise SpeechError(f"Could not load the Parakeet 3 model: {exc}") from exc
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
            warnings.append("Parakeet does not label speakers; speaker turns were skipped.")
        recognizer = self._ensure_recognizer(request.model_id)
        if progress is not None:
            progress(0.1, "Transcribing...")
        import tempfile

        with tempfile.TemporaryDirectory(prefix="quill-parakeet-") as tmp:
            audio = self._prepare_audio(request.source_path, Path(tmp), progress)
            text, duration, detected = _recognize(recognizer, audio, progress)
        full_text, segments = result_from_text(text, duration)
        if progress is not None:
            progress(1.0, "Done.")
        return TranscriptionResult(
            full_text=full_text,
            segments=segments,
            provider_id=PROVIDER_ID,
            model_id=request.model_id,
            # The model's own detection outranks the caller's hint — it heard
            # the audio; the hint guessed. Downstream, this is the evidence
            # the filler pass's language-gated tier runs on ("auto" = none).
            language=(detected or request.language or "auto"),
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
            raise SpeechError("Parakeet needs 16 kHz mono 16-bit WAV audio.")
        sample_rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
    samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    duration = (len(samples) / sample_rate) if sample_rate else 0.0
    return samples, duration


def _recognize(
    recognizer: Any, audio: Path, progress: ProgressCallback | None
) -> tuple[str, float, str]:
    """Decode a WAV through the offline recognizer: (text, duration, language).

    A Silero VAD pre-pass (see :mod:`quill.core.speech.speech_vad`) may already
    have trimmed leading/trailing silence; the transducer itself is silence-safe
    either way — it simply emits nothing for quiet audio.
    """
    samples, duration = _read_wav_samples(audio)
    stream = recognizer.create_stream()
    stream.accept_waveform(_TARGET_SAMPLE_RATE, samples)
    recognizer.decode_stream(stream)
    text = str(getattr(stream.result, "text", "") or "")
    # v3 detects its output language and sherpa surfaces it (as "en" or a
    # "<en>" token depending on version); normalized here, "" when absent.
    lang = str(getattr(stream.result, "lang", "") or "").strip().strip("<>").lower()
    if progress is not None:
        progress(0.9, "Finishing...")
    return text, duration, lang
