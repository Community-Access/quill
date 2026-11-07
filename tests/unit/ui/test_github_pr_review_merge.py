"""Review's Auto-Merge and Queue actions and check re-request, without a live GitHub."""

from __future__ import annotations

from types import SimpleNamespace

from quill.core.github.pr_review import GitHubCheckRun
from quill.ui import github_pr_review_merge as module
from quill.ui.github_pr_review_merge import GitHubPullReviewMergeMixin


class _Dialog(GitHubPullReviewMergeMixin):
    def __init__(self, *, confirm: bool = True) -> None:
        self._repo = "o/r"
        self._number = 5
        self.confirmed: list[str] = []
        self.actions: list[str] = []
        self.spoken: list[str] = []
        self._confirm_answer = confirm
        self._client = SimpleNamespace(_provider=SimpleNamespace(rerequested=[]))
        self._client._provider.rerequest_check_run = lambda repo, check_id: (
            self._client._provider.rerequested.append((repo, check_id))
        )
        self._checks = (
            GitHubCheckRun("build", "completed", "failure", check_run_id=31),
            GitHubCheckRun("legacy", "completed", "success"),
        )
        self._selected = ("check", 0)

    def _confirm(self, message: str, _title: str) -> bool:
        self.confirmed.append(message)
        return self._confirm_answer

    def _announce(self, message: str) -> None:
        self.spoken.append(message)

    def _node_kind(self) -> tuple[str, int]:
        return self._selected

    def _run_action(self, action, success: str) -> None:
        self.actions.append(success + (action() or ""))


def test_disable_enqueue_dequeue_confirm_then_say_github_reply(monkeypatch) -> None:
    monkeypatch.setattr(module, "disable_auto_merge", lambda _p, repo, n: f"off {repo} {n}")
    monkeypatch.setattr(module, "enqueue_pull_request", lambda _p, repo, n: f"queued {n}")
    monkeypatch.setattr(module, "dequeue_pull_request", lambda _p, repo, n: f"out {n}")
    dialog = _Dialog()
    dialog._disable_auto_merge(None)
    dialog._enqueue(None)
    dialog._dequeue(None)
    assert dialog.actions == ["off o/r 5", "queued 5", "out 5"]
    assert len(dialog.confirmed) == 3


def test_declining_sends_nothing(monkeypatch) -> None:
    monkeypatch.setattr(module, "enqueue_pull_request", lambda *_a: "queued")
    dialog = _Dialog(confirm=False)
    dialog._enqueue(None)
    dialog._rerequest_selected_check(None)
    assert dialog.actions == []
    assert dialog._client._provider.rerequested == []


def test_rerequest_check_uses_its_check_run_id() -> None:
    dialog = _Dialog()
    dialog._rerequest_selected_check(None)
    assert dialog._client._provider.rerequested == [("o/r", 31)]
    assert dialog.actions == ["GitHub queued build to run again."]


def test_a_commit_status_cannot_be_rerequested() -> None:
    dialog = _Dialog()
    dialog._selected = ("check", 1)
    dialog._rerequest_selected_check(None)
    assert dialog.actions == []
    assert "commit status" in dialog.spoken[-1]
