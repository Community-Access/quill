"""Copilot code review and the Copilot coding agent, for ``GitHubItemsProvider``.

Two writes, each checked against what GitHub's documentation says works:

- **Request Copilot Review** asks the pull request's ``requested_reviewers``
  endpoint for ``copilot-pull-request-reviewer[bot]``, the login GitHub's
  Copilot code review page names for the REST API. GitHub can answer 201 and
  still leave Copilot off the list when the account or repository has no
  Copilot code review, so the reply's reviewer list is read back and a
  missing Copilot is said plainly rather than reported as success.
- **Assign to Copilot** follows "Using Copilot cloud agent via the API"
  (docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/
  use-cloud-agent-via-the-api): one query reads the repository's
  ``suggestedActors(capabilities: [CAN_BE_ASSIGNED])`` and the issue, and when
  ``copilot-swe-agent`` is among them, ``replaceActorsForAssignable`` assigns
  it. The issue's existing assignees are passed too, because "replace" would
  otherwise drop them. Both calls send the ``GraphQL-Features`` opt-in the
  documentation asks for, and the mutation's own assignee list is the only
  proof of success.

No ``wx`` imports; strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from quill.core.github.github_graphql import as_dict, graphql_data, split_repo
from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.rest_transport import GitHubRestError, request_json, rest_failure_message
from quill.core.github.run_actions import repo_path

#: The reviewer login GitHub documents for requesting Copilot code review over REST.
COPILOT_REVIEWER_LOGIN = "copilot-pull-request-reviewer[bot]"
#: The coding agent's login in ``suggestedActors`` (REST spells it with ``[bot]``).
COPILOT_AGENT_LOGIN = "copilot-swe-agent"
#: The opt-in header GitHub's coding-agent API page asks every call to send.
COPILOT_GRAPHQL_FEATURES = {
    "GraphQL-Features": "issues_copilot_assignment_api_support,coding_agent_model_selection"
}

_ASSIGNMENT_QUERY = """
query($owner:String!, $name:String!, $number:Int!) {
  repository(owner:$owner, name:$name) {
    id
    suggestedActors(capabilities: [CAN_BE_ASSIGNED], first: 100) {
      nodes { login __typename ... on Bot { id } ... on User { id } }
    }
    issue(number:$number) {
      id state
      assignees(first: 100) { nodes { id login } }
    }
  }
}
"""

_ASSIGN_MUTATION = """
mutation($assignable:ID!, $actors:[ID!]!) {
  replaceActorsForAssignable(input: {assignableId: $assignable, actorIds: $actors}) {
    assignable { ... on Issue { number assignees(first: 100) { nodes { id login } } } }
  }
}
"""

_NOT_AVAILABLE = (
    "Copilot's coding agent is not available for {repo}. It needs a Copilot plan "
    "that includes the coding agent, and the agent turned on for this repository "
    "(an organization owner may have to allow it). Nothing was changed."
)


@dataclass(frozen=True, slots=True)
class CopilotAssignment:
    """What GitHub says about handing one issue to the Copilot coding agent."""

    full_name: str
    number: int
    available: bool
    bot_id: str = ""
    issue_id: str = ""
    issue_state: str = ""
    assignee_ids: tuple[str, ...] = ()
    assignee_logins: tuple[str, ...] = ()

    @property
    def already_assigned(self) -> bool:
        return any(_is_agent(login) for login in self.assignee_logins)

    def refusal(self) -> str:
        """Why the issue cannot go to Copilot, or "" when it can."""
        if not self.available:
            return _NOT_AVAILABLE.format(repo=self.full_name)
        if not self.issue_id:
            return f"GitHub has no issue #{self.number} in {self.full_name}."
        if self.issue_state.upper() == "CLOSED":
            return f"Issue #{self.number} is closed. Reopen it before assigning it to Copilot."
        if self.already_assigned:
            return f"Issue #{self.number} is already assigned to Copilot."
        return ""

    def confirmation(self) -> str:
        """The question asked before the assignment, naming who stays assigned."""
        others = [login for login in self.assignee_logins if not _is_agent(login)]
        kept = f" {', '.join(others)} stay assigned too." if others else ""
        return (
            f"Assign issue #{self.number} in {self.full_name} to Copilot? Copilot's coding "
            "agent starts working on it and opens a pull request for you to review."
            f"{kept}"
        )


def _is_agent(login: str) -> bool:
    # suggestedActors says copilot-swe-agent; an issue's assignees may show it as Copilot.
    return login.casefold().removesuffix("[bot]") in {COPILOT_AGENT_LOGIN, "copilot"}


def _is_copilot_reviewer(login: str) -> bool:
    folded = login.casefold().removesuffix("[bot]")
    return folded in {"copilot", "copilot-pull-request-reviewer"}


def parse_assignment(full_name: str, number: int, data: Mapping[str, Any]) -> CopilotAssignment:
    """The assignment query's ``data`` as a :class:`CopilotAssignment`."""
    repository = as_dict(data.get("repository"))
    nodes = as_dict(repository.get("suggestedActors")).get("nodes")
    bot_id = ""
    for node in nodes if isinstance(nodes, list) else ():
        row = as_dict(node)
        if _is_agent(str(row.get("login") or "")) and row.get("id"):
            bot_id = str(row["id"])
            break
    issue = as_dict(repository.get("issue"))
    assignees = as_dict(issue.get("assignees")).get("nodes")
    rows = [as_dict(node) for node in (assignees if isinstance(assignees, list) else ())]
    return CopilotAssignment(
        full_name=full_name,
        number=number,
        available=bool(bot_id),
        bot_id=bot_id,
        issue_id=str(issue.get("id") or ""),
        issue_state=str(issue.get("state") or ""),
        assignee_ids=tuple(str(row["id"]) for row in rows if row.get("id")),
        assignee_logins=tuple(str(row.get("login") or "") for row in rows if row.get("login")),
    )


class _CopilotAccess(Protocol):
    _token: str | None

    def _require_write_access(self, action: str) -> None: ...


def _number(number: int, what: str) -> int:
    if isinstance(number, bool) or not isinstance(number, int) or number <= 0:
        raise GitHubItemsError(f"Choose {what} first.")
    return number


class GitHubCopilotMixin:
    """Request Copilot Review on a pull request; Assign to Copilot on an issue."""

    def request_copilot_review(self: _CopilotAccess, full_name: str, number: int) -> str:
        """Ask Copilot to review pull request *number*; the sentence GitHub confirmed."""
        self._require_write_access("request a Copilot review")
        path = f"{repo_path(full_name)}/pulls/{_number(number, 'a pull request')}"
        try:
            response = request_json(
                self._token,
                "POST",
                f"{path}/requested_reviewers",
                body={"reviewers": [COPILOT_REVIEWER_LOGIN]},
            )
        except GitHubRestError as exc:
            if exc.status == 422:
                detail = str(exc.data.get("message", "")) if isinstance(exc.data, dict) else ""
                raise GitHubItemsError(
                    "GitHub would not add Copilot as a reviewer. Copilot code review may "
                    "not be available to your account or this repository"
                    + (f" (GitHub said: {detail})." if detail else ".")
                ) from exc
            raise GitHubItemsError(rest_failure_message("request a Copilot review", exc)) from exc
        if response.status not in (200, 201):
            raise GitHubItemsError(
                "Could not request a Copilot review. GitHub answered HTTP "
                f"{response.status} without confirming it."
            )
        data = response.data if isinstance(response.data, Mapping) else {}
        reviewers = data.get("requested_reviewers")
        logins = [
            str(as_dict(row).get("login") or "")
            for row in (reviewers if isinstance(reviewers, list) else ())
        ]
        if not any(_is_copilot_reviewer(login) for login in logins):
            raise GitHubItemsError(
                "GitHub accepted the request but did not list Copilot as a reviewer, so "
                "Copilot code review is probably not available to your account or this "
                "repository. Check Copilot's code review setting on GitHub."
            )
        return (
            f"Copilot review requested on pull request #{number}. Its review arrives as comments."
        )

    def check_copilot_assignment(
        self: _CopilotAccess, full_name: str, number: int
    ) -> CopilotAssignment:
        """Whether issue *number* can go to the Copilot coding agent, read in one query."""
        owner, name = split_repo(full_name)
        data = graphql_data(
            self._token,
            _ASSIGNMENT_QUERY,
            {"owner": owner, "name": name, "number": _number(number, "an issue")},
            action="check whether Copilot can be assigned",
            extra_headers=COPILOT_GRAPHQL_FEATURES,
        )
        return parse_assignment(full_name, number, data)

    def assign_issue_to_copilot(self: _CopilotAccess, assignment: CopilotAssignment) -> str:
        """Hand the checked issue to Copilot; the sentence GitHub's reply confirmed."""
        self._require_write_access("assign an issue to Copilot")
        if refusal := assignment.refusal():
            raise GitHubItemsError(refusal)
        actors = list(dict.fromkeys((*assignment.assignee_ids, assignment.bot_id)))
        data = graphql_data(
            self._token,
            _ASSIGN_MUTATION,
            {"assignable": assignment.issue_id, "actors": actors},
            action="assign the issue to Copilot",
            extra_headers=COPILOT_GRAPHQL_FEATURES,
        )
        assignable = as_dict(as_dict(data.get("replaceActorsForAssignable")).get("assignable"))
        nodes = as_dict(assignable.get("assignees")).get("nodes")
        rows = [as_dict(node) for node in (nodes if isinstance(nodes, list) else ())]
        if not any(
            row.get("id") == assignment.bot_id or _is_agent(str(row.get("login") or ""))
            for row in rows
        ):
            raise GitHubItemsError(
                "GitHub did not confirm Copilot as an assignee. Refresh the issue to see "
                "whether the assignment took."
            )
        return (
            f"Issue #{assignment.number} assigned to Copilot. Its pull request appears "
            "in the repository when the agent has started."
        )


__all__ = [
    "COPILOT_AGENT_LOGIN",
    "COPILOT_GRAPHQL_FEATURES",
    "COPILOT_REVIEWER_LOGIN",
    "CopilotAssignment",
    "GitHubCopilotMixin",
    "parse_assignment",
]
