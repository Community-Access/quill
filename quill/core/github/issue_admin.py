"""An issue's own field values, and deleting an issue (GitHub PRD sections 14 and 22.11).

* **Issue Fields...** reads the fields the repository's owner defines (an
  organization's, or your own for your repositories) and this issue's value
  for each, through the same parsers Across Repositories uses
  (:mod:`quill.core.github.across_issue_fields`), so the five states stay
  distinct. Setting one sends only that field
  (``POST .../issue-field-values``), so another person's value for a different
  field is never overwritten; clearing one deletes only its value. The
  Properties sheet's Issue Fields page sends the very same request
  (:func:`field_request`), so the two cannot drift apart.
* **Delete Issue...** deletes an issue for good through GraphQL's
  ``deleteIssue``, which only a repository's admins may do.

wx-free and strict-typed.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from quill.core.error_codes import CodedError
from quill.core.github.across_issue_fields import (
    FieldValue,
    combine,
    parse_definitions,
    parse_values,
    read_definitions,
)
from quill.core.github.rest_transport import GitHubRestError
from quill.core.github.workbench_api import GitHubApi

__all__ = [
    "IssueAdminError",
    "IssueFields",
    "clear_field_value",
    "delete_issue",
    "field_request",
    "read_issue_fields",
    "set_field_value",
]

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class IssueAdminError(CodedError):
    """A field value or deletion that could not be done; the message says why."""

    code = "QUILL-GITHUB-ISSUEADMIN-FAILED"


@dataclass(frozen=True, slots=True)
class IssueFields:
    """One issue's fields, and the choices each single select offers."""

    values: tuple[FieldValue, ...]
    choices: dict[str, tuple[str, ...]]


def _issue(repo: str, number: int) -> str:
    return f"/repos/{quote(repo, safe='/')}/issues/{int(number)}"


def _why(exc: GitHubRestError, doing: str) -> IssueAdminError:
    if exc.status in (401, 403):
        return IssueAdminError(f"GitHub refused to {doing}; it needs triage access or more.")
    if exc.status == 404:
        return IssueAdminError(f"GitHub found no issue fields to {doing} here.")
    return IssueAdminError(f"Could not {doing}: {exc}")


def _definitions(api: GitHubApi, repo: str) -> Any:
    try:
        return read_definitions(api, repo.split("/", 1)[0])
    except GitHubRestError as exc:
        raise _why(exc, "read the issue fields") from exc


def _choices(data: Any) -> dict[str, tuple[str, ...]]:
    rows = data.get("issue_fields") if isinstance(data, Mapping) else data
    found: dict[str, tuple[str, ...]] = {}
    for entry in rows if isinstance(rows, list) else []:
        if not isinstance(entry, Mapping) or entry.get("id") is None:
            continue
        options = [str(o.get("name")) for o in entry.get("options") or () if isinstance(o, Mapping)]
        if options:
            found[str(entry["id"])] = tuple(options)
    return found


def read_issue_fields(api: GitHubApi, repo: str, number: int) -> IssueFields:
    """Every field the owner defines, with this issue's value or why there is none."""
    definitions = _definitions(api, repo)
    try:
        values = api.rest("GET", f"{_issue(repo, number)}/issue-field-values").data
    except GitHubRestError as exc:
        raise _why(exc, "read this issue's fields") from exc
    combined = combine(parse_definitions(definitions), parse_values(values))
    return IssueFields(combined, _choices(definitions))


def _typed(field: FieldValue, answer: str, choices: tuple[str, ...]) -> object:
    text = answer.strip()
    if not text:
        raise IssueAdminError(f"Type a value for {field.name}, or choose Clear.")
    if field.data_type == "number":
        try:
            return float(text) if "." in text else int(text)
        except ValueError:
            raise IssueAdminError(f"{field.name} takes a number, such as 3.") from None
    if field.data_type == "date":
        if not _DATE.match(text):
            raise IssueAdminError(
                f"{field.name} takes a date as year-month-day, such as 2026-12-31."
            )
        return text
    if field.data_type == "single_select" and choices and text not in choices:
        raise IssueAdminError(f"{field.name} is one of: {', '.join(choices)}.")
    return text


def field_request(
    repo: str, number: int, field: FieldValue, answer: str, choices: tuple[str, ...] = ()
) -> tuple[str, str, dict[str, object] | None]:
    """The one request that sets *field* on an issue to *answer*, or clears it when empty.

    Setting POSTs only this field, so nobody's value for another field is
    touched; clearing DELETEs only this field's value. Issue Fields... and the
    sheet's Issue Fields page both send this.
    """
    base = f"{_issue(repo, number)}/issue-field-values"
    if not answer.strip():
        return "DELETE", f"{base}/{int(field.field_id)}", None
    value = _typed(field, answer, choices)
    return "POST", base, {"issue_field_values": [{"field_id": int(field.field_id), "value": value}]}


def set_field_value(
    api: GitHubApi,
    repo: str,
    number: int,
    field: FieldValue,
    answer: str,
    choices: tuple[str, ...] = (),
) -> str:
    """Set one field on one issue, leaving every other field as it is."""
    value = _typed(field, answer, choices)
    method, path, body = field_request(repo, number, field, answer, choices)
    try:
        api.rest(method, path, body=body)
    except GitHubRestError as exc:
        raise _why(exc, f"set {field.name}") from exc
    return f"{field.name} is now {value} on #{number}."


def clear_field_value(api: GitHubApi, repo: str, number: int, field: FieldValue) -> str:
    method, path, _body = field_request(repo, number, field, "")
    try:
        api.rest(method, path)
    except GitHubRestError as exc:
        raise _why(exc, f"clear {field.name}") from exc
    return f"{field.name} is cleared on #{number}."


_DELETE = """
mutation($id: ID!) {
  deleteIssue(input: {issueId: $id}) { repository { nameWithOwner } }
}
"""


def delete_issue(api: GitHubApi, repo: str, number: int) -> str:
    """Delete an issue for good. Needs admin rights; GitHub cannot bring it back."""
    try:
        data = api.rest("GET", _issue(repo, number)).data
    except GitHubRestError as exc:
        raise _why(exc, f"find #{number}") from exc
    node_id = str(data.get("node_id") or "") if isinstance(data, Mapping) else ""
    if not node_id:
        raise IssueAdminError(f"GitHub sent no id for #{number}, so nothing was deleted.")
    if isinstance(data, Mapping) and data.get("pull_request") is not None:
        raise IssueAdminError(f"#{number} is a pull request; GitHub deletes only issues.")
    reply = api.graphql(_DELETE, {"id": node_id})
    done = reply.get("deleteIssue") if isinstance(reply, Mapping) else None
    if not isinstance(done, Mapping) or not done.get("repository"):
        raise IssueAdminError(f"GitHub did not confirm deleting #{number}.")
    return f"#{number} is deleted from {repo}."
