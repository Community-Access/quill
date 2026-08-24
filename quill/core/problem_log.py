"""Recent Problems: the one place a failure that was spoken once still lives.

This family announces everything -- and announcements are transient by
design. A feed that failed while you were in another window, a download that
died overnight, a stream that dropped mid-sentence: each said its piece once,
to nobody, and then was gone. That is the single place this family is not
screen-reader-first, because a sighted listener still has a list to scroll
back through and a listener who missed the speech has nothing at all
(list.md 11.5).

So every failure worth a second look is also *written down* here: what
failed, what it was, why, when, and enough of a handle to try it again. The
log is:

* **Bounded** (:data:`MAX_PROBLEMS`) and newest-first, so it is a window on
  the recent past rather than a growing file nobody prunes.
* **Local.** It never leaves the machine and carries no credentials -- a
  private feed's address is recorded, its password is not.
* **Shared by both apps**, one file under the shared data folder, because a
  feed Quill Radio failed to read is the same feed QUILL Cast failed to read.
* **Retryable by key, not by closure.** Each entry carries a ``kind`` and a
  ``target``; an app registers one retry handler per kind it understands, and
  an entry whose kind nothing claims simply has no Retry -- which is honest,
  and survives a restart, where a stored callback could not.

wx-free and strict-typed: the window is
:mod:`quill.ui.problems_dialog`, and everything about *what happened* is
decided here where it can be tested without one.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quill.core.storage import write_json_atomic

__all__ = [
    "KIND_DOWNLOAD",
    "KIND_FEED",
    "KIND_LABELS",
    "KIND_OTHER",
    "KIND_RECORDING",
    "KIND_STREAM",
    "MAX_PROBLEMS",
    "TARGET_SEP",
    "Problem",
    "clear_problems",
    "load_problems",
    "record_problem",
    "store_path",
]

#: How a compound target is joined -- a download's show id and episode guid,
#: for instance. A vertical bar rather than a control character so the file
#: stays readable by eye, and because neither id can contain one.
TARGET_SEP = "|"

#: How many problems the log keeps. Two hundred is several bad weeks; past
#: that, the oldest are dropped rather than the file growing without end.
MAX_PROBLEMS = 200

KIND_FEED = "feed"
KIND_DOWNLOAD = "download"
KIND_STREAM = "stream"
KIND_RECORDING = "recording"
KIND_OTHER = "other"

#: How each kind reads out loud. The label leads the row, so arrowing the
#: list groups by kind by ear without the list being sorted by it.
KIND_LABELS: dict[str, str] = {
    KIND_FEED: "Feed",
    KIND_DOWNLOAD: "Download",
    KIND_STREAM: "Stream",
    KIND_RECORDING: "Recording",
    KIND_OTHER: "Problem",
}


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True, slots=True)
class Problem:
    """One thing that went wrong, with enough to understand and retry it."""

    kind: str
    #: What it happened to, as a person would name it ("The Daily").
    subject: str
    #: Why, in the words the failure itself gave ("404 Not Found").
    reason: str
    #: ISO-8601 UTC. Stored as text so the file stays readable by eye.
    when: str = field(default_factory=_now)
    #: The handle a retry handler needs -- a feed address, a download id, a
    #: stream URL. Never a credential.
    target: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "subject": self.subject,
            "reason": self.reason,
            "when": self.when,
            "target": self.target,
        }

    @classmethod
    def from_dict(cls, data: Any) -> Problem | None:
        if not isinstance(data, dict):
            return None
        kind = str(data.get("kind", "") or "").strip() or KIND_OTHER
        subject = str(data.get("subject", "") or "").strip()
        reason = str(data.get("reason", "") or "").strip()
        if not subject and not reason:
            return None
        return cls(
            kind=kind,
            subject=subject,
            reason=reason,
            when=str(data.get("when", "") or ""),
            target=str(data.get("target", "") or ""),
        )

    def when_display(self) -> str:
        """The time, local and short: "24 Aug, 14:03" (or "" if unparsable)."""
        try:
            moment = datetime.fromisoformat(self.when)
        except ValueError:
            return ""
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=UTC)
        return moment.astimezone().strftime("%d %b, %H:%M")

    def row_label(self) -> str:
        """The whole row as one sentence, in the order a listener needs it.

        Kind first (so arrowing groups by ear), then what it happened to, then
        why, then when -- the reason before the timestamp because the reason
        is what you are looking for and the time is only ever confirmation.
        """
        parts = [KIND_LABELS.get(self.kind, KIND_LABELS[KIND_OTHER])]
        if self.subject:
            parts.append(self.subject)
        parts.append(self.reason or "no reason given")
        stamp = self.when_display()
        if stamp:
            parts.append(stamp)
        return ", ".join(parts)


def store_path(data_dir: Path) -> Path:
    return data_dir / "recent-problems.json"


def load_problems(data_dir: Path) -> list[Problem]:
    """Every recorded problem, newest first. Never raises."""
    path = store_path(data_dir)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    rows = raw.get("problems") if isinstance(raw, dict) else raw
    if not isinstance(rows, list):
        return []
    problems = [p for p in (Problem.from_dict(row) for row in rows) if p is not None]
    return problems[:MAX_PROBLEMS]


def save_problems(data_dir: Path, problems: list[Problem]) -> None:
    """Write the log atomically, newest first, capped. Never raises."""
    try:
        write_json_atomic(
            store_path(data_dir),
            {"version": 1, "problems": [p.to_dict() for p in problems[:MAX_PROBLEMS]]},
        )
    except OSError:
        return


def record_problem(
    data_dir: Path,
    kind: str,
    subject: str,
    reason: str,
    *,
    target: str = "",
) -> Problem:
    """Write one problem down and return it.

    Deliberately not deduplicated by content: a feed that has failed on each
    of the last six checks is *six* facts, and collapsing them would hide the
    one thing the list is for -- how long this has been going on. Consecutive
    identical failures do collapse onto one row's timestamp update, so a feed
    checked every fifteen minutes does not fill the window by itself.
    """
    problem = Problem(kind=kind, subject=subject.strip(), reason=reason.strip(), target=target)
    problems = load_problems(data_dir)
    if problems and _same_failure(problems[0], problem):
        problems[0] = problem  # same failure, still happening: keep one row, fresh time
    else:
        problems.insert(0, problem)
    save_problems(data_dir, problems)
    return problem


def _same_failure(older: Problem, newer: Problem) -> bool:
    return (
        older.kind == newer.kind
        and older.subject == newer.subject
        and older.reason == newer.reason
        and older.target == newer.target
    )


def clear_problems(data_dir: Path) -> int:
    """Empty the log; returns how many rows went."""
    count = len(load_problems(data_dir))
    save_problems(data_dir, [])
    return count


def summary(problems: list[Problem]) -> str:
    """What the window says on open -- counted, like every other list."""
    if not problems:
        return "No recent problems. Nothing has failed since the list was last cleared."
    kinds: dict[str, int] = {}
    for problem in problems:
        kinds[problem.kind] = kinds.get(problem.kind, 0) + 1
    parts = [
        f"{count} {KIND_LABELS.get(kind, KIND_LABELS[KIND_OTHER]).lower()}"
        for kind, count in sorted(kinds.items())
    ]
    total = len(problems)
    return f"{total} recent problem{'' if total == 1 else 's'}: " + ", ".join(parts) + "."


def report_text(problems: list[Problem]) -> str:
    """The whole list as copyable text, newest first (Copy All)."""
    if not problems:
        return "No recent problems."
    return "\n".join(problem.row_label() for problem in problems)
