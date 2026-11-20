"""How a recording ended, and whether it recorded anything.

Extracted from ``recording.py`` under GATE-11 (extract, never rebaseline), and
it is a real concern rather than a slice: everything here answers one question
-- *what happened to this capture* -- from the only evidence available once
ffmpeg has exited, which is its last few stderr lines and the size of the file
it left behind.

Three verdicts, in the order they are asked:

* **Was the failure fatal or transient** (:func:`is_fatal`), which decides
  whether a reconnect is worth an attempt. A 404, a 410, a 451 or a full disk is
  gone for good; a 5xx, a timeout, a bare EOF and -- crucially -- a 403 from an
  expired CDN token are ordinary and recoverable.
* **Did ffmpeg get going again** (:func:`is_recovery`), so a transient error it
  already rode out cannot poison the verdict on an unrelated drop much later.
* **Did anything actually get recorded** (:func:`captured_nothing`), and if not,
  :func:`empty_capture_reason` puts it in words.

That last one exists because of a real report (John, 2026-08-14): pressing
Record on a station that would not stay connected gave no confirmation that a
recording had started or stopped, and left an empty recordings folder. A
recording that captured nothing must say so -- announcing "Recording saved" over
a zero-byte file, or saying nothing at all, sends somebody looking in a folder
for audio that does not exist.

wx-free, strict-typed.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
from pathlib import Path

from quill.stability.redaction import format_args_for_log

logger = logging.getLogger(__name__)

#: ffmpeg stderr markers that mean the failure is *fatal* -- the stream is gone
#: for good, or the disk is full -- rather than a transient drop worth spending a
#: reconnect attempt on. Only genuinely-terminal HTTP codes count: 404 Not Found,
#: 410 Gone, 451 Unavailable. A 5xx, a network timeout, a bare EOF, and crucially
#: a transient 403 Forbidden (an expired or rotating CDN token -- common, and
#: recoverable) or a 408/409 are treated as transient and DO reconnect, so a
#: hiccup no longer cuts a recording short after a minute.
FATAL_STDERR_RE = re.compile(
    r"(?i)(no space left|disk full|enospc|read-only|"
    r"server returned 4(?:04|10|51)|http error 4(?:04|10|51)|http/[0-9.]+ 4(?:04|10|51)|"
    r"404 not found|410 gone|451 unavailable)"
)

#: Evidence in ffmpeg's stderr that it (re)connected and is making forward
#: progress -- an ``Opening '...' for reading`` reconnect line, or a progress
#: stat line. Any earlier error was recovered from, so the recent-stderr tail is
#: cleared on this signal.
RECOVERY_STDERR_RE = re.compile(r"(?i)(opening .+ for reading|\btime=\d)")

#: Below this, a "recording" captured nothing worth keeping. ffmpeg writes a
#: container header before a single audio frame arrives, so "the file exists" is
#: not evidence that anything was recorded; a few kilobytes is. Deliberately
#: generous -- a genuine one-second capture at any bitrate clears it, and the
#: opposite failure (deleting audio somebody wanted) is far worse than keeping a
#: very short file.
MIN_USEFUL_CAPTURE_BYTES = 8_192

#: Why a capture produced nothing, keyed off ffmpeg's own stderr. Plain words:
#: the listener needs to know whether to try again or give up, and "the station
#: refused the connection" answers that where an exit code does not.
_EMPTY_CAPTURE_REASONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?i)(403 forbidden|server returned 403)"), "the station refused the connection"),
    (re.compile(r"(?i)(404 not found|410 gone|451)"), "that stream address is no longer there"),
    (re.compile(r"(?i)(no space left|disk full|enospc)"), "the disk is full"),
    (re.compile(r"(?i)(read-only|permission denied)"), "that folder could not be written to"),
    (re.compile(r"(?i)(connection|timed out|timeout|refused|reset)"), "the connection failed"),
    (
        re.compile(r"(?i)(invalid data|could not find codec|does not contain)"),
        "the stream was in a form it could not record",
    ),
)


def is_fatal(stderr_tail: list[str]) -> bool:
    """Whether these last lines describe a failure no reconnect can fix."""
    return any(FATAL_STDERR_RE.search(line) for line in stderr_tail)


def is_recovery(line: str) -> bool:
    """Whether this line is ffmpeg reporting that it is making progress again."""
    return bool(RECOVERY_STDERR_RE.search(line))


def captured_nothing(path: Path) -> bool:
    """Whether *path* holds too little to be a recording.

    A missing file counts, and so does a container header with no audio behind
    it: ffmpeg writes the header the moment it opens the output, so existence
    alone has never been evidence that anything was captured.
    """
    try:
        return path.stat().st_size < MIN_USEFUL_CAPTURE_BYTES
    except OSError:
        return True


def empty_capture_reason(stderr_tail: list[str]) -> str:
    """Why a capture produced nothing, in words, from ffmpeg's own last lines.

    Falls back to an honest admission rather than a guess: "it stopped before
    anything could be recorded" is a usable answer, and an invented cause is not.
    """
    return reason_from_stderr(stderr_tail) or "the stream stopped before anything could be recorded"


def reason_from_stderr(stderr_tail: list[str]) -> str:
    """The plain-words cause ffmpeg's last lines name, or ``""`` if none does.

    Shared by the empty-capture verdict and the end-of-recording report
    (``recording_report``), so a recording that ended early and one that
    captured nothing describe the same cause in the same words.
    """
    for line in reversed(stderr_tail):
        for pattern, reason in _EMPTY_CAPTURE_REASONS:
            if pattern.search(line):
                return reason
    return ""


def discard_empty_capture(path: Path) -> None:
    """Remove the empty file a failed capture left behind, if it left one.

    Best-effort by design: failing to delete it is not worth an error on top of
    the failure already being reported, and a stray zero-byte file is a far
    smaller problem than the exception would be.
    """
    try:
        path.unlink()
    except OSError:
        logger.debug("could not remove empty capture %s", format_args_for_log([str(path)]))


def _free_names(dst: Path) -> list[Path]:
    """*dst*, then ``"name (2).ext"`` .. ``"name (999).ext"`` beside it.

    The same numbering ``recording_commands.uniquify`` uses, so a recovered file
    and a fresh recording that collide end up named the same way.
    """
    return [dst, *(dst.parent / f"{dst.stem} ({n}){dst.suffix}" for n in range(2, 1000))]


def _move_no_clobber(src: Path, target: Path) -> None:
    """Move *src* to *target*, failing with ``FileExistsError`` if *target* exists.

    Never replaces anything. A hard link claims the name atomically on the same
    volume (``os.link`` refuses an existing name); a cross-volume move, or a
    file system without hard links, copies into a file opened with exclusive
    create (``"xb"``), so a file that appears between the check and the copy is
    still never overwritten. A copy that fails part-way removes only the file it
    created itself and re-raises, leaving *src* untouched.
    """
    try:
        os.link(src, target)
    except FileExistsError:
        raise
    except OSError:
        created = False
        try:
            with src.open("rb") as reader, target.open("xb") as writer:
                created = True
                shutil.copyfileobj(reader, writer)
            shutil.copystat(src, target)
            if target.stat().st_size != src.stat().st_size:
                raise OSError(f"copy of {src.name} is incomplete") from None
        except FileExistsError:
            raise
        except OSError:
            if created:
                target.unlink(missing_ok=True)
            raise
    try:
        src.unlink()
    except OSError as exc:
        # Both names now hold the recording; keeping a duplicate is the safe
        # failure (the reverse would lose it).
        logger.warning(
            "Moved recording to %s but could not remove the temp copy (%s).",
            format_args_for_log([str(target)]),
            exc,
        )


def finalize_move(src: Path, dst: Path) -> Path:
    """Move a finished recording from the temp dir *src* to its home *dst* (#5).

    Returns where the file actually ended up. **Never overwrites**: if *dst*
    already holds a file -- an earlier recording with the same name, or one
    that appeared while this move was running -- the recording lands beside it
    as ``"name (2).ext"`` and both are kept byte for byte. Startup crash recovery
    (``recording_resume.reconcile_temp_strays``) relies on this; it used to
    replace a kept recording with a same-name orphan (plan.md, Windows Radio
    recording review).

    A same-volume move is a hard link plus an unlink; a cross-volume move copies
    with exclusive create, then deletes the source. If the move fails the file
    is left in the temp dir (still playable) and *src* is returned, so a
    finished recording is never lost to a move error, and a partial copy is
    never left at the destination.
    """
    if not src.exists():
        return dst
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.warning(
            "Could not create %s (%s); left the recording in the temp folder.",
            format_args_for_log([str(dst.parent)]),
            exc,
        )
        return src
    for target in _free_names(dst):
        if target.exists() or target == src:
            continue
        try:
            _move_no_clobber(src, target)
            return target
        except FileExistsError:
            continue  # somebody took the name since we looked; try the next one
        except OSError as exc:
            logger.warning(
                "Could not move recording to %s (%s); left it in the temp folder.",
                format_args_for_log([str(target)]),
                exc,
            )
            return src
    logger.warning(
        "No free name for %s; left the recording in the temp folder.",
        format_args_for_log([str(dst)]),
    )
    return src
