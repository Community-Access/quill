"""Chapters inferred from an episode when no free, authored source has any.

:mod:`chapter_sources` owns the cheap tiers -- the feed's chapters document, ID3
frames, timestamps in the show notes -- and every one of those carries titles a
person wrote. This module owns the two tiers below them, for the episodes where
all of that came up empty:

* **Tier 3, transcript.** If a transcript was cached, sections can be found in
  the words themselves. :func:`segment_transcript` is a lexical-cohesion pass
  (the TextTiling shape): score how much vocabulary adjacent windows share, and
  cut where that score bottoms out, because a topic change is exactly where the
  words stop overlapping. Pure Python, no model, no network, deterministic, and
  fast enough to be imperceptible on an hour-long episode.
* **Tier 4, audio.** :mod:`quill.core.speech.silence` already scans for silences
  and turns them into chapters; what it lacked was podcast-shaped parameters.
  Its five-second default is right for an audiobook and would cut a chatty
  podcast into hundreds of fragments, so :data:`PODCAST_SILENCE` supplies the
  ninety-second floor and longer minimum silence that suit spoken programmes.

Both tiers are **explicit**, never automatic: they cost real time (tier 4 shells
out to ffmpeg over the whole file), and they produce titles nobody wrote, so the
listener asks for them and the result is always labelled with its source.

Two rules the whole module obeys:

* **An inferred chapter list never overwrites a published one.** Callers hold
  that invariant, and :func:`infer_chapters` refuses to run at all on an episode
  whose free tiers already answered.
* **Titles are honest about being inferred.** A section is named from its own
  opening words, so it reads as "what this part is about" rather than passing
  itself off as an authored chapter title.

wx-free, strict-typed. The segmentation and the parsing are pure; only the
sidecar cache touches disk.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from quill.core.podcasts.chapters import PodcastChapter

__all__ = [
    "TimedCue",
    "PODCAST_SILENCE",
    "Segmentation",
    "parse_timed_cues",
    "segment_transcript",
    "segment_with_evidence",
    "silence_chapters_for_podcast",
    "load_cached_inference",
    "save_cached_inference",
    "clear_cached_inference",
]

# -- tier 4 parameters ---------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SilenceParams:
    """ffmpeg silencedetect settings shaped for spoken programmes."""

    #: Below this level counts as silence. Podcast beds and room tone sit well
    #: above an audiobook's near-digital-silence, so -35 dB rather than -50.
    noise_db: float = -35.0
    #: A pause must last this long to be a candidate boundary. Sentence gaps in
    #: speech are a few hundred ms; a real section break is a beat longer.
    min_silence_s: float = 1.6
    #: No section shorter than this. The five-second default that suits an
    #: audiobook's tracks would slice an hour of conversation into hundreds of
    #: fragments, which is worse than no chapters at all.
    min_chapter_ms: int = 90 * 1000


#: The podcast-tuned parameter set (x.md: "ninety seconds and a longer minimum
#: silence are the right order").
PODCAST_SILENCE = SilenceParams()


# -- tier 3: timed transcript cues ---------------------------------------------

_VTT_TIMING = re.compile(r"^(?P<h1>\d{1,2}):(?P<m1>\d{2}):(?P<s1>\d{2})[.,](?P<ms1>\d{1,3})\s*-->")
_SRT_INDEX = re.compile(r"^\d+$")


@dataclass(frozen=True, slots=True)
class TimedCue:
    """One transcript line with the position it is spoken at."""

    start_ms: int
    text: str


def _cue_start_ms(match: re.Match[str]) -> int:
    return (
        int(match.group("h1")) * 3_600_000
        + int(match.group("m1")) * 60_000
        + int(match.group("s1")) * 1000
        + int(match.group("ms1").ljust(3, "0"))
    )


def parse_timed_cues(text: str, transcript_type: str = "") -> list[TimedCue]:
    """Transcript text -> cues that keep their timings.

    :func:`quill.core.podcasts.transcripts.parse_transcript` deliberately throws
    the timings away -- it exists to make a transcript *searchable*, and timing
    lines are noise for that. Chapters need the opposite, so this is a second,
    narrower parser rather than a change to the first: a cue without a position
    is useless here, and a word without a position is useless there.

    Handles WebVTT, SRT, and Podcasting 2.0 JSON (whose segments carry
    ``startTime`` in seconds). Anything unrecognised yields no cues, which the
    caller reads as "this tier has no answer" rather than as an error.
    """
    stripped = text.strip()
    if not stripped:
        return []

    if stripped.startswith("{") or "json" in transcript_type.lower():
        json_cues = _parse_json_cues(stripped)
        if json_cues:
            return json_cues

    cues: list[TimedCue] = []
    pending_ms: int | None = None
    pending: list[str] = []
    for raw_line in stripped.splitlines():
        line = raw_line.strip()
        if not line or line == "WEBVTT" or _SRT_INDEX.match(line):
            continue
        timing = _VTT_TIMING.match(line)
        if timing is not None:
            if pending_ms is not None and pending:
                cues.append(TimedCue(pending_ms, " ".join(pending)))
            pending_ms = _cue_start_ms(timing)
            pending = []
            continue
        if pending_ms is not None:
            pending.append(line)
    if pending_ms is not None and pending:
        cues.append(TimedCue(pending_ms, " ".join(pending)))
    return cues


def _parse_json_cues(raw: str) -> list[TimedCue]:
    try:
        data = json.loads(raw)
    except ValueError:
        return []
    segments = data.get("segments") if isinstance(data, dict) else None
    if not isinstance(segments, list):
        return []
    cues: list[TimedCue] = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        start = segment.get("startTime", segment.get("start"))
        body = str(segment.get("body", segment.get("text", ""))).strip()
        if body and isinstance(start, (int, float)) and start >= 0:
            cues.append(TimedCue(int(round(float(start) * 1000)), body))
    return cues


# -- tier 3: lexical-cohesion segmentation -------------------------------------

#: Words too common to say anything about what a section is *about*. Kept short
#: and English-only on purpose: this is a similarity heuristic, not linguistics,
#: and an over-long list starts discarding real topic words.
_STOPWORDS: frozenset[str] = frozenset(
    """a an and are as at be been but by can could did do does for from had has
    have he her his how i if in is it its just like me my no not of on or our out
    so such than that the their them then there these they this to too up us was
    we were what when where which who will with would you your yeah okay right
    know think really going get got one two now well said says say im ive dont
    thats its were theyre""".split()
)

_WORD = re.compile(r"[a-z0-9']+")

#: Cohesion this flat, relative to its own average, is an episode with no
#: sections in it rather than an episode whose sections are subtle.
_FLAT_COHESION = 0.02

#: How much speech is compared either side of a candidate boundary.
#:
#: Two and a half minutes, and the number is measured rather than chosen. Against
#: hand-built reference chapter lists for four Main Menu episodes, the previous
#: 45 seconds scored an F1 of 0.165 where cutting the episode into **equal
#: slices with no knowledge of it at all** scored 0.151 -- so it was, within
#: noise, no better than dividing by n. At 150 seconds the same code scores
#: 0.311 and proposes 14 sections instead of 35 where the truth is 7.
#:
#: The reason is what 45 seconds *is*. It is about the length of one caller's
#: question. When somebody rings a talk programme and asks about braille
#: displays, the vocabulary either side of them changes completely and then
#: changes back, and a narrow window reads that blip as a chapter. A chapter is a
#: section of a programme, and sections are minutes long -- so the window has to
#: be long enough to ask "did the subject change *and stay changed*".
DEFAULT_WINDOW_SECONDS = 150.0

#: No section shorter than three minutes. Measured alongside the window above:
#: at a 90-second floor the same settings return nearly twice as many sections,
#: and the extra ones are wrong. A chapter list somebody arrows through with a
#: screen reader is worth having only if nearly every row in it is real.
DEFAULT_MIN_CHAPTER_MS = 180_000

#: The fewest cues a comparison window may hold on each side, whatever the
#: window's duration works out to. A duration is the right *unit* -- see
#: :func:`_windowed_cohesion` -- but it cannot conjure resolution a transcript
#: does not have: a voice-activity detector emits cues of twenty-odd seconds, so
#: forty-five seconds of them is barely two, and two bags of words is not enough
#: to say anything about vocabulary. Where the transcript is coarser than the
#: window, the window widens to fit rather than the tier returning nothing.
_MIN_WINDOW_CUES = 4


def _content_words(text: str) -> list[str]:
    return [w for w in _WORD.findall(text.lower()) if len(w) > 2 and w not in _STOPWORDS]


def _cosine(left: dict[str, int], right: dict[str, int]) -> float:
    """Cosine similarity of two word-count bags (0.0 when either is empty)."""
    if not left or not right:
        return 0.0
    shared = set(left) & set(right)
    if not shared:
        return 0.0
    dot = sum(left[w] * right[w] for w in shared)
    left_norm = math.sqrt(sum(v * v for v in left.values()))
    right_norm = math.sqrt(sum(v * v for v in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def _title_from(text: str, *, max_chars: int = 60) -> str:
    """A section's opening words, as its name.

    Deliberately the literal opening rather than anything cleverer: it is
    obviously a quotation from the episode, so it cannot be mistaken for a title
    the publisher wrote.
    """
    flat = " ".join(text.split())
    if len(flat) <= max_chars:
        return flat
    cut = flat[:max_chars].rsplit(" ", 1)[0]
    return f"{cut}..." if cut else flat[:max_chars]


@dataclass(frozen=True, slots=True)
class Segmentation:
    """Boundaries, plus the evidence the segmenter has about its own quality."""

    chapters: list[PodcastChapter]
    #: How far below its own threshold the accepted boundaries sat, 0.0-0.5.
    #: :func:`quill.core.podcasts.chapter_scoring.score` has always asked for
    #: this and nothing used to compute it, so its ``confidence *= 1.0 + margin``
    #: term multiplied by one and every inferred answer scored the same whether
    #: its boundaries were obvious or marginal.
    cohesion_margin: float = 0.0


def _typical_cue_ms(rows: list[TimedCue]) -> int:
    """The median gap between cues -- how much speech one cue is worth.

    Median rather than mean: one long pause between two cues would otherwise
    make a fine-grained transcript look coarse and widen every window.
    """
    if len(rows) < 2:
        return 0
    gaps = sorted(
        b.start_ms - a.start_ms
        for a, b in zip(rows, rows[1:], strict=False)
        if b.start_ms > a.start_ms
    )
    return gaps[len(gaps) // 2] if gaps else 0


def _windowed_cohesion(
    rows: list[TimedCue], bags: list[dict[str, int]], window_ms: int
) -> list[tuple[int, float]]:
    """Cohesion at every gap, comparing a fixed *duration* either side.

    **The window is seconds of speech, not a count of cues**, and that is the
    whole point of this function. Cue length is a property of whoever produced
    the transcript, not of the episode: eight cues is about thirty seconds of a
    Whisper transcript, two minutes of a Vosk one, three minutes of a
    speech-recogniser fed through a voice-activity detector, and **three
    seconds** of a publisher's word-level transcript. The old count-based window
    therefore compared wildly different amounts of speech depending on the file
    it was handed, and answered a question about the *episode* using a fact about
    the *file*. A word-level transcript -- the best input this tier can ever
    receive -- was the input it handled worst.

    Two pointers rather than a slice per gap, so a word-level transcript with
    tens of thousands of cues costs the same per cue as a coarse one.
    """
    window_ms = max(window_ms, _MIN_WINDOW_CUES * _typical_cue_ms(rows))
    left: dict[str, int] = {}
    right: dict[str, int] = {}

    def _add(target: dict[str, int], bag: dict[str, int]) -> None:
        for word, count in bag.items():
            target[word] = target.get(word, 0) + count

    def _remove(target: dict[str, int], bag: dict[str, int]) -> None:
        for word, count in bag.items():
            remaining = target.get(word, 0) - count
            if remaining > 0:
                target[word] = remaining
            else:
                target.pop(word, None)

    low = 0  # first cue still inside the left window
    high = 0  # first cue beyond the right window
    scores: list[tuple[int, float]] = []
    for index in range(len(rows)):
        if index:
            _add(left, bags[index - 1])
            _remove(right, bags[index - 1])
        boundary_ms = rows[index].start_ms
        while low < index and rows[low].start_ms < boundary_ms - window_ms:
            _remove(left, bags[low])
            low += 1
        while high < len(rows) and rows[high].start_ms <= boundary_ms + window_ms:
            if high >= index:
                _add(right, bags[high])
            high += 1
        # A window that never filled is a window at the edge of the episode, and
        # an edge is not a topic change.
        if index - low < 2 or high - index < 2:
            continue
        scores.append((index, _cosine(left, right)))
    return scores


def segment_with_evidence(
    cues: Iterable[TimedCue],
    *,
    total_ms: int = 0,
    min_chapter_ms: int = DEFAULT_MIN_CHAPTER_MS,
    window_seconds: float = DEFAULT_WINDOW_SECONDS,
    max_chapters: int = 60,
) -> Segmentation:
    """Cut a timed transcript into sections where the vocabulary changes.

    The TextTiling shape: slide a pair of adjacent windows over the transcript,
    score how much vocabulary they share, and cut at the *local minima* of that
    score -- the points where the conversation stopped using the words it had
    been using. Boundaries are then thinned so no section is shorter than
    ``min_chapter_ms``.

    Deterministic and offline. Returns no chapters when the transcript is too
    short, or too uniform, to say anything useful -- which the caller reads as
    "no answer" rather than forcing a meaningless partition.
    """
    rows = [c for c in cues if c.text.strip()]
    if len(rows) < 6:
        return Segmentation([])

    bags = [dict(_counts(_content_words(c.text))) for c in rows]
    scores = _windowed_cohesion(rows, bags, int(window_seconds * 1000))
    if len(scores) < 3:
        return Segmentation([])

    # A gap is a candidate when it is a local minimum and meaningfully below the
    # average cohesion -- an episode that never changes subject should produce
    # no chapters rather than arbitrary ones.
    mean = sum(value for _, value in scores) / len(scores)
    spread = math.sqrt(sum((value - mean) ** 2 for _, value in scores) / len(scores))

    # Flat cohesion means there is nothing to find, and the threshold below
    # cannot say so: with no spread it collapses onto the mean, every gap sits
    # at exactly the threshold, and "meaningfully below average" silently
    # becomes "every local wobble". A programme that keeps to one subject for an
    # hour then gets a full set of invented boundaries -- confidently wrong,
    # which is the one output this tier must never produce.
    if spread < _FLAT_COHESION * max(mean, _FLAT_COHESION):
        return Segmentation([])

    threshold = mean - spread / 2.0

    candidates: list[tuple[int, float]] = []
    for position, (index, value) in enumerate(scores):
        if value > threshold:
            continue
        before = scores[position - 1][1] if position else math.inf
        after = scores[position + 1][1] if position + 1 < len(scores) else math.inf
        if value <= before and value <= after:
            candidates.append((index, threshold - value))

    # Always open at zero, then keep only boundaries far enough apart.
    starts = [0]
    depths: list[float] = []
    for index, depth in candidates:
        start_ms = rows[index].start_ms
        if start_ms - starts[-1] >= min_chapter_ms:
            starts.append(start_ms)
            depths.append(depth)
        if len(starts) >= max_chapters:
            break
    if total_ms and total_ms - starts[-1] < min_chapter_ms and len(starts) > 1:
        starts.pop()
        if depths:
            depths.pop()
    if len(starts) < 2:
        return Segmentation([])

    chapters: list[PodcastChapter] = []
    for position, start_ms in enumerate(starts):
        end_ms = starts[position + 1] if position + 1 < len(starts) else (total_ms or None)
        body = " ".join(
            c.text
            for c in rows
            if c.start_ms >= start_ms and (end_ms is None or c.start_ms < end_ms)
        )
        chapters.append(PodcastChapter(start_ms=start_ms, title=_title_from(body)))
    margin = sum(depths) / len(depths) if depths else 0.0
    return Segmentation(chapters, round(min(0.5, max(0.0, margin)), 4))


def segment_transcript(
    cues: Iterable[TimedCue],
    *,
    total_ms: int = 0,
    min_chapter_ms: int = DEFAULT_MIN_CHAPTER_MS,
    window_seconds: float = DEFAULT_WINDOW_SECONDS,
    max_chapters: int = 60,
) -> list[PodcastChapter]:
    """:func:`segment_with_evidence`, for callers that only want the chapters."""
    return segment_with_evidence(
        cues,
        total_ms=total_ms,
        min_chapter_ms=min_chapter_ms,
        window_seconds=window_seconds,
        max_chapters=max_chapters,
    ).chapters


def _counts(words: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for word in words:
        counts[word] = counts.get(word, 0) + 1
    return counts


# -- tier 4: silence, with podcast parameters ----------------------------------


def silence_chapters_for_podcast(
    silences: list[tuple[float, float]],
    total_ms: int,
    *,
    params: SilenceParams = PODCAST_SILENCE,
) -> list[PodcastChapter]:
    """Silence pairs -> podcast-shaped chapters.

    Thin wrapper over
    :func:`quill.core.speech.silence.propose_chapters_from_silences` that
    supplies the podcast floor and converts to :class:`PodcastChapter`.
    Returns nothing when the scan found only one section: "the whole episode" is
    not a chapter list, and offering it as one wastes the listener's time.
    """
    from quill.core.speech.silence import propose_chapters_from_silences

    sections = propose_chapters_from_silences(
        silences,
        total_ms,
        min_chapter_ms=params.min_chapter_ms,
        title_prefix="Section",
    )
    if len(sections) < 2:
        return []
    return [
        PodcastChapter(start_ms=int(section.start_ms), title=str(section.title))
        for section in sections
    ]


# -- sidecar cache -------------------------------------------------------------
#
# Inference is expensive enough that it must be computed once. The key includes
# the audio file's size and mtime, so a re-downloaded or replaced episode
# recomputes instead of showing chapters for a file it no longer has.

_CACHE_DIRNAME = "podcast-chapter-inference"


def _cache_path(show_id: str, episode_guid: str) -> Path:
    import hashlib

    from quill.core.paths import app_data_dir

    digest = hashlib.sha256(f"{show_id}\n{episode_guid}".encode()).hexdigest()[:32]
    return app_data_dir() / _CACHE_DIRNAME / f"{digest}.json"


def _stamp(audio_path: Path | None) -> str:
    if audio_path is None:
        return ""
    try:
        stat = audio_path.stat()
    except OSError:
        return ""
    return f"{stat.st_size}:{int(stat.st_mtime)}"


def save_cached_inference(
    show_id: str,
    episode_guid: str,
    chapters: list[PodcastChapter],
    source: str,
    *,
    audio_path: Path | None = None,
) -> None:
    """Persist an inferred chapter list. Best effort: never raises."""
    try:
        path = _cache_path(show_id, episode_guid)
        path.parent.mkdir(parents=True, exist_ok=True)
        from quill.core.storage import write_json_atomic

        write_json_atomic(
            path,
            {
                "source": source,
                "stamp": _stamp(audio_path),
                "chapters": [{"start_ms": c.start_ms, "title": c.title} for c in chapters],
            },
        )
    except Exception:  # noqa: BLE001 - a cache that cannot be written is not an error
        return


def load_cached_inference(
    show_id: str, episode_guid: str, *, audio_path: Path | None = None
) -> tuple[list[PodcastChapter], str]:
    """The cached inference as ``(chapters, source)``, or ``([], "")``.

    A cache whose stamp no longer matches the audio file on disk is ignored, so
    replacing the file silently recomputes rather than showing chapters that
    belong to different audio.
    """
    try:
        raw = json.loads(_cache_path(show_id, episode_guid).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return [], ""
    if not isinstance(raw, dict):
        return [], ""
    expected = _stamp(audio_path)
    if expected and str(raw.get("stamp", "")) != expected:
        return [], ""
    entries = raw.get("chapters")
    chapters: list[PodcastChapter] = []
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            continue
        title = str(entry.get("title", "")).strip()
        start = entry.get("start_ms")
        if title and isinstance(start, int) and start >= 0:
            chapters.append(PodcastChapter(start_ms=start, title=title))
    chapters.sort(key=lambda c: c.start_ms)
    return chapters, str(raw.get("source", ""))


def clear_cached_inference(show_id: str, episode_guid: str) -> None:
    """Forget an episode's inferred chapters (best effort)."""
    try:
        _cache_path(show_id, episode_guid).unlink(missing_ok=True)
    except OSError:
        return
