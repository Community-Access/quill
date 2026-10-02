"""What happened while an app was closing, kept for the next launch (F-06).

Quill Radio and QUILL Cast protect their close path with broad exception
handlers, and that is right: a failed tray removal must never stop a window
closing. But a failed *final write* -- the podcast library, the listening
statistics, the active-recording marker -- was swallowed too, and so it was
indistinguishable from a successful one. The next session then inherited
stale or incomplete state with nothing to explain it.

So each teardown step runs through :meth:`ShutdownReport.step` with one of three
classes:

* **must-record** -- user-owned data and markers. A failure is written down and
  said once at the next launch.
* **best-effort** -- tray icons, hotkeys, optional controllers. A failure is
  logged and nothing else: the listener cannot act on it.
* **background** -- work that may finish later but must not touch the closed
  window. Logged.

Close always completes: :meth:`step` never raises, and :meth:`persist` never
raises. What is persisted is a stable step id and a user-safe phrase -- never
exception text, a path, a feed address or a credential, because the record
outlives the session and travels in support bundles. The full exception goes
to the log, which is where a developer looks.

wx-free, strict-typed.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from quill.core import problem_log
from quill.core.storage import write_json_atomic

__all__ = [
    "BACKGROUND",
    "BEST_EFFORT",
    "MUST_RECORD",
    "STEP_PHRASES",
    "ShutdownFailure",
    "ShutdownReport",
    "pending_path",
    "take_pending",
]

logger = logging.getLogger(__name__)

MUST_RECORD = "must-record"
BEST_EFFORT = "best-effort"
BACKGROUND = "background"

#: What each must-record step was *for*, in words a listener can use. A step
#: missing here is described generically rather than by its id.
STEP_PHRASES: dict[str, str] = {
    "podcast_library": "save your podcast library",
    "listening_stats": "save your listening statistics",
    "recording_marker": "clear the note that a recording was running",
    "last_seen": "note when it closed, which is how missed recordings are found",
}


@dataclass(frozen=True, slots=True)
class ShutdownFailure:
    step: str
    step_class: str
    #: The exception's class name only: enough to tell a permissions error from
    #: a full disk in a support bundle, never the message, which can hold a path.
    error_type: str


@dataclass
class ShutdownReport:
    """One app's teardown, step by step. Create at the start of shutdown."""

    app_id: str
    app_title: str
    failures: list[ShutdownFailure] = field(default_factory=list)

    def step(self, step: str, step_class: str, action: Callable[[], object] | None) -> bool:
        """Run *action* and remember a failure. True when it ran cleanly.

        ``None`` (an optional subsystem the app does not have) is a clean no-op.
        """
        if action is None:
            return True
        try:
            action()
        except Exception as exc:  # noqa: BLE001 - shutdown must never block exit
            self.failures.append(ShutdownFailure(step, step_class, type(exc).__name__))
            logger.warning(
                "QUILL-SHUTDOWN-STEP-FAILED app=%s step=%s class=%s error=%s",
                self.app_id,
                step,
                step_class,
                type(exc).__name__,
                exc_info=True,
            )
            return False
        return True

    @property
    def must_record_failures(self) -> list[ShutdownFailure]:
        return [f for f in self.failures if f.step_class == MUST_RECORD]

    def sentence(self) -> str:
        """The one sentence the next launch says, or ``""`` when nothing needs it."""
        failed = self.must_record_failures
        if not failed:
            return ""
        phrases = [STEP_PHRASES.get(f.step, "finish saving") for f in failed]
        unique = list(dict.fromkeys(phrases))
        if len(unique) == 1:
            joined = unique[0]
        else:
            joined = ", ".join(unique[:-1]) + " or " + unique[-1]
        return (
            f"Last time {self.app_title} closed, it could not {joined}. Anything "
            "from the end of that session may be missing. Recent Problems has the "
            "details and a Retry."
        )

    def persist(self, data_dir: Path) -> None:
        """Keep must-record failures for the next launch. Never raises.

        Two records: an entry in the shared Recent Problems log, which is what
        makes it reviewable later; and a small pending file this app reads once
        at its next launch, which is what makes it said exactly once.
        """
        try:
            target = pending_path(data_dir, self.app_id)
            said = self.sentence()
            if not said:
                if target.exists():
                    target.unlink()
                return
            steps = [f.step for f in self.must_record_failures]
            write_json_atomic(target, {"sentence": said, "steps": steps})
            problem_log.record_problem(
                data_dir,
                problem_log.KIND_SHUTDOWN,
                self.app_title,
                said,
                target=problem_log.TARGET_SEP.join([self.app_id, *steps]),
            )
        except Exception:  # noqa: BLE001 - reporting must not become the failure
            logger.warning("QUILL-SHUTDOWN-REPORT-UNSAVED app=%s", self.app_id, exc_info=True)


def pending_path(data_dir: Path, app_id: str) -> Path:
    return Path(data_dir) / f"shutdown_pending_{app_id}.json"


def take_pending(data_dir: Path, app_id: str) -> str:
    """The sentence the previous session left, removed so it is said once."""
    target = pending_path(data_dir, app_id)
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    try:
        target.unlink()
    except OSError:
        pass
    said = raw.get("sentence", "") if isinstance(raw, dict) else ""
    return str(said or "")
