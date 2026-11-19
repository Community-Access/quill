"""Merge Selected...: each pull request checked on its own, merged one at a time (GX09)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from quill.core.github import batch_merge as bm
from quill.core.github.merge_readiness import Readiness
from quill.core.github.rest_transport import GitHubRestError, RestResponse


def _pull(number: int, **changes: Any) -> dict[str, Any]:
    pull: dict[str, Any] = {
        "state": "OPEN",
        "isDraft": False,
        "mergeable": "MERGEABLE",
        "mergeStateStatus": "CLEAN",
        "reviewDecision": "APPROVED",
        "isMergeQueueEnabled": False,
        "headRefOid": f"{number}aaaaaa111",
        "baseRefName": "main",
        "autoMergeRequest": None,
        "mergeQueueEntry": None,
        "commits": {"nodes": []},
    }
    pull.update(changes)
    return pull


class FakeApi:
    """Readiness answers by pull request number, in turn; merges recorded."""

    def __init__(self, answers: Mapping[int, list[dict[str, Any]]], **repos: Any) -> None:
        self.answers = {number: list(each) for number, each in answers.items()}
        self.repos = repos
        self.merged: list[tuple[str, Any]] = []
        self.refuse: dict[int, GitHubRestError] = {}

    def graphql(self, query: str, variables: Mapping[str, object]) -> dict[str, Any]:
        number = int(str(variables["i"]))
        queue = self.answers[number]
        pull = queue.pop(0) if len(queue) > 1 else queue[0]
        repo = dict(self.repos.get(str(variables["n"]), {}))
        return {"repository": {**repo, "pullRequest": pull}}

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        number = int(path.rsplit("/", 2)[-2])
        if number in self.refuse:
            raise self.refuse[number]
        self.merged.append((path, body))
        return RestResponse(200, {}, {"sha": f"merged{number}000", "merged": True})


def _targets(*numbers: int, repo: str = "o/r") -> list[bm.MergeTarget]:
    return [bm.MergeTarget(repo, n, f"Pull {n}") for n in numbers]


def _readings(api: FakeApi, targets: list[bm.MergeTarget]) -> list[tuple[Any, Any]]:
    from quill.core.github.merge_readiness import load_readiness

    return [(t, load_readiness(api, t.repository, t.number)) for t in targets]


def _no_enqueue(repo: str, number: int, head: str) -> str:
    raise AssertionError("nothing should be queued")


def test_each_is_planned_on_its_own_with_the_reasons() -> None:
    api = FakeApi({1: [_pull(1)], 2: [_pull(2, reviewDecision="REVIEW_REQUIRED")], 3: [_pull(3)]})
    plans = bm.plan(_readings(api, _targets(1, 2, 3)), "squash")
    assert [p.action for p in plans] == ["merge", "skip", "merge"]
    assert plans[1].reason == "It needs an approving review."
    text = bm.preview(plans)
    assert text.splitlines()[0].startswith("Of 3 pull requests: merge 2; 1 will not.")
    assert "#1: will merge into main by squash and merge, commit 1aaaaaa." in text
    assert "#2: will not merge. It needs an approving review." in text


def test_the_method_follows_what_each_repository_allows() -> None:
    api = FakeApi(
        {1: [_pull(1)], 2: [_pull(2)]},
        a={"squashMergeAllowed": True, "mergeCommitAllowed": True},
        b={"rebaseMergeAllowed": True},
    )
    targets = [bm.MergeTarget("o/a", 1), bm.MergeTarget("o/b", 2)]
    plans = bm.plan(_readings(api, targets), "merge")
    assert [p.method for p in plans] == ["merge", "rebase"]
    assert "o/b#2: will merge into main by rebase and merge" in bm.preview(plans)
    assert bm.choose_method("squash", ()) == ""
    assert bm.choose_method("squash", ("merge", "rebase")) == "merge"


def test_merges_one_at_a_time_with_the_previewed_commit() -> None:
    api = FakeApi({1: [_pull(1)], 2: [_pull(2)]})
    plans = bm.plan(_readings(api, _targets(1, 2)), "rebase")
    paused: list[float] = []
    results = bm.run(api, plans, enqueue=_no_enqueue, pace=1.0, sleep=paused.append)
    assert [r.status for r in results] == ["Merged", "Merged"]
    assert api.merged == [
        ("/repos/o/r/pulls/1/merge", {"merge_method": "rebase", "sha": "1aaaaaa111"}),
        ("/repos/o/r/pulls/2/merge", {"merge_method": "rebase", "sha": "2aaaaaa111"}),
    ]
    assert paused == [1.0]
    assert bm.summary(results) == "Merged 2 of 2 pull requests."


def test_one_that_conflicts_after_the_first_merge_is_left_alone() -> None:
    conflicted = _pull(2, mergeable="CONFLICTING", mergeStateStatus="DIRTY")
    api = FakeApi({1: [_pull(1)], 2: [_pull(2), conflicted]})
    plans = bm.plan(_readings(api, _targets(1, 2)), "squash")
    results = bm.run(api, plans, enqueue=_no_enqueue, pace=0)
    assert [r.status for r in results] == ["Merged", "Not merged"]
    assert results[1].detail.startswith("since the preview: It conflicts with main.")
    assert len(api.merged) == 1
    assert bm.summary(results) == "Merged 1 of 2 pull requests, 1 not merged."


def test_new_commits_since_the_preview_are_not_merged() -> None:
    api = FakeApi({1: [_pull(1), _pull(1, headRefOid="bbbbbbb222")]})
    plans = bm.plan(_readings(api, _targets(1)), "squash")
    results = bm.run(api, plans, enqueue=_no_enqueue, pace=0)
    assert results[0].status == "Not merged"
    assert "1aaaaaa is now bbbbbbb" in results[0].detail
    assert api.merged == []


def test_a_failure_stops_nothing_else() -> None:
    api = FakeApi({1: [_pull(1)], 2: [_pull(2)], 3: [_pull(3)]})
    api.refuse[2] = GitHubRestError("no", status=405, data={"message": "Base branch was modified"})
    plans = bm.plan(_readings(api, _targets(1, 2, 3)), "squash")
    results = bm.run(api, plans, enqueue=_no_enqueue, pace=0)
    assert [r.status for r in results] == ["Merged", "Failed", "Merged"]
    assert "Base branch was modified" in results[1].detail
    text = bm.results_text(results)
    assert text.splitlines()[-1] == "Merged 2 of 3 pull requests, 1 failed."
    assert "#2: Failed, GitHub will not merge #2: Base branch was modified." in text


def test_a_branch_with_a_merge_queue_is_queued_not_merged() -> None:
    queued = _pull(1, isMergeQueueEnabled=True, mergeStateStatus="BLOCKED")
    api = FakeApi({1: [queued]})
    plans = bm.plan(_readings(api, _targets(1)), "squash")
    assert plans[0].action == "queue"
    assert "#1: will join the merge queue for main, commit 1aaaaaa." in bm.preview(plans)
    asked: list[tuple[str, int, str]] = []

    def enqueue(repo: str, number: int, head: str) -> str:
        asked.append((repo, number, head))
        return "Pull request #1 is in the merge queue at position 2."

    results = bm.run(api, plans, enqueue=enqueue, pace=0)
    assert asked == [("o/r", 1, "1aaaaaa111")]
    assert results[0].status == "Queued" and api.merged == []
    assert bm.summary(results) == "Merged 0 of 1 pull request, 1 joined the merge queue."


def test_already_queued_and_unreadable_are_skipped_with_why() -> None:
    api = FakeApi({1: [_pull(1, mergeQueueEntry={"position": 3})]})
    readings: list[tuple[Any, Any]] = [
        *_readings(api, _targets(1)),
        (bm.MergeTarget("o/r", 9), RuntimeError("HTTP 502")),
    ]
    plans = bm.plan(readings, "squash")
    assert [p.action for p in plans] == ["skip", "skip"]
    assert plans[0].reason == "It is already in the merge queue, at position 3."
    assert plans[1].reason == "QUILL could not check it: HTTP 502"
    assert bm.preview(plans).startswith("Of 2 pull requests: none can merge; 2 will not.")
    results = bm.run(api, plans, enqueue=_no_enqueue, pace=0)
    assert [r.status for r in results] == ["Not merged", "Not merged"]


@pytest.mark.parametrize("state", ["MERGED", "CLOSED"])
def test_merged_or_closed_by_someone_else_meanwhile(state: str) -> None:
    api = FakeApi({1: [_pull(1), _pull(1, state=state)]})
    plans = bm.plan(_readings(api, _targets(1)), "squash")
    results = bm.run(api, plans, enqueue=_no_enqueue, pace=0)
    assert results[0].status == "Not merged" and api.merged == []


def test_readiness_reads_allowed_methods_and_the_queue() -> None:
    ready = Readiness(number=1, head="a", base="main", merge_state="BLOCKED", queue_required=True)
    assert ready.can_merge and ready.allowed_methods == ("squash", "merge", "rebase")
    assert ready.sentence == (
        "#1 can join the merge queue for main, as of commit a; main merges only through its queue."
    )
