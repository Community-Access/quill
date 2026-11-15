"""By name across repositories, and the Fleet, in the GitHub Workbench (PRD 22.11, 22.12).

Across Repositories > Labels by Name, Milestones by Name, Topics by Name and
Rules and Branch Protection each list one row per name across the Repository
Set in use ("bug: in 14 of 16 repositories, 3 colours, missing from 2"); the
details are its **Variants** (each set of properties with the repositories
that have it) and **Missing From** (the repositories that answered and lack
it), and a repository that could not be read is named apart, never counted
as missing. Labels, milestones, topics and rules can then be changed everywhere at once:
choose the winning variant, see the preview repository by repository -- what
changes, and what is blocked by permission or by a conflict -- and get one
result per repository, each kept in Change History (undoable where a
Properties sheet can reverse it). A ruleset can also be promoted to one
organization ruleset.

The Fleet lists each repository once: the exact revision it describes, its
checks, open pull requests, latest release and alerts, and when it was read;
a repository that failed keeps its line with the reason.

The engines are :mod:`quill.core.github.across_by_name`,
:mod:`quill.core.github.across_changes` and
:mod:`quill.core.github.across_fleet`; this mixin loads them off the UI thread
and asks before every write.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from quill.core.github.explore_models import ExploreRow

__all__ = ["NAME_LOADERS", "NAME_REASONS", "NAME_VERBS", "GitHubWorkbenchAcrossNamesMixin"]

#: Loader -> the by-name kind it reads.
NAME_LOADERS = {
    "across:by_labels": "labels",
    "across:by_milestones": "milestones",
    "across:by_topics": "topics",
    "across:by_rules": "rules",
}

NAME_VERBS: dict[str, frozenset[str]] = {
    "across_variants": frozenset({"by_name"}),
    "across_make_same": frozenset({"by_name"}),
    "across_add_missing": frozenset({"by_name"}),
    "across_rename_name": frozenset({"by_name"}),
    "across_merge_label": frozenset({"by_name"}),
    "across_delete_name": frozenset({"by_name"}),
    "across_close_milestone": frozenset({"by_name"}),
    "across_find_uses": frozenset({"by_name"}),
    "across_open_repository": frozenset({"fleet"}),
    "across_move_open": frozenset({"by_name"}),
    "across_promote_org": frozenset({"by_name"}),
}
NAME_REASONS: dict[str, str] = {
    "across_make_same": "A topic has no variants: Add to Missing or Delete Everywhere.",
    "across_add_missing": "Branch protection is per branch: Make Them the Same covers it.",
    "across_rename_name": "Only a label is renamed everywhere so far.",
    "across_merge_label": "Only labels are merged.",
    "across_delete_name": "Labels are deleted, and topics removed, everywhere; not this kind.",
    "across_close_milestone": "Only a milestone can be closed.",
    "across_find_uses": "Only labels and milestones are on issues to find.",
    "across_move_open": "Only a milestone's open work moves to another milestone.",
    "across_promote_org": (
        "Only a ruleset can become an organization ruleset; GitHub has no organization "
        "form for labels, milestones, topics or classic branch protection."
    ),
}
_P = "github.workbench."
_SEARCH_MAX = 250  # GitHub's search box takes 256 characters


def _kind_of(row: object) -> str:
    if isinstance(row, ExploreRow) and row.kind == "by_name":
        return row.key.partition(":")[0]
    return ""


class GitHubWorkbenchAcrossNamesMixin:
    """The by-name sheets and the Fleet over the Repository Set in use."""

    items: Any
    frame: Any
    _say: Callable[[str], None]
    _ask_text: Callable[..., str]
    _choose: Callable[[str, str, list[str]], int]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    local_note: str

    def github_api(self) -> Any:
        raise NotImplementedError

    def across_scope(self) -> tuple[list[str], str]:
        raise NotImplementedError

    # -- loading (off the UI thread) -------------------------------------------------

    def load_by_name(self, loader: str) -> list[ExploreRow]:
        from quill.core.github.across_by_name import survey

        kind = NAME_LOADERS[loader]
        repositories, note = self.across_scope()
        read_at = time.strftime("%H:%M UTC", time.gmtime())
        found = survey(self.github_api(), kind, repositories, read_at=read_at)
        if not hasattr(self, "_across_surveys"):
            self._across_surveys: dict[str, Any] = {}
        self._across_surveys[kind] = found
        self.local_note = found.summary() + (f" {note}" if note else "")
        return [
            ExploreRow(
                row.sentence(), row.detail(), "", "", "by_name", f"{kind}:{row.name}", "", row.name
            )
            for row in found.rows
        ]

    def load_fleet(self) -> list[ExploreRow]:
        from quill.core.github.across_fleet import read_fleet

        repositories, note = self.across_scope()
        read_at = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
        rows = read_fleet(self.github_api(), repositories, read_at=read_at)
        failed = sum(1 for r in rows if r.failed)
        self.local_note = f"{len(rows)} repositories, {failed} could not be read." + (
            f" {note}" if note else ""
        )
        return [
            ExploreRow(
                r.sentence(),
                r.detail(),
                f"https://github.com/{r.repository}",
                r.repository,
                "fleet",
                f"fleet:{r.repository}",
                r.read_at,
                r.repository,
            )
            for r in rows
        ]

    # -- what fits which row ---------------------------------------------------------

    def _fits_across_make_same(self, row: object) -> bool:
        return _kind_of(row) in ("labels", "milestones", "rules")

    def _fits_across_add_missing(self, row: object) -> bool:
        if _kind_of(row) == "rules":
            return isinstance(row, ExploreRow) and not row.title.startswith("Branch protection on ")
        return _kind_of(row) in ("labels", "milestones", "topics")

    def _fits_across_rename_name(self, row: object) -> bool:
        return _kind_of(row) == "labels"

    _fits_across_merge_label = _fits_across_rename_name

    def _fits_across_delete_name(self, row: object) -> bool:
        return _kind_of(row) in ("labels", "topics")

    def _fits_across_close_milestone(self, row: object) -> bool:
        return _kind_of(row) == "milestones"

    _fits_across_move_open = _fits_across_close_milestone

    def _fits_across_find_uses(self, row: object) -> bool:
        return _kind_of(row) in ("labels", "milestones")

    def _fits_across_promote_org(self, row: object) -> bool:
        return _fits_across_add_missing_rules(row)

    # -- reading ---------------------------------------------------------------------

    def _survey_row(self, row: object) -> tuple[Any, Any] | None:
        kind = _kind_of(row)
        found = getattr(self, "_across_surveys", {}).get(kind)
        hit = found.row(row.title) if found is not None and isinstance(row, ExploreRow) else None
        if hit is None:
            self._say("Load the list again first: F5.")
            return None
        return found, hit

    def _do_across_variants(self, _ref: Any, _row: object) -> None:
        self.frame.details.SetFocus()

    def _do_across_find_uses(self, _ref: Any, row: object) -> None:
        from quill.core.github.across_by_name import find_uses_query

        pair = self._survey_row(row)
        if pair is None:
            return
        found, hit = pair
        repos = [c.repository for c in hit.copies]
        query = find_uses_query(found.kind, hit.name, [])
        kept: list[str] = []
        for repo in repos:
            if len(find_uses_query(found.kind, hit.name, [*kept, repo])) > _SEARCH_MAX:
                break
            kept.append(repo)
        query = find_uses_query(found.kind, hit.name, kept)
        if len(kept) < len(repos):
            self._say(
                f"GitHub's search takes {len(kept)} of the {len(repos)} repositories at once; "
                "searching those."
            )
        self._go_filtered("", "search_issues", "", query)  # type: ignore[attr-defined]

    def _do_across_open_repository(self, _ref: Any, row: object) -> None:
        assert isinstance(row, ExploreRow)
        self._go_repository(row.repo)  # type: ignore[attr-defined]

    # -- changing --------------------------------------------------------------------

    def _winner(self, hit: Any, title: str) -> Any:
        from quill.core.github.across_by_name import describe_props

        variants = hit.variants()
        if len(variants) == 1:
            return variants[0][0]
        labels = [
            f"Variant {n}, {describe_props(props)}: {len(repos)} repositories, {', '.join(repos)}"
            for n, (props, repos) in enumerate(variants, start=1)
        ]
        index = self._choose(title, "Which version wins?", labels)
        return variants[index][0] if index >= 0 else None

    def _do_across_make_same(self, _ref: Any, row: object) -> None:
        from quill.core.github.across_admin_changes import plan_rules_same
        from quill.core.github.across_changes import plan_make_same

        pair = self._survey_row(row)
        if pair is None:
            return
        found, hit = pair
        if len(hit.variants()) < 2:
            self._say(f"{hit.name} is already the same in every repository that has it.")
            return
        winner = self._winner(hit, "Make Them the Same")
        if winner is None:
            return
        planner = plan_rules_same if found.kind == "rules" else plan_make_same
        self._run_plan("across_make_same", planner(found, hit, winner), "Make the Same")

    def _do_across_add_missing(self, _ref: Any, row: object) -> None:
        from quill.core.github.across_admin_changes import plan_rules_add_missing, plan_topic_add
        from quill.core.github.across_changes import plan_copy_missing

        pair = self._survey_row(row)
        if pair is None:
            return
        found, hit = pair
        if not hit.missing:
            self._say(f"Every repository that answered has {hit.name}.")
            return
        targets = self._choose_many(
            "Add to Missing", f"Add {hit.name} to:", list(hit.missing), list(hit.missing)
        )
        if not targets:
            return
        if found.kind == "topics":
            self._run_plan("across_add_missing", plan_topic_add(found, hit, targets), "Add")
            return
        winner = self._winner(hit, "Add to Missing")
        if winner is None:
            return
        planner = plan_rules_add_missing if found.kind == "rules" else plan_copy_missing
        self._run_plan("across_add_missing", planner(found, hit, winner, targets), "Add")

    def _do_across_rename_name(self, _ref: Any, row: object) -> None:
        from quill.core.github.across_changes import plan_rename

        pair = self._survey_row(row)
        if pair is None:
            return
        found, hit = pair
        new = self._ask_text("Rename Everywhere", f"New name for {hit.name}:", value=hit.name)
        if new and new != hit.name:
            self._run_plan("across_rename_name", plan_rename(found, hit, new), "Rename")

    def _do_across_merge_label(self, _ref: Any, row: object) -> None:
        from quill.core.github.across_changes import plan_merge

        pair = self._survey_row(row)
        if pair is None:
            return
        found, hit = pair
        others = [r.name for r in found.rows if r.name != hit.name]
        if not others:
            self._say("There is no other label to merge it into.")
            return
        index = self._choose("Merge Into", f"Move every item from {hit.name} to:", others)
        if index >= 0:
            self._run_plan("across_merge_label", plan_merge(found, hit, others[index]), "Merge")

    def _do_across_delete_name(self, _ref: Any, row: object) -> None:
        from quill.core.github.across_admin_changes import plan_topic_remove
        from quill.core.github.across_changes import plan_delete

        pair = self._survey_row(row)
        if pair is None:
            return
        if pair[0].kind == "topics":
            self._run_plan("across_delete_name", plan_topic_remove(*pair), "Remove")
        else:
            self._run_plan("across_delete_name", plan_delete(*pair), "Delete")

    def _do_across_move_open(self, _ref: Any, row: object) -> None:
        from quill.core.github.across_changes import plan_move_open

        pair = self._survey_row(row)
        if pair is None:
            return
        found, hit = pair
        others = [r.name for r in found.rows if r.name != hit.name]
        if not others:
            self._say("There is no other milestone to move the open work to.")
            return
        index = self._choose("Move Open Work", f"Move open items from {hit.name} to:", others)
        if index >= 0:
            plan = plan_move_open(found, hit, others[index])
            self._run_plan("across_move_open", plan, "Move")

    def _do_across_promote_org(self, _ref: Any, row: object) -> None:
        from quill.core.github.across_admin_changes import plan_promote

        pair = self._survey_row(row)
        if pair is None:
            return
        found, hit = pair
        owners = sorted({c.repository.split("/")[0] for c in hit.copies}, key=str.casefold)
        index = self._choose("Promote to Organization", "Which organization:", owners)
        if index < 0:
            return
        winner = self._winner(hit, "Promote to Organization")
        if winner is not None:
            plan = plan_promote(found, hit, winner, owners[index])
            self._run_plan("across_promote_org", plan, "Promote")

    def _do_across_close_milestone(self, _ref: Any, row: object) -> None:
        from quill.core.github.across_changes import plan_close

        pair = self._survey_row(row)
        if pair is not None:
            self._run_plan("across_close_milestone", plan_close(*pair), "Close")

    def _choose_many(
        self, title: str, prompt: str, labels: list[str], checked: list[str]
    ) -> list[str]:
        wx = self.frame._wx
        from quill.ui.dialog_contract import show_modal_dialog

        with wx.MultiChoiceDialog(self.frame.frame, prompt, title, labels) as dialog:
            dialog.SetSelections([i for i, label in enumerate(labels) if label in checked])
            if show_modal_dialog(dialog, title) != wx.ID_OK:
                return []
            return [labels[i] for i in dialog.GetSelections()]

    def _preview(self, title: str, plan: Any, yes: str) -> bool:
        from quill.ui.dialog_contract import show_modal_dialog
        from quill.ui.wordpress_workbench_dialogs import ask_preview

        return ask_preview(
            self.frame.frame,
            show_modal_dialog,
            title=title,
            summary=plan.preview().splitlines()[0],
            lines=[step.preview() for step in plan.steps],
            yes=yes,
        )

    def _run_plan(self, verb: str, plan: Any, yes: str) -> None:
        """Check the account's level, preview, then run off the UI thread; one result each."""
        from quill.core.github.across_admin_changes import apply_admin, apply_promote
        from quill.core.github.across_changes import apply, results_summary
        from quill.core.github.permissions import AccessLevel, WriteTier, level_allows
        from quill.core.github.write_requirements import requirement_for

        declared = requirement_for(f"{_P}{verb}")
        tier = declared[1] if declared is not None else WriteTier.VISIBLE
        if plan.kind == "rules":
            tier = max(tier, WriteTier.ACCESS)  # rules decide who may change code
        level = self.access_level()  # type: ignore[attr-defined]
        if not level_allows(level, tier):
            self._say(
                "This account is read only in the Workbench."
                if level is AccessLevel.READ_ONLY
                else "This account is set to Organize in the Workbench, which does not allow this."
            )
            return
        if not plan.runnable:
            self.frame.details.ChangeValue(plan.preview())
            self._say("Nothing would change. The details say why, repository by repository.")
            return
        if not self._preview(f"{yes}: {plan.name}", plan, yes):
            return
        api = self.github_api()
        if verb == "across_promote_org":
            work = lambda: apply_promote(api, plan)  # noqa: E731
        elif plan.kind in ("topics", "rules"):
            work = lambda: apply_admin(api, plan)  # noqa: E731
        else:
            work = lambda: apply(api, plan)  # noqa: E731

        def done(results: Any) -> None:
            self._record_across(results, int(tier))
            lines = [
                f"{r.repository}: {'done' if r.ok else 'not changed'}, {r.said}" for r in results
            ]
            said = results_summary(results)
            # The results stay in the details until you move; F5 reads the set again.
            self.frame.details.ChangeValue("\n".join([said, "", *lines]))
            self._say(f"{said} F5 reads the repositories again.")

        self._background(f"{yes.lower()} {plan.name}", work, done)

    def _record_across(self, results: Any, tier: int) -> None:
        """Change History: one row per repository that changed, undoable where a sheet can."""
        from quill.core.workbench.properties import FieldChange

        try:
            log = self.change_log()  # type: ignore[attr-defined]
            account = self.account_name()  # type: ignore[attr-defined]
            for result in results:
                entry = result.log
                if not result.ok or entry is None:
                    continue
                log.record(
                    account=account,
                    kind=entry.kind,
                    ident=dict(entry.ident),
                    target=entry.target,
                    summary=f"Across Repositories: {entry.summary}",
                    changes=[FieldChange(k, label, b, a) for k, label, b, a in entry.changes],  # type: ignore[arg-type]
                    tier=tier,
                    confirmed=entry.confirmed,
                    can_undo=entry.can_undo,
                )
        except OSError:
            pass  # a history that cannot be written must not hide the results


def _fits_across_add_missing_rules(row: object) -> bool:
    return (
        isinstance(row, ExploreRow)
        and _kind_of(row) == "rules"
        and not row.title.startswith("Branch protection on ")
    )
