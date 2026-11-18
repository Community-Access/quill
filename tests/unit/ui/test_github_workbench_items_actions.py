"""The item actions the GitHub Workbench now does itself, not through GitHub Items.

Each test runs a real Workbench frame over a fake provider, with background
work run inline, and replaces only the window or prompt the action opens --
where that module defines it, because the Workbench imports it at the call.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.github.items_provider import (  # noqa: E402
    GitHubBranch,
    GitHubItem,
    GitHubRelease,
    GitHubReleaseAsset,
    GitHubWorkflowRun,
)
from quill.ui.github_workbench_window import GitHubWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402

REPO = "owner/repo"
_P = "github.workbench."


class _Items:
    is_authenticated = True
    token = "test-token"

    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []

    def fetch_issues(self, _repo: str, **_kw: Any) -> list[GitHubItem]:
        return [GitHubItem(1, "Crash on start", "open", "https://github.com/o/r/issues/1", False)]

    def fetch_pulls(self, _repo: str, **_kw: Any) -> list[GitHubItem]:
        return [
            GitHubItem(
                2,
                "Fix the crash",
                "open",
                "https://github.com/o/r/pull/2",
                True,
                base_branch="main",
            )
        ]

    def fetch_workflow_runs(self, _repo: str, **_kw: Any) -> list[GitHubWorkflowRun]:
        return [
            GitHubWorkflowRun(
                id=9, name="CI", status="completed", conclusion="failure", run_number=41
            )
        ]

    def fetch_branches(self, _repo: str, **_kw: Any) -> list[GitHubBranch]:
        return [GitHubBranch("feature", "abc123", default_branch="main")]

    def fetch_releases(self, _repo: str, **_kw: Any) -> list[GitHubRelease]:
        asset = GitHubReleaseAsset("app.zip", 12, 2048, "https://example.invalid/app.zip")
        return [GitHubRelease("v1.0", "One", assets=(asset,))]

    def merge_pull_request(self, repo: str, number: int, **kw: Any) -> str:
        self.calls.append(("merge", repo, number, kw.get("merge_method")))
        return "deadbeefcafe"

    def cancel_workflow_run(self, repo: str, run_id: int) -> None:
        self.calls.append(("cancel", repo, run_id))

    def compare_branches(self, repo: str, base: str, head: str) -> Any:
        self.calls.append(("compare", repo, base, head))
        return SimpleNamespace(base=base, head=head, ahead_by=2, behind_by=0)

    def close(self) -> None:
        pass


def _inline(_name: str, work: Any, done: Any, failed: Any) -> None:
    try:
        result = work()
    except Exception as exc:  # noqa: BLE001
        failed(exc)
        return
    done(result)


@pytest.fixture
def bench(wx_session_app, quill_data_dir):
    said: list[str] = []
    items = _Items()
    provider = GitHubWorkbenchProvider(items, REPO, announce=said.append)
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    frame.items = items  # type: ignore[attr-defined]
    yield frame
    frame.frame.Destroy()


def _select(frame: WorkbenchFrame, key: str, index: int = 0) -> None:
    ref = NodeRef("repository", key, REPO)
    assert frame.select(ref)
    if frame.current != ref:  # no event loop: deliver the selection ourselves
        frame._show_node(ref, remember=True)
    frame.list.Select(index)


class _Window:
    """Stands in for a Workbench-opened window; remembers what it was given."""

    opened: list[tuple[tuple[Any, ...], dict[str, Any]]]
    answer: Any = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        type(self).opened.append((args, kwargs))

    def show(self) -> Any:
        return type(self).answer


def _window(monkeypatch, target: str, answer: Any = None) -> type[_Window]:
    fake = type("Fake", (_Window,), {"opened": [], "answer": answer})
    monkeypatch.setattr(target, fake)
    return fake


def _readiness(monkeypatch, bench, **changes: Any) -> None:
    from quill.core.github import merge_readiness as mr

    ready = mr.Readiness(number=2, head="abc1234def", base="main", merge_state="CLEAN")
    ready = mr.Readiness(**{**ready.__dict__, **changes})
    monkeypatch.setattr(mr, "load_readiness", lambda _api, repo, number: ready)

    def merge_at(_api: Any, repo: str, number: int, method: str, head: str) -> str:
        bench.items.calls.append(("merge", repo, number, method, head))
        return "deadbeefcafe"

    monkeypatch.setattr(mr, "merge_at", merge_at)


def test_merge_asks_for_the_number_then_merges_and_says_one_result(bench, monkeypatch) -> None:
    confirm = _window(monkeypatch, "quill.ui.github_repo_admin_dialogs.TypedConfirmDialog", True)
    monkeypatch.setattr(bench.provider, "_choose", lambda *_a: 0)
    _readiness(monkeypatch, bench)
    _select(bench, "pulls")
    assert bench.can_run(f"{_P}merge")
    bench.run(f"{_P}merge")
    assert confirm.opened[0][1]["expected"] == "2"
    assert "as of commit abc1234" in confirm.opened[0][1]["message"]
    assert confirm.opened[0][0][0] is bench.frame
    assert bench.items.calls == [("merge", REPO, 2, "squash", "abc1234def")]
    assert bench.said[-1] == "Merged #2 (deadbee)."


def test_merge_that_cannot_says_why_and_asks_nothing(bench, monkeypatch) -> None:
    confirm = _window(monkeypatch, "quill.ui.github_repo_admin_dialogs.TypedConfirmDialog", True)
    _readiness(monkeypatch, bench, draft=True)
    _select(bench, "pulls")
    bench.run(f"{_P}merge")
    assert confirm.opened == [] and bench.items.calls == []
    assert bench.said[-1].startswith("#2 cannot merge yet, as of commit abc1234. It is a draft.")


def test_merge_cancelled_at_the_typed_check_sends_nothing(bench, monkeypatch) -> None:
    _window(monkeypatch, "quill.ui.github_repo_admin_dialogs.TypedConfirmDialog", False)
    monkeypatch.setattr(bench.provider, "_choose", lambda *_a: 0)
    _readiness(monkeypatch, bench)
    _select(bench, "pulls")
    bench.run(f"{_P}merge")
    assert bench.items.calls == []
    assert bench.said == []


def test_merge_is_greyed_on_an_issue_with_a_reason(bench) -> None:
    _select(bench, "issues")
    assert not bench.can_run(f"{_P}merge")
    assert bench.reason(f"{_P}merge") == "Merge is for an open pull request that is not merged yet."


def test_jobs_opens_the_jobs_window_on_the_run(bench, monkeypatch) -> None:
    jobs = _window(monkeypatch, "quill.ui.github_workflow_jobs_dialog.WorkflowJobsDialog")
    _select(bench, "runs")
    bench.run(f"{_P}jobs")
    args, kwargs = jobs.opened[0]
    assert args[0] is bench.frame and args[1] is bench.items
    assert (kwargs["repo"], kwargs["run_id"]) == (REPO, 9)
    assert bench.said == []  # GATE-13: the window says itself


def test_cancel_run_asks_first_and_says_what_github_accepted(bench, monkeypatch) -> None:
    asked: list[str] = []
    monkeypatch.setattr(bench.provider, "_confirm", lambda _t, q: asked.append(q) or True)
    _select(bench, "runs")
    bench.run(f"{_P}cancel_run")
    assert asked == [f"Cancel run #41, CI in {REPO}?"]
    assert bench.items.calls == [("cancel", REPO, 9)]
    assert bench.said[-1] == "GitHub accepted the cancel request and is stopping run #41, CI."


def test_cancel_run_declined_sends_nothing(bench, monkeypatch) -> None:
    monkeypatch.setattr(bench.provider, "_confirm", lambda *_a: False)
    _select(bench, "runs")
    bench.run(f"{_P}cancel_run")
    assert bench.items.calls == []


def test_artifacts_opens_the_artifacts_window(bench, monkeypatch) -> None:
    artifacts = _window(monkeypatch, "quill.ui.github_artifacts_dialog.ArtifactsDialog")
    _select(bench, "runs")
    bench.run(f"{_P}artifacts")
    kwargs = artifacts.opened[0][1]
    assert (kwargs["repo"], kwargs["run_id"], kwargs["run_label"]) == (REPO, 9, "#41 - CI")


def test_delete_branch_needs_the_name_typed_and_deletes_with_the_token(bench, monkeypatch) -> None:
    confirm = _window(monkeypatch, "quill.ui.github_repo_admin_dialogs.TypedConfirmDialog", True)
    deleted: list[tuple[str, ...]] = []

    class _Admin:
        def __init__(self, token: str) -> None:
            deleted.append(("token", token))

        def delete_branch(self, repo: str, name: str) -> None:
            deleted.append((repo, name))

        def close(self) -> None:
            deleted.append(("closed",))

    monkeypatch.setattr("quill.core.github.repo_admin.GitHubRepoAdminProvider", _Admin)
    _select(bench, "branches")
    assert bench.provider.remove_command("branch") == f"{_P}delete_branch"
    bench.run(f"{_P}delete_branch")
    assert confirm.opened[0][1]["expected"] == "feature"
    assert deleted == [("token", "test-token"), (REPO, "feature"), ("closed",)]
    assert bench.said[-1] == "Deleted branch feature."


def test_compare_asks_for_the_base_and_opens_the_comparison(bench, monkeypatch) -> None:
    compare = _window(
        monkeypatch, "quill.ui.github_compare_branches_dialog.GitHubCompareBranchesDialog"
    )
    asked: list[str] = []
    monkeypatch.setattr(
        bench.provider, "_ask_text", lambda _t, _p, **kw: asked.append(kw["value"]) or "main"
    )
    _select(bench, "branches")
    bench.run(f"{_P}compare")
    assert asked == ["main"]
    assert bench.items.calls == [("compare", REPO, "main", "feature")]
    args = compare.opened[0][0]
    assert args[0] is bench.frame and args[2] == REPO and args[3].head == "feature"


def test_edit_release_reads_it_edits_it_and_says_githubs_sentence(bench, monkeypatch) -> None:
    record = SimpleNamespace(tag="v1.0", draft=False)
    edits: list[dict[str, Any]] = []

    class _ReleaseAdmin:
        def __init__(self, token: str) -> None:
            assert token == "test-token"

        def find_release(self, repo: str, tag: str) -> Any:
            assert (repo, tag) == (REPO, "v1.0")
            return record

        def edit_release(self, repo: str, release: Any, **values: Any) -> tuple[Any, str]:
            edits.append(values)
            return release, "Release v1.0 is updated."

    monkeypatch.setattr("quill.core.github.release_admin.GitHubReleaseAdmin", _ReleaseAdmin)
    values = SimpleNamespace(name="One point oh", body="Notes", draft=False, prerelease=False)
    editor = _window(monkeypatch, "quill.ui.github_release_edit_dialog.EditReleaseDialog", values)
    _select(bench, "releases")
    bench.run(f"{_P}edit_release")
    assert editor.opened[0][0][1] is record
    assert edits == [{"name": "One point oh", "body": "Notes", "draft": False, "prerelease": False}]
    assert bench.said[-1] == "Release v1.0 is updated."


def test_timeline_opens_on_the_selected_pull_request(bench, monkeypatch) -> None:
    timeline = _window(monkeypatch, "quill.ui.github_timeline_dialog.GitHubTimelineDialog")
    _select(bench, "pulls")
    bench.run(f"{_P}timeline")
    args, kwargs = timeline.opened[0]
    assert args[0] is bench.frame and args[2:] == (REPO, 2)
    assert kwargs["kind"] == "pull request"


def test_assets_list_the_release_files(bench, monkeypatch) -> None:
    shown = _window(monkeypatch, "quill.ui.github_workbench_list_dialog.WorkbenchListDialog")
    _select(bench, "releases")
    bench.run(f"{_P}assets")
    args, kwargs = shown.opened[0]
    assert args[1] == "Assets of v1.0"
    assert args[2] == ["app.zip, 12 downloads, 2.0 KB"]
    assert [label for label, _help, _act in kwargs["actions"]][-1] == "Dele&te..."


def test_rows_without_the_editors_hooks_are_greyed_and_say_why(bench) -> None:
    _select(bench, "issues")
    assert not bench.can_run(f"{_P}summarize")
    assert "AI connection" in bench.reason(f"{_P}summarize")
    assert not bench.can_run(f"{_P}start_worktree")


def test_start_worktree_uses_the_editors_hook(bench) -> None:
    started: list[tuple[Any, ...]] = []
    bench.provider.start_worktree = lambda *args: started.append(args)
    _select(bench, "issues")
    bench.run(f"{_P}start_worktree")
    assert started == [(bench.frame, REPO, 1, "Crash on start", False)]
