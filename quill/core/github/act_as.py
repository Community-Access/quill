"""Act As: one action, sent as another signed-in account (GitHub PRD 18.3).

The usual reason is a second pair of hands: approving your own pull request
needs another account, and so does checking what a contributor sees when they
comment. Act As does exactly one thing as the other account and then forgets
it; the Workbench stays signed in as itself.

Identity is never ambiguous:

* the account is one saved in Manage GitHub Accounts, named with its host
  ("kelly-test on github.com") in the confirmation and in the outcome;
* before anything is sent, its token is asked who it is (``GET /user``); if
  GitHub names anybody else, nothing is sent (:func:`identity_problem`);
* it is held to *that* account's Workbench level, not the active one's
  (:func:`quill.core.github.write_gate.refusal`), and Safe Mode holds it too;
* the request goes through a :class:`~quill.core.github.workbench_api.TokenApi`
  of its own, whose remembered reads are that account's alone, and the
  Workbench's own connection is not touched.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from quill.core.github.permissions import WriteTier

__all__ = [
    "ACT_AS_ACTIONS",
    "ActAsAction",
    "ActAsRequest",
    "actions_for",
    "confirmation",
    "identity_problem",
    "outcome",
    "plan",
]


@dataclass(frozen=True)
class ActAsAction:
    """One action Act As offers: what it is called, where, and its tier."""

    key: str
    title: str
    kinds: frozenset[str]
    tier: WriteTier
    needs_text: bool = False


ACT_AS_ACTIONS: tuple[ActAsAction, ...] = (
    ActAsAction(
        "approve", "Approve this pull request", frozenset({"pull_request"}), WriteTier.VISIBLE
    ),
    ActAsAction(
        "comment",
        "Comment on it",
        frozenset({"issue", "pull_request"}),
        WriteTier.VISIBLE,
        needs_text=True,
    ),
    ActAsAction(
        "close_reopen",
        "Close or reopen it",
        frozenset({"issue", "pull_request"}),
        WriteTier.VISIBLE,
    ),
    ActAsAction("star", "Star the repository", frozenset({"repository"}), WriteTier.ORGANIZING),
)


def actions_for(kind: str) -> list[ActAsAction]:
    """The actions for a selected row of *kind* (``issue``, ``pull_request``), then the repo's."""
    return [a for a in ACT_AS_ACTIONS if kind in a.kinds or "repository" in a.kinds]


@dataclass(frozen=True)
class ActAsRequest:
    """The one request, and what it is said as."""

    method: str
    path: str
    body: Mapping[str, object] | None
    words: str
    done: str
    tier: WriteTier


def plan(
    action: ActAsAction,
    repo: str,
    *,
    number: int = 0,
    is_open: bool = True,
    text: str = "",
) -> ActAsRequest:
    """The request *action* sends on *repo* (and item *number*), with its words."""
    noun = f"pull request #{number}" if action.key == "approve" else f"#{number}"
    if action.key == "approve":
        return ActAsRequest(
            "POST",
            f"/repos/{repo}/pulls/{number}/reviews",
            {"event": "APPROVE"},
            f"approve pull request #{number} in {repo}",
            f"approved pull request #{number} in {repo}",
            action.tier,
        )
    if action.key == "comment":
        return ActAsRequest(
            "POST",
            f"/repos/{repo}/issues/{number}/comments",
            {"body": text},
            f"comment on {noun} in {repo}: {text[:80]}",
            f"commented on {noun} in {repo}",
            action.tier,
        )
    if action.key == "close_reopen":
        verb = "close" if is_open else "reopen"
        return ActAsRequest(
            "PATCH",
            f"/repos/{repo}/issues/{number}",
            {"state": "closed" if is_open else "open"},
            f"{verb} {noun} in {repo}",
            f"{verb}d {noun} in {repo}" if verb == "close" else f"reopened {noun} in {repo}",
            action.tier,
        )
    return ActAsRequest(
        "PUT", f"/user/starred/{repo}", None, f"star {repo}", f"starred {repo}", action.tier
    )


def identity_problem(saved_login: str, host: str, answered: object) -> str:
    """ "" when the token's ``GET /user`` names *saved_login*; else why nothing is sent."""
    who = str(answered.get("login", "")) if isinstance(answered, Mapping) else ""
    if not who:
        return (
            f"Cannot act as {saved_login} on {host}: GitHub did not say whose its saved token "
            "is, so nothing was sent."
        )
    if who.casefold() != saved_login.casefold():
        return (
            f"Cannot act as {saved_login} on {host}: its saved token now belongs to {who}, so "
            f"nothing was sent. Sign in again as {saved_login} from Manage GitHub Accounts."
        )
    return ""


def confirmation(login: str, host: str, request: ActAsRequest) -> str:
    """The question asked before sending, naming the account and its host."""
    return (
        f"As {login} on {host}, not as you: {request.words}.\n\n"
        f"GitHub will show {login} as the one who did it."
    )


def outcome(login: str, request: ActAsRequest, failure: str = "") -> str:
    """The one sentence said afterwards, naming the account.

    It starts with the outcome ("Could not", "Approved") so the Workbench's
    outcome feedback hears a failure as a failure.
    """
    if failure:
        return f"Could not {request.words} as {login}: {failure}"
    said = f"{request.done} as {login}."
    return said[:1].upper() + said[1:]
