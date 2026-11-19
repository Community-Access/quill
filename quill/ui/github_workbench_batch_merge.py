"""Merge Selected...: several pull requests at once, each checked on its own (GX09).

Select two or more open pull requests in a list (Shift or Ctrl with the
arrows), then Item > Merge Selected.... The Workbench:

1. asks which way to merge, once (each repository's own allowed methods win
   where they differ);
2. asks Why Can't I Merge? of each pull request, off the UI thread;
3. shows the preview -- a line per pull request: will merge, will join the
   merge queue (when its base branch requires one), or will not and why --
   and asks for the number that will go in, typed back;
4. merges them one at a time, each asked again just before it goes in, and
   says one sentence with the counts; the results list has a line each, Copy
   Results, and Retry Failed.

The rules are :mod:`quill.core.github.batch_merge`; this mixin only sequences
the dialogs. Nothing is said on opening a window (GATE-13).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from quill.core.github.items_provider import GitHubItem

__all__ = ["BATCH_MERGE_REASONS", "BATCH_MERGE_VERBS", "GitHubWorkbenchBatchMergeMixin"]

BATCH_MERGE_VERBS: dict[str, frozenset[str]] = {"merge_selected": frozenset({"item"})}

BATCH_MERGE_REASONS: dict[str, str] = {
    "merge_selected": (
        "Merge Selected... is for two or more open pull requests selected in the list, "
        "while you are signed in. Shift or Ctrl with the arrows selects more than one."
    ),
}

#: The chooser's words, in the order offered, and the REST method each is.
_METHODS = (("Squash and merge", "squash"), ("Merge commit", "merge"), ("Rebase", "rebase"))


class GitHubWorkbenchBatchMergeMixin:
    items: Any
    frame: Any
    signed_in: bool
    batch_pace: float
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _choose: Callable[[str, str, list[str]], int]
    #: From the Properties mixin: the preview, then the count typed back (18.4).
    confirm_tier: Callable[[Any, str, str], bool]
    #: From the Properties mixin: a line per item, Copy Results, Retry Failed.
    show_results: Callable[..., None]

    def github_api(self) -> Any:
        raise NotImplementedError

    def _selected_pulls(self) -> list[GitHubItem]:
        frame = self.frame
        if frame is None:
            return []
        rows = [frame.rows[i] for i in frame.selected_indices()]
        return [
            row
            for row in rows
            if isinstance(row, GitHubItem)
            and row.is_pr
            and not row.is_merged
            and row.state.casefold() == "open"
        ]

    def _fits_merge_selected(self, _row: object) -> bool:
        return self.signed_in and len(self._selected_pulls()) >= 2

    def _do_merge_selected(self, ref: Any, _row: object) -> None:
        from quill.core.github.batch_merge import MergeTarget
        from quill.core.github.sheet_catalog import target_for

        instance = str(getattr(ref, "instance", "") or "")
        targets = []
        for pull in self._selected_pulls():
            found = target_for(pull, instance)
            repo = found.ident.get("repo", "") if found is not None else instance
            targets.append(MergeTarget(repo or instance, pull.number, pull.title))
        self._merge_targets(targets)

    def _merge_targets(self, targets: Sequence[Any]) -> None:
        picked = self._choose(
            "Merge Selected",
            f"How should the {len(targets)} pull requests merge? Where a repository does not "
            "allow that way, QUILL uses one it does, and the preview says which.",
            [label for label, _method in _METHODS],
        )
        if picked < 0:
            return
        preferred, api = _METHODS[picked][1], self.github_api()

        def check() -> list[tuple[Any, Any]]:
            from quill.core.github.merge_readiness import load_readiness

            readings: list[tuple[Any, Any]] = []
            for target in targets:
                try:
                    readings.append((target, load_readiness(api, target.repository, target.number)))
                except Exception as exc:  # noqa: BLE001 - one unreadable never stops the rest
                    readings.append((target, exc))
            return readings

        self._background(
            f"check {len(targets)} pull requests can merge",
            check,
            lambda readings: self._preview_merges(readings, preferred),
        )

    def _preview_merges(self, readings: Sequence[Any], preferred: str) -> None:
        from quill.core.github.batch_merge import plan, preview
        from quill.core.github.permissions import WriteTier

        plans = plan(readings, preferred)
        going = [p for p in plans if p.action != "skip"]
        words = preview(plans)
        if not going:
            self._say(f"None of the {len(plans)} pull requests can merge now.")
            self.show_results("Merge Selected: Preview", words)
            return
        if not self.confirm_tier(WriteTier.DESTRUCTIVE, words, str(len(going))):
            return
        self._run_merges(plans)

    def _run_merges(self, plans: Sequence[Any]) -> None:
        from quill.core.github import batch_merge
        from quill.core.github.merge_automation import enqueue_pull_request

        api, items, pace = self.github_api(), self.items, getattr(self, "batch_pace", 1.0)

        def enqueue(repository: str, number: int, head: str) -> str:
            return enqueue_pull_request(items, repository, number, expected_head=head)

        def work() -> Any:
            return batch_merge.run(api, plans, enqueue=enqueue, pace=pace)

        def finished(results: Any) -> None:
            self._say(batch_merge.summary(results))
            failed = {r.name for r in results if r.status == batch_merge.FAILED}
            many = len({p.target.repository for p in plans}) > 1
            again = [p.target for p in plans if p.name(many) in failed]
            self.show_results(
                "Merge Selected: Results",
                batch_merge.results_text(results),
                (lambda: self._merge_targets(again)) if again else None,
            )
            self.frame.reload()

        going = sum(1 for p in plans if p.action != "skip")
        self._background(f"merge {going} pull requests", work, finished)
