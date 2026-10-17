"""The live time-shift buffer on disk: how big, where, and cleaning up after it.

Pausing and rewinding live radio has always worked by keeping mpv's demuxer
cache behind the play position (:mod:`quill.ui.radio.live_dvr`). Until
2026-10-15 that cache lived in memory and was capped at 50 MiB -- roughly
forty-five minutes of an ordinary 128 kbps stream, much less of a good one.
mpv can keep the same cache in a file instead (``cache-on-disk``), which is
what turns "rewind a few minutes" into "pause the whole programme"
(xradio2.md section 4.3).

Three rules, all enforced here rather than trusted to the engine:

* **It never grows without bound.** The listener chooses a length; this module
  turns it into a byte cap mpv enforces, and halves the cap again when the disk
  is short of room. A buffer that fills a disk is a worse failure than a short
  buffer.
* **It lives in the machine-local cache folder**, never in a synced data
  folder (``paths.machine_local_dir``): hundreds of megabytes of regenerable
  audio re-uploaded to somebody's cloud drive on every station change would be
  a disaster nobody could hear coming.
* **Nothing outlives the session.** Each running engine writes into a folder of
  its own; the engine removes it on exit, and the next start sweeps whatever a
  crash left behind. A file still held open by another running copy cannot be
  deleted on Windows, so the sweep skips it rather than pulling a buffer out
  from under a station somebody else is listening to.

wx-free and strict-typed; the engine (``mpv_radio_engine``) only applies what
:func:`mpv_cache_options` returns.
"""

from __future__ import annotations

import logging
import os
import shutil
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

_log = logging.getLogger(__name__)

#: ``(minutes, label)`` for the Preferences choice. 0 keeps the old in-memory
#: buffer, for a computer whose disk should not be written to while listening.
CHOICES: tuple[tuple[int, str], ...] = (
    (0, "In memory only, about 45 minutes"),
    (30, "30 minutes, on disk"),
    (60, "1 hour, on disk (default)"),
    (120, "2 hours, on disk"),
    (180, "3 hours, on disk"),
    (300, "5 hours, on disk"),
)

DEFAULT_MINUTES = 60

#: The bitrate a byte cap is sized for: 320 kbps, the top of what a station
#: commonly sends. Sizing for the top means the chosen length is a floor --
#: an ordinary 128 kbps station gets well over the hour it was promised.
ASSUMED_BYTES_PER_SECOND = 40_000

#: The in-memory buffer, exactly as it shipped before the disk one.
MEMORY_BYTES = 50 * 1024 * 1024

#: Leave this much of the disk alone whatever the setting says.
_DISK_HEADROOM_BYTES = 1024 * 1024 * 1024

#: The folder under the machine-local cache that holds every session's buffer.
FOLDER_NAME = "radio-timeshift"


@dataclass(frozen=True, slots=True)
class TimeshiftPlan:
    """What the engine should be told: where the buffer lives and how big."""

    on_disk: bool
    back_bytes: int
    #: True when the disk was short of room and the cap came down to fit.
    reduced: bool = False


def normalise_minutes(value: object) -> int:
    """A stored setting as one of :data:`CHOICES`' lengths (pure).

    An unknown or corrupt value becomes the default rather than an error: a
    hand-edited settings file must never stop a station playing.
    """
    try:
        minutes = int(value)  # type: ignore[call-overload]
    except (TypeError, ValueError):
        return DEFAULT_MINUTES
    allowed = [choice for choice, _label in CHOICES]
    return minutes if minutes in allowed else DEFAULT_MINUTES


def choice_index(minutes: int) -> int:
    """The Preferences row for *minutes* (pure)."""
    for index, (choice, _label) in enumerate(CHOICES):
        if choice == normalise_minutes(minutes):
            return index
    return 0


def plan(minutes: int, *, free_bytes: int | None) -> TimeshiftPlan:
    """Turn the chosen length into a byte cap, never past the disk's room (pure).

    *free_bytes* is ``None`` when the free space could not be read; the cap
    then stands as chosen, because mpv itself still enforces it. When the disk
    cannot hold even the old in-memory buffer's worth beyond the headroom, the
    buffer goes back to memory rather than half-working on disk.
    """
    minutes = normalise_minutes(minutes)
    if minutes <= 0:
        return TimeshiftPlan(on_disk=False, back_bytes=MEMORY_BYTES)
    wanted = minutes * 60 * ASSUMED_BYTES_PER_SECOND
    if free_bytes is None:
        return TimeshiftPlan(on_disk=True, back_bytes=wanted)
    room = (free_bytes - _DISK_HEADROOM_BYTES) // 2
    if room < MEMORY_BYTES:
        return TimeshiftPlan(on_disk=False, back_bytes=MEMORY_BYTES, reduced=True)
    if room < wanted:
        return TimeshiftPlan(on_disk=True, back_bytes=room, reduced=True)
    return TimeshiftPlan(on_disk=True, back_bytes=wanted)


def mpv_cache_options(buffer_plan: TimeshiftPlan, cache_dir: Path | None) -> list[tuple[str, str]]:
    """The mpv option/value pairs for *buffer_plan*, in the order to set them (pure).

    ``cache-unlink-files=whendone`` makes mpv delete its own file when it closes
    the stream; the per-session folder and the start-up sweep are for the cases
    where mpv never got the chance.
    """
    options = [
        ("cache", "yes"),
        ("demuxer-max-bytes", str(MEMORY_BYTES)),
        ("demuxer-max-back-bytes", str(buffer_plan.back_bytes)),
    ]
    if buffer_plan.on_disk and cache_dir is not None:
        options += [
            ("cache-dir", str(cache_dir)),
            ("cache-unlink-files", "whendone"),
            ("cache-on-disk", "yes"),
        ]
    else:
        options.append(("cache-on-disk", "no"))
    return options


def default_root() -> Path:
    """Where every session's buffer folder lives: the machine-local cache."""
    from quill.core.paths import machine_local_dir

    return machine_local_dir() / FOLDER_NAME


def new_session_dir(root: Path) -> Path:
    """A folder name for this engine's buffer, unique to this process (pure).

    Not created here: the engine creates it just before each load, so a sweep
    by another copy in between costs nothing.
    """
    return root / f"session-{os.getpid()}-{uuid.uuid4().hex[:8]}"


def free_bytes_at(root: Path) -> int | None:
    """Free space on the disk that holds *root*, or ``None`` when unreadable."""
    probe = root
    while not probe.exists() and probe.parent != probe:
        probe = probe.parent
    try:
        return int(shutil.disk_usage(probe).free)
    except OSError:
        return None


def remove_session(session_dir: Path) -> bool:
    """Delete one session's buffer folder. True when nothing is left of it.

    Best effort, never raising: this runs on the way out of the app, where an
    exception would cost more than a stray file the next start will sweep.
    """
    if not session_dir.exists():
        return True
    shutil.rmtree(session_dir, ignore_errors=True)
    return not session_dir.exists()


def sweep_orphans(root: Path, *, keep: Path | None = None) -> int:
    """Remove what earlier sessions left behind. Returns how many folders went.

    Every entry under *root* except *keep* is a candidate. A file another
    running copy still holds open cannot be deleted on Windows, so that folder
    survives this sweep and goes on a later one -- which is exactly right, since
    its station is still being listened to.
    """
    if not root.is_dir():
        return 0
    removed = 0
    try:
        entries = list(root.iterdir())
    except OSError:
        return 0
    for entry in entries:
        if keep is not None and entry == keep:
            continue
        if entry.is_dir():
            if remove_session(entry):
                removed += 1
            continue
        try:
            entry.unlink()
            removed += 1
        except OSError:
            continue
    return removed


class TimeshiftSession:
    """One engine's buffer: its folder, its cap, and its clean-up.

    Holds an mpv option setter rather than an mpv handle, so the whole life
    cycle -- sweep at start, folder before each load, removal at exit -- is
    testable with a fake that records what it was told.
    """

    def __init__(self, set_option: Callable[[str, str], int], *, root: Path | None = None) -> None:
        self._set_option = set_option
        self._root = root
        self._session_dir: Path | None = None
        self.current_plan = TimeshiftPlan(on_disk=False, back_bytes=MEMORY_BYTES)

    def _resolved_root(self) -> Path:
        if self._root is None:
            self._root = default_root()
        return self._root

    def configure(self, minutes: int | None) -> TimeshiftPlan:
        """Size the buffer for *minutes* (``None`` = the default) and tell mpv.

        The first call also sweeps what earlier sessions left behind -- the
        start-up half of "nothing outlives the session".
        """
        chosen = DEFAULT_MINUTES if minutes is None else normalise_minutes(minutes)
        cache_dir: Path | None = None
        free: int | None = None
        if chosen > 0:
            try:
                root = self._resolved_root()
                if self._session_dir is None:
                    sweep_orphans(root)
                    self._session_dir = new_session_dir(root)
                cache_dir = self._session_dir
                free = free_bytes_at(root)
            except Exception:  # noqa: BLE001 - no folder means the memory buffer, not a failure
                _log.exception("time-shift folder unavailable; buffering in memory")
                cache_dir = None
        buffer_plan = (
            plan(chosen, free_bytes=free) if cache_dir is not None else plan(0, free_bytes=None)
        )
        for name, value in mpv_cache_options(buffer_plan, cache_dir):
            status = self._set_option(name, value)
            if isinstance(status, int) and status < 0:
                _log.warning("mpv refused %s=%s (status %s)", name, value, status)
        self.current_plan = buffer_plan
        return buffer_plan

    @property
    def session_dir(self) -> Path | None:
        return self._session_dir

    def prepare(self) -> None:
        """Make sure this session's folder exists before mpv writes into it."""
        if self._session_dir is None or not self.current_plan.on_disk:
            return
        try:
            self._session_dir.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            # No folder means the memory buffer for this load, not a stream
            # that fails to open because mpv cannot create its cache file.
            _log.warning("time-shift folder unavailable (%s); buffering in memory", error)
            self.current_plan = plan(0, free_bytes=None)
            for name, value in mpv_cache_options(self.current_plan, None):
                self._set_option(name, value)

    def close(self) -> None:
        """Remove this session's buffer folder (idempotent, never raising)."""
        if self._session_dir is not None:
            remove_session(self._session_dir)
