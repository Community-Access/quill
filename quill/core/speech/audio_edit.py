"""Audio surgery helpers: trim, fades, tempo, and split-into-chapter-files.

wx-free, strict-typed. Ported from ChapterForge (``s:\\code99\\forum``, MIT),
re-based on QUILL's ffmpeg/safe_subprocess idioms. All argv builders are pure
and unit-tested; runners raise :class:`TranscodeError` with speakable messages.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

from quill.core.speech.chapters import Chapter
from quill.core.speech.ffmpeg import INSTALL_HINT, TranscodeError, find_ffmpeg

_SAFE_FILENAME_RE = re.compile(r"[^\w\-. ]", re.UNICODE)


def _run(args: list[str], out_path: Path, action: str, *, timeout_seconds: float = 1800.0) -> Path:
    from quill.stability.safe_subprocess import run_subprocess_safely

    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        completed = run_subprocess_safely(args, timeout_seconds=timeout_seconds)
    except OSError as exc:
        raise TranscodeError(f"Could not run ffmpeg: {exc}") from exc
    if completed.returncode != 0 or not out_path.is_file():
        detail = (completed.stderr or "").strip()[:300]
        out_path.unlink(missing_ok=True)
        raise TranscodeError(f"ffmpeg could not {action}. {detail}".strip())
    return out_path


def _require_ffmpeg() -> str:
    ffmpeg = find_ffmpeg()
    if ffmpeg is None:
        raise TranscodeError(f"ffmpeg is not installed. {INSTALL_HINT}")
    return ffmpeg


def build_trim_command(
    ffmpeg: str, source: Path, out_path: Path, *, start_ms: int, end_ms: int
) -> list[str]:
    """The ffmpeg argv that keeps ``[start_ms, end_ms)`` of *source* (re-encoded)."""
    return [
        ffmpeg,
        "-hide_banner",
        "-nostdin",
        "-ss",
        f"{start_ms / 1000.0:.3f}",
        "-to",
        f"{end_ms / 1000.0:.3f}",
        "-i",
        str(source),
        "-y",
        str(out_path),
    ]


def trim_file(source: Path, out_path: Path, *, start_ms: int, end_ms: int) -> Path:
    """Write the ``[start_ms, end_ms)`` slice of *source* to *out_path*."""
    if end_ms <= start_ms:
        raise ValueError("The trim end must be after its start.")
    return _run(
        build_trim_command(_require_ffmpeg(), source, out_path, start_ms=start_ms, end_ms=end_ms),
        out_path,
        "trim the audio",
    )


def atempo_filter(speed: float) -> str:
    """An ``atempo`` chain for *speed* (each stage stays inside atempo's 0.5-2.0)."""
    speed = max(0.25, min(4.0, float(speed)))
    stages: list[str] = []
    remaining = speed
    while remaining > 2.0:
        stages.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        stages.append("atempo=0.5")
        remaining /= 0.5
    stages.append(f"atempo={remaining:.6g}")
    return ",".join(stages)


def build_tempo_command(ffmpeg: str, source: Path, out_path: Path, *, speed: float) -> list[str]:
    """The ffmpeg argv that re-times *source* by *speed*, pitch preserved."""
    return [
        ffmpeg,
        "-hide_banner",
        "-nostdin",
        "-i",
        str(source),
        "-af",
        atempo_filter(speed),
        "-y",
        str(out_path),
    ]


def apply_tempo(source: Path, out_path: Path, *, speed: float) -> Path:
    """Write a pitch-preserving speed-changed copy of *source* to *out_path*."""
    return _run(
        build_tempo_command(_require_ffmpeg(), source, out_path, speed=speed),
        out_path,
        "change the audio speed",
    )


def build_fade_command(
    ffmpeg: str,
    source: Path,
    out_path: Path,
    *,
    duration_ms: int,
    fade_in_ms: int = 0,
    fade_out_ms: int = 0,
) -> list[str]:
    """The ffmpeg argv that applies fade-in/fade-out to *source*."""
    filters: list[str] = []
    if fade_in_ms > 0:
        filters.append(f"afade=t=in:st=0:d={fade_in_ms / 1000.0:.3f}")
    if fade_out_ms > 0:
        start_s = max(0.0, (duration_ms - fade_out_ms) / 1000.0)
        filters.append(f"afade=t=out:st={start_s:.3f}:d={fade_out_ms / 1000.0:.3f}")
    return [
        ffmpeg,
        "-hide_banner",
        "-nostdin",
        "-i",
        str(source),
        "-af",
        ",".join(filters) if filters else "anull",
        "-y",
        str(out_path),
    ]


def apply_fades(
    source: Path, out_path: Path, *, duration_ms: int, fade_in_ms: int = 0, fade_out_ms: int = 0
) -> Path:
    """Write a faded copy of *source* to *out_path* (no-op filters when both are 0)."""
    return _run(
        build_fade_command(
            _require_ffmpeg(),
            source,
            out_path,
            duration_ms=duration_ms,
            fade_in_ms=fade_in_ms,
            fade_out_ms=fade_out_ms,
        ),
        out_path,
        "apply the fades",
    )


def prepare_chapter_files(
    paths: list[Path],
    work_dir: Path,
    *,
    trim_silence_files: bool = False,
    fade_in_ms: int = 0,
    fade_out_ms: int = 0,
    tempo: float = 1.0,
    on_progress: Callable[[str], None] | None = None,
) -> list[Path]:
    """Run each source file through the enabled polish steps; returns new paths.

    Steps, in order per file: head/tail silence trim, fades, pitch-preserving
    tempo. Files keep their names (under *work_dir*) so filename-derived
    chapter titles and natural ordering are unchanged. With nothing enabled
    the original paths come back untouched — zero cost on the default path.
    A file that fails a step keeps its previous form and the run continues;
    polish must never sink a book.
    """
    from quill.core.speech.ffmpeg import probe_duration_ms
    from quill.core.speech.silence import trim_silence

    wants_tempo = abs(tempo - 1.0) > 1e-6
    if not (trim_silence_files or fade_in_ms > 0 or fade_out_ms > 0 or wants_tempo):
        return list(paths)
    work_dir.mkdir(parents=True, exist_ok=True)
    prepared: list[Path] = []
    for index, source in enumerate(paths):
        current = source
        stage_dir = work_dir / f"{index:03d}"
        try:
            if trim_silence_files:
                if on_progress is not None:
                    on_progress(f"Trimming silence: {source.name}")
                current = trim_silence(current, stage_dir / f"trim_{source.name}")
            if fade_in_ms > 0 or fade_out_ms > 0:
                if on_progress is not None:
                    on_progress(f"Applying fades: {source.name}")
                current = apply_fades(
                    current,
                    stage_dir / f"fade_{source.name}",
                    duration_ms=probe_duration_ms(current),
                    fade_in_ms=fade_in_ms,
                    fade_out_ms=fade_out_ms,
                )
            if wants_tempo:
                if on_progress is not None:
                    on_progress(f"Adjusting tempo: {source.name}")
                current = apply_tempo(current, stage_dir / f"tempo_{source.name}", speed=tempo)
        except TranscodeError:
            pass  # keep the last good form of this file; the build goes on
        # The final copy carries the ORIGINAL name so titles/order are stable.
        if current != source:
            final = stage_dir / source.name
            try:
                current.replace(final)
                current = final
            except OSError:
                pass
        prepared.append(current)
    return prepared


def safe_chapter_filename(index: int, title: str, extension: str) -> str:
    """A per-chapter output filename: ``NN - Title.ext`` with unsafe characters removed."""
    cleaned = _SAFE_FILENAME_RE.sub("", title).strip() or f"Chapter {index}"
    return f"{index:02d} - {cleaned}{extension}"


def split_into_files(
    source: Path,
    chapters: list[Chapter],
    out_dir: Path,
    *,
    extension: str = ".mp3",
) -> list[Path]:
    """Cut *source* into one file per chapter under *out_dir*; returns the paths.

    The reverse trip of the audiobook build — a chaptered master becomes a folder
    of per-chapter files (podcast episodes, track-per-chapter players).
    """
    ffmpeg = _require_ffmpeg()
    written: list[Path] = []
    for i, c in enumerate(chapters, start=1):
        out_path = out_dir / safe_chapter_filename(i, c.title, extension)
        _run(
            build_trim_command(ffmpeg, source, out_path, start_ms=c.start_ms, end_ms=c.end_ms),
            out_path,
            f"write chapter {i}",
        )
        written.append(out_path)
    return written
