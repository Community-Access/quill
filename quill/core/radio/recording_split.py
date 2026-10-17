"""Cutting a finished recording into one file per song (xradio2 4.8).

A station that broadcasts ICY ``StreamTitle`` metadata says when the song
changes. With **Split the recording at each song change** on (Recording
Settings), the recorder notes the moment of every change while it records
(:mod:`quill.core.radio.recording_song_watch`) and, once the recording is
over, this module cuts the one finished file at those moments into one file
per song, named after the song.

Why after, rather than stopping and restarting the capture at each change:
restarting ffmpeg drops whatever the station sends while the new connection
opens, and reconnecting replays the station's connection advert into every
song. Cutting one continuous file afterwards loses nothing. The cut is a
single ffmpeg pass through the **segment muxer** with ``-c copy``: every
packet of the source lands in exactly one output file, in order, with no
decode and no re-encode, so the songs played back to back are the recording.

The safety contract is the one :mod:`quill.core.radio.recording_join` keeps:
**a failed split must never cost the user their recording.** The songs are
written into a private work folder beside the recording, verified (the right
number of files, none empty, together nearly the size of the source), moved
into place, and only then is the whole recording removed. Any failure -- no
FFmpeg, a non-zero exit, a short output, a file that cannot be moved -- removes
what the split wrote and leaves the recording exactly as it was, with the
reason said out loud.

The honest limit: the moments are when Quill Radio *noticed* the title change,
from a poll every few seconds, and a station often updates its title a little
before or after the music actually changes. A cut can therefore land a few
seconds into the next song or a few seconds before the end of this one. No
audio is lost either way; it is only in the neighbouring file.

wx-free, strict-typed. Subprocess execution goes through
``stability.safe_subprocess``; the tests pass a fake runner.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from quill.core.counted import plural
from quill.core.radio.now_playing import parse_now_playing
from quill.core.speech.ffmpeg import find_ffmpeg
from quill.stability.redaction import format_args_for_log
from quill.stability.safe_subprocess import run_subprocess_safely

logger = logging.getLogger(__name__)

__all__ = [
    "MIN_SONG_SECONDS",
    "SongChange",
    "SplitOutcome",
    "SplitPlan",
    "build_segment_command",
    "describe_split",
    "plan_split",
    "song_file_name",
    "split_recording",
]

#: A song shorter than this is not a song: it is a station flipping its title
#: to an advert marker and back, or two title updates for one change. A change
#: that would leave a piece shorter than this is folded into its neighbour.
MIN_SONG_SECONDS = 20.0

#: The ffmpeg muxer for each container the recorder can write, so the segment
#: muxer is told the format explicitly rather than guessing it from a name.
#: An extension missing here is refused: a recording kept whole is a mild
#: annoyance, a botched split is a lost show.
_MUXER_BY_EXTENSION: dict[str, str] = {
    ".mp3": "mp3",
    ".ogg": "ogg",
    ".opus": "opus",
    ".flac": "flac",
    ".wav": "wav",
    ".aac": "adts",
    ".m4a": "ipod",
    ".ac3": "ac3",
    ".mka": "matroska",
}

#: The songs, together, must come to at least this fraction of the source's
#: size. A stream copy keeps every audio byte; only small per-file headers
#: differ, so anything meaningfully smaller means ffmpeg stopped early.
_MIN_TOTAL_RATIO = 0.9

#: Seconds allowed for the split. A stream copy is bounded by the disk.
_SPLIT_TIMEOUT_SECONDS = 900.0

#: Longest song part of a file name, before the extension. Long enough for
#: "Artist - Title (Extended Mix)", short enough that a deep folder stays
#: inside Windows' path limit.
_MAX_TITLE_CHARS = 80

#: Names Windows reserves for devices; a file called "CON.mp3" cannot exist.
_RESERVED_NAMES = frozenset(
    {"con", "prn", "aux", "nul"}
    | {f"com{index}" for index in range(1, 10)}
    | {f"lpt{index}" for index in range(1, 10)}
)

_UNSAFE = re.compile(r'[\\/:*?"<>|\x00-\x1f]+')

#: Prefix of the private work folder, so a folder left by a crash is
#: recognisable (and the recordings scan, which reads files, never lists it).
_WORK_PREFIX = ".quill-splitting-"


class _Runner(Protocol):
    """Matches ``stability.safe_subprocess.run_subprocess_safely``."""

    def __call__(
        self, args: Sequence[str], *, timeout_seconds: float = ...
    ) -> subprocess.CompletedProcess[str]: ...


@dataclass(frozen=True, slots=True)
class SongChange:
    """One song starting, ``offset`` seconds into the recording."""

    offset: float
    title: str


@dataclass(frozen=True, slots=True)
class SplitPlan:
    """Where to cut and what each piece is called.

    ``cuts`` are the offsets, in seconds, where a new file begins (the first
    file begins at zero and is not listed); ``names`` has one more entry than
    ``cuts``. ``splittable`` is the verdict and ``reason`` says, in plain
    words, why a recording is being kept whole.
    """

    source: Path
    cuts: tuple[float, ...]
    names: tuple[str, ...]
    splittable: bool
    reason: str = ""

    @property
    def song_count(self) -> int:
        return len(self.names)


@dataclass(frozen=True, slots=True)
class SplitOutcome:
    """What happened. ``files`` are the songs when ``split`` is true, else
    just the recording, untouched; ``reason`` explains a refusal or failure."""

    split: bool
    source: Path
    files: tuple[Path, ...]
    reason: str = ""


def song_file_name(title: str) -> str:
    """The song part of a file name, from a raw stream title (pure).

    "Artist - Title" when the stream says both, the title alone otherwise;
    characters no file name may hold are removed, runs of spaces collapse,
    and trailing dots and spaces (which Windows silently drops) go. A title
    with nothing usable left, or one that is a reserved device name, comes
    back as "Untitled song".
    """
    parsed = parse_now_playing(title)
    if parsed.artist and parsed.title:
        text = f"{parsed.artist} - {parsed.title}"
    else:
        text = parsed.title or parsed.raw
    cleaned = re.sub(r"\s+", " ", _UNSAFE.sub(" ", text)).strip()
    cleaned = cleaned[:_MAX_TITLE_CHARS].rstrip(" .")
    if not cleaned or cleaned.casefold() in _RESERVED_NAMES:
        return "Untitled song"
    return cleaned


def plan_split(
    source: Path,
    changes: Sequence[SongChange],
    *,
    duration: float,
    first_title: str = "",
    lead_trim: float = 0.0,
) -> SplitPlan:
    """Decide where to cut *source* and name every piece (pure apart from
    checking the source exists).

    *changes* are offsets measured from when the capture started; *lead_trim*
    is how much the pre-roll guard later cut from the front of the file, so
    every offset moves back by that much. *duration* is how long the capture
    ran, in the same clock. *first_title* is the song already playing when
    the recording began (the first file's name).

    A change too close to the start, to the previous cut or to the end (see
    :data:`MIN_SONG_SECONDS`) is folded into its neighbour; a change to the
    same title as the piece it would end is no change at all.
    """
    extension = source.suffix.lower()
    length = duration - lead_trim

    def refuse(reason: str) -> SplitPlan:
        return SplitPlan(source, (), (), splittable=False, reason=reason)

    if extension not in _MUXER_BY_EXTENSION:
        return refuse(f"{extension or 'that file type'} recordings cannot be split safely")
    if not source.is_file():
        return refuse("the recording could not be found")
    cuts: list[float] = []
    titles: list[str] = [first_title]
    for change in sorted(changes, key=lambda item: item.offset):
        at = change.offset - lead_trim
        previous = cuts[-1] if cuts else 0.0
        if change.title == titles[-1]:
            continue
        if at - previous < MIN_SONG_SECONDS:
            # Too soon after the last cut: the piece it would end is not a
            # song. The newer title wins the piece, because the poll saw it
            # last and it is what was playing when the music settled.
            titles[-1] = change.title
            continue
        if length - at < MIN_SONG_SECONDS:
            break
        cuts.append(at)
        titles.append(change.title)
    if not cuts:
        return refuse("no song change was heard while it recorded")
    stem = source.stem
    numbered = [
        f"{stem} - {index:02d} {song_file_name(title)}{source.suffix}"
        for index, title in enumerate(titles, start=1)
    ]
    return SplitPlan(source, tuple(cuts), tuple(numbered), splittable=True)


def build_segment_command(
    ffmpeg: str,
    source: Path,
    cuts: Sequence[float],
    pattern: Path,
    *,
    muxer: str,
    loglevel: str = "error",
) -> list[str]:
    """The ffmpeg argv that cuts *source* at *cuts* into numbered files (pure).

    ``-f segment`` with ``-segment_times`` writes every packet into exactly
    one numbered output; ``-c copy`` keeps it lossless; ``-map 0:a`` keeps
    only the audio (a cover-art stream has no place in twelve song files);
    ``-reset_timestamps 1`` makes every song start at zero, so a player shows
    its real length.
    """
    return [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        loglevel,
        "-nostdin",
        "-i",
        str(source),
        "-map",
        "0:a",
        "-c",
        "copy",
        "-f",
        "segment",
        "-segment_format",
        muxer,
        "-segment_times",
        ",".join(f"{cut:.3f}" for cut in cuts),
        "-reset_timestamps",
        "1",
        "-y",
        str(pattern),
    ]


def _unique_targets(folder: Path, names: Sequence[str]) -> list[Path]:
    """Final paths for *names*, none of which exists or repeats."""
    taken: set[str] = set()
    targets: list[Path] = []
    for name in names:
        candidate = folder / name
        stem, suffix = candidate.stem, candidate.suffix
        counter = 2
        while candidate.exists() or candidate.name.casefold() in taken:
            candidate = folder / f"{stem} ({counter}){suffix}"
            counter += 1
        taken.add(candidate.name.casefold())
        targets.append(candidate)
    return targets


def _size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _verify(pieces: Sequence[Path], expected: int, source: Path) -> str:
    """An empty string when *pieces* are a plausible split of *source*."""
    if len(pieces) != expected:
        return f"FFmpeg made {plural(len(pieces), 'file')} where {expected} songs were expected"
    if any(_size(piece) == 0 for piece in pieces):
        return "one of the song files came out empty"
    whole = _size(source)
    if whole and sum(_size(piece) for piece in pieces) < whole * _MIN_TOTAL_RATIO:
        return "the song files were much smaller than the recording"
    return ""


def split_recording(
    plan: SplitPlan,
    *,
    ffmpeg: str | None = None,
    runner: _Runner = run_subprocess_safely,
    timeout_seconds: float = _SPLIT_TIMEOUT_SECONDS,
) -> SplitOutcome:
    """Carry out *plan*, or explain why the recording was kept whole.

    Order is the safety contract: cut into a private folder, verify, move
    every song into place, and only then remove the whole recording. If a move
    fails, the songs already moved are removed again and the recording stays.
    """
    source = plan.source
    if not plan.splittable:
        return SplitOutcome(False, source, (source,), plan.reason)
    binary = ffmpeg if ffmpeg is not None else find_ffmpeg()
    if not binary:
        return SplitOutcome(False, source, (source,), "FFmpeg is not available to split it")
    muxer = _MUXER_BY_EXTENSION[source.suffix.lower()]
    try:
        work = Path(tempfile.mkdtemp(prefix=_WORK_PREFIX, dir=source.parent))
    except OSError as exc:
        logger.warning("Could not make a work folder to split a recording: %s", exc)
        return SplitOutcome(False, source, (source,), "there was no room to split it")
    try:
        return _split_into(plan, binary, muxer, work, runner, timeout_seconds)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _split_into(
    plan: SplitPlan,
    binary: str,
    muxer: str,
    work: Path,
    runner: _Runner,
    timeout_seconds: float,
) -> SplitOutcome:
    source = plan.source
    kept = SplitOutcome(False, source, (source,))
    pattern = work / f"song%03d{source.suffix}"
    args = build_segment_command(binary, source, plan.cuts, pattern, muxer=muxer)
    logger.info(
        "Splitting a recording into %d songs: %s", plan.song_count, format_args_for_log(args)
    )
    try:
        completed = runner(args, timeout_seconds=timeout_seconds)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        logger.warning("Splitting a recording failed to run: %s", exc)
        return SplitOutcome(False, source, kept.files, "FFmpeg could not be run to split it")
    if completed.returncode != 0:
        detail = format_args_for_log((completed.stderr or "").strip().splitlines()[-3:])
        logger.warning("Splitting a recording failed (exit %s): %s", completed.returncode, detail)
        return SplitOutcome(False, source, kept.files, "FFmpeg reported an error splitting it")
    pieces = sorted(work.glob(f"song*{source.suffix}"))
    problem = _verify(pieces, plan.song_count, source)
    if problem:
        logger.warning("Split recording rejected: %s", problem)
        return SplitOutcome(False, source, kept.files, problem)
    targets = _unique_targets(source.parent, plan.names)
    moved: list[Path] = []
    for piece, target in zip(pieces, targets, strict=True):
        try:
            os.replace(piece, target)
        except OSError as exc:
            logger.warning("Could not put a split song in place: %s", exc)
            for done in moved:
                try:
                    done.unlink(missing_ok=True)
                except OSError:
                    pass
            return SplitOutcome(False, source, kept.files, "the song files could not be saved")
        moved.append(target)
    try:
        source.unlink()
    except OSError as exc:
        # Every song is safely in place; the whole recording beside them is
        # clutter, not data loss. Said, so nobody wonders about the copy.
        logger.warning("Could not remove the whole recording after splitting: %s", exc)
        return SplitOutcome(True, source, tuple(moved), "the whole recording was also kept")
    logger.info("Split a recording into %d songs.", len(moved))
    return SplitOutcome(True, source, tuple(moved))


def describe_split(outcome: SplitOutcome) -> str:
    """One honest, speakable sentence about *outcome*.

    Every sentence carries a number or a reason (GATE-BULK-COUNT): how many
    songs, and the first and last names so the listener knows where to look;
    or that the recording was kept whole, and why.
    """
    if outcome.split:
        count = len(outcome.files)
        first = outcome.files[0].name
        said = f"Split {outcome.source.name} into {plural(count, 'song')}, starting with {first}."
        if outcome.reason:
            said += f" {outcome.reason[0].upper()}{outcome.reason[1:]}."
        return said
    reason = outcome.reason or "it could not be split"
    return f"Kept {outcome.source.name} as one recording: {reason}."
