"""Build one chaptered audiobook/podcast master from a folder of audio files.

The ChapterForge-aligned surface (design source: ``D:\\code99\\forum``, MIT):
point QUILL at a folder of audio files and combine them into a single chaptered
**MP3** or **M4B** master that an audiobook/podcast player navigates track by
track. Each source file becomes a chapter (its title derived from the filename),
a cover image found in the folder is picked up, and the book's tags
(title/author/narrator/genre/year) are written.

wx-free, strict-typed. All ffmpeg work goes through
:mod:`quill.core.speech.ffmpeg`; chapter timing reuses
:func:`quill.core.speech.chapters.compute_chapters`. Only the surfaces that fit
QUILL's current audiobook vision are ported here — ChapterForge's Auphonic, RSS
feed, SFTP-publish, and metadata-lookup features are intentionally left out.
"""

from __future__ import annotations

import re
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from quill.core.speech.ffmpeg import AudioMetadata, TranscodeError

if TYPE_CHECKING:
    from quill.core.speech.chapters import Chapter

# Source audio formats accepted as chapter files, and cover-image discovery.
AUDIO_EXTENSIONS: tuple[str, ...] = (
    ".mp3",
    ".m4a",
    ".m4b",
    ".wav",
    ".flac",
    ".ogg",
    ".opus",
    ".aac",
)
# Output formats that carry navigable chapters: MP3 (ID3 CHAP via mutagen) and
# M4B (native MP4 chapter atoms). These are the only meaningful audiobook outputs —
# FLAC/Opus cannot carry the chapter markers an audiobook needs, so they are not
# offered as output (they are still accepted as source chapter files).
OUTPUT_FORMATS: tuple[str, ...] = ("mp3", "m4b")
_COVER_STEMS: tuple[str, ...] = ("cover", "folder", "front", "albumart", "album", "artwork")
_COVER_EXTENSIONS: tuple[str, ...] = (".jpg", ".jpeg", ".png")

_NUM_RE = re.compile(r"(\d+)")
# A leading track-number prefix: "01 - ", "02_", "03.", "4) ", or a bare "01 "
# before a word. \d{1,3} leaves four-digit years like "1984" alone.
_TRACK_PREFIX_RE = re.compile(r"^\s*\d{1,3}\s*(?:[-._)]+\s*|\s+(?=[^\W\d]))", re.UNICODE)


def natural_key(text: str) -> list[object]:
    """Natural sort key so "track2" precedes "track10" (digits compared as ints)."""
    return [int(part) if part.isdigit() else part.lower() for part in _NUM_RE.split(text)]


def title_from_filename(path: Path) -> str:
    """Derive a chapter title from a filename, stripping a leading track prefix.

    Returns "" when nothing meaningful remains (e.g. ``01.mp3``) so the caller can
    substitute a generated "Chapter N".
    """
    stem = path.stem
    cleaned = _TRACK_PREFIX_RE.sub("", stem).replace("_", " ").strip()
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    # A purely numeric name (e.g. "01") has no real title; let the caller add one.
    return "" if cleaned.isdigit() else cleaned


def find_cover(folder: Path) -> Path | None:
    """Return a likely cover image in *folder* (preferred names first), or None."""
    images = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in _COVER_EXTENSIONS]
    for stem in _COVER_STEMS:
        for image in images:
            if image.stem.lower() == stem:
                return image
    return images[0] if images else None


@dataclass(slots=True)
class AudiobookChapter:
    """One chapter: a primary file, display title, duration, and any merged files.

    A chapter is normally one source file (``extra_paths`` empty). When the user
    **merges** adjacent files in the builder, the trailing files land in
    ``extra_paths`` — they play as part of this chapter (in order, after ``path``)
    but get no chapter marker of their own. ``duration_ms`` is the sum of all parts.
    """

    path: Path
    title: str
    duration_ms: int
    extra_paths: list[Path] = field(default_factory=list)

    @property
    def all_paths(self) -> list[Path]:
        """The chapter's files in play order: the primary file then any merged ones."""
        return [self.path, *self.extra_paths]


@dataclass(slots=True)
class AudiobookResult:
    """What a build produced."""

    output_path: Path
    chapter_count: int
    notes: list[str] = field(default_factory=list)


def scan_audio_folder(folder: Path, *, recursive: bool = False) -> list[Path]:
    """Return the audio files under *folder*, natural-sorted by name."""
    from quill.core.speech.batch_discovery import discover_files

    found = discover_files(folder, list(AUDIO_EXTENSIONS), recursive)
    return sorted(found, key=lambda p: natural_key(p.name))


def build_chapter_list(paths: list[Path]) -> list[AudiobookChapter]:
    """Probe each file's duration and derive its chapter title ("Chapter N" fallback)."""
    from quill.core.speech.ffmpeg import probe_duration_ms

    chapters: list[AudiobookChapter] = []
    for index, path in enumerate(paths, start=1):
        title = title_from_filename(path) or f"Chapter {index}"
        duration = probe_duration_ms(path)
        chapters.append(AudiobookChapter(path=path, title=title, duration_ms=duration))
    return chapters


def chapters_from_plan(plan: list[tuple[str, list[Path]]]) -> list[AudiobookChapter]:
    """Build chapters from an edited ``(title, [files])`` plan, probing durations.

    Each entry is one chapter; entries with more than one file are merged chapters
    (the first file is primary, the rest go to ``extra_paths``). Used by the builder
    when the user has renamed / reordered / merged chapters before building.
    """
    from quill.core.speech.ffmpeg import probe_duration_ms

    chapters: list[AudiobookChapter] = []
    for index, (title, files) in enumerate(plan, start=1):
        if not files:
            continue
        parts = [Path(f) for f in files]
        duration = sum(probe_duration_ms(p) for p in parts)
        chapters.append(
            AudiobookChapter(
                path=parts[0],
                title=title.strip() or f"Chapter {index}",
                duration_ms=duration,
                extra_paths=parts[1:],
            )
        )
    return chapters


def is_probable_master(name: str, folder: Path) -> bool:
    """Heuristic: does *name* look like a previously-built master in *folder*?

    Recognizes a file named after the folder (``My Book.mp3`` inside ``My Book``),
    the suggested output name (``<folder> - Master.mp3``), and any ``… - Master``.
    Used to avoid folding a prior build back in as a chapter.
    """
    base = folder.name.strip().lower()
    stem = Path(name).stem.strip().lower()
    if base and stem in (base, f"{base} - master"):
        return True
    return stem.endswith(" - master") or stem.endswith("- master")


@dataclass(slots=True)
class StreamStats:
    """One source file's audio stream shape, for the pre-flight check."""

    path: Path
    sample_rate: int = 0
    channels: int = 0
    codec: str = ""
    bit_rate_kbps: int = 0


def probe_stream_stats(path: Path, *, timeout_seconds: float = 60.0) -> StreamStats:
    """Read *path*'s first audio stream shape via ffprobe (zeros when unknown)."""
    import json

    from quill.core.speech.ffmpeg import find_ffprobe
    from quill.stability.safe_subprocess import run_subprocess_safely

    stats = StreamStats(path=path)
    ffprobe = find_ffprobe()
    if ffprobe is None or not path.is_file():
        return stats
    args = [
        ffprobe,
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=sample_rate,channels,codec_name,bit_rate:format=bit_rate",
        "-of",
        "json",
        str(path),
    ]
    try:
        completed = run_subprocess_safely(args, timeout_seconds=timeout_seconds)
        data = json.loads(completed.stdout or "{}")
    except (OSError, ValueError):
        return stats
    streams = data.get("streams") or []
    if streams:
        stream = streams[0]
        try:
            stats.sample_rate = int(stream.get("sample_rate") or 0)
        except (TypeError, ValueError):
            pass
        try:
            stats.channels = int(stream.get("channels") or 0)
        except (TypeError, ValueError):
            pass
        stats.codec = str(stream.get("codec_name") or "")
        bit_rate = stream.get("bit_rate")
        if not bit_rate or bit_rate == "N/A":
            bit_rate = (data.get("format") or {}).get("bit_rate")
        try:
            stats.bit_rate_kbps = int(int(bit_rate) / 1000) if bit_rate else 0
        except (TypeError, ValueError):
            pass
    return stats


@dataclass(slots=True)
class PreflightReport:
    """The pre-flight verdict for a set of source files, in speakable sentences."""

    uniform: bool
    notes: list[str] = field(default_factory=list)


def preflight_check(stats: list[StreamStats]) -> PreflightReport:
    """Whether the sources share one stream shape (lossless concat) — and if not, why.

    Pure: probe with :func:`probe_stream_stats` first. Mixed shapes are fine —
    the build re-encodes — but the user should hear it before a long run.
    """
    known = [s for s in stats if s.sample_rate > 0 and s.channels > 0]
    if not known:
        return PreflightReport(uniform=True)
    notes: list[str] = []
    rates = {s.sample_rate for s in known}
    channels = {s.channels for s in known}
    codecs = {s.codec for s in known if s.codec}
    first = known[0]
    if len(rates) > 1:
        offenders = ", ".join(
            f"{s.path.name} ({s.sample_rate} Hz)"
            for s in known[:20]
            if s.sample_rate != first.sample_rate
        )
        notes.append(f"Sample rates differ: {offenders}.")
    if len(channels) > 1:
        offenders = ", ".join(
            f"{s.path.name} ({s.channels} ch)" for s in known[:20] if s.channels != first.channels
        )
        notes.append(f"Channel counts differ: {offenders}.")
    if len(codecs) > 1:
        notes.append(f"Formats differ: {', '.join(sorted(codecs))}.")
    return PreflightReport(uniform=not notes, notes=notes)


def estimate_output(
    chapters: list[AudiobookChapter], *, bitrate_kbps: int = 96, gap_ms: int = 0
) -> tuple[int, int]:
    """Estimate the master's ``(total_ms, approximate_bytes)`` before building."""
    total_ms = sum(max(0, c.duration_ms) for c in chapters)
    total_ms += max(0, len(chapters) - 1) * max(0, gap_ms)
    est_bytes = int(bitrate_kbps * 1000 / 8 * (total_ms / 1000.0))
    return total_ms, est_bytes


def format_size(num_bytes: int) -> str:
    """Human-readable byte size ("118.3 MB")."""
    size = float(max(0, num_bytes))
    for unit in ("bytes", "KB", "MB"):
        if size < 1024:
            return f"{int(size)} {unit}" if unit == "bytes" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def read_m4b_chapters(path: Path, *, timeout_seconds: float = 60.0) -> list[Chapter]:
    """Read the native MP4 chapter atoms from an M4B/M4A via ffprobe."""
    import json

    from quill.core.speech.chapters import Chapter
    from quill.core.speech.ffmpeg import find_ffprobe
    from quill.stability.safe_subprocess import run_subprocess_safely

    ffprobe = find_ffprobe()
    if ffprobe is None or not path.is_file():
        return []
    args = [ffprobe, "-v", "error", "-show_chapters", "-of", "json", str(path)]
    try:
        completed = run_subprocess_safely(args, timeout_seconds=timeout_seconds)
        data = json.loads(completed.stdout or "{}")
    except (OSError, ValueError):
        return []
    chapters: list[Chapter] = []
    for index, entry in enumerate(data.get("chapters") or []):
        try:
            start_ms = int(round(float(entry.get("start_time", 0)) * 1000))
            end_ms = int(round(float(entry.get("end_time", 0)) * 1000))
        except (TypeError, ValueError):
            continue
        title = str((entry.get("tags") or {}).get("title") or f"Chapter {index + 1}")
        chapters.append(Chapter(index=index, title=title, start_ms=start_ms, end_ms=end_ms))
    return chapters


def read_chapters(path: Path) -> list[Chapter]:
    """Read the chapter markers from an existing MP3 (ID3 CHAP) or M4B/M4A file."""
    from quill.core.speech.chapters import read_mp3_chapters

    if path.suffix.lower() == ".mp3":
        try:
            return read_mp3_chapters(path)
        except Exception:  # noqa: BLE001 - unreadable/absent tags read as no chapters
            return []
    return read_m4b_chapters(path)


@dataclass(slots=True)
class VerificationResult:
    """The post-build read-back: honest numbers for the completion announcement."""

    ok: bool
    chapter_count: int
    total_ms: int
    issues: list[str] = field(default_factory=list)


def verify_audiobook(path: Path, *, expected_chapters: int | None = None) -> VerificationResult:
    """Re-read a freshly built master and sanity-check what a player will see."""
    from quill.core.speech.ffmpeg import probe_duration_ms

    issues: list[str] = []
    chapters = read_chapters(path)
    count = len(chapters)
    total_ms = probe_duration_ms(path)
    if expected_chapters is not None and count != expected_chapters:
        issues.append(f"Expected {expected_chapters} chapter(s) but found {count}.")
    if total_ms <= 0:
        issues.append("Could not read a positive duration.")
    for i in range(1, count):
        if chapters[i].start_ms < chapters[i - 1].start_ms:
            issues.append("Chapter start times are out of order.")
            break
    return VerificationResult(ok=not issues, chapter_count=count, total_ms=total_ms, issues=issues)


def chapter_report_text(chapters: list[AudiobookChapter], *, title: str = "") -> str:
    """A plain-text chapter report (one readable line per chapter) for the output folder."""
    from quill.core.speech.chapter_io import format_timestamp
    from quill.core.speech.chapters import ChapterSection, compute_chapters

    computed = compute_chapters([
        ChapterSection(title=c.title, duration_ms=c.duration_ms) for c in chapters
    ])
    lines = [f"Chapter report{': ' + title if title else ''}", ""]
    for c in computed:
        lines.append(
            f"{c.index + 1:3d}. {c.title} — starts {format_timestamp(c.start_ms)}, "
            f"runs {format_timestamp(c.duration_ms)}"
        )
    total = computed[-1].end_ms if computed else 0
    lines.extend(["", f"{len(computed)} chapter(s), {format_timestamp(total)} total."])
    return "\n".join(lines) + "\n"


def write_book_sidecars(
    output_path: Path, chapters: list[AudiobookChapter], *, title: str = ""
) -> list[Path]:
    """Write the chapter report and Podcasting 2.0 ``…chapters.json`` next to the book.

    Best-effort artifacts for the completion story: the report is a plain-text
    listing anyone can read, the sidecar is the podcast-namespace chapters file
    players and hosts consume. Returns the paths written.
    """
    from quill.core.speech.chapter_io import chapters_to_pod2
    from quill.core.speech.chapters import ChapterSection, compute_chapters

    computed = compute_chapters([
        ChapterSection(title=c.title, duration_ms=c.duration_ms) for c in chapters
    ])
    report_path = output_path.with_suffix(".chapters.txt")
    report_path.write_text(chapter_report_text(chapters, title=title), encoding="utf-8")
    sidecar_path = output_path.with_suffix(".chapters.json")
    sidecar_path.write_text(chapters_to_pod2(computed), encoding="utf-8")
    return [report_path, sidecar_path]


def _ffconcat_quote(path: Path) -> str:
    """Quote a path for the ffmpeg concat demuxer (single quotes are escaped)."""
    return "'" + str(path).replace("'", "'\\''") + "'"


def build_concat_list(paths: list[Path]) -> str:
    """Build the ffmpeg concat-demuxer list document for *paths*."""
    return "\n".join(f"file {_ffconcat_quote(p)}" for p in paths) + "\n"


def build_audiobook_command(
    ffmpeg: str,
    concat_list: Path,
    out_path: Path,
    fmt: str,
    *,
    ffmetadata: Path | None = None,
    cover: Path | None = None,
    map_chapters: bool = False,
    acx_normalize: bool = False,
) -> list[str]:
    """Build the ffmpeg argv that concatenates the chapter files into *out_path*.

    Inputs are ordered: the concat list, then (optional) the FFMETADATA document,
    then (optional) the cover image. Tags/chapters come from the metadata input;
    the cover is mapped as an attached picture. When *acx_normalize* is set the
    audio is run through the ``loudnorm`` filter to bring it into ACX loudness range
    during the (already re-encoding) build. Pure and unit-tested.
    """
    args = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_list),
    ]
    next_index = 1
    meta_index = cover_index = -1
    if ffmetadata is not None:
        args.extend(["-i", str(ffmetadata)])
        meta_index = next_index
        next_index += 1
    if cover is not None:
        args.extend(["-i", str(cover)])
        cover_index = next_index
        next_index += 1
    args.extend(["-map", "0:a"])
    if cover is not None:
        args.extend(["-map", f"{cover_index}:v", "-disposition:v:0", "attached_pic"])
    if meta_index >= 0:
        args.extend(["-map_metadata", str(meta_index)])
        if map_chapters:
            args.extend(["-map_chapters", str(meta_index)])
    if acx_normalize:
        from quill.core.speech.loudness import loudnorm_filter

        args.extend(["-af", loudnorm_filter()])
    if fmt == "m4b":
        args.extend(["-c:a", "aac", "-b:a", "96k", "-c:v", "copy", "-f", "ipod"])
    else:  # mp3
        args.extend(["-c:a", "libmp3lame", "-q:a", "4", "-c:v", "copy"])
    args.extend(["-y", str(out_path)])
    return args


def build_audiobook(
    chapters: list[AudiobookChapter],
    output_path: Path,
    *,
    output_format: str = "m4b",
    metadata: AudioMetadata | None = None,
    cover: Path | None = None,
    acx_normalize: bool = False,
    trim_silence_files: bool = False,
    fade_in_ms: int = 0,
    fade_out_ms: int = 0,
    tempo: float = 1.0,
    on_progress: Callable[[str], None] | None = None,
    cancel_event: threading.Event | None = None,
) -> AudiobookResult:
    """Concatenate *chapters* into one chaptered audiobook master at *output_path*.

    Before concatenation each source file is run through the optional polish
    pipeline in :func:`quill.core.speech.audio_edit.prepare_chapter_files`:
    head/tail silence trim (when *trim_silence_files*), fade-in/fade-out
    (when *fade_in_ms* / *fade_out_ms*), and pitch-preserving tempo
    (*tempo* != 1.0). A failure in one step keeps the file's previous form
    and the build continues — polish must never sink a book. Polish writes
    to a per-chapter stage directory under the build's tempdir, so the
    caller's source files are never modified.

    Returns an :class:`AudiobookResult`. Raises :class:`TranscodeError` when ffmpeg
    is unavailable or the build fails, and :class:`ValueError` on empty input.
    """
    import tempfile

    from quill.core.speech.audio_edit import prepare_chapter_files
    from quill.core.speech.chapters import (
        ChapterSection,
        compute_chapters,
        write_mp3_chapters,
    )
    from quill.core.speech.ffmpeg import build_ffmetadata, find_ffmpeg
    from quill.stability.safe_subprocess import run_subprocess_safely

    fmt = output_format.strip().lower()
    if fmt not in OUTPUT_FORMATS:
        raise ValueError(f"Unsupported audiobook format: {output_format!r}")
    speakable = [c for c in chapters if c.path.is_file()]
    if not speakable:
        raise ValueError("No audio files to build an audiobook from.")
    if cancel_event is not None and cancel_event.is_set():
        raise TranscodeError("Audiobook build cancelled.")

    ffmpeg = find_ffmpeg()
    if ffmpeg is None:
        from quill.core.speech.ffmpeg import INSTALL_HINT

        raise TranscodeError(f"ffmpeg is not installed. {INSTALL_HINT}")

    # Pre-build polish: trim/fade/tempo runs against the flat concat list, in
    # order, with the original chapter structure preserved (polish is per-file;
    # it never reorders or splits anything). The staged files are written under
    # the build's tempdir so the caller's sources are untouched.
    want_polish = (
        trim_silence_files or fade_in_ms > 0 or fade_out_ms > 0 or abs(float(tempo) - 1.0) > 1e-6
    )
    concat_paths: list[Path]
    with tempfile.TemporaryDirectory(prefix="quill_audiobook_") as tmp:
        tmp_dir = Path(tmp)
        if want_polish:
            if on_progress is not None:
                on_progress("Polishing chapter files...")
            staged_src = [p for c in speakable for p in c.all_paths if p.is_file()]
            concat_paths = prepare_chapter_files(
                staged_src,
                tmp_dir / "polish",
                trim_silence_files=trim_silence_files,
                fade_in_ms=fade_in_ms,
                fade_out_ms=fade_out_ms,
                tempo=float(tempo),
                on_progress=on_progress,
            )
        else:
            concat_paths = [p for c in speakable for p in c.all_paths if p.is_file()]

        computed = compute_chapters(
            [ChapterSection(title=c.title, duration_ms=c.duration_ms) for c in speakable], gap_ms=0
        )
        notes: list[str] = []
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if on_progress is not None:
            on_progress("Combining chapters...")

        list_path = tmp_dir / "chapters.txt"
        list_path.write_text(build_concat_list(concat_paths), encoding="utf-8")
        meta_path = tmp_dir / "meta.ffmeta"
        # M4B carries chapters natively; MP3 gets tags from ffmpeg and chapters from
        # mutagen afterwards (ffmpeg does not write ID3 CHAP frames reliably).
        chapter_tuples = [(c.title, c.start_ms, c.end_ms) for c in computed] if fmt == "m4b" else []
        meta_path.write_text(build_ffmetadata(chapter_tuples, metadata), encoding="utf-8")
        args = build_audiobook_command(
            ffmpeg,
            list_path,
            output_path,
            fmt,
            ffmetadata=meta_path,
            cover=cover if (cover and cover.is_file()) else None,
            map_chapters=(fmt == "m4b"),
            acx_normalize=acx_normalize,
        )
        try:
            completed = run_subprocess_safely(args, timeout_seconds=1800.0)
        except OSError as exc:
            raise TranscodeError(f"Could not run ffmpeg: {exc}") from exc

    if completed.returncode != 0:
        detail = (completed.stderr or "").strip()[:300]
        output_path.unlink(missing_ok=True)
        raise TranscodeError(f"ffmpeg could not build the audiobook. {detail}".strip())
    if not output_path.is_file():
        raise TranscodeError("ffmpeg produced no output.")

    if fmt == "mp3":
        if on_progress is not None:
            on_progress("Writing chapter markers...")
        try:
            write_mp3_chapters(output_path, computed)
        except RuntimeError as exc:  # mutagen missing
            notes.append(f"Chapter markers not written ({exc}).")

    return AudiobookResult(output_path=output_path, chapter_count=len(speakable), notes=notes)
