"""How far each branch is ahead of and behind the default branch.

One GraphQL request answers up to 100 branches (``Ref.compare``), where REST
would need a compare call per branch. GHManage does the same; note the
direction, which is easy to get backwards: ``compare(headRef: D)`` on branch
X treats X as the base and the default branch D as the head, so its
``aheadBy`` is what D has that X lacks -- X's *behind* -- and ``behindBy`` is
X's *ahead*.

Best effort: a branch this does not answer for stays "not known", never 0,
because "0 ahead, 0 behind" is a claim that the branch is even with the
default, and an unanswered request must not make it.

No ``wx`` imports; strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from quill.core.github.github_graphql import as_dict, graphql_data, split_repo

__all__ = [
    "Divergence",
    "describe_divergence",
    "fetch_divergence",
    "parse_divergence_page",
    "with_divergence",
]

#: GitHub's own ceiling for one connection page.
_PAGE = 100
#: At most this many pages (500 branches); the rest stay "not known".
_MAX_PAGES = 5

_QUERY = """
query($owner: String!, $name: String!, $base: String!, $first: Int!, $after: String) {
  repository(owner: $owner, name: $name) {
    refs(refPrefix: "refs/heads/", first: $first, after: $after) {
      pageInfo { hasNextPage endCursor }
      nodes { name compare(headRef: $base) { aheadBy behindBy } }
    }
  }
}
"""


@dataclass(frozen=True, slots=True)
class Divergence:
    """Commits a branch has that the default lacks (*ahead*), and the reverse."""

    ahead: int
    behind: int


def parse_divergence_page(data: Mapping[str, Any]) -> tuple[dict[str, Divergence], str]:
    """One page of the query's ``data``: the answers, and the next cursor ("" at the end)."""
    refs = as_dict(as_dict(data.get("repository")).get("refs"))
    found: dict[str, Divergence] = {}
    for node in refs.get("nodes") or ():
        row = as_dict(node)
        name = str(row.get("name") or "")
        compare = as_dict(row.get("compare"))
        if not name or not compare:
            continue
        try:
            # The swap the module docstring explains: X is the base here.
            found[name] = Divergence(
                ahead=int(compare.get("behindBy") or 0), behind=int(compare.get("aheadBy") or 0)
            )
        except (TypeError, ValueError):
            continue
    page = as_dict(refs.get("pageInfo"))
    cursor = str(page.get("endCursor") or "") if page.get("hasNextPage") else ""
    return found, cursor


def fetch_divergence(
    token: str | None, full_name: str, default_branch: str
) -> dict[str, Divergence]:
    """Every branch's divergence from *default_branch* that GitHub answered for."""
    owner, name = split_repo(full_name)
    found: dict[str, Divergence] = {}
    after: str | None = None
    for _page in range(_MAX_PAGES):
        data = graphql_data(
            token,
            _QUERY,
            {"owner": owner, "name": name, "base": default_branch, "first": _PAGE, "after": after},
            action="read how far each branch is from the default",
        )
        page, cursor = parse_divergence_page(data)
        found.update(page)
        if not cursor:
            break
        after = cursor
    return found


def describe_divergence(
    ahead: int | None, behind: int | None, *, default_branch: str, is_default: bool = False
) -> str:
    """The cell and detail sentence: "3 ahead, 1 behind main", "even with main", or ""."""
    if is_default:
        return "the default branch"
    if ahead is None or behind is None:
        return ""
    if not ahead and not behind:
        return f"even with {default_branch}"
    parts = []
    if ahead:
        parts.append(f"{ahead} ahead")
    if behind:
        parts.append(f"{behind} behind")
    return f"{', '.join(parts)} {default_branch}"


def with_divergence(
    branches: list[Any], token: str | None, full_name: str, default_branch: str
) -> list[Any]:
    """*branches* (``GitHubBranch``) with ahead/behind filled where GitHub answered.

    Anonymous, or a failed request, returns them unchanged: "not known", the
    honest answer, rather than an error that would cost the whole list.
    """
    from dataclasses import replace

    if not branches or not token or not default_branch:
        return [replace(b, default_branch=default_branch) for b in branches]
    try:
        found = fetch_divergence(token, full_name, default_branch)
    except Exception:  # noqa: BLE001 - the list matters more than its counts
        found = {}
    out = []
    for branch in branches:
        known = found.get(branch.name)
        if known is None or branch.name == default_branch:
            out.append(replace(branch, default_branch=default_branch))
        else:
            out.append(
                replace(
                    branch, ahead=known.ahead, behind=known.behind, default_branch=default_branch
                )
            )
    return out
