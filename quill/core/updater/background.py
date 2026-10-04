"""Background downloads on Beta and Dev, and when they wait (owner decision 11).

On Beta and Dev every app fetches a new version quietly, as soon as an
automatic check finds one, so that "Install now" is instant when it is
offered. It **never installs** without asking. Stable is unchanged.

An automatic download waits, and says why in Update History, when:

* the connection is **metered** (:func:`quill.core.net_metered.connection_cost`;
  "unknown" counts as unmetered, as everywhere in the family);
* it is **Quiet Hours** (:mod:`quill.core.quiet_hours`, the family's shared
  window) -- nothing that was not asked for happens in the night;
* **Quill Radio is recording** -- a download competing for the line could
  cost a recording, and that is the one thing the listener cannot get back.

A download somebody asks for (the update dialog's Update button) is never held.

wx-free and strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from quill.core.updater.channels import STABLE, ChannelState

__all__ = [
    "BackgroundGate",
    "Conditions",
    "background_gate",
    "read_conditions",
]

HELD_METERED = "Held back because you are on a metered connection."
HELD_QUIET = "Held back during Quiet Hours."
HELD_RECORDING = "Held back while Quill Radio is recording."

#: A recording marker with no scheduled end counts as live for this long.
_OPEN_ENDED = timedelta(hours=12)


@dataclass(frozen=True)
class Conditions:
    metered: bool = False
    quiet: bool = False
    recording: bool = False


@dataclass(frozen=True)
class BackgroundGate:
    #: Download now, in the background.
    download: bool
    #: Why not, for Update History; empty when downloading or on Stable.
    reason: str = ""
    #: Whether the app may still show its update dialog on this silent check
    #: (not during Quiet Hours or a recording: nothing pops up then).
    may_show: bool = True


def background_gate(state: ChannelState, conditions: Conditions) -> BackgroundGate:
    """What an automatic check that found *a newer build* may do now."""
    if state.channel == STABLE or (state.pending_return and not state.keep_beta_while_waiting):
        return BackgroundGate(download=False)
    if conditions.recording:
        return BackgroundGate(False, HELD_RECORDING, may_show=False)
    if conditions.quiet:
        return BackgroundGate(False, HELD_QUIET, may_show=False)
    if conditions.metered:
        return BackgroundGate(False, HELD_METERED)
    return BackgroundGate(download=True)


def _radio_recording(data_dir: Path, now: datetime) -> bool:
    try:
        from quill.core.radio.recording_resume import load_markers, remaining_minutes
    except Exception:  # noqa: BLE001 - no Radio code in this build: nothing records
        return False
    for marker in load_markers(data_dir):
        if remaining_minutes(marker, now) > 0:
            return True
        started = marker.started
        if marker.end is None and started is not None:
            began = started if started.tzinfo is not None else started.astimezone()
            if now.astimezone() - began < _OPEN_ENDED:
                return True
    return False


def read_conditions(*, now: datetime | None = None) -> Conditions:
    """This computer's conditions right now. Never raises; unknown means "go"."""
    moment = now or datetime.now().astimezone()
    metered = quiet = recording = False
    try:
        from quill.core.net_metered import METERED, connection_cost

        metered = connection_cost() == METERED
    except Exception:  # noqa: BLE001
        metered = False
    try:
        from quill.core.paths import app_data_dir

        data = app_data_dir()
    except Exception:  # noqa: BLE001
        return Conditions(metered=metered)
    try:
        from quill.core.quiet_hours import Kind, load_quiet_hours, silences

        quiet = silences(load_quiet_hours(data), Kind.BACKGROUND, moment.time())
    except Exception:  # noqa: BLE001
        quiet = False
    try:
        recording = _radio_recording(data, moment)
    except Exception:  # noqa: BLE001
        recording = False
    return Conditions(metered=metered, quiet=quiet, recording=recording)
