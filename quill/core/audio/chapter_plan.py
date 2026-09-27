"""Chapters through every conversion: where they come from, and where they land.

Chapter marks are how somebody who cannot glance at a waveform finds their way
around a long recording, so the Converter treats them as content, not as
metadata that may or may not survive. Two questions, answered here:

**Where do this file's chapters come from?** (:class:`ChapterSource`)

* ``keep`` -- the file's own chapters (ID3 CHAP in an MP3, atoms in an M4B,
  Matroska chapters...), carried across as they are.
* ``list`` -- a chapter list you wrote, sitting beside the file with the same
  name: ``book.cue``, ``book.chapters.txt``, ``book.chapters.json``
  (Podcasting 2.0), Audacity labels, or plain ``0:00 Title`` lines typed in
  any text editor. This is how you define chapters yourself for *any* format.
* ``pauses`` -- found at the recording's silences.
* ``every-N`` -- one every N minutes, for a lecture or a ten-hour recording.
* ``none`` -- removed.

**Where do they land?** (:func:`chapter_home`) FFmpeg writes chapters natively
into MP3 (ID3 CHAP and CTOC), the MP4 family, Matroska and WebM, Opus and WMA.
Ogg Vorbis, FLAC and Speex get ``CHAPTERnnn`` comments written with mutagen,
the convention their players read. Everything else -- WAV, AIFF, WavPack,
AC-3 and the rest -- has no place for chapters inside the file, so a
``.cue`` sheet is written beside it instead, and nothing is silently lost.

Pure except for :func:`resolve_chapters` (which may probe or scan) and
:func:`write_vorbis_chapters` / :func:`write_cue_beside` (which write files).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from quill.core.speech.audio_tags_core import Chapter

#: Chapter sources, in the order the main window offers them.
KEEP = "keep"
LIST = "list"
PAUSES = "pauses"
NONE = "none"
EVERY_MINUTES: tuple[int, ...] = (5, 10, 15, 30, 60)


def every(minutes: int) -> str:
    return f"every-{int(minutes)}"


CHAPTER_SOURCES: tuple[tuple[str, str], ...] = (
    (KEEP, "Keep each file's own chapters"),
    (
        LIST,
        "Use the chapter list beside each file "
        "(.cue, .chapters.txt, Audacity labels, .chapters.json)",
    ),
    (PAUSES, "Find chapters at the pauses"),
    *((every(m), f"A chapter every {m} minutes") for m in EVERY_MINUTES),
    (NONE, "Remove all chapters"),
)

#: Formats FFmpeg writes chapters into itself (checked end to end).
NATIVE_FORMATS: frozenset[str] = frozenset({
    "mp3",
    "m4a",
    "m4b",
    "alac",
    "m4r",
    "opus",
    "mka",
    "weba",
    "wma",
    "mp4",
    "mp4_hevc",
    "mov",
    "mkv",
    "webm",
    "wmv",
})

#: Formats whose players read ``CHAPTERnnn`` comments, which FFmpeg does not write.
VORBIS_COMMENT_FORMATS: frozenset[str] = frozenset({"ogg", "flac", "spx", "ogv"})


def chapter_home(fmt: str) -> str:
    """``"native"``, ``"comments"`` or ``"cue"``: where *fmt* keeps chapters."""
    key = fmt.strip().lower()
    if key in NATIVE_FORMATS:
        return "native"
    if key in VORBIS_COMMENT_FORMATS:
        return "comments"
    return "cue"


# --------------------------------------------------------------------------- #
# Chapter lists you write yourself
# --------------------------------------------------------------------------- #


def sidecar_candidates(source: Path) -> list[Path]:
    """Where a chapter list for *source* may sit, most specific first."""
    stem = source.with_suffix("")
    return [
        Path(f"{stem}.chapters.txt"),
        Path(f"{stem}.chapters.json"),
        source.with_suffix(".cue"),
        Path(f"{stem}.labels.txt"),
        source.with_suffix(".txt"),
    ]


def find_chapter_list(source: Path, total_ms: int) -> tuple[Path, list[Chapter]] | None:
    """The first sidecar beside *source* that parses into two or more chapters."""
    from quill.core.speech.chapter_io import ChapterParseError, parse_chapter_text

    for candidate in sidecar_candidates(source):
        if not candidate.is_file() or candidate == source:
            continue
        try:
            text = candidate.read_text(encoding="utf-8-sig", errors="replace")
            chapters = parse_chapter_text(text, total_ms)
        except (OSError, ChapterParseError):
            continue
        if len(chapters) >= 2:
            return candidate, chapters
    return None


# --------------------------------------------------------------------------- #
# Making and reshaping chapter lists
# --------------------------------------------------------------------------- #


def every_n_minutes(total_ms: int, minutes: int) -> list[Chapter]:
    """Evenly spaced chapters; a last piece under a minute joins the one before."""
    step = max(1, int(minutes)) * 60_000
    starts = list(range(0, max(0, total_ms), step))
    if len(starts) > 1 and total_ms - starts[-1] < 60_000:
        starts.pop()
    starts = starts or [0]
    bounds = [*starts, total_ms]
    return [
        Chapter(index=i, title=f"Part {i + 1}", start_ms=bounds[i], end_ms=bounds[i + 1])
        for i in range(len(starts))
    ]


def clip_chapters(chapters: Sequence[Chapter], start_ms: int, end_ms: int) -> list[Chapter]:
    """The chapters inside ``[start_ms, end_ms)``, shifted to begin at zero.

    For "keep only part of each file": a chapter cut by the window keeps its
    title and is trimmed; one entirely outside it is dropped. ``end_ms`` of 0
    means the end of the file.
    """
    out: list[Chapter] = []
    for chapter in chapters:
        lo = max(chapter.start_ms, start_ms)
        hi = chapter.end_ms if not end_ms else min(chapter.end_ms, end_ms)
        if hi - lo < 500:  # nothing, or a sliver, left inside the window
            continue
        out.append(replace(chapter, index=len(out), start_ms=lo - start_ms, end_ms=hi - start_ms))
    return out


def resolve_chapters(
    source: Path,
    how: str,
    *,
    total_ms: int = 0,
    own: Sequence[Chapter] | None = None,
) -> tuple[list[Chapter] | None, str]:
    """This file's chapters for *how*, and a note for the report.

    Returns ``(None, "")`` for ``keep`` when the file's own chapters should
    simply be carried (``own`` is then only used by the non-native homes), an
    empty list for ``none``, else the computed list. Never raises: a scan that
    fails, or a missing list, falls back to the file's own chapters and says so.
    """
    if how == NONE:
        return [], ""
    if how == KEEP:
        return (list(own) if own else None), ""
    if total_ms <= 0:
        from quill.core.speech.ffmpeg import probe_duration_ms

        total_ms = probe_duration_ms(source)
    if total_ms <= 0:
        return None, "Its length could not be read, so its own chapters were kept."
    if how == LIST:
        found = find_chapter_list(source, total_ms)
        if found is None:
            return (
                list(own) if own else None
            ), "No chapter list beside it; its own chapters were kept."
        return found[1], f"Chapters from {found[0].name}."
    if how == PAUSES:
        try:
            from quill.core.speech.silence import detect_silence_chapters

            # Two seconds of quiet, not a sentence break: chapter pauses are
            # long, and a chapter shorter than twenty seconds is a mistake.
            found_at_pauses = detect_silence_chapters(
                source, min_silence_s=2.0, min_chapter_ms=20_000
            )
        except Exception as error:  # noqa: BLE001 - a failed scan keeps the file usable
            return (list(own) if own else None), f"Could not scan for pauses ({error})."
        return found_at_pauses, f"{len(found_at_pauses)} chapters found at pauses."
    if how.startswith("every-"):
        try:
            minutes = int(how.split("-", 1)[1])
        except ValueError:
            minutes = 10
        return every_n_minutes(total_ms, minutes), ""
    return None, ""


# --------------------------------------------------------------------------- #
# Writing chapters where FFmpeg does not
# --------------------------------------------------------------------------- #


def _stamp(ms: int) -> str:
    hours, rest = divmod(max(0, int(ms)), 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    seconds, millis = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def vorbis_chapter_comments(chapters: Sequence[Chapter]) -> dict[str, str]:
    """``CHAPTER001=00:00:00.000`` / ``CHAPTER001NAME=Title`` pairs (pure)."""
    comments: dict[str, str] = {}
    for number, chapter in enumerate(chapters, start=1):
        comments[f"CHAPTER{number:03d}"] = _stamp(chapter.start_ms)
        comments[f"CHAPTER{number:03d}NAME"] = chapter.title
    return comments


def write_vorbis_chapters(path: Path, chapters: Sequence[Chapter]) -> bool:
    """Write chapter comments into an Ogg, Opus, Speex or FLAC file."""
    import mutagen

    audio = mutagen.File(str(path))
    if audio is None:
        return False
    if audio.tags is None:
        audio.add_tags()
    tags = audio.tags
    for key in [k for k in tags.keys() if k.upper().startswith("CHAPTER")]:
        del tags[key]
    for key, value in vorbis_chapter_comments(chapters).items():
        tags[key] = [value]
    audio.save()
    return True


def write_cue_beside(path: Path, chapters: Sequence[Chapter]) -> Path:
    """A ``.cue`` sheet beside *path* that names it and lists its chapters."""
    from quill.core.speech.chapter_io import chapters_to_cue

    cue = path.with_suffix(".cue")
    kind = {".aiff": "AIFF", ".aif": "AIFF", ".mp3": "MP3"}.get(path.suffix.lower(), "WAVE")
    text = chapters_to_cue(list(chapters), path.name).replace(
        f'FILE "{path.name}" MP3', f'FILE "{path.name}" {kind}'
    )
    cue.write_text(text, encoding="utf-8")
    return cue


def place_chapters(path: Path, fmt: str, chapters: Sequence[Chapter]) -> str:
    """Put *chapters* into or beside a finished *path*; a note for the report.

    Native formats already have them (FFmpeg wrote them), so nothing is done.
    Best effort by contract: a failure is a note, never an exception.
    """
    if len(chapters) < 2:
        return ""
    home = chapter_home(fmt)
    try:
        if home == "comments" and write_vorbis_chapters(path, chapters):
            return f"{len(chapters)} chapters written."
        if home == "cue":
            cue = write_cue_beside(path, chapters)
            count = len(chapters)
            return f"{fmt.upper()} has no chapters of its own; {count} chapters are in {cue.name}."
    except Exception as error:  # noqa: BLE001 - chapters are extra, never a failure
        return f"Chapters could not be written ({error})."
    return f"{len(chapters)} chapters."
