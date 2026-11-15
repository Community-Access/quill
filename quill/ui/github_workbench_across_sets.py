"""Named Repository Sets in the GitHub Workbench (PRD 22.11; GH-E).

Across Repositories > Repository Sets lists the account's sets, one row each
("QuillVille family: made by the filter org:Community-Access
topic:quillville, 12 repositories last time, in use"). Enter makes a set the
one every Across Repositories list and by-name sheet reads; the row's menu
makes a new set, edits a hand-made set's repositories, turns a set into a
filter-made one, renames it or deletes it (asking first). The sets are
:class:`quill.core.github.repository_sets.RepositorySets`, one file per
account, saved atomically; they never leave the computer, and a filter is
run against GitHub's repository search only when the set is used.

Nothing here speaks on its own (GATE-13): what is said is the outcome of a
change the person asked for.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.explore_models import ExploreRow

__all__ = [
    "SET_REASONS",
    "SET_VERBS",
    "GitHubWorkbenchAcrossSetsMixin",
    "load_sets",
    "resolve_set",
]

#: Workbench verbs for set rows, and the row kinds each needs.
SET_VERBS: dict[str, frozenset[str]] = {
    "across_use_set": frozenset({"repository_set"}),
    "across_edit_set": frozenset({"repository_set"}),
    "across_set_filter": frozenset({"repository_set"}),
    "across_rename_set": frozenset({"repository_set"}),
    "across_delete_set": frozenset({"repository_set"}),
    "across_new_set": frozenset({"view"}),
}
SET_REASONS: dict[str, str] = {
    "across_use_set": "Select a set under Across Repositories, Repository Sets.",
    "across_edit_set": "Select a set under Across Repositories, Repository Sets.",
    "across_set_filter": "Select a set under Across Repositories, Repository Sets.",
    "across_rename_set": "Select a set under Across Repositories, Repository Sets.",
    "across_delete_set": "Select a set under Across Repositories, Repository Sets.",
}


def sets_for(items: Any) -> Any:
    """The signed-in account's Repository Sets (read from disk each time)."""
    from quill.core.github.navigation_state import account_key_for_token
    from quill.core.github.repository_sets import RepositorySets

    return RepositorySets.load(account_key_for_token(getattr(items, "token", None)))


def resolve_set(sets: Any, api: Any, name: str = "") -> tuple[list[str], str]:
    """The set's repositories now, and a note when a filter could not be run.

    A hand-made set is its list. A filter-made set runs GitHub's repository
    search (one request, the first 100) and keeps the answer, so the set's row
    can say how many it found; if the search fails, the last answer is used
    and the note says so. Runs off the UI thread.
    """
    name = name or sets.current_name
    search = sets.filter_for(name)
    if not search:
        return sets.repositories(name), ""
    from quill.core.github.across import why_failed
    from quill.core.github.repository_sets import EVERY

    if search == EVERY:
        return _every(sets, api, name)
    try:
        answer = api.rest("GET", "/search/repositories", query={"q": search, "per_page": "100"})
    except Exception as exc:  # noqa: BLE001 - the last answer stands in, and says so
        last = sets.repositories(name)
        return last, (
            f"The filter {search} could not be run ({why_failed(exc)}); "
            f"using the {len(last)} repositories it found last time."
        )
    data = answer.data if isinstance(answer.data, dict) else {}
    found = [
        str(item.get("full_name"))
        for item in data.get("items") or []
        if isinstance(item, dict) and item.get("full_name")
    ]
    sets.resolved(name, found)
    sets.save()
    note = ""
    if data.get("incomplete_results") or int(data.get("total_count") or 0) > len(found):
        note = (
            f"The filter {search} matches {data.get('total_count')} repositories; "
            f"the first {len(found)} are used."
        )
    return sets.repositories(name), note


def _every(sets: Any, api: Any, name: str) -> tuple[list[str], str]:
    """Every repository the account may read: GitHub's own list, bounded, truncation said."""
    from quill.core.github.across import why_failed
    from quill.core.github.repository_sets import MAX_REPOSITORIES

    found: list[str] = []
    more = False
    page = 1
    try:
        while len(found) < MAX_REPOSITORIES:
            answer = api.rest(
                "GET",
                "/user/repos",
                query={
                    "affiliation": "owner,collaborator,organization_member",
                    "sort": "pushed",
                    "per_page": "100",
                    "page": str(page),
                },
            )
            rows = answer.data if isinstance(answer.data, list) else []
            found += [
                str(r.get("full_name")) for r in rows if isinstance(r, dict) and r.get("full_name")
            ]
            if len(rows) < 100:
                break
            page += 1
        else:
            more = True
    except Exception as exc:  # noqa: BLE001 - the last answer stands in, and says so
        last = sets.repositories(name)
        return last, (
            f"Your repositories could not be listed ({why_failed(exc)}); using the "
            f"{len(last)} found last time."
        )
    sets.resolved(name, found[:MAX_REPOSITORIES])
    sets.save()
    note = (
        f"Every repository you can reach: the {MAX_REPOSITORIES} most recently pushed are "
        "used; GitHub may list more."
        if more
        else ""
    )
    return sets.repositories(name), note


def load_sets(items: Any) -> list[ExploreRow]:
    """Across Repositories > Repository Sets: one row per set."""
    sets = sets_for(items)
    names = sets.names() or [sets.current_name]
    return [
        ExploreRow(
            sets.describe(name),
            "\n".join([
                sets.describe(name) + ".",
                f"Filter: {sets.filter_for(name)}" if sets.filter_for(name) else "Chosen by hand.",
                "Repositories: " + (", ".join(sets.repositories(name)) or "none yet"),
            ]),
            "",
            "",
            "repository_set",
            f"set:{name}",
            "",
            name,
        )
        for name in names
    ]


class GitHubWorkbenchAcrossSetsMixin:
    """New, edit, filter, rename, delete and use a Repository Set."""

    items: Any
    frame: Any
    _say: Callable[[str], None]
    _ask_text: Callable[..., str]
    _confirm: Callable[[str, str], bool]
    _choose: Callable[[str, str, list[str]], int]

    @staticmethod
    def _set_name(row: object) -> str:
        return row.title if isinstance(row, ExploreRow) and row.kind == "repository_set" else ""

    def _do_across_use_set(self, _ref: Any, row: object) -> None:
        sets = sets_for(self.items)
        name = self._set_name(row)
        if not sets.choose(name):
            self._say("That set is gone. F5 lists the sets again.")
            return
        sets.save()
        self._say(f"Using {name}.")
        self.frame.reload()

    def _do_across_new_set(self, _ref: Any, _row: object) -> None:
        from quill.core.github.repository_sets import EVERY, normalize_set_name

        sets = sets_for(self.items)
        name = normalize_set_name(self._ask_text("New Repository Set", "Name for the new set:"))
        if not name:
            return
        if name.casefold() in {n.casefold() for n in sets.names()}:
            self._say(f"There is already a set called {name}.")
            return
        how = self._choose(
            "New Repository Set",
            f"How {name} is made:",
            [
                "Choose repositories from a list",
                "By a filter, such as org:name topic:x",
                "Every repository I can reach (up to 200)",
            ],
        )
        if how < 0:
            return
        if how == 0:
            self.pick_repositories(name)
            return
        if how == 1:
            search = self._ask_text(
                "New Repository Set", "Filter, as GitHub's repository search (org:name topic:x):"
            )
            if not search:
                return
        else:
            search = EVERY
        sets.set_filter(name, search)
        sets.choose(name)
        sets.save()
        self._say(f"Made {sets.describe(name)}.")
        self.frame.reload()

    def _do_across_edit_set(self, _ref: Any, row: object) -> None:
        sets = sets_for(self.items)
        name = self._set_name(row)
        if sets.filter_for(name):
            self._say(f"{name} is made by a filter. Set Filter changes it.")
            return
        self.pick_repositories(name)

    def _checklist(
        self, title: str, candidates: list[str], checked: list[str], note: str
    ) -> list[str] | None:
        from quill.ui.dialog_contract import show_modal_dialog
        from quill.ui.github_repository_checklist import choose_repositories

        return choose_repositories(
            self.frame.frame,
            show_modal_dialog,
            title=title,
            repositories=candidates,
            checked=checked,
            note=note,
        )

    def pick_repositories(self, name: str) -> None:
        """The checklist for *name*: its repositories, then those the account can reach."""
        from quill.core.github.across import why_failed

        current = sets_for(self.items).repositories(name)
        api = self.github_api()  # type: ignore[attr-defined]

        def work() -> tuple[list[str], str]:
            try:
                answer = api.rest(
                    "GET",
                    "/user/repos",
                    query={
                        "affiliation": "owner,collaborator,organization_member",
                        "sort": "pushed",
                        "per_page": "100",
                    },
                )
            except Exception as exc:  # noqa: BLE001 - the set itself is still listed
                return [], (
                    f"Your repositories could not be listed ({why_failed(exc)}); Add takes "
                    "any repository by name."
                )
            rows = answer.data if isinstance(answer.data, list) else []
            names = [
                str(r["full_name"]) for r in rows if isinstance(r, dict) and r.get("full_name")
            ]
            note = (
                "The 100 repositories you pushed to most recently are listed; Add takes any other."
                if len(rows) >= 100
                else ""
            )
            return names, note

        def done(answer: tuple[list[str], str]) -> None:
            names, note = answer
            seen: dict[str, str] = {}
            for repo in [*current, *names]:
                seen.setdefault(repo.lower(), repo)
            chosen = self._checklist(f"Repositories in {name}", list(seen.values()), current, note)
            if chosen is None:
                return
            sets = sets_for(self.items)
            sets.set_repositories(name, chosen)
            if not sets.choose(sets.current_name):
                sets.choose(name)
            sets.save()
            self._say(f"{len(sets.repositories(name))} repositories in {name}.")
            self.frame.reload()

        self._background("list your repositories", work, done)  # type: ignore[attr-defined]

    def _do_across_set_filter(self, _ref: Any, row: object) -> None:
        sets = sets_for(self.items)
        name = self._set_name(row)
        search = self._ask_text(
            f"Filter for {name}",
            "Filter, as GitHub's repository search (org:name topic:x). The set is made "
            "by it each time it is used:",
            value=sets.filter_for(name),
        )
        if not search:
            return
        sets.set_filter(name, search)
        sets.save()
        self._say(f"{name} is now made by the filter {search}.")
        self.frame.reload()

    def _do_across_rename_set(self, _ref: Any, row: object) -> None:
        sets = sets_for(self.items)
        name = self._set_name(row)
        new = self._ask_text("Rename Repository Set", f"New name for {name}:", value=name)
        if not new or new == name:
            return
        problem = sets.rename(name, new)
        if problem:
            self._say(problem)
            return
        sets.save()
        self._say(f"Renamed to {new}.")
        self.frame.reload()

    def _do_across_delete_set(self, _ref: Any, row: object) -> None:
        sets = sets_for(self.items)
        name = self._set_name(row)
        if not self._confirm(
            "Delete Repository Set",
            f"Delete the set {name}? Only the list on this computer goes; nothing on "
            "GitHub changes.",
        ):
            return
        sets.delete(name)
        sets.save()
        self._say(f"Deleted {name}. Using {sets.current_name}.")
        self.frame.reload()
