"""An unfinished demonstration recording, named the way the person knows it (FUX-05).

Recovery used to name each unfinished recording by its hidden work folder,
``...\\.studio-recording-3f9a...``: a path nobody chose and nobody can recognise.
This reads the folder's ``session.json`` for what the recording *is* -- the
name it will be saved under, when it was started, how much was recorded -- and
whether an earlier recovery already saved it (its check failed, so the pieces
were kept), so recovering it again cannot make a " (2)" copy.

wx-free and strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from quill.core.demo_recording import DemoRecordingError
from quill.core.demo_recording_session import SessionRecord

__all__ = ["Unfinished", "describe_unfinished", "length_words", "spoken_when"]


@dataclass(frozen=True, slots=True)
class Unfinished:
    """One hidden work folder, described."""

    work: Path
    #: The name it is saved under, without the folder: "Product demo".
    name: str
    #: Where the finished file goes.
    output: Path | None
    started: datetime | None
    #: Seconds recorded in closed segments; 0 when not known.
    seconds: float
    #: A file an earlier recovery already wrote (its check failed), if it still exists.
    saved: Path | None = None
    #: Nothing usable was recorded (an earlier recovery found no pieces).
    empty: bool = False

    @property
    def label(self) -> str:
        """``Product demo, started Friday 4:58 PM, 12 minutes recorded``."""
        parts = [self.name]
        if self.started is not None:
            parts.append(f"started {spoken_when(self.started)}")
        if self.saved is not None:
            parts.append(f"already saved as {self.saved.name}, but its check found problems")
        elif self.empty:
            parts.append("nothing usable was recorded")
        elif self.seconds >= 1:
            parts.append(f"{length_words(self.seconds)} recorded")
        return ", ".join(parts)

    @property
    def needs_finishing(self) -> bool:
        """Whether Finish would make something new (not a duplicate, not nothing)."""
        return self.saved is None and not self.empty


def spoken_when(when: datetime) -> str:
    """``Friday 4:58 PM``, the way Quill Radio names a recording."""
    hour = when.hour % 12 or 12
    return f"{when:%A} {hour}:{when:%M} {'AM' if when.hour < 12 else 'PM'}"


def length_words(seconds: float) -> str:
    """``1 hour 4 minutes``, ``12 minutes``, ``under a minute``."""
    minutes = int(max(0.0, seconds)) // 60
    if minutes < 1:
        return "under a minute"
    hours, minutes = divmod(minutes, 60)
    parts = []
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    return " ".join(parts)


def _parse(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value) if value else None
    except ValueError:
        return None


def describe_unfinished(work: Path) -> Unfinished:
    """What *work* holds. An unreadable session is still a row, named plainly."""
    try:
        session = SessionRecord.load(work)
    except (DemoRecordingError, OSError, TypeError, ValueError):
        where = work.parent.name or str(work.parent)
        return Unfinished(work, f"An unfinished recording in {where}", None, None, 0.0)
    output = Path(session.output) if session.output else None
    saved = Path(session.saved) if session.saved else None
    if saved is not None and not saved.is_file():
        saved = None
    return Unfinished(
        work=work,
        name=output.stem if output is not None else "An unfinished recording",
        output=output,
        started=_parse(session.started),
        seconds=sum(max(0.0, segment.duration) for segment in session.segments),
        saved=saved,
        empty=session.state == "failed" and not session.saved,
    )
