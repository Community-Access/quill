"""Plain language in, a previewed batch out, for GitHub (GitHub PRD 22.6, GH-R-086).

The GitHub Workbench's half of the plain-language batches the WordPress
Workbench has had since W7 (:mod:`quill.core.wordpress.workbench_plain_batch`):
a small, fixed grammar read without AI, so the same words always mean the
same query and the same change, and nothing is guessed. The age it reads is
the one shared reading (:mod:`quill.core.workbench.plain_age`).

- ``close every issue labelled duplicate older than 90 days``
- ``close all issues labeled stale that nobody touched in 90 days as not planned``
- ``reopen the closed issues labelled regression``
- ``add label triage to every issue with no label``
- ``remove label wontfix from all closed issues``
- ``assign alice to every open issue labelled bug``
- ``unassign bob from all pull requests``
- ``which pull requests are waiting on me, oldest first?`` or
  ``how many issues are labelled bug?``: a question, which lists or counts
  and changes nothing.

:func:`parse_request` reads the words into a :class:`PlainRequest`, whose
:attr:`PlainRequest.query` is GitHub's own search (``is:issue is:open
label:"duplicate" created:<2026-08-21``), or raises :class:`PlainError` with
what it understands. The Workbench resolves the query to the exact items,
shows them as an editable checklist, and sends what is left checked through
the same batch as several rows' Properties (:mod:`quill.core.github.batch`):
the tier preview, a conflict check, the verify re-read, Change History.

Wx-free and strict-typed.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from quill.core.error_codes import CodedError
from quill.core.workbench.plain_age import AgeError, find_age
from quill.core.workbench.properties import FieldChange, ListDelta

__all__ = [
    "EXAMPLES",
    "LIMIT",
    "PlainError",
    "PlainRequest",
    "order_items",
    "parse_request",
]

#: The most items one sentence may reach: GitHub's search returns 1000 at most.
LIMIT = 500
EXAMPLES = (
    "close every issue labelled duplicate older than 90 days",
    "close all issues labeled stale that nobody touched in 90 days as not planned",
    "add label triage to every issue with no label",
    "assign alice to every open issue labelled bug",
    "which pull requests are waiting on me, oldest first?",
)

#: Words that start a filter, so an age or a name stops before them.
_STOPS = (
    "labelled",
    "labeled",
    "with",
    "without",
    "by",
    "assigned",
    "unassigned",
    "in",
    "that",
    "which",
    "and",
    "opened",
    "created",
    "updated",
    "waiting",
    "mentioning",
    "oldest",
    "newest",
    "as",
)
_KIND = re.compile(r"\b(issues?|pull requests?|prs?)\b", re.IGNORECASE)
_NAME = r"(?:\"(?P<q{n}>[^\"]+)\"|'(?P<s{n}>[^']+)'|(?P<w{n}>[^\s,?]+))"
_LEAD = re.compile(r"^(?:every|all(?: the)?|each|the|any)\s+", re.IGNORECASE)
_STATE = re.compile(r"\b(open|closed)\b", re.IGNORECASE)
_TOUCHED = re.compile(
    r"\b(?:that\s+)?(?:nobody|no one|no-one)\s+(?:has\s+)?touched\s+(?:in|for)\s+"
    r"(?P<span>.+?)(?=\s+(?:labelled|labeled|with|without|by|assigned|as|oldest|newest)\b|$)"
    r"|\b(?:not updated|untouched|inactive)\s+(?:in|for)\s+"
    r"(?P<span2>.+?)(?=\s+(?:labelled|labeled|with|without|by|assigned|as|oldest|newest)\b|$)",
    re.IGNORECASE,
)
_ORDERS = {
    "oldest first": "created_asc",
    "newest first": "created_desc",
    "least recently updated first": "updated_asc",
    "recently updated first": "updated_desc",
}
_CLOSE_AS = {
    "completed": "closed as completed",
    "complete": "closed as completed",
    "not planned": "closed as not planned",
}


class PlainError(CodedError):
    """A sentence the GitHub batch grammar does not read, said plainly with examples."""

    code = "QUILL-GITHUB-WORKBENCH-PHRASE"

    @property
    def plain(self) -> str:
        return str(self.args[0]) if self.args else ""


@dataclass(frozen=True)
class PlainRequest:
    """What a sentence asks for: an action on a kind of item, and the search for them.

    *action* is ``close``, ``reopen``, ``add_label``, ``remove_label``,
    ``assign``, ``unassign``, ``list`` or ``count``; *value* is the label or
    login it changes, or the closed state for ``close``.
    """

    action: str
    value: str
    kind: str  # "issue" or "pull_request"
    qualifiers: tuple[str, ...]
    order: str = ""
    words: str = ""

    @property
    def changes_anything(self) -> bool:
        return self.action not in ("list", "count")

    @property
    def noun(self) -> str:
        return "pull requests" if self.kind == "pull_request" else "issues"

    @property
    def query(self) -> str:
        """GitHub's search for the items, without the repository (the Workbench adds it)."""
        kind = "is:pr" if self.kind == "pull_request" else "is:issue"
        return " ".join((kind, *self.qualifiers))

    def changes(self) -> list[FieldChange]:
        """The batch's one change, as a several-items sheet would send it."""
        if self.action == "close":
            after = self.value if self.kind == "issue" else "closed"
            return [FieldChange("state", "State", None, after)]
        if self.action == "reopen":
            return [FieldChange("state", "State", None, "open")]
        key, label = (
            ("labels", "Labels") if self.action.endswith("label") else ("assignees", "Assignees")
        )
        adds = self.action in ("add_label", "assign")
        delta = ListDelta((self.value,), ()) if adds else ListDelta((), (self.value,))
        return [FieldChange(key, label, None, delta)]

    def said(self) -> str:
        """The request in the Workbench's words, for the preview's title line."""
        verb = {
            "close": f"Close ({self.value.removeprefix('closed as ')})"
            if self.kind == "issue"
            else "Close",
            "reopen": "Reopen",
            "add_label": f"Add label {self.value} to",
            "remove_label": f"Remove label {self.value} from",
            "assign": f"Assign {self.value} to",
            "unassign": f"Unassign {self.value} from",
            "list": "List",
            "count": "Count",
        }[self.action]
        return f"{verb} {self.noun} matching {self.query}"


def _name(found: re.Match[str], n: int) -> str:
    return next(
        (found.group(f"{k}{n}") for k in ("q", "s", "w") if found.group(f"{k}{n}")), ""
    ).strip()


def _quote(value: str) -> str:
    return f'"{value}"' if re.search(r"\s", value) else value


def _login(value: str) -> str:
    login = value.lstrip("@")
    return "@me" if login.lower() in ("me", "myself") else login


def _action(text: str) -> tuple[str, str, str]:
    """(action, value, the rest of the sentence) from its first words."""
    lowered = text.lower()
    for pattern, action in (
        (rf"^add (?:the )?label {_NAME.format(n=1)} to\s+", "add_label"),
        (rf"^label (?:as )?{_NAME.format(n=1)}\s+", "add_label"),
        (rf"^remove (?:the )?label {_NAME.format(n=1)} from\s+", "remove_label"),
        (rf"^unlabel {_NAME.format(n=1)} (?:from|on)\s+", "remove_label"),
        (rf"^assign {_NAME.format(n=1)} to\s+", "assign"),
        (rf"^unassign {_NAME.format(n=1)} from\s+", "unassign"),
    ):
        found = re.match(pattern, text, re.IGNORECASE)
        if found:
            value = _name(found, 1)
            if action in ("assign", "unassign"):
                value = _login(value)  # "@me" is the signed-in account; the Workbench names it
            return action, value, text[found.end() :]
    for word, action in (("close ", "close"), ("reopen ", "reopen")):
        if lowered.startswith(word):
            return action, "", text[len(word) :]
    for pattern, action in (
        (r"^how many\s+", "count"),
        (r"^(?:which|what|show(?: me)?|list|find)\s+", "list"),
    ):
        found = re.match(pattern, text, re.IGNORECASE)
        if found:
            return action, "", text[found.end() :]
    raise PlainError(
        f"QUILL does not read {text!r} as a GitHub batch. Start with close, reopen, add label, "
        "remove label, assign, unassign, which or how many. For example: "
        + "; ".join(EXAMPLES[:3])
        + "."
    )


def parse_request(text: str, today: date | None = None) -> PlainRequest:
    """Read *text* into a :class:`PlainRequest`; :class:`PlainError` when a word is not read."""
    today = today or date.today()
    words = " ".join(text.strip().split()).rstrip("?.!")
    if not words:
        raise PlainError("Say what to change, for example: " + EXAMPLES[0] + ".")
    action, value, rest = _action(words)
    rest = _LEAD.sub("", rest.strip())
    if action in ("count", "list"):
        rest = re.sub(r"\b(?:are|is|were|have been)\b", " ", rest, flags=re.IGNORECASE)
    qualifiers: list[str] = []
    # The state first, as an adjective: "the closed issues", "open pull requests".
    state = ""
    before_kind = _KIND.search(rest)
    if before_kind:
        head = rest[: before_kind.start()]
        adjective = _STATE.search(head)
        if adjective:
            state = adjective.group(1).lower()
            head = head[: adjective.start()] + head[adjective.end() :]
        if head.strip(" ,"):
            raise PlainError(f"QUILL does not read {head.strip()!r} before the kind of item.")
        kind_word = before_kind.group(1).lower()
        rest = rest[before_kind.end() :]
    else:
        raise PlainError("Say issues or pull requests, for example: " + EXAMPLES[0] + ".")
    kind = "issue" if kind_word.startswith("issue") else "pull_request"
    # "as not planned" belongs to close.
    if action == "close":
        found = re.search(r"\bas (completed|complete|not planned)\b", rest, re.IGNORECASE)
        if found:
            value = _CLOSE_AS[found.group(1).lower()]
            rest = rest[: found.start()] + rest[found.end() :]
        elif re.search(r"\bas duplicates?\b", rest, re.IGNORECASE):
            raise PlainError(
                "Closing as a duplicate needs the issue each one duplicates, so it is not a "
                "batch: close each with Close Issue... (Ctrl+Shift+W on the row)."
            )
        value = value or "closed as completed"
    order = ""
    for phrase, key in _ORDERS.items():
        found = re.search(rf",?\s*\b{phrase}\b", rest, re.IGNORECASE)
        if found:
            order, rest = key, rest[: found.start()] + rest[found.end() :]
            break
    # "that nobody touched in 90 days": updated before then.
    touched = _TOUCHED.search(rest)
    if touched:
        span = touched.group("span") or touched.group("span2")
        try:
            age, _left = find_age(f"older than {span}", today, stops=())
        except AgeError as exc:
            raise PlainError(exc.plain) from exc
        qualifiers.append(f"updated:<{age.before[:10]}")
        rest = rest[: touched.start()] + rest[touched.end() :]
    rest = _filters(rest, qualifiers, today)
    leftover = re.sub(r"\b(?:and|that|which|are|is|with|,)\b|,", " ", rest).strip()
    if leftover:
        raise PlainError(
            f"QUILL does not read {leftover!r} here. It reads labelled, without label, with no "
            "label, by, assigned to, unassigned, in milestone, waiting on me, mentioning me, "
            "open or closed, an age (older than 90 days, updated before March 2024), and "
            "oldest first or newest first."
        )
    if state:
        qualifiers.insert(0, f"is:{state}")
    elif action == "reopen":
        qualifiers.insert(0, "is:closed")
    elif not any(q in ("is:open", "is:closed") for q in qualifiers):
        qualifiers.insert(0, "is:open")
    if action == "reopen" and "is:open" in qualifiers:
        raise PlainError("Open items are already open: say closed, or nothing, to reopen.")
    if action == "close" and "is:closed" in qualifiers:
        raise PlainError("Closed items are already closed: say open, or nothing, to close.")
    if not value and action in ("add_label", "remove_label", "assign", "unassign"):
        raise PlainError("Say which label or person, for example: " + EXAMPLES[2] + ".")
    return PlainRequest(action, value, kind, tuple(qualifiers), order, words)


def _filters(rest: str, qualifiers: list[str], today: date) -> str:
    """Take each filter the grammar knows out of *rest*, as qualifiers; what is left."""
    patterns: Sequence[tuple[str, str]] = (
        (rf"\b(?:without|not) (?:the )?label(?:led|ed)? {_NAME.format(n=1)}", "-label:{v}"),
        (r"\b(?:with no|without any|without an?|without) labels?\b|\bunlabell?ed\b", "no:label"),
        (rf"\b(?:labell?ed|with (?:the )?label|tagged) {_NAME.format(n=1)}", "label:{v}"),
        (r"\b(?:unassigned|assigned to nobody|assigned to no one|with no assignee)\b",
         "no:assignee"),
        (rf"\bassigned to {_NAME.format(n=1)}", "assignee:{login}"),
        (rf"\b(?:opened by|created by|authored by|written by|by|from) {_NAME.format(n=1)}",
         "author:{login}"),
        (r"\b(?:with no|without an?|without) milestone\b", "no:milestone"),
        (rf"\b(?:in )?milestone {_NAME.format(n=1)}", "milestone:{v}"),
        (r"\b(?:waiting on|waiting for|waiting for a review from|awaiting) me\b",
         "review-requested:@me"),
        (r"\bmentioning me\b", "mentions:@me"),
        (r"\b(open|closed)\b", "is:{state}"),
    )  # fmt: skip
    for pattern, qualifier in patterns:
        while True:
            found = re.search(pattern, rest, re.IGNORECASE)
            if not found:
                break
            value = _name(found, 1) if "(?P<q1>" in pattern else ""
            text = qualifier.format(
                v=_quote(value),
                login=_login(value),
                state=found.group(1).lower() if "{state}" in qualifier else "",
            )
            if text not in qualifiers:
                qualifiers.append(text)
            rest = rest[: found.start()] + " " + rest[found.end() :]
    # An age: "older than 90 days" (created), "updated before March 2024" (updated).
    while True:
        field = "updated" if re.search(r"\b(?:updated|touched)\b", rest, re.IGNORECASE) else ""
        rest = re.sub(r"\b(?:updated|touched|created|opened)\b", " ", rest, flags=re.IGNORECASE)
        try:
            age, left = find_age(" ".join(rest.split()), today, stops=_STOPS)
        except AgeError as exc:
            raise PlainError(exc.plain) from exc
        if not age.words:
            break
        name = field or "created"
        if age.before:
            qualifiers.append(f"{name}:<{age.before[:10]}")
        if age.after:
            qualifiers.append(f"{name}:>{age.after[:10]}")
        rest = left
    return rest


def order_items[T](rows: Sequence[T], order: str) -> list[T]:
    """*rows* in the sentence's order ("oldest first"); unchanged when it named none."""
    if not order:
        return list(rows)
    field, _sep, way = order.partition("_")
    attribute = "created_at" if field == "created" else "updated_at"
    return sorted(
        rows, key=lambda row: str(getattr(row, attribute, "") or ""), reverse=way == "desc"
    )
