"""Ctrl+N, Change and Delete for every list of the resource engine (GitHub PRD section 19).

The lists are described in :mod:`quill.core.github.resource_specs`; this
mixin asks each :class:`~quill.core.github.resource_engine.Field` in turn:
a text box, a multi-line box, a choice, a yes or no, or, for a secret, a
password box whose answer is never said, shown or kept: it is sealed, sent,
and dropped from the answers once the call ends. Delete asks first.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.explore_models import ExploreRow

__all__ = ["RESOURCE_REASONS", "RESOURCE_VERBS", "GitHubWorkbenchResourcesMixin"]

RESOURCE_VERBS: dict[str, frozenset[str]] = {
    "resource_new": frozenset({"view"}),
    "resource_edit": frozenset({"resource"}),
    "resource_delete": frozenset({"resource"}),
    "resource_repositories": frozenset({"resource"}),
}

RESOURCE_REASONS: dict[str, str] = {
    "resource_new": "New Here adds to this list, while you are signed in.",
    "resource_edit": "Change is for a row GitHub lets you change.",
    "resource_delete": "Delete is for a row GitHub lets you delete.",
    "resource_repositories": (
        "Repositories Allowed is for an organization's secret, variable or runner group, "
        "or one of your Codespaces secrets."
    ),
}


class GitHubWorkbenchResourcesMixin:
    frame: Any
    signed_in: bool
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _choose: Callable[[str, str, list[str]], int]
    _confirm: Callable[[str, str], bool]
    _ask_text: Callable[..., str]

    def github_api(self) -> Any:
        raise NotImplementedError

    # -- which list, and which row ---------------------------------------------------------

    def _current_spec(self) -> Any:
        from quill.core.github.resource_specs import spec_for

        return spec_for(getattr(getattr(self.frame, "current", None), "key", ""))

    @staticmethod
    def _row_spec(row: object) -> tuple[Any, str]:
        from quill.core.github.resource_engine import row_spec_and_id
        from quill.core.github.resource_specs import spec_for

        if not isinstance(row, ExploreRow) or row.kind != "resource":
            return None, ""
        key, item_id = row_spec_and_id(row.key)
        return spec_for(key), item_id

    def _fits_resource_new(self, _row: object) -> bool:
        spec = self._current_spec()
        return self.signed_in and spec is not None and bool(spec.create)

    def _fits_resource_edit(self, row: object) -> bool:
        spec, _item = self._row_spec(row)
        return self.signed_in and spec is not None and bool(spec.edit)

    def _fits_resource_delete(self, row: object) -> bool:
        spec, _item = self._row_spec(row)
        return self.signed_in and spec is not None and spec.delete

    def _fits_resource_repositories(self, row: object) -> bool:
        spec, _item = self._row_spec(row)
        return self.signed_in and spec is not None and bool(spec.repositories)

    # -- asking ----------------------------------------------------------------------------

    def _ask_secret(self, title: str, prompt: str) -> str | None:
        from quill.ui.dialog_contract import show_modal_dialog

        wx = self.frame._wx
        with wx.PasswordEntryDialog(self.frame.frame, prompt, title) as box:
            box.SetName("Value")
            if show_modal_dialog(box, title) != wx.ID_OK:
                return None
            return str(box.GetValue())

    def _ask_fields(self, title: str, fields: tuple[Any, ...]) -> dict[str, str] | None:
        """Every field's answer by key, or None the moment one is cancelled."""
        answers: dict[str, str] = {}
        for one in fields:
            if one.kind == "secret":
                found = self._ask_secret(title, one.prompt)
                if found is None or (not found and not one.optional):
                    return None
                answers[one.key] = found
            elif one.kind in ("choice", "bool"):
                labels = list(one.choices) if one.kind == "choice" else ["Yes", "No"]
                picked = self._choose(title, one.prompt, labels)
                if picked < 0:
                    return None
                answers[one.key] = (
                    labels[picked] if one.kind == "choice" else ("true" if picked == 0 else "false")
                )
            else:
                text = self._ask_text(title, one.prompt, multiline=one.kind == "multiline")
                if not text and not one.optional:
                    return None
                answers[one.key] = text
        return answers

    # -- doing -----------------------------------------------------------------------------

    def _then_reload_said(self, said: object) -> None:
        self._say(str(said))
        self.frame.reload()

    def _do_resource_new(self, ref: Any, _row: object) -> None:
        from quill.core.github.resource_engine import create

        spec = self._current_spec()
        if spec is None:
            return
        answers = self._ask_fields(f"New {spec.noun}", spec.create)
        if answers is None:
            return
        api, target = self.github_api(), ref.instance
        self._background(
            f"add the {spec.noun}",
            lambda: _then_forget(answers, spec.create, lambda: create(api, spec, target, answers)),
            self._then_reload_said,
        )

    def _do_resource_edit(self, ref: Any, row: object) -> None:
        from quill.core.github.resource_engine import edit

        spec, item_id = self._row_spec(row)
        if spec is None:
            return
        answers = self._ask_fields(f"Change {spec.noun}", spec.edit)
        if answers is None:
            return
        api, target = self.github_api(), ref.instance
        self._background(
            f"change the {spec.noun}",
            lambda: _then_forget(
                answers, spec.edit, lambda: edit(api, spec, target, item_id, answers)
            ),
            self._then_reload_said,
        )

    def _do_resource_delete(self, ref: Any, row: object) -> None:
        from quill.core.github.resource_engine import delete

        spec, item_id = self._row_spec(row)
        if spec is None or not isinstance(row, ExploreRow):
            return
        if not self._confirm(f"Delete {spec.noun}", f"Delete: {row.label}"):
            return
        if spec.typed_delete:
            expected = row.title or item_id
            typed = self._ask_text(
                "Type to Confirm", f"This is hard to reverse. Type {expected} to go ahead:"
            ).strip()
            if typed != expected:
                if typed:
                    self._say("The name did not match. Nothing changed.")
                return
        api, target = self.github_api(), ref.instance
        self._background(
            f"delete the {spec.noun}",
            lambda: delete(api, spec, target, item_id),
            self._then_reload_said,
        )

    # -- which repositories may use it -------------------------------------------------------

    def _choose_repositories(
        self, title: str, prompt: str, labels: list[str], checked: set[int]
    ) -> list[int] | None:
        """The checked rows' positions, or None when cancelled (unchecking all is an answer)."""
        from quill.ui.dialog_contract import show_modal_dialog

        wx = self.frame._wx
        with wx.MultiChoiceDialog(self.frame.frame, prompt, title, labels) as box:
            box.SetName(title)
            box.SetSelections(sorted(checked))
            if show_modal_dialog(box, title) != wx.ID_OK:
                return None
            return [int(i) for i in box.GetSelections()]

    def _do_resource_repositories(self, ref: Any, row: object) -> None:
        from quill.core.github.resource_engine import (
            allowed_repositories,
            candidate_repositories,
            set_repositories,
        )

        spec, item_id = self._row_spec(row)
        if spec is None:
            return
        api, target = self.github_api(), ref.instance

        def read() -> Any:
            return allowed_repositories(api, spec, target, item_id), candidate_repositories(
                api, spec, target
            )

        def chosen(found: Any) -> None:
            had, choices = found
            known = {repo.id for repo in choices}
            choices = choices + [repo for repo in had if repo.id not in known]
            labels = [repo.name for repo in choices]
            ids = {repo.id for repo in had}
            title = f"Repositories Allowed: {item_id}"
            picked = self._choose_repositories(
                title,
                f"Check each repository that may use the {spec.noun} {item_id}:",
                labels,
                {i for i, repo in enumerate(choices) if repo.id in ids},
            )
            if picked is None:
                return
            wanted = [choices[i] for i in picked]
            self._background(
                f"change which repositories may use {item_id}",
                lambda: set_repositories(api, spec, target, item_id, had, wanted),
                self._then_reload_said,
            )

        self._background(f"read which repositories may use {item_id}", read, chosen)


def _then_forget(answers: dict[str, str], fields: tuple[Any, ...], send: Callable[[], Any]) -> Any:
    """Send, then drop every secret answer, whether GitHub took it or not (decision 12)."""
    try:
        return send()
    finally:
        for one in fields:
            if one.kind == "secret":
                answers.pop(one.key, None)
