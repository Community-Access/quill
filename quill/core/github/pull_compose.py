"""Opening a pull request well: prefill, the existing-PR check, and kept drafts.

The Workbench's New Pull Request (Ctrl+N on Pull Requests, or from a
comparison) uses these so that, like GHManage's (v1.0.0):

* the title and description start from what is being proposed -- one commit
  gives its subject and body, several give the head branch's name in words;
* a branch that already has an open pull request into the same base opens
  that one instead of starting a duplicate GitHub would refuse;
* an unsent draft is kept per (repository, base, head) for the session, so
  Cancel never throws away a description somebody typed, and is dropped once
  GitHub has the pull request, so it cannot be sent twice.

No ``wx`` imports; strict-typed. The network calls are the provider's own
(``fetch_pulls`` is not used: one ``GET /repos/{r}/pulls?head=&base=``).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

__all__ = [
    "PullDraft",
    "describe_refusal",
    "drop_draft",
    "find_open_pull",
    "open_pull_item",
    "keep_draft",
    "kept_draft",
    "prefill",
]


@dataclass(frozen=True, slots=True)
class PullDraft:
    """What the New Pull Request window holds."""

    repository: str
    base: str
    head: str
    title: str = ""
    body: str = ""
    draft: bool = False


_KEPT: dict[tuple[str, str, str], PullDraft] = {}


def _key(repository: str, base: str, head: str) -> tuple[str, str, str]:
    return (repository.lower(), base, head)


def keep_draft(draft: PullDraft) -> None:
    """Keep *draft* for this session (Cancel, or a failed send)."""
    if draft.title.strip() or draft.body.strip():
        _KEPT[_key(draft.repository, draft.base, draft.head)] = draft


def kept_draft(repository: str, base: str, head: str) -> PullDraft | None:
    return _KEPT.get(_key(repository, base, head))


def drop_draft(repository: str, base: str, head: str) -> None:
    """GitHub has the pull request (or may have it): never offer to send it again."""
    _KEPT.pop(_key(repository, base, head), None)


def _words(branch: str) -> str:
    """``fix/login-crash_2`` -> "Fix login crash 2"."""
    tail = branch.rsplit("/", 1)[-1]
    text = re.sub(r"[-_.]+", " ", tail).strip()
    return text[:1].upper() + text[1:] if text else branch


def prefill(repository: str, base: str, head: str, commit_messages: Sequence[str]) -> PullDraft:
    """The starting title and body: a kept draft first, else from the commits."""
    kept = kept_draft(repository, base, head)
    if kept is not None:
        return kept
    messages = [m for m in commit_messages if m.strip()]
    if len(messages) == 1:
        subject, _, body = messages[0].strip().partition("\n")
        return PullDraft(repository, base, head, subject.strip(), body.strip())
    return PullDraft(repository, base, head, _words(head), "")


def describe_refusal(base: str, head: str, *, ahead_by: int | None) -> str:
    """Why a pull request cannot start here ("" when it can)."""
    if not head or not base:
        return "Choose the branch to merge from and the branch to merge into."
    if head == base:
        return "The two branches are the same branch. Choose a different one to merge from."
    if ahead_by is not None and ahead_by <= 0:
        return (
            f"{head} has nothing that {base} does not already have, so there is nothing to propose."
        )
    return ""


def find_open_pull(repo: Any, base: str, head: str) -> Any | None:
    """The open pull request from *head* into *base* on a PyGithub *repo*, or None.

    GitHub's ``head`` filter wants ``owner:branch``; the owner is the
    repository's, which is right for a branch in the same repository (the
    only kind the Workbench offers).
    """
    owner = str(getattr(getattr(repo, "owner", None), "login", "") or "")
    qualified = f"{owner}:{head}" if owner else head
    for row in repo.get_pulls(state="open", base=base, head=qualified):
        return row
    return None


def open_pull_item(provider: Any, full_name: str, base: str, head: str) -> Any | None:
    """:func:`find_open_pull` through a ``GitHubItemsProvider``, as its ``GitHubItem``.

    Lives here rather than on the provider to keep that module under its
    GATE-11 budget, the way :mod:`quill.core.github.branch_compare` does.
    """
    from quill.core.github.items_errors import GitHubItemsError

    repo = provider._repo(full_name)
    try:
        row = find_open_pull(repo, base, head)
    except Exception as exc:  # noqa: BLE001
        raise GitHubItemsError(f"Could not check for an open pull request: {exc}") from exc
    return None if row is None else provider._map_issue(row, is_pr=True)
