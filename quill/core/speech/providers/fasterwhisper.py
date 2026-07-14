"""Faster Whisper speech-to-text provider (#617 S4).

An optional, higher-throughput offline engine. Unlike the bundled whisper.cpp
provider (a CLI over GGML files), Faster Whisper is a Python library built on
CTranslate2 that loads a CTranslate2 *model directory* and runs in-process,
using the GPU automatically when one is available (and a fast int8 CPU path
otherwise). Models are CTranslate2 repositories on the Hugging Face Hub, fetched
with ``huggingface_hub.snapshot_download``.

Design rules mirror the whisper.cpp provider (#617 section 8.2 / 17):

- Lazy: ``faster_whisper`` / ``ctranslate2`` / ``huggingface_hub`` are imported
  only inside methods, so an uninstalled engine never affects QUILL startup or
  the bundled provider.
- Safe: downloads run only on an explicit user action, are blocked in Safe Mode,
  and are tracked by the network-egress audit.
- Honest: failures raise :class:`SpeechError` with clear, speakable messages.

The pure helpers (:func:`pick_device_and_compute`,
:func:`segments_from_faster_whisper`) are unit-tested directly; the model load
and download paths are thin wrappers over them.
"""

from __future__ import annotations

import io
import os
import shutil
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quill.core.speech import catalog, models
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

PROVIDER_ID = "fasterwhisper"

_TRANSCRIBE_TIMEOUT_S = 1800.0  # parity with whisper.cpp; informational here


# --------------------------------------------------------------------------- #
# Pure helpers (unit-tested directly)
# --------------------------------------------------------------------------- #


def pick_device_and_compute() -> tuple[str, str]:
    """Return ``(device, compute_type)`` for Faster Whisper.

    Uses CUDA with float16 when a GPU is visible to CTranslate2, otherwise a
    fast int8 CPU path. Any probing failure falls back to CPU/int8 so the engine
    still runs.
    """
    try:
        import ctranslate2

        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda", "float16"
    except Exception:  # noqa: BLE001 - never let device probing break transcription
        pass
    return "cpu", "int8"


def segments_from_faster_whisper(
    raw_segments: Iterable[Any],
) -> tuple[TranscriptionSegment, ...]:
    """Map Faster Whisper segment objects to QUILL :class:`TranscriptionSegment`.

    Accepts anything exposing ``start``, ``end``, and ``text`` (the library's
    ``Segment`` namedtuple, or a test stand-in). Empty-text segments are dropped.
    Faster Whisper does not attribute speakers, so ``speaker`` is always empty.
    """
    out: list[TranscriptionSegment] = []
    for seg in raw_segments:
        text = str(getattr(seg, "text", "")).strip()
        if not text:
            continue
        try:
            start = float(getattr(seg, "start", 0.0))
            end = float(getattr(seg, "end", 0.0))
        except (TypeError, ValueError):
            continue
        out.append(TranscriptionSegment(start, end, text))
    return tuple(out)


def _model_dir(model_id: str) -> Path:
    return models.models_root() / PROVIDER_ID / model_id


# --------------------------------------------------------------------------- #
# Provider
# --------------------------------------------------------------------------- #


class FasterWhisperProvider:
    """Optional offline provider built on Faster Whisper (CTranslate2)."""

    id = PROVIDER_ID
    display_name = "Faster Whisper (offline)"
    description = (
        "Local, private transcription using Faster Whisper. Uses your GPU when "
        "available for higher speed. No audio leaves your computer."
    )

    def __init__(self) -> None:
        self._model: Any = None
        self._loaded_model_id: str | None = None

    # -- availability ----------------------------------------------------- #

    def is_available(self) -> bool:
        # Probe by locating the module, NOT by importing it: ``import
        # faster_whisper`` pulls in CTranslate2 and can take tens of seconds on
        # first load. is_available() runs on the UI thread (registry build,
        # engine chooser, model manager), so a real import here freezes the
        # whole app. The heavy import stays in ``_ensure_model`` (transcription),
        # which runs on a background task. A broken install surfaces there as a
        # clean, speakable SpeechError instead of a UI hang.
        import importlib.util

        try:
            return importlib.util.find_spec("faster_whisper") is not None
        except Exception:  # noqa: BLE001 - any probing failure means unavailable
            return False

    def get_install_status(self) -> ProviderInstallStatus:
        if not self.is_available():
            return ProviderInstallStatus(
                installed=False,
                detail=(
                    "Faster Whisper is not installed. Install QUILL's optional "
                    "'fasterwhisper' dependency to use this engine."
                ),
            )
        device, compute = pick_device_and_compute()
        return ProviderInstallStatus(installed=True, detail=f"{device} ({compute})")

    # -- models ----------------------------------------------------------- #

    def list_supported_models(self) -> list[SpeechModelInfo]:
        return list(catalog.FASTER_WHISPER_MODELS)

    def list_installed_models(self) -> list[InstalledSpeechModel]:
        return [m for m in models.load_installed_models() if m.provider_id == PROVIDER_ID]

    def estimate_model_size(self, model_id: str) -> SizeEstimate:
        info = catalog.fw_model_by_id(model_id)
        size = info.approximate_size_mb if info else 0
        return SizeEstimate(download_mb=size, on_disk_mb=size)

    def download_model(
        self, model_id: str, progress: ProgressCallback | None = None
    ) -> InstalledSpeechModel:
        if os.environ.get("QUILL_SAFE_MODE") == "1":
            raise SpeechError("Downloading speech models is disabled in Safe Mode.")
        info = catalog.fw_model_by_id(model_id)
        if info is None or not info.download_url:
            raise SpeechError(f"No download is available for the '{model_id}' model.")
        target = _model_dir(model_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        _download_repo(info.download_url, target, info, progress)
        installed = InstalledSpeechModel(
            id=model_id,
            display_name=info.display_name,
            path=target,
            size_mb=info.approximate_size_mb,
            provider_id=PROVIDER_ID,
            sha256=info.sha256,
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
        """Load the model into memory now so the first transcription is fast.

        Best-effort: a missing/unloadable model raises, which the caller (a
        background prewarm) swallows. No-op once the model is already loaded.
        """
        self._ensure_model(model_id)

    def _ensure_model(self, model_id: str) -> Any:
        if self._model is not None and self._loaded_model_id == model_id:
            return self._model
        from faster_whisper import WhisperModel

        model_dir = _model_dir(model_id)
        if not model_dir.is_dir():
            raise SpeechError(
                f"The '{model_id}' Faster Whisper model is not installed. "
                "Download it from Manage Speech Models first."
            )
        device, compute = pick_device_and_compute()
        try:
            self._model = WhisperModel(str(model_dir), device=device, compute_type=compute)
        except Exception as exc:  # noqa: BLE001 - surface a clean, speakable message
            raise SpeechError(f"Could not load the Faster Whisper model: {exc}") from exc
        self._loaded_model_id = model_id
        return self._model

    def transcribe_file(
        self, request: TranscriptionRequest, progress: ProgressCallback | None = None
    ) -> TranscriptionResult:
        if not request.source_path.is_file():
            raise SpeechError(f"The audio file was not found: {request.source_path}")
        model = self._ensure_model(request.model_id)
        if progress is not None:
            progress(0.05, "Transcribing...")
        warnings: list[str] = []
        if request.diarize:
            warnings.append("Faster Whisper does not label speakers; speaker turns were skipped.")
        task = "translate" if request.translate_to_english else "transcribe"
        kwargs: dict[str, Any] = {"task": task}
        if request.language:
            kwargs["language"] = request.language
        if request.initial_prompt:
            kwargs["initial_prompt"] = request.initial_prompt
        if request.temperature is not None:
            kwargs["temperature"] = request.temperature
        try:
            raw_segments, info = model.transcribe(str(request.source_path), **kwargs)
            collected: list[Any] = []
            total = float(getattr(info, "duration", 0.0) or 0.0)
            for seg in raw_segments:  # generator: this is where work happens
                collected.append(seg)
                if progress is not None and total > 0:
                    end = float(getattr(seg, "end", 0.0) or 0.0)
                    progress(min(0.05 + 0.9 * (end / total), 0.99), "Transcribing...")
        except SpeechError:
            raise
        except Exception as exc:  # noqa: BLE001 - clean message for any engine error
            raise SpeechError(f"Transcription failed: {exc}") from exc
        segments = segments_from_faster_whisper(collected)
        full_text = " ".join(seg.text for seg in segments if seg.text).strip()
        language = getattr(info, "language", None)
        duration = segments[-1].end_seconds if segments else None
        if progress is not None:
            progress(1.0, "Done.")
        return TranscriptionResult(
            full_text=full_text,
            segments=segments,
            provider_id=PROVIDER_ID,
            model_id=request.model_id,
            language=language,
            duration_seconds=duration,
            warnings=tuple(warnings),
        )

    def cancel(self) -> None:
        return None

    def unload(self) -> None:
        self._model = None
        self._loaded_model_id = None


def _download_repo(
    repo_id: str, target: Path, info: SpeechModelInfo, progress: ProgressCallback | None
) -> None:
    """Fetch a CTranslate2 model repo from the Hugging Face Hub into ``target``.

    GATE-9 / network-egress: the only outbound call here. It runs only on an
    explicit user "download model" action and is blocked in Safe Mode by the
    caller. ``huggingface_hub`` verifies TLS and file integrity.
    """
    try:
        from huggingface_hub import snapshot_download
    except Exception as exc:  # noqa: BLE001
        raise SpeechError(
            "Downloading Faster Whisper models needs the 'huggingface_hub' package."
        ) from exc
    if progress is not None:
        progress(0.02, f"Downloading {info.display_name}...")
    kwargs: dict[str, Any] = {"repo_id": repo_id, "local_dir": str(target)}
    if info.revision:
        kwargs["revision"] = info.revision  # pinned commit; huggingface_hub verifies files
    from quill.core.speech.hf_auth import load_hf_token

    token = load_hf_token()
    if token:
        kwargs["token"] = token
    if progress is not None:
        tqdm_cls = _make_progress_tqdm(info, progress)
        if tqdm_cls is not None:
            kwargs["tqdm_class"] = tqdm_cls
    try:
        snapshot_download(**kwargs)
    except Exception as exc:  # noqa: BLE001 - surface a clean message
        shutil.rmtree(target, ignore_errors=True)
        from quill.core.speech.hf_auth import RATE_LIMIT_HELP, looks_rate_limited

        if looks_rate_limited(exc):
            raise SpeechError(RATE_LIMIT_HELP) from exc
        raise SpeechError(f"The model download failed: {exc}") from exc


def _make_progress_tqdm(info: SpeechModelInfo, progress: ProgressCallback) -> type | None:
    """Build a tqdm subclass that forwards Hugging Face byte progress to ``progress``.

    huggingface_hub creates one progress bar per file; we accumulate bytes across
    them and divide by the model's approximate size to report a single moving
    percentage (0.02-0.99). If ``progress`` raises (user cancelled), the exception
    propagates out of ``snapshot_download`` and aborts the download.
    """
    try:
        from tqdm.auto import tqdm as _BaseTqdm  # type: ignore[import-untyped]
    except Exception:  # noqa: BLE001 - no tqdm means we simply skip byte progress
        return None

    total_bytes = max(1, int(info.approximate_size_mb) * 1024 * 1024)
    shared = {"done": 0}

    class _ProgressTqdm(_BaseTqdm):  # type: ignore[misc, valid-type]
        def __init__(self, *args: object, **kwargs: object) -> None:
            # QUILL's bundled quill.exe is a windowed pythonw.exe with no
            # console, so sys.stderr is None there -- tqdm's own default
            # write target for its bar rendering. We report progress
            # ourselves via progress() below and never need tqdm's own bar,
            # so give it a real sink instead of crashing on "'NoneType'
            # object has no attribute 'write'".
            kwargs.setdefault("file", io.StringIO())
            super().__init__(*args, **kwargs)  # type: ignore[no-untyped-call]

        def update(self, n: float | None = 1) -> bool | None:
            shared["done"] += int(n or 0)
            fraction = 0.02 + 0.95 * min(shared["done"] / total_bytes, 1.0)
            progress(min(fraction, 0.99), f"Downloading {info.display_name}...")
            return super().update(n)  # type: ignore[no-any-return]

    return _ProgressTqdm
