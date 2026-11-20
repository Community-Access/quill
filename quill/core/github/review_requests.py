"""Review requests made to you, and those made to a team you belong to (GH-R-143).

GitHub's search has two qualifiers for this. ``user-review-requested:LOGIN``
finds the pull requests that ask *you* by name; ``review-requested:LOGIN``
finds those and, as well, every pull request that asks a team you are on. So
the Workbench asks both: a row only the second search finds is a request made
to one of your teams, and it says so. The search cannot say *which* team (a
search result carries no reviewer list), so the row says "your team" and the
pull request's sheet names it under Team reviewers.

Both My Work's Review Requests and the Inbox read these two searches, so the
two lists can never disagree about what a team request is.
"""

from __future__ import annotations

from dataclasses import replace

from quill.core.github.explore_models import ExploreRow

__all__ = [
    "DIRECT_SOURCE",
    "REVIEW_SOURCES",
    "TEAM_MARK",
    "TEAM_SOURCE",
    "as_team_request",
    "is_direct_request",
    "review_request_searches",
]

DIRECT_SOURCE = "Review requested"
TEAM_SOURCE = "Team review requested"
REVIEW_SOURCES = (DIRECT_SOURCE, TEAM_SOURCE)
#: What a team request's row says after its kind, so it is heard on the row.
TEAM_MARK = "team review request"


def review_request_searches(login: str) -> tuple[tuple[str, str], tuple[str, str]]:
    """The two searches, the direct one first so a team row can be told apart."""
    return (
        (DIRECT_SOURCE, f"is:open is:pr user-review-requested:{login}"),
        (TEAM_SOURCE, f"is:open is:pr review-requested:{login}"),
    )


def is_direct_request(sources: str) -> bool:
    """Whether a row's first detail line (its sources) already says "asked you"."""
    parts = sources.replace("Also:", "").replace(";", ",").split(",")
    return DIRECT_SOURCE in (part.strip() for part in parts)


def as_team_request(row: ExploreRow) -> ExploreRow:
    """The row marked as asked of your team: "... (PR, team review request)"."""
    label = row.label
    if TEAM_MARK in label:
        return row
    label = label[:-1] + f", {TEAM_MARK})" if label.endswith(")") else f"{label} ({TEAM_MARK})"
    lines = row.detail.split("\n")
    if len(lines) > 1 and lines[1] == row.label:
        lines[1] = label
    lines.insert(1, "Asked of a team you belong to; the sheet's Team reviewers names it.")
    return replace(row, label=label, detail="\n".join(lines))
