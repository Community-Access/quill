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

from .speech.formatters import to_markdown, to_plain_text, to_srt, to_vtt
from .speech.provider import TranscriptionResult
from .watch_actions import (
    WatchActionOutcome,
    WatchItem,
    _BaseAction,
    _humanize_action_error,
)

logger = logging.getLogger(__name__)

#: Output formats the offline transcribe action can write, mapped to the sibling
#: file extension. "txt"/"md" use the whole result; "srt"/"vtt" need timestamped
#: segments and fall back to plain text when the engine returned none.
_TRANSCRIBE_OUTPUT_FORMATS: dict[str, str] = {
    "txt": ".txt",
    "srt": ".srt",
    "vtt": ".vtt",
    "md": ".md",
}


def _maybe_make_action_document(
    source_path: Path, transcript: str, options: Mapping[str, object]
) -> str:
    """Optionally run an AI Transcript Action and save a sibling document.

    When ``options["transcript_action"]`` names a Transcript Action (Meeting
    Minutes, Action Items, ...), generate it over the just-made transcript through
    the configured provider and write ``<stem>-<action>.md`` next to the source.
    Returns a short status fragment to append to the outcome message ('' when no
    action is requested). Never raises and never fails the transcript job — the
    transcript already succeeded, so a missing key or provider just skips the
    action with a clear note.
    """
    action_id = str(options.get("transcript_action", "")).strip()
    if not action_id:
        return ""
    try:
        from quill.core.ai.model_manager import load_ai_enabled
        from quill.core.ai.provider_backend import ProviderChatBackend
        from quill.core.ai.transcript_actions import run_action_by_id

        if not load_ai_enabled():
            return " (AI is off — kept just the transcript)"
        backend = ProviderChatBackend()
        ok, _reason = backend.is_available()
        if not ok:
            return " (no AI provider configured — kept just the transcript)"
        text, error = run_action_by_id(transcript, action_id, backend)
        if error or not (text and text.strip()):
            return f" (could not create the {action_id} document)"
        target = source_path.with_name(f"{source_path.stem}-{action_id}.md")
        body = text if text.endswith("\n") else text + "\n"
        target.write_text(body, encoding="utf-8")
    except Exception:  # noqa: BLE001 - never fail the transcript over the action
        logger.exception("Transcript action %r failed for %s", action_id, source_path)
        return " (the AI action failed — kept the transcript)"
    return f"; created {target.name}"


def _render_transcript(result: TranscriptionResult, output_format: str) -> tuple[str, str]:
    """Return ``(body, extension)`` for ``output_format``.

    Unknown formats and caption formats with no segments fall back to plain text,
    so a profile never writes an empty ``.srt``/``.vtt``.
    """
    fmt = (output_format or "txt").strip().lower()
    if fmt in ("srt", "vtt") and not result.segments:
        return to_plain_text(result), ".txt"
    if fmt == "srt":
        return to_srt(result.segments), ".srt"
    if fmt == "vtt":
        return to_vtt(result.segments), ".vtt"
    if fmt in ("md", "markdown"):
        return to_markdown(result), ".md"
    return to_plain_text(result), ".txt"


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
    label: str = "Transcribe audio (offline)"
    description: str = (
        "Transcribe each arriving audio or video file on your machine with the "
        "offline speech engine and save the transcript next to it (text, SubRip "
        ".srt, WebVTT .vtt, or Markdown)."
    )
    on_transcribe: Callable[[Path, Mapping[str, object]], TranscriptionResult] | None = None

    def _resolve_transcriber(self) -> Callable[[Path, Mapping[str, object]], TranscriptionResult]:
        if self.on_transcribe is not None:
            return self.on_transcribe

        def _default(path: Path, options: Mapping[str, object]) -> TranscriptionResult:
            from quill.core.speech.transcribe import transcribe_audio_file

            model_id = str(options.get("model_id", "")) or None
            language = str(options.get("language", "")) or None
            return transcribe_audio_file(path, model_id=model_id, language=language)

        return _default

    def validate(self, options: Mapping[str, object]) -> list[str]:
        output_format = str(options.get("output_format", "txt")).strip().lower()
        if output_format and output_format not in _TRANSCRIBE_OUTPUT_FORMATS:
            allowed = ", ".join(sorted(_TRANSCRIBE_OUTPUT_FORMATS))
            return [f"Unknown transcript format '{output_format}'. Choose one of: {allowed}."]
        # An injected transcriber owns its own availability; only the default,
        # engine-backed path needs a model installed to do anything.
        if self.on_transcribe is not None:
            return []
        try:
            from quill.core.speech.transcribe import has_installed_offline_model

            if not has_installed_offline_model():
                return [
                    "No offline speech model is installed. Open Tools > Speech > "
                    "Manage Speech Models to download one."
                ]
        except Exception:  # noqa: BLE001 - missing optional engine, not a crash
            return ["The offline speech engine is not available on this machine."]
        return []

    def preview(self, item: WatchItem, options: Mapping[str, object]) -> str:
        ext = _TRANSCRIBE_OUTPUT_FORMATS.get(
            str(options.get("output_format", "txt")).strip().lower(), ".txt"
        )
        return (
            f"Transcribe {item.source_path.name} on this machine with the offline "
            f"speech engine and save the transcript as {item.source_path.stem}{ext} "
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
            result = transcriber(path, options)
        except Exception as error:  # surfaced as a failed outcome
            logger.exception("Offline transcription failed for %s", path)
            return WatchActionOutcome.failed(_humanize_action_error(self.action_id, error))
        body, ext = _render_transcript(result, str(options.get("output_format", "txt")))
        if not body.endswith("\n"):
            body += "\n"
        target = path.with_suffix(ext)
        try:
            target.write_text(body, encoding="utf-8")
        except OSError as error:
            return WatchActionOutcome.failed(f"Could not write transcript: {error}")
        extra = _maybe_make_action_document(path, to_plain_text(result), options)
        return WatchActionOutcome.done(
            f"Transcribed {path.name} to {target.name}{extra}", result_path=target
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

        extra = _maybe_make_action_document(path, transcript, options)
        return WatchActionOutcome.done(
            f"Transcribed {path.name} to {target.name}{extra}", result_path=target
        )


__all__ = [
    "CloudTranscribeAction",
    "WhispererTranscribeAction",
]
