"""Read as Document (PRD 22.3): an issue, pull request or discussion as one document.

The thread is read fresh through :class:`quill.core.github.workbench_api.GitHubApi`
and written as Markdown a screen reader moves through by heading: the title is
heading 1; the opening post, then each comment, review and reply is a heading
2 (or 3 for a reply, or a line comment under its review) that names its author
and date. Bodies are kept as GitHub wrote them, so code blocks, links,
headings and lists survive; a line comment says the file and line before its
text. :func:`thread_html` is the same document through the editor's own
Markdown export, for saving as HTML.

Reads only: the issue or pull request and its comments, a pull request's
reviews and review comments (REST), or a discussion with its comments and
replies (GraphQL, with ``body`` so Markdown survives). wx-free, strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from quill.core.github.workbench_api import GitHubApi

__all__ = [
    "ThreadDocument",
    "ThreadEntry",
    "fetch_thread",
    "suggested_name",
    "thread_html",
    "thread_markdown",
]

_PAGES = 5
_PER_PAGE = "100"

_DISCUSSION_QUERY = """
query($owner:String!, $repo:String!, $number:Int!) {
  repository(owner:$owner, name:$repo) {
    discussion(number:$number) {
      number title body url createdAt closed
      author { login }
      category { name }
      answer { id }
      comments(first:100) {
        totalCount
        nodes {
          id body url createdAt isAnswer author { login }
          replies(first:100) { totalCount nodes { id body url createdAt author { login } } }
        }
      }
    }
  }
}
"""


@dataclass(frozen=True)
class ThreadEntry:
    """One post in the thread: its heading words, its body, its depth."""

    heading: str
    author: str
    date: str
    body: str
    level: int = 2
    url: str = ""
    note: str = ""


@dataclass(frozen=True)
class ThreadDocument:
    kind: str  # "issue", "pull request" or "discussion"
    repository: str
    number: int
    title: str
    url: str
    state: str
    entries: tuple[ThreadEntry, ...] = ()
    warnings: tuple[str, ...] = field(default=())


def _login(node: object, key: str = "user") -> str:
    value = node.get(key) if isinstance(node, Mapping) else None
    return str(value.get("login", "")) if isinstance(value, Mapping) else ""


def _date(value: object) -> str:
    text = str(value or "")
    return text[:10] if len(text) >= 10 else text


def _pages(api: GitHubApi, path: str) -> tuple[list[dict[str, Any]], bool]:
    """Up to :data:`_PAGES` pages of a list; (rows, complete)."""
    rows: list[dict[str, Any]] = []
    for page in range(1, _PAGES + 1):
        data = api.rest("GET", path, query={"per_page": _PER_PAGE, "page": str(page)}).data
        batch = [row for row in data if isinstance(row, dict)] if isinstance(data, list) else []
        rows.extend(batch)
        if len(batch) < int(_PER_PAGE):
            return rows, True
    return rows, False


def fetch_thread(api: GitHubApi, repository: str, number: int, kind: str) -> ThreadDocument:
    """Read the whole thread. *kind* is ``issue``, ``pull_request`` or ``discussion``."""
    if kind == "discussion":
        return _fetch_discussion(api, repository, number)
    issue = api.rest("GET", f"/repos/{repository}/issues/{number}").data
    issue = issue if isinstance(issue, dict) else {}
    is_pr = kind == "pull_request" or "pull_request" in issue
    warnings: list[str] = []
    entries: list[ThreadEntry] = [
        ThreadEntry(
            "Opening post",
            _login(issue),
            _date(issue.get("created_at")),
            str(issue.get("body") or ""),
            url=str(issue.get("html_url") or ""),
        )
    ]
    timed: list[tuple[str, ThreadEntry]] = []
    comments, complete = _pages(api, f"/repos/{repository}/issues/{number}/comments")
    if not complete:
        warnings.append("Only the first 500 comments are here; open it on GitHub for the rest.")
    for row in comments:
        timed.append((
            str(row.get("created_at") or ""),
            ThreadEntry(
                "Comment",
                _login(row),
                _date(row.get("created_at")),
                str(row.get("body") or ""),
                url=str(row.get("html_url") or ""),
            ),
        ))
    if is_pr:
        reviews, _ = _pages(api, f"/repos/{repository}/pulls/{number}/reviews")
        line_comments, _ = _pages(api, f"/repos/{repository}/pulls/{number}/comments")
        by_review: dict[object, list[dict[str, Any]]] = {}
        for row in line_comments:
            by_review.setdefault(row.get("pull_request_review_id"), []).append(row)
        for review in reviews:
            state = str(review.get("state") or "").replace("_", " ").lower()
            if state == "pending":
                continue
            when = str(review.get("submitted_at") or "")
            timed.append((
                when,
                ThreadEntry(
                    "Review",
                    _login(review),
                    _date(when),
                    str(review.get("body") or ""),
                    url=str(review.get("html_url") or ""),
                    note=state.capitalize() if state else "",
                ),
            ))
            for line in by_review.pop(review.get("id"), []):
                timed.append((when, _line_entry(line)))
        for rest in by_review.values():
            for line in rest:
                timed.append((str(line.get("created_at") or ""), _line_entry(line)))
    timed.sort(key=lambda pair: pair[0])
    entries.extend(entry for _when, entry in timed)
    state = str(issue.get("state") or "")
    pull = issue.get("pull_request")
    if is_pr and isinstance(pull, dict) and pull.get("merged_at"):
        state = "merged"
    return ThreadDocument(
        "pull request" if is_pr else "issue",
        repository,
        number,
        str(issue.get("title") or ""),
        str(issue.get("html_url") or ""),
        state,
        tuple(entries),
        tuple(warnings),
    )


def _line_entry(row: Mapping[str, Any]) -> ThreadEntry:
    line = row.get("line") or row.get("original_line") or ""
    where = f"{row.get('path', '')}, line {line}" if line else str(row.get("path", ""))
    return ThreadEntry(
        "Line comment",
        _login(row),
        _date(row.get("created_at")),
        str(row.get("body") or ""),
        level=3,
        url=str(row.get("html_url") or ""),
        note=f"On {where}" if where else "",
    )


def _fetch_discussion(api: GitHubApi, repository: str, number: int) -> ThreadDocument:
    owner, _, name = repository.partition("/")
    data = api.graphql(_DISCUSSION_QUERY, {"owner": owner, "repo": name, "number": number})
    repo = data.get("repository") if isinstance(data, dict) else None
    node = repo.get("discussion") if isinstance(repo, dict) else None
    if not isinstance(node, dict):
        raise ValueError(f"Discussion #{number} was not found in {repository}.")
    category = node.get("category")
    entries = [
        ThreadEntry(
            "Opening post",
            _login(node, "author"),
            _date(node.get("createdAt")),
            str(node.get("body") or ""),
            url=str(node.get("url") or ""),
            note=f"Category: {category.get('name')}" if isinstance(category, dict) else "",
        )
    ]
    raw_comments = node.get("comments")
    connection: dict[str, Any] = raw_comments if isinstance(raw_comments, dict) else {}
    comments = [c for c in connection.get("nodes") or () if isinstance(c, dict)]
    for comment in comments:
        entries.append(
            ThreadEntry(
                "Answer" if comment.get("isAnswer") else "Comment",
                _login(comment, "author"),
                _date(comment.get("createdAt")),
                str(comment.get("body") or ""),
                url=str(comment.get("url") or ""),
            )
        )
        raw_replies = comment.get("replies")
        replies: dict[str, Any] = raw_replies if isinstance(raw_replies, dict) else {}
        for reply in replies.get("nodes") or ():
            if isinstance(reply, dict):
                entries.append(
                    ThreadEntry(
                        "Reply",
                        _login(reply, "author"),
                        _date(reply.get("createdAt")),
                        str(reply.get("body") or ""),
                        level=3,
                        url=str(reply.get("url") or ""),
                    )
                )
    warnings: list[str] = []
    total = connection.get("totalCount")
    if isinstance(total, int) and total > len(comments):
        warnings.append(f"Only the first {len(comments)} of {total} comments are here.")
    return ThreadDocument(
        "discussion",
        repository,
        int(node.get("number") or number),
        str(node.get("title") or ""),
        str(node.get("url") or ""),
        "closed" if node.get("closed") else "open",
        tuple(entries),
        tuple(warnings),
    )


def _heading(entry: ThreadEntry) -> str:
    who = entry.author or "unknown"
    when = f", {entry.date}" if entry.date else ""
    return f"{'#' * entry.level} {entry.heading} by {who}{when}"


def thread_markdown(doc: ThreadDocument) -> str:
    """The document as Markdown: a heading per post, bodies as GitHub wrote them."""
    kind = doc.kind.capitalize()
    lines = [
        f"# {kind} {doc.repository}#{doc.number}: {doc.title}",
        "",
        f"State: {doc.state or 'unknown'}. {len(doc.entries)} posts. Source: <{doc.url}>"
        if doc.url
        else f"State: {doc.state or 'unknown'}. {len(doc.entries)} posts.",
    ]
    lines.extend(f"\n{warning}" for warning in doc.warnings)
    for entry in doc.entries:
        lines.extend(["", _heading(entry), ""])
        if entry.note:
            lines.extend([f"{entry.note}.", ""])
        body = entry.body.strip()
        lines.append(body if body else "(No text.)")
        if entry.url:
            lines.extend(["", f"Link: <{entry.url}>"])
    return "\n".join(lines).rstrip() + "\n"


def thread_html(doc: ThreadDocument) -> str:
    """The same document as HTML, through the editor's own Markdown export."""
    from quill.io.export import markdown_to_html

    return markdown_to_html(thread_markdown(doc), f"{doc.repository}#{doc.number} {doc.title}")


def suggested_name(doc: ThreadDocument, extension: str = ".md") -> str:
    """A file name: ``owner-name-issue-42.md``."""
    safe = doc.repository.replace("/", "-")
    kind = {"pull request": "pr", "discussion": "discussion"}.get(doc.kind, "issue")
    keep = "".join(c if c.isalnum() or c in "-_." else "-" for c in f"{safe}-{kind}-{doc.number}")
    return keep + extension
