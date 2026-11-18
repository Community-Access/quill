"""An issue's field values, deleting an issue, related issues and pinned comments."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github.comment_moderation import pin_comment
from quill.core.github.issue_admin import (
    IssueAdminError,
    clear_field_value,
    delete_issue,
    read_issue_fields,
    set_field_value,
)
from quill.core.github.issue_relations import GitHubIssueRelations, IssueRef
from quill.core.github.rest_transport import GitHubRestError, RestResponse
from quill.core.github.timeline import timeline_entry


class _Api:
    def __init__(self, replies: dict[str, Any] | None = None, graph: Any = None) -> None:
        self.replies, self.graph = replies or {}, graph
        self.sent: list[tuple[str, str, Any]] = []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> RestResponse:
        self.sent.append((method, path, body))
        reply = self.replies.get(f"{method} {path}", {} if method != "GET" else [])
        if isinstance(reply, Exception):
            raise reply
        return RestResponse(200, {}, reply)

    def graphql(self, query: str, variables: Any) -> Any:
        self.sent.append(("GRAPHQL", query.split("(", 1)[0].strip(), variables))
        return self.graph


DEFS = [
    {
        "id": 1,
        "name": "Priority",
        "data_type": "single_select",
        "options": [{"name": "High"}, {"name": "Low"}],
    },
    {"id": 2, "name": "Due", "data_type": "date"},
    {"id": 3, "name": "Points", "data_type": "number"},
]


def test_fields_read_with_their_states_and_choices() -> None:
    api = _Api({
        "GET /orgs/acme/issue-fields": DEFS,
        "GET /repos/acme/site/issues/4/issue-field-values": [
            {
                "issue_field_id": 1,
                "data_type": "single_select",
                "single_select_option": {"name": "High"},
            },
        ],
    })
    found = read_issue_fields(api, "acme/site", 4)
    assert [v.state for v in found.values] == ["value", "unset", "unset"]
    assert found.choices == {"1": ("High", "Low")}


def test_a_personal_repository_falls_back_to_your_own_fields() -> None:
    api = _Api({
        "GET /orgs/jeff/issue-fields": GitHubRestError("no", status=404),
        "GET /user/issue-fields": DEFS[:1],
    })
    assert read_issue_fields(api, "jeff/notes", 1).values[0].name == "Priority"


def test_setting_one_field_sends_only_that_field_typed() -> None:
    api = _Api({
        "GET /orgs/acme/issue-fields": DEFS,
        "GET /repos/acme/site/issues/4/issue-field-values": [],
    })
    found = read_issue_fields(api, "acme/site", 4)
    priority, due, points = found.values
    assert set_field_value(api, "acme/site", 4, points, "5") == "Points is now 5 on #4."
    assert api.sent[-1] == (
        "POST",
        "/repos/acme/site/issues/4/issue-field-values",
        {"issue_field_values": [{"field_id": 3, "value": 5}]},
    )
    with pytest.raises(IssueAdminError, match="year-month-day"):
        set_field_value(api, "acme/site", 4, due, "next friday")
    with pytest.raises(IssueAdminError, match="High, Low"):
        set_field_value(api, "acme/site", 4, priority, "Urgent", ("High", "Low"))
    clear_field_value(api, "acme/site", 4, due)
    assert api.sent[-1][:2] == ("DELETE", "/repos/acme/site/issues/4/issue-field-values/2")


def test_deleting_an_issue_uses_its_node_id_and_refuses_a_pull_request() -> None:
    api = _Api(
        {"GET /repos/acme/site/issues/4": {"node_id": "I_4"}},
        {"deleteIssue": {"repository": {"nameWithOwner": "acme/site"}}},
    )
    assert delete_issue(api, "acme/site", 4) == "#4 is deleted from acme/site."
    assert api.sent[-1][2] == {"id": "I_4"}
    api = _Api({"GET /repos/acme/site/issues/5": {"node_id": "PR_5", "pull_request": {}}})
    with pytest.raises(IssueAdminError, match="pull request"):
        delete_issue(api, "acme/site", 5)
    api = _Api({"GET /repos/acme/site/issues/6": {"node_id": "I_6"}}, {"deleteIssue": None})
    with pytest.raises(IssueAdminError, match="did not confirm"):
        delete_issue(api, "acme/site", 6)


def test_related_issues_are_read_added_and_removed() -> None:
    sent: list[tuple[str, str, Any]] = []
    other = {
        "id": 77,
        "number": 9,
        "title": "Docs",
        "repository_url": "https://api.github.com/repos/acme/site",
    }

    def request(_token: Any, method: str, path: str, **kw: Any) -> RestResponse:
        sent.append((method, path, kw.get("body")))
        if path.endswith("/parent"):
            raise GitHubRestError("none", status=404)
        if path.endswith("/relates_to") and method == "GET":
            return RestResponse(200, data=[other])
        return RestResponse(204 if method == "DELETE" else 200, data=[])

    api = GitHubIssueRelations("t", request)
    found = api.relations("acme/site", 4)
    assert found.lines("acme/site") == ["Related: #9 Docs (open)"]
    assert found.summary() == "1 related issue"
    ref = IssueRef(77, 9, "Docs", "acme/site")
    api.add_related("acme/site", 4, ref)
    assert sent[-1] == ("POST", "/repos/acme/site/issues/4/relates_to", {"issue_id": 77})
    api.remove_related("acme/site", 4, ref)
    assert sent[-1][:2] == ("DELETE", "/repos/acme/site/issues/4/relates_to/77")


def test_a_comment_keeps_its_rest_id_so_it_can_be_pinned() -> None:
    entry = timeline_entry({
        "event": "commented",
        "id": 555,
        "node_id": "IC_1",
        "actor": {"login": "jeff"},
        "body": "Hi",
    })
    assert entry is not None and entry.comment_id == "555"
    api = _Api()
    assert pin_comment(api, "acme/site", "555").startswith("Pinned")
    assert api.sent[-1][:2] == ("PUT", "/repos/acme/site/issues/comments/555/pin")
    pin_comment(api, "acme/site", "555", pin=False)
    assert api.sent[-1][0] == "DELETE"
    with pytest.raises(ValueError):
        pin_comment(api, "acme/site", "")
