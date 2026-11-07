"""Bounded mapping of a single GitHub issue or pull-request comment thread."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.reactions import reaction_counts_in_words


def list_comments(
    repo: Any,
    number: int,
    *,
    limit: int,
    take: Callable[[Any, int], list[Any]],
    safe_str: Callable[[object], str],
    login_of: Callable[[object], str],
    iso: Callable[[Any], str],
) -> list[dict[str, str]]:
    issue = repo.get_issue(number=number)
    comments = take(issue.get_comments(), limit)
    return [
        {
            "id": safe_str(getattr(comment, "id", "")),
            "author": login_of(getattr(comment, "user", None)),
            "created_at": iso(getattr(comment, "created_at", None)),
            "body": safe_str(getattr(comment, "body", "")),
            "reactions": reaction_counts_in_words(_reactions_of(comment)),
        }
        for comment in comments
    ]


def _reactions_of(comment: Any) -> object:
    # The list response already carries the reaction summary; reading it costs no request.
    try:
        return getattr(comment, "reactions", None)
    except Exception:  # noqa: BLE001 - an older PyGithub may lack the attribute
        return None
