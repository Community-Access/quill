"""Open, edit, and save an existing chaptered audiobook (MP3 or M4B/M4A).

The core of the Audio Studio's *edit an existing audiobook* journey (ported
from ChapterForge's ``read_master`` / in-place save, ``s:\\code99\\forum``,
MIT): read a finished book's tags + chapters + duration, and write an edited
plan back — **in place** for MP3 (mutagen rewrites only the tag frames; the
audio bytes are untouched) or as a **lossless re-mux** for M4B (``-c copy``
with a fresh FFMETADATA document, so no re-encode and no quality loss).

wx-free, strict-typed. Chapter math lives in :mod:`chapters`; the UI's
Chapter Workbench drives this module.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from quill.core.speech.chapters import Chapter
from quill.core.speech.ffmpeg import (
    INSTALL_HINT,
    AudioMetadata,
    TranscodeError,
    build_ffmetadata,
    find_ffmpeg,
    find_ffprobe,
)


class BookReadError(ValueError):
    """The file could not be read as a chaptered audiobook; message is speakable."""


@dataclass(slots=True)
class BookFile:
    """An opened audiobook: where it lives, its tags, chapters, and length."""

    path: Path
    tags: AudioMetadata
    chapters: list[Chapter]
    total_ms: int

    @property
    def kind(self) -> str:
        """ "mp3" or "m4b" (M4A files count as m4b — same container)."""
        return "mp3" if self.path.suffix.lower() == ".mp3" else "m4b"


def read_book(path: Path) -> BookFile:
    """Read tags + chapters + duration from an existing chaptered file.

    Supports MP3 (ID3v2 CHAP/CTOC via mutagen) and M4B/M4A/MP4 (ffprobe). A
    file with no chapter markers opens as a single chapter spanning the whole
    file, so it can be split up in the Workbench. Raises
    :class:`BookReadError` when the file cannot be read at all.
    """
    if not path.is_file():
        raise BookReadError(f"File not found: {path}")
    book = _read_mp3(path) if path.suffix.lower() == ".mp3" else _read_mp4(path)
    if not book.chapters:
        if book.total_ms <= 0:
            raise BookReadError("Could not read the file's duration.")
        book.chapters = [Chapter(index=0, title=path.stem, start_ms=0, end_ms=book.total_ms)]
    return book


def _read_mp3(path: Path) -> BookFile:
    try:
        from mutagen.id3 import ID3, ID3NoHeaderError
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise BookReadError("Editing MP3 books requires the 'mutagen' package.") from exc
    from quill.core.speech.chapters import read_mp3_chapters
    from quill.core.speech.ffmpeg import probe_duration_ms

    try:
        id3 = ID3(str(path))
    except ID3NoHeaderError:
        id3 = ID3()
    except Exception as exc:  # noqa: BLE001 - mutagen raises many shapes
        raise BookReadError(f"Could not read tags: {exc}") from exc

    def text(key: str) -> str:
        frame = id3.get(key)
        if frame is not None and getattr(frame, "text", None):
            return str(frame.text[0])
        return ""

    comment = ""
    comms = id3.getall("COMM")
    if comms and comms[0].text:
        comment = str(comms[0].text[0])
    tags = AudioMetadata(
        title=text("TIT2"),
        artist=text("TPE1"),
        album=text("TALB"),
        album_artist=text("TPE2"),
        genre=text("TCON"),
        year=text("TDRC"),
        comment=comment,
    )
    try:
        chapters = read_mp3_chapters(path)
    except Exception:  # noqa: BLE001 - unreadable/absent chapter frames read as none
        chapters = []
    total_ms = probe_duration_ms(path)
    if chapters and chapters[-1].end_ms > total_ms:
        total_ms = chapters[-1].end_ms
    return BookFile(path=path, tags=tags, chapters=chapters, total_ms=total_ms)


def _read_mp4(path: Path) -> BookFile:
    from quill.stability.safe_subprocess import run_subprocess_safely

    ffprobe = find_ffprobe()
    if ffprobe is None:
        raise BookReadError(f"Reading this book needs ffprobe. {INSTALL_HINT}")
    args = [
        ffprobe,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_chapters",
        str(path),
    ]
    try:
        completed = run_subprocess_safely(args, timeout_seconds=120.0)
        data = json.loads(completed.stdout or "{}")
    except (OSError, ValueError) as exc:
        raise BookReadError(f"Could not read the file: {exc}") from exc
    if completed.returncode != 0:
        raise BookReadError("Could not read the file with ffprobe.")

    fmt = data.get("format") or {}
    fmt_tags = {str(k).lower(): str(v) for k, v in (fmt.get("tags") or {}).items()}
    tags = AudioMetadata(
        title=fmt_tags.get("title", ""),
        artist=fmt_tags.get("artist", ""),
        album=fmt_tags.get("album", ""),
        album_artist=fmt_tags.get("album_artist", "") or fmt_tags.get("albumartist", ""),
        genre=fmt_tags.get("genre", ""),
        year=fmt_tags.get("date", "") or fmt_tags.get("year", ""),
        comment=fmt_tags.get("comment", ""),
    )
    chapters: list[Chapter] = []
    for i, entry in enumerate(data.get("chapters") or []):
        try:
            start_ms = int(round(float(entry.get("start_time", 0)) * 1000))
            end_ms = int(round(float(entry.get("end_time", 0)) * 1000))
        except (TypeError, ValueError):
            continue
        title = str((entry.get("tags") or {}).get("title") or f"Chapter {i + 1}")
        chapters.append(Chapter(index=i, title=title, start_ms=start_ms, end_ms=end_ms))
    try:
        total_ms = int(round(float(fmt.get("duration", 0)) * 1000))
    except (TypeError, ValueError):
        total_ms = 0
    if chapters and chapters[-1].end_ms > total_ms:
        total_ms = chapters[-1].end_ms
    return BookFile(path=path, tags=tags, chapters=chapters, total_ms=total_ms)


def save_mp3_book(book: BookFile) -> None:
    """Write the book's tags + chapters back onto its MP3 **in place**.

    Only tag frames change; the audio stream is untouched, so this is instant
    and lossless. Other existing frames (cover art, custom tags) are preserved.
    """
    try:
        from mutagen.id3 import (
            COMM,
            ID3,
            TALB,
            TCON,
            TDRC,
            TIT2,
            TPE1,
            TPE2,
            ID3NoHeaderError,
        )
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise TranscodeError("Saving MP3 books requires the 'mutagen' package.") from exc
    from quill.core.speech.chapters import write_mp3_chapters

    try:
        id3 = ID3(str(book.path))
    except ID3NoHeaderError:
        id3 = ID3()
    values = {
        "TIT2": (TIT2, book.tags.title or book.tags.album),
        "TPE1": (TPE1, book.tags.artist),
        "TALB": (TALB, book.tags.album),
        "TPE2": (TPE2, book.tags.album_artist),
        "TCON": (TCON, book.tags.genre),
        "TDRC": (TDRC, book.tags.year),
    }
    for key, (frame_cls, value) in values.items():
        if value.strip():
            id3.setall(key, [frame_cls(encoding=3, text=[value])])
        else:
            id3.delall(key)
    if book.tags.comment.strip():
        id3.setall("COMM", [COMM(encoding=3, lang="eng", desc="", text=[book.tags.comment])])
    id3.save(str(book.path), v2_version=3)
    # Chapters go through the shared CHAP/CTOC writer (idempotent, preserves tags).
    write_mp3_chapters(book.path, book.chapters)


def build_m4b_remux_command(
    ffmpeg: str, source: Path, ffmetadata: Path, out_path: Path
) -> list[str]:
    """The ffmpeg argv that re-muxes *source* with new chapters/tags, no re-encode.

    ``-map_metadata 1 -map_chapters 1`` takes everything from the FFMETADATA
    input; ``-c copy`` keeps the audio (and attached cover) bit-identical.

    Maps only the audio stream plus an optional video stream (an embedded
    cover image) — never ``-map 0`` blindly. Some M4B sources carry a stray
    ``bin_data``/``SubtitleHandler`` data track (seen on a real Windows-built
    file in end-to-end testing); copying that stream into the ``ipod`` muxer
    fails with "Tag text incompatible with output codec id", so data/subtitle
    streams are excluded outright — a real ffmpeg-path bug no stubbed-source
    unit test could have caught.
    """
    return [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-i",
        str(ffmetadata),
        "-map",
        "0:a",
        "-map",
        "0:v?",
        "-map_metadata",
        "1",
        "-map_chapters",
        "1",
        "-c",
        "copy",
        "-f",
        "ipod",
        "-y",
        str(out_path),
    ]


def save_m4b_book_as(book: BookFile, out_path: Path) -> Path:
    """Write the book with its edited chapters/tags to *out_path* (lossless re-mux).

    M4B chapter atoms cannot be rewritten in place, so the edit is saved as a
    new file (Save As); pointing *out_path* at a different name next to the
    original is the safe default the UI offers.
    """
    import tempfile

    from quill.stability.safe_subprocess import run_subprocess_safely

    ffmpeg = find_ffmpeg()
    if ffmpeg is None:
        raise TranscodeError(f"Saving this book needs ffmpeg. {INSTALL_HINT}")
    if out_path.resolve() == book.path.resolve():
        raise TranscodeError("Choose a different name — an M4B is saved as a new file.")
    chapter_tuples = [(c.title, c.start_ms, c.end_ms) for c in book.chapters]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="quill_book_") as tmp:
        meta_path = Path(tmp) / "meta.ffmeta"
        meta_path.write_text(build_ffmetadata(chapter_tuples, book.tags), encoding="utf-8")
        args = build_m4b_remux_command(ffmpeg, book.path, meta_path, out_path)
        try:
            completed = run_subprocess_safely(args, timeout_seconds=1800.0)
        except OSError as exc:
            raise TranscodeError(f"Could not run ffmpeg: {exc}") from exc
    if completed.returncode != 0 or not out_path.is_file():
        detail = (completed.stderr or "").strip()[:300]
        out_path.unlink(missing_ok=True)
        raise TranscodeError(f"ffmpeg could not save the book. {detail}".strip())
    return out_path
