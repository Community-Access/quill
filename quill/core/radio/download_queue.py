"""The download queue: what is waiting, what is going, what arrived.

Downloading one thing needs no queue. Downloading *a book* does, and downloading
three books while listening to a fourth definitely does -- and that is the real
shape of this: somebody wanders the libraries, finds four things worth keeping,
and should be able to say yes to all four and carry on listening.

So the queue is the feature, and these are its rules:

* **One at a time, in the order you asked.** Not four at once. Every source here
  is a free library run on donations, and politeness is not optional. In order
  also means a part-finished book is a playable prefix rather than a scattering.
* **Nothing is lost by stopping.** Cancel one, clear the lot, or close the
  window -- whatever already arrived stays on disk, and a part-transferred file
  resumes rather than restarting.
* **Every item knows where it went.** A finished item keeps its path, so *Open
  Containing Folder* works afterwards. A queue you cannot get back to is a
  progress bar with extra steps.
* **It survives being minimised, and says so.** Closing the window with work
  outstanding either keeps going in the background or stops -- the listener's
  choice, made once in preferences -- and either way it is stated rather than
  guessed at.

This module is the **state**: a list, its transitions, and the words for each.
It never touches the network or a thread; the runner drives it. That split is
what makes the whole thing testable without downloading anything.

wx-free, strict-typed.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

#: The states one item moves through. A finished item stays in the list on
#: purpose: "did that actually download?" is the question people have most, and
#: a queue that empties itself as it succeeds cannot answer it.
WAITING = "waiting"
RUNNING = "running"
DONE = "done"
FAILED = "failed"
CANCELLED = "cancelled"

#: How each state reads in the list. Whole words, because these are spoken.
STATE_LABELS: dict[str, str] = {
    WAITING: "waiting",
    RUNNING: "downloading now",
    DONE: "saved",
    FAILED: "failed",
    CANCELLED: "cancelled",
}

#: States that are over, one way or another.
FINISHED_STATES: frozenset[str] = frozenset({DONE, FAILED, CANCELLED})

_ids = itertools.count(1)


@dataclass(slots=True)
class QueueItem:
    """One thing to download, and what became of it."""

    station: Any
    folder: str
    #: The book or show this belongs to, for the row and for grouping.
    group: str = ""
    state: str = WAITING
    path: str = ""
    error: str = ""
    id: int = field(default_factory=lambda: next(_ids))

    @property
    def name(self) -> str:
        return str(getattr(self.station, "name", "") or "Untitled")

    @property
    def is_finished(self) -> bool:
        return self.state in FINISHED_STATES

    def row_label(self) -> str:
        """The whole row as one sentence, state last so it can be scanned.

        State last because when you are arrowing a queue you already know what
        the items are -- what changes, and what you are looking for, is where
        each one has got to.
        """
        parts = [self.name]
        if self.group and self.group != self.name:
            parts.append(self.group)
        parts.append(STATE_LABELS.get(self.state, self.state))
        if self.state == FAILED and self.error:
            parts.append(self.error)
        return ", ".join(parts)


@dataclass(slots=True)
class DownloadQueue:
    """Everything queued this session, in the order it was asked for."""

    items: list[QueueItem] = field(default_factory=list)

    # -- adding ---------------------------------------------------------------

    def add(self, station: Any, folder: Path | str, *, group: str = "") -> QueueItem:
        item = QueueItem(station=station, folder=str(folder), group=group)
        self.items.append(item)
        return item

    def add_all(
        self, stations: list[Any], folder: Path | str, *, group: str = ""
    ) -> list[QueueItem]:
        return [self.add(station, folder, group=group) for station in stations]

    # -- reading --------------------------------------------------------------

    @property
    def waiting(self) -> list[QueueItem]:
        return [item for item in self.items if item.state == WAITING]

    @property
    def running(self) -> QueueItem | None:
        return next((item for item in self.items if item.state == RUNNING), None)

    @property
    def outstanding(self) -> int:
        """How much is left to do -- what decides whether closing matters."""
        return len([item for item in self.items if not item.is_finished])

    def next_waiting(self) -> QueueItem | None:
        """The next thing to start, or ``None`` when there is nothing left."""
        return next((item for item in self.items if item.state == WAITING), None)

    def find(self, item_id: int) -> QueueItem | None:
        return next((item for item in self.items if item.id == item_id), None)

    # -- transitions ----------------------------------------------------------

    def start(self, item: QueueItem) -> None:
        item.state = RUNNING

    def finish(self, item: QueueItem, path: Path | str) -> None:
        item.state = DONE
        item.path = str(path)

    def fail(self, item: QueueItem, error: str) -> None:
        item.state = FAILED
        item.error = error

    def cancel(self, item: QueueItem) -> bool:
        """Cancel one item. A finished one is left alone rather than rewritten."""
        if item.is_finished:
            return False
        item.state = CANCELLED
        return True

    def remove(self, item: QueueItem) -> bool:
        """Take one row out of the list entirely.

        Allowed for anything that is not currently transferring: removing the
        running item would leave a transfer with nothing to report back to.
        """
        if item.state == RUNNING:
            return False
        self.items.remove(item)
        return True

    def clear_finished(self) -> int:
        """Tidy away everything that is over, keeping anything outstanding."""
        before = len(self.items)
        self.items = [item for item in self.items if not item.is_finished]
        return before - len(self.items)

    def clear_all(self) -> int:
        """Empty the queue. Anything running is cancelled, not orphaned."""
        for item in self.items:
            if not item.is_finished:
                item.state = CANCELLED
        removed = len(self.items)
        self.items = []
        return removed

    # -- words ----------------------------------------------------------------

    def summary(self) -> str:
        """One sentence for the window title and the status line."""
        if not self.items:
            return "Nothing in the download queue."
        done = len([i for i in self.items if i.state == DONE])
        failed = len([i for i in self.items if i.state == FAILED])
        left = self.outstanding
        parts = []
        if left:
            parts.append(f"{left} to go")
        if done:
            parts.append(f"{done} saved")
        if failed:
            parts.append(f"{failed} failed")
        return ", ".join(parts) + "." if parts else "Download queue is empty."

    def closing_message(self, *, keep_going: bool) -> str:
        """What to say when the window closes with work outstanding.

        Said either way. A queue that silently keeps running is as surprising as
        one that silently stops, and which of the two happens is a preference
        somebody set once and will not remember.
        """
        left = self.outstanding
        if not left:
            return ""
        if keep_going:
            return (
                f"{left} download{'' if left == 1 else 's'} still going. "
                "Quill Radio will finish them in the background."
            )
        return (
            f"{left} download{'' if left == 1 else 's'} stopped. "
            "Anything already saved is kept, and starting them again will resume."
        )
