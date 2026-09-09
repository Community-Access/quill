"""What an episode already has, so nothing is generated twice.

The second module vendored byte-identical into QUILL
(``quill/core/speech/reuse_core.py``) and podHarvest
(``podharvest/reuse_core.py``), alongside ``audio_tags_core``. Same rules: it
imports nothing from either host, so both copies can be the same bytes, and a
SHA-256 drift test in each repo fails the build if they stop being.

It answers two questions, and both are versions of *do we already have this?*

**Which transcript.** A Podcasting 2.0 feed may carry several
``<podcast:transcript>`` elements for one episode -- the same words as JSON,
WebVTT, SRT and HTML. Taking the first one the feed happened to list gives the
choice to whoever wrote the element order, and only the structured formats
carry cue times. A publisher who listed HTML first silently cost their
listeners the timed reader, chapter inference and timestamped export, on every
episode, with no error anywhere. So the order here is by **what the format can
do**, not by preference, and an unrecognised type sorts last but is still kept:
a feed that grows a format nobody anticipated should degrade to "the words",
never to nothing.

**Where the chapters come from.** Most podcasts worth navigating already say
where their sections are -- in the file's own tags, or as timestamps in the
show notes -- and reading either costs nothing and yields titles a person
actually wrote. Generating chapters with a language model when the publisher
already wrote them is slower, worse, and rude about it.

The show-notes reader is lifted from QUILL Cast
(``quill/core/podcasts/show_note_chapters.py``), which is where it was worked
out against real feeds; Cast now delegates here so there is one implementation
rather than two that drift. Its docstrings keep the reasoning, because every
number in it has a podcast behind it.

Pure: string and tag parsing, no network, no model, no filesystem except the
one optional ID3 read, which is handed in as a callable.
"""

from __future__ import annotations

import html
import json
import re
from collections.abc import Callable
from dataclasses import dataclass

# --------------------------------------------------------------- transcripts

#: Best first. The rank is the format's *capability*, so a reader that needs
#: timings gets them whenever the source has them at all.
_TRANSCRIPT_RANK: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("json", ("application/json", "json")),
    ("vtt", ("text/vtt", "vtt", "webvtt")),
    ("srt", ("application/x-subrip", "srt", "subrip")),
    ("html", ("text/html", "html", "xhtml")),
    ("text", ("text/plain", "plain", "txt", "md", "markdown")),
)

#: What an unrecognised type scores. Below everything named, above nothing: an
#: unknown format is still a transcript, and refusing it would lose the words
#: in order to protect the timings.
TRANSCRIPT_UNKNOWN_RANK = len(_TRANSCRIPT_RANK)


def transcript_rank(transcript_type: object, url: object = "") -> int:
    """How good this representation is, lower being better (pure).

    The declared ``type`` decides it. When there is none -- which is legal and
    common -- the URL or filename's extension is the fallback, because a
    publisher who omitted the attribute still named the file.
    """
    declared = str(transcript_type or "").strip().lower()
    for index, (_name, tokens) in enumerate(_TRANSCRIPT_RANK):
        if any(token in declared for token in tokens):
            return index
    tail = str(url or "").strip().lower().split("?", 1)[0].rsplit(".", 1)
    suffix = tail[-1] if len(tail) == 2 else ""
    for index, (name, tokens) in enumerate(_TRANSCRIPT_RANK):
        if suffix and (suffix == name or suffix in tokens):
            return index
    return TRANSCRIPT_UNKNOWN_RANK


def best_transcript(candidates: list[tuple[object, object]]) -> tuple[object, object] | None:
    """The most capable of ``(type, url)`` pairs, or None when there are none.

    Ties keep feed order, so a publisher listing two WebVTT files still gets
    the one they put first.
    """
    best: tuple[object, object] | None = None
    best_rank = TRANSCRIPT_UNKNOWN_RANK + 1
    for entry in candidates:
        transcript_type, url = entry
        if not str(url or "").strip():
            continue
        score = transcript_rank(transcript_type, url)
        if score < best_rank:
            best, best_rank = entry, score
    return best


# ------------------------------------------------------ show-notes chapters

#: The most marks a real chapter list has. Beyond this it is a transcript, a
#: tracklist with per-second cues, or a page of times that is not a chapter
#: list.
MAX_MARKS = 120

#: Two marks closer together than this are not two chapters. Half a minute.
#: The floor is deliberately strict *and* applied per row: the defect in the
#: reader this replaced was never this number, it was that failing it discarded
#: the whole list instead of the one offending mark.
MIN_GAP_MS = 30_000

#: A chapter list that does not begin near the beginning is not this episode's
#: chapter list -- it is a schedule, a set of references, or somebody's notes.
MAX_FIRST_MARK_MS = 20 * 60 * 1000

#: How much of a list may be repaired before it stops being a list at all.
#: Dropping the odd unusable row is tidying; dropping a third of them means the
#: page was never a chapter list and the survivors are a coincidence.
MIN_MARK_RETENTION = 0.8

#: ``1:02:03`` / ``12:34`` / ``12.34`` -- colon or point separated.
_CLOCK = r"(?:(?P<h>\d{1,2})[:.])?(?P<m>\d{1,2})[:.](?P<s>\d{2})"

#: ``1h05m``, ``1 hr 5 min``, ``5m30s``, ``90s`` -- the spelled-out forms.
_SPELLED = (
    r"(?:(?P<sh>\d{1,2})\s*(?:h|hr|hrs|hour|hours)\s*)?"
    r"(?:(?P<sm>\d{1,3})\s*(?:m|min|mins|minute|minutes)\s*)?"
    r"(?:(?P<ss>\d{1,2})\s*(?:s|sec|secs|second|seconds))?"
)

_LEAD = r"^[\s\-\*•–—>]*(?:\d{1,3}[\.\)]\s*)?[\[\(]?"
_TRAIL = r"[\]\)]?"
_SEP = r"(?:\s*[-–—:\|]\s*|\s+)"

#: Timestamp first: "00:00 Introduction", "1. [1:02:03] - The interview".
_LEADING = re.compile(_LEAD + _CLOCK + _TRAIL + _SEP + r"(?P<title>\S.*?)\s*$")
_LEADING_SPELLED = re.compile(_LEAD + _SPELLED + _TRAIL + _SEP + r"(?P<title>\S.*?)\s*$")

#: Timestamp last: "Introduction — 00:00", "The interview (1:02:03)".
_TRAILING = re.compile(
    r"^[\s\-\*•–—>]*(?P<title>.*?\S)" + _SEP + r"[\[\(]?" + _CLOCK + r"[\]\)]?\s*$"
)


def _clock_ms(hours: str | None, minutes: str, seconds: str) -> int:
    return ((int(hours or 0) * 60 + int(minutes)) * 60 + int(seconds)) * 1000


def _spelled_ms(hours: str | None, minutes: str | None, seconds: str | None) -> int:
    if not any((hours, minutes, seconds)):
        return -1
    return ((int(hours or 0) * 60 + int(minutes or 0)) * 60 + int(seconds or 0)) * 1000


def strip_markup(notes: str) -> str:
    """Show notes as lines of text, whether they arrived as HTML or as text.

    Show notes are *usually* markup, and a reader that only handled text was
    skipping most of the internet. Block tags become line breaks so a
    ``<li>00:00 Intro</li>`` list reads as one timestamp per line, which is
    what the line-oriented matching below assumes.
    """
    if "<" not in notes:
        return notes
    text = re.sub(r"(?i)<\s*br\s*/?>", "\n", notes)
    text = re.sub(r"(?i)</\s*(p|div|li|tr|h[1-6])\s*>", "\n", text)
    text = re.sub(r"(?i)<\s*(p|div|li|tr|h[1-6])[^>]*>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text)


def _mark_from_line(line: str) -> tuple[int, str] | None:
    """``(start_ms, title)`` for one line, or ``None``.

    Leading timestamps are tried before trailing ones: a line with a time at
    both ends is far more likely to be "00:00 Intro (2 min)" than a title
    ending in a time, and the leading form is the one that means what it looks
    like.
    """
    stripped = line.strip()
    if not stripped:
        return None
    for pattern in (_LEADING, _TRAILING):
        match = pattern.match(stripped)
        if match is None:
            continue
        title = (match.group("title") or "").strip(" -–—:|\t.")
        if not title:
            continue
        return _clock_ms(match.group("h"), match.group("m"), match.group("s")), title
    match = _LEADING_SPELLED.match(stripped)
    if match is not None:
        milliseconds = _spelled_ms(match.group("sh"), match.group("sm"), match.group("ss"))
        title = (match.group("title") or "").strip(" -–—:|\t.")
        if milliseconds >= 0 and title:
            return milliseconds, title
    return None


def parse_marks(notes: str) -> list[tuple[int, str]]:
    """Every timestamped line in *notes*, in the order written. No validation."""
    if not notes or not notes.strip():
        return []
    marks: list[tuple[int, str]] = []
    for line in strip_markup(notes).replace("\r", "\n").split("\n"):
        mark = _mark_from_line(line)
        if mark is not None:
            marks.append(mark)
    return marks


def usable_marks(marks: list[tuple[int, str]], *, total_ms: int = 0) -> list[tuple[int, str]]:
    """The marks that can be this episode's chapters, or ``[]`` for none.

    Rows are dropped, not the list: a mark that runs past the end of the
    episode, or that arrives too soon after the one before it, is discarded and
    the rest are kept. That single rule is worth more than every pattern this
    module recognises -- an outro sign-off twenty seconds from the end used to
    cost a publisher all ten of their authored chapters.

    The whole list is still refused when it was never a chapter list: fewer
    than two usable marks, implausibly many, a first mark an hour in, or so
    much repair needed that the survivors are a coincidence rather than a
    structure.
    """
    if len(marks) < 2 or len(marks) > MAX_MARKS:
        return []
    if marks[0][0] > MAX_FIRST_MARK_MS:
        return []

    kept: list[tuple[int, str]] = []
    for start_ms, title in marks:
        if total_ms and start_ms >= total_ms:
            continue
        # Strictly after the last mark kept, and far enough after it to be a
        # different chapter. This drops both an out-of-order row and a crammed
        # one, which are the same defect seen from two directions.
        if kept and start_ms - kept[-1][0] < MIN_GAP_MS:
            continue
        kept.append((start_ms, title))

    if len(kept) < 2 or len(kept) < MIN_MARK_RETENTION * len(marks):
        return []
    return kept


def looks_like_a_chapter_list(marks: list[tuple[int, str]], *, total_ms: int = 0) -> bool:
    """Whether these marks are this episode's chapters rather than merely times.

    Each refusal has a page behind it: a set of references with times, a
    schedule, a transcript with per-line cues. Returning any of them as
    chapters would be a confident wrong answer, which is the one output this
    refuses to produce.
    """
    return bool(usable_marks(marks, total_ms=total_ms))


def marks_from_notes(*sources: str, total_ms: int = 0) -> list[tuple[int, str]]:
    """Marks from the first of *sources* that yields a real chapter list.

    Several sources on purpose: the description, the summary, and any
    structured notes an episode carries are all places publishers put this, and
    reading only one field throws away lists that were right there.
    """
    for notes in sources:
        marks = usable_marks(parse_marks(notes or ""), total_ms=total_ms)
        if marks:
            return marks
    return []


# ------------------------------------------------------------- the cascade

#: How each source is described. A chapter list must never be mistaken for the
#: publisher's own when it was inferred, so the label travels with the list.
SOURCE_LABELS: dict[str, str] = {
    "published": "Published chapters",
    "file": "Chapters in the file",
    "show_notes": "From the show notes",
    "transcript": "From the transcript",
    "audio": "Detected from the audio",
    "suggested": "Suggested",
}

#: Sources whose titles were written by a person, so they are used as-is and
#: never re-generated.
AUTHORED_SOURCES: frozenset[str] = frozenset({"published", "file", "show_notes"})

#: Episodes shorter than this are not worth sectioning.
MIN_EPISODE_MS = 10 * 60 * 1000


@dataclass(slots=True)
class ChapterSource:
    """A chapter list and where it came from. Empty means nothing free was found."""

    marks: list[tuple[int, str]]
    source: str = ""

    def __bool__(self) -> bool:
        return bool(self.marks)

    @property
    def label(self) -> str:
        """What to tell the listener this list is."""
        return SOURCE_LABELS.get(self.source, "Chapters")

    @property
    def authored(self) -> bool:
        """Whether a person wrote these titles."""
        return self.source in AUTHORED_SOURCES


def free_chapters(
    *,
    published: Callable[[], list[tuple[int, str]]] | None = None,
    from_file: Callable[[], list[tuple[int, str]]] | None = None,
    show_notes: str = "",
    total_ms: int = 0,
) -> ChapterSource:
    """The first free, authored source that yields chapters, with its label.

    Cheapest and best first: what the publisher put in the feed, then what is
    already in the file's own tags, then the timestamps in the show notes. Each
    tier is free, and each carries titles a person wrote -- which is why all
    three beat anything a model could infer, not merely cost less.

    Both callables are callables because either may touch the network or the
    disk; neither is invoked unless the tier above it came up empty, and a tier
    that raises is treated as having no chapters rather than as an error. An
    empty result is not a failure: it means no free source had an answer, and
    the caller may now spend something.
    """
    if total_ms and total_ms < MIN_EPISODE_MS:
        return ChapterSource([])

    for name, getter in (("published", published), ("file", from_file)):
        if getter is None:
            continue
        try:
            marks = [(int(start), str(title)) for start, title in getter() if str(title)]
        except Exception:  # noqa: BLE001 - an unreadable source has no chapters
            marks = []
        if len(marks) >= 2:
            return ChapterSource(sorted(marks), name)

    marks = marks_from_notes(show_notes, total_ms=total_ms)
    if marks:
        return ChapterSource(marks, "show_notes")

    return ChapterSource([])


# ------------------------------------------------- reading a transcript file

#: A WebVTT/SRT cue line: a sequence number, or a timing line. Anything else is
#: spoken text to keep.
_VTT_TIMING_RE = re.compile(r"^\d{2}:\d{2}:\d{2}[.,]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[.,]\d{3}")
_SRT_INDEX_RE = re.compile(r"^\d+$")


class TranscriptParseError(Exception):
    """A transcript document was fetched but could not be read."""


def _parse_vtt_or_srt(text: str) -> str:
    """WebVTT and SRT share the same shape closely enough for one parser.

    Drop the ``WEBVTT`` header, cue index numbers, and timing lines; keep
    everything else.
    """
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line == "WEBVTT":
            continue
        if _VTT_TIMING_RE.match(line) or _SRT_INDEX_RE.match(line):
            continue
        lines.append(line)
    return "\n".join(lines)


def _parse_podcast_json_transcript(data: object) -> str:
    """Podcasting 2.0's JSON transcript shape.

    ``{"segments": [{"speaker": ..., "body": "..."}, ...]}``. Falls back to an
    empty string for anything unrecognised rather than raising -- a malformed
    transcript should not block the rest of the episode.
    """
    if not isinstance(data, dict):
        return ""
    segments = data.get("segments")
    if not isinstance(segments, list):
        return ""
    lines: list[str] = []
    for entry in segments:
        if not isinstance(entry, dict):
            continue
        body = str(entry.get("body", "")).strip()
        if not body:
            continue
        speaker = str(entry.get("speaker", "")).strip()
        lines.append(f"{speaker}: {body}" if speaker else body)
    return "\n".join(lines)


def parse_transcript(raw_bytes: bytes, transcript_type: str) -> str:
    """Already-fetched transcript bytes into plain text, by declared type.

    An unrecognised type is decoded as best-effort plain text rather than
    rejected: most real transcript files are readable as text whatever the
    declared type says, and the words are the point.
    """
    text = raw_bytes.decode("utf-8", errors="replace")
    mime = str(transcript_type or "").strip().lower()
    if mime == "application/json" or mime.endswith("+json"):
        try:
            data = json.loads(text)
        except ValueError as error:
            raise TranscriptParseError(
                f"That transcript file was not valid JSON: {error}"
            ) from error
        return _parse_podcast_json_transcript(data)
    if mime in ("text/vtt", "application/srt", "text/srt", "application/x-subrip"):
        return _parse_vtt_or_srt(text)
    return text.strip()
