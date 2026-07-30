"""Headless command-line front end for the audio converter (#1255 CLI).

``python -m quill convert INPUT... --to FORMAT [options]`` drives the exact same
wx-free engine the Audio Studio dialog uses (:mod:`quill.core.audio.convert` +
:mod:`~quill.core.audio.presets` + :mod:`~quill.core.audio.dsp`), so a script or
a power user gets format conversion, presets, the Advanced DSP catalog, a mixed
file/folder queue, conflict policy, multi-worker batching and a dry-run without
opening the UI.

Design: everything that decides *what* to do is a pure function returning data
(:func:`resolve_queue`, :func:`resolve_spec`); the only side effects live in
:func:`run_cli`, which takes an injectable ``emit`` sink and ``ffmpeg_finder`` so
the whole flow is unit-testable without spawning ffmpeg or writing to stdout.
"""

from __future__ import annotations

import glob as _glob
import sys
from argparse import ArgumentParser, Namespace
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from quill.core.audio.convert import (
    Channels,
    ConversionJob,
    ConversionSpec,
    OnExisting,
    SingleJobRunner,
    available_output_formats,
    default_destination,
    plan_jobs,
    run_conversion_batch,
)
from quill.core.audio.dsp import DspOptions, build_dsp_filters
from quill.core.audio.presets import DEFAULT_PRESET_ID, preset_choices, preset_spec

Emit = Callable[[str], None]

_PROG = "quill convert"


def _safe_print(text: str) -> None:
    """Print a line without ever raising on a legacy (cp1252) Windows console.

    Preset labels and summaries carry Unicode (em-dashes, arrows); a strict
    console encoding would otherwise crash the CLI mid-listing with
    ``UnicodeEncodeError``. Fall back to a replace-encoded rendering instead of
    dying — a degraded character beats a broken command.
    """
    try:
        print(text)
    except UnicodeEncodeError:
        enc = (sys.stdout.encoding or "utf-8") if sys.stdout else "utf-8"
        print(text.encode(enc, "replace").decode(enc))


def build_parser() -> ArgumentParser:
    """The ``quill convert`` argument parser (also used to render ``--help``)."""
    parser = ArgumentParser(
        prog=_PROG,
        description="Convert audio (and extract audio from video) files, offline.",
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help="Files, folders, or glob patterns to convert. Folders mirror their tree.",
    )
    parser.add_argument("--to", "--format", dest="to", default="", help="Output format, e.g. mp3.")
    parser.add_argument(
        "--preset",
        default=DEFAULT_PRESET_ID,
        help="Preset id supplying the base recipe (see --list-presets).",
    )
    parser.add_argument("--out", "--dest", dest="out", default="", help="Output folder.")
    parser.add_argument(
        "--recurse",
        action="store_true",
        help="Descend into sub-folders when an input is a folder.",
    )
    parser.add_argument(
        "--flatten",
        action="store_true",
        help="Write every output straight into --out (do not mirror the source tree).",
    )
    parser.add_argument(
        "--on-existing",
        choices=[p.value for p in OnExisting],
        default=OnExisting.RENAME.value,
        help="What to do when an output already exists (default: rename/auto-number).",
    )
    parser.add_argument(
        "--workers", type=int, default=0, help="Parallel workers (0 = auto: CPUs - 1)."
    )

    quality = parser.add_argument_group("quality overrides (override the preset)")
    quality.add_argument("--bitrate", type=int, metavar="KBPS", help="CBR bitrate in kbps.")
    quality.add_argument("--sample-rate", type=int, metavar="HZ", help="Output sample rate.")
    quality.add_argument("--channels", choices=[c.value for c in Channels], help="Channel layout.")
    quality.add_argument("--bit-depth", type=int, choices=[16, 24, 32], help="PCM/FLAC bit depth.")

    dsp = parser.add_argument_group("processing (Advanced DSP catalog)")
    dsp.add_argument(
        "--loudness", choices=["audiobook", "podcast"], help="Loudness-normalize to a target."
    )
    dsp.add_argument("--gain", type=float, default=0.0, metavar="DB", help="Gain in dB.")
    dsp.add_argument("--high-pass", action="store_true", help="Remove low-frequency rumble.")
    dsp.add_argument("--trim-silence", action="store_true", help="Trim leading/trailing silence.")
    dsp.add_argument(
        "--speed", type=float, default=1.0, metavar="X", help="Tempo multiplier (no pitch shift)."
    )
    dsp.add_argument("--compress", action="store_true", help="Compress dynamics.")
    dsp.add_argument("--level", action="store_true", help="Level volume across the file.")
    dsp.add_argument("--fade-in", type=float, default=0.0, metavar="SEC", help="Fade-in seconds.")
    dsp.add_argument("--fade-out", type=float, default=0.0, metavar="SEC", help="Fade-out seconds.")

    parser.add_argument("--dry-run", action="store_true", help="Show the plan; convert nothing.")
    parser.add_argument("--list-presets", action="store_true", help="List presets and exit.")
    parser.add_argument("--list-formats", action="store_true", help="List output formats and exit.")
    return parser


def resolve_queue(raw_inputs: list[str]) -> tuple[list[tuple[Path, Path | None]], list[str]]:
    """Expand raw CLI inputs into a ``(queue, unmatched)`` pair (pure).

    Each input is a file, a folder (mirrored: ``root == itself``), or a glob
    pattern (``**`` recursion supported). Patterns that match nothing are
    returned in *unmatched* so the caller can warn instead of silently dropping.
    """
    queue: list[tuple[Path, Path | None]] = []
    unmatched: list[str] = []
    for raw in raw_inputs:
        direct = Path(raw)
        if direct.exists():
            queue.append((direct, direct if direct.is_dir() else None))
            continue
        matches = sorted(_glob.glob(raw, recursive=True))
        if not matches:
            unmatched.append(raw)
            continue
        for match in matches:
            path = Path(match)
            queue.append((path, path if path.is_dir() else None))
    return queue, unmatched


def resolve_spec(ns: Namespace) -> ConversionSpec:
    """Build the :class:`ConversionSpec` from parsed args (pure).

    The preset supplies the base recipe; ``--to`` and the quality/DSP options
    override only what the user set (unset numeric overrides keep the preset's
    value), mirroring the dialog's Advanced semantics.
    """
    base = preset_spec(ns.preset)
    fmt = (ns.to or base.fmt).strip().lower()
    dsp = DspOptions(
        loudness=ns.loudness or "",
        gain_db=ns.gain,
        high_pass=ns.high_pass,
        trim_silence=ns.trim_silence,
        tempo=ns.speed,
        compressor=ns.compress,
        leveler=ns.level,
        fade_in_s=ns.fade_in,
        fade_out_s=ns.fade_out,
    )
    dsp_filters = build_dsp_filters(dsp)
    return replace(
        base,
        fmt=fmt,
        bitrate_kbps=ns.bitrate if ns.bitrate is not None else base.bitrate_kbps,
        sample_rate=ns.sample_rate if ns.sample_rate is not None else base.sample_rate,
        channels=Channels(ns.channels) if ns.channels else base.channels,
        bit_depth=ns.bit_depth if ns.bit_depth is not None else base.bit_depth,
        filters=dsp_filters if dsp_filters else base.filters,
    )


def run_cli(
    argv: list[str],
    *,
    emit: Emit = _safe_print,
    ffmpeg_finder: Callable[[], str | None] | None = None,
    single_runner: SingleJobRunner | None = None,
) -> int:
    """Parse *argv*, run the conversion, and return a process exit code.

    ``0`` success, ``1`` a runnable request that produced no output or had a
    failed job, ``2`` a setup problem (no ffmpeg, no inputs). ``emit`` and
    ``ffmpeg_finder``/``single_runner`` are injectable so the whole flow runs
    headless in tests without ffmpeg or real stdout.
    """
    ns = build_parser().parse_args(argv)

    if ns.list_presets:
        for pid, label in preset_choices():
            emit(f"{pid}\t{label}")
        return 0

    finder = ffmpeg_finder or _default_ffmpeg_finder
    ffmpeg = finder()

    if ns.list_formats:
        for fmt in available_output_formats(ffmpeg):
            emit(fmt)
        return 0

    if not ffmpeg:
        emit("FFmpeg was not found. Install it, or use the app's Download Optional Components.")
        return 2

    queue, unmatched = resolve_queue(ns.inputs)
    for miss in unmatched:
        emit(f"warning: no files matched: {miss}")
    if not queue:
        emit("Nothing to convert: no input files were given or matched.")
        return 2

    dest = Path(ns.out) if ns.out else default_destination(queue[0][0])
    spec = resolve_spec(ns)
    jobs, skipped = plan_jobs(
        queue,
        dest,
        spec,
        recurse=ns.recurse,
        flatten=ns.flatten,
        on_existing=OnExisting(ns.on_existing),
    )

    if ns.dry_run:
        emit(f"Would convert {len(jobs)} file(s) into {dest}:")
        for job in jobs:
            emit(f"  {job.source}  ->  {job.dest}")
        if skipped:
            emit(f"{len(skipped)} input(s) skipped by the '{ns.on_existing}' policy.")
        return 0

    if not jobs:
        emit("Nothing to convert after planning (all inputs skipped or empty).")
        return 1

    total = len(jobs)

    def on_progress(done: int, total_jobs: int, job: ConversionJob) -> None:
        pct = int(done * 100 / total_jobs) if total_jobs else 100
        emit(f"[{done}/{total_jobs}] {pct}%  {job.source.name}")

    result = run_conversion_batch(
        ffmpeg,
        jobs,
        workers=ns.workers,
        on_progress=on_progress,
        single_runner=single_runner,
    )
    emit(result.summary(total))
    return 0 if not result.failed else 1


def _default_ffmpeg_finder() -> str | None:
    from quill.core.speech.ffmpeg import find_ffmpeg

    return find_ffmpeg()
