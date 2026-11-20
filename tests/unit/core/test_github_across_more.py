"""PRD 22.11: tags, branches, environments, secrets, variables, webhooks, deploy keys and
autolinks by name across repositories; their previews, results and what GitHub cannot do.
Against a recorded fake of the Workbench's GitHubApi: nothing reaches GitHub.
"""

from __future__ import annotations

import base64
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github.across_by_name import survey
from quill.core.github.across_more_changes import (
    apply_more,
    plan_branch_rename,
    plan_hooks_on_off,
    plan_more_add,
    plan_more_delete,
    plan_more_same,
    plan_set_secret,
)
from quill.core.github.across_more_promote import (
    apply_more_promote,
    plan_more_promote,
    plan_release_train,
)


class FakeApi:
    def __init__(self, answers: dict[tuple[str, str], Any]) -> None:
        self.answers = answers
        self.sent: list[tuple[str, str, Any]] = []

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        if method != "GET":
            self.sent.append((method, path, body))
            failure = self.answers.get((method, path))
            if isinstance(failure, Exception):
                raise failure
            return SimpleNamespace(status=200, data={}, headers={})
        answer = self.answers.get((method, path))
        if callable(answer):
            answer = answer(query or {})
        if isinstance(answer, Exception):
            raise answer
        if answer is None:
            raise RuntimeError(f"404 Not Found: {path}")
        return SimpleNamespace(status=200, data=answer, headers={})


def _repo(admin: bool = True, default: str = "main", ident: int = 1) -> dict[str, Any]:
    return {
        "id": ident,
        "default_branch": default,
        "permissions": {"push": True, "admin": admin},
    }


# -- tags and the release train --------------------------------------------------------


def _tag_api() -> FakeApi:
    return FakeApi({
        ("GET", "/repos/a/one"): _repo(),
        ("GET", "/repos/a/two"): _repo(),
        ("GET", "/repos/a/three"): _repo(),
        ("GET", "/repos/a/one/tags"): [{"name": "v1", "commit": {"sha": "aaaaaaa111"}}],
        ("GET", "/repos/a/two/tags"): [{"name": "v1", "commit": {"sha": "bbbbbbb222"}}],
        ("GET", "/repos/a/three/tags"): [],
        ("GET", "/repos/a/three/git/matching-refs/tags/v1"): [],
        ("GET", "/repos/a/three/commits/main"): {"sha": "ccccccc333"},
    })


def test_tags_by_name_say_which_commit_each_is_on() -> None:
    found = survey(_tag_api(), "tags", ["a/one", "a/two", "a/three"])
    row = found.row("v1")
    assert row is not None
    assert row.sentence() == "v1: in 2 of 3 repositories, 2 different commits, missing from 1"
    assert "Variant 1, commit aaaaaaa: a/one" in row.detail()


def test_a_release_train_skips_a_repository_with_the_tag_and_never_moves_it() -> None:
    api = _tag_api()
    found = survey(api, "tags", ["a/one", "a/two", "a/three"])
    plan = plan_release_train(found, "v1", ["a/one", "a/three"], "tag")
    assert plan.steps[0].action == "skip" and "never moved" in plan.steps[0].after
    one, three = apply_more(api, plan)
    assert one.ok and one.said.startswith("no change")
    assert three.ok and "Made tag v1 on main, commit ccccccc" in three.said
    assert ("POST", "/repos/a/three/git/refs", {"ref": "refs/tags/v1", "sha": "ccccccc333"}) in (
        api.sent
    )
    assert not any(path.startswith("/repos/a/one") for _m, path, _b in api.sent)


def test_a_release_train_with_a_draft_release_and_a_tag_made_meanwhile() -> None:
    api = _tag_api()
    found = survey(api, "tags", ["a/one", "a/three"])
    plan = plan_release_train(found, "v1", ["a/three"], "draft", "Notes")
    assert "the tag is made when it is published" in plan.steps[0].after
    (three,) = apply_more(api, plan)
    assert three.ok and three.said == "drafted v1 on main"
    (sent,) = api.sent
    assert sent[1] == "/repos/a/three/releases" and sent[2]["draft"] is True
    api.answers[("GET", "/repos/a/three/git/matching-refs/tags/v1")] = [{"ref": "refs/tags/v1"}]
    (again,) = apply_more(api, plan)
    assert not again.ok and "an existing tag is never moved" in again.said


def test_a_tag_with_a_release_on_it_is_not_deleted() -> None:
    api = _tag_api()
    api.answers[("GET", "/repos/a/one/git/matching-refs/tags/v1")] = [{"ref": "refs/tags/v1"}]
    api.answers[("GET", "/repos/a/two/git/matching-refs/tags/v1")] = [{"ref": "refs/tags/v1"}]
    api.answers[("GET", "/repos/a/two/releases/tags/v1")] = {"name": "Version 1"}
    found = survey(api, "tags", ["a/one", "a/two"])
    one, two = apply_more(api, plan_more_delete(found, found.row("v1")))
    assert one.ok and ("DELETE", "/repos/a/one/git/refs/tags/v1", None) in api.sent
    assert not two.ok and "the release Version 1 is built on it" in two.said


# -- branches ----------------------------------------------------------------------------


def test_a_branch_rename_previews_default_protection_and_retargeted_pull_requests() -> None:
    api = FakeApi({
        ("GET", "/repos/a/one"): _repo(),
        ("GET", "/repos/a/two"): _repo(admin=False, default="trunk"),
        ("GET", "/repos/a/one/branches"): [{"name": "main", "protected": True}],
        ("GET", "/repos/a/two/branches"): [
            {"name": "main", "protected": True},
            {"name": "trunk", "protected": False},
        ],
        ("GET", "/repos/a/one/pulls"): [{"base": {"ref": "main"}}, {"base": {"ref": "main"}}],
        ("GET", "/repos/a/two/pulls"): [],
        ("GET", "/repos/a/one/branches/main"): {"name": "main"},
    })
    found = survey(api, "branches", ["a/one", "a/two"])
    row = found.row("main")
    assert row is not None and row.sentence().startswith(
        "main: in 2 of 2 repositories, default in 1, protected in 2"
    )
    plan = plan_branch_rename(found, row, "trunk")
    one, two = plan.steps
    assert one.after == (
        "renamed to trunk; the default branch becomes trunk; its protection moves with it; "
        "2 open pull requests based on it are retargeted"
    )
    assert "needs admin access" in two.blocked
    first, second = apply_more(api, plan)
    assert first.ok and ("POST", "/repos/a/one/branches/main/rename", {"new_name": "trunk"}) in (
        api.sent
    )
    assert not second.ok


# -- environments ------------------------------------------------------------------------


def _env(wait: int, reviewer: dict[str, Any] | None = None, policy: Any = None) -> dict[str, Any]:
    rules: list[dict[str, Any]] = [{"type": "wait_timer", "wait_timer": wait}]
    if reviewer is not None:
        rules.append({
            "type": "required_reviewers",
            "prevent_self_review": True,
            "reviewers": [reviewer],
        })
    return {"name": "production", "protection_rules": rules, "deployment_branch_policy": policy}


def test_environments_are_made_the_same_but_custom_branches_and_foreign_teams_are_not() -> None:
    team = {"type": "Team", "reviewer": {"slug": "release", "id": 9}}
    api = FakeApi({
        ("GET", "/repos/a/one"): _repo(),
        ("GET", "/repos/a/two"): _repo(),
        ("GET", "/repos/b/three"): _repo(),
        ("GET", "/repos/a/one/environments"): {"environments": [_env(30, team)]},
        ("GET", "/repos/a/two/environments"): {"environments": [_env(0)]},
        ("GET", "/repos/b/three/environments"): {"environments": [_env(5)]},
        ("GET", "/repos/a/two/environments/production"): _env(0),
    })
    found = survey(api, "environments", ["a/one", "a/two", "b/three"])
    row = found.row("production")
    assert row is not None and "3 wait timers" in row.sentence()
    winner = row.copies[0].props
    plan = plan_more_same(found, row, winner)
    skip, two, three = plan.steps
    assert skip.action == "skip" and not two.blocked
    assert "cannot review in another owner's" in three.blocked
    results = apply_more(api, plan)
    assert [r.ok for r in results] == [True, True, False]
    method, path, body = api.sent[0]
    assert (method, path) == ("PUT", "/repos/a/two/environments/production")
    assert body == {
        "wait_timer": 30,
        "prevent_self_review": True,
        "reviewers": [{"type": "Team", "id": 9}],
        "deployment_branch_policy": None,
    }
    custom = {"protected_branches": False, "custom_branch_policies": True}
    api.answers[("GET", "/repos/a/one/environments")] = {"environments": [_env(30, None, custom)]}
    found = survey(api, "environments", ["a/one", "a/two"])
    row = found.row("production")
    plan = plan_more_same(found, row, row.copies[0].props)
    assert "custom list of branches" in plan.steps[1].blocked


# -- secrets -----------------------------------------------------------------------------


def _public_key() -> dict[str, str]:
    pytest.importorskip("nacl")
    from nacl.public import PrivateKey

    key = PrivateKey.generate().public_key
    return {"key": base64.b64encode(bytes(key)).decode("ascii"), "key_id": "k1"}


def test_a_secret_is_typed_once_sealed_per_repository_and_never_kept() -> None:
    key = _public_key()
    api = FakeApi({
        ("GET", "/repos/a/one"): _repo(),
        ("GET", "/repos/a/two"): _repo(admin=False),
        ("GET", "/repos/a/three"): _repo(),
        ("GET", "/repos/a/one/actions/secrets"): {"secrets": [{"name": "TOKEN"}]},
        ("GET", "/repos/a/two/actions/secrets"): {"secrets": [{"name": "TOKEN"}]},
        ("GET", "/repos/a/three/actions/secrets"): {"secrets": []},
        ("GET", "/repos/a/one/actions/secrets/public-key"): key,
        ("GET", "/repos/a/three/actions/secrets/public-key"): key,
    })
    found = survey(api, "secrets", ["a/one", "a/two", "a/three"])
    row = found.row("TOKEN")
    assert row is not None and row.missing == ("a/three",)
    plan = plan_set_secret(found, "TOKEN", ["a/one", "a/two", "a/three"])
    assert "needs admin access" in plan.steps[1].blocked
    assert "s3cret" not in plan.preview()
    one, two, three = apply_more(api, plan, secret="s3cret")
    assert one.ok and three.ok and not two.ok
    for _method, _path, body in api.sent:
        assert "s3cret" not in repr(body) and body["key_id"] == "k1"
    assert one.log is not None and "s3cret" not in repr(one.log)


def test_a_secret_promoted_to_the_organization_deletes_copies_only_after() -> None:
    key = _public_key()
    api = FakeApi({
        ("GET", "/repos/a/one"): _repo(ident=11),
        ("GET", "/repos/b/two"): _repo(ident=22),
        ("GET", "/repos/a/one/actions/secrets"): {"secrets": [{"name": "TOKEN"}]},
        ("GET", "/repos/b/two/actions/secrets"): {"secrets": [{"name": "TOKEN"}]},
        ("GET", "/orgs/a/actions/secrets/public-key"): key,
        ("GET", "/repos/a/one/actions/secrets/TOKEN"): {"name": "TOKEN"},
    })
    found = survey(api, "secrets", ["a/one", "b/two"])
    row = found.row("TOKEN")
    plan = plan_more_promote(found, row, (), "a")
    head, one, two = apply_more_promote(api, plan, secret="v")
    assert head.ok and one.ok and two.ok and two.said.startswith("no change")
    put, delete = api.sent
    assert put[1] == "/orgs/a/actions/secrets/TOKEN"
    assert put[2]["visibility"] == "selected" and put[2]["selected_repository_ids"] == [11]
    assert delete[:2] == ("DELETE", "/repos/a/one/actions/secrets/TOKEN")
    api.sent.clear()
    api.answers[("PUT", "/orgs/a/actions/secrets/TOKEN")] = RuntimeError("403 Forbidden")
    head, one, _two = apply_more_promote(api, plan, secret="v")
    assert not head.ok and not one.ok and "was not created" in one.said
    assert [m for m, _p, _b in api.sent] == ["PUT"]


# -- variables, webhooks, deploy keys, autolinks -------------------------------------------


def test_variables_made_the_same_added_and_promoted() -> None:
    api = FakeApi({
        ("GET", "/repos/a/one"): _repo(ident=1),
        ("GET", "/repos/a/two"): _repo(ident=2),
        ("GET", "/repos/a/three"): _repo(ident=3),
        ("GET", "/repos/a/one/actions/variables"): {"variables": [{"name": "CH", "value": "beta"}]},
        ("GET", "/repos/a/two/actions/variables"): {"variables": [{"name": "CH", "value": "dev"}]},
        ("GET", "/repos/a/three/actions/variables"): {"variables": []},
        ("GET", "/repos/a/two/actions/variables/CH"): {"name": "CH", "value": "dev"},
        ("GET", "/repos/a/one/actions/variables/CH"): {"name": "CH", "value": "beta"},
    })
    found = survey(api, "variables", ["a/one", "a/two", "a/three"])
    row = found.row("CH")
    winner = (("value", "beta"),)
    assert [r.ok for r in apply_more(api, plan_more_same(found, row, winner))] == [True, True]
    assert api.sent[-1] == (
        "PATCH",
        "/repos/a/two/actions/variables/CH",
        {"name": "CH", "value": "beta"},
    )
    (added,) = apply_more(api, plan_more_add(found, row, winner))
    assert added.ok and api.sent[-1][1:] == (
        "/repos/a/three/actions/variables",
        {"name": "CH", "value": "beta"},
    )
    api.sent.clear()
    head, *_rest = apply_more_promote(api, plan_more_promote(found, row, winner, "a"))
    assert head.ok
    assert api.sent[0] == (
        "POST",
        "/orgs/a/actions/variables",
        {
            "name": "CH",
            "value": "beta",
            "visibility": "selected",
            "selected_repository_ids": [1, 2],
        },
    )


def _hook(ident: int, active: bool, events: list[str]) -> dict[str, Any]:
    url = "https://hooks.example.org/ci"
    return {"id": ident, "active": active, "events": events, "config": {"url": url}}


def test_webhooks_turned_off_made_the_same_keep_their_secret_and_promotion_is_honest() -> None:
    url = "https://hooks.example.org/ci"
    api = FakeApi({
        ("GET", "/repos/a/one"): _repo(),
        ("GET", "/repos/a/two"): _repo(),
        ("GET", "/repos/a/one/hooks"): [_hook(1, True, ["push"])],
        ("GET", "/repos/a/two/hooks"): [_hook(2, False, ["push", "release"])],
        ("GET", "/repos/a/one/hooks/1"): _hook(1, True, ["push"]),
        ("GET", "/repos/a/two/hooks/2"): _hook(2, False, ["push", "release"]),
    })
    found = survey(api, "webhooks", ["a/one", "a/two"])
    row = found.row(url)
    assert row is not None and "2 event lists" in row.sentence()
    off = plan_hooks_on_off(found, row, on=False)
    assert off.steps[1].action == "skip"
    apply_more(api, off)
    assert api.sent == [("PATCH", "/repos/a/one/hooks/1", {"active": False})]
    api.sent.clear()
    apply_more(api, plan_more_same(found, row, row.copies[0].props))
    assert api.sent == [
        ("PATCH", "/repos/a/two/hooks/2", {"events": ["push"], "active": True}),
        ("PATCH", "/repos/a/two/hooks/2/config", {"content_type": "form"}),
    ]
    plan = plan_more_promote(found, row, row.copies[0].props, "a")
    assert "for every repository in a, not only the set's" in plan.steps[0].after


def test_a_deploy_key_cannot_be_added_to_more_and_autolinks_are_added() -> None:
    api = FakeApi({
        ("GET", "/repos/a/one"): _repo(),
        ("GET", "/repos/a/two"): _repo(),
        ("GET", "/repos/a/one/keys"): [{"id": 4, "title": "deploy", "key": "ssh-ed25519 AAAA"}],
        ("GET", "/repos/a/two/keys"): [],
        ("GET", "/repos/a/one/autolinks"): [
            {"id": 7, "key_prefix": "JIRA-", "url_template": "https://j/<num>"}
        ],
        ("GET", "/repos/a/two/autolinks"): [],
    })
    keys = survey(api, "deploy_keys", ["a/one", "a/two"])
    row = keys.row("deploy")
    plan = plan_more_add(keys, row, row.copies[0].props)
    assert "one repository only" in plan.steps[0].blocked and not plan.runnable
    links = survey(api, "autolinks", ["a/one", "a/two"])
    row = links.row("JIRA-")
    (two,) = apply_more(api, plan_more_add(links, row, row.copies[0].props))
    assert two.ok and api.sent[-1] == (
        "POST",
        "/repos/a/two/autolinks",
        {"key_prefix": "JIRA-", "url_template": "https://j/<num>", "is_alphanumeric": False},
    )


def test_a_repository_that_refuses_is_unread_not_missing() -> None:
    api = FakeApi({
        ("GET", "/repos/a/one"): _repo(),
        ("GET", "/repos/a/two"): _repo(admin=False),
        ("GET", "/repos/a/one/actions/variables"): {"variables": [{"name": "X", "value": "1"}]},
        ("GET", "/repos/a/two/actions/variables"): RuntimeError("403 Forbidden"),
    })
    found = survey(api, "variables", ["a/one", "a/two"])
    row = found.row("X")
    assert row is not None and row.missing == () and found.unread
