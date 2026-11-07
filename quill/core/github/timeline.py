"""An issue's or pull request's timeline as one readable history.

GitHub's ``GET /repos/{owner}/{repo}/issues/{number}/timeline`` returns every
event of a conversation in a different shape per event. This module turns
each one worth reading into one line, with its date and who did it, oldest
first and newest last, and says plainly when there were more pages than it
read. Subscribe and mention bookkeeping is left out; an event it does not
know is still listed, by GitHub's own name, so nothing is silently dropped.

No ``wx`` imports; strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.rest_transport import GitHubRestError, request_json, rest_failure_message
from quill.core.github.run_actions import repo_path

_PAGE_SIZE = 100
_MAX_PAGES = 5
_SKIPPED = frozenset({"subscribed", "unsubscribed", "mentioned"})
_REVIEW_STATES = {
    "approved": "approved",
    "changes_requested": "requested changes",
    "commented": "reviewed with comments",
    "dismissed": "had a review dismissed",
}


@dataclass(frozen=True, slots=True)
class TimelineEntry:
    """One event: when, who, and what happened."""

    when: str
    actor: str
    text: str

    @property
    def line(self) -> str:
        date = _date(self.when) or "date unknown"
        return f"{date}, {self.actor or 'someone'}: {self.text}"


@dataclass(frozen=True, slots=True)
class TimelineResult:
    entries: tuple[TimelineEntry, ...]
    complete: bool = True
    note: str = ""

    def text(self, title: str = "") -> str:
        lines = [title] if title else []
        if not self.entries:
            lines.append("No events in this history yet.")
        lines.extend(entry.line for entry in self.entries)
        lines.append(self.note or f"Complete history: {len(self.entries)} events.")
        return "\n".join(lines)


def _date(value: str) -> str:
    if len(value) >= 16 and value[10] in "T ":
        return f"{value[:10]} {value[11:16]}"
    return value[:10]


def _get(row: Mapping[str, Any], *keys: str) -> Any:
    value: Any = row
    for key in keys:
        value = value.get(key) if isinstance(value, Mapping) else None
    return value


def _login(value: Any) -> str:
    return str(value.get("login") or "") if isinstance(value, Mapping) else ""


def _first_line(value: Any, limit: int = 90) -> str:
    text = str(value or "").strip()
    first = text.splitlines()[0] if text else ""
    return first if len(first) <= limit else first[: limit - 3] + "..."


def timeline_entry(row: Mapping[str, Any]) -> TimelineEntry | None:
    """One timeline event as a readable line; None for bookkeeping events."""
    event = str(row.get("event") or "")
    if not event or event in _SKIPPED:
        return None
    actor = _login(row.get("actor")) or _login(row.get("user"))
    when = str(row.get("created_at") or row.get("submitted_at") or "")
    if event in ("labeled", "unlabeled"):
        verb = "added" if event == "labeled" else "removed"
        text = f"{verb} the label {_get(row, 'label', 'name') or 'unknown'}"
    elif event in ("assigned", "unassigned"):
        who = _login(row.get("assignee")) or "someone"
        text = f"assigned {who}" if event == "assigned" else f"unassigned {who}"
    elif event in ("review_requested", "review_request_removed"):
        who = _login(row.get("requested_reviewer")) or str(
            _get(row, "requested_team", "name") or "a team"
        )
        text = (
            f"requested a review from {who}"
            if event == "review_requested"
            else f"removed the review request for {who}"
        )
    elif event == "reviewed":
        state = str(row.get("state") or "").casefold()
        text = _REVIEW_STATES.get(state, "reviewed")
        if summary := _first_line(row.get("body")):
            text += f": {summary}"
    elif event == "committed":
        actor = actor or str(_get(row, "author", "name") or "")
        when = when or str(_get(row, "author", "date") or _get(row, "committer", "date") or "")
        sha = str(row.get("sha") or "")[:7]
        text = f"committed {sha}: {_first_line(row.get('message'))}".rstrip(": ")
    elif event == "head_ref_force_pushed":
        text = "force-pushed the branch"
    elif event == "cross-referenced":
        source = _get(row, "source", "issue")
        number = _get(source, "number") if isinstance(source, Mapping) else None
        repo = _get(source, "repository", "full_name") if isinstance(source, Mapping) else None
        title = _first_line(_get(source, "title")) if isinstance(source, Mapping) else ""
        where = f"{repo}#{number}" if repo and number else f"#{number}" if number else "elsewhere"
        text = f"mentioned this in {where}" + (f": {title}" if title else "")
    elif event in ("closed", "reopened"):
        text = "closed this" if event == "closed" else "reopened this"
    elif event == "merged":
        sha = str(row.get("commit_id") or "")[:7]
        text = f"merged this as {sha}" if sha else "merged this"
    elif event == "commented":
        text = "commented" + (f": {summary}" if (summary := _first_line(row.get("body"))) else "")
    else:
        text = event.replace("_", " ").replace("-", " ")
    return TimelineEntry(when=when, actor=actor, text=text)


def build_timeline(rows: list[Any], *, complete: bool = True, note: str = "") -> TimelineResult:
    """Order events oldest first and keep only the readable ones."""
    entries = [entry for row in rows if isinstance(row, Mapping) and (entry := timeline_entry(row))]
    entries.sort(key=lambda entry: entry.when or "")
    return TimelineResult(tuple(entries), complete=complete, note=note)


class _TimelineAccess(Protocol):
    _token: str | None


class GitHubTimelineMixin:
    """Read a conversation's timeline, page by page, with a completeness note."""

    def fetch_timeline(self: _TimelineAccess, full_name: str, number: int) -> TimelineResult:
        if isinstance(number, bool) or not isinstance(number, int) or number <= 0:
            raise GitHubItemsError("Choose an issue or pull request first.")
        path = f"{repo_path(full_name)}/issues/{number}/timeline"
        rows: list[Any] = []
        complete = True
        note = ""
        for page in range(1, _MAX_PAGES + 1):
            try:
                response = request_json(
                    self._token,
                    "GET",
                    path,
                    query={"per_page": str(_PAGE_SIZE), "page": str(page)},
                )
            except GitHubRestError as exc:
                if not rows:
                    raise GitHubItemsError(rest_failure_message("read the timeline", exc)) from exc
                complete = False
                note = (
                    f"Partial history: page {page} could not be read "
                    f"({rest_failure_message('read the rest', exc)})"
                )
                break
            batch = response.data if isinstance(response.data, list) else []
            rows.extend(batch)
            has_next = 'rel="next"' in response.header("link")
            if len(batch) < _PAGE_SIZE or not has_next:
                break
            if page == _MAX_PAGES:
                complete = False
                note = (
                    f"Partial history: QUILL read the first {len(rows)} events and GitHub "
                    "has more. Open the conversation on GitHub for the rest."
                )
        result = build_timeline(rows, complete=complete, note=note)
        if complete:
            return TimelineResult(
                result.entries, note=f"Complete history: {len(result.entries)} events."
            )
        return result


__all__ = [
    "GitHubTimelineMixin",
    "TimelineEntry",
    "TimelineResult",
    "build_timeline",
    "timeline_entry",
]
