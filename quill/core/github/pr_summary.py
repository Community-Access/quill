"""A pull request said in one sentence, from one batched GraphQL query.

"Approved, 2 checks failing, 1 open thread, 3 commits behind main." Everything
in that sentence comes from one request: ``reviewDecision``, the head commit's
``statusCheckRollup`` and its contexts, the unresolved review threads,
``autoMergeRequest``, ``mergeStateStatus`` and, when the head branch lives in
the same repository, how far behind the base it is. Several pull requests can
share the request through GraphQL aliases (``p0``, ``p1``...), which is what
the attention queue would use.

The sentence never says a pull request is ready on data it does not have:
readiness goes through the same conservative rules as the review header
(:attr:`~quill.core.github.review_models.GitHubPullReviewState.merge_readiness`),
so unknown or partial data reads as "merge readiness unknown".

No ``wx`` imports; strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.review_graphql import ReviewGraphQLError, _request
from quill.core.github.review_models import GitHubPullReviewState
from quill.core.github.review_thread_models import GitHubCheckRun

_MAX_BATCH = 20
_PULL_FIELDS = """
      number title state isDraft merged mergeable mergeStateStatus reviewDecision
      baseRefName headRefName headRefOid isCrossRepository
      autoMergeRequest { enabledAt mergeMethod }
      reviewThreads(first: 100) { totalCount pageInfo { hasNextPage } nodes { isResolved } }
      commits(last: 1) { nodes { commit { statusCheckRollup { state
        contexts(first: 100) { totalCount pageInfo { hasNextPage } nodes {
          __typename
          ... on CheckRun { name status conclusion }
          ... on StatusContext { context state }
        } }
      } } } }
"""
_FAILING = frozenset({
    "failure",
    "timed_out",
    "cancelled",
    "action_required",
    "startup_failure",
    "stale",
    "error",
})


@dataclass(frozen=True, slots=True)
class PullRef:
    """Which pull request to summarise; *head_ref* lets GitHub count commits behind."""

    full_name: str
    number: int
    head_ref: str = ""


@dataclass(frozen=True, slots=True)
class PullSummary:
    full_name: str
    number: int
    title: str = ""
    state: str = ""  # OPEN / CLOSED / MERGED
    draft: bool = False
    merged: bool = False
    mergeable: str = "UNKNOWN"  # MERGEABLE / CONFLICTING / UNKNOWN
    merge_state: str = "UNKNOWN"  # CLEAN / BEHIND / BLOCKED / DIRTY / UNSTABLE / ...
    review_decision: str = ""  # APPROVED / CHANGES_REQUESTED / REVIEW_REQUIRED / ""
    base_ref: str = ""
    head_ref: str = ""
    head_sha: str = ""
    auto_merge: bool = False
    checks: tuple[GitHubCheckRun, ...] = ()
    checks_complete: bool = True
    open_threads: int = 0
    threads_complete: bool = True
    behind_by: int | None = None
    warnings: tuple[str, ...] = ()
    error: str = ""

    def review_state(self) -> GitHubPullReviewState:
        """The same facts in the review header's model, for its readiness rules."""
        return GitHubPullReviewState(
            number=self.number,
            title=self.title,
            state="open" if self.state == "OPEN" else "closed" if self.state else "",
            draft=self.draft,
            merged=self.merged,
            mergeable=None if self.mergeable == "UNKNOWN" else self.mergeable == "MERGEABLE",
            mergeable_state=self.merge_state.casefold(),
            base_ref=self.base_ref,
            head_ref=self.head_ref,
            head_sha=self.head_sha,
            checks=self.checks,
            unresolved_thread_count=self.open_threads,
            checks_complete=self.checks_complete,
            threads_complete=self.threads_complete,
            data_warnings=self.warnings,
        )

    def _checks_phrase(self) -> str:
        if not self.checks:
            return "no checks" if self.checks_complete else "checks not read"
        failing = sum(
            1
            for check in self.checks
            if check.status == "completed" and check.conclusion in _FAILING
        )
        running = sum(1 for check in self.checks if check.status != "completed")
        phrases = []
        if failing:
            phrases.append(f"{failing} check{'s' if failing != 1 else ''} failing")
        if running:
            phrases.append(f"{running} check{'s' if running != 1 else ''} running")
        if not phrases:
            total = len(self.checks)
            phrases.append(f"all {total} checks passing" if total != 1 else "the 1 check passing")
        if not self.checks_complete:
            phrases[-1] += " (more checks not read)"
        return ", ".join(phrases)

    def _readiness_phrase(self) -> str:
        readiness = self.review_state().merge_readiness
        complete = self.checks_complete and self.threads_complete and not self.warnings
        if (
            self.merge_state == "CLEAN"
            and complete
            and readiness.startswith("GitHub reports no merge conflict")
        ):
            return "GitHub reports it can merge"
        if self.merge_state == "BLOCKED":
            return "blocked by branch rules"
        if readiness.startswith("Merge readiness unknown"):
            return "merge readiness unknown"
        return ""

    def sentence(self) -> str:
        """The one sentence the review window shows and says on open."""
        if self.error:
            return f"Summary unavailable: {self.error}"
        if self.merged:
            return "Merged."
        if self.state == "CLOSED":
            return "Closed without merging."
        parts: list[str] = ["Draft"] if self.draft else []
        parts.append(
            {
                "APPROVED": "Approved",
                "CHANGES_REQUESTED": "Changes requested",
                "REVIEW_REQUIRED": "Review required",
            }.get(self.review_decision, "No review decision")
        )
        parts.append(self._checks_phrase())
        threads = (
            f"{self.open_threads} open thread{'s' if self.open_threads != 1 else ''}"
            if self.open_threads
            else "no open threads"
        )
        parts.append(threads if self.threads_complete else f"at least {threads}")
        base = self.base_ref or "the base branch"
        if self.behind_by:
            plural = "s" if self.behind_by != 1 else ""
            parts.append(f"{self.behind_by} commit{plural} behind {base}")
        elif self.behind_by == 0:
            parts.append(f"up to date with {base}")
        elif self.merge_state == "BEHIND":
            parts.append(f"behind {base}")
        if self.mergeable == "CONFLICTING":
            parts.append("merge conflicts")
        if self.auto_merge:
            parts.append("auto-merge on")
        if readiness := self._readiness_phrase():
            parts.append(readiness)
        return ", ".join(parts) + "."


def _check(node: Mapping[str, Any]) -> GitHubCheckRun | None:
    kind = node.get("__typename")
    if kind == "CheckRun":
        status = str(node.get("status") or "").casefold()
        return GitHubCheckRun(
            name=str(node.get("name") or ""),
            status="completed" if status == "completed" else status or "queued",
            conclusion=str(node.get("conclusion") or "").casefold(),
        )
    if kind == "StatusContext":
        state = str(node.get("state") or "").casefold()
        pending = state in ("pending", "expected")
        return GitHubCheckRun(
            name=str(node.get("context") or ""),
            status="in_progress" if pending else "completed",
            conclusion="" if pending else state,
        )
    return None


def _get(value: Any, *keys: str) -> Any:
    for key in keys:
        value = value.get(key) if isinstance(value, Mapping) else None
    return value


def parse_pull_summary(ref: PullRef, pull: Any, *, compare_requested: bool = False) -> PullSummary:
    """One alias's ``pullRequest`` object as a :class:`PullSummary`."""
    if not isinstance(pull, Mapping):
        return PullSummary(ref.full_name, ref.number, error="GitHub returned no pull request.")
    threads = pull.get("reviewThreads")
    thread_nodes = _get(threads, "nodes")
    open_threads = sum(
        1 for node in thread_nodes or () if isinstance(node, Mapping) and not node.get("isResolved")
    )
    threads_complete = isinstance(thread_nodes, list) and not _get(
        threads, "pageInfo", "hasNextPage"
    )
    commit_nodes = _get(pull, "commits", "nodes")
    rollup = (
        _get(commit_nodes[0], "commit", "statusCheckRollup")
        if isinstance(commit_nodes, list) and commit_nodes
        else None
    )
    contexts = _get(rollup, "contexts")
    checks = tuple(
        check
        for node in _get(contexts, "nodes") or ()
        if isinstance(node, Mapping) and (check := _check(node)) is not None
    )
    checks_complete = not _get(contexts, "pageInfo", "hasNextPage")
    behind: int | None = None
    if compare_requested and pull.get("isCrossRepository") is False:
        # A fork's branch name means nothing in the base repository.
        value = _get(pull, "baseRef", "compare", "behindBy")
        if isinstance(value, int) and not isinstance(value, bool):
            behind = value
    review_decision = pull.get("reviewDecision")
    return PullSummary(
        full_name=ref.full_name,
        number=ref.number,
        title=str(pull.get("title") or ""),
        state=str(pull.get("state") or ""),
        draft=bool(pull.get("isDraft")),
        merged=bool(pull.get("merged")),
        mergeable=str(pull.get("mergeable") or "UNKNOWN"),
        merge_state=str(pull.get("mergeStateStatus") or "UNKNOWN"),
        review_decision=review_decision if isinstance(review_decision, str) else "",
        base_ref=str(pull.get("baseRefName") or ""),
        head_ref=str(pull.get("headRefName") or ""),
        head_sha=str(pull.get("headRefOid") or ""),
        auto_merge=isinstance(pull.get("autoMergeRequest"), Mapping),
        checks=checks,
        checks_complete=checks_complete,
        open_threads=open_threads,
        threads_complete=threads_complete,
        behind_by=behind,
    )


def build_summary_query(refs: Sequence[PullRef]) -> tuple[str, dict[str, object]]:
    """One GraphQL document with one alias per pull request."""
    declarations: list[str] = []
    selections: list[str] = []
    variables: dict[str, object] = {}
    for index, ref in enumerate(refs):
        owner, _, name = ref.full_name.partition("/")
        declarations.append(
            f"$o{index}:String!, $r{index}:String!, $n{index}:Int!, "
            f"$h{index}:String!, $c{index}:Boolean!"
        )
        selections.append(
            f"  p{index}: repository(owner:$o{index}, name:$r{index}) {{\n"
            f"    pullRequest(number:$n{index}) {{{_PULL_FIELDS}"
            f"      baseRef {{ compare(headRef:$h{index}) @include(if:$c{index}) "
            "{ aheadBy behindBy } }\n    }\n  }"
        )
        variables.update({
            f"o{index}": owner,
            f"r{index}": name,
            f"n{index}": ref.number,
            f"h{index}": ref.head_ref,
            f"c{index}": bool(ref.head_ref),
        })
    query = "query(" + ", ".join(declarations) + ") {\n" + "\n".join(selections) + "\n}"
    return query, variables


def fetch_pull_summaries(token: str, refs: Sequence[PullRef]) -> tuple[PullSummary, ...]:
    """Summaries in the order asked, batched up to twenty pull requests a request."""
    out: list[PullSummary] = []
    for start in range(0, len(refs), _MAX_BATCH):
        batch = list(refs[start : start + _MAX_BATCH])
        for ref in batch:
            parts = ref.full_name.split("/")
            if len(parts) != 2 or not all(parts) or ref.number <= 0:
                raise GitHubItemsError("Each pull request needs an owner/repo and a number.")
        query, variables = build_summary_query(batch)
        errors: list[str] = []
        try:
            data = _request(token, query, variables, errors_out=errors)
        except ReviewGraphQLError as exc:
            out.extend(PullSummary(ref.full_name, ref.number, error=str(exc)) for ref in batch)
            continue
        note = "; ".join(errors)
        for index, ref in enumerate(batch):
            pull = _get(data, f"p{index}", "pullRequest")
            if pull is None:
                out.append(
                    PullSummary(
                        ref.full_name, ref.number, error=note or "GitHub returned no pull request."
                    )
                )
                continue
            summary = parse_pull_summary(ref, pull, compare_requested=bool(ref.head_ref))
            out.append(summary)
    return tuple(out)


class _SummaryAccess(Protocol):
    _token: str | None


class GitHubPullSummaryMixin:
    """The one-sentence pull request summary for the review window."""

    def fetch_pull_summary(
        self: _SummaryAccess, full_name: str, number: int, *, head_ref: str = ""
    ) -> PullSummary:
        if not self._token:
            raise GitHubItemsError("Sign in to GitHub to hear the one-line summary.")
        return fetch_pull_summaries(self._token, [PullRef(full_name, number, head_ref)])[0]

    def fetch_pull_summaries(
        self: _SummaryAccess, refs: Sequence[PullRef]
    ) -> tuple[PullSummary, ...]:
        if not self._token:
            raise GitHubItemsError("Sign in to GitHub to read pull request summaries.")
        return fetch_pull_summaries(self._token, refs)


__all__ = [
    "GitHubPullSummaryMixin",
    "PullRef",
    "PullSummary",
    "build_summary_query",
    "fetch_pull_summaries",
    "parse_pull_summary",
]
