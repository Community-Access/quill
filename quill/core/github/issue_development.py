"""Closing an issue with its reason, its development branches, and its task list (GH-D).

GitHub closes an issue as completed, as not planned, or as a duplicate of
another issue; only the last needs a second issue, and only GraphQL records
which (``closeIssue`` with ``duplicateIssueId``), so that one goes through
GraphQL and the other two through the REST ``state_reason`` the issue sheet
already writes. An issue's development is the branches linked to it
(``linkedBranches``) and the pull requests that close it; a branch made for
it here is linked the way GitHub's own "Create a branch" links it
(``createLinkedBranch``), so it shows under the issue's Development on the
web too.

An issue's task list is the ``- [ ]`` lines of its body. :func:`toggle_task`
checks or unchecks one, and :func:`linked_body` rewrites the items made into
sub-issues as ``#number``, which GitHub shows as the issue and its state.

Every function takes the Workbench's :class:`~quill.core.github.workbench_api.GitHubApi`,
so tests pass recorded answers. wx-free and strict-typed.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.github.workbench_api import GitHubApi

__all__ = [
    "CLOSE_REASONS",
    "CloseReason",
    "IssueDevelopmentError",
    "TaskItem",
    "branch_name_for",
    "close_issue",
    "convertible",
    "create_linked_branch",
    "linked_body",
    "linked_branches",
    "task_items",
    "toggle_task",
    "valid_branch_name",
]


class IssueDevelopmentError(CodedError):
    """A close or a linked branch GitHub would refuse, said in one sentence."""

    code = "QUILL-GITHUB-ISSUE-DEVELOPMENT"


@dataclass(frozen=True)
class CloseReason:
    label: str
    """What the chooser shows."""
    rest: str
    """The REST ``state_reason``."""
    said: str
    """The end of the sentence said after: "Closed #42 as ..."."""


CLOSE_REASONS: tuple[CloseReason, ...] = (
    CloseReason("Completed", "completed", "completed"),
    CloseReason("Not planned", "not_planned", "not planned"),
    CloseReason("Duplicate of another issue...", "duplicate", "a duplicate"),
)

_NODE_QUERY = (
    "query($o:String!,$n:String!,$i:Int!){repository(owner:$o,name:$n){id "
    "issue(number:$i){id title state}}}"
)

_CLOSE_DUPLICATE = (
    "mutation($id:ID!,$dup:ID!){closeIssue(input:{issueId:$id,stateReason:DUPLICATE,"
    "duplicateIssueId:$dup}){issue{number state stateReason}}}"
)

_LINKED_QUERY = (
    "query($o:String!,$n:String!,$i:Int!){repository(owner:$o,name:$n){"
    "issue(number:$i){linkedBranches(first:20){nodes{ref{name}}}}}}"
)

_CREATE_LINKED = (
    "mutation($issue:ID!,$oid:GitObjectID!,$name:String!,$repo:ID!){createLinkedBranch("
    "input:{issueId:$issue,oid:$oid,name:$name,repositoryId:$repo}){linkedBranch{ref{name}}}}"
)


def _split(repository: str) -> tuple[str, str]:
    owner, _slash, name = repository.partition("/")
    if not owner or not name:
        raise IssueDevelopmentError(f"{repository!r} is not owner/name.")
    return owner, name


def _issue_node(api: GitHubApi, repository: str, number: int) -> tuple[str, str, Mapping[str, Any]]:
    owner, name = _split(repository)
    data = api.graphql(_NODE_QUERY, {"o": owner, "n": name, "i": int(number)})
    repo = data.get("repository") or {}
    issue = repo.get("issue") if isinstance(repo, Mapping) else None
    if not isinstance(issue, Mapping) or not issue.get("id"):
        raise IssueDevelopmentError(f"{repository} has no issue #{number}.")
    return str(repo.get("id") or ""), str(issue["id"]), issue


def close_issue(
    api: GitHubApi,
    repository: str,
    number: int,
    reason: CloseReason,
    *,
    duplicate_of: int = 0,
) -> str:
    """Close #*number* for *reason*; the sentence to say. A duplicate names its original."""
    if reason.rest == "duplicate":
        if not duplicate_of:
            raise IssueDevelopmentError("Name the issue it duplicates, by number.")
        if int(duplicate_of) == int(number):
            raise IssueDevelopmentError(f"#{number} cannot be a duplicate of itself.")
        _repo, issue_id, _issue = _issue_node(api, repository, number)
        _repo, original_id, original = _issue_node(api, repository, duplicate_of)
        api.graphql(_CLOSE_DUPLICATE, {"id": issue_id, "dup": original_id})
        title = str(original.get("title") or "")
        return f"Closed #{number} as a duplicate of #{duplicate_of}" + (
            f", {title}." if title else "."
        )
    api.rest(
        "PATCH",
        f"/repos/{repository}/issues/{int(number)}",
        body={"state": "closed", "state_reason": reason.rest},
    )
    return f"Closed #{number} as {reason.said}."


def linked_branches(api: GitHubApi, repository: str, number: int) -> list[str]:
    """The branches linked to #*number* (its Development on GitHub), by name."""
    owner, name = _split(repository)
    data = api.graphql(_LINKED_QUERY, {"o": owner, "n": name, "i": int(number)})
    issue = (data.get("repository") or {}).get("issue") or {}
    nodes = (issue.get("linkedBranches") or {}).get("nodes") or []
    return [str(node["ref"]["name"]) for node in nodes if (node or {}).get("ref")]


_UNSAFE = re.compile(r"[^a-z0-9]+")


def branch_name_for(number: int, title: str, *, limit: int = 60) -> str:
    """GitHub's own suggestion for an issue's branch: ``42-fix-the-parser``."""
    slug = _UNSAFE.sub("-", title.lower()).strip("-")
    name = f"{int(number)}-{slug}" if slug else str(int(number))
    return name[:limit].rstrip("-")


_BAD_REF = re.compile(r"(^[-/.])|([/.]$)|(\.\.)|(//)|(@\{)|([\s~^:?*\[\\\x00-\x1f\x7f])|(\.lock$)")


def valid_branch_name(name: str) -> str:
    """Why *name* cannot be a branch, or "" when it can (git check-ref-format's rules)."""
    if not name:
        return "A branch needs a name."
    if name == "@" or _BAD_REF.search(name):
        return (
            f"{name!r} cannot be a branch name: no spaces, no ~ ^ : ? * [ or backslash, "
            "no two dots in a row, and it cannot start with - or end with / or ."
        )
    return ""


def create_linked_branch(
    api: GitHubApi, repository: str, number: int, name: str, *, base: str = ""
) -> str:
    """Make branch *name* from *base* (the default branch when empty), linked to #*number*.

    Returns the sentence to say. Refuses a name git would refuse, and a branch
    that already exists, before sending anything.
    """
    why = valid_branch_name(name)
    if why:
        raise IssueDevelopmentError(why)
    if not base:
        base = str(api.rest("GET", f"/repos/{repository}").data.get("default_branch") or "")
    try:
        head = api.rest("GET", f"/repos/{repository}/git/ref/heads/{base}").data
    except Exception as exc:  # noqa: BLE001 - said as one sentence below
        raise IssueDevelopmentError(f"{repository} has no branch {base}.") from exc
    oid = str((head.get("object") or {}).get("sha") or "") if isinstance(head, Mapping) else ""
    if not oid:
        raise IssueDevelopmentError(f"{repository} has no branch {base}.")
    try:
        api.rest("GET", f"/repos/{repository}/branches/{name}")
    except Exception:  # noqa: BLE001 - not found is the answer wanted
        pass
    else:
        raise IssueDevelopmentError(f"{repository} already has a branch called {name}.")
    repo_id, issue_id, _issue = _issue_node(api, repository, number)
    api.graphql(_CREATE_LINKED, {"issue": issue_id, "oid": oid, "name": name, "repo": repo_id})
    return f"Made branch {name} from {base}, linked to #{number}."


# -- task lists ----------------------------------------------------------------

_TASK = re.compile(r"^(?P<lead>\s*[-*+]\s+\[)(?P<mark>[ xX])(?P<close>\]\s+)(?P<text>.*?)\s*$")
_REF_ONLY = re.compile(r"^(?:[\w.-]+/[\w.-]+)?#\d+$")


@dataclass(frozen=True)
class TaskItem:
    line: int
    """Its 0-based line in the body."""
    checked: bool
    text: str

    @property
    def is_issue(self) -> bool:
        """Whether the item is already an issue reference (``#12``, ``owner/name#12``)."""
        return bool(_REF_ONLY.match(self.text))

    @property
    def sentence(self) -> str:
        return f"{'Done' if self.checked else 'Not done'}: {self.text}"


def task_items(body: str) -> list[TaskItem]:
    """Every ``- [ ]`` and ``- [x]`` line of *body*, outside fenced code."""
    found: list[TaskItem] = []
    fenced = False
    for index, line in enumerate(body.replace("\r\n", "\n").split("\n")):
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
            continue
        match = None if fenced else _TASK.match(line)
        if match and match["text"]:
            found.append(TaskItem(index, match["mark"] != " ", match["text"]))
    return found


def _rewrite(body: str, line: int, change: Any) -> str:
    newline = "\r\n" if "\r\n" in body else "\n"
    lines = body.replace("\r\n", "\n").split("\n")
    match = _TASK.match(lines[line]) if 0 <= line < len(lines) else None
    if match is None:
        raise IssueDevelopmentError("That task is no longer in the issue; read it again.")
    lines[line] = change(match)
    return newline.join(lines)


def toggle_task(body: str, item: TaskItem) -> str:
    """*body* with *item* checked if it was not, and unchecked if it was."""
    mark = " " if item.checked else "x"
    return _rewrite(body, item.line, lambda m: f"{m['lead']}{mark}{m['close']}{m['text']}")


def convertible(body: str) -> list[TaskItem]:
    """The task items that are not issues yet, in order."""
    return [item for item in task_items(body) if not item.is_issue]


def linked_body(body: str, made: Mapping[int, int]) -> str:
    """*body* with each converted item's text replaced by ``#number``, its mark kept.

    *made* maps an item's line to the issue made from it. GitHub shows a task
    item that is only a reference as that issue, with its state.
    """
    for line, number in sorted(made.items()):
        body = _rewrite(body, line, lambda m, n=number: f"{m['lead']}{m['mark']}{m['close']}#{n}")
    return body
