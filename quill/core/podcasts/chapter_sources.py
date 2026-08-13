"""Where an episode's chapters come from, cheapest and best source first.

Most podcasts that are worth navigating already tell you where their sections
are -- in the feed, in the file's own tags, or as a list of timestamps in the
episode description. None of that costs anything to read, and all of it carries
titles a person actually wrote. So the rule is a cascade: try the free, exact
sources in order and stop at the first that works.

This module owns the two cheapest tiers that were not already implemented --
reading the timestamps out of show notes, and labelling which tier produced a
result -- plus the cascade that ties every tier together.

Tier order:

0. ``published``  -- the feed's own chapters document (``chapters.py``).
1. ``file``       -- ID3 chapter frames in the downloaded audio
   (``quill.core.speech.chapters.read_mp3_chapters``).
2. ``show_notes`` -- "00:12:34 Topic" lines parsed from the description.
3. ``transcript`` / 4. ``audio`` / 5. ``suggested`` -- the expensive tiers, which
   are not part of this module; :func:`chapter_cascade` simply reports that
   nothing free was found so the caller can offer them.

Pure and wx-free: every tier here is string or tag parsing, no network, no model.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from quill.core.podcasts.chapters import PodcastChapter

if TYPE_CHECKING:
    from quill.core.podcasts.models import PodcastEpisode, PodcastShow

#: How each source is described to the listener. A chapter list must never be
#: mistaken for the publisher's own when it was inferred.
SOURCE_LABELS: dict[str, str] = {
    "published": "Published chapters",
    "file": "Chapters in the file",
    "show_notes": "From the show notes",
    "transcript": "From the transcript",
    "audio": "Detected from the audio",
    "suggested": "Suggested",
}

#: Sources whose titles were written by a person, so they are used as-is.
AUTHORED_SOURCES: frozenset[str] = frozenset({"published", "file", "show_notes"})

#: Episodes shorter than this are not worth sectioning.
MIN_EPISODE_MS = 10 * 60 * 1000

#: Two chapters closer together than this are almost certainly a mis-parse.
MIN_CHAPTER_MS = 30 * 1000

#: A sane ceiling. A "chapter list" longer than this is noise, not navigation.
MAX_CHAPTERS = 200

#: ``12:34`` / ``1:02:03`` / ``[00:04:11]`` / ``(4:11)`` at the start of a line,
#: or after a bullet, dash, or index number -- the shapes show notes actually
#: use. The title is whatever follows, minus any separator.
_TIMESTAMP_LINE = re.compile(
    r"""
    ^[\s\-\*•–—]*        # bullets and dashes
    (?:\d{1,2}[\.\)]\s*)?               # an optional "1." / "2)" index
    [\[\(]?                             # an optional bracket
    (?P<h>\d{1,2}:)?(?P<m>\d{1,2}):(?P<s>\d{2})
    [\]\)]?
    (?P<sep>\s*[-–—:\|]?\s+|\s+)
    (?P<title>\S.*?)\s*$
    """,
    re.VERBOSE,
)


@dataclass(slots=True)
class ChapterSet:
    """Chapters plus an honest account of where they came from."""

    chapters: list[PodcastChapter] = field(default_factory=list)
    #: One of :data:`SOURCE_LABELS`, or "" when nothing was found.
    source: str = ""

    @property
    def label(self) -> str:
        return SOURCE_LABELS.get(self.source, "")

    @property
    def authored(self) -> bool:
        """Whether a person wrote these titles (as opposed to inferred ones)."""
        return self.source in AUTHORED_SOURCES

    def __bool__(self) -> bool:
        return bool(self.chapters)


def parse_timestamp_ms(hours: str, minutes: str, seconds: str) -> int:
    """Milliseconds from the three captured groups (``hours`` may be empty)."""
    h = int(hours.rstrip(":")) if hours else 0
    return ((h * 60 + int(minutes)) * 60 + int(seconds)) * 1000


def parse_show_notes_chapters(notes: str, *, total_ms: int = 0) -> list[PodcastChapter]:
    """Chapters from the timestamp lines in an episode description.

    Accepts the shapes show notes really use -- ``12:34 Topic``,
    ``- 1:02:03 - Topic``, ``[00:04:11] Topic``, ``3) 4:11 | Topic`` -- and
    ignores everything else, including a stray duration mentioned mid-sentence
    (a timestamp only counts when its line *starts* with it).

    Returns [] rather than a bad guess when the result does not look like a
    chapter list: fewer than two marks, marks out of order, marks past the end
    of the episode, or implausibly many.
    """
    if not notes.strip():
        return []
    marks: list[tuple[int, str]] = []
    for raw_line in notes.replace("\r", "\n").split("\n"):
        match = _TIMESTAMP_LINE.match(raw_line.strip())
        if match is None:
            continue
        title = match.group("title").strip(" -–—:|\t")
        if not title:
            continue
        marks.append((
            parse_timestamp_ms(match.group("h") or "", match.group("m"), match.group("s")),
            title,
        ))

    if len(marks) < 2 or len(marks) > MAX_CHAPTERS:
        return []
    # A real chapter list is in order and starts at or near the beginning.
    if any(b[0] <= a[0] for a, b in zip(marks, marks[1:], strict=False)):
        return []
    if marks[0][0] > 15 * 60 * 1000:
        return []
    if total_ms and marks[-1][0] >= total_ms:
        return []
    if any(b[0] - a[0] < MIN_CHAPTER_MS for a, b in zip(marks, marks[1:], strict=False)):
        return []
    return [PodcastChapter(start_ms=start, title=title) for start, title in marks]


def show_identity(show: PodcastShow | None) -> str:
    """A show's stable id, whichever name the caller reached for.

    ``PodcastShow`` calls the field ``id``; a download-queue item calls the
    same value ``show_id``, and code that crossed between the two quietly got
    an empty string -- which is how Find Chapters came to answer "this episode
    cannot be identified" for every episode. One helper, so the two spellings
    cannot disagree again.
    """
    if show is None:
        return ""
    return str(getattr(show, "id", "") or getattr(show, "show_id", "") or "")


def read_file_chapters(path: Path) -> list[PodcastChapter]:
    """Chapters embedded in a downloaded episode's own tags, or []."""
    try:
        from quill.core.speech.chapters import read_mp3_chapters
    except Exception:  # noqa: BLE001 - mutagen missing is not an error here
        return []
    try:
        return [
            PodcastChapter(start_ms=c.start_ms, title=c.title)
            for c in read_mp3_chapters(path)
            if c.title
        ]
    except Exception:  # noqa: BLE001 - an unreadable tag is simply "no chapters"
        return []


def chapter_cascade(
    *,
    published: Callable[[], list[PodcastChapter]] | None = None,
    audio_path: Path | None = None,
    show_notes: str = "",
    total_ms: int = 0,
) -> ChapterSet:
    """The first free source that yields chapters, with its label.

    ``published`` is a callable because reading the feed's chapters document is
    the one tier that may touch the network; it is only called when the caller
    supplies it, and its failures are treated as "no chapters".

    An empty result is not a failure -- it means no *free* source had an answer,
    and the caller may offer the expensive tiers (transcript segmentation, an
    audio scan, or model-suggested titles).
    """
    if total_ms and total_ms < MIN_EPISODE_MS:
        return ChapterSet()

    if published is not None:
        try:
            chapters = [c for c in published() if c.title]
        except Exception:  # noqa: BLE001
            chapters = []
        if len(chapters) >= 2:
            return ChapterSet(_clamp(chapters, total_ms), "published")

    if audio_path is not None and audio_path.exists():
        chapters = read_file_chapters(audio_path)
        if len(chapters) >= 2:
            return ChapterSet(_clamp(chapters, total_ms), "file")

    chapters = parse_show_notes_chapters(show_notes, total_ms=total_ms)
    if chapters:
        return ChapterSet(_clamp(chapters, total_ms), "show_notes")

    return ChapterSet()


def episode_has_possible_chapters(episode: PodcastEpisode) -> bool:
    """Whether it is worth offering Chapters for this episode at all.

    Cheap enough to call while building a list: it only asks whether *any* free
    source could exist, never parses anything.
    """
    return bool(
        str(getattr(episode, "chapters_url", ""))
        or str(getattr(episode, "description", ""))
        or str(getattr(episode, "downloaded_path", ""))
    )


def build_episode_chapters(
    episode: PodcastEpisode, show: PodcastShow | None = None, *, safe_mode: bool = False
) -> ChapterSet:
    """Run the free cascade for one episode. Never raises.

    Call this off the UI thread: the published tier may perform one network
    fetch (and refuses outright in Safe Mode, which is treated here as simply
    having no published chapters rather than as an error).
    """
    from quill.core.podcasts import chapters as chapters_module
    from quill.core.podcasts import feed_auth

    chapters_url = str(getattr(episode, "chapters_url", ""))

    def _published() -> list[PodcastChapter]:
        if not chapters_url or safe_mode:
            return []
        auth_header = ""
        if show is not None:
            try:
                auth_header = feed_auth.auth_header_for_url(show, chapters_url)
            except Exception:  # noqa: BLE001
                auth_header = ""
        return chapters_module.fetch_and_parse_chapters(
            chapters_url, safe_mode=safe_mode, auth_header=auth_header
        )

    # Downloaded file, or the playback cache entry a streamed episode fills as
    # it plays -- both are bytes, and the file tiers cannot tell them apart.
    from quill.core.podcasts.playback_cache import local_audio_path

    audio_path = local_audio_path(show, episode)
    duration_seconds = int(getattr(episode, "duration_seconds", 0) or 0)
    found = chapter_cascade(
        published=_published,
        audio_path=audio_path,
        show_notes=str(getattr(episode, "description", "")),
        total_ms=duration_seconds * 1000,
    )
    if found.chapters:
        return found

    # Nothing free and authored had an answer. If the listener has previously
    # asked for the expensive tiers on this episode, use that cached result --
    # reading a sidecar costs nothing. Computing one is never automatic: tier 4
    # scans the whole file with ffmpeg, and neither tier writes titles a person
    # wrote, so both stay an explicit request (see chapter_inference).
    from quill.core.podcasts.chapter_inference import load_cached_inference

    cached, source = load_cached_inference(
        show_identity(show),
        str(getattr(episode, "guid", "")),
        audio_path=audio_path,
    )
    if len(cached) >= 2 and source in SOURCE_LABELS:
        return ChapterSet(_clamp(cached, duration_seconds * 1000), source)
    return found


def _clamp(chapters: list[PodcastChapter], total_ms: int) -> list[PodcastChapter]:
    """Sorted, de-duplicated, and inside the episode."""
    seen: set[int] = set()
    result: list[PodcastChapter] = []
    for chapter in sorted(chapters, key=lambda c: c.start_ms):
        if chapter.start_ms < 0 or chapter.start_ms in seen:
            continue
        if total_ms and chapter.start_ms >= total_ms:
            continue
        seen.add(chapter.start_ms)
        result.append(chapter)
    return result[:MAX_CHAPTERS]
