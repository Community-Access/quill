"""Explore's Insights and Community profile views, read as sentences.

Insights is the last 14 days of traffic (views and clones, each day as well
as the total), the sites people came from, the pages they read, and the
contributors with their commits on the default branch. Every row reads whole
on its own -- "Views on 2026-11-01: 120 views, 30 unique visitors" -- so the
list *is* the numbers table, one figure set per line, and the first row says
the whole picture in one sentence.

Traffic needs push access. When GitHub refuses it, the view says so in words
and still shows the contributors, which anyone can read.

The community profile is GitHub's checklist (README, license, contributing
guide, code of conduct, issue templates, pull request template), said as
present or missing, with the health percentage first.

Reads go through :func:`~quill.core.github.conditional_requests.conditional_get`,
so a refresh that changed nothing costs no rate limit. No ``wx``; strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.conditional_requests import ConditionalResult, conditional_get
from quill.core.github.explore_models import ExploreRow, GitHubExploreError
from quill.core.github.rest_transport import GitHubRestError, rest_failure_message
from quill.core.github.run_actions import repo_path

Getter = Callable[[str, dict[str, str] | None], ConditionalResult]


def _getter(token: str | None) -> Getter:
    return lambda path, query: conditional_get(token, path, query=query)


def _count(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    try:
        return int(str(value or 0))
    except ValueError:
        return 0


def _plural(number: int, word: str) -> str:
    return f"{number:,} {word}{'' if number == 1 else 's'}"


def _visitors(number: int) -> str:
    return f"{number:,} unique visitor{'' if number == 1 else 's'}"


def traffic_refused_sentence(repo: str, exc: GitHubRestError) -> str:
    if exc.status in (403, 404):
        return (
            f"Traffic needs push access to {repo}, and GitHub refused it to this account. "
            "Contributors are still listed."
        )
    return rest_failure_message("read the traffic", exc)


def _traffic_rows(repo: str, kind: str, data: object) -> list[ExploreRow]:
    section = "Views" if kind == "views" else "Clones"
    noun = "view" if kind == "views" else "clone"
    page = f"https://github.com/{repo}/graphs/traffic"
    body = data if isinstance(data, dict) else {}
    days = [day for day in body.get(kind) or () if isinstance(day, dict)]
    total = _count(body.get("count"))
    uniques = _count(body.get("uniques"))
    rows = [
        ExploreRow(
            f"{section}, last 14 days: {_plural(total, noun)}, {_visitors(uniques)}",
            f"{section}, last 14 days\n{_plural(total, noun)}, {_visitors(uniques)}.\n"
            "GitHub keeps 14 days of traffic, counted by day in UTC.\n" + page,
            page,
            repo,
            "insight",
            f"{kind}:total",
        )
    ]
    for day in reversed(days):
        date = str(day.get("timestamp") or "")[:10]
        count, unique = _count(day.get("count")), _count(day.get("uniques"))
        rows.append(
            ExploreRow(
                f"{section} on {date}: {_plural(count, noun)}, {_visitors(unique)}",
                f"{section} on {date}\n{_plural(count, noun)}, {_visitors(unique)}.\n{page}",
                page,
                repo,
                "insight",
                f"{kind}:{date}",
            )
        )
    return rows


def _popular_rows(repo: str, referrers: object, paths: object) -> list[ExploreRow]:
    page = f"https://github.com/{repo}/graphs/traffic"
    rows: list[ExploreRow] = []
    for row in referrers if isinstance(referrers, list) else ():
        if isinstance(row, dict) and row.get("referrer"):
            name = str(row["referrer"])
            count, unique = _count(row.get("count")), _count(row.get("uniques"))
            rows.append(
                ExploreRow(
                    f"Referring site {name}: {_plural(count, 'view')}, {_visitors(unique)}",
                    f"Referring site: {name}\n{_plural(count, 'view')}, {_visitors(unique)}, "
                    f"in the last 14 days.\n{page}",
                    page,
                    repo,
                    "insight",
                    f"referrer:{name}",
                )
            )
    for row in paths if isinstance(paths, list) else ():
        if isinstance(row, dict) and row.get("path"):
            path = str(row["path"])
            title = str(row.get("title") or path)
            count, unique = _count(row.get("count")), _count(row.get("uniques"))
            url = f"https://github.com{path}"
            rows.append(
                ExploreRow(
                    f"Popular page {title}: {_plural(count, 'view')}, {_visitors(unique)}",
                    f"Popular page: {title}\nPath: {path}\n{_plural(count, 'view')}, "
                    f"{_visitors(unique)}, in the last 14 days.\n{url}",
                    url,
                    repo,
                    "insight",
                    f"path:{path}",
                )
            )
    return rows


def _contributor_rows(repo: str, data: object, limit: int) -> list[ExploreRow]:
    rows: list[ExploreRow] = []
    for row in data if isinstance(data, list) else ():
        if not isinstance(row, dict) or not row.get("login"):
            continue
        login = str(row["login"])
        commits = _count(row.get("contributions"))
        url = str(row.get("html_url") or f"https://github.com/{login}")
        rows.append(
            ExploreRow(
                f"Contributor {login}: {_plural(commits, 'commit')}",
                f"Contributor: {login}\n{_plural(commits, 'commit')} on the default branch.\n{url}",
                url,
                repo,
                "person",
                login,
            )
        )
        if len(rows) >= limit:
            break
    return rows


def _total(data: object) -> tuple[int, int]:
    body = data if isinstance(data, dict) else {}
    return _count(body.get("count")), _count(body.get("uniques"))


def fetch_insights(
    token: str | None,
    repo: str,
    *,
    limit: int,
    warnings: list[str],
    get: Getter | None = None,
) -> list[ExploreRow]:
    """The summary sentence, then traffic, referrers, pages and contributors."""
    base = repo_path(repo)
    read = get or _getter(token)
    traffic: list[ExploreRow] = []
    views: object = None
    clones: object = None
    refused = ""
    try:
        views = read(f"{base}/traffic/views", None).data
        clones = read(f"{base}/traffic/clones", None).data
        referrers = read(f"{base}/traffic/popular/referrers", None).data
        paths = read(f"{base}/traffic/popular/paths", None).data
        traffic = (
            _traffic_rows(repo, "views", views)
            + _traffic_rows(repo, "clones", clones)
            + _popular_rows(repo, referrers, paths)
        )
    except GitHubRestError as exc:
        refused = traffic_refused_sentence(repo, exc)
        warnings.append(refused)
    people: list[ExploreRow] = []
    counting = False
    try:
        reply = read(f"{base}/contributors", {"per_page": str(max(1, min(limit, 100)))})
        counting = reply.status == 202
        people = _contributor_rows(repo, reply.data, limit)
    except GitHubRestError as exc:
        warnings.append(rest_failure_message("read the contributors", exc))
    parts: list[str] = []
    if traffic:
        views_total, views_unique = _total(views)
        clones_total, clones_unique = _total(clones)
        parts.append(
            f"{_plural(views_total, 'view')} ({views_unique:,} unique) and "
            f"{_plural(clones_total, 'clone')} ({clones_unique:,} unique) in the last 14 days"
        )
    if counting:
        parts.append("GitHub is still counting the contributors; refresh in a moment")
    else:
        parts.append(_plural(len(people), "contributor"))
    summary = f"{repo}: {', '.join(parts)}."
    if refused:
        summary += f" {refused}"
    page = f"https://github.com/{repo}/pulse"
    head = ExploreRow(summary, summary + f"\n{page}", page, repo, "insight", "summary")
    return [head, *traffic, *people]


_CHECKLIST = (
    ("readme", "README"),
    ("license", "License"),
    ("contributing", "Contributing guide"),
    ("code_of_conduct", "Code of conduct"),
    ("issue_template", "Issue templates"),
    ("pull_request_template", "Pull request template"),
)


def community_rows(repo: str, data: object) -> list[ExploreRow]:
    """GitHub's community checklist: the health percentage, then each item."""
    body: dict[str, Any] = data if isinstance(data, dict) else {}
    raw_files = body.get("files")
    files: dict[str, Any] = raw_files if isinstance(raw_files, dict) else {}
    present: list[str] = []
    missing: list[str] = []
    rows: list[ExploreRow] = []
    settings = f"https://github.com/{repo}/community"
    for key, name in _CHECKLIST:
        entry = files.get(key)
        here = isinstance(entry, dict) or (key == "issue_template" and bool(entry))
        (present if here else missing).append(name)
        url = ""
        if isinstance(entry, dict):
            url = str(entry.get("html_url") or entry.get("url") or "")
        rows.append(
            ExploreRow(
                f"{name}: {'present' if here else 'missing'}",
                f"{name} is {'present' if here else 'missing'} in {repo}.\n{url or settings}",
                url or settings,
                repo,
                "community",
                key,
            )
        )
    health = _count(body.get("health_percentage"))
    summary = f"Community profile for {repo}: {health} percent."
    if present:
        summary += f" Present: {', '.join(present)}."
    if missing:
        summary += f" Missing: {', '.join(missing)}."
    head = ExploreRow(summary, summary + f"\n{settings}", settings, repo, "community", "summary")
    return [head, *rows]


def fetch_community_profile(
    token: str | None, repo: str, *, get: Getter | None = None
) -> list[ExploreRow]:
    read = get or _getter(token)
    try:
        data = read(f"{repo_path(repo)}/community/profile", None).data
    except GitHubRestError as exc:
        raise GitHubExploreError(rest_failure_message("read the community profile", exc)) from exc
    return community_rows(repo, data)


__all__ = [
    "community_rows",
    "fetch_community_profile",
    "fetch_insights",
    "traffic_refused_sentence",
]
