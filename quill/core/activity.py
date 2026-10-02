"""One shape for "what happened", shared by every app: results, activity, progress.

qc.md F-10 and sections 7.1-7.6. Before this module every feature invented its
own sentence at its own call site, so a save that failed in Lite, a feed that
failed in Cast and a write that failed on the way out of Radio each explained
themselves differently -- and once spoken, each was gone. The recurring report
"I pressed it and nothing happened" is usually one of three things: the result
was never said, it was said while the listener was elsewhere, or it was said
and there was no way to act on it.

So a result is a record, not a sentence:

* :class:`ActionResult` -- the action, the object, the outcome, one spoken
  summary, the reason, the **next actions** (Retry, Undo, Open, Open Folder,
  Details), a correlation id and an importance. Rendered as speech, a status
  line, an activity row and a details page from the same fields.
* :class:`ActivityLog` -- the recent results of this app, newest first,
  bounded, in memory. "Repeat Last Result" reads its newest *important* entry
  rather than the last thing the screen reader happened to say.
* :class:`Progress` and :class:`ProgressAnnouncer` -- one progress model whose
  announcer speaks milestones (a quarter, a half, three quarters, done) and
  phase changes, never every percent; an owner token keeps a finished or
  closed operation from announcing again.
* :func:`restore_index` -- focus memory by identity: return to the same object
  after a list changed, or the nearest valid row when it is gone.

No document content, stream URL or credential is ever put in a record: callers
pass object *names*. wx-free, strict-typed, pure apart from the process-wide
:data:`LOG`.
"""

from __future__ import annotations

import threading
import uuid
from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime

# -- outcomes and importance ----------------------------------------------------

COMPLETED = "completed"
BLOCKED = "blocked"
CANCELLED = "cancelled"
FAILED = "failed"
PARTIAL = "partial"
OUTCOMES = (COMPLETED, BLOCKED, CANCELLED, FAILED, PARTIAL)

OUTCOME_WORDS: dict[str, str] = {
    COMPLETED: "Done",
    BLOCKED: "Blocked",
    CANCELLED: "Cancelled",
    FAILED: "Failed",
    PARTIAL: "Partly done",
}

#: Said at once, and kept for review.
SPEAK = "speak"
#: Kept for review only -- background news nobody is waiting for.
REVIEW = "review"


@dataclass(frozen=True, slots=True)
class NextAction:
    """Something the listener can do about a result, by a stable id."""

    id: str
    label: str


RETRY = NextAction("retry", "Retry")
UNDO = NextAction("undo", "Undo")
OPEN = NextAction("open", "Open")
OPEN_FOLDER = NextAction("open_folder", "Open Folder")
DETAILS = NextAction("details", "Details")
NEXT_ACTIONS = (RETRY, UNDO, OPEN, OPEN_FOLDER, DETAILS)


def _now() -> datetime:
    return datetime.now()


@dataclass(frozen=True, slots=True)
class ActionResult:
    """One finished (or refused) action, as every renderer needs it."""

    action: str
    object_name: str
    outcome: str
    summary: str
    reason: str = ""
    next_actions: tuple[NextAction, ...] = ()
    importance: str = SPEAK
    details: str = ""
    operation_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    when: datetime = field(default_factory=_now)

    @property
    def is_problem(self) -> bool:
        return self.outcome in (FAILED, PARTIAL, BLOCKED)

    def has(self, action_id: str) -> bool:
        return any(action.id == action_id for action in self.next_actions)

    def spoken(self) -> str:
        """The sentence to say: the summary, then the reason if it adds one."""
        text = self.summary.strip()
        reason = self.reason.strip()
        if reason and reason.lower() not in text.lower():
            text = f"{text} {reason}" if text.endswith((".", "!", "?")) else f"{text}. {reason}"
        return text

    def row(self) -> str:
        """One list row: outcome first, then what, then when."""
        stamp = self.when.strftime("%H:%M")
        word = OUTCOME_WORDS.get(self.outcome, self.outcome.capitalize())
        clean_reason = self.reason.strip().rstrip(".")
        reason = f" -- {clean_reason}" if clean_reason and self.is_problem else ""
        return f"{word}: {self.summary.strip().rstrip('.')}{reason}. {stamp}"

    def details_text(self) -> str:
        """Everything about the result, for the details pane."""
        lines = [self.spoken(), f"Action: {self.action}"]
        if self.object_name:
            lines.append(f"Object: {self.object_name}")
        lines.append(f"Outcome: {OUTCOME_WORDS.get(self.outcome, self.outcome)}")
        lines.append(f"When: {self.when.strftime('%Y-%m-%d %H:%M:%S')}")
        if self.next_actions:
            lines.append("You can: " + ", ".join(a.label for a in self.next_actions) + ".")
        if self.details.strip():
            lines.extend(("", self.details.strip()))
        return "\n".join(lines)


# -- the log -------------------------------------------------------------------------

#: How many results an app remembers. Enough for a session's worth of review;
#: small enough that the list stays something you can arrow through.
LOG_LIMIT = 200


class ActivityLog:
    """The recent results of one app, newest first. Thread-safe."""

    def __init__(self, limit: int = LOG_LIMIT) -> None:
        self._items: deque[ActionResult] = deque(maxlen=limit)
        self._lock = threading.Lock()
        self._listeners: list[Callable[[ActionResult], None]] = []
        self._progress: dict[str, Progress] = {}

    def record(self, result: ActionResult) -> ActionResult:
        with self._lock:
            self._items.appendleft(result)
            listeners = list(self._listeners)
        for listener in listeners:
            try:
                listener(result)
            except Exception:  # noqa: BLE001 - one bad listener must not stop the rest
                pass
        return result

    def recent(self) -> list[ActionResult]:
        with self._lock:
            return list(self._items)

    def find(self, operation_id: str) -> ActionResult | None:
        with self._lock:
            return next((r for r in self._items if r.operation_id == operation_id), None)

    def latest_important(self) -> ActionResult | None:
        """The newest result worth repeating: spoken ones, and any problem."""
        with self._lock:
            return next((r for r in self._items if r.importance == SPEAK or r.is_problem), None)

    def clear(self) -> int:
        with self._lock:
            count = len(self._items)
            self._items.clear()
        return count

    def subscribe(self, listener: Callable[[ActionResult], None]) -> Callable[[], None]:
        with self._lock:
            self._listeners.append(listener)

        def unsubscribe() -> None:
            with self._lock:
                if listener in self._listeners:
                    self._listeners.remove(listener)

        return unsubscribe

    # -- operations in flight -------------------------------------------------------

    def begin(self, progress: Progress) -> Progress:
        with self._lock:
            self._progress[progress.operation_id] = progress
        return progress

    def update(self, progress: Progress) -> None:
        with self._lock:
            if progress.operation_id in self._progress:
                self._progress[progress.operation_id] = progress

    def end(self, operation_id: str) -> None:
        with self._lock:
            self._progress.pop(operation_id, None)

    def active(self) -> list[Progress]:
        with self._lock:
            return list(self._progress.values())


#: This process's log. Each QuillVille app is its own process, so one log per
#: process is one log per app; QUILL Lite's windows share theirs on purpose.
LOG = ActivityLog()


def summary_sentence(results: Sequence[ActionResult]) -> str:
    """How much there is to review, in one sentence."""
    if not results:
        return "Nothing has happened yet in this session."
    problems = sum(1 for r in results if r.is_problem)
    noun = "result" if len(results) == 1 else "results"
    if not problems:
        return f"{len(results)} {noun}, no problems."
    plural = "problem" if problems == 1 else "problems"
    return f"{len(results)} {noun}, {problems} {plural}."


# -- progress -------------------------------------------------------------------------

PREPARING = "preparing"
READING = "reading"
PARSING = "parsing"
DOWNLOADING = "downloading"
WRITING = "writing"
FINALIZING = "finalizing"


@dataclass(frozen=True, slots=True)
class Progress:
    """Where one operation has got to."""

    operation_id: str
    phase: str
    message: str
    current: int = 0
    total: int = 0
    can_cancel: bool = False
    #: Whoever started it; a mismatched owner never announces (a closed window,
    #: or a newer run of the same operation).
    owner_token: object = None

    @property
    def fraction(self) -> float | None:
        if self.total <= 0:
            return None
        return max(0.0, min(1.0, self.current / self.total))

    def spoken(self) -> str:
        fraction = self.fraction
        if fraction is None:
            return self.message
        return f"{self.message}, {round(fraction * 100)} percent"


class ProgressAnnouncer:
    """Decide which progress updates are worth saying. Never a speech storm.

    Speaks a phase change, and the first update to cross each milestone
    (every *step* percent, 25 by default). An update from an owner that is not
    the current one is ignored, so a stale run cannot talk over a new one.
    """

    def __init__(self, *, step: int = 25, owner_token: object = None) -> None:
        self._step = max(1, min(100, step))
        self._owner = owner_token
        self._phase: str | None = None
        self._last_milestone = -1
        self._finished = False

    def retarget(self, owner_token: object) -> None:
        """A new run: forget the old one's milestones and its owner."""
        self._owner = owner_token
        self._phase = None
        self._last_milestone = -1
        self._finished = False

    def next_sentence(self, progress: Progress) -> str | None:
        if self._finished:
            return None
        if self._owner is not None and progress.owner_token is not self._owner:
            return None
        if progress.phase != self._phase:
            self._phase = progress.phase
            self._last_milestone = self._milestone(progress)
            return progress.spoken()
        milestone = self._milestone(progress)
        if milestone > self._last_milestone:
            self._last_milestone = milestone
            if milestone >= 100:
                self._finished = True
            return progress.spoken()
        return None

    def _milestone(self, progress: Progress) -> int:
        fraction = progress.fraction
        if fraction is None:
            return -1
        return int(fraction * 100) // self._step * self._step


# -- focus memory ------------------------------------------------------------------------


def restore_index(keys: Sequence[str], wanted: str | None, previous_index: int) -> int:
    """The row to put focus back on after a list was rebuilt.

    By identity first: the row whose key is *wanted*. If that object is gone,
    the row now at its old position (the one that moved up into its place),
    or the last row when the list got shorter. ``-1`` for an empty list.
    Returning to a bare row index after the list changed is how focus lands
    on the wrong podcast; returning to nothing is how it lands nowhere.
    """
    if not keys:
        return -1
    if wanted is not None:
        for index, key in enumerate(keys):
            if key == wanted:
                return index
    if previous_index < 0:
        return 0
    return min(previous_index, len(keys) - 1)


__all__ = [
    "BLOCKED",
    "CANCELLED",
    "COMPLETED",
    "DETAILS",
    "DOWNLOADING",
    "FAILED",
    "FINALIZING",
    "LOG",
    "LOG_LIMIT",
    "NEXT_ACTIONS",
    "OPEN",
    "OPEN_FOLDER",
    "OUTCOMES",
    "OUTCOME_WORDS",
    "PARSING",
    "PARTIAL",
    "PREPARING",
    "READING",
    "RETRY",
    "REVIEW",
    "SPEAK",
    "UNDO",
    "WRITING",
    "ActionResult",
    "ActivityLog",
    "NextAction",
    "Progress",
    "ProgressAnnouncer",
    "restore_index",
    "summary_sentence",
]
