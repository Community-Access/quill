"""Parakeet speech-to-text provider (NVIDIA NeMo) — optional offline engine.

Parakeet is NVIDIA's high-accuracy **English** ASR family. Like Faster Whisper it
is an optional, GPU-oriented offline engine that runs entirely on the machine; it
is heavier (it pulls in the NeMo toolkit and PyTorch) and is therefore never
imported at startup. Models are single ``.nemo`` archives on the Hugging Face
Hub, fetched with ``huggingface_hub.snapshot_download`` and loaded in-process via
``nemo.collections.asr``.

Design rules mirror the Faster Whisper provider (#617 §8.2 / consolidation #669):

- Lazy: ``nemo`` / ``torch`` / ``huggingface_hub`` are imported only inside
  methods, so an uninstalled engine never affects QUILL startup or other engines.
  ``is_available`` only *locates* the module (``find_spec``) — importing NeMo is
  slow and must never run on the UI thread.
- Safe: downloads run only on an explicit user action, are blocked in Safe Mode,
  pin the model commit, and are tracked by the network-egress audit.
- On-device: ``requires_network`` is False; this is an offline engine the offline
  transcribe paths may use freely.
- Honest: failures raise :class:`SpeechError` with clear, speakable messages.

The pure helpers (:func:`pick_device`, :func:`result_from_parakeet`) are
unit-tested directly; the model load and transcription are thin wrappers.
"""

from __future__ import annotations

import os
import shutil
import tempfile
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

PROVIDER_ID = "parakeet"


# --------------------------------------------------------------------------- #
# Pure helpers (unit-tested directly)
# --------------------------------------------------------------------------- #


def pick_device() -> str:
    """Return ``"cuda"`` when a GPU is visible to PyTorch, else ``"cpu"``.

    Any probing failure falls back to CPU so the engine still runs (slowly).
    """
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
    except Exception:  # noqa: BLE001 - never let device probing break transcription
        pass
    return "cpu"


def _coerce_hypotheses(raw: Any) -> list[Any]:
    """Normalize NeMo ``transcribe`` return shapes to a flat list.

    Across NeMo versions ``transcribe`` returns a list of strings, a list of
    ``Hypothesis`` objects, or a ``(best, all)`` tuple. Reduce all of them to the
    list of best results.
    """
    if isinstance(raw, tuple) and len(raw) == 2 and isinstance(raw[0], list):
        raw = raw[0]
    if isinstance(raw, list):
        return raw
    return [raw]


def result_from_parakeet(item: Any) -> tuple[str, tuple[TranscriptionSegment, ...]]:
    """Map one NeMo result (string or ``Hypothesis``) to text + segments.

    Tolerant of version differences: a plain string yields no segments; a
    ``Hypothesis`` contributes its ``.text`` and, when ``timestamps=True`` was
    honored, segment-level start/end from ``.timestamp["segment"]``. Parakeet does
    not attribute speakers, so ``speaker`` is always empty.
    """
    if isinstance(item, str):
        return item.strip(), ()
    text = str(getattr(item, "text", "") or "").strip()
    timestamp = getattr(item, "timestamp", None)
    raw_segments: Iterable[Any] = ()
    if isinstance(timestamp, dict):
        raw_segments = timestamp.get("segment") or ()
    segments: list[TranscriptionSegment] = []
    for seg in raw_segments:
        if not isinstance(seg, dict):
            continue
        seg_text = str(seg.get("segment") or seg.get("text") or "").strip()
        if not seg_text:
            continue
        start_val = seg.get("start", seg.get("start_offset"))
        end_val = seg.get("end", seg.get("end_offset"))
        try:
            start = float(start_val) if start_val is not None else 0.0
            end = float(end_val) if end_val is not None else 0.0
        except (TypeError, ValueError):
            start = end = 0.0
        segments.append(TranscriptionSegment(start, end, seg_text))
    if not text and segments:
        text = " ".join(s.text for s in segments).strip()
    return text, tuple(segments)


def _model_dir(model_id: str) -> Path:
    return models.models_root() / PROVIDER_ID / model_id


def _find_nemo_file(model_dir: Path) -> Path | None:
    return next(iter(sorted(model_dir.glob("*.nemo"))), None)


# --------------------------------------------------------------------------- #
# Provider
# --------------------------------------------------------------------------- #


class ParakeetProvider:
    """Optional offline provider built on NVIDIA NeMo Parakeet (English)."""

    id = PROVIDER_ID
    display_name = "Parakeet (offline, English)"
    description = (
        "Local, private English transcription using NVIDIA Parakeet. High accuracy; "
        "a GPU is strongly recommended. No audio leaves your computer."
    )
    requires_network = False

    def __init__(self) -> None:
        self._model: Any = None
        self._loaded_model_id: str | None = None

    # -- availability ----------------------------------------------------- #

    def is_available(self) -> bool:
        # Probe by locating the module, NOT importing it: ``import nemo`` pulls in
        # PyTorch and can take tens of seconds. is_available() runs on the UI
        # thread (registry build, engine chooser), so a real import would freeze
        # the app. The heavy import stays in ``_ensure_model`` (a background task).
        import importlib.util

        try:
            return importlib.util.find_spec("nemo") is not None
        except Exception:  # noqa: BLE001 - any probing failure means unavailable
            return False

    def get_install_status(self) -> ProviderInstallStatus:
        if not self.is_available():
            return ProviderInstallStatus(
                installed=False,
                detail=(
                    "NVIDIA NeMo is not installed. Install QUILL's optional 'parakeet' "
                    "dependency to use this engine (a GPU is recommended)."
                ),
            )
        return ProviderInstallStatus(installed=True, detail=f"{pick_device()}")

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

    def _ensure_model(self, model_id: str) -> Any:
        if self._model is not None and self._loaded_model_id == model_id:
            return self._model
        model_dir = _model_dir(model_id)
        nemo_file = _find_nemo_file(model_dir)
        if nemo_file is None:
            raise SpeechError(
                f"The '{model_id}' Parakeet model is not installed. "
                "Download it from Manage Speech Models first."
            )
        try:
            from nemo.collections.asr.models import ASRModel
        except Exception as exc:  # noqa: BLE001
            raise SpeechError(
                "NVIDIA NeMo is not installed. Install QUILL's optional 'parakeet' dependency."
            ) from exc
        try:
            self._model = ASRModel.restore_from(
                restore_path=str(nemo_file), map_location=pick_device()
            )
        except Exception as exc:  # noqa: BLE001 - surface a clean, speakable message
            raise SpeechError(f"Could not load the Parakeet model: {exc}") from exc
        self._loaded_model_id = model_id
        return self._model

    def _prepare_audio(
        self, source: Path, tmp_dir: Path, progress: ProgressCallback | None
    ) -> Path:
        """Return a 16 kHz mono WAV path NeMo can read (transcoded via ffmpeg)."""
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
        if request.language and request.language.lower() not in ("en", "english"):
            warnings.append("Parakeet transcribes English only; the language request was ignored.")
        model = self._ensure_model(request.model_id)
        if progress is not None:
            progress(0.1, "Transcribing...")
        with tempfile.TemporaryDirectory(prefix="quill-parakeet-") as tmp:
            audio = self._prepare_audio(request.source_path, Path(tmp), progress)
            try:
                try:
                    raw = model.transcribe([str(audio)], timestamps=True)
                except TypeError:
                    # Older NeMo signatures do not accept ``timestamps``.
                    raw = model.transcribe([str(audio)])
            except SpeechError:
                raise
            except Exception as exc:  # noqa: BLE001 - clean message for any engine error
                raise SpeechError(f"Transcription failed: {exc}") from exc
        hypotheses = _coerce_hypotheses(raw)
        text, segments = result_from_parakeet(hypotheses[0] if hypotheses else "")
        duration = segments[-1].end_seconds if segments else None
        if progress is not None:
            progress(1.0, "Done.")
        return TranscriptionResult(
            full_text=text,
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
        self._model = None
        self._loaded_model_id = None


def _download_repo(
    repo_id: str, target: Path, info: SpeechModelInfo, progress: ProgressCallback | None
) -> None:
    """Fetch a Parakeet ``.nemo`` repo from the Hugging Face Hub into ``target``.

    GATE-9 / network-egress: the only outbound call here. It runs only on an
    explicit user "download model" action and is blocked in Safe Mode by the
    caller. ``huggingface_hub`` verifies TLS and pins the commit ``revision``.
    """
    try:
        from huggingface_hub import snapshot_download
    except Exception as exc:  # noqa: BLE001
        raise SpeechError(
            "Downloading Parakeet models needs the 'huggingface_hub' package."
        ) from exc
    if progress is not None:
        progress(0.02, f"Downloading {info.display_name}...")
    kwargs: dict[str, Any] = {
        "repo_id": repo_id,
        "local_dir": str(target),
        "allow_patterns": ["*.nemo"],
    }
    if info.revision:
        kwargs["revision"] = info.revision  # pinned commit; huggingface_hub verifies files
    from quill.core.speech.hf_auth import load_hf_token

    token = load_hf_token()
    if token:
        kwargs["token"] = token
    try:
        snapshot_download(**kwargs)
    except Exception as exc:  # noqa: BLE001 - surface a clean message
        shutil.rmtree(target, ignore_errors=True)
        from quill.core.speech.hf_auth import RATE_LIMIT_HELP, looks_rate_limited

        if looks_rate_limited(exc):
            raise SpeechError(RATE_LIMIT_HELP) from exc
        raise SpeechError(f"The model download failed: {exc}") from exc
    if progress is not None:
        progress(0.99, f"Finishing {info.display_name}...")
