"""Explore's searches beyond issues: code, commits and repositories.

Each is one GitHub REST search (``/search/code``, ``/search/commits``,
``/search/repositories``) given the query exactly as typed, so qualifiers such
as ``repo:``, ``language:`` and ``author:`` work as they do on github.com.
Results come back as :class:`~quill.core.github.explore_models.ExploreRow`
rows the Explore list reads one per line.

Code search asks for text-match fragments
(``application/vnd.github.text-match+json``). GitHub's API gives the matching
excerpt, not a line number in the file, so a code row reads as the path, the
line of the excerpt the match is on, and the words that matched:
``quill/core/paths.py: def app_data_dir() -> Path: (matched app_data_dir)``.

Search has its own allowance (30 requests a minute; 10 for code) and never
returns more than 1,000 results; a capped or incomplete answer says so.
No ``wx`` imports; strict-typed.
"""

from __future__ import annotations

from typing import Any

from quill.core.github.explore_models import ExploreRow, GitHubExploreError
from quill.core.github.rest_transport import GitHubRestError, request_json, rest_failure_message

SEARCH_VIEWS = frozenset({"code_search", "commit_search", "repo_search"})
_TEXT_MATCH = "application/vnd.github.text-match+json"
_ENDPOINT = {
    "code_search": "/search/code",
    "commit_search": "/search/commits",
    "repo_search": "/search/repositories",
}
_WHAT = {
    "code_search": "code",
    "commit_search": "commits",
    "repo_search": "repositories",
}


def _s(value: object) -> str:
    return str(value) if value is not None else ""


def _dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _repo_name(item: dict[str, Any]) -> str:
    repository = item.get("repository")
    return _s(repository.get("full_name")) if isinstance(repository, dict) else ""


def matching_line(fragment: str, start: int) -> str:
    """The whole line of *fragment* that holds character *start*, trimmed."""
    if not fragment:
        return ""
    start = max(0, min(start, len(fragment)))
    line_start = fragment.rfind("\n", 0, start) + 1
    line_end = fragment.find("\n", start)
    return fragment[line_start : line_end if line_end >= 0 else len(fragment)].strip()


def _text_matches(item: dict[str, Any]) -> list[tuple[str, str, tuple[str, ...]]]:
    """``(fragment, matching line, matched words)`` for each text match."""
    out: list[tuple[str, str, tuple[str, ...]]] = []
    for match in item.get("text_matches") or ():
        if not isinstance(match, dict):
            continue
        fragment = _s(match.get("fragment"))
        words: list[str] = []
        first = -1
        for hit in match.get("matches") or ():
            if not isinstance(hit, dict):
                continue
            text = _s(hit.get("text"))
            if text and text not in words:
                words.append(text)
            indices = hit.get("indices")
            if first < 0 and isinstance(indices, list) and indices and isinstance(indices[0], int):
                first = indices[0]
        if first < 0 and words:
            first = max(0, fragment.find(words[0]))
        out.append((fragment, matching_line(fragment, max(first, 0)), tuple(words)))
    return out


def code_row(item: dict[str, Any]) -> ExploreRow:
    repo = _repo_name(item)
    path = _s(item.get("path")) or _s(item.get("name"))
    url = _s(item.get("html_url"))
    matches = _text_matches(item)
    if matches:
        _fragment, line, words = matches[0]
        said = f" (matched {', '.join(words)})" if words else ""
        label = f"{path}: {line}{said}" if line else f"{path}{said}"
    else:
        label = path
    detail = [f"Code in {repo}", f"Path: {path}"]
    for index, (fragment, line, words) in enumerate(matches, 1):
        detail.append(f"Match {index}: {line}")
        if words:
            detail.append(f"Matched text: {', '.join(words)}")
        detail.append("Excerpt:")
        detail.append(fragment.strip())
    if not matches:
        detail.append("GitHub sent no excerpt for this file.")
    detail.append(url)
    return ExploreRow(label, "\n".join(detail), url, repo, "code", path)


def commit_row(item: dict[str, Any]) -> ExploreRow:
    repo = _repo_name(item)
    sha = _s(item.get("sha"))
    commit = _dict(item.get("commit"))
    message = _s(commit.get("message"))
    headline = message.splitlines()[0] if message else "(no message)"
    author_block = _dict(commit.get("author"))
    account = _dict(item.get("author"))
    who = _s(account.get("login")) or _s(author_block.get("name")) or "unknown author"
    when = _s(author_block.get("date"))[:10]
    url = _s(item.get("html_url"))
    label = f"{repo} {sha[:7]}: {headline}, by {who}" + (f", {when}" if when else "")
    detail = (
        f"Commit {sha} in {repo}\nAuthor: {who}\nDate: {_s(author_block.get('date'))}\n\n"
        f"{message}\n{url}"
    )
    return ExploreRow(label, detail, url, repo, "commit", sha, _s(author_block.get("date")))


def repository_row(item: dict[str, Any]) -> ExploreRow:
    name = _s(item.get("full_name"))
    description = _s(item.get("description"))
    url = _s(item.get("html_url"))
    stars = int(item.get("stargazers_count") or 0)
    language = _s(item.get("language"))
    facts = [f"{stars:,} star{'' if stars == 1 else 's'}"]
    if language:
        facts.append(language)
    if item.get("archived"):
        facts.append("archived")
    if item.get("fork"):
        facts.append("fork")
    label = f"{name}: {description}" if description else name
    label += f" ({', '.join(facts)})"
    detail = (
        f"Repository: {name}\n{description}\n{'; '.join(facts)}\n"
        f"Updated: {_s(item.get('updated_at'))}\n{url}"
    )
    return ExploreRow(label, detail, url, name, "repo", name, _s(item.get("updated_at")))


_MAPPERS = {
    "code_search": code_row,
    "commit_search": commit_row,
    "repo_search": repository_row,
}


def run_search(
    token: str | None, view: str, query: str, *, limit: int, warnings: list[str]
) -> list[ExploreRow]:
    """Run one search view; capped or incomplete answers add a warning."""
    if view not in SEARCH_VIEWS:
        raise GitHubExploreError(f"Unknown GitHub search: {view}")
    if not query.strip():
        raise GitHubExploreError("Enter a search query first.")
    if view == "code_search" and not token:
        raise GitHubExploreError("GitHub's code search needs a signed-in account.")
    per_page = max(1, min(limit, 100))
    headers = {"Accept": _TEXT_MATCH} if view == "code_search" else None
    try:
        response = request_json(
            token,
            "GET",
            _ENDPOINT[view],
            query={"q": query.strip(), "per_page": str(per_page)},
            extra_headers=headers,
        )
    except GitHubRestError as exc:
        if exc.status == 422:
            detail = exc.data.get("message", "") if isinstance(exc.data, dict) else ""
            raise GitHubExploreError(
                f"GitHub could not run that {_WHAT[view]} search: "
                f"{detail or 'check the query and its qualifiers'}."
            ) from exc
        raise GitHubExploreError(rest_failure_message(f"search {_WHAT[view]}", exc)) from exc
    data = response.data if isinstance(response.data, dict) else {}
    items = [item for item in data.get("items") or () if isinstance(item, dict)][:per_page]
    total = int(data.get("total_count") or 0)
    if data.get("incomplete_results"):
        warnings.append("GitHub's search timed out early, so some matches may be missing")
    if total > len(items):
        warnings.append(f"showing the first {len(items):,} of {total:,} matches")
    mapper = _MAPPERS[view]
    return [mapper(item) for item in items]


__all__ = [
    "SEARCH_VIEWS",
    "code_row",
    "commit_row",
    "matching_line",
    "repository_row",
    "run_search",
]
