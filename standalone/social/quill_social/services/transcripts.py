"""Transcript model, import/export, search, and playback sync (PRD 19.5).

A transcript is an ordered list of :class:`Cue`s, each a start/end millisecond
window and its text. QUILL Social lets a listener read a supplied transcript,
search it, jump playback to a line, quote a time point, clip a range, and export
to SRT, VTT, TXT, or Markdown (PRD 19.5).

Everything here is pure, deterministic parsing and formatting -- no timers, no
randomness, no wall-clock. Transcripts persist through the generic document
store under kind ``"transcript"``, keyed by the resource id (a media uri or item
id), so a corrected transcript survives with the rest of the durable local data.

The SRT/VTT parsers are intentionally small and forgiving: they accept the
common single-file forms produced by the ecosystem (QUILL Cast, QUILL Audio
Studio) and round-trip cleanly, without pulling in a subtitle library.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from quill_social.db import SocialStore

DOC_KIND = "transcript"

_SRT_TIME = re.compile(
    r"(?P<h>\d+):(?P<m>\d{2}):(?P<s>\d{2})[,.](?P<ms>\d{1,3})"
)
# "start --> end" with either , or . as the millisecond separator.
_SRT_RANGE = re.compile(
    r"(?P<start>\d+:\d{2}:\d{2}[,.]\d{1,3})\s*-->\s*(?P<end>\d+:\d{2}:\d{2}[,.]\d{1,3})"
)


@dataclass
class Cue:
    """One timed line of a transcript (PRD 19.5)."""

    start_ms: int = 0
    end_ms: int = 0
    text: str = ""

    def to_dict(self) -> dict:
        return {"start_ms": self.start_ms, "end_ms": self.end_ms, "text": self.text}

    @classmethod
    def from_dict(cls, d: dict) -> Cue:
        return cls(
            start_ms=int(d.get("start_ms", 0) or 0),
            end_ms=int(d.get("end_ms", 0) or 0),
            text=d.get("text", ""),
        )

    def contains(self, ms: int) -> bool:
        return self.start_ms <= ms < self.end_ms


@dataclass
class Transcript:
    """An ordered set of cues for one media resource (PRD 19.5)."""

    resource_id: str = ""  # media uri or item id this transcript belongs to
    lang: str = ""
    source: str = "supplied"  # supplied | generated | corrected
    cues: list[Cue] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "resource_id": self.resource_id,
            "lang": self.lang,
            "source": self.source,
            "cues": [c.to_dict() for c in self.cues],
        }

    @classmethod
    def from_dict(cls, d: dict) -> Transcript:
        return cls(
            resource_id=d.get("resource_id", ""),
            lang=d.get("lang", ""),
            source=d.get("source", "supplied"),
            cues=[Cue.from_dict(c) for c in d.get("cues", [])],
        )

    @property
    def duration_ms(self) -> int:
        return max((c.end_ms for c in self.cues), default=0)


# -- time formatting --------------------------------------------------------


def _parse_timestamp(text: str) -> int:
    m = _SRT_TIME.search(text.strip())
    if not m:
        return 0
    frac = m.group("ms")
    millis = int((frac + "000")[:3])  # pad/truncate to exactly 3 digits
    return (
        int(m.group("h")) * 3_600_000
        + int(m.group("m")) * 60_000
        + int(m.group("s")) * 1000
        + millis
    )


def _fmt_srt_time(ms: int) -> str:
    ms = max(0, int(ms))
    hours, rem = divmod(ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, millis = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def _fmt_vtt_time(ms: int) -> str:
    return _fmt_srt_time(ms).replace(",", ".")


def _fmt_clock(ms: int) -> str:
    """``mm:ss`` (or ``h:mm:ss``) for a quotable, spoken time point (PRD 19.5)."""
    total = max(0, int(ms)) // 1000
    hours, rem = divmod(total, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


# -- import -----------------------------------------------------------------


def _split_blocks(text: str) -> list[list[str]]:
    """Split a cue file into blocks separated by blank lines."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in normalized.split("\n"):
        if line.strip() == "":
            if current:
                blocks.append(current)
                current = []
        else:
            current.append(line)
    if current:
        blocks.append(current)
    return blocks


def _cues_from_blocks(blocks: list[list[str]]) -> list[Cue]:
    cues: list[Cue] = []
    for block in blocks:
        range_line_idx = None
        for i, line in enumerate(block):
            if "-->" in line:
                range_line_idx = i
                break
        if range_line_idx is None:
            continue  # a header (WEBVTT) or index-only block; skip
        m = _SRT_RANGE.search(block[range_line_idx])
        if not m:
            continue
        start = _parse_timestamp(m.group("start"))
        end = _parse_timestamp(m.group("end"))
        body = "\n".join(block[range_line_idx + 1 :]).strip()
        cues.append(Cue(start_ms=start, end_ms=end, text=body))
    return cues


def from_srt(text: str, *, resource_id: str = "", lang: str = "") -> Transcript:
    """Parse SubRip (SRT) subtitle text into a transcript (PRD 19.5)."""
    cues = _cues_from_blocks(_split_blocks(text))
    return Transcript(resource_id=resource_id, lang=lang, source="supplied", cues=cues)


def from_vtt(text: str, *, resource_id: str = "", lang: str = "") -> Transcript:
    """Parse WebVTT text into a transcript (PRD 19.5).

    The mandatory ``WEBVTT`` header and any ``NOTE``/style blocks are ignored;
    only timed cue blocks become :class:`Cue`s.
    """
    cues = _cues_from_blocks(_split_blocks(text))
    return Transcript(resource_id=resource_id, lang=lang, source="supplied", cues=cues)


# -- export -----------------------------------------------------------------


def to_srt(transcript: Transcript) -> str:
    """Render a transcript as SubRip (SRT) text (PRD 19.5)."""
    out: list[str] = []
    for i, cue in enumerate(transcript.cues, start=1):
        out.append(str(i))
        out.append(f"{_fmt_srt_time(cue.start_ms)} --> {_fmt_srt_time(cue.end_ms)}")
        out.append(cue.text)
        out.append("")
    return "\n".join(out).rstrip("\n") + "\n"


def to_vtt(transcript: Transcript) -> str:
    """Render a transcript as WebVTT text (PRD 19.5)."""
    out: list[str] = ["WEBVTT", ""]
    for cue in transcript.cues:
        out.append(f"{_fmt_vtt_time(cue.start_ms)} --> {_fmt_vtt_time(cue.end_ms)}")
        out.append(cue.text)
        out.append("")
    return "\n".join(out).rstrip("\n") + "\n"


def to_txt(transcript: Transcript) -> str:
    """Render just the transcript text, one cue per line (PRD 19.5)."""
    return "\n".join(cue.text for cue in transcript.cues) + (
        "\n" if transcript.cues else ""
    )


def to_markdown(transcript: Transcript) -> str:
    """Render a readable Markdown transcript with time points (PRD 19.5)."""
    lines: list[str] = ["# Transcript"]
    if transcript.lang:
        lines.append(f"Language: {transcript.lang}")
    lines.append("")
    for cue in transcript.cues:
        lines.append(f"- **[{_fmt_clock(cue.start_ms)}]** {cue.text}")
    return "\n".join(lines) + "\n"


# -- query ------------------------------------------------------------------


def search(transcript: Transcript, query: str) -> list[Cue]:
    """Return cues whose text contains ``query`` (case-insensitive) (PRD 19.5)."""
    q = query.strip().lower()
    if not q:
        return []
    return [cue for cue in transcript.cues if q in cue.text.lower()]


def cue_at(transcript: Transcript, ms: int) -> Cue | None:
    """The cue active at ``ms`` for playback sync (PRD 19.5).

    A cue covers ``[start_ms, end_ms)``. If ``ms`` falls in a gap between cues,
    returns ``None``; before the first cue also returns ``None``.
    """
    for cue in transcript.cues:
        if cue.contains(ms):
            return cue
    return None


def quote_timepoint(transcript: Transcript, ms: int) -> str:
    """A quotable ``"text @ mm:ss"`` string for a time point (PRD 19.5).

    Uses the cue active at ``ms`` when there is one; otherwise the nearest cue at
    or before ``ms`` so a quote at a gap still reads sensibly.
    """
    cue = cue_at(transcript, ms)
    if cue is None:
        before = [c for c in transcript.cues if c.start_ms <= ms]
        cue = before[-1] if before else None
    if cue is None:
        return f"@ {_fmt_clock(ms)}"
    text = cue.text.replace("\n", " ").strip()
    return f"{text} @ {_fmt_clock(cue.start_ms)}"


def make_clip(transcript: Transcript, start_ms: int, end_ms: int) -> Transcript:
    """Extract a sub-transcript covering ``[start_ms, end_ms)`` (PRD 19.5).

    Cues that overlap the range are included, and their times are rebased so the
    clip starts at 0 -- ready to attach to a fresh clip in QUILL Audio Studio.
    """
    lo, hi = (start_ms, end_ms) if start_ms <= end_ms else (end_ms, start_ms)
    clip_cues: list[Cue] = []
    for cue in transcript.cues:
        if cue.end_ms <= lo or cue.start_ms >= hi:
            continue
        new_start = max(cue.start_ms, lo) - lo
        new_end = min(cue.end_ms, hi) - lo
        clip_cues.append(Cue(start_ms=new_start, end_ms=new_end, text=cue.text))
    return Transcript(
        resource_id=transcript.resource_id,
        lang=transcript.lang,
        source="corrected" if transcript.source == "corrected" else transcript.source,
        cues=clip_cues,
    )


# -- persistence ------------------------------------------------------------


def save_transcript(store: SocialStore, transcript: Transcript) -> None:
    """Persist a transcript under kind ``transcript``, keyed by resource id."""
    store.put_document(DOC_KIND, transcript.resource_id, transcript.to_dict())


def load_transcript(store: SocialStore, resource_id: str) -> Transcript | None:
    """Load a persisted transcript by resource id, or ``None`` if absent."""
    data = store.get_document(DOC_KIND, resource_id)
    return Transcript.from_dict(data) if data else None


def delete_transcript(store: SocialStore, resource_id: str) -> None:
    """Remove a persisted transcript by resource id."""
    store.delete_document(DOC_KIND, resource_id)
