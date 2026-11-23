"""Delete Where Merged, Draft Releases Together and Dismiss Everywhere (PRD 22.11; GH-R-151).

Three across-repository writes whose preview needs GitHub's answers first, so
each plan is made off the UI thread and then goes through the same preview,
level check and result per repository as every other by-name change
(``_run_plan`` in :mod:`quill.ui.github_workbench_across_names`):

- **Delete Where Merged...** on a Branches by Name row
  (:mod:`quill.core.github.across_branch_release`): destructive, so the preview
  starts on Cancel and its summary names the count and the repositories.
- **Draft Releases Together...** on a Tags by Name row: the notes are typed
  once, ``{repository}`` and ``{tag}`` filled in for each, and the repositories
  that have the tag are checked.
- **Dismiss Everywhere...** on an alert row of Across Repositories > Security
  Alerts (:mod:`quill.core.github.across_alerts`): one of GitHub's reasons and
  one comment; the preview starts on Cancel. Each dismissed alert can be
  reopened from Change History (Undo).

The repository chooser (``_choose_many``) and the preview (``_across_preview``)
that every by-name change shows live here too.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.explore_models import ExploreRow

__all__ = ["OPS_REASONS", "OPS_VERBS", "GitHubWorkbenchAcrossOpsMixin"]

OPS_VERBS: dict[str, frozenset[str]] = {
    "across_delete_merged": frozenset({"by_name"}),
    "across_draft_releases": frozenset({"by_name"}),
    "across_dismiss_alerts": frozenset({"across_item"}),
}
OPS_REASONS: dict[str, str] = {
    "across_delete_merged": "Delete Where Merged is for a branch, under Branches by Name.",
    "across_draft_releases": "Draft Releases Together is for a tag, under Tags by Name.",
    "across_dismiss_alerts": (
        "Only an open Dependabot or code scanning alert under Security Alerts is dismissed "
        "everywhere. Each leaked secret is its own, so a secret scanning alert is resolved in "
        "its own repository."
    ),
}


def _kind_of(row: object) -> str:
    if isinstance(row, ExploreRow) and row.kind == "by_name":
        return row.key.partition(":")[0]
    return ""


class GitHubWorkbenchAcrossOpsMixin:
    """The three by-name and Security Alerts writes that read GitHub before their preview."""

    frame: Any
    _say: Callable[[str], None]
    _ask_text: Callable[..., str]
    _ask_optional: Callable[[str, str], str | None]
    _choose: Callable[[str, str, list[str]], int]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _survey_row: Callable[[object], tuple[Any, Any] | None]
    _run_plan: Callable[..., None]
    _answered: Callable[[Any], list[str]]

    def github_api(self) -> Any:
        raise NotImplementedError

    def across_scope(self) -> tuple[list[str], str]:
        raise NotImplementedError

    # -- the chooser and the preview every by-name change uses (``_run_plan``) ------

    def _choose_many(
        self, title: str, prompt: str, labels: list[str], checked: list[str]
    ) -> list[str]:
        """Real check boxes that each say their state (A11Y-SR-1); [] on Cancel."""
        from quill.ui.dialog_contract import show_modal_dialog
        from quill.ui.wordpress_workbench_dialogs import ask_checks

        chosen = ask_checks(
            self.frame.frame,
            show_modal_dialog,
            title=title,
            prompt=prompt,
            rows=labels,
            checked=[i for i, label in enumerate(labels) if label in checked],
            help_text="The repositories this change reaches. The preview comes next.",
        )
        return [labels[i] for i in chosen or ()]

    def _across_preview(
        self,
        title: str,
        plan: Any,
        yes: str,
        *,
        destructive: bool | None = None,
        undoable: bool = False,
    ) -> bool:
        """The preview; a destructive one starts on Cancel and names every repository."""
        from quill.ui.dialog_contract import show_modal_dialog
        from quill.ui.wordpress_workbench_dialogs import (
            IRREVERSIBLE,
            _destructive_now,
            ask_preview,
        )

        summary = plan.preview().splitlines()[0]
        if destructive is None:
            destructive = _destructive_now() or yes in IRREVERSIBLE
        names = [step.repository for step in plan.runnable]
        if destructive and names:  # it starts on Cancel, so it says where it reaches
            listed = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]
            summary += f" They are: {listed}."
        return ask_preview(
            self.frame.frame,
            show_modal_dialog,
            title=title,
            summary=summary,
            lines=[step.preview() for step in plan.steps],
            yes=yes,
            destructive=destructive,
            undoable=undoable,
        )

    # -- what fits which row ---------------------------------------------------------

    def _fits_across_delete_merged(self, row: object) -> bool:
        return _kind_of(row) == "branches"

    def _fits_across_draft_releases(self, row: object) -> bool:
        return _kind_of(row) == "tags"

    def _open_alert(self, row: object) -> tuple[str, Any] | None:
        from quill.core.github.across_alerts import DISMISSABLE

        source = self._source(row)  # type: ignore[attr-defined]
        if source is None or source[0] != "alerts":
            return None
        _kind, repo, model = source
        if getattr(model, "alert_type", "") not in DISMISSABLE:
            return None
        if str(getattr(model, "state", "")).lower() != "open":
            return None
        return repo, model

    def _fits_across_dismiss_alerts(self, row: object) -> bool:
        return self._open_alert(row) is not None

    # -- Delete Where Merged ---------------------------------------------------------

    def _do_across_delete_merged(self, _ref: Any, row: object) -> None:
        from quill.core.github.across_branch_release import (
            apply_merged_delete,
            plan_merged_delete,
        )

        pair = self._survey_row(row)
        if pair is None:
            return
        found, hit = pair
        api = self.github_api()

        def planned(plan: Any) -> None:
            self._run_plan(
                "across_delete_merged", plan, "Delete", engine=apply_merged_delete, destructive=True
            )

        self._background(
            f"check where {hit.name} is merged",
            lambda: plan_merged_delete(api, found, hit),
            planned,
        )

    # -- Draft Releases Together -----------------------------------------------------

    def _do_across_draft_releases(self, _ref: Any, row: object) -> None:
        from quill.core.github.across_branch_release import (
            TEMPLATE_HELP,
            apply_draft_releases,
            plan_draft_releases,
        )

        pair = self._survey_row(row)
        if pair is None:
            return
        found, hit = pair
        title = "Draft Releases Together"
        answered = self._answered(found)
        having = [c.repository for c in hit.copies]
        targets = self._choose_many(title, f"Draft a release of {hit.name} in:", answered, having)
        if not targets:
            return
        notes = self._ask_text(
            title, f"The release notes, written once. {TEMPLATE_HELP}", multiline=True
        )
        if not notes:
            return
        index = self._choose(
            title,
            "Add GitHub's generated notes after yours?",
            ["No, only my notes", "Yes, add GitHub's generated notes"],
        )
        if index < 0:
            return
        api, tag = self.github_api(), hit.name

        def planned(plan: Any) -> None:
            self._run_plan("across_draft_releases", plan, "Draft", engine=apply_draft_releases)

        self._background(
            f"read the releases of {tag}",
            lambda: plan_draft_releases(api, found, tag, targets, notes, generated=index == 1),
            planned,
        )

    # -- Dismiss Everywhere ----------------------------------------------------------

    def _do_across_dismiss_alerts(self, _ref: Any, row: object) -> None:
        from quill.core.github.across_alerts import (
            COMMENT_LIMIT,
            apply_dismiss,
            match_for,
            plan_dismiss,
        )
        from quill.core.github.alert_triage import DISMISS_REASONS, alert_kind_for

        found = self._open_alert(row)
        if found is None:
            self._say("Load the list again first: F5.")
            return
        repo, model = found
        kind = alert_kind_for(model.alert_type)
        title = "Dismiss Everywhere"
        reasons = DISMISS_REASONS[kind.key]
        index = self._choose(
            title,
            f"Why dismiss {kind.label.lower()} alert #{model.number} in {repo}, and every open "
            f"alert in the set for the same {'advisory' if kind.key == 'dependabot' else 'rule'}?",
            [words for _value, words in reasons],
        )
        if index < 0:
            return
        comment = self._ask_optional(
            title, f"A comment for every dismissal, up to {COMMENT_LIMIT} characters (optional):"
        )
        if comment is None:
            return
        if len(comment) > COMMENT_LIMIT:
            self._say(
                f"The comment is {len(comment)} characters; GitHub takes at most "
                f"{COMMENT_LIMIT}. Nothing was dismissed."
            )
            return
        reason, api, number = reasons[index][0], self.github_api(), int(model.number)

        def plan() -> tuple[Any, Any]:
            match = match_for(api, repo, model.alert_type, number)
            repositories, _note = self.across_scope()
            return match, plan_dismiss(api, match, repositories, reason, comment)

        def planned(pair: tuple[Any, Any]) -> None:
            match, made = pair
            self._run_plan(
                "across_dismiss_alerts",
                made,
                "Dismiss",
                engine=lambda api_, plan_: apply_dismiss(api_, match, plan_),
                destructive=True,
                undoable=True,
            )

        self._background(f"find every copy of alert #{number}", plan, planned)
