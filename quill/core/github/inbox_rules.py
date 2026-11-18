"""Inbox rules for notifications: a condition and an action, Outlook's way (PRD 22.12).

A rule says which notifications it is for -- a repository (``*`` matches any
part, so ``octo/*`` is every repository of ``octo``), GitHub's reason for the
notification, what it is about (pull request, issue, release...) and words in
its title -- and what to do with them: mark them done, mark them read, or move
them to the top of the list. Every condition a rule names must hold; one with
no condition is refused, since it would act on everything.

Rules run each time Notifications loads (:func:`apply_rules`), on the
worker thread, before the list is shown; :func:`preview` is the same run on
today's list without sending anything, said before a rule is saved. They are
kept in ``github_inbox_rules.json`` in QUILL's data folder.

wx-free and strict-typed.
"""

from __future__ import annotations

import fnmatch
import json
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path

from quill.core.github.notification_triage import reason_in_words, subject_in_words
from quill.core.github.notifications import GitHubNotification

__all__ = [
    "ACTIONS",
    "SUBJECTS",
    "InboxRule",
    "RuleRun",
    "apply_rules",
    "load_rules",
    "preview",
    "rules_path",
    "save_rules",
]

#: What a notification can be about, in the order a chooser offers them.
SUBJECTS: tuple[str, ...] = (
    "PullRequest",
    "Issue",
    "Discussion",
    "Release",
    "CheckSuite",
    "Commit",
    "RepositoryVulnerabilityAlert",
)

#: Action code -> what is said for it.
ACTIONS: dict[str, str] = {
    "mark_done": "mark it done",
    "mark_read": "mark it read",
    "to_top": "move it to the top",
}


@dataclass(frozen=True)
class InboxRule:
    action: str
    repository: str = ""
    reason: str = ""
    subject: str = ""
    title_contains: str = ""

    @property
    def has_condition(self) -> bool:
        return bool(self.repository or self.reason or self.subject or self.title_contains)

    def matches(self, note: GitHubNotification) -> bool:
        if self.repository and not fnmatch.fnmatchcase(
            note.repository.casefold(), self.repository.casefold()
        ):
            return False
        if self.reason and note.reason != self.reason:
            return False
        if self.subject and note.subject_type != self.subject:
            return False
        return not (
            self.title_contains
            and self.title_contains.casefold() not in note.subject_title.casefold()
        )

    @property
    def sentence(self) -> str:
        """ "When a notification is from octo/*, about a pull request: mark it done."."""
        parts = []
        if self.repository:
            parts.append(f"from {self.repository}")
        if self.reason:
            parts.append(f"because {reason_in_words(self.reason)}")
        if self.subject:
            parts.append(f"about {_article(subject_in_words(self.subject))}")
        if self.title_contains:
            parts.append(f"with {self.title_contains!r} in its title")
        what = ", ".join(parts) or "of any kind"
        return f"When a notification is {what}: {ACTIONS.get(self.action, self.action)}."


def _article(noun: str) -> str:
    return ("an " if noun[:1] in "aeiou" else "a ") + noun


@dataclass
class RuleRun:
    """What the rules did, or would do, to one load of notifications."""

    kept: list[GitHubNotification] = field(default_factory=list)
    done: list[str] = field(default_factory=list)
    read: list[str] = field(default_factory=list)
    to_top: int = 0

    @property
    def sentence(self) -> str:
        said = []
        if self.done:
            said.append(f"{len(self.done)} marked done")
        if self.read:
            said.append(f"{len(self.read)} marked read")
        if self.to_top:
            said.append(f"{self.to_top} moved to the top")
        return ("Inbox rules: " + ", ".join(said) + ".") if said else ""


def apply_rules(rules: Sequence[InboxRule], notes: Iterable[GitHubNotification]) -> RuleRun:
    """Run *rules* over *notes*, in order; the first rule that matches a note decides.

    Returns the notes still to show (those moved to the top first, otherwise in
    GitHub's order) and the ids to mark done or read. Nothing is sent here.
    """
    run = RuleRun()
    top: list[GitHubNotification] = []
    rest: list[GitHubNotification] = []
    for note in notes:
        rule = next((r for r in rules if r.has_condition and r.matches(note)), None)
        action = rule.action if rule is not None else ""
        if action == "mark_done":
            run.done.append(note.id)
            continue
        if action == "mark_read" and note.unread:
            run.read.append(note.id)
        if action == "to_top":
            top.append(note)
            continue
        rest.append(note)
    run.to_top = len(top)
    run.kept = top + rest
    return run


def preview(rule: InboxRule, notes: Sequence[GitHubNotification], *, show: int = 5) -> str:
    """What *rule* would do to today's list, said before it is saved."""
    hits = [note for note in notes if rule.matches(note)]
    if not notes:
        return "There are no notifications loaded today to try it on."
    if not hits:
        return f"It matches none of the {len(notes)} notifications loaded today."
    titles = "; ".join(f"{n.repository}: {n.subject_title}" for n in hits[:show])
    more = f"; and {len(hits) - show} more" if len(hits) > show else ""
    verb = ACTIONS.get(rule.action, rule.action).replace(" it ", " them ")
    if verb.endswith(" it"):
        verb = verb[:-3] + " them"
    return (
        f"It matches {len(hits)} of the {len(notes)} notifications loaded today, and would "
        f"{verb}: {titles}{more}."
    )


def rules_path() -> Path:
    from quill.core.paths import app_data_dir

    return app_data_dir() / "github_inbox_rules.json"


def load_rules(path: Path | None = None) -> list[InboxRule]:
    target = path or rules_path()
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    rules: list[InboxRule] = []
    for entry in raw.get("rules", []) if isinstance(raw, dict) else []:
        if not isinstance(entry, dict) or entry.get("action") not in ACTIONS:
            continue
        rule = InboxRule(
            action=str(entry["action"]),
            repository=str(entry.get("repository") or ""),
            reason=str(entry.get("reason") or ""),
            subject=str(entry.get("subject") or ""),
            title_contains=str(entry.get("title_contains") or ""),
        )
        if rule.has_condition:
            rules.append(rule)
    return rules


def save_rules(rules: Sequence[InboxRule], path: Path | None = None) -> None:
    from quill.core.storage import write_json_atomic

    target = path or rules_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(target, {"version": 1, "rules": [asdict(rule) for rule in rules]})
