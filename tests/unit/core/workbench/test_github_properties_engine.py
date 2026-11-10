"""GitHub Phase 7: the Properties engine over recorded answers (GitHub PRD 15, GH-R-030 to 036)."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github.permissions import AccessLevel, ViewerContext
from quill.core.github.sheet_catalog import SHEETS, Target, context_for, target_for
from quill.core.github.sheet_engine import (
    inverse,
    load,
    load_options,
    locked_fields,
    plan,
    save,
    sentence,
)
from quill.core.github.sheets_items import ISSUE
from quill.core.github.sheets_labels import LABEL, MILESTONE
from quill.core.github.sheets_pulls import PULL_REQUEST
from quill.core.github.sheets_repo import REPOSITORY
from quill.core.workbench.properties import FieldChange, ListDelta
from tests.github_api_fake import FakeGitHubApi

REPO = "owner/repo"
IDENT = {"repo": REPO, "number": "42"}


def _issue_json(**changes: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "number": 42,
        "title": "Crash on start",
        "body": "It crashes.",
        "state": "open",
        "user": {"login": "kellylford"},
        "created_at": "2026-11-09T14:05:00Z",
        "updated_at": "2026-11-09T14:05:00Z",
        "labels": [{"name": "docs"}],
        "assignees": [],
        "milestone": None,
        "comments": 3,
        "html_url": "https://github.com/owner/repo/issues/42",
        "locked": False,
    }
    data.update(changes)
    return data


def _viewer(**flags: bool) -> dict[str, Any]:
    item = {
        "__typename": "Issue",
        "id": "I_42",
        "isPinned": False,
        "viewerCanUpdate": True,
        "viewerCanLabel": True,
        "viewerCanAssign": True,
        "viewerSubscription": "UNSUBSCRIBED",
        "reactionGroups": [{"content": "HEART", "viewerHasReacted": True}],
        "projectItems": {"nodes": [{"project": {"title": "Roadmap"}}]},
        "subIssues": {"nodes": [{"number": 43, "title": "Part one"}]},
    }
    item.update(flags)
    return {"repository": {"viewerPermission": "TRIAGE", "issueOrPullRequest": item}}


@pytest.fixture
def api() -> FakeGitHubApi:
    fake = FakeGitHubApi()
    state = {"issue": _issue_json()}

    def on_write(method: str, path: str, body: Any) -> None:
        if method == "PATCH" and path == "/repos/owner/repo/issues/42" and body:
            issue = dict(state["issue"])
            if "labels" in body:
                issue["labels"] = [{"name": n} for n in body["labels"]]
            if "title" in body:
                issue["title"] = body["title"]
            if "milestone" in body:
                issue["milestone"] = {"title": "2027.1", "number": body["milestone"]}
            state["issue"] = issue

    fake.on_write = on_write
    fake.answer("GET", "/repos/owner/repo/issues/42", lambda: state["issue"])
    fake.answer_graphql("issueOrPullRequest", _viewer())
    fake.answer("GET", "/repos/owner/repo/labels", [{"name": "bug"}, {"name": "docs"}])
    fake.answer("GET", "/repos/owner/repo/milestones", [{"title": "2027.1", "number": 7}])
    fake.answer("GET", "/repos/owner/repo/assignees", [{"login": "kellylford"}])
    fake.state = state  # type: ignore[attr-defined]
    return fake


def test_every_phase_7_sheet_opens_on_general_and_has_writes_for_its_editable_fields() -> None:
    for sheet in (ISSUE, PULL_REQUEST, REPOSITORY, LABEL, MILESTONE):
        assert sheet.sheet.pages[0].key == "general"
        for key in sheet.editable_keys():
            assert key in sheet.writes, f"{sheet.kind}.{key} has no write"
        assert sheet.kind in SHEETS


def test_a_load_reads_the_object_and_its_viewer_fields(api: FakeGitHubApi) -> None:
    loaded = load(api, ISSUE, IDENT)
    assert loaded.values["title"] == "Crash on start"
    assert loaded.values["labels"] == ("docs",)
    assert loaded.values["your_access"] == "triage"
    assert loaded.values["reactions"] == ("heart",)
    assert loaded.values["projects"] == ("Roadmap",)
    assert loaded.values["sub_issues"] == ("#43 Part one",)
    assert loaded.viewer["viewerCanLabel"] is True
    assert "9 November 2026" in str(loaded.values["created"])


def test_an_optional_viewer_read_that_fails_leaves_the_rest(api: FakeGitHubApi) -> None:
    api.graphql_answers.clear()
    loaded = load(api, ISSUE, IDENT)
    assert loaded.values["title"] == "Crash on start"
    assert loaded.missing == ("graphql",)


def test_fields_lock_with_a_reason_when_your_role_is_too_low(api: FakeGitHubApi) -> None:
    loaded = load(api, ISSUE, IDENT)
    ctx = context_for(loaded.values, loaded.viewer, signed_in=True, where=REPO)
    locked = locked_fields(ISSUE, ctx)
    assert "labels" not in locked
    assert "locked" in locked
    assert "needs write access to owner/repo. You have triage access" in locked["locked"]
    read_only = ViewerContext(repo_role="admin", level=AccessLevel.READ_ONLY)
    assert all("read only in the Workbench" in r for r in locked_fields(ISSUE, read_only).values())


def test_a_plan_sends_only_changed_fields_one_request_per_endpoint(api: FakeGitHubApi) -> None:
    choices = load_options(api, ISSUE, IDENT)
    changed = [
        FieldChange("title", "Title", "Crash on start", "Crash at start"),
        FieldChange("labels", "Labels", ("docs",), ("docs", "bug")),
        FieldChange("milestone", "Milestone", "", "2027.1"),
        FieldChange("state", "State", "open", "closed as not planned"),
    ]
    requests = plan(ISSUE, IDENT, changed, choices)
    assert len(requests) == 1
    body = requests[0].body
    assert body == {
        "title": "Crash at start",
        "labels": ["docs", "bug"],
        "milestone": 7,
        "state": "closed",
        "state_reason": "not_planned",
    }


def test_a_three_state_delta_becomes_the_item_s_own_new_list() -> None:
    change = FieldChange("labels", "Labels", ("docs", "ui"), ListDelta(("bug",), ("ui",)))
    (request,) = plan(ISSUE, IDENT, [change])
    assert request.body == {"labels": ["docs", "bug"]}


def test_reactions_and_reviewers_send_one_request_per_addition_and_removal() -> None:
    ident = {**IDENT, "node_id": "I_42"}
    reactions = FieldChange("reactions", "Your reactions", ("heart",), ("rocket",))
    found = plan(ISSUE, ident, [reactions])
    assert [r.body for r in found] == [
        {"id": "I_42", "content": "ROCKET"},
        {"id": "I_42", "content": "HEART"},
    ]
    assert "addReaction" in found[0].graphql and "removeReaction" in found[1].graphql
    reviewers = FieldChange("reviewers", "Reviewers", ("a",), ("b",))
    sent = plan(PULL_REQUEST, IDENT, [reviewers])
    assert [(r.method, r.body) for r in sent] == [
        ("POST", {"reviewers": ["b"]}),
        ("DELETE", {"reviewers": ["a"]}),
    ]


def test_a_watch_level_of_participating_deletes_the_subscription() -> None:
    change = FieldChange("watch", "Watch level", "all activity", "participating and mentions")
    (request,) = plan(REPOSITORY, {"repo": REPO}, [change])
    assert (request.method, request.path, request.body) == (
        "DELETE",
        "/repos/owner/repo/subscription",
        None,
    )


def test_save_verifies_and_reports_only_what_the_re_read_proves(api: FakeGitHubApi) -> None:
    loaded = load(api, ISSUE, IDENT)
    choices = load_options(api, ISSUE, IDENT)
    outcome = save(
        api,
        ISSUE,
        IDENT,
        [
            FieldChange("labels", "Labels", ("docs",), ("bug",)),
            FieldChange("assignees", "Assignees", (), ("kellylford",)),
        ],
        loaded=loaded.values,
        choices=choices,
    )
    # The fake ignores assignees, as GitHub does for people without access.
    assert [c.key for c in outcome.done] == ["labels"]
    assert [c.key for c in outcome.not_taken] == ["assignees"]
    said = sentence("#42", outcome)
    assert said.startswith("#42: added bug, removed docs.")
    assert "did not change assignees" in said


def test_someone_else_s_change_stops_the_save_until_you_choose(api: FakeGitHubApi) -> None:
    loaded = load(api, ISSUE, IDENT)
    api.state["issue"] = _issue_json(title="Renamed by someone")  # type: ignore[attr-defined]
    change = FieldChange("title", "Title", "Crash on start", "Mine")
    outcome = save(api, ISSUE, IDENT, [change], loaded=loaded.values)
    assert [c.before for c in outcome.conflicts] == ["Renamed by someone"]
    assert api.writes() == []
    assert "Changed on GitHub since you opened this: title" in sentence("#42", outcome)
    kept = save(
        api,
        ISSUE,
        IDENT,
        [change],
        loaded=loaded.values,
        keep_theirs=frozenset({"title"}),
        check_conflicts=False,
    )
    assert kept.done == [] and api.writes() == []
    mine = save(api, ISSUE, IDENT, [change], loaded=loaded.values, check_conflicts=False)
    assert [c.key for c in mine.done] == ["title"]


def test_undo_is_the_inverse_and_says_what_cannot_be_undone() -> None:
    done = [
        FieldChange("labels", "Labels", ("docs",), ("bug",)),
        FieldChange("milestone", "Milestone", "", "2027.1"),
    ]
    back, cannot = inverse(ISSUE, done)
    assert [(c.key, c.after) for c in back] == [("labels", ("docs",)), ("milestone", "")]
    assert cannot == []


def test_renaming_a_label_moves_its_ident_for_the_re_read() -> None:
    api = FakeGitHubApi()
    api.answer("GET", "/repos/owner/repo/labels/bug", {"name": "bug", "color": "d73a4a"})
    api.answer("GET", "/repos/owner/repo/labels/defect", {"name": "defect", "color": "d73a4a"})
    ident = {"repo": REPO, "name": "bug"}
    loaded = load(api, LABEL, ident)
    assert loaded.values["colour_name"] == "red (d73a4a)"
    change = FieldChange("name", "Name", "bug", "defect")
    outcome = save(api, LABEL, ident, [change], loaded=loaded.values, check_conflicts=False)
    assert api.writes()[0] == ("PATCH", "/repos/owner/repo/labels/bug", {"new_name": "defect"})
    assert [c.key for c in outcome.done] == ["name"]


def test_a_label_colour_can_be_typed_as_a_word() -> None:
    change = FieldChange("colour", "Colour", "d73a4a", "green")
    (request,) = plan(LABEL, {"repo": REPO, "name": "bug"}, [change])
    assert request.body == {"color": "0e8a16"}


def test_a_milestone_due_date_is_sent_as_github_wants_it() -> None:
    ident = {"repo": REPO, "number": "7"}
    (request,) = plan(MILESTONE, ident, [FieldChange("due", "Due date", "", "2027-03-31")])
    assert request.body == {"due_on": "2027-03-31T00:00:00Z"}


def test_rows_and_nodes_name_their_object() -> None:
    from quill.core.github.explore_models import ExploreRow
    from quill.core.github.items_provider import GitHubItem

    item = GitHubItem(42, "Crash", "open", "https://github.com/owner/repo/issues/42", False)
    target = target_for(item, REPO)
    assert target == Target("issue", {"repo": REPO, "number": "42"})
    assert target.title() == "Issue #42 Properties - owner/repo"
    label = ExploreRow("bug", "", "", REPO, "label", "bug", title="bug")
    assert target_for(label) == Target("label", {"repo": REPO, "name": "bug"})
    milestone = ExploreRow("2027.1", "", "https://github.com/o/r/milestone/7", REPO, "milestone")
    found = target_for(milestone)
    assert found is not None and found.ident["number"] == "7"
    repo_row = ExploreRow("owner/repo", "", "", REPO, "repo", REPO)
    assert target_for(repo_row) == Target("repository", {"repo": REPO})
