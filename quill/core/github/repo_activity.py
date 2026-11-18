"""Repository > Insights > Commit Activity: GitHub's statistics graphs as tables (PRD 14.2).

GitHub draws a repository's statistics as charts: commits a week, lines added
and removed a week, the punch card of busy hours, and each contributor's
lines. A chart is a picture; here each is rows that read whole on their own,
so the list *is* the table:

* "Commit activity, week of 2026-11-09: 14 commits. Busiest Tuesday, 5."
  for the last twelve weeks (``/stats/commit_activity``).
* "Code frequency, week of 2026-11-09: 1,204 lines added, 310 removed."
  (``/stats/code_frequency``).
* "Busiest hour 1: Tuesdays at 14:00 UTC, 23 commits." for the ten busiest
  hours of the week (``/stats/punch_card``).
* "Last 4 weeks: 30 commits, 22 by the owner." (``/stats/participation``).
* "Contributor sam: 120 commits, 3,000 lines added, 900 removed." for each
  author GitHub counts (``/stats/contributors``).

GitHub computes statistics in the background and answers 202 with nothing
while it does; the first row then says to refresh in a moment rather than
showing an empty table. Repositories with 10,000 commits or more get no
statistics from GitHub at all, and the row says that too.

No ``wx``; strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from quill.core.github.conditional_requests import ConditionalResult, conditional_get
from quill.core.github.explore_models import ExploreRow
from quill.core.github.rest_transport import GitHubRestError, rest_failure_message
from quill.core.github.run_actions import repo_path

__all__ = ["WEEKS", "fetch_activity"]

Getter = Callable[[str, dict[str, str] | None], ConditionalResult]

#: How many recent weeks the weekly tables show.
WEEKS = 12
_DAYS = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")


def _int(value: object) -> int:
    return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0


def _n(number: int, word: str) -> str:
    return f"{number:,} {word}{'' if number == 1 else 's'}"


def _week(stamp: object) -> str:
    return datetime.fromtimestamp(_int(stamp), tz=UTC).strftime("%Y-%m-%d")


def _row(repo: str, label: str, key: str) -> ExploreRow:
    page = f"https://github.com/{repo}/graphs/commit-activity"
    return ExploreRow(label, label + f"\n{page}", page, repo, "insight", key)


def _commit_rows(repo: str, data: object) -> list[ExploreRow]:
    rows = []
    for week in (data if isinstance(data, list) else [])[-WEEKS:]:
        if not isinstance(week, dict):
            continue
        days = [_int(d) for d in week.get("days") or ()]
        total = _int(week.get("total"))
        label = f"Commit activity, week of {_week(week.get('week'))}: {_n(total, 'commit')}."
        if total and len(days) == 7:
            busiest = max(range(7), key=lambda i: days[i])
            label += f" Busiest {_DAYS[busiest]}, {days[busiest]}."
        rows.append(_row(repo, label, f"week:{week.get('week')}"))
    return rows[::-1]


def _frequency_rows(repo: str, data: object) -> list[ExploreRow]:
    rows = []
    for week in (data if isinstance(data, list) else [])[-WEEKS:]:
        if isinstance(week, list) and len(week) == 3:
            added, removed = _int(week[1]), abs(_int(week[2]))
            label = (
                f"Code frequency, week of {_week(week[0])}: {_n(added, 'line')} added, "
                f"{removed:,} removed."
            )
            rows.append(_row(repo, label, f"frequency:{week[0]}"))
    return rows[::-1]


def _punch_rows(repo: str, data: object) -> list[ExploreRow]:
    hours = [
        (_int(h[0]), _int(h[1]), _int(h[2]))
        for h in (data if isinstance(data, list) else [])
        if isinstance(h, list) and len(h) == 3 and _int(h[2])
    ]
    hours.sort(key=lambda h: (-h[2], h[0], h[1]))
    return [
        _row(
            repo,
            f"Busiest hour {rank}: {_DAYS[day % 7]}s at {hour:02d}:00 UTC, {_n(count, 'commit')}.",
            f"hour:{day}:{hour}",
        )
        for rank, (day, hour, count) in enumerate(hours[:10], start=1)
    ]


def _participation_row(repo: str, data: object) -> list[ExploreRow]:
    if not isinstance(data, dict):
        return []
    every = [_int(n) for n in data.get("all") or ()][-4:]
    owner = [_int(n) for n in data.get("owner") or ()][-4:]
    if not every:
        return []
    label = f"Last 4 weeks: {_n(sum(every), 'commit')}, {sum(owner):,} by the owner."
    return [_row(repo, label, "participation")]


def _contributor_rows(repo: str, data: object, limit: int) -> list[ExploreRow]:
    people = []
    for person in data if isinstance(data, list) else []:
        if not isinstance(person, dict):
            continue
        author = person.get("author") if isinstance(person.get("author"), dict) else {}
        login = str((author or {}).get("login") or "someone without an account")
        weeks = [w for w in person.get("weeks") or () if isinstance(w, dict)]
        added = sum(_int(w.get("a")) for w in weeks)
        removed = sum(_int(w.get("d")) for w in weeks)
        people.append((_int(person.get("total")), login, added, removed))
    people.sort(key=lambda p: (-p[0], p[1].lower()))
    return [
        _row(
            repo,
            f"Contributor {login}: {_n(total, 'commit')}, {_n(added, 'line')} added, "
            f"{removed:,} removed.",
            f"contributor:{login}",
        )
        for total, login, added, removed in people[:limit]
    ]


def fetch_activity(
    token: str | None,
    repo: str,
    *,
    limit: int,
    warnings: list[str],
    get: Getter | None = None,
) -> list[ExploreRow]:
    """The summary sentence, then each statistic as rows; 202 is said, not shown empty."""
    base = repo_path(repo)
    read = get or (lambda path, query: conditional_get(token, path, query=query))
    sections: list[list[ExploreRow]] = []
    counting = empty = False
    makers: tuple[tuple[str, Callable[[object], list[ExploreRow]]], ...] = (
        ("participation", lambda d: _participation_row(repo, d)),
        ("commit_activity", lambda d: _commit_rows(repo, d)),
        ("code_frequency", lambda d: _frequency_rows(repo, d)),
        ("punch_card", lambda d: _punch_rows(repo, d)),
        ("contributors", lambda d: _contributor_rows(repo, d, limit)),
    )
    for name, make in makers:
        try:
            reply = read(f"{base}/stats/{name}", None)
        except GitHubRestError as exc:
            warnings.append(rest_failure_message(f"read the {name.replace('_', ' ')}", exc))
            continue
        if reply.status == 202:
            counting = True
            continue
        if reply.status == 204 or reply.data in (None, [], {}):
            empty = True
            continue
        sections.append(make(reply.data))
    rows = [row for section in sections for row in section]
    if counting:
        summary = (
            f"{repo}: GitHub is still counting its statistics; refresh in a moment. "
            f"{_n(len(rows), 'row')} ready so far."
        )
    elif not rows and empty:
        summary = (
            f"{repo}: no commit statistics. The repository is empty, or has 10,000 commits "
            "or more, which GitHub does not count."
        )
    else:
        summary = f"{repo}: commit activity in {_n(len(rows), 'row')}, newest first."
    return [_row(repo, summary, "summary"), *rows]
