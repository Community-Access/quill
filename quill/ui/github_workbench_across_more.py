"""Release Train, Set Secret Everywhere and Turn On or Off Everywhere (PRD 22.11).

The three by-name commands that belong to one kind each, on top of the shared
ones in :mod:`quill.ui.github_workbench_across_names` (which also routes Make
Them the Same, Add to Missing, Rename, Delete and Promote to Organization for
these kinds):

- **Release Train...** on a Tags by Name row: the tag to make (the row's, or
  another), what to make with it (the tag only, a draft release, or the tag and
  a published release), the notes once, and the repositories, with those that
  lack it checked. A repository that has the tag is skipped in the preview and
  its tag is never moved.
- **Set Secret Everywhere...** on a Secrets by Name row: the repositories (those
  that have it checked), then the new value, typed once in a password box. It
  is sealed for each repository on the way out and is never written to Change
  History, the details pane or the preview.
- **Turn On or Off Everywhere...** on a Webhooks by Name row.

Each goes through the same preview and result per repository as every other
by-name change (``_run_plan``), and the Workbench level is checked once by the
dispatcher.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.explore_models import ExploreRow

__all__ = ["MORE_REASONS", "MORE_VERBS", "GitHubWorkbenchAcrossMoreMixin", "kind_of"]

MORE_VERBS: dict[str, frozenset[str]] = {
    "across_release_train": frozenset({"by_name"}),
    "across_set_secret": frozenset({"by_name"}),
    "across_hooks_on_off": frozenset({"by_name"}),
}
MORE_REASONS: dict[str, str] = {
    "across_release_train": "Only a row under Tags by Name starts a release train.",
    "across_set_secret": "Only a row under Secrets by Name has a value to set.",
    "across_hooks_on_off": "Only a webhook is turned on or off.",
}


def kind_of(row: object) -> str:
    """The by-name kind of *row* ("" when it is not a by-name row)."""
    if isinstance(row, ExploreRow) and row.kind == "by_name":
        return row.key.partition(":")[0]
    return ""


class GitHubWorkbenchAcrossMoreMixin:
    """The one-kind commands of the by-name sheets."""

    frame: Any
    _say: Callable[[str], None]
    _ask_text: Callable[..., str]
    _choose: Callable[[str, str, list[str]], int]
    _ask_secret: Callable[[str, str], str | None]
    _survey_row: Callable[[object], tuple[Any, Any] | None]
    _choose_many: Callable[[str, str, list[str], list[str]], list[str]]
    _run_plan: Callable[..., None]

    def _fits_across_release_train(self, row: object) -> bool:
        return kind_of(row) == "tags"

    def _fits_across_set_secret(self, row: object) -> bool:
        return kind_of(row) == "secrets"

    def _fits_across_hooks_on_off(self, row: object) -> bool:
        return kind_of(row) == "webhooks"

    @staticmethod
    def _answered(found: Any) -> list[str]:
        """The set's repositories that could be read, in the set's order."""
        unread = {repo for repo, _why in found.unread}
        return [repo for repo in found.scope if repo not in unread]

    def _hook_secret(self, kind: str, title: str) -> str | None:
        """A webhook's secret, typed once ("" for none); None when cancelled. "" for other kinds."""
        if kind != "webhooks":
            return ""
        return self._ask_secret(
            title,
            "The webhook's secret, typed once and sent to each repository, or leave it empty "
            "for none. GitHub never shows an existing webhook's secret, so it cannot be copied:",
        )

    def _do_across_release_train(self, _ref: Any, row: object) -> None:
        from quill.core.github.across_more_promote import TRAIN_CHOICES, plan_release_train
        from quill.core.github.tags import valid_tag_name

        pair = self._survey_row(row)
        if pair is None:
            return
        found, hit = pair
        title = "Release Train"
        name = self._ask_text(title, "The tag to make in each repository:", value=hit.name)
        if not name:
            return
        why = valid_tag_name(name)
        if why:
            self._say(why)
            return
        index = self._choose(title, f"What to make for {name}:", [w for _k, w in TRAIN_CHOICES])
        if index < 0:
            return
        make = TRAIN_CHOICES[index][0]
        notes = ""
        if make != "tag":
            notes = self._ask_text(title, "The release notes, the same in each:", multiline=True)
        answered = self._answered(found)
        lacking = [repo for repo in answered if found.has(repo, name) is None]
        targets = self._choose_many(title, f"Make {name} in:", answered, lacking)
        if targets:
            plan = plan_release_train(found, name, targets, make, notes)
            self._run_plan("across_release_train", plan, "Make")

    def _do_across_set_secret(self, _ref: Any, row: object) -> None:
        from quill.core.github.across_more_changes import plan_set_secret

        pair = self._survey_row(row)
        if pair is None:
            return
        found, hit = pair
        title = "Set Secret Everywhere"
        answered = self._answered(found)
        having = [c.repository for c in hit.copies]
        targets = self._choose_many(title, f"Set {hit.name} in:", answered, having)
        if not targets:
            return
        value = self._ask_secret(
            title,
            f"The new value of {hit.name}, typed once. It is sealed for each repository before "
            "it leaves this computer and is never shown again:",
        )
        if value:
            plan = plan_set_secret(found, hit.name, targets)
            self._run_plan("across_set_secret", plan, "Set", secret=value)

    def _do_across_hooks_on_off(self, _ref: Any, row: object) -> None:
        from quill.core.github.across_more_changes import plan_hooks_on_off

        pair = self._survey_row(row)
        if pair is None:
            return
        found, hit = pair
        index = self._choose("Turn On or Off Everywhere", f"{hit.name}:", ["Turn off", "Turn on"])
        if index >= 0:
            plan = plan_hooks_on_off(found, hit, on=index == 1)
            self._run_plan("across_hooks_on_off", plan, ("Turn off", "Turn on")[index])

    def _promote_more(self, found: Any, hit: Any, winner: Any, organization: str) -> None:
        """Promote a secret, variable or webhook; a secret's value is typed once."""
        from quill.core.github.across_more_promote import plan_more_promote

        title = "Promote to Organization"
        secret: str | None = ""
        if found.kind == "secrets":
            secret = self._ask_secret(
                title,
                f"The value of {hit.name} for the organization, typed once. No repository's "
                "value can be read, so it cannot be copied:",
            )
            if not secret:
                return
        else:
            secret = self._hook_secret(found.kind, title)
            if secret is None:
                return
        plan = plan_more_promote(found, hit, winner, organization)
        self._run_plan("across_promote_org", plan, "Promote", secret=secret)
