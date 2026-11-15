"""GH-E: milestones' open work moved, topics, rulesets and protection aligned, Promote to
Organization, and what each write leaves for Change History. Against a recorded fake.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.core.github.across_admin_changes import (
    apply_admin,
    apply_promote,
    plan_promote,
    plan_rules_add_missing,
    plan_rules_same,
    plan_topic_add,
    plan_topic_remove,
)
from quill.core.github.across_by_name import survey
from quill.core.github.across_changes import apply, plan_move_open


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


def _repo(admin: bool = True) -> dict[str, Any]:
    return {"default_branch": "main", "permissions": {"push": True, "admin": admin}}


def test_open_work_moves_to_another_milestone_and_one_without_it_is_blocked() -> None:
    api = FakeApi({
        ("GET", "/repos/a/one"): _repo(),
        ("GET", "/repos/a/two"): _repo(),
        ("GET", "/repos/a/one/milestones"): [
            {"title": "1.0", "number": 1, "state": "open", "open_issues": 2, "closed_issues": 0},
            {"title": "1.1", "number": 2, "state": "open", "open_issues": 0, "closed_issues": 0},
        ],
        ("GET", "/repos/a/two/milestones"): [
            {"title": "1.0", "number": 4, "state": "open", "open_issues": 1, "closed_issues": 0},
        ],
        ("GET", "/repos/a/one/milestones/1"): {"state": "open"},
        ("GET", "/repos/a/one/issues"): lambda q: (
            [{"number": 7}, {"number": 8}] if q.get("page") == "1" else []
        ),
    })
    found = survey(api, "milestones", ["a/one", "a/two"])
    row = found.row("1.0")
    assert row is not None
    plan = plan_move_open(found, row, "1.1")
    assert "it has no milestone 1.1" in plan.steps[1].blocked
    one, two = apply(api, plan)
    assert one.ok and one.said == "moved 2 open items to 1.1 (#7, #8)"
    assert ("PATCH", "/repos/a/one/issues/7", {"milestone": 2}) in api.sent
    assert not two.ok and one.log is not None and not one.log.can_undo


def _topic_api() -> FakeApi:
    lists = {"a/one": ["docs", "a11y"], "a/two": ["docs"]}
    api = FakeApi({
        ("GET", "/repos/a/one"): _repo(),
        ("GET", "/repos/a/two"): _repo(),
        ("GET", "/repos/a/ro"): _repo(admin=False),
        ("GET", "/repos/a/ro/topics"): {"names": []},
    })
    for repo in lists:
        api.answers[("GET", f"/repos/{repo}/topics")] = lambda _q, r=repo: {"names": lists[r]}
    api.lists = lists  # type: ignore[attr-defined]
    return api


def test_topics_are_added_and_removed_keeping_the_others() -> None:
    api = _topic_api()
    found = survey(api, "topics", ["a/one", "a/two", "a/ro"])
    a11y = found.row("a11y")
    assert a11y is not None and a11y.missing == ("a/two", "a/ro")
    add = plan_topic_add(found, a11y)
    assert "needs admin access" in add.steps[1].blocked
    api.lists["a/two"].append("added-meanwhile")  # type: ignore[attr-defined]
    (two, ro) = apply_admin(api, add)
    assert (
        two.ok
        and ("PUT", "/repos/a/two/topics", {"names": ["docs", "added-meanwhile", "a11y"]})
        in api.sent
    )
    assert not ro.ok
    log = two.log
    assert log is not None and log.kind == "repository" and log.can_undo
    assert log.changes[0][2:] == (("docs", "added-meanwhile"), ("docs", "added-meanwhile", "a11y"))
    docs = found.row("docs")
    assert docs is not None
    removed = apply_admin(api, plan_topic_remove(found, docs))
    assert [r.ok for r in removed] == [True, True]
    assert ("PUT", "/repos/a/one/topics", {"names": ["a11y"]}) in api.sent


def _rules_api() -> FakeApi:
    full = {
        "name": "Main rules",
        "target": "branch",
        "enforcement": "active",
        "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
        "rules": [{"type": "deletion"}],
        "bypass_actors": [],
        "id": 1,
        "_links": {},
    }
    return FakeApi({
        ("GET", "/repos/org/one"): _repo(),
        ("GET", "/repos/org/two"): _repo(),
        ("GET", "/repos/me/three"): _repo(),
        ("GET", "/repos/org/one/rulesets"): [
            {"name": "Main rules", "id": 1, "enforcement": "active", "target": "branch"}
        ],
        ("GET", "/repos/org/two/rulesets"): [
            {"name": "Main rules", "id": 2, "enforcement": "evaluate", "target": "branch"}
        ],
        ("GET", "/repos/me/three/rulesets"): [],
        ("GET", "/repos/org/one/rulesets/1"): full,
        ("GET", "/repos/org/two/rulesets/2"): {**full, "id": 2, "enforcement": "evaluate"},
        ("GET", "/repos/org/one/branches/main/protection"): {
            "required_pull_request_reviews": {"required_approving_review_count": 2},
            "enforce_admins": {"enabled": True},
        },
        ("GET", "/repos/org/two/branches/main/protection"): RuntimeError("404 Not Found"),
        ("GET", "/repos/me/three/branches/main/protection"): {
            "required_pull_request_reviews": {"required_approving_review_count": 1},
        },
    })


def test_rulesets_and_protection_are_made_the_same_and_unprotecting_is_refused() -> None:
    api = _rules_api()
    found = survey(api, "rules", ["org/one", "org/two", "me/three"])
    rules = found.row("Main rules")
    assert rules is not None and rules.missing == ("me/three",)
    winner = next(p for p, repos in rules.variants() if repos == ["org/one"])
    results = apply_admin(api, plan_rules_same(found, rules, winner))
    sent = {(m, p): b for m, p, b in api.sent}
    body = sent[("PUT", "/repos/org/two/rulesets/2")]
    assert body["enforcement"] == "active" and "_links" not in body and "id" not in body
    assert [r.ok for r in results] == [True, True]
    added = apply_admin(api, plan_rules_add_missing(found, rules, winner))
    assert added[0].ok and ("POST", "/repos/me/three/rulesets") in {(m, p) for m, p, _b in api.sent}
    protection = found.row("Branch protection on main")
    assert protection is not None and "protection states" in protection.sentence()
    unprotected = next(p for p, repos in protection.variants() if repos == ["org/two"])
    refused = plan_rules_same(found, protection, unprotected)
    assert all("would remove it" in s.blocked for s in refused.steps if s.action != "skip")
    strict = next(p for p, repos in protection.variants() if repos == ["org/one"])
    done = apply_admin(api, plan_rules_same(found, protection, strict))
    put = {(m, p): b for m, p, b in api.sent}[("PUT", "/repos/me/three/branches/main/protection")]
    assert put["required_pull_request_reviews"]["required_approving_review_count"] == 2
    assert put["restrictions"] is None and put["enforce_admins"] is True
    assert any(r.ok for r in done)


def test_promote_creates_the_organization_ruleset_before_deleting_copies() -> None:
    api = _rules_api()
    found = survey(api, "rules", ["org/one", "org/two", "me/three"])
    rules = found.row("Main rules")
    assert rules is not None
    winner = next(p for p, repos in rules.variants() if repos == ["org/one"])
    plan = plan_promote(found, rules, winner, "org")
    results = apply_promote(api, plan)
    posted = [b for m, p, b in api.sent if (m, p) == ("POST", "/orgs/org/rulesets")]
    assert posted[0]["conditions"]["repository_name"]["include"] == ["one", "two"]
    deleted = [p for m, p, _b in api.sent if m == "DELETE"]
    assert deleted == ["/repos/org/one/rulesets/1", "/repos/org/two/rulesets/2"]
    assert all(r.ok for r in results)
    failing = _rules_api()
    failing.answers[("POST", "/orgs/org/rulesets")] = RuntimeError("403 Forbidden")
    kept = apply_promote(failing, plan_promote(found, rules, winner, "org"))
    assert not kept[0].ok and not [m for m, _p, _b in failing.sent if m == "DELETE"]
    assert "the organization ruleset was not created" in kept[1].said
