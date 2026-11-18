"""Lists that belong to one row, such as a gist's comments, through the resource engine.

A row that owns a small list (a gist's comments, history and forks) opens it
in a chooser: "Add a comment..." first where GitHub allows adding, then one
row per item; choosing an item offers Change and Delete where GitHub allows
them. This is the environment mixin's pattern, for any scope the engine knows.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.explore_models import ExploreRow

__all__ = ["SCOPED_REASONS", "SCOPED_VERBS", "GitHubWorkbenchScopedListsMixin"]

_GIST = frozenset({"gist"})

SCOPED_VERBS: dict[str, frozenset[str]] = {
    "gist_comments": _GIST,
    "gist_history": _GIST,
    "gist_forks": _GIST,
    "fork_gist": _GIST,
}

SCOPED_REASONS: dict[str, str] = {
    "gist_comments": "Comments is for a gist.",
    "gist_history": "History is for a gist.",
    "gist_forks": "Forks is for a gist.",
    "fork_gist": "Fork is for a gist, while you are signed in.",
}


class GitHubWorkbenchScopedListsMixin:
    frame: Any
    signed_in: bool
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _choose: Callable[[str, str, list[str]], int]
    _confirm: Callable[[str, str], bool]
    _ask_fields: Callable[[str, tuple[Any, ...]], dict[str, str] | None]

    def github_api(self) -> Any:
        raise NotImplementedError

    @staticmethod
    def _gist(row: object) -> ExploreRow | None:
        found = isinstance(row, ExploreRow) and row.kind == "gist" and bool(row.key)
        return row if found else None  # type: ignore[return-value]

    def _fits_gist_list(self, row: object) -> bool:
        return self._gist(row) is not None

    _fits_gist_comments = _fits_gist_list
    _fits_gist_history = _fits_gist_list
    _fits_gist_forks = _fits_gist_list

    def _fits_fork_gist(self, row: object) -> bool:
        return self.signed_in and self._gist(row) is not None

    def _do_gist_comments(self, _ref: Any, row: object) -> None:
        self._gist_list(row, "gist_comments")

    def _do_gist_history(self, _ref: Any, row: object) -> None:
        self._gist_list(row, "gist_history")

    def _do_gist_forks(self, _ref: Any, row: object) -> None:
        self._gist_list(row, "gist_forks")

    def _do_fork_gist(self, _ref: Any, row: object) -> None:
        from quill.core.github.resource_specs_gist import fork_gist

        found = self._gist(row)
        if found is None:
            return
        api = self.github_api()
        self._background("fork the gist", lambda: fork_gist(api, found.key), self._say)

    def _gist_list(self, row: object, key: str) -> None:
        from quill.core.github.resource_specs_gist import gist_spec

        found, spec = self._gist(row), gist_spec(key)
        if found is None or spec is None:
            return
        name = found.title or found.label
        self._manage_scoped(spec, found.key, name)

    def _manage_scoped(self, spec: Any, target: str, name: str) -> None:
        """List *spec* for *target* in a chooser, with Add, Change and Delete as allowed."""
        from quill.core.github import resource_engine as engine

        api = self.github_api()
        title = f"{name}: {spec.label.split()[-1]}"

        def listed(rows: Any) -> None:
            rows = list(rows)
            adds = [f"Add a {spec.noun}..."] if spec.create and self.signed_in else []
            labels = [*adds, *(one.label for one in rows)]
            if not labels:
                self._say(f"No {spec.noun}s.")
                return
            picked = self._choose(title, f"{name}'s {spec.noun}s:", labels)
            if picked < 0:
                return
            if adds and picked == 0:
                answers = self._ask_fields(f"New {spec.noun}", spec.create)
                if answers is not None:
                    self._background(
                        f"add the {spec.noun}",
                        lambda: engine.create(api, spec, target, answers),
                        lambda said: self._say(str(said)),
                    )
                return
            item = rows[picked - len(adds)]
            actions = (["Change it..."] if spec.edit else []) + (
                ["Delete..."] if spec.delete else []
            )
            if not actions or not self.signed_in:
                self._say(item.label)
                return
            _key, item_id = engine.row_spec_and_id(item.key)
            act = self._choose(title, item.label, actions)
            if act < 0:
                return
            if spec.edit and act == 0:
                answers = self._ask_fields(f"Change {spec.noun}", spec.edit)
                if answers is not None:
                    self._background(
                        f"change the {spec.noun}",
                        lambda: engine.edit(api, spec, target, item_id, answers),
                        lambda said: self._say(str(said)),
                    )
                return
            if self._confirm(f"Delete {spec.noun}", f"Delete this {spec.noun}? {item.label}"):
                self._background(
                    f"delete the {spec.noun}",
                    lambda: engine.delete(api, spec, target, item_id),
                    lambda said: self._say(str(said)),
                )

        self._background(
            f"list {name}'s {spec.noun}s", lambda: engine.fetch(api, spec, target), listed
        )
