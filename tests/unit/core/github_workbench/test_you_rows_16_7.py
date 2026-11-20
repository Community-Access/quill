"""The rest of PRD 16.7: You relationships as context-menu rows, and the You page's new fields.

Recorded answers only (:class:`tests.github_api_fake.FakeGitHubApi` and a
small host for the quick-command mixin); nothing reaches GitHub.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github.explore_models import ExploreRow
from quill.core.github.items_provider import GitHubCommit, GitHubItem
from quill.core.github.quick_tables import QUICK
from quill.core.github.sheet_catalog import SHEETS
from quill.core.github.sheet_engine import SheetSaveError, load, save
from quill.core.github.star_lists import FOR_ITEM_MUTATION
from quill.core.github.you_local import apply_local, local_values, with_local_fields
from quill.core.workbench.properties import FieldChange, ListDelta
from quill.ui.github_workbench_quick import GitHubWorkbenchQuickMixin
from tests.github_api_fake import FakeGitHubApi

REPO = "acme/site"
state: dict[str, Any] = {"forked": False}


class _Frame:
    def __init__(self, key: str = "", instance: str = REPO) -> None:
        self.current = type("Ref", (), {"key": key, "instance": instance})()
        self.frame = None
        self.reloads = 0

    def reload(self) -> None:
        self.reloads += 1


class _Host(GitHubWorkbenchQuickMixin):
    def __init__(self, api: FakeGitHubApi, answers: list[Any], **frame: str) -> None:
        self.api, self.answers, self.said, self.signed_in = api, answers, [], True
        self.frame = _Frame(**frame)
        self._say = self.said.append  # type: ignore[assignment]
        self._background = lambda _w, work, done: done(work())  # type: ignore[assignment]
        self._choose = lambda *a, **k: self.answers.pop(0)  # type: ignore[assignment]
        self._confirm = lambda *a, **k: self.answers.pop(0)  # type: ignore[assignment]
        self._ask_text = lambda *a, **k: self.answers.pop(0)  # type: ignore[assignment]

    def github_api(self) -> Any:
        return self.api


def _issue(number: int = 4) -> GitHubItem:
    return GitHubItem(number, "Crash", "open", f"https://github.com/{REPO}/issues/{number}", False)


def _quick(verb: str) -> Any:
    return next(q for q in QUICK if q.verb == verb)


# -- Subscribe and Block --------------------------------------------------------------


@pytest.mark.parametrize(
    ("row", "fragment"),
    [
        (_issue(), "issueOrPullRequest"),
        (GitHubCommit(sha="abc123", short_sha="abc123", message="m"), "object(expression"),
        (ExploreRow("Ideas", "d", "u", REPO, "discussion", "7"), "discussion(number"),
    ],
)
def test_subscribe_sends_update_subscription_and_says_what_github_kept(
    row: object, fragment: str
) -> None:
    api = FakeGitHubApi()
    api.answer_graphql(fragment, {"repository": {"issueOrPullRequest": {"id": "N1"},
                                                  "object": {"id": "N1"},
                                                  "discussion": {"id": "N1"}}})  # fmt: skip
    api.answer_graphql(
        "updateSubscription",
        {"updateSubscription": {"subscribable": {"id": "N1", "viewerSubscription": "SUBSCRIBED"}}},
    )
    host = _Host(api, [0])  # All activity
    host._do_subscribe(None, row)
    query, variables = api.graphql_calls[-1]
    assert "updateSubscription" in query and variables == {"id": "N1", "state": "SUBSCRIBED"}
    assert host.said[-1].startswith("Subscribed to ") and host.said[-1].endswith("activity.")


def test_unsubscribe_says_when_you_still_hear_of_it() -> None:
    api = FakeGitHubApi()
    api.answer_graphql("issueOrPullRequest", {"repository": {"issueOrPullRequest": {"id": "N"}}})
    api.answer_graphql(
        "updateSubscription",
        {"updateSubscription": {"subscribable": {"viewerSubscription": "UNSUBSCRIBED"}}},
    )
    host = _Host(api, [1])
    host._do_subscribe(None, _issue())
    assert host.said == [
        "Unsubscribed from #4, Crash: you hear of it only when you take part or are mentioned."
    ]


@pytest.mark.parametrize(("pick", "method"), [(0, "PUT"), (1, "DELETE")])
def test_block_or_unblock_is_the_person_sheets_own_request(pick: int, method: str) -> None:
    api = FakeGitHubApi()
    host = _Host(api, [pick])
    host._do_block_person(None, ExploreRow("sam", "d", "u", "", "person", "sam"))
    assert api.writes() == [(method, "/user/blocks/sam", None)]
    assert host.said[-1].startswith("Blocked sam:" if pick == 0 else "Unblocked sam.")
    assert "/user/blocks/" in SHEETS["person"].writes["blocked"].path  # the You page's own


# -- repositories: Fork, star lists, sponsoring ----------------------------------------


def test_fork_row_forks_to_you_or_an_organization() -> None:
    api = FakeGitHubApi()
    api.answer("POST", f"/repos/{REPO}/forks", {"full_name": "team/site"})
    host = _Host(api, ["team"])
    host._do_fork(None, ExploreRow(REPO, "d", "u", REPO, "repo", REPO))
    assert api.writes() == [("POST", f"/repos/{REPO}/forks", {"organization": "team"})]
    assert host.said == [f"Forked {REPO} to team/site. GitHub copies its files in a moment."]


def _repo_api(lists: list[dict[str, Any]], forked: bool = False) -> FakeGitHubApi:
    api = FakeGitHubApi()
    api.answer("GET", f"/repos/{REPO}", {"name": "site", "full_name": REPO})
    api.answer_graphql("viewerPermission", {"repository": {"id": "R1"}})
    api.answer_graphql("lists(first: 100)", lambda: {"viewer": {"lists": {"nodes": lists}}})
    api.answer_graphql(
        "parent{nameWithOwner}",
        lambda: {"viewer": {"repository": {"parent": {"nameWithOwner": REPO}} if state["forked"]
                            else None}},
    )  # fmt: skip
    state["forked"] = forked
    return api


def _lists(*holding: str) -> list[dict[str, Any]]:
    out = []
    for name, ident in (("Tools", "L1"), ("Reading", "L2")):
        items = [{"nameWithOwner": REPO, "description": ""}] if name in holding else []
        out.append({"id": ident, "name": name, "description": "", "isPrivate": False,
                    "items": {"nodes": items}})  # fmt: skip
    return out


def test_the_repository_you_page_reads_lists_fork_and_sponsoring() -> None:
    api = _repo_api(_lists("Tools"), forked=True)
    api.answer_graphql("viewerIsSponsoring", {"repositoryOwner": {"viewerIsSponsoring": True}})
    values = load(api, SHEETS["repository"], {"repo": REPO}).values
    assert values["star_lists"] == ("Tools",)
    assert values["forked"] is True and values["sponsoring"] is True
    spec = SHEETS["repository"].sheet.field("sponsoring")
    assert spec.readonly and "Sponsor the Owner..." in spec.help and "money" in spec.help


def test_star_lists_save_is_star_lists_own_mutation_and_is_checked() -> None:
    held = ["Tools"]
    api = _repo_api([])
    api.graphql_answers.clear()
    api.answer_graphql("viewerPermission", {"repository": {"id": "R1"}})
    api.answer_graphql("lists(first: 100)", lambda: {"viewer": {"lists": {"nodes": _lists(*held)}}})
    sheet = SHEETS["repository"]
    loaded = load(api, sheet, {"repo": REPO}).values
    choices = {"star_lists": {"Tools": "L1", "Reading": "L2"}}
    change = FieldChange("star_lists", "Star lists", ("Tools",), ListDelta(added=("Reading",)))

    def mutation() -> dict[str, Any]:
        held.append("Reading")
        return {}

    api.answer_graphql("updateUserListsForItem", mutation)
    outcome = save(api, sheet, {"repo": REPO}, [change], loaded=loaded, choices=choices)
    query, variables = next(c for c in api.graphql_calls if "updateUserListsForItem" in c[0])
    assert query == FOR_ITEM_MUTATION
    assert variables == {"itemId": "R1", "listIds": ["L1", "L2"]}
    assert outcome.ok and [c.key for c in outcome.done] == ["star_lists"]


def test_forking_from_the_you_page_is_checked_and_unforking_is_refused() -> None:
    api = _repo_api([], forked=False)
    sheet = SHEETS["repository"]
    loaded = load(api, sheet, {"repo": REPO}).values
    assert loaded["forked"] is False
    api.on_write = lambda *_a: state.update(forked=True)
    outcome = save(
        api, sheet, {"repo": REPO}, [FieldChange("forked", "Forked by you", False, True)],
        loaded=loaded,
    )  # fmt: skip
    assert api.writes() == [("POST", f"/repos/{REPO}/forks", {})]
    assert outcome.ok and sheet.writes["forked"].undo is False
    with pytest.raises(SheetSaveError, match="Delete Repository"):
        save(
            api, sheet, {"repo": REPO}, [FieldChange("forked", "Forked by you", True, False)],
            loaded={**loaded, "forked": True},
        )  # fmt: skip


# -- Pin and Favorite, on this device ----------------------------------------------------


class _Saved:
    def __init__(self) -> None:
        self.favorites: list[Any] = []
        self.pinned: set[str] = set()
        self.saves = 0

    def add_favorite(self, item: Any) -> bool:
        self.favorites.append(item)
        return True

    def remove_favorite(self, key: str) -> bool:
        self.favorites = [f for f in self.favorites if f.key != key]
        return True

    def is_pinned(self, repo: str) -> bool:
        return repo in self.pinned

    def pin_repo(self, repo: str) -> bool:
        self.pinned.add(repo)
        return True

    def unpin_repo(self, repo: str) -> bool:
        self.pinned.discard(repo)
        return True

    def save(self) -> None:
        self.saves += 1


def test_pin_and_favorite_join_the_repository_you_page_and_change_the_same_store() -> None:
    sheet = with_local_fields(SHEETS["repository"].sheet, "repository")
    you = next(page for page in sheet.pages if page.key == "you")
    assert [f.key for f in you.fields][-2:] == ["in_favorites", "workbench_pinned"]
    saved, url, ident = _Saved(), f"https://github.com/{REPO}", {"repo": REPO}
    changes = [
        FieldChange("in_favorites", "In Favorites", False, True),
        FieldChange("workbench_pinned", "Pinned in the Workbench", False, True),
        FieldChange("starred", "Starred", False, True),
    ]
    said, rest = apply_local(saved, "repository", ident, url, REPO, changes)
    assert said == [f"Added {REPO} to Favorites.", f"Pinned {REPO} in the Workbench."]
    assert [c.key for c in rest] == ["starred"]  # GitHub's, for the one checked save path
    assert local_values(saved, "repository", ident, url) == {
        "in_favorites": True,
        "workbench_pinned": True,
    }
    apply_local(
        saved, "repository", ident, url, REPO, [FieldChange("in_favorites", "", True, False)]
    )
    assert local_values(saved, "repository", ident, url)["in_favorites"] is False


def test_an_issue_gets_favorite_and_a_label_has_no_local_fields() -> None:
    issue = with_local_fields(SHEETS["issue"].sheet, "issue")
    assert "in_favorites" in [f.key for f in issue.fields()]
    assert "in_favorites" not in SHEETS["issue"].writes  # never a GitHub write
    assert with_local_fields(SHEETS["label"].sheet, "label") is SHEETS["label"].sheet


# -- organizations, invitations, comments -----------------------------------------------


def test_block_from_organization_asks_then_sends_the_block() -> None:
    api = FakeGitHubApi()
    host = _Host(api, ["spammer", True], instance="acme")
    host._do_block_from_org(None, ExploreRow("acme", "d", "u", "", "org", "acme"))
    assert api.writes() == [("PUT", "/orgs/acme/blocks/spammer", None)]
    assert host.said == ["Blocked spammer from acme. Its Blocked Users list unblocks."]


def test_leaving_asks_first_and_cancel_sends_nothing() -> None:
    api = FakeGitHubApi()
    api.answer("GET", "/user", {"login": "jeff"})
    host = _Host(api, [False], instance="acme")
    row = ExploreRow("acme", "d", "u", "", "org", "acme")
    host._do_leave_org(None, row)
    assert api.writes() == []
    host.answers = [True]
    host._do_leave_org(None, row)
    assert api.writes() == [("DELETE", "/orgs/acme/memberships/jeff", None)]
    assert host.said[-1] == "You have left acme."


def test_your_invitation_says_github_cannot_decline_and_where_it_can() -> None:
    api = FakeGitHubApi()
    api.answer("GET", "/user/memberships/orgs/acme", {"state": "pending", "role": "member"})
    host = _Host(api, [], instance="acme")
    host._do_org_invitation(None, ExploreRow("acme", "d", "u", "", "org", "acme"))
    assert "API cannot decline" in host.said[0]
    assert "https://github.com/orgs/acme/invitation" in host.said[0]
    assert api.writes() == []
    assert not _quick("org_invitation").writes


@pytest.mark.parametrize(("mine", "method"), [(False, "POST"), (True, "DELETE")])
def test_react_to_a_comment_adds_or_takes_back_only_yours(mine: bool, method: str) -> None:
    api = FakeGitHubApi()
    api.answer("GET", "/user", {"login": "jeff"})
    api.answer(
        "GET",
        f"/repos/{REPO}/issues/4/comments",
        [{"id": 11, "body": "It crashes", "user": {"login": "jo"}}],
    )
    theirs = {"id": 1, "content": "heart", "user": {"login": "jo"}}
    yours = {"id": 2, "content": "heart", "user": {"login": "jeff"}}
    api.answer(
        "GET", f"/repos/{REPO}/issues/comments/11/reactions", [theirs, *([yours] if mine else [])]
    )
    host = _Host(api, [0, 4])  # the comment, then Heart
    host._do_react_comment(None, _issue())
    if mine:
        assert api.writes() == [("DELETE", f"/repos/{REPO}/issues/comments/11/reactions/2", None)]
        assert host.said == ["Took back your heart from jo's comment."]
    else:
        assert api.writes() == [
            ("POST", f"/repos/{REPO}/issues/comments/11/reactions", {"content": "heart"})
        ]
        assert host.said == ["Added a heart to jo's comment."]


def test_a_discussion_comment_reaction_toggles_by_what_github_says_is_yours() -> None:
    api = FakeGitHubApi()
    api.answer_graphql(
        "comments(first:50)",
        {"repository": {"discussion": {"comments": {"nodes": [
            {"id": "C1", "body": "Hi", "author": {"login": "jo"}, "replies": {"nodes": []}}
        ]}}}},
    )  # fmt: skip
    api.answer_graphql(
        "reactionGroups",
        {"node": {"reactionGroups": [{"content": "ROCKET", "viewerHasReacted": True}]}},
    )
    host = _Host(api, [0, 6])  # the comment, then Rocket
    host._do_react_discussion_comment(None, ExploreRow("Ideas", "d", "u", REPO, "discussion", "7"))
    query, variables = api.graphql_calls[-1]
    assert "removeReaction" in query and variables == {"id": "C1", "c": "ROCKET"}
    assert host.said == ["Took back your rocket from jo's comment."]


def test_every_new_row_says_its_outcome_and_has_a_live_scenario_reason() -> None:
    for verb in (
        "subscribe",
        "block_person",
        "fork",
        "block_from_org",
        "block_member",
        "leave_org",
        "react_comment",
        "react_discussion_comment",
    ):
        quick = _quick(verb)
        assert quick.writes and quick.live, verb
