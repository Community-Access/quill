"""Review refresh: a failed diff is said aloud, and a stale refresh is dropped."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github.items_errors import GitHubItemsError
from quill.ui import github_pr_review_dialog as module
from quill.ui.github_pr_review_dialog import GitHubPullReviewDialog


class _Label:
    def __init__(self) -> None:
        self.text = ""

    def SetLabel(self, text: str) -> None:  # noqa: N802 - wx's name
        self.text = text


class _Stub:
    _refresh = GitHubPullReviewDialog._refresh
    _refresh_landed = GitHubPullReviewDialog._refresh_landed
    _refresh_failed = GitHubPullReviewDialog._refresh_failed

    def __init__(self, diff_error: str = "") -> None:
        self._repo, self._number = "o/r", 5
        self._loading = False
        self._refresh_generation = 0
        self._status = _Label()
        self.dialog = object()
        self.spoken: list[str] = []
        self.rendered: list[Any] = []
        self.pending: list[tuple[Any, tuple[Any, ...]]] = []
        self._wx = SimpleNamespace(CallAfter=lambda fn, *a: self.pending.append((fn, a)))

        def diff(_repo: str, _number: int) -> object:
            if diff_error:
                raise GitHubItemsError(diff_error)
            return "diff"

        self._client = SimpleNamespace(
            fetch_review_threads=lambda *_a: SimpleNamespace(items=()),
            fetch_review_state=lambda *_a, **_k: "state",
            _provider=SimpleNamespace(fetch_pull_diff=diff),
        )

    def _announce(self, message: str) -> None:
        self.spoken.append(message)

    def _refresh_ready(self, state: object, threads: object, diff: object) -> None:
        self._loading = False
        self.rendered.append(diff)
        self._status.SetLabel("Review loaded.")

    def run_pending(self) -> None:
        while self.pending:
            fn, args = self.pending.pop(0)
            fn(*args)


class _SyncThread:
    def __init__(self, target=None, daemon=None, **_kw) -> None:
        self._target = target

    def start(self) -> None:
        self._target()


@pytest.fixture(autouse=True)
def _sync(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module.threading, "Thread", _SyncThread)
    monkeypatch.setattr(module, "dialog_alive", lambda _dialog: True)


def test_a_failed_diff_is_shown_and_spoken() -> None:
    stub = _Stub(diff_error="GitHub had a server error (HTTP 502).")
    stub._refresh()
    stub.run_pending()
    assert stub.rendered == [None]
    assert stub.spoken == ["Could not load the diff: GitHub had a server error (HTTP 502)."]
    assert stub._status.text.startswith("Review loaded. Could not load the diff:")


def test_a_loaded_diff_says_nothing_extra() -> None:
    stub = _Stub()
    stub._refresh()
    stub.run_pending()
    assert stub.rendered == ["diff"]
    assert stub.spoken == []


def test_a_slow_refresh_cannot_overwrite_a_newer_one() -> None:
    stub = _Stub()
    stub._refresh()  # its reply is queued, not yet delivered
    stub._loading = False  # e.g. a policy re-render cleared the flag meanwhile
    stub._refresh()
    assert stub._refresh_generation == 2
    stub.run_pending()
    assert stub.rendered == ["diff"]  # only the second refresh rendered


def test_a_stale_failure_is_dropped_too() -> None:
    stub = _Stub()
    stub._refresh_generation = 3
    stub._refresh_failed("old error", 2)
    assert stub.spoken == []
    stub._refresh_failed("new error", 3)
    assert stub.spoken == ["Could not load pull request review: new error"]
