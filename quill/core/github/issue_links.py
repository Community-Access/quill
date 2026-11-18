"""Undoing two links an issue can carry: a linked branch, and "duplicate of" (PRD 14.1).

* **Unlink Branch...** lists the branches linked to an issue (its
  Development on GitHub) and unlinks the one chosen (``deleteLinkedBranch``).
  The branch itself stays; only the link goes.
* **Not a Duplicate...** takes back "duplicate of #n" (``unmarkIssueAsDuplicate``)
  when an issue was closed as a duplicate of the wrong one. It does not
  reopen the issue; Close or Reopen does that.

Takes the Workbench's :class:`~quill.core.github.workbench_api.GitHubApi`.
wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from quill.core.error_codes import CodedError
from quill.core.github.workbench_api import GitHubApi

__all__ = [
    "IssueLinkError",
    "LinkedBranch",
    "linked_branch_ids",
    "not_a_duplicate",
    "unlink_branch",
]


class IssueLinkError(CodedError):
    """A link could not be read or undone; the message is said."""

    code = "QUILL-GITHUB-ISSUE-LINKS"


@dataclass(frozen=True)
class LinkedBranch:
    id: str
    name: str


_LINKED = (
    "query($o:String!,$n:String!,$i:Int!){repository(owner:$o,name:$n){"
    "issue(number:$i){linkedBranches(first:20){nodes{id ref{name}}}}}}"
)
_UNLINK = "mutation($id:ID!){deleteLinkedBranch(input:{linkedBranchId:$id}){clientMutationId}}"
_ISSUE = (
    "query($o:String!,$n:String!,$i:Int!){repository(owner:$o,name:$n){issue(number:$i){id title}}}"
)
_UNMARK = (
    "mutation($dup:ID!,$canon:ID!){unmarkIssueAsDuplicate("
    "input:{duplicateId:$dup,canonicalId:$canon}){clientMutationId}}"
)


def _split(repository: str) -> tuple[str, str]:
    owner, _slash, name = repository.partition("/")
    if not owner or not name:
        raise IssueLinkError(f"{repository!r} is not owner/name.")
    return owner, name


def linked_branch_ids(api: GitHubApi, repository: str, number: int) -> list[LinkedBranch]:
    owner, name = _split(repository)
    data = api.graphql(_LINKED, {"o": owner, "n": name, "i": int(number)})
    repo = data.get("repository") if isinstance(data, Mapping) else None
    issue = repo.get("issue") if isinstance(repo, Mapping) else None
    links = issue.get("linkedBranches") if isinstance(issue, Mapping) else None
    found = []
    for node in (links.get("nodes") if isinstance(links, Mapping) else None) or ():
        ref = node.get("ref") if isinstance(node, Mapping) else None
        if isinstance(ref, Mapping) and node.get("id"):
            found.append(LinkedBranch(str(node["id"]), str(ref.get("name") or "")))
    return found


def unlink_branch(api: GitHubApi, number: int, branch: LinkedBranch) -> str:
    api.graphql(_UNLINK, {"id": branch.id})
    return f"Unlinked {branch.name} from #{number}. The branch is still there."


def _issue(api: GitHubApi, repository: str, number: int) -> tuple[str, str]:
    owner, name = _split(repository)
    data = api.graphql(_ISSUE, {"o": owner, "n": name, "i": int(number)})
    repo = data.get("repository") if isinstance(data, Mapping) else None
    issue = repo.get("issue") if isinstance(repo, Mapping) else None
    if not isinstance(issue, Mapping) or not issue.get("id"):
        raise IssueLinkError(f"{repository} has no issue #{number}.")
    return str(issue["id"]), str(issue.get("title") or "")


def not_a_duplicate(api: GitHubApi, repository: str, number: int, original: int) -> str:
    """Take back "#*number* is a duplicate of #*original*"."""
    if int(number) == int(original):
        raise IssueLinkError(f"#{number} cannot be a duplicate of itself.")
    duplicate, _title = _issue(api, repository, number)
    canonical, title = _issue(api, repository, original)
    api.graphql(_UNMARK, {"dup": duplicate, "canon": canonical})
    return f"#{number} is no longer marked a duplicate of #{original}" + (
        f", {title}." if title else "."
    )
