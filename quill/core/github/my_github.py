"""My GitHub: one personal queue from what the Workbench already fetches.

The front door of the GitHub Workbench. It does not read GitHub itself and it
adds no client: it takes the rows Inbox and Notifications already load (the
notification inbox, and the attention queue's assigned issues, review requests
and pull requests whose checks failed) and puts them in one list, each saying
what it is, where, and why it is there.

Two honesty rules:

- A source that fails is **named**, and the rest still show. "Notifications
  could not load" never reads as "nothing needs you".
- Only what GitHub says is said. A notification has a read state; an assigned
  issue or a review request does not, so the unread filter leaves those alone
  rather than calling them unread or read. A pull request is here because its
  checks failed, never because QUILL guessed it needed work.

Each item keeps the ``ExploreRow`` it came from, so Enter, Mark Read, Done and
every other action work exactly as they do in the view the row came from.

No ``wx`` imports; strict-typed.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace

from quill.core.github.explore_models import ExploreRow
from quill.core.github.my_github_prefs import GROUPS, KINDS, MyGitHubPrefs
from quill.core.github.review_requests import REVIEW_SOURCES

__all__ = [
    "QueueItem",
    "QueueResult",
    "SourceFailure",
    "assemble",
    "changes_sentence",
    "empty_sentence",
    "group_counts_sentence",
    "item_key",
    "present",
    "refine",
    "summary_sentence",
]

_KIND_LABELS = dict(KINDS)
#: Spoken in a count: "2 unread notifications, 1 assigned issue, 1 review request".
_COUNT_WORDS: dict[str, tuple[str, str]] = {
    "notification": ("unread notification", "unread notifications"),
    "assigned_issue": ("assigned issue", "assigned issues"),
    "assigned_pull": ("assigned pull request", "assigned pull requests"),
    "review_request": ("review request", "review requests"),
    "my_pull_request": (
        "pull request of yours with failing checks",
        "pull requests of yours with failing checks",
    ),
}
#: The short name a row starts with, so a list read aloud says what each is first.
_ROW_WORDS = {
    "notification": "Notification",
    "assigned": "Assigned",
    "review_request": "Review requested",
    "my_pull_request": "Failing checks",
}
_THREAD = re.compile(r"/(?:issues|pulls|pull)/(\d+)")
_WHY = "Why you got it: "


@dataclass(frozen=True, slots=True)
class SourceFailure:
    """One source that did not load: its name, and what went wrong in plain words."""

    source: str
    message: str

    @property
    def sentence(self) -> str:
        said = self.message.strip().rstrip(".") or "it did not answer"
        return f"{self.source} could not load: {said}."


@dataclass(frozen=True, slots=True)
class QueueItem:
    """One thing that wants the person: what it is, where, why, and the row behind it."""

    kind: str
    repository: str
    title: str
    reason: str
    updated_at: str
    unread: bool | None
    row: ExploreRow
    also: tuple[str, ...] = ()

    @property
    def key(self) -> str:
        return item_key(self.row)


@dataclass(frozen=True, slots=True)
class QueueResult:
    """The assembled queue, before the person's filter, and the sources that failed."""

    items: tuple[QueueItem, ...]
    failures: tuple[SourceFailure, ...] = ()
    notes: tuple[str, ...] = ()


def item_key(row: ExploreRow) -> str:
    """A stable identity for a row, across refreshes."""
    return f"{row.kind}:{row.key}" if row.kind == "notification" else (row.url or row.label)


def _thread_ref(row: ExploreRow) -> tuple[str, str] | None:
    """(repository, number) of the issue or pull request a row is about, if it is one."""
    found = _THREAD.search(row.url)
    return (row.repo.casefold(), found.group(1)) if found and row.repo else None


def _notification_item(row: ExploreRow) -> QueueItem:
    why = next(
        (line[len(_WHY) :] for line in row.detail.splitlines() if line.startswith(_WHY)),
        "",
    )
    unread = not row.label.startswith("Read,")
    return QueueItem(
        "notification",
        row.repo,
        row.title or row.label,
        why or "GitHub sent you a notification",
        row.updated_at,
        unread,
        row,
    )


def _attention_kind(row: ExploreRow) -> tuple[str, tuple[str, ...]]:
    """The queue kind for an attention row, and every reason its search lines gave."""
    first = row.detail.split("\n", 1)[0].removeprefix("Also: ")
    sources = tuple(part.strip() for part in first.split(",") if part.strip())
    if any(source in REVIEW_SOURCES for source in sources):
        kind = "review_request"
    elif "Assigned" in sources:
        kind = "assigned"
    elif "Failed checks" in sources:
        kind = "my_pull_request"
    else:
        kind = ""
    return kind, sources


_REASON_WORDS = {
    "Assigned": "assigned to you",
    "Review requested": "your review was requested",
    "Team review requested": "your team's review was requested",
    "Failed checks": "its checks failed",
    "Mentioned": "you were mentioned",
}


def _attention_item(row: ExploreRow) -> QueueItem | None:
    kind, sources = _attention_kind(row)
    if not kind:
        return None
    words = [_REASON_WORDS.get(source, source.lower()) for source in sources]
    reason = words[0][:1].upper() + words[0][1:]
    return QueueItem(
        kind,
        row.repo,
        row.title or row.label,
        reason,
        row.updated_at,
        None,
        row,
        also=tuple(words[1:]),
    )


_PRIORITY = {"notification": 0, "review_request": 1, "assigned": 2, "my_pull_request": 3}


def _merge(first: QueueItem, second: QueueItem) -> QueueItem:
    """One thing both a notification and a search found: one row, both reasons."""
    keep, other = sorted((first, second), key=lambda item: _PRIORITY[item.kind])
    also = tuple(dict.fromkeys((*keep.also, other.reason, *other.also)))
    return replace(keep, also=also, updated_at=max(keep.updated_at, other.updated_at))


def assemble(
    *,
    notifications: Callable[[], Sequence[ExploreRow]],
    attention: Callable[[], Sequence[ExploreRow]],
    attention_note: Callable[[], str] | None = None,
) -> QueueResult:
    """Read both sources, naming one that fails, and put what came back in one list.

    *notifications* and *attention* are the Workbench's own reads (the inbox
    and the attention queue); either may raise, which becomes a
    :class:`SourceFailure` and leaves the other's rows in place. *attention_note*
    is the second read's own warning ("showing the first 50 items"), said as is.
    """
    items: list[QueueItem] = []
    failures: list[SourceFailure] = []
    notes: list[str] = []
    for source, read, build in (
        ("Notifications", notifications, _notification_item),
        ("Assigned issues and review requests", attention, _attention_item),
    ):
        try:
            rows = list(read())
        except Exception as exc:  # noqa: BLE001 - any source failing must not hide the others
            message = str(exc.args[0]) if getattr(exc, "args", None) else str(exc)
            failures.append(SourceFailure(source, message))
            continue
        items.extend(item for item in (build(row) for row in rows) if item is not None)
    if attention_note is not None:
        note = attention_note().strip()
        if note:
            notes.append(note)
    return QueueResult(_dedupe(items), tuple(failures), tuple(notes))


def _dedupe(items: Sequence[QueueItem]) -> tuple[QueueItem, ...]:
    by_ref: dict[tuple[str, str], int] = {}
    by_key: set[str] = set()
    out: list[QueueItem] = []
    for item in items:
        if item.key in by_key:
            continue
        ref = _thread_ref(item.row)
        if ref is not None and ref in by_ref:
            index = by_ref[ref]
            out[index] = _merge(out[index], item)
            continue
        by_key.add(item.key)
        if ref is not None:
            by_ref[ref] = len(out)
        out.append(item)
    return tuple(out)


# -- filter, sort, group ------------------------------------------------------------


def refine(items: Sequence[QueueItem], prefs: MyGitHubPrefs) -> tuple[QueueItem, ...]:
    """The items the person's filter keeps, in the order they chose."""
    kept = [
        item
        for item in items
        if (not prefs.kinds or item.kind in prefs.kinds)
        and (not prefs.repository or item.repository.casefold() == prefs.repository.casefold())
        # Only a notification has a read state; the rest are never hidden as "read".
        and not (prefs.unread_only and item.unread is False)
    ]
    newest_first = sorted(kept, key=lambda item: (item.updated_at, item.key), reverse=True)
    if prefs.sort == "oldest":
        ordered = list(reversed(newest_first))
    elif prefs.sort == "repository":
        ordered = sorted(newest_first, key=lambda item: item.repository.casefold())
    else:
        ordered = newest_first
    if prefs.group == "repository":
        ordered = sorted(ordered, key=lambda item: item.repository.casefold())
    elif prefs.group == "kind":
        order = [key for key, _label in KINDS]
        ordered = sorted(ordered, key=lambda item: order.index(item.kind))
    return tuple(ordered)


def _group_name(item: QueueItem, group: str) -> str:
    if group == "repository":
        return item.repository or "No repository"
    return _KIND_LABELS.get(item.kind, item.kind)


def group_counts_sentence(items: Sequence[QueueItem], group: str) -> str:
    """ "Groups: octo/app 3, octo/web 1." for the status bar, or "" when not grouped."""
    if group == "none" or not items:
        return ""
    counts = Counter(_group_name(item, group) for item in items)
    label = dict(GROUPS)[group].lower()
    parts = ", ".join(f"{name} {count}" for name, count in counts.items())
    return f"Grouped {label}: {parts}."


_COUNT_ORDER = (
    "notification",
    "assigned_issue",
    "assigned_pull",
    "review_request",
    "my_pull_request",
)


def _count_key(item: QueueItem) -> str:
    if item.kind == "assigned":
        return "assigned_pull" if item.row.kind == "pr" else "assigned_issue"
    return item.kind


def _plural(count: int, kind: str) -> str:
    one, many = _COUNT_WORDS[kind]
    return f"{count} {one if count == 1 else many}"


def summary_sentence(items: Sequence[QueueItem]) -> str:
    """ "4 need your attention: 2 unread notifications, 1 assigned item, 1 review request."""
    if not items:
        return empty_sentence()
    counts = Counter(_count_key(item) for item in items)
    parts = [_plural(counts[key], key) for key in _COUNT_ORDER if counts.get(key)]
    verb = "needs" if len(items) == 1 else "need"
    return f"{len(items)} {verb} your attention: {', '.join(parts)}."


def empty_sentence(*, hidden: int = 0) -> str:
    """One sentence for an empty queue; when a filter hid items it says how many."""
    if hidden:
        return (
            f"Nothing shows with your filters; {hidden} "
            f"{'item is' if hidden == 1 else 'items are'} hidden."
        )
    return "Nothing needs your attention."


def changes_sentence(previous: frozenset[str] | None, items: Sequence[QueueItem]) -> str:
    """What a refresh changed, said once: "2 new, 1 cleared." Empty on the first load."""
    if previous is None:
        return ""
    now = {item.key for item in items}
    new, cleared = len(now - previous), len(previous - now)
    if not new and not cleared:
        return "No changes since the last refresh."
    parts = ([f"{new} new"] if new else []) + ([f"{cleared} cleared"] if cleared else [])
    return f"{', '.join(parts)} since the last refresh."


def present(item: QueueItem) -> ExploreRow:
    """The list row for *item*: what it is first, then where, what, and why.

    The ``kind``, ``key``, ``url`` and ``repo`` of the row behind it are kept,
    so the Workbench's own actions work on it unchanged.
    """
    unread = {True: "unread", False: "read", None: ""}[item.unread]
    head = ", ".join(part for part in (_ROW_WORDS[item.kind], unread) if part)
    label = f"{head}: {item.repository} - {item.title}. {item.reason}"
    if item.also:
        label += f"; also {', '.join(item.also)}"
    lines = [
        f"Why it is here: {item.reason}" + (f"; also {', '.join(item.also)}" if item.also else ""),
        f"Kind: {_KIND_LABELS[item.kind]}",
        f"Repository: {item.repository}",
        *(["Read state: " + unread.capitalize()] if unread else []),
        *([f"Updated: {item.updated_at}"] if item.updated_at else []),
        "",
        item.row.detail,
    ]
    return replace(item.row, label=label, detail="\n".join(lines).strip())
