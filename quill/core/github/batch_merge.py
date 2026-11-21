"""Merge Selected...: several pull requests, each checked on its own (GX09, complete.md 1.3).

Each selected pull request is asked :func:`~quill.core.github.merge_readiness.load_readiness`
-- the same question Why Can't I Merge? asks -- and :func:`plan` decides for
each, independently of the others, one of three things:

- **merge** it, with the method the person preferred when its repository
  allows that method, or the first one it does allow (squash, merge, rebase);
- **queue** it, when its base branch merges only through a merge queue;
- **skip** it, with the reasons Why Can't I Merge? gives.

:func:`preview` is the list said before anything changes. :func:`run` then
goes one at a time and **asks again just before each one**, because merging
one pull request can make the next conflict or put it behind its base. A pull
request whose head moved since the preview is not merged: the person agreed to
merge the commit they were shown (GX09's "changing HEAD invalidates prior
readiness"), and :func:`~quill.core.github.merge_readiness.merge_at` sends that
commit's SHA so GitHub refuses a push that lands in between. A failure stops
nothing else. :func:`summary` is the one sentence said at the end.

Takes the Workbench's :class:`~quill.core.github.workbench_api.GitHubApi`.
wx-free and strict-typed.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from quill.core.github import merge_readiness as _readiness
from quill.core.github.batch import DEFAULT_PACE_SECONDS, BatchResult
from quill.core.github.merge_readiness import Readiness
from quill.core.github.workbench_api import GitHubApi

__all__ = [
    "FAILED",
    "MERGED",
    "METHOD_WORDS",
    "NOT_MERGED",
    "QUEUED",
    "MergeTarget",
    "PlannedMerge",
    "choose_method",
    "plan",
    "preview",
    "results_text",
    "run",
    "summary",
]

#: The REST merge methods, in the order offered, and how each is said.
METHOD_WORDS: dict[str, str] = {
    "squash": "squash and merge",
    "merge": "merge commit",
    "rebase": "rebase and merge",
}

MERGED, QUEUED, NOT_MERGED, FAILED = "Merged", "Queued", "Not merged", "Failed"


@dataclass(frozen=True)
class MergeTarget:
    repository: str
    number: int
    title: str = ""


@dataclass(frozen=True)
class PlannedMerge:
    target: MergeTarget
    action: str
    """``merge``, ``queue`` or ``skip``."""
    method: str = ""
    head: str = ""
    base: str = ""
    reason: str = ""

    def name(self, many_repositories: bool) -> str:
        where = self.target.repository if many_repositories else ""
        return f"{where}#{self.target.number}"

    def line(self, many_repositories: bool = False) -> str:
        name = self.name(many_repositories)
        at = f", commit {self.head[:7]}" if self.head else ""
        if self.action == "merge":
            return f"{name}: will merge into {self.base} by {METHOD_WORDS[self.method]}{at}."
        if self.action == "queue":
            return f"{name}: will join the merge queue for {self.base}{at}."
        return f"{name}: will not merge. {self.reason}"


def _said(exc: BaseException) -> str:
    """The raiser's own words, without the support code in brackets."""
    return str(exc.args[0]) if exc.args and isinstance(exc.args[0], str) else str(exc)


def choose_method(preferred: str, allowed: Sequence[str]) -> str:
    """*preferred* when the repository allows it, otherwise the first it does allow."""
    if preferred in allowed:
        return preferred
    return next((method for method in METHOD_WORDS if method in allowed), "")


def _planned(target: MergeTarget, ready: Readiness, preferred: str) -> PlannedMerge:
    if ready.queue_position is not None:
        why = f"It is already in the merge queue, at position {ready.queue_position}."
        return PlannedMerge(target, "skip", head=ready.head, base=ready.base, reason=why)
    if not ready.can_merge:
        why = " ".join(ready.reasons)
        return PlannedMerge(target, "skip", head=ready.head, base=ready.base, reason=why)
    if ready.queue_required:
        return PlannedMerge(target, "queue", head=ready.head, base=ready.base)
    method = choose_method(preferred, ready.allowed_methods)
    if not method:
        why = "Its repository allows no merge method GitHub's API can use."
        return PlannedMerge(target, "skip", head=ready.head, base=ready.base, reason=why)
    return PlannedMerge(target, "merge", method, ready.head, ready.base)


def plan(
    readings: Sequence[tuple[MergeTarget, Readiness | Exception]], preferred: str
) -> list[PlannedMerge]:
    """What will happen to each pull request, decided for each on its own."""
    found: list[PlannedMerge] = []
    for target, ready in readings:
        if isinstance(ready, Exception):
            why = f"QUILL could not check it: {_said(ready)}"
            found.append(PlannedMerge(target, "skip", reason=why))
        else:
            found.append(_planned(target, ready, preferred))
    return found


def _many(plans: Sequence[PlannedMerge]) -> bool:
    return len({p.target.repository for p in plans}) > 1


def _count(number: int, noun: str) -> str:
    return f"{number} {noun}" + ("" if number == 1 else "s")


def preview(plans: Sequence[PlannedMerge]) -> str:
    """The list before anything changes: a line per pull request, then what will happen."""
    many = _many(plans)
    lines = [p.line(many) for p in plans]
    going = [p for p in plans if p.action != "skip"]
    merging = sum(1 for p in going if p.action == "merge")
    queueing = len(going) - merging
    parts = [f"merge {merging}"] if merging else []
    parts += [f"add {queueing} to the merge queue"] if queueing else []
    staying = len(plans) - len(going)
    head = (
        f"Of {_count(len(plans), 'pull request')}: "
        + (" and ".join(parts) or "none can merge")
        + (f"; {staying} will not." if staying else ".")
    )
    if going:
        head += (
            " One at a time, each checked again just before it goes in; one that has "
            "changed or can no longer merge is left alone, and a failure stops nothing else."
        )
    return "\n".join([head, "", *lines])


def run(
    api: GitHubApi,
    plans: Sequence[PlannedMerge],
    *,
    enqueue: Callable[[str, int, str], str],
    pace: float = DEFAULT_PACE_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
    progress: Callable[[int, int], None] | None = None,
) -> list[BatchResult]:
    """Merge or queue each planned pull request in turn; a result for every one.

    *enqueue* is ``(repository, number, expected head) -> sentence``: the merge
    queue's own mutation, which the caller binds to its signed-in provider.
    """
    many = _many(plans)
    results: list[BatchResult] = []
    sent = 0
    for index, item in enumerate(plans, start=1):
        name = item.name(many)
        if item.action == "skip":
            results.append(BatchResult(name, NOT_MERGED, item.reason))
            continue
        if progress is not None:
            progress(index, len(plans))
        if sent and pace > 0:
            sleep(pace)
        sent += 1
        results.append(_one(api, item, name, enqueue))
    return results


def _one(
    api: GitHubApi, item: PlannedMerge, name: str, enqueue: Callable[[str, int, str], str]
) -> BatchResult:
    repo, number = item.target.repository, item.target.number
    try:
        now = _readiness.load_readiness(api, repo, number, named=True)
    except Exception as exc:  # noqa: BLE001 - one failure never stops the rest
        return BatchResult(name, FAILED, f"QUILL could not check it again: {_said(exc)}")
    if item.head and now.head and now.head != item.head:
        return BatchResult(
            name,
            NOT_MERGED,
            f"it has new commits since the preview ({item.head[:7]} is now "
            f"{now.head[:7]}), so it was left alone",
        )
    if now.queue_position is not None:
        return BatchResult(name, QUEUED, f"already in the queue at position {now.queue_position}")
    if not now.can_merge:
        return BatchResult(name, NOT_MERGED, "since the preview: " + " ".join(now.reasons))
    try:
        if item.action == "queue" or now.queue_required:
            return BatchResult(name, QUEUED, enqueue(repo, number, item.head or now.head))
        sha = _readiness.merge_at(api, repo, number, item.method, item.head or now.head)
    except Exception as exc:  # noqa: BLE001 - one failure never stops the rest
        return BatchResult(name, FAILED, _said(exc))
    return BatchResult(name, MERGED, f"by {METHOD_WORDS[item.method]}, as {sha[:7]}")


def summary(results: Sequence[BatchResult]) -> str:
    """The one sentence said at the end, with the counts."""
    merged = sum(1 for r in results if r.status == MERGED)
    queued = sum(1 for r in results if r.status == QUEUED)
    left = sum(1 for r in results if r.status == NOT_MERGED)
    failed = sum(1 for r in results if r.status == FAILED)
    parts = [f"Merged {merged} of {_count(len(results), 'pull request')}"]
    if queued:
        parts.append(f"{queued} joined the merge queue")
    if left:
        parts.append(f"{left} not merged")
    if failed:
        parts.append(f"{failed} failed")
    return ", ".join(parts) + "."


def results_text(results: Sequence[BatchResult]) -> str:
    """Copy Results: one line per pull request, then the summary."""
    return "\n".join([*(r.row() for r in results), summary(results)])
