"""Transcription watch actions (WATCH-9, BITS Whisperer consolidation).

The two "turn arriving audio into a transcript" watch actions, split out of
:mod:`quill.core.watch_actions` to keep that module within its size budget
(GATE-11):

- :class:`WhispererTranscribeAction` -- offline, on-device (whisper.cpp / Faster
  Whisper); nothing is uploaded, so it needs no consent.
- :class:`CloudTranscribeAction` -- OpenAI Whisper cloud; gated by ``future.ai``
  and per-profile consent (no silent network).

Both share the base action plumbing from :mod:`quill.core.watch_actions`; this
module imports from there one-way. ``watch_actions.default_registry`` imports
these back lazily (inside the function) so there is no import-time cycle.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from .watch_actions import (
    WatchActionOutcome,
    WatchItem,
    _BaseAction,
    _humanize_action_error,
)

logger = logging.getLogger(__name__)


#: Audio/video containers the offline Whisperer engine accepts (decoded via the
#: bundled ffmpeg). Kept deliberately broad; unknown extensions are skipped, not
#: failed, so a mixed inbox folder is safe to point a transcribe profile at.
_TRANSCRIBE_AUDIO_EXTENSIONS = frozenset({
    ".mp3",
    ".m4a",
    ".aac",
    ".wav",
    ".flac",
    ".ogg",
    ".opus",
    ".wma",
    ".mp4",
    ".m4v",
    ".mov",
    ".mkv",
    ".webm",
    ".avi",
})


@dataclass(slots=True)
class WhispererTranscribeAction(_BaseAction):
    """Watch action: transcribe arriving audio offline with Whisperer (WATCH-9).

    The BITS Whisperer consolidation's offline path: it runs whisper.cpp or
    Faster Whisper entirely on the machine, so it carries no ``requires_consent``
    (nothing is uploaded) and is the on-device counterpart to
    :class:`CloudTranscribeAction`. It writes a sibling ``.txt`` transcript next
    to the source file.

    Transcription is delegated to an injected ``on_transcribe`` callback so the
    action stays wx-free and unit-testable without an engine present; when none
    is supplied it routes to :func:`quill.core.speech.transcribe.transcribe_audio_file`.
    The action is left ungated (``required_feature_id=""``) and instead reports
    itself unusable through :meth:`validate` when no offline model is installed,
    so it is discoverable with guidance rather than silently hidden.
    """

    action_id: str = "bw_transcribe"
    label: str = "Transcribe audio (Whisperer)"
    description: str = (
        "Transcribe each arriving audio or video file on your machine with the "
        "offline Whisperer engine and save the transcript as a text file next to it."
    )
    on_transcribe: Callable[[Path, Mapping[str, object]], str] | None = None
    output_suffix: str = ".txt"

    def _resolve_transcriber(self) -> Callable[[Path, Mapping[str, object]], str]:
        if self.on_transcribe is not None:
            return self.on_transcribe

        def _default(path: Path, options: Mapping[str, object]) -> str:
            from quill.core.speech.transcribe import transcribe_audio_file

            model_id = str(options.get("model_id", "")) or None
            language = str(options.get("language", "")) or None
            result = transcribe_audio_file(path, model_id=model_id, language=language)
            return result.full_text

        return _default

    def validate(self, options: Mapping[str, object]) -> list[str]:  # noqa: ARG002
        # An injected transcriber owns its own availability; only the default,
        # engine-backed path needs a model installed to do anything.
        if self.on_transcribe is not None:
            return []
        try:
            from quill.core.speech.transcribe import has_installed_offline_model

            if not has_installed_offline_model():
                return [
                    "No offline speech model is installed. Open Tools > Speech > "
                    "Whisperer > Manage Speech Models to download one."
                ]
        except Exception:  # noqa: BLE001 - missing optional engine, not a crash
            return ["The offline Whisperer engine is not available on this machine."]
        return []

    def preview(self, item: WatchItem, options: Mapping[str, object]) -> str:  # noqa: ARG002
        return (
            f"Transcribe {item.source_path.name} on this machine with the offline "
            f"Whisperer engine and save the transcript as {item.source_path.stem}.txt "
            "next to the audio (nothing is uploaded)."
        )

    def run(self, item: WatchItem, options: Mapping[str, object]) -> WatchActionOutcome:
        path = item.source_path
        if path.suffix.lower() not in _TRANSCRIBE_AUDIO_EXTENSIONS:
            return WatchActionOutcome.skipped(
                f"{path.name} is not a supported audio or video format. Skipped."
            )
        transcriber = self._resolve_transcriber()
        try:
            transcript = transcriber(path, options)
        except Exception as error:  # surfaced as a failed outcome
            logger.exception("Offline transcription failed for %s", path)
            return WatchActionOutcome.failed(_humanize_action_error(self.action_id, error))
        target = path.with_suffix(self.output_suffix)
        body = transcript if transcript.endswith("\n") else transcript + "\n"
        try:
            target.write_text(body, encoding="utf-8")
        except OSError as error:
            return WatchActionOutcome.failed(f"Could not write transcript: {error}")
        return WatchActionOutcome.done(
            f"Transcribed {path.name} to {target.name}", result_path=target
        )


@dataclass(slots=True)
class CloudTranscribeAction(_BaseAction):
    """Watch action: transcribe arriving audio via OpenAI Whisper (AI-cloud).

    Gated by ``future.ai`` and requires an OpenAI API key stored in the
    credential manager. Sends audio bytes to the OpenAI transcription endpoint
    (GATE-9 reviewed: ``transcription.py::_post_audio``). The user must have
    enabled AI and configured an OpenAI API key — no silent transcription.

    The action writes a sibling ``.txt`` file next to the audio file.
    Supported extensions: .mp3, .mp4, .m4a, .wav, .webm, .ogg, .flac.
    Files over 25 MB are skipped with a OUTCOME_SKIPPED outcome.
    """

    action_id: str = "cloud_transcribe"
    label: str = "Transcribe audio (OpenAI Whisper)"
    description: str = (
        "Transcribe arriving audio files via OpenAI Whisper and save the transcript "
        "as a text file next to the audio. Requires an OpenAI API key."
    )
    required_feature_id: str = "future.ai"
    requires_consent: bool = True
    output_suffix: str = ".txt"

    def describe(self) -> str:
        return self.description

    def preview(self, item: WatchItem, options: Mapping[str, object]) -> str:  # noqa: ARG002
        return (
            f"Transcribe {item.source_path.name} via OpenAI Whisper and save "
            f"the transcript as {item.source_path.stem}.txt next to the audio file."
        )

    def validate(self, options: Mapping[str, object]) -> list[str]:  # noqa: ARG002
        problems: list[str] = []
        try:
            from quill.core.assistant_ai import load_assistant_api_key

            if not load_assistant_api_key():
                problems.append(
                    "No OpenAI API key is configured. "
                    "Add one in AI Hub before using cloud transcription."
                )
        except Exception:  # noqa: BLE001
            problems.append("Could not check API key configuration.")
        return problems

    def run(self, item: WatchItem, options: Mapping[str, object]) -> WatchActionOutcome:
        from quill.core.ai.transcription import (
            MAX_FILE_SIZE_BYTES,
            SUPPORTED_AUDIO_EXTENSIONS,
            TranscriptionError,
            TranscriptionFileTooLargeError,
            TranscriptionFormatError,
            transcribe_file,
        )
        from quill.core.assistant_ai import load_assistant_api_key

        path = item.source_path
        if path.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
            return WatchActionOutcome.skipped(
                f"{path.name} is not a supported audio format. Skipped."
            )

        size = path.stat().st_size if path.exists() else 0
        if size > MAX_FILE_SIZE_BYTES:
            size_mb = size / (1024 * 1024)
            return WatchActionOutcome.skipped(
                f"{path.name} is {size_mb:.1f} MB, which exceeds the 25 MB cloud limit. Skipped."
            )

        api_key = load_assistant_api_key() or ""
        if not api_key:
            return WatchActionOutcome.failed(
                "No OpenAI API key configured. Add one in AI Hub to use cloud transcription."
            )

        language = str(options.get("language", "")) or None
        try:
            transcript = transcribe_file(path, api_key, language=language)
        except TranscriptionFileTooLargeError as exc:
            return WatchActionOutcome.skipped(str(exc))
        except TranscriptionFormatError as exc:
            return WatchActionOutcome.skipped(str(exc))
        except TranscriptionError as exc:
            logger.exception("Cloud transcription failed for %s", path)
            return WatchActionOutcome.failed(f"Transcription failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            logger.exception("Cloud transcription crashed for %s", path)
            return WatchActionOutcome.failed(_humanize_action_error(self.action_id, exc))

        target = path.with_suffix(self.output_suffix)
        body = transcript if transcript.endswith("\n") else transcript + "\n"
        try:
            target.write_text(body, encoding="utf-8")
        except OSError as exc:
            return WatchActionOutcome.failed(f"Could not write transcript: {exc}")

        return WatchActionOutcome.done(
            f"Transcribed {path.name} to {target.name}", result_path=target
        )


__all__ = [
    "CloudTranscribeAction",
    "WhispererTranscribeAction",
]
