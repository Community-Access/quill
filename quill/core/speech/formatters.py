"""Transcription output formatters: TXT, SRT, VTT, JSON (#617 section 6.2).

Pure functions that turn a :class:`TranscriptionResult` (or its segments) into
the standard caption/transcript formats. No I/O, no wx — the UI decides where to
write the returned string.
"""

from __future__ import annotations

import html
import json

from quill.core.speech.provider import TranscriptionResult, TranscriptionSegment


def _turns(result: TranscriptionResult) -> list[tuple[str, str]]:
    """Group segments into ``(speaker, text)`` turns (merging consecutive speakers).

    Falls back to a single empty-speaker turn carrying ``full_text`` when there
    are no segments.
    """
    if not result.segments:
        return [("", result.full_text.strip())]
    turns: list[list[str]] = []
    speakers: list[str] = []
    for seg in result.segments:
        text = seg.text.strip()
        if not text:
            continue
        if turns and speakers[-1] == seg.speaker:
            turns[-1].append(text)
        else:
            turns.append([text])
            speakers.append(seg.speaker)
    return [(spk, " ".join(parts)) for spk, parts in zip(speakers, turns, strict=True)]


def _has_speakers(result: TranscriptionResult) -> bool:
    return any(seg.speaker for seg in result.segments)


def to_plain_text(result: TranscriptionResult) -> str:
    """The transcript as plain text (with "Speaker N:" prefixes when available)."""
    if _has_speakers(result):
        lines = [f"{spk}: {text}" if spk else text for spk, text in _turns(result)]
        return "\n".join(lines).strip() + "\n"
    return result.full_text.strip() + "\n"


def to_markdown(result: TranscriptionResult) -> str:
    """The transcript as Markdown (speaker turns in bold when available)."""
    parts = ["# Transcript", ""]
    for spk, text in _turns(result):
        parts.append(f"**{spk}:** {text}" if spk else text)
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def to_html(result: TranscriptionResult) -> str:
    """The transcript as a minimal standalone HTML document."""
    body: list[str] = []
    for spk, text in _turns(result):
        escaped = html.escape(text)
        if spk:
            body.append(f"<p><strong>{html.escape(spk)}:</strong> {escaped}</p>")
        else:
            body.append(f"<p>{escaped}</p>")
    return (
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        "<title>Transcript</title>\n</head>\n<body>\n<h1>Transcript</h1>\n"
        + "\n".join(body)
        + "\n</body>\n</html>\n"
    )


def to_srt(segments: tuple[TranscriptionSegment, ...]) -> str:
    """SubRip (.srt) captions. Indices are 1-based; times use a comma."""
    blocks: list[str] = []
    for index, segment in enumerate(segments, start=1):
        blocks.append(
            f"{index}\n"
            f"{_srt_timestamp(segment.start_seconds)} --> {_srt_timestamp(segment.end_seconds)}\n"
            f"{segment.text.strip()}\n"
        )
    return "\n".join(blocks)


def to_vtt(segments: tuple[TranscriptionSegment, ...]) -> str:
    """WebVTT (.vtt) captions. Header + dot-separated times."""
    parts = ["WEBVTT", ""]
    for segment in segments:
        parts.append(
            f"{_vtt_timestamp(segment.start_seconds)} --> {_vtt_timestamp(segment.end_seconds)}"
        )
        parts.append(segment.text.strip())
        parts.append("")
    return "\n".join(parts)


def to_json(result: TranscriptionResult) -> str:
    """A structured JSON transcript (stable keys, 2-space indent)."""
    payload = {
        "provider_id": result.provider_id,
        "model_id": result.model_id,
        "language": result.language,
        "duration_seconds": result.duration_seconds,
        "full_text": result.full_text,
        "segments": [
            {
                "start_seconds": round(seg.start_seconds, 3),
                "end_seconds": round(seg.end_seconds, 3),
                "text": seg.text,
            }
            for seg in result.segments
        ],
        "warnings": list(result.warnings),
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def _clamp(seconds: float) -> float:
    return seconds if seconds > 0 else 0.0


def _split_hms_ms(seconds: float) -> tuple[int, int, int, int]:
    total_ms = int(round(_clamp(seconds) * 1000))
    hours, total_ms = divmod(total_ms, 3_600_000)
    minutes, total_ms = divmod(total_ms, 60_000)
    secs, millis = divmod(total_ms, 1000)
    return hours, minutes, secs, millis


def _srt_timestamp(seconds: float) -> str:
    h, m, s, ms = _split_hms_ms(seconds)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _vtt_timestamp(seconds: float) -> str:
    h, m, s, ms = _split_hms_ms(seconds)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
