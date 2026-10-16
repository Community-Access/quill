"""The bundled Moonshine tiny model, as a speech provider for the voice features.

Voice Command, Conversation Mode and the always-listening Hey QUILL wake word
ask ``MainFrame._voice_provider`` for an engine and then speak to it through
the :class:`~quill.core.speech.provider.SpeechToTextProvider` shape: is it
available, which models are installed, transcribe this recording. This
adapter gives them the Moonshine tiny model that already ships in every copy
of QUILL for live dictation (``quill.core.windows_dictation``), so the lightest
voice engine needs no download and no second model folder.

It is a thin seam, not an engine of its own:

* **The model** is the one ``windows_dictation.engines.model_dir("moonshine")``
  finds -- the installer's ``dictation-models/moonshine-tiny-en`` folder.
* **The recogniser** is dictation's: :func:`local_recognizer.transcribe` loads
  it once per session into the same cache live dictation uses, and the same
  idle unloader gives the memory back a few minutes after the last use.
* **Nothing downloads.** :meth:`download_model` and :meth:`remove_model` refuse
  with a sentence; the model belongs to the installation.

It is deliberately **not** registered in ``service.default_registry``: it is
not a dictation or transcription engine choice (live dictation already runs
Moonshine through its own path), only the voice features' light option. It
replaced Vosk in that role on 2026-10-13: Vosk is English only, its last
release was in 2022 and its models are checked by MD5 only, where Moonshine
tiny is bundled and measured faster and more accurate (the dictation design
record, docs/design/2026-10-05-dictation-plan-and-status.md section 6).
"""

from __future__ import annotations

import importlib.util
import wave
from collections.abc import Callable
from pathlib import Path
from typing import Any

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

PROVIDER_ID = "moonshine_tiny"
MODEL_ID = "moonshine-tiny-en"
_DISPLAY_MODEL = "Moonshine tiny (English, built in)"
_RATE = 16_000
#: Live dictation cuts a phrase at 20 seconds; a longer recording is decoded
#: in pieces of the same length so Moonshine never sees more than it is used to.
_PIECE_SECONDS = 20
_APPROX_SIZE_MB = 120

Transcriber = Callable[[Any], str]
FolderFinder = Callable[[], "Path | None"]


def _bundled_folder() -> Path | None:
    from quill.core.windows_dictation.engines import model_dir

    return model_dir("moonshine")


def _sherpa_present() -> bool:
    """Whether sherpa-onnx can be imported, here or from beside the models."""
    try:
        if importlib.util.find_spec("sherpa_onnx") is not None:
            return True
    except Exception:  # noqa: BLE001 - any probing failure means "look further"
        pass
    from quill.core.windows_dictation.engines import package_dirs

    return any((folder / "sherpa_onnx").is_dir() for folder in package_dirs())


def _dictation_transcribe(samples: Any) -> str:
    """One piece of audio through live dictation's Moonshine, held while it runs."""
    from quill.core.windows_dictation.local_recognizer import _UNLOADER, transcribe

    _UNLOADER.busy()
    try:
        return transcribe("moonshine", samples)
    finally:
        _UNLOADER.idle()


def read_wav_samples(path: Path) -> tuple[Any, float]:
    """A 16 kHz mono 16-bit WAV as float32 samples in [-1, 1], and its length."""
    import numpy as np

    try:
        wf = wave.open(str(path), "rb")
    except Exception as exc:  # noqa: BLE001 - any read failure is one sentence
        raise SpeechError(f"Could not read the recording: {exc}") from exc
    with wf:
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() != _RATE:
            raise SpeechError("Moonshine tiny needs 16 kHz mono 16-bit WAV audio.")
        frames = wf.readframes(wf.getnframes())
    samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    return samples, len(samples) / _RATE


class MoonshineTinyProvider:
    """The bundled Moonshine tiny model, for Voice Command and Hey QUILL."""

    id = PROVIDER_ID
    display_name = "Moonshine tiny (fast, light)"
    description = (
        "The small English speech model built into QUILL. Fast and light, so it "
        "suits the always-listening Hey QUILL wake word. Nothing to download, and "
        "no audio leaves your computer."
    )
    requires_network = False

    def __init__(
        self,
        *,
        transcriber: Transcriber | None = None,
        folder: FolderFinder | None = None,
        sherpa_present: Callable[[], bool] | None = None,
    ) -> None:
        self._transcriber = transcriber or _dictation_transcribe
        self._folder = folder or _bundled_folder
        self._sherpa_present = sherpa_present or _sherpa_present

    # -- availability ----------------------------------------------------- #

    def _model_folder(self) -> Path | None:
        try:
            return self._folder()
        except Exception:  # noqa: BLE001 - a probing failure means "not here"
            return None

    def is_available(self) -> bool:
        try:
            return self._model_folder() is not None and bool(self._sherpa_present())
        except Exception:  # noqa: BLE001 - a probing failure means unavailable
            return False

    def get_install_status(self) -> ProviderInstallStatus:
        if self._model_folder() is None:
            return ProviderInstallStatus(
                installed=False,
                detail="The built-in Moonshine tiny model is missing. Reinstalling QUILL "
                "puts it back.",
            )
        if not self._sherpa_present():
            return ProviderInstallStatus(
                installed=False,
                detail="The built-in speech engines are not included in this copy of QUILL.",
            )
        return ProviderInstallStatus(installed=True, detail="CPU")

    # -- models ----------------------------------------------------------- #

    def list_supported_models(self) -> list[SpeechModelInfo]:
        return []  # nothing to download: the one model ships with QUILL

    def list_installed_models(self) -> list[InstalledSpeechModel]:
        folder = self._model_folder()
        if folder is None or not self.is_available():
            return []
        return [
            InstalledSpeechModel(
                id=MODEL_ID,
                display_name=_DISPLAY_MODEL,
                path=folder,
                size_mb=_APPROX_SIZE_MB,
                provider_id=PROVIDER_ID,
            )
        ]

    def estimate_model_size(self, model_id: str) -> SizeEstimate:
        return SizeEstimate(download_mb=0, on_disk_mb=_APPROX_SIZE_MB)

    def download_model(
        self, model_id: str, progress: ProgressCallback | None = None
    ) -> InstalledSpeechModel:
        raise SpeechError("Moonshine tiny is built into QUILL. There is nothing to download.")

    def remove_model(self, model_id: str) -> None:
        raise SpeechError("Moonshine tiny is part of QUILL and cannot be removed on its own.")

    # -- transcription ---------------------------------------------------- #

    def transcribe_file(
        self, request: TranscriptionRequest, progress: ProgressCallback | None = None
    ) -> TranscriptionResult:
        if not request.source_path.is_file():
            raise SpeechError(f"The recording was not found: {request.source_path}")
        if self._model_folder() is None:
            raise SpeechError(
                "The built-in Moonshine tiny model is missing. Reinstalling QUILL puts it back."
            )
        samples, duration = read_wav_samples(request.source_path)
        if progress is not None:
            progress(0.1, "Recognizing...")
        piece = _RATE * _PIECE_SECONDS
        texts: list[str] = []
        try:
            for start in range(0, max(len(samples), 1), piece):
                chunk = samples[start : start + piece]
                if len(chunk) == 0:
                    continue
                text = str(self._transcriber(chunk) or "").strip()
                if text:
                    texts.append(text)
        except SpeechError:
            raise
        except Exception as exc:  # noqa: BLE001 - one speakable sentence
            raise SpeechError(f"Moonshine tiny could not recognize the recording: {exc}") from exc
        full_text = " ".join(texts)
        segments = (TranscriptionSegment(0.0, float(duration), full_text),) if full_text else ()
        if progress is not None:
            progress(1.0, "Done.")
        return TranscriptionResult(
            full_text=full_text,
            segments=segments,
            provider_id=PROVIDER_ID,
            model_id=request.model_id or MODEL_ID,
            language="en",
            duration_seconds=duration,
        )

    def cancel(self) -> None:
        return None

    def unload(self) -> None:
        # The recogniser is live dictation's, and its idle unloader owns it.
        return None
