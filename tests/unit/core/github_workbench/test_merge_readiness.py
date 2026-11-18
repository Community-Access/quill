"""Why a pull request can or cannot merge, for one exact commit (GH-MR)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from quill.core.github import merge_readiness as mr
from quill.core.github.rest_transport import GitHubRestError, RestResponse


def _pull(**changes: Any) -> dict[str, Any]:
    pull: dict[str, Any] = {
        "state": "OPEN",
        "isDraft": False,
        "mergeable": "MERGEABLE",
        "mergeStateStatus": "CLEAN",
        "reviewDecision": "APPROVED",
        "headRefOid": "abc1234def",
        "baseRefName": "main",
        "viewerCanMergeAsAdmin": False,
        "autoMergeRequest": None,
        "mergeQueueEntry": None,
        "commits": {"nodes": [{"commit": {"statusCheckRollup": {"contexts": {"nodes": []}}}}]},
    }
    pull.update(changes)
    return pull


def _checks(*nodes: dict[str, Any]) -> dict[str, Any]:
    return {"nodes": [{"commit": {"statusCheckRollup": {"contexts": {"nodes": list(nodes)}}}}]}


def _run(name: str, conclusion: str | None, *, required: bool = True, done: bool = True) -> Any:
    return {
        "__typename": "CheckRun",
        "name": name,
        "status": "COMPLETED" if done else "IN_PROGRESS",
        "conclusion": conclusion,
        "isRequired": required,
    }


class FakeApi:
    def __init__(self, pull: Any = None, *, error: Exception | None = None) -> None:
        self.pull, self.error = pull, error
        self.sent: list[tuple[str, str, Any]] = []

    def graphql(self, query: str, variables: Mapping[str, object]) -> dict[str, Any]:
        self.sent.append(("GRAPHQL", "", dict(variables)))
        return {"repository": {"pullRequest": self.pull}}

    def rest(self, method: str, path: str, *, body: Any = None, query: Any = None) -> Any:
        self.sent.append((method, path, body))
        if self.error is not None:
            raise self.error
        return RestResponse(200, {}, {"sha": "fedcba9876", "merged": True})


def _ready(**changes: Any) -> mr.Readiness:
    return mr.load_readiness(FakeApi(_pull(**changes)), "o/r", 4)


def test_a_clean_pull_can_merge_and_names_its_commit() -> None:
    ready = _ready()
    assert ready.can_merge and ready.head == "abc1234def"
    assert ready.sentence == "#4 can merge into main, as of commit abc1234."


def test_every_reason_is_said_with_what_to_do() -> None:
    ready = _ready(
        isDraft=True,
        mergeable="CONFLICTING",
        mergeStateStatus="DIRTY",
        reviewDecision="CHANGES_REQUESTED",
        commits=_checks(
            _run("test", "FAILURE"),
            _run("lint", None, done=False),
            _run("docs", "SUCCESS"),
            _run("flaky", "FAILURE", required=False),
        ),
    )
    assert not ready.can_merge
    said = ready.sentence
    assert said.startswith("#4 cannot merge yet, as of commit abc1234.")
    for part in (
        "It is a draft.",
        "It conflicts with main. Resolve Conflicts in a Worktree...",
        "A reviewer requested changes.",
        "Required check test failed. Re-run or fix it.",
        "Required check lint has not finished.",
    ):
        assert part in said
    assert "docs" not in said and "flaky" not in said


def test_behind_blocked_unknown_and_review_required() -> None:
    assert "behind main" in _ready(mergeStateStatus="BEHIND").sentence
    assert "Check Merge Policy" in _ready(mergeStateStatus="BLOCKED").sentence
    assert "still working out" in _ready(mergeStateStatus="UNKNOWN").sentence
    needs = _ready(reviewDecision="REVIEW_REQUIRED", mergeStateStatus="BLOCKED")
    assert needs.reasons == ("It needs an approving review.",)


def test_several_checks_are_one_sentence() -> None:
    ready = _ready(commits=_checks(_run("a", "FAILURE"), _run("b", "TIMED_OUT")))
    assert "Required checks a and b failed." in ready.sentence


def test_statuses_count_like_check_runs() -> None:
    status = {
        "__typename": "StatusContext",
        "context": "ci/x",
        "state": "PENDING",
        "isRequired": True,
    }
    assert "Required check ci/x has not finished." in _ready(commits=_checks(status)).sentence


def test_a_failing_optional_check_does_not_block() -> None:
    ready = _ready(
        mergeStateStatus="UNSTABLE", commits=_checks(_run("x", "FAILURE", required=False))
    )
    assert ready.can_merge
    assert ready.sentence.endswith("abc1234. Check x failed, but it is not required.")


def test_merged_closed_auto_merge_and_queue() -> None:
    assert _ready(state="MERGED").reasons == ("#4 is already merged.",)
    assert "Reopen" in _ready(state="CLOSED").sentence
    auto = _ready(mergeStateStatus="BLOCKED", autoMergeRequest={"mergeMethod": "SQUASH"})
    assert "Auto-merge is on, to squash it when it can." in auto.sentence
    queued = _ready(mergeQueueEntry={"position": 2, "state": "QUEUED"})
    assert queued.queue_position == 2 and "at position 2" in queued.sentence


def test_a_missing_pull_is_refused() -> None:
    with pytest.raises(mr.MergeReadinessError, match="no pull request #4"):
        mr.load_readiness(FakeApi(None), "o/r", 4)
    assert mr.MergeReadinessError.code == "QUILL-GITHUB-MERGE-READINESS"


def test_merge_at_sends_the_commit_it_was_checked_at() -> None:
    api = FakeApi()
    assert mr.merge_at(api, "o/r", 4, "squash", "abc1234def") == "fedcba9876"
    assert api.sent == [
        ("PUT", "/repos/o/r/pulls/4/merge", {"merge_method": "squash", "sha": "abc1234def"})
    ]


def test_a_push_in_between_merges_nothing_and_says_so() -> None:
    api = FakeApi(error=GitHubRestError("conflict", status=409))
    with pytest.raises(mr.MergeReadinessError, match="pushed to #4 after commit abc1234"):
        mr.merge_at(api, "o/r", 4, "merge", "abc1234def")
    refused = FakeApi(
        error=GitHubRestError("no", status=405, data={"message": "Base branch was modified"})
    )
    with pytest.raises(mr.MergeReadinessError, match="Base branch was modified"):
        mr.merge_at(refused, "o/r", 4, "merge", "abc")
    with pytest.raises(mr.MergeReadinessError, match="Unknown merge method"):
        mr.merge_at(FakeApi(), "o/r", 4, "octopus", "abc")
