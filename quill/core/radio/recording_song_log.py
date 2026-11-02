"""The songs a finished recording heard, kept beside it, and splitting it later.

The recorder notes every ICY title change while it records
(:mod:`quill.core.radio.recording_song_watch`). With **Split the recording at
each song change** on, it cuts the file into songs the moment the recording
ends. With it off, those moments used to be thrown away -- so a listener who
recorded a show and only later wanted it in songs had nothing to cut at.

Now the moments are kept in a small file beside the recording,
``<recording>.songs.json``, and **Split into Songs** in the Recordings window
reads it. That split never touches the recording: the songs go into a folder
beside it, ``<recording name> songs``, each named "Artist - Title" (the title
alone when the station gives no artist), and the whole recording stays where
it was. The cut itself is :func:`quill.core.radio.recording_split.split_recording`
-- one lossless ffmpeg stream copy, verified before anything is moved into
place -- so this module only decides *what* to cut and says how it went.

The log is plain JSON of offsets measured from the start of the **file** (the
pre-roll trim is already taken off), so it stays right however long ago the
recording was made. The recordings scan only lists audio files, so the log
never shows up as a recording; deleting a recording takes its log with it
(:func:`companions`).

wx-free, strict-typed. The tests pass a fake ffmpeg runner.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from quill.core.counted import plural
from quill.core.radio.recording_split import (
    SongChange,
    SplitOutcome,
    SplitPlan,
    plan_split,
    song_file_name,
    split_recording,
)
from quill.core.storage import read_json, write_json_atomic

logger = logging.getLogger(__name__)

__all__ = [
    "NO_SONG_CHANGES",
    "SIDECAR_SUFFIX",
    "SongLog",
    "companions",
    "describe_splits",
    "load_song_log",
    "plan_finished",
    "save_song_log",
    "sidecar_path",
    "songs_folder",
    "split_finished",
]

#: What the song log beside a recording is called, after the recording's name.
SIDECAR_SUFFIX = ".songs.json"

#: The reason given for a recording with nothing to cut at.
NO_SONG_CHANGES = "no song changes were recorded while it was made"

#: Bumped if the shape of the file ever changes; an unknown version is ignored.
_VERSION = 1


@dataclass(frozen=True, slots=True)
class SongLog:
    """The songs one recording heard: offsets from the start of the file."""

    first_title: str
    changes: tuple[SongChange, ...]
    duration: float
    interrupted: bool = False


def sidecar_path(recording: Path) -> Path:
    """``Show.mp3`` -> ``Show.mp3.songs.json``, beside it."""
    return recording.with_name(recording.name + SIDECAR_SUFFIX)


def songs_folder(recording: Path) -> Path:
    """Where a split of *recording* puts its songs: ``Show songs``, beside it."""
    return recording.with_name(f"{recording.stem} songs")


def companions(recording: Path) -> list[Path]:
    """The files that belong to *recording* and go wherever it goes (its
    song log), when they exist."""
    log = sidecar_path(recording)
    return [log] if log.is_file() else []


def save_song_log(
    recording: Path,
    *,
    first_title: str,
    changes: Sequence[SongChange],
    duration: float,
    lead_trim: float = 0.0,
    interrupted: bool = False,
) -> bool:
    """Keep what *recording* heard beside it. Returns whether a log was written.

    Nothing is written when there is nothing worth keeping: no change heard
    and the stream never dropped. *changes* and *duration* are on the
    capture's clock; *lead_trim* (what the pre-roll guard cut from the front)
    is taken off here, once, so the log is in the file's own time.
    """
    if not changes and not interrupted:
        return False
    data: dict[str, Any] = {
        "version": _VERSION,
        "first_title": first_title,
        "duration": round(max(0.0, duration - lead_trim), 3),
        "interrupted": interrupted,
        "changes": [
            {"offset": round(change.offset - lead_trim, 3), "title": change.title}
            for change in changes
            if change.offset - lead_trim > 0
        ],
    }
    try:
        write_json_atomic(sidecar_path(recording), data)
    except OSError as exc:
        # The recording is safe; only the chance to split it later is lost.
        logger.warning("Could not keep the song changes beside a recording: %s", exc)
        return False
    return True


def load_song_log(recording: Path) -> SongLog | None:
    """The log beside *recording*, or ``None`` when there is none to use."""
    data = read_json(sidecar_path(recording), None)
    if not isinstance(data, dict) or data.get("version") != _VERSION:
        return None
    changes: list[SongChange] = []
    for item in data.get("changes") or []:
        if not isinstance(item, dict):
            continue
        try:
            changes.append(SongChange(float(item["offset"]), str(item["title"])))
        except (KeyError, TypeError, ValueError):
            continue
    try:
        duration = float(data.get("duration") or 0.0)
    except (TypeError, ValueError):
        duration = 0.0
    return SongLog(
        first_title=str(data.get("first_title") or ""),
        changes=tuple(changes),
        duration=duration,
        interrupted=bool(data.get("interrupted")),
    )


def plan_finished(recording: Path, log: SongLog | None) -> SplitPlan:
    """Where to cut a finished *recording*, its songs named "Artist - Title".

    A recording with no log, or a log with no change in it, is refused with
    :data:`NO_SONG_CHANGES`; one whose stream dropped is refused because its
    moments no longer line up with the audio.
    """
    if log is None or not log.changes:
        return SplitPlan(recording, (), (), splittable=False, reason=NO_SONG_CHANGES)
    if log.interrupted:
        return SplitPlan(
            recording,
            (),
            (),
            splittable=False,
            reason="the stream dropped while it recorded, so the song changes "
            "no longer line up with the audio",
        )
    plan = plan_split(recording, log.changes, duration=log.duration, first_title=log.first_title)
    if not plan.splittable:
        return plan
    names = tuple(f"{song_file_name(title)}{recording.suffix}" for title in plan.titles)
    return replace(plan, names=names)


def split_finished(recording: Path, **split_options: Any) -> SplitOutcome:
    """Split a finished *recording* into its songs, keeping it whole.

    *split_options* go to :func:`split_recording` (``ffmpeg``, ``runner``);
    the songs always go to :func:`songs_folder` and the recording is kept.
    """
    plan = plan_finished(recording, load_song_log(recording))
    return split_recording(
        plan, destination=songs_folder(recording), keep_source=True, **split_options
    )


def describe_splits(outcomes: Sequence[SplitOutcome]) -> str:
    """The one sentence said when a split of one or more recordings is over.

    Every clause carries a number or a reason (GATE-BULK-COUNT). One
    recording names itself and the folder its songs went to; several are
    counted, with the ones that had nothing to cut at counted apart from the
    ones that failed, because the first is a fact and the second a problem.
    """
    if not outcomes:
        return "No recording to split."
    if len(outcomes) == 1:
        outcome = outcomes[0]
        name = outcome.source.name
        if outcome.split:
            pieces = plural(len(outcome.files), "song")
            return f"Split {name} into {pieces}, in the folder {outcome.files[0].parent.name}."
        if outcome.reason == NO_SONG_CHANGES:
            return f"{name} has no song changes recorded, so there is nothing to split it at."
        return f"Did not split {name}: {outcome.reason or 'it could not be split'}."
    done = [outcome for outcome in outcomes if outcome.split]
    bare = [o for o in outcomes if not o.split and o.reason == NO_SONG_CHANGES]
    failed = len(outcomes) - len(done) - len(bare)
    songs = sum(len(outcome.files) for outcome in done)
    total = plural(len(outcomes), "recording")
    said = f"Split {len(done)} of {total} into {plural(songs, 'song')}."
    if bare:
        verb = "has" if len(bare) == 1 else "have"
        said += f" {len(bare)} {verb} no song changes recorded."
    if failed:
        said += f" {failed} could not be split."
    return said
