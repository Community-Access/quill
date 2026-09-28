"""Preview, Join and Split: the Converter's three ways of working on a whole.

* **Preview** renders fifteen seconds exactly as the batch would -- through
  the chosen format's own encoder and every effect -- and decodes it back to a
  WAV the app plays. "Preview Original" renders the same fifteen seconds
  untouched, so the two can be compared back to back. The window starts a
  quarter of the way in (at most thirty seconds), because the first seconds
  of most recordings are silence, a jingle or somebody saying "is this on?".
* **Join** makes one file of the queue, in queue order. Every source is first
  decoded to a FLAC of one shape (so files of different rates and channel
  counts join cleanly, which the concat demuxer alone does not promise), then
  the batch's own spec encodes the joined whole -- effects and all -- and a
  chapter is written per source for the formats that carry chapters.
* **Split by chapters** turns one chaptered file into one file per chapter.
  It produces ordinary :class:`~quill.core.audio.convert.ConversionJob`\\ s,
  clipped with the spec's ``start_s``/``end_s``, so the tested batch runner does
  the work and Stop, progress and the report all come for free.

Command builders are pure; the two ``run_*`` functions shell out.
"""

from __future__ import annotations

import re
import shutil
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import replace
from pathlib import Path

from quill.core.audio.chapter_plan import NATIVE_FORMATS, place_chapters
from quill.core.audio.convert import (
    Channels,
    ConversionJob,
    ConversionSpec,
    build_convert_command,
    discover_inputs,
)
from quill.core.audio.ffmpeg_live import LiveHooks, run_ffmpeg_live
from quill.core.audio.formats import VIDEO_EXTENSIONS, VIDEO_OUTPUT_FORMATS
from quill.core.audio.media_probe import Chapter, probe
from quill.core.speech.ffmpeg import AudioMetadata, build_ffmetadata

PREVIEW_SECONDS = 15.0

#: The audio format a video format's sound is previewed as.
_VIDEO_AUDIO_AS: dict[str, str] = {
    "aac": "m4a",
    "libopus": "opus",
    "libmp3lame": "mp3",
    "wmav2": "wma",
    "mp2": "mp2",
    "libvorbis": "ogg",
}

#: Formats FFmpeg writes a Join's chapter marks into; every other format gets
#: them placed afterwards (Ogg/FLAC comments, or a .cue beside the file).
CHAPTER_FORMATS: frozenset[str] = NATIVE_FORMATS


def preview_start(duration_s: float, clip_start: float = 0.0) -> float:
    """Where a preview begins: a quarter in, at most 30 s, inside the clip."""
    if duration_s <= PREVIEW_SECONDS:
        return clip_start
    return clip_start + min(30.0, max(0.0, (duration_s - clip_start) * 0.25))


def preview_audio_spec(spec: ConversionSpec, start_s: float) -> ConversionSpec:
    """The spec a preview encodes with: the batch's sound, fifteen seconds of it."""
    fmt = spec.fmt.strip().lower()
    video = VIDEO_OUTPUT_FORMATS.get(fmt)
    if video is not None:
        fmt = _VIDEO_AUDIO_AS.get(video.audio_codec, "m4a")
    return replace(
        spec,
        fmt=fmt,
        start_s=start_s,
        end_s=start_s + PREVIEW_SECONDS,
        extract_from_video=True,
        copy_audio=False,
        copy_video=False,
        metadata=None,
        exact_optilab=None,
        chapter_source="none",  # fifteen seconds need no chapters, nor a pause scan
    )


def build_original_preview_command(
    ffmpeg: str, source: Path, start_s: float, out_wav: Path
) -> list[str]:
    """Fifteen untouched seconds of *source* as a WAV (pure)."""
    return [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{start_s:g}",
        "-t",
        f"{PREVIEW_SECONDS:g}",
        "-i",
        str(source),
        "-map",
        "0:a:0",
        "-c:a",
        "pcm_s16le",
        "-f",
        "wav",
        "-y",
        str(out_wav),
    ]


def build_decode_to_wav_command(ffmpeg: str, source: Path, out_wav: Path) -> list[str]:
    """Decode an encoded preview back to a WAV the system can play (pure)."""
    return [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-map",
        "0:a:0",
        "-c:a",
        "pcm_s16le",
        "-f",
        "wav",
        "-y",
        str(out_wav),
    ]


def render_preview(
    ffmpeg: str,
    source: Path,
    spec: ConversionSpec,
    out_wav: Path,
    *,
    original: bool,
    run: Callable[[list[str]], object] | None = None,
    duration_s: float | None = None,
) -> Path:
    """Render a preview WAV of *source*; raises ``RuntimeError`` with a reason."""
    runner = run or _run
    length = duration_s if duration_s is not None else probe(source).duration_s
    start = preview_start(length, float(spec.start_s or 0.0))
    if original:
        _check(runner(build_original_preview_command(ffmpeg, source, start, out_wav)))
        return out_wav
    pspec = preview_audio_spec(spec, start)
    encoded = out_wav.with_name(out_wav.stem + "-encoded" + pspec.output_extension())
    job = ConversionJob(source=source, dest=encoded, spec=pspec)
    _check(runner(build_convert_command(ffmpeg, job)))
    _check(runner(build_decode_to_wav_command(ffmpeg, encoded, out_wav)))
    encoded.unlink(missing_ok=True)
    return out_wav


# --------------------------------------------------------------------------- #
# Join
# --------------------------------------------------------------------------- #


def join_inputs(queue: Sequence[tuple[Path, Path | None]], *, recurse: bool) -> list[Path]:
    """The files a Join takes, in queue order (a folder contributes its files sorted)."""
    seen: set[Path] = set()
    out: list[Path] = []
    for entry, _root in queue:
        for path in discover_inputs(entry, recurse=recurse):
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                out.append(path)
    return out


def chapter_title_for(path: Path, tags: dict[str, str]) -> str:
    """A source's chapter title: its own title tag, else a tidied file name."""
    title = (tags.get("title") or "").strip()
    if title:
        return title
    stem = re.sub(r"^\d+[\s._-]+", "", path.stem)  # "01 - Intro" -> "Intro"
    return stem.replace("_", " ").strip() or path.stem


def build_normalize_command(
    ffmpeg: str, source: Path, out_flac: Path, *, rate: int, channels: int
) -> list[str]:
    """Decode one Join source to a FLAC of the shared shape (pure)."""
    return [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-map",
        "0:a:0",
        "-ar",
        str(rate),
        "-ac",
        str(channels),
        "-c:a",
        "flac",
        "-y",
        str(out_flac),
    ]


def build_concat_list(parts: Sequence[Path]) -> str:
    """The concat demuxer's list file for *parts* (pure; quotes escaped)."""
    lines = []
    for part in parts:
        escaped = str(part).replace("\\", "/").replace("'", "'\\''")
        lines.append(f"file '{escaped}'")
    return "\n".join(lines) + "\n"


def build_join_command(
    ffmpeg: str, concat_list: Path, ffmetadata: Path | None, spec: ConversionSpec, out_path: Path
) -> list[str]:
    """Encode the concatenated FLACs with the batch's spec (pure).

    Reuses :func:`build_convert_command` for the whole encode half -- format,
    bit rate, effects, sample-rate fitting -- by describing the concat list as
    the job's source, then splices in the demuxer and the chapter input.
    """
    joined = replace(
        spec,
        extract_from_video=False,
        start_s=0.0,
        end_s=0.0,
        copy_audio=False,
        chapter_source="keep",  # the Join's own chapters arrive as input 1
    )
    job = ConversionJob(source=concat_list, dest=out_path, spec=joined)
    argv = build_convert_command(ffmpeg, job)
    at = argv.index("-i")
    head, tail = argv[:at], argv[at + 2 :]
    inputs = ["-f", "concat", "-safe", "0", "-i", str(concat_list)]
    if ffmetadata is not None:
        inputs += ["-i", str(ffmetadata), "-map_metadata", "1", "-map_chapters", "1"]
    return head + inputs + tail


def run_join(
    ffmpeg: str,
    sources: Sequence[Path],
    spec: ConversionSpec,
    out_path: Path,
    *,
    progress: Callable[[str, int, int], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
    run: Callable[[list[str]], object] | None = None,
) -> Path:
    """Join *sources* into *out_path*. Raises ``RuntimeError`` with a reason.

    Progress is reported inside each step as well as between them, and a stop
    ends the FFmpeg step in progress at once. The joined file is written in the
    temp folder and moved into place only when it is finished, so a stopped or
    failed Join leaves nothing at *out_path*.
    """
    if not sources:
        raise RuntimeError("There is nothing to join.")
    fmt = spec.fmt.strip().lower()
    if fmt in VIDEO_OUTPUT_FORMATS:
        raise RuntimeError("Join makes one sound file; choose an audio format for it.")
    channels = 1 if spec.channels in (Channels.MONO, Channels.LEFT, Channels.RIGHT) else 2
    rate = int(spec.sample_rate or 48000 if fmt in ("opus", "weba") else spec.sample_rate or 44100)
    total = len(sources) + 1

    def step(command: list[str], index: int, text: str, seconds: float) -> None:
        if run is not None:
            _check(run(command))
            return

        def report(fraction: float) -> None:
            if progress is not None:
                progress(text, int((index + fraction) * 1000), total * 1000)

        hooks = LiveHooks(on_fraction=report, cancel=_Stop(cancelled))
        done = run_ffmpeg_live(command, duration_s=seconds, hooks=hooks, timeout_seconds=6 * 3600.0)
        if done.cancelled:
            raise RuntimeError("Join was stopped.")
        _check(done)

    with tempfile.TemporaryDirectory(prefix="quill_join_") as tmp:
        folder = Path(tmp)
        parts: list[Path] = []
        chapters: list[tuple[str, int, int]] = []
        position_ms = 0
        for index, source in enumerate(sources):
            if cancelled is not None and cancelled():
                raise RuntimeError("Join was stopped.")
            text = f"Preparing {index + 1} of {len(sources)}: {source.name}"
            if progress is not None:
                progress(text, index * 1000, total * 1000)
            part = folder / f"part{index:05d}.flac"
            original = probe(source)
            step(
                build_normalize_command(ffmpeg, source, part, rate=rate, channels=channels),
                index,
                text,
                original.duration_s,
            )
            info = probe(part)
            length_ms = int(round(info.duration_s * 1000))
            chapters.append((
                chapter_title_for(source, original.tags),
                position_ms,
                position_ms + length_ms,
            ))
            position_ms += length_ms
            parts.append(part)
        concat = folder / "parts.txt"
        concat.write_text(build_concat_list(parts), encoding="utf-8")
        meta: Path | None = None
        if fmt in CHAPTER_FORMATS:
            meta = folder / "chapters.ffmeta"
            meta.write_text(
                build_ffmetadata(chapters, spec.metadata or AudioMetadata()), encoding="utf-8"
            )
        text = f"Joining {len(sources)} files into {out_path.name}"
        if progress is not None:
            progress(text, len(sources) * 1000, total * 1000)
        if cancelled is not None and cancelled():
            raise RuntimeError("Join was stopped.")
        joined = folder / ("joined" + out_path.suffix)
        step(
            build_join_command(ffmpeg, concat, meta, spec, joined),
            len(sources),
            text,
            position_ms / 1000,
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(joined), str(out_path))
    if meta is None:
        from quill.core.speech.audio_tags_core import Chapter as MarkChapter

        marks = [MarkChapter(i, t, a, b) for i, (t, a, b) in enumerate(chapters)]
        place_chapters(out_path, fmt, marks)
    return out_path


# --------------------------------------------------------------------------- #
# Split by chapters
# --------------------------------------------------------------------------- #

_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe_file_title(title: str, fallback: str) -> str:
    """A chapter title made safe as a Windows file name."""
    cleaned = _UNSAFE.sub(" ", title).strip(" .")
    return re.sub(r"\s+", " ", cleaned)[:120] or fallback


def plan_chapter_split(
    source: Path, chapters: Sequence[Chapter], dest_dir: Path, spec: ConversionSpec
) -> list[ConversionJob]:
    """One job per chapter of *source*, into ``dest_dir/<source name>/`` (pure)."""
    folder = dest_dir / source.stem
    width = max(2, len(str(len(chapters))))
    jobs: list[ConversionJob] = []
    for number, chapter in enumerate(chapters, start=1):
        name = f"{number:0{width}d} - {safe_file_title(chapter.title, f'Chapter {number}')}"
        job_spec = replace(
            spec,
            start_s=chapter.start_s,
            end_s=chapter.end_s,
            extract_from_video=source.suffix.lower() in VIDEO_EXTENSIONS,
            metadata=AudioMetadata(title=chapter.title, track=f"{number}/{len(chapters)}"),
            chapter_source="none",  # each piece is one chapter; it needs no marks inside
        )
        jobs.append(
            ConversionJob(
                source=source, dest=folder / (name + job_spec.output_extension()), spec=job_spec
            )
        )
    return jobs


# --------------------------------------------------------------------------- #


def _run(command: list[str]) -> object:
    from quill.stability.safe_subprocess import run_subprocess_safely

    return run_subprocess_safely(command, timeout_seconds=6 * 3600.0)


class _Stop:
    """``cancelled()`` in the shape :class:`LiveHooks` polls."""

    def __init__(self, cancelled: Callable[[], bool] | None) -> None:
        self._cancelled = cancelled

    def is_cancelled(self) -> bool:
        return self._cancelled is not None and self._cancelled()


def _check(completed: object) -> None:
    if int(getattr(completed, "returncode", 1)) != 0:
        from quill.core.audio.ffmpeg_errors import explain_failure

        raise RuntimeError(explain_failure(str(getattr(completed, "stderr", "") or "")))
