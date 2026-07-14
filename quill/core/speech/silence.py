"""Silence detection: auto-chapter proposals and per-file silence trimming.

wx-free, strict-typed. Ported from ChapterForge (``s:\\code99\\forum``, MIT) and
re-based on QUILL's ffmpeg/safe_subprocess idioms. Two surfaces:

- :func:`detect_silence_chapters` — split one long recording into a proposed
  chapter list at detected silences (ffmpeg ``silencedetect``). The proposal is
  always reviewed by the user in the Chapter Workbench, never applied blind.
- :func:`build_silence_trim_command` / :func:`trim_silence` — remove leading
  and trailing silence from a file before it is merged into a book.

The argv builders are pure and unit-tested; only the runners touch ffmpeg.
"""

from __future__ import annotations

import re
from pathlib import Path

from quill.core.speech.chapters import Chapter
from quill.core.speech.ffmpeg import INSTALL_HINT, TranscodeError, find_ffmpeg

_SILENCE_START_RE = re.compile(r"silence_start:\s*([0-9.]+)")
_SILENCE_END_RE = re.compile(r"silence_end:\s*([0-9.]+)")


def build_silence_detect_command(
    ffmpeg: str, path: Path, *, noise_db: float, min_silence_s: float
) -> list[str]:
    """The ffmpeg argv that scans *path* for silences (output parsed from stderr)."""
    return [
        ffmpeg,
        "-hide_banner",
        "-nostdin",
        "-i",
        str(path),
        "-af",
        f"silencedetect=noise={noise_db}dB:d={min_silence_s}",
        "-f",
        "null",
        "-",
    ]


def parse_silence_log(text: str) -> list[tuple[float, float]]:
    """Pair each ``silence_start`` with its following ``silence_end`` (seconds).

    A trailing start with no end (silence running to EOF) pairs with itself so
    the midpoint lands at the silence start.
    """
    starts = [float(m) for m in _SILENCE_START_RE.findall(text)]
    ends = [float(m) for m in _SILENCE_END_RE.findall(text)]
    pairs: list[tuple[float, float]] = []
    ei = 0
    for s in starts:
        while ei < len(ends) and ends[ei] < s:
            ei += 1
        if ei < len(ends):
            pairs.append((s, ends[ei]))
            ei += 1
        else:
            pairs.append((s, s))
    return pairs


def propose_chapters_from_silences(
    silences: list[tuple[float, float]],
    total_ms: int,
    *,
    min_chapter_ms: int = 5000,
    title_prefix: str = "Chapter",
) -> list[Chapter]:
    """Turn silence pairs into a contiguous chapter proposal over ``[0, total_ms]``.

    A boundary is placed at the midpoint of each silence; boundaries that would
    create a chapter shorter than *min_chapter_ms* are merged into the previous
    one. Always returns at least one chapter spanning the whole file.
    """
    splits: list[int] = []
    for start_s, end_s in silences:
        mid_ms = int(round((start_s + end_s) / 2.0 * 1000))
        if 0 < mid_ms < total_ms:
            splits.append(mid_ms)

    boundaries = [0, *sorted(set(splits)), total_ms]
    merged = [boundaries[0]]
    for b in boundaries[1:-1]:
        if b - merged[-1] >= min_chapter_ms:
            merged.append(b)
    merged.append(total_ms)
    # A too-short final chapter folds back into the one before it.
    if len(merged) > 2 and merged[-1] - merged[-2] < min_chapter_ms:
        merged.pop(-2)

    return [
        Chapter(index=i, title=f"{title_prefix} {i + 1}", start_ms=merged[i], end_ms=merged[i + 1])
        for i in range(len(merged) - 1)
    ]


def detect_silence_chapters(
    path: Path,
    *,
    noise_db: float = -30.0,
    min_silence_s: float = 0.8,
    min_chapter_ms: int = 5000,
    title_prefix: str = "Chapter",
    timeout_seconds: float = 600.0,
) -> list[Chapter]:
    """Scan *path* and propose chapters at its silences.

    Raises :class:`TranscodeError` when ffmpeg is unavailable, the file's
    duration cannot be read, or the scan fails.
    """
    from quill.core.speech.ffmpeg import probe_duration_ms
    from quill.stability.safe_subprocess import run_subprocess_safely

    ffmpeg = find_ffmpeg()
    if ffmpeg is None:
        raise TranscodeError(f"ffmpeg is not installed. {INSTALL_HINT}")
    total_ms = probe_duration_ms(path)
    if total_ms <= 0:
        raise TranscodeError("Could not read the audio file's duration.")
    try:
        completed = run_subprocess_safely(
            build_silence_detect_command(
                ffmpeg, path, noise_db=noise_db, min_silence_s=min_silence_s
            ),
            timeout_seconds=timeout_seconds,
        )
    except OSError as exc:
        raise TranscodeError(f"Could not run ffmpeg: {exc}") from exc
    silences = parse_silence_log(completed.stderr or "")
    return propose_chapters_from_silences(
        silences, total_ms, min_chapter_ms=min_chapter_ms, title_prefix=title_prefix
    )


def build_silence_trim_command(
    ffmpeg: str,
    source: Path,
    out_path: Path,
    *,
    noise_db: float = -45.0,
    min_silence_s: float = 0.35,
) -> list[str]:
    """The ffmpeg argv that trims leading and trailing silence from *source*.

    Uses two ``silenceremove`` passes around an ``areverse`` pair (the standard
    trick: trim the head, reverse, trim the new head — the old tail — and
    reverse back). Re-encodes to the output's format.
    """
    remove = (
        f"silenceremove=start_periods=1:start_threshold={noise_db}dB:start_silence={min_silence_s}"
    )
    return [
        ffmpeg,
        "-hide_banner",
        "-nostdin",
        "-i",
        str(source),
        "-af",
        f"{remove},areverse,{remove},areverse",
        "-y",
        str(out_path),
    ]


def trim_silence(
    source: Path, out_path: Path, *, noise_db: float = -45.0, min_silence_s: float = 0.35
) -> Path:
    """Write a head/tail silence-trimmed copy of *source* to *out_path*."""
    from quill.stability.safe_subprocess import run_subprocess_safely

    ffmpeg = find_ffmpeg()
    if ffmpeg is None:
        raise TranscodeError(f"ffmpeg is not installed. {INSTALL_HINT}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        completed = run_subprocess_safely(
            build_silence_trim_command(
                ffmpeg, source, out_path, noise_db=noise_db, min_silence_s=min_silence_s
            ),
            timeout_seconds=1800.0,
        )
    except OSError as exc:
        raise TranscodeError(f"Could not run ffmpeg: {exc}") from exc
    if completed.returncode != 0 or not out_path.is_file():
        detail = (completed.stderr or "").strip()[:300]
        out_path.unlink(missing_ok=True)
        raise TranscodeError(f"ffmpeg could not trim silence. {detail}".strip())
    return out_path
