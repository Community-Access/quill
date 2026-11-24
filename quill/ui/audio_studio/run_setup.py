"""What a Studio narration run uses: one place, so a sample uses the same (FUX-11).

The batch runner (``quill.ui.batch_speech_runner``) and Try a Sample
(:mod:`quill.ui.audio_studio.try_sample`) both build their engine spec, their
assembly options and the list of audio-shaping settings here. A sample made
any other way would prove a different setup from the one the run uses.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from quill.ui.audio_studio.request import BatchSpeechRequest

if TYPE_CHECKING:
    from quill.core.speech.chapter_assemble import ChapterAssembleOptions
    from quill.core.speech.document_speech import SynthesisSpec

__all__ = [
    "chapter_options",
    "effective_format",
    "output_suffix",
    "shaping_settings",
    "synthesis_spec",
]


def effective_format(req: BatchSpeechRequest) -> str:
    """The per-document format: WAV chapters in book mode, else the chosen format."""
    return "wav" if req.make_book else req.output_format


def output_suffix(fmt: str) -> str:
    """The file suffix for a per-document *fmt*."""
    return {"mp3": ".mp3", "m4b": ".m4b"}.get(fmt, ".wav")


def synthesis_spec(req: BatchSpeechRequest) -> SynthesisSpec:
    """The engine, voice, rate and speed the run speaks with."""
    from quill.core.speech.document_speech import SynthesisSpec

    return SynthesisSpec(engine=req.engine, voice=req.voice, rate=req.rate, speed=req.speed)


def chapter_options(
    req: BatchSpeechRequest, *, sound_path: Path | None = None
) -> ChapterAssembleOptions:
    """Gaps, sounder, loudness, format and chunking, exactly as the run assembles."""
    from quill.core.speech.chapter_assemble import ChapterAssembleOptions
    from quill.core.speech.document_speech import engine_chunk_chars

    return ChapterAssembleOptions(
        article_gap_ms=req.article_gap_ms,
        sound_enabled=req.sound_enabled,
        sound_volume=req.sound_volume,
        sound_path=sound_path,
        output_format=effective_format(req),
        speak_headings=req.speak_headings,
        sentence_gap_ms=req.sentence_gap_ms,
        tail_padding_ms=req.tail_padding_ms,
        normalize_loudness=req.normalize_loudness,
        # Auto-chunk very long sections so a single synthesis call never runs
        # past the engine timeout; short sections are unaffected (one call).
        # Kokoro's ~510 phoneme-token window means over-feeding it stalls.
        max_chunk_chars=engine_chunk_chars(req.engine),
    )


def shaping_settings(frame: Any, req: BatchSpeechRequest, dictionaries: Any) -> dict[str, object]:
    """Every setting that changes the sound of the result.

    The incremental-rebuild cache fingerprints these, and so does a sample:
    when any of them changes, an earlier sample is out of date.
    """
    return {
        "engine": req.engine,
        "voice": req.voice,
        "rate": req.rate,
        "speed": req.speed,
        "format": effective_format(req),
        "sound": [
            req.sound_enabled,
            req.sound_volume,
            str(getattr(getattr(frame, "settings", None), "batch_speech_chapter_sound_id", "")),
        ],
        "gaps": [req.article_gap_ms, req.sentence_gap_ms, req.tail_padding_ms],
        "speak_headings": req.speak_headings,
        "combine_headings": req.combine_headings,
        "normalize_loudness": req.normalize_loudness,
        "round_robin": list(req.round_robin_voices),
        "casting": [list(rule) for rule in req.casting_rules],
        "translations": [list(t) for t in req.translation_targets],
        "translation_provider": req.translation_provider,
        "dictionaries": repr(dictionaries),
    }
