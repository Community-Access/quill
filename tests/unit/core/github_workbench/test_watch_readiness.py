"""Watch Readiness: says once when a pull request can merge, and once when it stops (GX09)."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from quill.core.github.rest_transport import GitHubRestError, RestResponse
from quill.core.github.watches import READY, WatchStore, check_round, parse_target


def _pull(**changes: Any) -> dict[str, Any]:
    pull: dict[str, Any] = {
        "state": "OPEN",
        "mergeable": "MERGEABLE",
        "mergeStateStatus": "BLOCKED",
        "reviewDecision": "REVIEW_REQUIRED",
        "headRefOid": "abc1234def",
        "baseRefName": "main",
        "commits": {"nodes": []},
    }
    pull.update(changes)
    return pull


CLEAN = {"mergeStateStatus": "CLEAN", "reviewDecision": "APPROVED"}


class FakeApi:
    """One pull request's GraphQL answer, which a test changes; REST rules by path."""

    def __init__(self, pull: dict[str, Any], rest: Mapping[str, Any] | None = None) -> None:
        self.pull, self.answers = pull, dict(rest or {})
        self.reads: list[str] = []

    def graphql(self, query: str, variables: Mapping[str, object]) -> dict[str, Any]:
        self.reads.append("GRAPHQL")
        return {"repository": {"pullRequest": self.pull}}

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        self.reads.append(path)
        if path not in self.answers:
            raise GitHubRestError("Not Found", status=404)
        return RestResponse(200, {}, self.answers[path])


def _store() -> WatchStore:
    store = WatchStore.load("alice")
    store.add(READY, "o/r", number=4)
    return store


def test_the_target_is_a_pull_request_and_the_rule_reads_plainly(quill_data_dir: Path) -> None:
    assert parse_target(READY, "https://github.com/o/r/pull/4") == ("o/r", "", 4)
    watch = _store().watches[0]
    assert watch.describe() == "Whether pull request o/r#4 can merge"
    assert watch.url() == "https://github.com/o/r/pull/4"


def test_it_learns_first_then_says_each_change_once(quill_data_dir: Path) -> None:
    store = _store()
    api = FakeApi(_pull())
    assert check_round(api, store, now=lambda: 1.0) == []  # learns, says nothing
    assert store.watches[0].last_result == "started watching: it cannot merge yet"
    assert check_round(api, store, now=lambda: 2.0) == []  # no change
    assert store.watches[0].last_result == "no change, it cannot merge yet"
    api.pull = _pull(**CLEAN)
    assert check_round(api, store, now=lambda: 3.0) == [
        "Pull request o/r#4 can merge now, as of commit abc1234."
    ]
    assert check_round(api, store, now=lambda: 4.0) == []  # said once, not again
    api.pull = _pull(headRefOid="fff9999aaa", reviewDecision="REVIEW_REQUIRED")
    said = check_round(api, store, now=lambda: 5.0)
    assert said == [
        "Pull request o/r#4 cannot merge now, as of commit fff9999. It needs an approving review."
    ]
    assert check_round(api, store, now=lambda: 6.0) == []


def test_stopping_names_the_blocking_rule(quill_data_dir: Path) -> None:
    store = _store()
    rules = [
        {
            "type": "pull_request",
            "ruleset_id": 7,
            "parameters": {"required_approving_review_count": 2},
        }
    ]
    api = FakeApi(
        _pull(**CLEAN),
        {
            "/repos/o/r/rules/branches/main": rules,
            "/repos/o/r/rulesets": [{"id": 7, "name": "Protect main"}],
            "/repos/o/r/pulls/4/reviews": [{"user": {"login": "ann"}, "state": "APPROVED"}],
        },
    )
    check_round(api, store, now=lambda: 1.0)
    api.pull = _pull()
    assert check_round(api, store, now=lambda: 2.0) == [
        "Pull request o/r#4 cannot merge now, as of commit abc1234. "
        'The ruleset "Protect main" wants 2 approving reviews; it has 1.'
    ]


def test_rules_are_read_only_when_something_will_be_said(quill_data_dir: Path) -> None:
    store = _store()
    api = FakeApi(_pull())
    check_round(api, store, now=lambda: 1.0)
    check_round(api, store, now=lambda: 2.0)
    assert api.reads == ["GRAPHQL", "GRAPHQL"]


def test_while_github_works_it_out_nothing_is_learned_or_said(quill_data_dir: Path) -> None:
    store = _store()
    api = FakeApi(_pull(mergeable="UNKNOWN", mergeStateStatus="UNKNOWN"))
    assert check_round(api, store, now=lambda: 1.0) == []
    watch = store.watches[0]
    assert not watch.primed and watch.seen == ()
    assert watch.last_result == "GitHub is still working out whether it can merge"
    api.pull = _pull(**CLEAN)
    assert check_round(api, store, now=lambda: 2.0) == []  # the first real answer only learns


def test_merged_is_said_once_and_a_failure_keeps_the_last_answer(quill_data_dir: Path) -> None:
    store = _store()
    api = FakeApi(_pull())
    check_round(api, store, now=lambda: 1.0)
    api.pull = None  # type: ignore[assignment]
    assert check_round(api, store, now=lambda: 2.0) == []
    assert store.watches[0].last_result.startswith("Could not check:")
    assert store.watches[0].seen == ("blocked",)
    api.pull = _pull(state="MERGED")
    assert check_round(api, store, now=lambda: 3.0) == ["Pull request o/r#4 was merged."]
    assert check_round(api, store, now=lambda: 4.0) == []


def test_it_survives_a_save_and_load(quill_data_dir: Path) -> None:
    store = _store()
    check_round(FakeApi(_pull(**CLEAN)), store, now=lambda: 1.0)
    store.save()
    again = WatchStore.load("alice").watches[0]
    assert (again.kind, again.number, again.seen) == (READY, 4, ("mergeable",))
