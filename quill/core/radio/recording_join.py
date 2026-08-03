"""Stitching an interrupted recording's parts back into one file.

When a stream drops mid-recording the recorder waits, reconnects, and resumes
into a continuation file named ``... (part 2)``, ``... (part 3)``, and so on.
That much already worked -- but nothing ever put the pieces back together, so a
show that dropped twice left the listener with three separate files to find,
order, and play in sequence. For a screen-reader user that is three trips
through a file list to hear one programme.

This module joins them. The join is a *stream copy* through ffmpeg's concat
demuxer (``-f concat`` reading a list file, then ``-c copy``): no decode, no
re-encode, so it is lossless and takes seconds rather than minutes even for a
three-hour capture. The concat **demuxer** is used rather than the ``concat``
filter or the ``concat:`` protocol precisely because it re-muxes properly for
any container QUILL records to, instead of blindly gluing bytes together.

The safety rule this module exists to honour: **a failed join must never cost
the user their recording.** Source parts are deleted only after the joined file
has been verified to exist and be plausibly sized, and the joined result
replaces part one in a single atomic step. If anything at all goes wrong --
mismatched formats, a missing part, ffmpeg unavailable, a non-zero exit, a
short output -- every part is left exactly where it was and the reason is
reported so it can be said out loud.

wx-free, strict-typed. Subprocess execution goes through QUILL's
``stability.safe_subprocess`` helper (redacted arg logging, timeout, no
console window on Windows), never a bare ``subprocess`` call.
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from quill.core.radio.recording_commands import RECORD_FORMATS
from quill.core.speech.ffmpeg import find_ffmpeg
from quill.stability.redaction import format_args_for_log
from quill.stability.safe_subprocess import run_subprocess_safely

logger = logging.getLogger(__name__)

__all__ = [
    "JoinOutcome",
    "JoinPlan",
    "build_concat_command",
    "build_concat_list",
    "describe_join",
    "describe_reconnect",
    "join_recording_parts",
    "plan_join",
]

#: Extensions a stream-copy join is attempted for: the re-encode formats the
#: recorder writes (``RECORD_FORMATS`` minus the ``copy`` pseudo-format) plus
#: every container raw capture can choose from the stream's own codec (see
#: ``recording_commands._RAW_EXT_BY_CODEC``). Anything else is refused rather
#: than guessed at -- an unjoinable recording kept as parts is a mild
#: annoyance; a botched join is a lost show.
_JOINABLE_EXTENSIONS = frozenset(
    {f".{fmt}" for fmt in RECORD_FORMATS if fmt != "copy"}
    | {".aac", ".opus", ".m4a", ".ac3", ".mka"}
)

#: A joined file smaller than this is not a recording, it is a stub or a
#: container header ffmpeg wrote before failing. Never delete parts for it.
_MIN_JOINED_BYTES = 1024

#: A joined file must also be at least this fraction of its parts' combined
#: size. A stream copy preserves essentially every audio byte; only small
#: per-part container headers are dropped, so anything meaningfully smaller
#: means ffmpeg stopped early and the join is not trustworthy.
_MIN_JOINED_SIZE_RATIO = 0.9

#: Seconds allowed for the concat. A stream copy is I/O-bound -- gigabytes per
#: minute on any modern disk -- so this is generous even for a long overnight
#: capture, while still bounding a hung ffmpeg.
_JOIN_TIMEOUT_SECONDS = 900.0

#: Marker inserted into the work file's name while the join is running, so a
#: half-written join is never mistaken for a finished recording (it does not
#: end in a recording extension, so the recordings-folder scan skips it).
_WORK_MARKER = ".joining"


class _Runner(Protocol):
    """The subprocess entry point :func:`join_recording_parts` uses.

    Matches ``stability.safe_subprocess.run_subprocess_safely``; tests pass a
    fake so no real ffmpeg is ever launched.
    """

    def __call__(
        self, args: Sequence[str], *, timeout_seconds: float = ...
    ) -> subprocess.CompletedProcess[str]: ...


@dataclass(frozen=True, slots=True)
class JoinPlan:
    """An ordered, validated plan for concatenating a recording's parts.

    ``parts`` is the base recording followed by its continuations, in the order
    they were captured; ``output`` is where the joined recording belongs (the
    base recording's own path, so the user simply finds the whole show under
    the name they expected). ``joinable`` is the verdict and ``reason`` says,
    in plain words, why a plan cannot be carried out.
    """

    parts: tuple[Path, ...]
    output: Path
    extension: str
    joinable: bool
    reason: str = ""

    @property
    def part_count(self) -> int:
        return len(self.parts)


@dataclass(frozen=True, slots=True)
class JoinOutcome:
    """What actually happened. ``path`` is where the audio is now: the joined
    recording when ``joined`` is true, otherwise the first surviving part.
    ``parts`` is what was on disk going in, so a caller can say how many pieces
    were involved either way, and ``reason`` explains a refusal or failure."""

    joined: bool
    path: Path
    parts: tuple[Path, ...]
    reason: str = ""

    @property
    def part_count(self) -> int:
        return len(self.parts)


def plan_join(paths: Sequence[Path], output: Path | None = None) -> JoinPlan:
    """Validate *paths* as one recording's parts and return the join plan.

    Duplicates are collapsed (a caller may hand the same path twice if a
    reconnect never produced a distinct file) while the given order -- capture
    order -- is preserved, because concatenating a show out of order would be
    worse than not joining it at all.
    """
    ordered: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        if path not in seen:
            seen.add(path)
            ordered.append(path)
    parts = tuple(ordered)
    target = output if output is not None else (parts[0] if parts else Path())
    extension = parts[0].suffix.lower() if parts else ""

    def refuse(reason: str) -> JoinPlan:
        return JoinPlan(parts, target, extension, joinable=False, reason=reason)

    if len(parts) < 2:
        return refuse("there is only one file, so there is nothing to join")
    extensions = sorted({part.suffix.lower() for part in parts})
    if len(extensions) > 1:
        listed = ", ".join(ext or "(no extension)" for ext in extensions)
        return refuse(
            f"the parts are not all the same format ({listed}), and joining them "
            "would need re-encoding"
        )
    if extension not in _JOINABLE_EXTENSIONS:
        return refuse(f"{extension or 'that file type'} recordings cannot be joined safely")
    missing = [part for part in parts if not part.is_file()]
    if missing:
        return refuse(f"{len(missing)} of the {len(parts)} part files could not be found")
    return JoinPlan(parts, target, extension, joinable=True)


def build_concat_list(paths: Sequence[Path]) -> str:
    """The text of an ffmpeg concat-demuxer list file naming *paths* in order.

    Each entry is a single-quoted ``file`` directive with any literal quote
    escaped the way the demuxer's own tokenizer expects. Paths are written with
    forward slashes: ffmpeg accepts them on Windows, and it sidesteps the
    demuxer treating a backslash as an escape character, which is what makes a
    plain ``C:\\Users\\...`` path silently fail to open.
    """
    lines = [f"file '{_escape(_as_list_path(path))}'" for path in paths]
    return "\n".join(lines) + "\n"


def _as_list_path(path: Path) -> str:
    return os.fspath(path).replace("\\", "/")


def _escape(text: str) -> str:
    return text.replace("'", "'\\''")


def build_concat_command(
    ffmpeg: str,
    list_file: Path,
    output: Path,
    *,
    loglevel: str = "error",
) -> list[str]:
    """The ffmpeg argv that concatenates the parts named in *list_file* (pure).

    ``-f concat`` selects the concat *demuxer* and ``-safe 0`` allows the
    absolute paths the list file carries. ``-c copy`` is what makes the join
    lossless and fast: packets are re-muxed, never decoded. ``-nostdin`` stops
    ffmpeg from consuming the host's stdin, and ``-y`` is safe here because the
    output is always a private work file this module just named, never one of
    the recordings.
    """
    return [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        loglevel,
        "-nostdin",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_file),
        "-c",
        "copy",
        "-y",
        str(output),
    ]


def _work_path(plan: JoinPlan) -> Path:
    """A private, non-recording-looking path to join into, beside part one."""
    base = plan.output
    candidate = base.with_name(f"{base.stem}{_WORK_MARKER}{base.suffix}")
    counter = 2
    while candidate.exists():
        candidate = base.with_name(f"{base.stem}{_WORK_MARKER}{counter}{base.suffix}")
        counter += 1
    return candidate


def _sizes(paths: Sequence[Path]) -> list[int]:
    sizes: list[int] = []
    for path in paths:
        try:
            sizes.append(path.stat().st_size)
        except OSError:
            sizes.append(0)
    return sizes


def _verify(work: Path, parts: Sequence[Path]) -> str:
    """An empty string if *work* is a plausible join of *parts*, else why not.

    This is the gate on deleting anything. It is deliberately conservative:
    the cost of a false "bad" is that the user keeps their parts, while the
    cost of a false "good" is a destroyed recording.
    """
    try:
        joined_size = work.stat().st_size
    except OSError:
        return "the joined file was not created"
    if joined_size < _MIN_JOINED_BYTES:
        return "the joined file came out empty"
    expected = sum(_sizes(parts))
    if expected and joined_size < expected * _MIN_JOINED_SIZE_RATIO:
        return "the joined file was much smaller than the parts it came from"
    return ""


def join_recording_parts(
    paths: Sequence[Path],
    *,
    output: Path | None = None,
    ffmpeg: str | None = None,
    runner: _Runner = run_subprocess_safely,
    timeout_seconds: float = _JOIN_TIMEOUT_SECONDS,
) -> JoinOutcome:
    """Join a recording's parts into one file, or explain why it was not done.

    The order of operations is the safety contract: join into a private work
    file, verify it, *then* replace part one with it atomically and only then
    remove the continuations. At no point does the audio exist in fewer than
    one complete form, so an interruption anywhere -- including a crash --
    leaves either the original parts or the finished recording, never neither.
    """
    plan = plan_join(paths, output)
    fallback = plan.parts[0] if plan.parts else (output if output is not None else Path())
    if not plan.joinable:
        return JoinOutcome(False, fallback, plan.parts, plan.reason)
    binary = ffmpeg if ffmpeg is not None else find_ffmpeg()
    if not binary:
        return JoinOutcome(False, fallback, plan.parts, "FFmpeg is not available to join them")
    work = _work_path(plan)
    try:
        with tempfile.TemporaryDirectory(prefix="quill-radio-join-") as scratch:
            list_file = Path(scratch) / "parts.txt"
            list_file.write_text(build_concat_list(plan.parts), encoding="utf-8")
            args = build_concat_command(binary, list_file, work)
            logger.info(
                "Joining %d recording parts: %s",
                plan.part_count,
                format_args_for_log(args),
            )
            completed = runner(args, timeout_seconds=timeout_seconds)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        _discard(work)
        logger.warning("Joining recording parts failed to run: %s", exc)
        return JoinOutcome(False, fallback, plan.parts, "FFmpeg could not be run to join them")
    if completed.returncode != 0:
        _discard(work)
        detail = format_args_for_log((completed.stderr or "").strip().splitlines()[-3:])
        logger.warning("Joining recording parts failed (exit %s): %s", completed.returncode, detail)
        return JoinOutcome(False, fallback, plan.parts, "FFmpeg reported an error joining them")
    problem = _verify(work, plan.parts)
    if problem:
        _discard(work)
        logger.warning("Joined recording rejected: %s", problem)
        return JoinOutcome(False, fallback, plan.parts, problem)
    # Verified. Replace part one atomically, then drop the continuations.
    try:
        os.replace(work, plan.output)
    except OSError as exc:
        _discard(work)
        logger.warning("Could not put the joined recording in place: %s", exc)
        return JoinOutcome(False, fallback, plan.parts, "the joined recording could not be saved")
    for part in plan.parts[1:]:
        if part == plan.output:
            continue
        try:
            part.unlink(missing_ok=True)
        except OSError as exc:
            # The audio is safe -- it is all in the joined file now. A part we
            # cannot remove is clutter, not data loss, so it is logged, not failed.
            logger.warning("Could not remove a joined recording part: %s", exc)
    logger.info("Joined %d recording parts into one file.", plan.part_count)
    return JoinOutcome(True, plan.output, plan.parts)


def _discard(work: Path) -> None:
    """Remove a failed join's work file; its absence is not an error."""
    try:
        work.unlink(missing_ok=True)
    except OSError:
        pass


def describe_join(outcome: JoinOutcome) -> str:
    """One honest, speakable sentence about *outcome* ("" when nothing to say).

    A single-part recording says nothing -- there was never anything to join,
    and announcing it would be noise. Everything else is reported plainly,
    including the failures: the user needs to know they have three files rather
    than discovering it later in the folder.
    """
    count = outcome.part_count
    if count < 2:
        return ""
    if outcome.joined:
        return f"Joined {count} parts into one recording: {outcome.path.name}."
    reason = outcome.reason or "they could not be joined"
    return f"Kept {count} separate parts: {reason}."


def describe_reconnect(attempt: int, maximum: int) -> str:
    """What to say when a dropped recording is about to be resumed (pure).

    Names the part file *and* promises the stitch, so the announcement is the
    whole truth: the user is not left believing they will have to reassemble
    the show themselves.
    """
    return (
        f"Recording lost its stream; reconnecting, attempt {attempt} of {maximum}. "
        "The recording continues in a new part file, and the parts are joined back "
        "into one recording when it finishes."
    )
