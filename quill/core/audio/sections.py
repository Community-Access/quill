"""Marking a piece of a recording, and collecting several into one file.

The cut itself has worked for a long time (``speech/audio_edit.trim_file``).
What was missing is the *workflow*, and the workflow is the feature: mark a
start, mark an end, hear what you marked before committing to it, save it, and
then go and find the next piece and add it to the same file.

That last part is what makes this worth building rather than a Save-As with two
numbers in it. Pulling four quotes out of a two-hour interview, or the six songs
somebody actually wants out of a four-hour broadcast recording, is a *collecting*
task, and every player that offers "trim" without "and another one" makes you do
it six times and stitch the results yourself.

Three rules this keeps, and the first is the one that matters:

* **The source is never touched.** Every operation reads it and writes somewhere
  else. There is no undo for a destructive edit of the only copy of a recording,
  so there is no destructive edit.
* **A mark is a position, not a commitment.** Marks can be moved, cleared and
  re-heard as often as you like; nothing is written until you ask for a file.
* **Every position is a number of milliseconds**, matching the player stack, so
  a mark set from the playhead needs no conversion and cannot drift.

wx-free, strict-typed. The ffmpeg work is delegated to ``audio_edit``; this
module is the bookkeeping and the words.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

#: Below this, a section is a slip of the finger rather than a selection. Saving
#: one produces a file too short to be anything, and the listener almost
#: certainly meant to move a mark rather than keep it.
MIN_SECTION_MS = 250


@dataclass(frozen=True, slots=True)
class Section:
    """One marked piece of one file."""

    source: Path
    start_ms: int
    end_ms: int
    label: str = ""

    @property
    def duration_ms(self) -> int:
        return max(0, self.end_ms - self.start_ms)

    @property
    def is_usable(self) -> bool:
        return self.duration_ms >= MIN_SECTION_MS


@dataclass(slots=True)
class SectionMarks:
    """The start and end being marked right now, before anything is saved.

    Deliberately allows either mark on its own: somebody listens forward, marks
    the start when they hear it begin, and marks the end when they hear it stop.
    Requiring both at once would mean knowing the answer before listening.
    """

    source: Path | None = None
    start_ms: int | None = None
    end_ms: int | None = None

    def mark_start(self, source: Path, position_ms: int) -> None:
        # Marking in a different file starts a fresh pair: a section that
        # spanned two recordings would be meaningless.
        if self.source is not None and self.source != source:
            self.end_ms = None
        self.source = source
        self.start_ms = max(0, int(position_ms))
        if self.end_ms is not None and self.end_ms <= self.start_ms:
            self.end_ms = None

    def mark_end(self, source: Path, position_ms: int) -> None:
        if self.source is not None and self.source != source:
            self.start_ms = None
        self.source = source
        self.end_ms = max(0, int(position_ms))
        if self.start_ms is not None and self.start_ms >= self.end_ms:
            self.start_ms = None

    def clear(self) -> None:
        self.source = None
        self.start_ms = None
        self.end_ms = None

    def section(self, *, label: str = "") -> Section | None:
        """The marked section, or ``None`` when it is not complete or usable."""
        if self.source is None or self.start_ms is None or self.end_ms is None:
            return None
        candidate = Section(self.source, self.start_ms, self.end_ms, label)
        return candidate if candidate.is_usable else None


def spoken_span(section: Section) -> str:
    """ "from 4 minutes 12 seconds to 5 minutes 30 seconds, 1 minute 18 seconds long"."""
    from quill.ui.radio.bounded_playback_ui import spoken_duration

    return (
        f"from {spoken_duration(section.start_ms)} to {spoken_duration(section.end_ms)}, "
        f"{spoken_duration(section.duration_ms)} long"
    )


def describe_marks(marks: SectionMarks) -> str:
    """What is marked so far, in words. Never silent, never a pair of numbers."""
    from quill.ui.radio.bounded_playback_ui import spoken_duration

    if marks.source is None or (marks.start_ms is None and marks.end_ms is None):
        return "Nothing is marked."
    if marks.start_ms is None:
        return f"End marked at {spoken_duration(marks.end_ms or 0)}. No start yet."
    if marks.end_ms is None:
        return f"Start marked at {spoken_duration(marks.start_ms)}. No end yet."
    section = Section(marks.source, marks.start_ms, marks.end_ms)
    if not section.is_usable:
        return f"Marked {spoken_span(section)} -- too short to save. Move one of the marks."
    return f"Marked {spoken_span(section)}."


@dataclass(slots=True)
class SectionCollection:
    """Sections gathered on the way to one output file, in the order added."""

    sections: list[Section] = field(default_factory=list)

    def add(self, section: Section) -> bool:
        """Keep *section*. False when it is too short to be one."""
        if not section.is_usable:
            return False
        self.sections.append(section)
        return True

    def remove(self, index: int) -> Section | None:
        if 0 <= index < len(self.sections):
            return self.sections.pop(index)
        return None

    def clear(self) -> None:
        self.sections.clear()

    @property
    def total_ms(self) -> int:
        return sum(section.duration_ms for section in self.sections)

    def describe(self) -> str:
        """How much is collected, in words."""
        from quill.ui.radio.bounded_playback_ui import spoken_duration

        count = len(self.sections)
        if not count:
            return "No sections collected yet."
        return (
            f"{count} section{'' if count == 1 else 's'} collected, "
            f"{spoken_duration(self.total_ms)} in total."
        )

    def row_label(self, index: int) -> str:
        """One collected section as a whole sentence, the way the list reads it."""
        section = self.sections[index]
        name = section.label or section.source.name
        return f"{index + 1}. {name}, {spoken_span(section)}"


def save_sections(
    collection: SectionCollection,
    destination: Path,
    *,
    work_dir: Path,
    append: bool = False,
) -> Path:
    """Write every collected section into *destination*, in order.

    *append* adds them to the end of a file that already exists rather than
    replacing it, which is the whole point of collecting: the fourth quote from
    the third interview joins the three already there.

    Nothing here writes to any source file. Each section is cut to its own
    temporary file and the pieces are joined, so a failure part way through
    leaves the destination exactly as it was -- either the file gains everything
    asked for or it gains nothing.
    """
    from quill.core.radio.recording_join import join_recording_parts
    from quill.core.speech.audio_edit import trim_file

    if not collection.sections:
        raise ValueError("There are no sections to save.")

    work_dir.mkdir(parents=True, exist_ok=True)
    pieces: list[Path] = []
    if append and destination.exists():
        # The existing file is the first piece, copied rather than appended to,
        # so a failure cannot damage what is already there.
        existing = work_dir / f"existing{destination.suffix}"
        existing.write_bytes(destination.read_bytes())
        pieces.append(existing)

    for index, section in enumerate(collection.sections, start=1):
        piece = work_dir / f"section{index}{section.source.suffix}"
        trim_file(section.source, piece, start_ms=section.start_ms, end_ms=section.end_ms)
        pieces.append(piece)

    if len(pieces) == 1:
        pieces[0].replace(destination)
        return destination
    outcome = join_recording_parts(pieces, output=destination)
    if not outcome.joined:
        # The joiner refuses rather than half-writes -- mixed formats, an
        # ffmpeg failure -- and it says why. Passing that up is the whole of
        # the promise that the destination gains everything or nothing.
        raise ValueError(
            f"The sections could not be joined into one file: {outcome.reason or 'unknown reason'}"
        )
    return outcome.path
