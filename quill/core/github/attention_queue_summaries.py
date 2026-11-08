"""The attention queue's pull requests, each said in one sentence.

The queue's search rows say why a pull request is there ("Review requested",
"Also: Assigned, Mentioned") but not where it stands. This adds Wave 2's
one-sentence summary ("Approved, 2 checks failing, 1 open thread.") to each
pull request row, from **one** batched GraphQL request per refresh:
:func:`~quill.core.github.pr_summary.fetch_pull_summaries` takes up to twenty
pull requests in one aliased query, so the queue summarises its twenty newest
and says when there were more.

The rules are the summary's own: a sentence never calls a pull request ready
on data it does not have, and a pull request GitHub did not answer for reads
"summary unavailable" rather than borrowing a guess. The row's reason stays its
first detail line, so the queue's "why is this here" is unchanged.

No ``wx`` imports; strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import replace

from quill.core.github.explore_models import ExploreRow
from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.pr_summary import PullRef, PullSummary

#: One aliased request holds this many pull requests (``pr_summary._MAX_BATCH``).
SUMMARY_LIMIT = 20

Fetch = Callable[[Sequence[PullRef]], Sequence[PullSummary]]


def _with_summary(row: ExploreRow, sentence: str) -> ExploreRow:
    reason, _, rest = row.detail.partition("\n")
    detail = f"{reason}\nSummary: {sentence}" + (f"\n{rest}" if rest else "")
    return replace(row, label=f"{row.label}. {sentence}", detail=detail)


def summarize_queue_rows(
    rows: Sequence[ExploreRow], fetch: Fetch | None
) -> tuple[tuple[ExploreRow, ...], str]:
    """*rows* with a summary on each pull request, and a warning ("" when none).

    *fetch* is the provider's ``fetch_pull_summaries``; ``None`` (an anonymous or
    older provider) leaves the rows as they were. It is called once, or not at
    all when the queue has no pull requests.
    """
    if fetch is None:
        return tuple(rows), ""
    pulls = [
        index
        for index, row in enumerate(rows)
        if row.kind == "pr" and row.key.isdecimal() and row.repo.count("/") == 1
    ]
    if not pulls:
        return tuple(rows), ""
    chosen = pulls[:SUMMARY_LIMIT]
    refs = [PullRef(rows[index].repo, int(rows[index].key)) for index in chosen]
    warnings: list[str] = []
    try:
        summaries = list(fetch(refs))
    except GitHubItemsError as exc:
        message = str(exc.args[0]) if exc.args else str(exc)
        return tuple(rows), f"Pull request summaries unavailable: {message}"
    out = list(rows)
    unavailable = 0
    for index, summary in zip(chosen, summaries, strict=False):
        if summary.error:
            unavailable += 1
            out[index] = _with_summary(rows[index], "Summary unavailable")
        else:
            out[index] = _with_summary(rows[index], summary.sentence().rstrip("."))
    if unavailable:
        plural = "s" if unavailable != 1 else ""
        warnings.append(f"GitHub did not summarise {unavailable} pull request{plural}")
    if len(pulls) > SUMMARY_LIMIT:
        warnings.append(f"Summaries cover the newest {SUMMARY_LIMIT} of {len(pulls)} pull requests")
    return tuple(out), "; ".join(warnings)


__all__ = ["SUMMARY_LIMIT", "summarize_queue_rows"]
