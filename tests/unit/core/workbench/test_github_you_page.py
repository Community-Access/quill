"""GH-R-046: every relationship on a You page, right after General, and in batch (PRD 16.7).

Every test talks to :class:`tests.github_api_fake.FakeGitHubApi`; nothing
reaches GitHub. For each kind of object: the You page is the second page and
holds the relationships :data:`YOU_PAGES` names; changing one sends only that
relationship, through the request its menu row sends too; several selected
show Mixed and change each of them; and a relationship GitHub's API cannot
change reads, with one sentence saying why.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from quill.core.github.batch import BatchItem, run
from quill.core.github.permissions import AccessLevel, ViewerContext, level_refusal
from quill.core.github.quick_table_discuss import DISCUSS_QUICK
from quill.core.github.sheet_catalog import SHEETS
from quill.core.github.sheet_engine import load, locked_fields, save
from quill.core.github.sheet_fields import input_mutation
from quill.core.github.sheets_you import YOU_PAGES, you_page_keys
from quill.core.workbench.properties import MIXED, FieldChange, ListDelta, merge_values
from tests.github_api_fake import FakeGitHubApi

#: Read-only relationships GitHub's API cannot change, each of which must say why.
CANNOT_CHANGE = {
    "repository": ("custom_watch", "profile_pinned"),
    "gist": ("profile_pinned",),
    "person": ("sponsoring", "report"),
    "organization": ("sponsoring",),
    "pull_request": ("pinned",),
    "discussion": ("pinned",),
}


@pytest.mark.parametrize("kind", sorted(YOU_PAGES))
def test_the_you_page_is_right_after_general_with_its_relationships(kind: str) -> None:
    sheet = SHEETS[kind]
    pages = [page.key for page in sheet.sheet.pages]
    assert pages[:2] == ["general", "you"], (kind, pages)
    editable, read_only = YOU_PAGES[kind]
    assert you_page_keys(sheet) == editable + read_only
    for key in editable:
        spec = sheet.sheet.field(key)
        assert not spec.readonly, (kind, key)
        assert key in sheet.writes, (kind, key)
    for key in read_only:
        assert sheet.sheet.field(key).readonly, (kind, key)
        assert key not in sheet.writes, (kind, key)


def test_a_sheet_without_a_relationship_has_no_you_page() -> None:
    for kind, sheet in SHEETS.items():
        if kind not in YOU_PAGES:
            assert not you_page_keys(sheet), kind


@pytest.mark.parametrize(
    ("kind", "key"), [(k, f) for k, keys in CANNOT_CHANGE.items() for f in keys]
)
def test_a_relationship_github_cannot_change_reads_and_says_why(kind: str, key: str) -> None:
    spec = SHEETS[kind].sheet.field(key)
    assert spec.readonly
    why = spec.help.strip()
    assert why.endswith("."), (kind, key, why)
    assert any(word in why for word in ("API", "money", "GitHub")), (kind, key, why)


def test_read_only_and_safe_mode_lock_every_relationship_with_the_reason() -> None:
    ctx = ViewerContext(signed_in=True, repo_role="admin", org_role="owner", is_self=True)
    ctx_read_only = ViewerContext(
        signed_in=True, repo_role="admin", org_role="owner", is_self=True,
        level=AccessLevel.READ_ONLY,
    )  # fmt: skip
    for kind, (editable, _read_only) in YOU_PAGES.items():
        sheet = SHEETS[kind]
        locked = locked_fields(sheet, ctx_read_only)
        for key in editable:
            assert locked.get(key) == level_refusal(
                AccessLevel.READ_ONLY, sheet.writes[key].tier
            ), (kind, key)
        assert "starred" not in locked_fields(SHEETS["repository"], ctx)


# -- one kind at a time: only the changed relationship is sent ----------------------


def _save(api: FakeGitHubApi, kind: str, ident: dict[str, str], key: str, after: Any) -> Any:
    sheet = SHEETS[kind]
    loaded = load(api, sheet, ident).values
    change = FieldChange(key, sheet.sheet.field(key).label, loaded.get(key), after)
    return save(api, sheet, ident, [change], loaded=loaded, check_conflicts=False)


def _mutations(api: FakeGitHubApi) -> list[tuple[str, dict[str, Any]]]:
    return [(q, v) for q, v in api.graphql_calls if q.lstrip().startswith("mutation")]


def _repository_api(starred: dict[str, bool]) -> FakeGitHubApi:
    api = FakeGitHubApi()
    api.answer("GET", "/repos/owner/repo", {"full_name": "owner/repo", "name": "repo"})
    api.answer("GET", "/repos/owner/repo/subscription", {"subscribed": True})
    api.answer_graphql(
        "viewerHasStarred",
        lambda: {"repository": {"id": "R_1", "viewerHasStarred": starred["on"]}},
    )
    api.answer_graphql(
        "pinnedItems",
        {"viewer": {"pinnedItems": {"nodes": [{"nameWithOwner": "Owner/Repo"}]}}},
    )

    def on_write(method: str, path: str, _body: Any) -> None:
        if path == "/user/starred/owner/repo":
            starred["on"] = method == "PUT"

    api.on_write = on_write
    return api


def test_a_repository_star_is_the_one_request_sent_and_proven() -> None:
    state = {"on": False}
    api = _repository_api(state)
    loaded = load(api, SHEETS["repository"], {"repo": "owner/repo"}).values
    assert loaded["starred"] is False and loaded["watch"] == "all activity"
    assert loaded["profile_pinned"] is True  # read from your profile's pins, case-blind
    outcome = _save(api, "repository", {"repo": "owner/repo"}, "starred", True)
    assert api.writes() == [("PUT", "/user/starred/owner/repo", None)]
    assert outcome.ok and [c.key for c in outcome.done] == ["starred"]


def test_a_repository_watch_level_is_its_subscription_only() -> None:
    api = _repository_api({"on": False})
    _save(api, "repository", {"repo": "owner/repo"}, "watch", "ignore")
    assert api.writes() == [
        ("PUT", "/repos/owner/repo/subscription", {"subscribed": False, "ignored": True})
    ]


def test_a_person_follow_is_the_request_follow_or_unfollow_sends() -> None:
    api = FakeGitHubApi()
    api.answer("GET", "/users/sam", {"login": "sam", "type": "User"})
    api.answer_graphql("Sponsorable", {"repositoryOwner": {"viewerIsSponsoring": True}})
    loaded = load(api, SHEETS["person"], {"login": "sam", "me": "me"}).values
    assert loaded["following"] is False and loaded["blocked"] is False
    assert loaded["sponsoring"] is True
    _save(api, "person", {"login": "sam", "me": "me"}, "following", True)
    # The same PUT /user/following/{login} as Follow or Unfollow (repo_actions.set_following).
    assert api.writes() == [("PUT", "/user/following/sam", None)]


def test_an_organization_follow_is_the_follow_organization_row_s_own_mutation() -> None:
    api = FakeGitHubApi()
    api.answer("GET", "/orgs/acme", {"login": "acme"})
    api.answer_graphql(
        "viewerIsFollowing",
        {"organization": {"id": "O_1", "viewerIsFollowing": False, "viewerIsSponsoring": False}},
    )
    api.answer_graphql("organization(login: $l)", {"organization": {"id": "O_1"}})
    _save(api, "organization", {"org": "acme", "me": "me"}, "following", True)
    sheet_call = _mutations(api)
    assert api.writes() == [] and len(sheet_call) == 1
    query, variables = sheet_call[0]
    assert query == input_mutation("followOrganization")
    assert variables == {"input": {"organizationId": "O_1"}}

    row = next(q for q in DISCUSS_QUICK if q.verb == "follow_org")
    row.run(api, {"org": "acme"})
    assert _mutations(api)[-1] == sheet_call[0], "the menu row and the check box are one call"


def _item_api(kind: str) -> FakeGitHubApi:
    api = FakeGitHubApi()
    path = "pulls" if kind == "pull_request" else "issues"
    api.answer("GET", f"/repos/owner/repo/{path}/7", {"number": 7, "title": "T", "state": "open"})
    api.answer_graphql(
        "issueOrPullRequest",
        {
            "repository": {
                "viewerPermission": "TRIAGE",
                "issueOrPullRequest": {
                    "id": "I_7",
                    "viewerCanSubscribe": True,
                    "viewerCanReact": True,
                    "viewerSubscription": "UNSUBSCRIBED",
                    "reactionGroups": [{"content": "HEART", "viewerHasReacted": True}],
                },
            }
        },
    )
    return api


def test_an_issue_pin_is_pin_issue_and_nothing_else() -> None:
    api = _item_api("issue")
    _save(api, "issue", {"repo": "owner/repo", "number": "7"}, "pinned", True)
    ((query, variables),) = _mutations(api)
    assert "pinIssue(" in query and variables == {"id": "I_7"}
    assert api.writes() == []


def test_a_pull_request_reaction_is_one_add_reaction() -> None:
    api = _item_api("pull_request")
    ident = {"repo": "owner/repo", "number": "7"}
    sheet = SHEETS["pull_request"]
    loaded = load(api, sheet, ident).values
    assert loaded["reactions"] == ("heart",) and loaded["pinned"] is False
    change = FieldChange("reactions", "Your reactions", ("heart",), ListDelta(("rocket",), ()))
    save(api, sheet, ident, [change], loaded=loaded, check_conflicts=False)
    ((query, variables),) = _mutations(api)
    assert "addReaction(" in query and variables == {"id": "I_7", "content": "ROCKET"}


def _discussion_api() -> FakeGitHubApi:
    api = FakeGitHubApi()
    api.answer_graphql(
        "discussion(number:$number)",
        {
            "repository": {
                "discussion": {
                    "id": "D_3",
                    "title": "Ideas",
                    "upvoteCount": 4,
                    "viewerCanUpvote": True,
                    "viewerHasUpvoted": False,
                    "viewerCanSubscribe": True,
                    "viewerCanReact": True,
                    "viewerSubscription": "SUBSCRIBED",
                    "reactionGroups": [{"content": "EYES", "viewerHasReacted": True}],
                }
            }
        },
    )
    api.answer_graphql(
        "pinnedDiscussions",
        {"repository": {"pinnedDiscussions": {"nodes": [{"discussion": {"number": 3}}]}}},
    )
    api.answer_graphql("discussion(number: $x)", {"repository": {"discussion": {"id": "D_3"}}})
    return api


def test_a_discussion_reads_its_relationships_and_upvotes_as_the_row_does() -> None:
    api = _discussion_api()
    ident = {"repo": "owner/repo", "number": "3"}
    loaded = load(api, SHEETS["discussion"], ident).values
    assert loaded["subscribed"] is True and loaded["upvoted"] is False
    assert loaded["reactions"] == ("eyes",) and loaded["pinned"] is True
    _save(api, "discussion", ident, "upvoted", True)
    sheet_call = _mutations(api)
    assert sheet_call == [(input_mutation("addUpvote"), {"input": {"subjectId": "D_3"}})]

    row = next(q for q in DISCUSS_QUICK if q.verb == "upvote_discussion")
    row.run(api, {"repo": "owner/repo", "key": "3"})
    assert _mutations(api)[-1] == sheet_call[0], "Upvote on the row is the same call"


def test_a_discussion_unsubscribe_is_update_subscription_only() -> None:
    api = _discussion_api()
    _save(api, "discussion", {"repo": "owner/repo", "number": "3"}, "subscribed", False)
    ((query, variables),) = _mutations(api)
    assert "updateSubscription(" in query
    assert variables == {"id": "D_3", "state": "UNSUBSCRIBED"}


def test_a_release_reaction_goes_to_the_release_s_node() -> None:
    api = FakeGitHubApi()
    api.answer("GET", "/repos/owner/repo/releases/tags/v1", {"id": 9, "tag_name": "v1"})
    api.answer_graphql(
        "release(tagName:$tag)",
        {"repository": {"release": {"id": "RE_9", "viewerCanReact": True, "reactionGroups": []}}},
    )
    sheet = SHEETS["release"]
    ident = {"repo": "owner/repo", "tag": "v1"}
    loaded = load(api, sheet, ident).values
    assert loaded["reactions"] == ()
    change = FieldChange("reactions", "Your reactions", (), ("hooray",))
    save(api, sheet, ident, [change], loaded=loaded, check_conflicts=False)
    ((query, variables),) = _mutations(api)
    assert "addReaction(" in query and variables == {"id": "RE_9", "content": "HOORAY"}


def test_a_gist_star_is_its_star_request() -> None:
    api = FakeGitHubApi()
    api.answer("GET", "/gists/abc", {"id": "abc", "public": True})
    _save(api, "gist", {"id": "abc"}, "starred", True)
    assert api.writes() == [("PUT", "/gists/abc/star", None)]


# -- several at once ---------------------------------------------------------------

Maker = Callable[[], tuple[FakeGitHubApi, list[dict[str, str]]]]


def _repos() -> tuple[FakeGitHubApi, list[dict[str, str]]]:
    api = FakeGitHubApi()
    starred = {"owner/a": True, "owner/b": False, "owner/c": False}
    for repo in starred:
        api.answer("GET", f"/repos/{repo}", {"full_name": repo})

    def viewer() -> dict[str, Any]:
        # The fake answers GraphQL by fragment, not variables: the repository the
        # last read asked for is the one that answers.
        repo = api.graphql_calls[-1][1].get("name", "")
        return {"repository": {"id": f"R_{repo}", "viewerHasStarred": starred[f"owner/{repo}"]}}

    api.answer_graphql("viewerHasStarred", viewer)

    def on_write(method: str, path: str, _body: Any) -> None:
        starred[path.removeprefix("/user/starred/")] = method == "PUT"

    api.on_write = on_write
    return api, [{"repo": repo} for repo in starred]


def _people() -> tuple[FakeGitHubApi, list[dict[str, str]]]:
    api = FakeGitHubApi()
    for login in ("ann", "bo"):
        api.answer("GET", f"/users/{login}", {"login": login})
    api.answer("GET", "/user/following/ann", {})  # ann is followed already

    def on_write(method: str, path: str, _body: Any) -> None:
        if method == "PUT":
            api.answer("GET", path, {})  # GitHub's 204: now followed

    api.on_write = on_write
    return api, [{"login": "ann", "me": "me"}, {"login": "bo", "me": "me"}]


@pytest.mark.parametrize(
    ("kind", "make", "key", "after", "sent", "skipped"),
    [
        (
            "repository",
            _repos,
            "starred",
            True,
            ["/user/starred/owner/b", "/user/starred/owner/c"],
            1,
        ),
        ("person", _people, "following", True, ["/user/following/bo"], 1),
    ],
)
def test_batch_shows_mixed_and_changes_each_selected_row(
    kind: str, make: Maker, key: str, after: Any, sent: list[str], skipped: int
) -> None:
    api, idents = make()
    sheet = SHEETS[kind]
    loads = [load(api, sheet, ident).values for ident in idents]
    assert merge_values(loads)[key] is MIXED
    label = sheet.sheet.field(key).label
    items = [
        BatchItem(str(i), ident, values)
        for i, (ident, values) in enumerate(zip(idents, loads, strict=True))
    ]
    results = run(api, sheet, items, [FieldChange(key, label, MIXED, after)], pace=0)
    assert [path for _method, path, _body in api.writes()] == sent
    assert sum(r.status == "Skipped" for r in results) == skipped
    assert all(r.status in ("Done", "Skipped") for r in results), [r.row() for r in results]
