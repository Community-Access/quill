"""Across Repositories: one kind of thing from several chosen repositories (GX16).

PRD 22.11's category-first browsing, ported from GHManage's Categories mode
(v1.2.0): choose repositories once, then read Issues and Pull Requests,
Releases, Workflow Runs, Commits, Tags, Milestones, Discussions or Security
Alerts from all of them in one list. The rules that make it trustworthy are
the point, so they live here, tested, with no ``wx``:

* every repository answers on its own: its rows, a note ("Discussions are
  off"), or why it failed ("not found, or no access") -- a repository never
  vanishes from the result without a sentence;
* each repository's share is bounded (``MAX_PER_REPO``), so one busy
  repository cannot crowd out the rest, and a full page says so;
* a fork's issues are its upstream's on GitHub; when the upstream is chosen
  too, the fork adds none and says why, so nothing is listed twice;
* Releases can be "latest only": the newest published, non-prerelease
  release, else the newest published one;
* rows keep their repository, and ordering is newest, oldest, by name or
  grouped by repository in the order chosen, with ``next_repository`` for the
  ] and [ keys.

The provider calls are the single-repository ones the Workbench already
makes, so there is no new network call. Strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "CATEGORIES",
    "FIRST_PAGE",
    "MAX_PER_REPO",
    "MORE_STEP",
    "SORT_ORDERS",
    "WORKERS",
    "AcrossResult",
    "RepoOutcome",
    "fetch_across",
    "latest_release",
    "more_limit",
    "next_repository",
    "order_rows",
    "why_failed",
]

#: (key, label) in the order the tree and Ctrl+1 to Ctrl+8 list them.
CATEGORIES: tuple[tuple[str, str], ...] = (
    ("issues", "Issues and Pull Requests"),
    ("releases", "Releases"),
    ("runs", "Workflow Runs"),
    ("commits", "Commits"),
    ("tags", "Tags"),
    ("milestones", "Milestones"),
    ("discussions", "Discussions"),
    ("alerts", "Security Alerts"),
)
#: GitHub's page limit: no repository is read past it in one list.
MAX_PER_REPO = 100
#: What each repository shows first, and what View More adds (PRD GX16).
FIRST_PAGE = 30
MORE_STEP = 30
WORKERS = 6

#: View > Sort By's choices, as the order :func:`order_rows` understands.
SORT_ORDERS: dict[str, str] = {
    "number_desc": "newest",
    "updated_desc": "newest",
    "comments_desc": "newest",
    "number_asc": "oldest",
    "updated_asc": "oldest",
    "title_asc": "name",
    "title_desc": "name_desc",
}

#: Words in a failure that mean the feature is off, not that reading failed.
_DISABLED: tuple[tuple[str, str], ...] = (
    ("discussion", "Discussions are off"),
    ("dependabot alerts are disabled", "Dependabot alerts are off"),
    ("code scanning is not enabled", "code scanning is off"),
    ("secret scanning is disabled", "secret scanning is off"),
    ("issues are disabled", "Issues are off"),
    ("issues has been disabled", "Issues are off"),
    ("actions is disabled", "Actions are off"),
)


@dataclass(frozen=True, slots=True)
class RepoOutcome:
    """What one repository answered."""

    repository: str
    count: int = 0
    note: str = ""
    error: str = ""
    #: The repository had more than its bounded share.
    more: bool = False
    #: How many it was asked for (its page, after any View More).
    limit: int = 0

    @property
    def state(self) -> str:
        """complete, partial, empty, skipped, disabled, no_access or error."""
        if self.error:
            if self.error.endswith((" are off", " is off")):
                return "disabled"
            if "no access" in self.error:
                return "no_access"
            return "error"
        if self.count == 0:
            return "skipped" if self.note.startswith("a fork of") else "empty"
        return "partial" if self.more else "complete"

    def sentence(self) -> str:
        """What this repository answered, in one line a listener can act on."""
        state = self.state
        if state == "disabled":
            return f"{self.repository}: {self.error}, so it has none to list"
        if state == "no_access":
            return f"{self.repository}: could not be read, {self.error}"
        if state == "error":
            return f"{self.repository}: could not be read: {self.error}"
        if state in ("empty", "skipped"):
            return f"{self.repository}: {self.note}"
        if state == "partial":
            more = "View More reads more" if self.limit < MAX_PER_REPO else "the rest is on GitHub"
            return f"{self.repository}: first {self.count} shown, it has more; {more}"
        return f"{self.repository}: {self.count} shown, all it has"


@dataclass(frozen=True, slots=True)
class AcrossResult:
    category: str
    #: ``(repository, row)`` pairs, in the order fetched.
    rows: tuple[tuple[str, Any], ...] = ()
    outcomes: tuple[RepoOutcome, ...] = ()

    @property
    def failed(self) -> tuple[RepoOutcome, ...]:
        return tuple(o for o in self.outcomes if o.error)

    @property
    def empty(self) -> tuple[RepoOutcome, ...]:
        return tuple(o for o in self.outcomes if not o.error and not o.count)

    def summary(self) -> str:
        """One sentence for the status bar: rows, repositories, and what did not answer."""
        answered = len(self.outcomes) - len(self.failed)
        parts = [f"{len(self.rows)} from {answered} of {len(self.outcomes)} repositories"]
        if self.failed:
            parts.append(f"{len(self.failed)} could not be read")
        cut = [o.repository for o in self.outcomes if o.more]
        if cut:
            parts.append(f"{len(cut)} had more than shown")
        none = [o for o in self.outcomes if o.state in ("empty", "skipped", "disabled")]
        if none:
            parts.append(f"{len(none)} had none")
        return "; ".join(parts) + "."


def why_failed(error: BaseException | str) -> str:
    """A failure as the sentence a listener needs, not the stack."""
    text = str(error)
    lowered = text.lower()
    for words, said in _DISABLED:
        if words in lowered and ("disabled" in lowered or "not enabled" in lowered):
            return said
    if "404" in lowered or "not found" in lowered:
        return "not found, or no access"
    if "403" in lowered or "forbidden" in lowered or "permission" in lowered:
        return "no access"
    if "timed out" in lowered or "timeout" in lowered:
        return "GitHub didn't answer in time"
    return text.splitlines()[0][:200] if text else "unknown error"


def latest_release(releases: Sequence[Any]) -> Any | None:
    """The newest published non-prerelease release, else the newest published one."""
    published = [r for r in releases if not getattr(r, "draft", False)]
    stable = [r for r in published if not getattr(r, "prerelease", False)]
    pick = stable or published
    if not pick:
        return None
    return max(pick, key=lambda r: str(getattr(r, "published_at", "") or ""))


Fetch = Callable[[str, int], list[Any]]


def more_limit(current: int) -> int:
    """A repository's page after one more View More: 30 more, up to GitHub's 100."""
    return min(MAX_PER_REPO, max(current, FIRST_PAGE) + MORE_STEP)


def _fetchers(provider: Any, token: str | None) -> Mapping[str, Fetch]:
    def discussions(repo: str, limit: int) -> list[Any]:
        from quill.core.github.discussions import list_discussions

        rows, _complete, _note = list_discussions(token, repo, limit=limit)
        return rows

    return {
        "issues": lambda repo, limit: provider.fetch_issues(repo, state="open", limit=limit),
        "releases": lambda repo, limit: provider.fetch_releases(repo, limit=limit),
        "runs": lambda repo, limit: provider.fetch_workflow_runs(repo, limit=limit),
        "commits": lambda repo, limit: provider.fetch_commits(repo, limit=limit),
        "tags": lambda repo, limit: provider.fetch_tags(repo, limit=limit),
        "milestones": lambda repo, limit: provider.fetch_milestones(repo, limit=limit),
        "discussions": discussions,
        "alerts": lambda repo, limit: provider.fetch_security_alerts(repo, limit=limit),
    }


@dataclass
class _One:
    repository: str
    rows: list[Any] = field(default_factory=list)
    outcome: RepoOutcome | None = None


def fetch_across(
    provider: Any,
    category: str,
    repositories: Sequence[str],
    *,
    token: str | None = None,
    per_repo: int = FIRST_PAGE,
    per_repo_limits: Mapping[str, int] | None = None,
    latest_only: bool = False,
    upstream_of: Callable[[str], str] | None = None,
    fetchers: Mapping[str, Fetch] | None = None,
) -> AcrossResult:
    """Read *category* from every repository; each answers for itself.

    *upstream_of* names a fork's upstream ("" when not a fork) so a fork whose
    upstream is also chosen adds no issues. *per_repo_limits* is View More's
    page for each repository that asked for more. *fetchers* replaces the
    provider calls (tests).
    """
    table = fetchers or _fetchers(provider, token)
    if category not in table:
        raise ValueError(f"Unknown category {category!r}.")
    fetch = table[category]
    limit = max(1, min(per_repo, MAX_PER_REPO))
    chosen = list(dict.fromkeys(r.strip() for r in repositories if r.strip()))
    chosen_lower = {r.lower() for r in chosen}

    limits = {k.lower(): v for k, v in (per_repo_limits or {}).items()}

    def one(repo: str) -> _One:
        page = max(1, min(limits.get(repo.lower(), limit), MAX_PER_REPO))
        if category == "issues" and upstream_of is not None:
            try:
                upstream = upstream_of(repo)
            except Exception:  # noqa: BLE001 - not knowing is "not a fork"
                upstream = ""
            if upstream and upstream.lower() in chosen_lower:
                note = f"a fork of {upstream}, which is chosen too; its issues are listed there"
                return _One(repo, outcome=RepoOutcome(repo, note=note))
        try:
            rows = list(fetch(repo, page + 1))
        except Exception as exc:  # noqa: BLE001 - one repository never sinks the rest
            return _One(repo, outcome=RepoOutcome(repo, error=why_failed(exc), limit=page))
        more = len(rows) > page
        rows = rows[:page]
        if category == "releases" and latest_only:
            newest = latest_release(rows)
            rows = [newest] if newest is not None else []
            more = False
        note = "" if rows else f"no {dict(CATEGORIES)[category].lower()}"
        outcome = RepoOutcome(repo, count=len(rows), note=note, more=more, limit=page)
        return _One(repo, rows, outcome)

    with ThreadPoolExecutor(max_workers=min(WORKERS, max(1, len(chosen)))) as pool:
        answers = list(pool.map(one, chosen))
    rows = tuple((a.repository, row) for a in answers for row in a.rows)
    outcomes = tuple(a.outcome for a in answers if a.outcome is not None)
    return AcrossResult(category, rows, outcomes)


def _when(row: Any) -> str:
    for name in ("updated_at", "published_at", "created_at", "date", "commit_date"):
        value = getattr(row, name, "")
        if value:
            return str(value)
    return ""


def _name(row: Any) -> str:
    for name in ("title", "name", "message", "label"):
        value = getattr(row, name, "")
        if value:
            return str(value).casefold()
    return ""


def order_rows(
    rows: Sequence[tuple[str, Any]], order: str, *, chosen: Sequence[str] = ()
) -> list[tuple[str, Any]]:
    """Rows sorted "newest", "oldest", "name", "name_desc" or "repository".

    "repository" groups by repository in the chosen order. Every sort is
    stable, so rows that tie keep the order they came in.
    """
    if order == "oldest":
        return sorted(rows, key=lambda pair: _when(pair[1]))
    if order == "name":
        return sorted(rows, key=lambda pair: (_name(pair[1]), pair[0].lower()))
    if order == "name_desc":
        return sorted(rows, key=lambda pair: (_name(pair[1]), pair[0].lower()), reverse=True)
    if order == "repository":
        rank = {repo.lower(): i for i, repo in enumerate(chosen)}
        return sorted(rows, key=lambda pair: rank.get(pair[0].lower(), len(rank)))
    return sorted(rows, key=lambda pair: _when(pair[1]), reverse=True)


def next_repository(rows: Sequence[tuple[str, Any]], index: int, step: int = 1) -> int:
    """The first row of the next (or, with step -1, previous) repository's run; *index* if none."""
    if not rows or not 0 <= index < len(rows):
        return index
    here = rows[index][0]
    i = index
    if step > 0:
        while i < len(rows) and rows[i][0] == here:
            i += 1
        return i if i < len(rows) else index
    while i >= 0 and rows[i][0] == here:
        i -= 1
    if i < 0:
        return index
    there = rows[i][0]
    while i > 0 and rows[i - 1][0] == there:
        i -= 1
    return i
