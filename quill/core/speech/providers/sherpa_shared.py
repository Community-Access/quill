"""One provider for every local sherpa-onnx model (dict.md D-26).

QUILL's Locked Dictation, offline Transcribe Audio or Video and the voice
features reach a speech engine through the
:class:`~quill.core.speech.provider.SpeechToTextProvider` shape. Live
dictation, QUILL Lite and QUILL Transcribe reach the same sherpa-onnx models
through :mod:`quill.core.windows_dictation`. Until 2026-10-16 the first path
had two engines of its own for Nemotron and Parakeet, with a second model
folder; this one adapter replaced both, so **one model folder serves every
app** and a fix to the pipeline is made once:

* **The models** are the family store's
  (:mod:`~quill.core.windows_dictation.model_store`): the built-in Moonshine
  tiny and Whisper tiny, and every model downloaded in Dictation Settings,
  Speech Models, in QUILL, QUILL Lite or QUILL Transcribe. A Parakeet that was
  downloaded the old way is adopted into the store the first time the list is
  read (:mod:`quill.core.speech.sherpa_migration`), never downloaded twice.
* **The pipeline** is Transcribe a Recording's
  (:class:`~quill.core.windows_dictation.file_transcribe.FileTranscriber`):
  decoding, Silero voice detection, the engine a phrase at a time, and
  dictation's tidying. So Locked Dictation and Transcribe a Recording give the
  same text for the same file and model, by construction.
* **Translation** into English goes to multilingual Whisper with
  ``task="translate"``; any other model refuses in one sentence
  (``QUILL-SPEECH-SHERPA-UNSUPPORTED``) rather than returning untranslated text.
* **An initial prompt** (Locked Dictation's dictation profile) is not something
  any sherpa-onnx model takes. It is reported as one warning sentence, never
  silently dropped; My Words still apply afterwards.
* **Speaker labels** come from :mod:`~quill.core.windows_dictation.post_passes`
  once a speaker model is adopted (D-29); until then a request for them is one
  warning sentence.

wx-free. Every heavy piece is injectable, so the tests use fakes and download
nothing.
"""

from __future__ import annotations

import importlib.util
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.speech.provider import (
    InstalledSpeechModel,
    ProgressCallback,
    ProviderInstallStatus,
    SizeEstimate,
    SpeechCancelledError,
    SpeechError,
    SpeechModelInfo,
    TranscriptionRequest,
    TranscriptionResult,
    TranscriptionSegment,
)

PROVIDER_ID = "sherpa"
#: The two models every copy ships, by engine id: (name, approximate MB).
_BUILT_IN: dict[str, tuple[str, int]] = {
    "moonshine": ("Moonshine tiny (built in)", 119),
    "whisper": ("Whisper tiny (built in)", 99),
}
#: Said when a request carries an initial prompt (the old whisper.cpp feature).
PROMPT_UNSUPPORTED = (
    "This engine does not take an initial prompt, so the prompt was not used; "
    "your words in My Words and Phrases still correct the text."
)
_TIER_ACCURACY = {"Lightweight": "medium", "Balanced": "high", "High accuracy": "highest"}

FileRunner = Callable[[Any, Callable[[float | None, float], None], Callable[[], bool]], Any]


def _sherpa_present() -> bool:
    try:
        if importlib.util.find_spec("sherpa_onnx") is not None:
            return True
    except Exception:  # noqa: BLE001 - any probing failure means "look further"
        pass
    from quill.core.windows_dictation.engines import package_dirs

    return any((folder / "sherpa_onnx").is_dir() for folder in package_dirs())


def _built_in_folder(engine_id: str) -> Path | None:
    from quill.core.windows_dictation.engines import model_dir

    return model_dir(engine_id)


def _run_file(job: Any, progress: Callable[[float | None, float], None], cancelled: Any) -> Any:
    from quill.core.windows_dictation.file_transcribe import FileTranscriber

    return FileTranscriber(job).run(progress, cancelled)


def model_info(model: Any) -> SpeechModelInfo:
    """A catalogue model as the model manager lists it."""
    from quill.core.windows_dictation.model_types import TRANSLATE, ram_tier_sentence

    cost = model.cost_factor
    capabilities = ["silence-safe"] if model.kind in {"nemo_transducer", "nemotron"} else []
    if model.streaming:
        capabilities.append("streaming")
    if TRANSLATE in model.tasks:
        capabilities.append("translate")
    return SpeechModelInfo(
        id=model.id,
        display_name=model.name,
        language_mode="english" if model.languages == ("en",) else "multilingual",
        approximate_size_mb=round(model.download_bytes / 1_000_000),
        accuracy_tier=_TIER_ACCURACY.get(model.tier, "high"),
        speed_tier="fast" if cost <= 5 else ("medium" if cost <= 10 else "slow"),
        recommended_use=f"{model.good_for} {ram_tier_sentence(model.ram_tier)}",
        download_url=model.source_url,
        license_name=model.licence,
        revision=model.commit,
        capabilities=tuple(capabilities),
    )


def can_translate(model_id: str, language: str) -> bool:
    """Whether *model_id* can turn *language* speech into English text: a
    multilingual Whisper (the built-ins use one for Spanish)."""
    from quill.core.windows_dictation.model_catalog import downloadable
    from quill.core.windows_dictation.model_types import TRANSLATE

    if language == "en":
        return False
    model = downloadable(model_id)
    if model is not None:
        return TRANSLATE in model.tasks and language in model.languages
    return model_id in _BUILT_IN  # Spanish runs the multilingual Whisper tiny


class SherpaSharedProvider:
    """Every local sherpa-onnx model, from the family's one model store."""

    id = PROVIDER_ID
    display_name = "QUILL speech models (on this computer)"
    description = (
        "The speech models QUILL, QUILL Lite and QUILL Transcribe share: the built-in "
        "Moonshine and Whisper, and any model downloaded in Dictation Settings, "
        "Speech Models, such as Parakeet or Nemotron. A model downloaded in any of "
        "the apps is used by all of them. Runs on your computer's processor, and no "
        "audio leaves your computer."
    )
    requires_network = False

    def __init__(
        self,
        *,
        run_file: FileRunner | None = None,
        sherpa_present: Callable[[], bool] | None = None,
        built_in_folder: Callable[[str], Path | None] | None = None,
        downloaded: Callable[[], list[Any]] | None = None,
        adopt: Callable[[], list[str]] | None = None,
    ) -> None:
        self._run_file = run_file or _run_file
        self._sherpa_present = sherpa_present or _sherpa_present
        self._built_in_folder = built_in_folder or _built_in_folder
        self._downloaded = downloaded
        self._adopt = adopt
        self._adopted = False
        self._cancel = threading.Event()

    # -- availability ----------------------------------------------------- #

    def is_available(self) -> bool:
        try:
            return bool(self._sherpa_present())
        except Exception:  # noqa: BLE001 - a probing failure means unavailable
            return False

    def get_install_status(self) -> ProviderInstallStatus:
        if not self.is_available():
            return ProviderInstallStatus(
                installed=False,
                detail="The speech engine these models run on (sherpa-onnx) is not in "
                "this copy of QUILL. Install it from Download Optional Components.",
            )
        return ProviderInstallStatus(installed=True, detail="CPU")

    # -- models ----------------------------------------------------------- #

    def list_supported_models(self) -> list[SpeechModelInfo]:
        from quill.core.windows_dictation.model_catalog import CATALOGUE

        return [model_info(model) for model in CATALOGUE]

    def _downloaded_models(self) -> list[Any]:
        if not self._adopted:
            self._adopted = True
            try:
                from quill.core.speech.sherpa_migration import adopt_legacy_models

                (self._adopt or adopt_legacy_models)()
            except Exception:  # noqa: BLE001 - adoption is a saving, never a blocker
                pass
        if self._downloaded is not None:
            return list(self._downloaded())
        from quill.core.windows_dictation.model_store import installed_models

        return installed_models()

    def list_installed_models(self) -> list[InstalledSpeechModel]:
        """Every model here, most accurate first (Transcribe a Recording's order)."""
        from quill.core.windows_dictation.file_models import FILE_RANK
        from quill.core.windows_dictation.model_store import model_folder

        found: list[InstalledSpeechModel] = []
        for engine_id, (name, size_mb) in _BUILT_IN.items():
            folder = self._safe_folder(engine_id)
            if folder is not None:
                found.append(InstalledSpeechModel(engine_id, name, folder, size_mb, PROVIDER_ID))
        for model in self._downloaded_models():
            found.append(
                InstalledSpeechModel(
                    model.id,
                    f"{model.name} (downloaded)",
                    model_folder(model),
                    round(model.download_bytes / 1_000_000),
                    PROVIDER_ID,
                )
            )

        def rank(item: InstalledSpeechModel) -> int:
            return FILE_RANK.index(item.id) if item.id in FILE_RANK else len(FILE_RANK)

        return sorted(found, key=rank)

    def _safe_folder(self, engine_id: str) -> Path | None:
        try:
            return self._built_in_folder(engine_id)
        except Exception:  # noqa: BLE001 - a probing failure means "not here"
            return None

    def estimate_model_size(self, model_id: str) -> SizeEstimate:
        from quill.core.windows_dictation.model_catalog import downloadable

        if model_id in _BUILT_IN:
            return SizeEstimate(download_mb=0, on_disk_mb=_BUILT_IN[model_id][1])
        model = downloadable(model_id)
        size = round(model.download_bytes / 1_000_000) if model is not None else 0
        return SizeEstimate(download_mb=size, on_disk_mb=size)

    def download_model(
        self, model_id: str, progress: ProgressCallback | None = None
    ) -> InstalledSpeechModel:
        from quill.core.windows_dictation import model_store
        from quill.core.windows_dictation.model_catalog import downloadable

        if model_id in _BUILT_IN:
            raise SpeechError(
                f"{_BUILT_IN[model_id][0]} is part of QUILL; there is nothing to download."
            )
        model = downloadable(model_id)
        if model is None:
            raise SpeechError(f"No download is available for the '{model_id}' model.")
        problem = model_store.free_space_problem(model)
        if problem:
            raise SpeechError(problem)
        try:
            folder = model_store.download(model, progress=progress)
        except model_store.ModelDownloadError as error:
            raise SpeechError(str(error.args[0] if error.args else error)) from error
        return InstalledSpeechModel(
            model.id,
            f"{model.name} (downloaded)",
            folder,
            round(model.download_bytes / 1_000_000),
            PROVIDER_ID,
        )

    def remove_model(self, model_id: str) -> None:
        from quill.core.windows_dictation import model_store

        if model_id in _BUILT_IN:
            raise SpeechError(f"{_BUILT_IN[model_id][0]} is part of QUILL and cannot be removed.")
        try:
            model_store.remove(model_id)
        except model_store.ModelDownloadError as error:
            raise SpeechError(str(error.args[0] if error.args else error)) from error

    # -- transcription ---------------------------------------------------- #

    def warm(self, model_id: str) -> None:
        """Load the model ahead of the first dictation (the prewarm hook)."""
        from quill.core.windows_dictation.local_recognizer import _load

        _load(model_id or "moonshine")

    def transcribe_file(
        self, request: TranscriptionRequest, progress: ProgressCallback | None = None
    ) -> TranscriptionResult:
        from quill.core.windows_dictation.file_transcribe import (
            FileJob,
            FileTranscribeError,
            TranscriptionCancelled,
            plain,
        )
        from quill.core.windows_dictation.model_catalog import downloadable
        from quill.core.windows_dictation.model_loader import (
            SherpaRuntimeError,
            SherpaUnsupportedError,
            unsupported_translation,
        )
        from quill.core.windows_dictation.speech_language import coerce_speech_language

        if not request.source_path.is_file():
            raise SpeechError(f"The audio file was not found: {request.source_path}")
        if not self.is_available():
            raise SherpaRuntimeError(
                "The speech engine these models run on is not in this copy of QUILL."
            )
        model_id = request.model_id or "moonshine"
        language = coerce_speech_language(request.language or "en")
        if request.translate_to_english and not can_translate(model_id, language):
            model = downloadable(model_id)
            if model is not None:
                raise unsupported_translation(model)
            raise SherpaUnsupportedError(
                "Translating into English needs a recording in another language and a "
                "multilingual Whisper model."
            )
        warnings: list[str] = []
        if request.initial_prompt:
            warnings.append(PROMPT_UNSUPPORTED)
        job = FileJob(
            request.source_path,
            model_id,
            language=language,
            timestamps=request.output_timestamps,
            translate=request.translate_to_english,
        )
        self._cancel.clear()

        def heard(fraction: float | None, _seconds: float) -> None:
            if progress is not None:
                progress(0.5 if fraction is None else fraction, "Transcribing...")

        try:
            transcript = self._run_file(job, heard, self._cancel.is_set)
        except TranscriptionCancelled as error:
            raise SpeechCancelledError("Transcription cancelled.") from error
        except FileTranscribeError as error:
            raise SpeechError(plain(error)) from error
        if transcript.notice:
            warnings.append(transcript.notice)
        segments = self._segments(transcript, request, warnings)
        if progress is not None:
            progress(1.0, "Done.")
        return TranscriptionResult(
            full_text=transcript.text(),
            segments=segments,
            provider_id=PROVIDER_ID,
            model_id=model_id,
            language="en" if request.translate_to_english else language,
            duration_seconds=transcript.audio_seconds,
            warnings=tuple(warnings),
        )

    @staticmethod
    def _segments(
        transcript: Any, request: TranscriptionRequest, warnings: list[str]
    ) -> tuple[TranscriptionSegment, ...]:
        paragraphs = list(transcript.paragraphs)
        ends = [p.start for p in paragraphs[1:]] + [float(transcript.audio_seconds)]
        spans = [(p.start, max(p.start, end)) for p, end in zip(paragraphs, ends, strict=True)]
        labels = [""] * len(spans)
        if request.diarize:
            from quill.core.windows_dictation.post_passes import SPEAKERS_UNAVAILABLE

            warnings.append(SPEAKERS_UNAVAILABLE)  # until D-29's speaker model is adopted
        return tuple(
            TranscriptionSegment(start, end, p.text, speaker=label)
            for (start, end), p, label in zip(spans, paragraphs, labels, strict=True)
        )

    def cancel(self) -> None:
        self._cancel.set()

    def unload(self) -> None:
        # The recognisers are live dictation's cache, and its idle unloader owns it.
        return None
