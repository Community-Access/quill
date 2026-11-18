"""Why Can't I Merge?, auto-merge and the merge queue, on a pull request's row (GH-MR).

The review window has had Auto-Merge and Queue since the review work; these
are the same answers on the Workbench's own row, so a pull request can be
asked about, set to merge itself, or queued without opening its review.

* **Why Can't I Merge?** reads :func:`~quill.core.github.merge_readiness.load_readiness`
  and says it: that the pull request can merge, or each reason it cannot with
  what to do, always naming the commit the answer is for.
* **Auto-Merge...** turns it on, asking the method, or off when it is on.
* **Merge Queue...** adds the pull request to its branch's queue, or takes it
  out when it is in.

Merge itself (:mod:`~quill.ui.github_workbench_items`) asks the same question
first and merges only the commit it read.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.items_provider import GitHubItem

__all__ = ["MERGE_REASONS", "MERGE_VERBS", "GitHubWorkbenchMergeMixin"]

MERGE_VERBS: dict[str, frozenset[str]] = {
    "why_cant_merge": frozenset({"item"}),
    "auto_merge": frozenset({"item"}),
    "merge_queue": frozenset({"item"}),
}

MERGE_REASONS: dict[str, str] = {
    "why_cant_merge": "Why Can't I Merge? is for an open pull request.",
    "auto_merge": "Auto-merge is for an open pull request, while you are signed in.",
    "merge_queue": "The merge queue is for an open pull request, while you are signed in.",
}


class GitHubWorkbenchMergeMixin:
    items: Any
    frame: Any
    signed_in: bool
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _choose: Callable[[str, str, list[str]], int]
    _confirm: Callable[[str, str], bool]

    def github_api(self) -> Any:
        raise NotImplementedError

    @staticmethod
    def _open_pull(row: object) -> bool:
        return isinstance(row, GitHubItem) and row.is_pr and row.state.casefold() == "open"

    def _fits_why_cant_merge(self, row: object) -> bool:
        return self._open_pull(row)

    def _fits_auto_merge(self, row: object) -> bool:
        return self.signed_in and self._open_pull(row)

    _fits_merge_queue = _fits_auto_merge

    def _readiness_then(self, ref: Any, row: object, then: Callable[[Any], None]) -> None:
        from quill.core.github.merge_readiness import load_readiness

        assert isinstance(row, GitHubItem)
        api, repository, number = self.github_api(), ref.instance, row.number
        self._background(
            f"check #{number} can merge", lambda: load_readiness(api, repository, number), then
        )

    def _do_why_cant_merge(self, ref: Any, row: object) -> None:
        self._readiness_then(ref, row, lambda ready: self._say(ready.sentence))

    def _do_auto_merge(self, ref: Any, row: object) -> None:
        self._readiness_then(ref, row, lambda ready: self._auto_merge(ref.instance, ready))

    def _auto_merge(self, repository: str, ready: Any) -> None:
        from quill.core.github.merge_automation import (
            MERGE_METHODS,
            disable_auto_merge,
            enable_auto_merge,
        )

        number, items = ready.number, self.items
        if ready.auto_merge:
            how = ready.auto_merge.casefold()
            if not self._confirm(
                "Auto-Merge",
                f"Auto-merge is on for #{number}, to {how} it. Turn it off? "
                "It then waits for somebody to merge it.",
            ):
                return
            self._background(
                "turn off auto-merge",
                lambda: disable_auto_merge(items, repository, number),
                lambda said: (self._say(str(said)), self.frame.reload()),
            )
            return
        if ready.can_merge:
            self._say(f"#{number} can merge now, so auto-merge has nothing to wait for.")
            return
        labels = list(MERGE_METHODS)
        picked = self._choose(
            "Auto-Merge",
            f"#{number} merges itself when it can. It is waiting for: "
            f"{' '.join(ready.reasons)} How should it merge?",
            labels,
        )
        if picked < 0:
            return
        method = labels[picked]
        self._background(
            "turn on auto-merge",
            lambda: enable_auto_merge(items, repository, number, method),
            lambda said: (self._say(str(said)), self.frame.reload()),
        )

    def _do_merge_queue(self, ref: Any, row: object) -> None:
        self._readiness_then(ref, row, lambda ready: self._merge_queue(ref.instance, ready))

    def _merge_queue(self, repository: str, ready: Any) -> None:
        from quill.core.github.merge_automation import (
            dequeue_pull_request,
            enqueue_pull_request,
        )

        number, items = ready.number, self.items
        if ready.queue_position is not None:
            question = (
                f"#{number} is in the merge queue at position {ready.queue_position}. Take it out?"
            )
            work, name = (lambda: dequeue_pull_request(items, repository, number)), "dequeue"
        else:
            question = (
                f"Add #{number}, as of commit {ready.short_head}, to the merge queue for "
                f"{ready.base}? The queue merges it after the pull requests ahead of it, "
                "once its checks pass with theirs."
            )
            work, name = (lambda: enqueue_pull_request(items, repository, number)), "enqueue"
        if not self._confirm("Merge Queue", question):
            return
        self._background(
            f"{name} #{number}", work, lambda said: (self._say(str(said)), self.frame.reload())
        )
