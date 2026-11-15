"""Across Repositories in the GitHub Workbench (PRD 22.11, GX16; GH-E).

The ``across`` node lists the Repository Set in use (Ctrl+N there edits it);
Repository Sets, under it, lists every named set
(:mod:`quill.ui.github_workbench_across_sets`). The category children list
one kind of thing -- Issues and Pull Requests, Releases, Workflow Runs,
Commits, Tags, Milestones, Discussions, Security Alerts -- from every
repository in the set, and the by-name children and the Fleet are
:mod:`quill.ui.github_workbench_across_names`.

The rules a category list keeps, so a listener can trust it:

- **Every row starts with its repository**, and Enter opens the exact item in
  its own repository's node. Back (Backspace) returns to the same row, the
  same filter, the same grouping and the same View More pages.
- **No repository vanishes.** One that had none, has the feature off, may not
  be read, stopped at its page, or failed has a row of its own saying so,
  and the Items cell counts them.
- **Each repository's share is bounded**: 30 first; View More from This
  Repository reads 30 more, up to GitHub's 100.
- **Sort By and Group By** apply within the category; Group By Repository
  keeps the set's order. ``]`` and ``[`` in the list move to the next and
  previous repository's first row (a list key, like Enter and Backspace:
  outside the list they type).
- **Issue rows carry their issue type and organization fields** once read
  (Read Issue Type and Fields, or a ``type:`` or ``field:`` filter), and an
  issue whose fields could not be read is counted apart from one that does
  not match.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.explore_models import ExploreRow
from quill.core.github.items_provider import GitHubItem
from quill.ui.github_workbench_across_names import (
    NAME_LOADERS,
    NAME_REASONS,
    NAME_VERBS,
    GitHubWorkbenchAcrossNamesMixin,
)
from quill.ui.github_workbench_across_sets import (
    SET_REASONS,
    SET_VERBS,
    GitHubWorkbenchAcrossSetsMixin,
    load_sets,
    resolve_set,
    sets_for,
)

__all__ = ["ACROSS_PREFIX", "ACROSS_REASONS", "ACROSS_VERBS", "GitHubWorkbenchAcrossMixin"]

ACROSS_PREFIX = "across:"
_ITEM = frozenset({"across_item", "across_status"})
ACROSS_VERBS: dict[str, frozenset[str]] = {
    **SET_VERBS,
    **NAME_VERBS,
    "across_open_source": frozenset({"across_item"}),
    "next_repository": _ITEM,
    "previous_repository": _ITEM,
    "across_view_more": _ITEM,
    "across_issue_fields": _ITEM,
    "across_all_releases": _ITEM,
}
ACROSS_REASONS: dict[str, str] = {
    **SET_REASONS,
    **NAME_REASONS,
    "across_view_more": "This repository already shows all it has, or GitHub's 100.",
    "across_issue_fields": "Only Issues and Pull Requests rows have an issue type and fields.",
    "across_all_releases": "Only the Releases list has a latest-only choice.",
}
#: Repository node keys each category's item lives under.
_HOME = {
    "releases": "releases",
    "runs": "runs",
    "commits": "commits",
    "tags": "tags",
    "milestones": "milestones",
    "discussions": "discussions",
    "alerts": "alerts",
}


def _ident(model: object) -> str:
    for name in ("number", "tag", "tag_name", "sha", "id", "name", "title"):
        value = getattr(model, name, None)
        if value not in (None, "", 0):
            return f"#{value}" if name == "number" else str(value)
    return ""


def _word(model: object) -> str:
    """What to type in the item's own list to find it again."""
    for name in ("tag", "tag_name", "name", "title", "sha"):
        value = getattr(model, name, None)
        if value:
            return str(value)[:40]
    return ""


def _item_row(repository: str, category: str, model: object, extras: Any, said: str) -> ExploreRow:
    from quill.core.github.across import CATEGORIES
    from quill.ui.github_items_view import model_detail, model_label, model_url

    if isinstance(model, ExploreRow):
        label, detail, url = model.label, model.detail, model.url
        title, updated = model.title or model.label, model.updated_at
    else:
        label, detail, url = model_label(model), model_detail(model), model_url(model)
        title = str(getattr(model, "title", "") or getattr(model, "name", "") or "")
        updated = str(getattr(model, "updated_at", "") or "")
    lines = [
        f"Repository: {repository}",
        f"Category: {dict(CATEGORIES)[category]}",
        f"Identifier: {_ident(model) or 'none'}",
        f"Address: {url or 'none'}",
        f"This repository: {said}",
    ]
    if extras is not None:
        lines += extras.detail_lines()
    elif category == "issues" and isinstance(model, GitHubItem) and not model.is_pr:
        lines.append("Issue type and fields: not read yet (Read Issue Type and Fields).")
    if extras is not None and extras.type_state == "set":
        label = f"{label}, type {extras.issue_type}"
    key = url or f"{repository}:{category}:{label}"
    return ExploreRow(
        f"{repository}: {label}",
        "\n".join([*lines, "", detail]),
        url,
        repository,
        "across_item",
        key,
        updated,
        title,
    )


def _status_row(category: str, outcome: Any) -> ExploreRow:
    return ExploreRow(
        outcome.sentence(),
        outcome.sentence() + ".\n\nThis row stands for the repository, so it is never "
        "left out of the list without a sentence.",
        f"https://github.com/{outcome.repository}",
        outcome.repository,
        "across_status",
        f"status:{category}:{outcome.repository}",
        "",
        outcome.repository,
    )


class GitHubWorkbenchAcrossMixin(GitHubWorkbenchAcrossSetsMixin, GitHubWorkbenchAcrossNamesMixin):
    """Loading the ``across:`` nodes, and what their rows do."""

    items: Any
    frame: Any
    local_note: str
    _say: Callable[[str], None]
    _ask_text: Callable[..., str]

    def _across(self) -> dict[str, Any]:
        """Per-window state: View More pages, sources, issue extras, the place to return to."""
        if getattr(self, "_across_state", None) is None:
            self._across_state: dict[str, Any] = {
                "more": {},
                "sources": {},
                "extras": {},
                "all_releases": False,
                "return": None,
                "keys_bound": False,
            }
        return self._across_state

    def across_scope(self) -> tuple[list[str], str]:
        return resolve_set(sets_for(self.items), self.github_api())

    def across_unavailable(self, loader: str) -> str:
        if loader in (f"{ACROSS_PREFIX}chosen", f"{ACROSS_PREFIX}sets"):
            return ""
        sets = sets_for(self.items)
        if not sets.repositories() and not sets.filter_for():
            return (
                "Choose the repositories first: select Across Repositories (Ctrl+0) "
                "and press Ctrl+N, or make a set under Repository Sets."
            )
        return ""

    # -- loading (off the UI thread) -------------------------------------------------

    def load_across(self, loader: str, query: Any = None) -> list[object]:
        if loader == f"{ACROSS_PREFIX}sets":
            self.local_note = "Enter uses a set; Ctrl+N makes one."
            return list(load_sets(self.items))
        if loader in NAME_LOADERS:
            return list(self.load_by_name(loader))
        if loader == f"{ACROSS_PREFIX}fleet":
            return list(self.load_fleet())
        sets = sets_for(self.items)
        chosen, note = self.across_scope()
        kind = loader.removeprefix(ACROSS_PREFIX)
        if kind == "chosen":
            self.local_note = (
                f"{len(chosen)} repositories in {sets.current_name}. Ctrl+N changes them."
                + (f" {note}" if note else "")
            )
            return [
                ExploreRow(
                    repo,
                    f"In the set {sets.current_name}.",
                    f"https://github.com/{repo}",
                    repo,
                    "repo",
                    repo,
                )
                for repo in chosen
            ]
        return self._load_category(kind, chosen, note, query)

    def _load_category(self, kind: str, chosen: list[str], note: str, query: Any) -> list[object]:
        from quill.core.github import across
        from quill.core.github.across_issue_fields import match

        state = self._across()
        limits = state["more"].setdefault(kind, {})
        result = across.fetch_across(
            self.items,
            kind,
            chosen,
            token=getattr(self.items, "token", None),
            per_repo_limits=limits,
            latest_only=kind == "releases" and not state["all_releases"],
        )
        conditions = [
            (c.attribute, c.value, c.operator.name.endswith("NOT"))
            for c in getattr(query, "conditions", ())
            if c.attribute in ("type", "field")
        ]
        extras: dict[tuple[str, int], Any] = state["extras"]
        if kind == "issues" and conditions:
            self._read_extras([(r, m) for r, m in result.rows if isinstance(m, GitHubItem)])
        sentences = {o.repository: o.sentence() for o in result.outcomes}
        rows: list[tuple[str, object]] = []
        unknown = 0
        for repo, model in result.rows:
            extra = extras.get((repo, getattr(model, "number", 0))) if kind == "issues" else None
            if conditions:
                verdict = match(extra, conditions)
                if verdict is None:
                    unknown += 1
                if not verdict:
                    continue
            rows.append((repo, model))
        group = self.view_choice("group") == "repository"  # type: ignore[attr-defined]
        order = (
            "repository"
            if group
            else across.SORT_ORDERS.get(
                self.view_choice("sort"),
                "newest",  # type: ignore[attr-defined]
            )
        )
        ordered = across.order_rows(rows, order, chosen=chosen)
        made: list[object] = []
        for repo, model in ordered:
            extra = extras.get((repo, getattr(model, "number", 0)))
            row = _item_row(repo, kind, model, extra, sentences.get(repo, ""))
            state["sources"][row.key] = (kind, repo, model)
            made.append(row)
        status = [_status_row(kind, o) for o in result.outcomes if o.count == 0]
        made = self._place_status(made, status, chosen) if group else made + status
        notes = [o.sentence() for o in result.outcomes if o.state not in ("complete",)]
        said = result.summary()
        if kind == "releases":
            said += " Latest release only." if not state["all_releases"] else " Every release."
        if unknown:
            said += f" {unknown} issues could not be checked: type or fields unreadable."
        self.local_note = (
            said + (f" {note}" if note else "") + (" " + "; ".join(notes) + "." if notes else "")
        )
        return made

    @staticmethod
    def _place_status(
        rows: list[object], status: list[ExploreRow], chosen: list[str]
    ) -> list[object]:
        """Grouped by repository: each status row where its repository falls in the set's order."""
        rank = {repo.lower(): i for i, repo in enumerate(chosen)}
        everything = [*rows, *status]
        return sorted(
            everything, key=lambda r: rank.get(str(getattr(r, "repo", "")).lower(), len(rank))
        )

    def _read_extras(self, pairs: list[tuple[str, Any]]) -> None:
        """Issue type and fields for the issues in *pairs*, per repository. Off the UI thread."""
        from quill.core.github.across_issue_fields import read_issue_extras

        extras: dict[tuple[str, int], Any] = self._across()["extras"]
        by_repo: dict[str, list[int]] = {}
        for repo, model in pairs:
            if not model.is_pr and (repo, model.number) not in extras:
                by_repo.setdefault(repo, []).append(model.number)
        api = self.github_api()
        for repo, numbers in by_repo.items():
            found = read_issue_extras(api, repo, numbers, organization=repo.split("/")[0])
            for number, value in found.items():
                extras[(repo, number)] = value

    # -- what fits which row ---------------------------------------------------------

    def _source(self, row: object) -> tuple[str, str, Any] | None:
        if not isinstance(row, ExploreRow):
            return None
        found = self._across()["sources"].get(row.key)
        return found if isinstance(found, tuple) else None

    def _fits_across_view_more(self, row: object) -> bool:
        from quill.core.github import across

        if not isinstance(row, ExploreRow) or self.frame is None or self.frame.current is None:
            return False
        kind = self.frame.current.key.removeprefix("across_")
        page = self._across()["more"].get(kind, {}).get(row.repo, across.FIRST_PAGE)
        return page < across.MAX_PER_REPO

    def _fits_across_issue_fields(self, row: object) -> bool:
        source = self._source(row)
        return source is not None and source[0] == "issues"

    def _fits_across_all_releases(self, row: object) -> bool:
        current = self.frame.current if self.frame is not None else None
        return current is not None and current.key == "across_releases"

    # -- the rows' commands ------------------------------------------------------------

    def _do_across_open_source(self, _ref: Any, row: object) -> None:
        """Enter: the exact item, in its own repository; Back returns to this row."""
        source = self._source(row)
        if source is None:
            self._say("Load the list again first: F5.")
            return
        kind, repo, model = source
        frame = self.frame
        assert isinstance(row, ExploreRow)
        self._across()["return"] = (frame.current, row.key, frame.filter.GetValue())
        if self.add_instance("repository", repo) is not None:  # type: ignore[attr-defined]
            frame.rebuild_tree()  # the item's repository gets its node, the selection stays
        if kind == "issues":
            self._open_classic(None, None, reference=row.url)  # type: ignore[attr-defined, union-attr]
            return
        self._go_filtered("repository", _HOME[kind], repo, _word(model))  # type: ignore[attr-defined]

    def _move_repository(self, step: int) -> None:
        from quill.core.github.across import next_repository

        frame = self.frame
        rows = [(str(getattr(r, "repo", "")), r) for r in frame.rows]
        chosen = frame.selected_indices()
        start = chosen[0] if chosen else 0
        target = next_repository(rows, start, step)
        if target == start:
            self._say("No more repositories." if step > 0 else "This is the first repository.")
            return
        frame.focus_row(target)  # one change, so the row is read once
        frame.list.SetFocus()

    def _do_next_repository(self, _ref: Any, _row: object) -> None:
        self._move_repository(1)

    def _do_previous_repository(self, _ref: Any, _row: object) -> None:
        self._move_repository(-1)

    def _do_across_view_more(self, _ref: Any, row: object) -> None:
        from quill.core.github import across

        assert isinstance(row, ExploreRow)
        kind = self.frame.current.key.removeprefix("across_")
        pages = self._across()["more"].setdefault(kind, {})
        pages[row.repo] = across.more_limit(pages.get(row.repo, across.FIRST_PAGE))
        self._say(f"Reading up to {pages[row.repo]} from {row.repo}.")
        self.frame.reload()

    def _do_across_issue_fields(self, _ref: Any, _row: object) -> None:
        pairs = [
            source[1:]
            for source in (self._source(r) for r in self.frame.rows)
            if source is not None and source[0] == "issues"
        ]
        self._background(  # type: ignore[attr-defined]
            "read issue types and fields",
            lambda: self._read_extras([p for p in pairs if isinstance(p[1], GitHubItem)]),
            lambda _done: self.frame.reload(),
        )

    def _do_across_all_releases(self, _ref: Any, _row: object) -> None:
        state = self._across()
        state["all_releases"] = not state["all_releases"]
        self._say("Every release." if state["all_releases"] else "Latest release only.")
        self.frame.reload()

    def _do_choose_repositories(self, _ref: Any, _row: object) -> None:
        """Ctrl+N on Across Repositories: the set in use, as a checklist."""
        sets = sets_for(self.items)
        name = sets.current_name
        if sets.filter_for(name):
            self._say(f"{name} is made by a filter; Repository Sets, Set Filter changes it.")
            return
        self.pick_repositories(name)

    # -- after a fill: ] and [, and Back to the same place ------------------------------

    def across_after_fill(self, frame: Any) -> None:
        state = self._across()
        if not state["keys_bound"]:
            state["keys_bound"] = True
            frame.list.Bind(frame._wx.EVT_CHAR, self._on_list_char)
        back = state["return"]
        if back is None or frame.current != back[0]:
            return
        state["return"] = None
        _ref, key, text = back
        if text and frame.filter.GetValue() != text:
            from quill.core.workbench.filters import parse

            frame.filter.ChangeValue(text)
            frame.query = parse(text)
            if frame.query.conditions:
                state["return"] = (back[0], key, "")  # land on the row after this reload
                frame.reload()
                return
            frame._fill_list()
        for index, row in enumerate(frame.rows):
            if getattr(row, "key", None) == key:
                frame.focus_row(index)
                break

    def _on_list_char(self, event: Any) -> None:
        frame = self.frame
        current = frame.current if frame is not None else None
        code = event.GetUnicodeKey() if hasattr(event, "GetUnicodeKey") else event.GetKeyCode()
        if (
            current is not None
            and current.key.startswith("across_")
            and code in (ord("]"), ord("["))
            and not event.HasAnyModifiers()
        ):
            self._move_repository(1 if code == ord("]") else -1)
            return
        event.Skip()
