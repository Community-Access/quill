"""Merge Selected..., Release Evidence..., Attestations... and an environment's Deployments..."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github import merge_automation as auto
from quill.core.github import merge_readiness as mr
from quill.core.github import release_evidence as ev
from quill.core.github.explore_models import ExploreRow
from quill.core.github.item_actions import GITHUB_ACTIONS
from quill.core.github.items_provider import GitHubItem, GitHubRelease, GitHubReleaseAsset
from quill.core.github.write_requirements import COMMAND_REQUIREMENTS
from quill.ui.github_workbench_batch_merge import GitHubWorkbenchBatchMergeMixin
from quill.ui.github_workbench_development import DEVELOPMENT_REASONS, DEVELOPMENT_VERBS
from quill.ui.github_workbench_evidence import GitHubWorkbenchEvidenceMixin
from quill.ui.github_workbench_items import GitHubWorkbenchItemsMixin


def _pull(number: int, state: str = "open", *, is_pr: bool = True) -> GitHubItem:
    return GitHubItem(
        number=number,
        title=f"Pull {number}",
        state=state,
        url=f"https://github.com/o/r/pull/{number}",
        is_pr=is_pr,
    )


ROWS = [_pull(1), _pull(2), _pull(3, "closed"), _pull(4, is_pr=False)]


class _Window(GitHubWorkbenchBatchMergeMixin, GitHubWorkbenchEvidenceMixin):
    signed_in = True
    batch_pace = 0.0

    def __init__(self, *, selected: list[int], choice: int = 0, confirm: bool = True) -> None:
        self.said: list[str] = []
        self.asked: list[str] = []
        self.shown: list[tuple[str, str, Any]] = []
        self.choice, self.confirm = choice, confirm
        self.items = object()
        self.frame = SimpleNamespace(
            rows=ROWS,
            selected_indices=lambda: selected,
            reload=lambda: self.said.append("(reloaded)"),
            current=SimpleNamespace(instance="o/r"),
        )

    def github_api(self) -> Any:
        return "API"

    def _say(self, text: str) -> None:
        self.said.append(text)

    def _choose(self, title: str, prompt: str, labels: list[str]) -> int:
        self.asked.append(prompt)
        return self.choice

    def confirm_tier(self, tier: Any, words: str, name: str) -> bool:
        self.asked.append(f"{int(tier)}|{name}|{words}")
        return self.confirm

    def show_results(self, title: str, text: str, retry: Any = None) -> None:
        self.shown.append((title, text, retry))

    def _show_text(self, title: str, text: str) -> None:
        self.shown.append((title, text, None))

    def _background(self, _name: str, work: Any, done: Any) -> None:
        done(work())


@pytest.fixture
def readiness(monkeypatch: pytest.MonkeyPatch) -> dict[int, list[mr.Readiness]]:
    """Each pull request's answers in turn: the preview's, then the re-check's."""
    answers: dict[int, list[mr.Readiness]] = {
        1: [mr.Readiness(number=1, head="1111111aaa", base="main", merge_state="CLEAN")],
        2: [mr.Readiness(number=2, head="2222222bbb", base="main", review="REVIEW_REQUIRED")],
    }

    def load(_api: Any, _repo: str, number: int, **_named: Any) -> mr.Readiness:
        queue = answers[number]
        return queue.pop(0) if len(queue) > 1 else queue[0]

    monkeypatch.setattr(mr, "load_readiness", load)
    return answers


@pytest.fixture
def merged(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Any, ...]]:
    calls: list[tuple[Any, ...]] = []

    def merge_at(_api: Any, repo: str, number: int, method: str, head: str) -> str:
        calls.append((repo, number, method, head))
        return f"m{number}aaaaaa"

    monkeypatch.setattr(mr, "merge_at", merge_at)
    monkeypatch.setattr(
        auto,
        "enqueue_pull_request",
        lambda _items, repo, number, expected_head="": (
            calls.append(("queue", repo, number, expected_head)),
            f"Pull request #{number} is in the merge queue.",
        )[1],
    )
    return calls


def test_the_rows_are_registered_with_their_needs() -> None:
    for verb in ("merge_selected", "release_evidence", "asset_attestations"):
        assert verb in DEVELOPMENT_VERBS and verb in DEVELOPMENT_REASONS
    assert "environment_deployments" in DEVELOPMENT_VERBS
    assert COMMAND_REQUIREMENTS["github.workbench.merge_selected"][0] == "repo:write"
    ids = {
        kind: [row.command_id for row in GITHUB_ACTIONS.rows_for(kind)]
        for kind in ("pull_request", "release", "release_asset", "environment")
    }
    assert "github.workbench.merge_selected" in ids["pull_request"]
    assert "github.workbench.release_evidence" in ids["release"]
    assert "github.workbench.asset_attestations" in ids["release_asset"]
    assert "github.workbench.environment_deployments" in ids["environment"]


def test_merge_selected_needs_two_open_pull_requests() -> None:
    assert _Window(selected=[0, 1])._fits_merge_selected(None)
    assert not _Window(selected=[0, 2, 3])._fits_merge_selected(None)
    window = _Window(selected=[0, 1])
    window.signed_in = False
    assert not window._fits_merge_selected(None)


def test_preview_then_typed_count_then_one_sentence(readiness: Any, merged: Any) -> None:
    window = _Window(selected=[0, 1], choice=0)
    window._do_merge_selected(SimpleNamespace(instance="o/r"), ROWS[0])
    tier, count, words = window.asked[1].split("|", 2)
    assert int(tier) == 3 and count == "1"
    assert words.startswith("Of 2 pull requests: merge 1; 1 will not.")
    assert "#2: will not merge. It needs an approving review." in words
    assert merged == [("o/r", 1, "squash", "1111111aaa")]
    assert window.said == ["Merged 1 of 2 pull requests, 1 not merged.", "(reloaded)"]
    title, text, retry = window.shown[0]
    assert title == "Merge Selected: Results" and retry is None
    assert text.splitlines()[0] == "#1: Merged, by squash and merge, as m1aaaaa"


def test_cancel_at_the_preview_merges_nothing(readiness: Any, merged: Any) -> None:
    window = _Window(selected=[0, 1], confirm=False)
    window._do_merge_selected(SimpleNamespace(instance="o/r"), ROWS[0])
    assert merged == [] and window.said == []


def test_none_can_merge_says_so_and_shows_why(readiness: Any, merged: Any) -> None:
    readiness[1] = [mr.Readiness(number=1, head="1111111aaa", base="main", draft=True)]
    window = _Window(selected=[0, 1])
    window._do_merge_selected(SimpleNamespace(instance="o/r"), ROWS[0])
    assert window.said == ["None of the 2 pull requests can merge now."]
    assert window.shown[0][0] == "Merge Selected: Preview" and merged == []


def test_a_failure_offers_retry_of_the_failed_one_only(
    readiness: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    readiness[2] = [mr.Readiness(number=2, head="2222222bbb", base="main", merge_state="CLEAN")]

    def merge_at(_api: Any, _repo: str, number: int, _method: str, _head: str) -> str:
        if number == 2:
            raise mr.MergeReadinessError("GitHub will not merge #2: no.")
        return "m1aaaaaa"

    monkeypatch.setattr(mr, "merge_at", merge_at)
    window = _Window(selected=[0, 1])
    window._do_merge_selected(SimpleNamespace(instance="o/r"), ROWS[0])
    assert window.said[0] == "Merged 1 of 2 pull requests, 1 failed."
    _title, text, retry = window.shown[0]
    assert "#2: Failed, GitHub will not merge #2: no." in text
    assert retry is not None
    window.confirm = False
    retry()
    assert "How should the 1 pull requests merge?" in window.asked[-2]


def test_a_queue_required_branch_is_queued_with_the_previewed_head(
    readiness: Any, merged: Any
) -> None:
    for number in (1, 2):
        readiness[number] = [
            mr.Readiness(
                number=number,
                head=f"{number}" * 7,
                base="main",
                merge_state="BLOCKED",
                queue_required=True,
            )
        ]
    window = _Window(selected=[0, 1])
    window._do_merge_selected(SimpleNamespace(instance="o/r"), ROWS[0])
    assert merged == [("queue", "o/r", 1, "1111111"), ("queue", "o/r", 2, "2222222")]
    assert window.said[0] == "Merged 0 of 2 pull requests, 2 joined the merge queue."


def test_single_merge_offers_only_allowed_methods_and_refuses_a_queue_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Items(GitHubWorkbenchItemsMixin):
        signed_in = True

        def __init__(self) -> None:
            self.said: list[str] = []
            self.offered: list[list[str]] = []

        def _say(self, text: str) -> None:
            self.said.append(text)

        def _choose(self, _title: str, _prompt: str, labels: list[str]) -> int:
            self.offered.append(labels)
            return -1

    window = _Items()
    allowed = mr.Readiness(
        number=1, head="a", base="main", merge_state="CLEAN", methods=("rebase",)
    )
    window._merge_checked("o/r", ROWS[0], allowed)
    assert window.offered == [["Rebase"]]
    queued = mr.Readiness(number=1, head="a", base="main", merge_state="CLEAN", queue_required=True)
    window._merge_checked("o/r", ROWS[0], queued)
    assert window.said[-1].endswith("Add to or Remove from Merge Queue... queues it.")


def test_release_evidence_says_one_sentence_and_shows_the_lines(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    found = ev.ReleaseEvidence("o/r", "v1", immutable=True, sha="abc")
    asked: list[tuple[Any, ...]] = []
    monkeypatch.setattr(
        ev, "load_release_evidence", lambda api, repo, tag: (asked.append((repo, tag)), found)[1]
    )
    window = _Window(selected=[])
    release = GitHubRelease(tag="v1", name="One", url="https://github.com/o/r/releases/tag/v1")
    assert window._fits_release_evidence(release)
    window._do_release_evidence(SimpleNamespace(instance=""), release)
    assert asked == [("o/r", "v1")]
    assert window.said == [found.sentence]
    assert window.shown[0][0] == "Release Evidence: v1"
    assert "Immutable: its tag and files cannot change." in window.shown[0][1]


def test_attestations_on_a_file_say_the_count(monkeypatch: pytest.MonkeyPatch) -> None:
    found = ev.AssetEvidence("app.zip", "sha256:" + "a" * 64, 2, ("build provenance",))
    monkeypatch.setattr(ev, "attestations_for_asset", lambda api, repo, tag, name: found)
    asset = GitHubReleaseAsset(
        name="app.zip",
        download_count=0,
        size_bytes=1,
        browser_download_url="https://github.com/o/r/releases/download/v1/app.zip",
    )
    window = _Window(selected=[])
    assert window._fits_asset_attestations(asset)
    window._do_asset_attestations(SimpleNamespace(instance="o/r"), asset)
    assert window.said == ["app.zip (digest aaaaaaaaaaaa): 2 attestations: build provenance."]
    assert ev.VERIFY_NOTE in window.shown[0][1]


def test_an_environments_deployments(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [ev.DeploymentEvidence(1, "prod", "success", "2026-11-01 10:00", "abcdef1", "main")]
    monkeypatch.setattr(ev, "environment_deployments", lambda api, repo, name: rows)
    env = ExploreRow("prod: no protection rules.", "", "u", "o/r", "environment", "prod")
    window = _Window(selected=[])
    assert window._fits_environment_deployments(env)
    window._do_environment_deployments(None, env)
    assert window.said == ["1 deployments to prod; the newest is success."]
    assert window.shown[0][1] == "prod: success, 2026-11-01 10:00 (main, commit abcdef1)."
    monkeypatch.setattr(ev, "environment_deployments", lambda api, repo, name: [])
    window._do_environment_deployments(None, env)
    assert window.said[-1] == "Nothing has deployed to prod yet."
