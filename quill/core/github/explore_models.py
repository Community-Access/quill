"""Plain models and bounded row mappers shared by GitHub Explore views."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from quill.core.error_codes import CodedError


class GitHubExploreError(CodedError):
    """A GitHub discovery view or action could not be completed."""

    code = "QUILL-GITHUB-EXPLORE-ERROR"


@dataclass(frozen=True, slots=True)
class ExploreRow:
    label: str
    detail: str
    url: str = ""
    repo: str = ""
    kind: str = ""
    key: str = ""
    updated_at: str = ""
    title: str = ""


def _text(value: object) -> str:
    return str(value) if value is not None else ""


def _date(value: object) -> str:
    return _text(value.isoformat() if hasattr(value, "isoformat") else value)


def _rows(iterable: Any, limit: int, *, source: str, warnings: list[str]) -> list[Any]:
    """Load a bounded page, retaining rows and describing incomplete reads."""
    rows: list[Any] = []
    try:
        iterator = iter(() if iterable is None else iterable)
        while len(rows) < limit:
            try:
                rows.append(next(iterator))
            except StopIteration:
                return rows
        try:
            next(iterator)
        except StopIteration:
            return rows
        except Exception as exc:  # noqa: BLE001 - preserve rows and report partial data
            warnings.append(f"{source}: loading stopped after {len(rows)} item(s): {exc}")
            return rows
        warnings.append(f"{source}: showing the first {limit} items; more may exist")
    except Exception as exc:  # noqa: BLE001 - preserve rows and report partial data
        warnings.append(f"{source}: results may be incomplete: {exc}")
    return rows


def _repo_row(row: Any, source: str = "") -> ExploreRow:
    name = _text(getattr(row, "full_name", ""))
    description = _text(getattr(row, "description", ""))
    url = _text(getattr(row, "html_url", ""))
    detail = f"Repository: {name}\n{description}\nSource: {source}\n{url}"
    return ExploreRow(name, detail.strip(), url, name, "repo")


def _person_row(row: Any, source: str) -> ExploreRow:
    login = _text(getattr(row, "login", ""))
    url = _text(getattr(row, "html_url", ""))
    return ExploreRow(login, f"{source}: @{login}\n{url}", url, kind="person", key=login)


def _issue_row(row: Any, source: str) -> ExploreRow:
    repo = _text(getattr(getattr(row, "repository", None), "full_name", ""))
    number = int(getattr(row, "number", 0) or 0)
    title = _text(getattr(row, "title", ""))
    url = _text(getattr(row, "html_url", ""))
    is_pr = "/pull/" in url or bool(getattr(row, "pull_request", None))
    kind = "PR" if is_pr else "issue"
    label = f"{repo} #{number}: {title} ({kind})"
    updated_at = _date(getattr(row, "updated_at", None))
    detail = f"{source}\n{label}\nState: {_text(getattr(row, 'state', ''))}"
    if updated_at:
        detail += f"\nUpdated: {updated_at}"
    detail += f"\n{url}"
    return ExploreRow(
        label,
        detail,
        url,
        repo,
        "pr" if is_pr else "issue",
        str(number),
        updated_at,
        title,
    )


def _event_row(row: Any, source: str) -> ExploreRow:
    actor = _text(getattr(getattr(row, "actor", None), "login", ""))
    repo = _text(getattr(getattr(row, "repo", None), "name", ""))
    event = _text(getattr(row, "type", "Event")).removesuffix("Event")
    when = _date(getattr(row, "created_at", None))
    url = f"https://github.com/{repo}" if repo else ""
    label = f"{event}: {repo} — {actor}"
    return ExploreRow(label, f"{source}\n{label}\n{when}\n{url}", url, repo, "event")


__all__ = ["ExploreRow", "GitHubExploreError"]
