"""A person's profile, read as sentences: People > person > Profile, and People > My Profile.

GitHub's profile page is a picture: a name and bio, pinned repositories, and
a calendar of green squares. Here it is rows, each whole on its own:

* who they are: "jeff (Jeff Bishop): Tucson, Arizona; 120 followers,
  following 40." and their bio and status;
* the year's contributions: "1,234 contributions in the last year: 900
  commits, 120 issues, 200 pull requests and 14 reviews.";
* the calendar as numbers: the busiest day, the longest and the current
  streak, and one row per month, newest first ("October 2026: 140
  contributions");
* the pinned repositories, as repository rows ("Pinned: owner/name, ...,
  12 stars"), so Enter opens one.

GraphQL ``user(login)`` with ``pinnedItems`` and ``contributionsCollection``.
Takes the Workbench's :class:`~quill.core.github.workbench_api.GitHubApi`.
wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.github.explore_models import ExploreRow
from quill.core.github.workbench_api import GitHubApi

__all__ = ["ProfileError", "calendar_rows", "fetch_profile"]


class ProfileError(CodedError):
    """A profile could not be read; the message is said."""

    code = "QUILL-GITHUB-PROFILE"


_PROFILE = """
query($login: String!) {
  user(login: $login) { ...profile }
}
fragment profile on User {
  login name bio company location websiteUrl
  followers { totalCount } following { totalCount }
  status { message emoji }
  pinnedItems(first: 6) {
    nodes {
      ... on Repository { nameWithOwner description stargazerCount }
      ... on Gist { name description url }
    }
  }
  contributionsCollection {
    totalCommitContributions totalIssueContributions
    totalPullRequestContributions totalPullRequestReviewContributions
    contributionCalendar {
      totalContributions
      weeks { contributionDays { date contributionCount } }
    }
  }
}
"""

_VIEWER = _PROFILE.replace("query($login: String!) {\n  user(login: $login)", "query {\n  viewer")


def _n(number: int, word: str, plural: str = "") -> str:
    return f"{number:,} {word if number == 1 else plural or word + 's'}"


def _int(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _total(value: object) -> int:
    return _int(value.get("totalCount")) if isinstance(value, Mapping) else 0


def _row(login: str, label: str, key: str, url: str = "") -> ExploreRow:
    page = url or f"https://github.com/{login}"
    return ExploreRow(label, f"{label}\n{page}", page, "", "profile", key)


def calendar_rows(login: str, days: list[tuple[date, int]], today: date) -> list[ExploreRow]:
    """The busiest day, the streaks, and one row a month, newest first."""
    if not days:
        return []
    days = sorted(days)
    busiest = max(days, key=lambda day: (day[1], day[0]))
    rows = []
    if busiest[1]:
        rows.append(
            _row(
                login,
                f"Busiest day: {busiest[0].isoformat()}, {_n(busiest[1], 'contribution')}.",
                "busiest",
            )
        )
    longest = run = 0
    longest_end = days[0][0]
    for when, count in days:
        run = run + 1 if count else 0
        if run > longest:
            longest, longest_end = run, when
    if longest:
        rows.append(
            _row(
                login,
                f"Longest streak: {_n(longest, 'day')}, ending {longest_end.isoformat()}.",
                "longest",
            )
        )
    current = 0
    for when, count in reversed(days):
        if when > today:
            continue
        if count:
            current += 1
        elif when < today:  # today may still be empty without breaking the streak
            break
    rows.append(_row(login, f"Current streak: {_n(current, 'day')}.", "current"))
    months: dict[tuple[int, int], int] = {}
    for when, count in days:
        months[(when.year, when.month)] = months.get((when.year, when.month), 0) + count
    for (year, month), count in sorted(months.items(), reverse=True):
        name = date(year, month, 1).strftime("%B %Y")
        rows.append(_row(login, f"{name}: {_n(count, 'contribution')}.", f"month:{year}-{month}"))
    return rows


def _days(collection: Mapping[str, Any]) -> list[tuple[date, int]]:
    calendar = collection.get("contributionCalendar")
    weeks = calendar.get("weeks") if isinstance(calendar, Mapping) else None
    found = []
    for week in weeks or ():
        for day in (week.get("contributionDays") if isinstance(week, Mapping) else None) or ():
            if isinstance(day, Mapping) and day.get("date"):
                try:
                    found.append((
                        date.fromisoformat(str(day["date"])),
                        _int(day.get("contributionCount")),
                    ))
                except ValueError:
                    continue
    return found


def fetch_profile(
    api: GitHubApi, login: str = "", *, today: date | None = None
) -> list[ExploreRow]:
    """*login*'s profile as rows; an empty *login* reads your own."""
    who = login.strip().lstrip("@")
    data = api.graphql(_PROFILE, {"login": who}) if who else api.graphql(_VIEWER, {})
    user = data.get("user" if who else "viewer") if isinstance(data, Mapping) else None
    if not isinstance(user, Mapping):
        raise ProfileError(f"GitHub has no account called {who}.")
    name = str(user.get("login") or who)
    full = str(user.get("name") or "")
    facts = [str(user.get(key)) for key in ("company", "location") if user.get(key)]
    people = (
        f"{_n(_total(user.get('followers')), 'follower')}, "
        f"following {_total(user.get('following')):,}"
    )
    head = f"{name}" + (f" ({full})" if full else "") + ": " + "; ".join([*facts, people]) + "."
    rows = [_row(name, head, "who")]
    if user.get("bio"):
        rows.append(_row(name, f"Bio: {str(user['bio']).strip()}", "bio"))
    status = user.get("status")
    if isinstance(status, Mapping) and status.get("message"):
        rows.append(_row(name, f"Status: {status['message']}", "status"))
    if user.get("websiteUrl"):
        rows.append(
            _row(name, f"Website: {user['websiteUrl']}", "website", str(user["websiteUrl"]))
        )
    collection = user.get("contributionsCollection")
    if isinstance(collection, Mapping):
        calendar = collection.get("contributionCalendar")
        total = _int(calendar.get("totalContributions")) if isinstance(calendar, Mapping) else 0
        parts = [
            _n(_int(collection.get("totalCommitContributions")), "commit"),
            _n(_int(collection.get("totalIssueContributions")), "issue"),
            _n(_int(collection.get("totalPullRequestContributions")), "pull request"),
            _n(_int(collection.get("totalPullRequestReviewContributions")), "review"),
        ]
        rows.append(
            _row(
                name,
                f"{_n(total, 'contribution')} in the last year: {', '.join(parts[:-1])} "
                f"and {parts[-1]}.",
                "year",
            )
        )
        rows += calendar_rows(name, _days(collection), today or date.today())
    pinned = user.get("pinnedItems")
    for item in (pinned.get("nodes") if isinstance(pinned, Mapping) else None) or ():
        if not isinstance(item, Mapping):
            continue
        if item.get("nameWithOwner"):
            repo = str(item["nameWithOwner"])
            stars = _int(item.get("stargazerCount"))
            text = str(item.get("description") or "")
            label = f"Pinned: {repo}" + (f", {text}" if text else "") + f", {_n(stars, 'star')}."
            rows.append(ExploreRow(label, label, f"https://github.com/{repo}", repo, "repo", repo))
        elif item.get("url"):
            text = str(item.get("description") or item.get("name") or "a gist")
            rows.append(
                _row(name, f"Pinned gist: {text}", f"gist:{item.get('name')}", str(item["url"]))
            )
    return rows
