"""Bounded, read-only GitHub Discussions view for the shared Explore dialog."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from quill.core.github.explore_models import ExploreRow, GitHubExploreError, _text
from quill.core.net import verified_ssl_context

_PAGE_SIZE = 50
_MAX_LIMIT = 100
_MAX_BODY_CHARS = 8_000

_DISCUSSIONS_QUERY = """
query($owner:String!, $repo:String!, $first:Int!, $after:String) {
  repository(owner:$owner, name:$repo) {
    discussions(first:$first, after:$after, orderBy:{field:UPDATED_AT,direction:DESC}) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes {
        number title bodyText url createdAt updatedAt closed
        author { login }
        category { name emoji isAnswerable }
        answer { isAnswer bodyText url author { login } }
      }
    }
  }
}
"""
_DISCUSSION_QUERY = """
query($owner:String!, $repo:String!, $number:Int!) {
  repository(owner:$owner, name:$repo) {
    discussion(number:$number) {
      number title bodyText url createdAt updatedAt closed
      author { login }
      category { name emoji isAnswerable }
      answer { isAnswer bodyText url author { login } }
    }
  }
}
"""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_args: object, **_kwargs: object) -> None:
        return None


def _request(token: str, query: str, variables: dict[str, object]) -> dict[str, Any]:
    request = Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "QUILL-GitHub-Workbench",
        },
        method="POST",
    )
    try:
        opener = build_opener(_NoRedirect, HTTPSHandler(context=verified_ssl_context()))
        with opener.open(request, timeout=20) as response:
            payload = json.load(response)
    except HTTPError as exc:
        if exc.code in (301, 302, 303, 307, 308):
            raise GitHubExploreError(
                "GitHub redirected the Discussions request; credentials were not forwarded."
            ) from exc
        if exc.code in (401, 403):
            raise GitHubExploreError(
                "GitHub denied the Discussions request. Check repository access "
                "and organization SSO."
            ) from exc
        raise GitHubExploreError(f"GitHub returned HTTP {exc.code} for Discussions.") from exc
    except Exception as exc:  # noqa: BLE001 - network failures are user-visible
        raise GitHubExploreError(f"Could not load GitHub Discussions: {exc}") from exc
    if not isinstance(payload, dict):
        raise GitHubExploreError("GitHub returned an invalid Discussions response.")
    errors = payload.get("errors")
    if errors:
        messages = [row.get("message", "error") for row in errors if isinstance(row, dict)]
        raise GitHubExploreError(
            "; ".join(str(message) for message in messages) or "GitHub rejected the request."
        )
    data = payload.get("data")
    if not isinstance(data, dict):
        raise GitHubExploreError("GitHub returned no Discussions data.")
    return data


def _map(row: Any, repository: str) -> ExploreRow:
    number = row.get("number") if isinstance(row, dict) else 0
    if isinstance(number, bool) or not isinstance(number, int) or number <= 0:
        raise GitHubExploreError("GitHub returned a Discussion without a valid number.")
    title = _text(row.get("title"))[:512]
    body = _text(row.get("bodyText"))[:_MAX_BODY_CHARS]
    url = _text(row.get("url"))[:2048]
    author_data = row.get("author")
    author = _text(author_data.get("login")) if isinstance(author_data, dict) else "unknown"
    category_data = row.get("category")
    category = _text(category_data.get("name")) if isinstance(category_data, dict) else ""
    emoji = _text(category_data.get("emoji")) if isinstance(category_data, dict) else ""
    updated_at = _text(row.get("updatedAt"))
    created_at = _text(row.get("createdAt"))
    closed = bool(row.get("closed", False))
    answer_data = row.get("answer")
    answer = answer_data if isinstance(answer_data, dict) else None
    answer_body = _text(answer.get("bodyText"))[:2_000] if answer else ""
    answer_author_data = answer.get("author") if answer else None
    answer_author = (
        _text(answer_author_data.get("login")) if isinstance(answer_author_data, dict) else ""
    )
    state = "closed" if closed else "open"
    answer_status = f"Answered by {answer_author}." if answer_author else "Unanswered."
    category_label = f"{emoji} {category}".strip()
    label = f"#{number} {title} ({category_label}; {answer_status[:-1]})"
    details = [
        f"{repository} Discussion #{number}: {title}",
        f"Category: {category_label or 'uncategorized'}",
        f"Author: {author}",
        f"State: {state}",
        f"Created: {created_at}",
        f"Updated: {updated_at}",
        answer_status,
    ]
    if body:
        details.extend(["", body])
    if answer_body:
        details.extend(["", "Chosen answer:", answer_body])
    if url:
        details.extend(["", url])
    return ExploreRow(
        label=label,
        detail="\n".join(details),
        url=url,
        repo=repository,
        kind="discussion",
        key=str(number),
        updated_at=updated_at,
        title=title,
    )


def list_discussions(
    token: str | None,
    repository: str,
    *,
    limit: int = 50,
) -> tuple[list[ExploreRow], bool, str]:
    """Fetch an ordered, bounded page; incomplete pagination is never hidden."""
    if not token:
        raise GitHubExploreError("Sign in to GitHub to view repository Discussions.")
    parts = repository.split("/", 1)
    if len(parts) != 2 or not all(part.strip() for part in parts):
        raise GitHubExploreError("Enter a repository as owner/repo to view Discussions.")
    requested = max(1, min(limit, _MAX_LIMIT))
    page_size = min(_PAGE_SIZE, requested)
    after: str | None = None
    rows: list[ExploreRow] = []
    while len(rows) < requested:
        data = _request(
            token,
            _DISCUSSIONS_QUERY,
            {
                "owner": parts[0],
                "repo": parts[1],
                "first": min(page_size, requested - len(rows)),
                "after": after,
            },
        )
        try:
            connection = data["repository"]["discussions"]
            nodes = connection["nodes"]
            page_info = connection["pageInfo"]
            total_count = connection["totalCount"]
        except (KeyError, TypeError) as exc:
            raise GitHubExploreError("GitHub returned incomplete Discussions data.") from exc
        if not isinstance(nodes, list) or not isinstance(page_info, dict):
            raise GitHubExploreError("GitHub returned malformed Discussions pagination data.")
        rows.extend(_map(row, repository) for row in nodes)
        has_next = page_info.get("hasNextPage")
        if not isinstance(has_next, bool):
            raise GitHubExploreError("GitHub returned invalid Discussions page status.")
        if not has_next:
            return rows, True, ""
        cursor = page_info.get("endCursor")
        if not isinstance(cursor, str) or not cursor or cursor == after:
            raise GitHubExploreError("GitHub returned an invalid Discussions page cursor.")
        after = cursor
        if len(rows) >= requested:
            warning = (
                f"Showing {len(rows)} of {total_count} discussions; more results are available."
                if isinstance(total_count, int) and total_count > len(rows)
                else "More Discussions may exist beyond this page."
            )
            return rows[:requested], False, warning
    return rows[:requested], True, ""


def fetch_discussion(token: str | None, repository: str, number: int) -> ExploreRow:
    """Fetch one discussion by its exact repository number."""
    if not token:
        raise GitHubExploreError("Sign in to GitHub to view repository Discussions.")
    parts = repository.split("/", 1)
    if len(parts) != 2 or not all(part.strip() for part in parts):
        raise GitHubExploreError("Enter a repository as owner/repo to view Discussions.")
    if number <= 0:
        raise GitHubExploreError("Discussion numbers must be positive.")
    data = _request(
        token,
        _DISCUSSION_QUERY,
        {"owner": parts[0], "repo": parts[1], "number": number},
    )
    try:
        discussion = data["repository"]["discussion"]
    except (KeyError, TypeError) as exc:
        raise GitHubExploreError("GitHub returned incomplete Discussion data.") from exc
    if not isinstance(discussion, dict):
        raise GitHubExploreError(f"Discussion #{number} was not found in {repository}.")
    return _map(discussion, repository)


__all__ = ["fetch_discussion", "list_discussions"]
