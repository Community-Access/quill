"""Alt+Enter in the GitHub Workbench: the Properties sheet, its save, batch and undo (PRD 15, 16).

The GitHub provider's half of :meth:`WorkbenchFrame.show_properties`. One
object opens its sheet, loaded fresh off the UI thread; several of one kind
open one combined sheet ("Properties of 5 issues", Mixed values, three-state
check lists); a tree node opens its own object (the repository on
``owner/name``) or, for a folder that is not an object, the view's options.

Saving follows section 15.3 and 18.4 to the letter: tier 2 changes are
previewed in words, tier 3 also asks for the name typed; somebody else's
change since the sheet opened is shown per field with Keep Theirs or Use
Mine; GitHub's re-read decides what is reported; one sentence says it
through the announcement service; and each proven change is a row in Change
History that Undo GitHub Change (Ctrl+Z in the list) can reverse.

The wx-free work is :mod:`quill.core.github.sheet_engine` and
:mod:`quill.core.github.batch`; this mixin only sequences dialogs and the
background runner.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from typing import Any

from quill.core.github.batch import BatchItem, preview, results_text
from quill.core.github.permissions import WriteTier
from quill.core.github.sheet_catalog import (
    LAST_PAGE,
    SHEETS,
    Target,
    context_for,
    target_for,
    target_for_node,
)
from quill.core.github.sheet_engine import (
    Loaded,
    SaveOutcome,
    load,
    load_options,
    locked_fields,
    sentence,
)
from quill.core.workbench.properties import (
    FieldChange,
    FieldKind,
    FieldSpec,
    list_states,
    merge_values,
)
from quill.ui.github_workbench_history import GitHubWorkbenchHistoryMixin

__all__ = ["PAGE_FOR_VERB", "GitHubWorkbenchPropertiesMixin"]

#: Menu rows that open the sheet at a page rather than a dialog of their own
#: (decision 11: no per-property keys; the menus still name every change).
PAGE_FOR_VERB: dict[str, tuple[str, str]] = {
    "labels": ("organize", "labels"),
    "assignees": ("organize", "assignees"),
    "milestone": ("organize", "milestone"),
    "react": ("you", "reactions"),
    "subscribe": ("you", "subscribed"),
    "watch": ("you", "watch"),
    "lock": ("conversation", "locked"),
    "reviewers": ("reviews", "reviewers"),
    "access": ("access", ""),
    "team_members": ("members", ""),
}

_NOUNS = {"issue": "issues", "pull_request": "pull requests", "repository": "repositories"}


class GitHubWorkbenchPropertiesMixin(GitHubWorkbenchHistoryMixin):
    """Properties for :class:`~quill.ui.github_workbench_window.GitHubWorkbenchProvider`."""

    items: Any
    frame: Any
    api: Any = None
    batch_pace: float = 1.0
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]

    # -- what the sheets talk to ---------------------------------------------------

    def github_api(self) -> Any:
        if self.api is None:
            from quill.core.github.workbench_api import TokenApi

            self.api = TokenApi(getattr(self.items, "token", None))
        return self.api

    def account_name(self) -> str:
        try:
            from quill.core.github.accounts import active_github_account

            account = active_github_account()
        except Exception:  # noqa: BLE001 - no registry is "no account"
            account = None
        return str(getattr(account, "login", "") or "")

    def access_level(self) -> Any:
        from quill.core.github.permissions import AccessStore, effective_level

        return effective_level(AccessStore.load().level(self.account_name()))

    def token_scopes(self) -> tuple[str, ...] | None:
        from quill.core.github.token_health import parse_scopes

        header = getattr(self.items, "last_scopes_header", None)
        return parse_scopes(header) if isinstance(header, str) else None

    # -- opening -------------------------------------------------------------------

    def open_properties(self, ref: Any, rows: Sequence[object], page: str = "") -> None:
        """Alt+Enter: the rows' sheet, or the tree node's own object."""
        if not rows:
            target = target_for_node(ref.template, ref.key, ref.instance)
            if target is None:
                self._view_options(ref)
                return
            self._open_one(self._with_me(target), page)
            return
        targets = [target_for(row, ref.instance) for row in rows]
        if any(target is None for target in targets):
            self._say("This row has no Properties sheet yet.")
            return
        found = [self._with_me(t) for t in targets if t is not None]
        if len({t.kind for t in found}) > 1:
            self._say("Select rows of one kind for one sheet: these are of different kinds.")
            return
        if len(found) == 1:
            self._open_one(found[0], page)
        else:
            self._open_many(found)

    def _with_me(self, target: Target) -> Target:
        """*target* with the signed-in login as ``me``, for reads such as "follows you"."""
        me = self.account_name()
        return Target(target.kind, {**target.ident, "me": me}) if me else target

    def open_sheet_at(self, verb: str, ref: Any, row: object) -> bool:
        """A menu row such as Item > Labels...: the sheet at its page. False if none."""
        where = PAGE_FOR_VERB.get(verb)
        if where is None:
            return False
        chosen = self.frame.selected_indices() if self.frame is not None else []
        rows = [self.frame.rows[i] for i in chosen] if chosen else ([row] if row else [])
        self.open_properties(ref, rows, where[0])
        return True

    def _view_options(self, ref: Any) -> None:
        frame = self.frame
        node = frame.node(ref)
        from quill.core.workbench.filters import describe

        words = (
            f"{node.label}: a place, not an object, so its Properties are the view's options. "
            f"Columns: {', '.join(frame._columns) or 'name'}. Filter: {describe(frame.query)}. "
            "View, Sort and Columns change them; F5 refreshes."
        )
        frame.details.ChangeValue(words)
        frame.details.SetFocus()

    def _context(self, target: Target, loaded: Loaded) -> Any:
        return context_for(
            loaded.values,
            loaded.viewer,
            signed_in=bool(getattr(self.items, "is_authenticated", False)),
            login=self.account_name(),
            scopes=self.token_scopes(),
            level=self.access_level(),
            where=target.ident.get("repo", "") or target.ident.get("org", ""),
        )

    def _open_one(self, target: Target, page: str = "") -> None:
        api = self.github_api()
        sheet = target.sheet

        def work() -> tuple[Loaded, dict[str, dict[str, object]]]:
            return load(api, sheet, target.ident), load_options(api, sheet, target.ident)

        self._background(
            f"load {target.title()}", work, lambda got: self._show_one(target, got[0], got[1], page)
        )

    def _show_one(
        self, target: Target, loaded: Loaded, choices: dict[str, dict[str, object]], page: str
    ) -> None:
        from quill.ui.workbench_properties_sheet import PropertiesSheet

        sheet = target.sheet
        state: dict[str, Any] = {"loaded": loaded, "ident": dict(target.ident)}
        holder: dict[str, Any] = {}

        def apply(changes: Sequence[FieldChange], close: bool) -> None:
            self._apply_one(target, state, changes, choices, holder["sheet"], close)

        def reload() -> None:
            def done(got: Loaded) -> None:
                state["loaded"] = got
                holder["sheet"].reloaded(got.values, f"Loaded at {time.strftime('%H:%M')}")

            self._background("reload", lambda: load(self.github_api(), sheet, state["ident"]), done)

        url = sheet.url(target.ident)
        view = PropertiesSheet(
            self.frame.frame,
            sheet.sheet,
            loaded.values,
            title=target.title(),
            copy_text=self.frame.copy_text,
            on_apply=apply if sheet.writes else None,
            locked=locked_fields(sheet, self._context(target, loaded)),
            choices={k: list(v) for k, v in choices.items()},
            on_create=lambda spec: self._create(target, spec, choices),
            on_table=self.table_action(target, state) if hasattr(self, "table_action") else None,
            on_reload=reload,
            open_web=(lambda: self._browse(url)) if url else None,
            copy_link=(lambda: self.frame.copy_text(url)) if url else None,
            start_page=page or LAST_PAGE.get(target.kind, ""),
            loaded_at=f"Loaded at {time.strftime('%H:%M')}"
            + (". Some pages need more access and are empty." if loaded.missing else ""),
        )
        holder["sheet"] = view
        try:
            view.show()
        finally:
            LAST_PAGE[target.kind] = view.page_key() if view.notebook else ""

    def _browse(self, url: str) -> None:
        import webbrowser

        if not webbrowser.open(url, new=2):
            self._say("Could not open this in your browser.")

    # -- saving ------------------------------------------------------------------

    def tier_of(self, target: Target, changes: Sequence[FieldChange]) -> WriteTier:
        tiers = [target.sheet.writes[c.key].tier for c in changes if c.key in target.sheet.writes]
        return max(tiers, default=WriteTier.ORGANIZING)

    def confirm_tier(self, tier: WriteTier, words: str, name: str) -> bool:
        """Tier 2: a preview in words; tier 3: the preview, then the name typed (18.4)."""
        if tier < WriteTier.ACCESS:
            return True
        frame = self.frame
        wx = frame._wx
        from quill.ui.dialog_contract import show_modal_dialog

        with wx.MessageDialog(
            frame.frame,
            words + "\n\nEnter goes ahead; Escape changes nothing.",
            "Preview",
            wx.OK | wx.CANCEL | wx.ICON_WARNING,
        ) as dialog:
            if show_modal_dialog(dialog, "Preview") != wx.ID_OK:
                return False
        if tier < WriteTier.DESTRUCTIVE:
            return True
        typed = self._ask_text(  # type: ignore[attr-defined]
            "Type to Confirm", f"This is hard to reverse. Type {name} to go ahead:"
        )
        if typed != name:
            if typed:
                self._say("The name did not match. Nothing changed.")
            return False
        return True

    def _apply_one(
        self,
        target: Target,
        state: dict[str, Any],
        changes: Sequence[FieldChange],
        choices: dict[str, dict[str, object]],
        view: Any,
        close: bool,
    ) -> None:
        tier = self.tier_of(target, changes)
        words = f"{target.title()}: " + "; ".join(f"{c.label} to {c.after}" for c in changes)
        name = target.ident.get("repo") or target.ident.get("name") or target.title()
        if not self.confirm_tier(tier, words, name):
            return
        self._save(target, state, changes, choices, view, close, frozenset(), True)

    def _save(
        self,
        target: Target,
        state: dict[str, Any],
        changes: Sequence[FieldChange],
        choices: dict[str, dict[str, object]],
        view: Any,
        close: bool,
        keep: frozenset[str],
        check: bool,
    ) -> None:
        from quill.core.github.sheet_engine import save

        api = self.github_api()
        sheet = target.sheet

        def work() -> SaveOutcome:
            return save(
                api,
                sheet,
                state["ident"],
                changes,
                loaded=state["loaded"].values,
                choices=choices,
                keep_theirs=keep,
                check_conflicts=check,
            )

        def done(outcome: SaveOutcome) -> None:
            if outcome.conflicts:
                theirs = self._choose_conflicts(outcome.conflicts)
                if theirs is None:
                    return
                self._save(target, state, changes, choices, view, close, theirs, False)
                return
            name = sheet.title(target.ident) or target.kind
            said = sentence(name, outcome)
            self._say(said)
            if outcome.done:
                self.record_change(target, outcome.done, said, outcome.ok)
            state["ident"] = sheet.ident_after(state["ident"], outcome.done)
            state["loaded"].values.update(outcome.after)
            view.saved(outcome.after, said, close=close and outcome.ok)

        self._background(f"save {target.title()}", work, done)

    def _choose_conflicts(self, found: Sequence[FieldChange]) -> frozenset[str] | None:
        """Keep Theirs or Use Mine, field by field. None is Cancel."""
        frame = self.frame
        wx = frame._wx
        from quill.ui.dialog_contract import show_modal_dialog

        theirs: set[str] = set()
        for change in found:
            question = (
                f"Changed on GitHub since you opened this: {change.label.lower()} is now "
                f"{change.before or 'empty'}. Yours is {change.after or 'empty'}."
            )
            with wx.MessageDialog(
                frame.frame, question, "Changed on GitHub", wx.YES_NO | wx.CANCEL
            ) as dialog:
                dialog.SetYesNoLabels("Keep &Theirs", "Use &Mine")
                answer = show_modal_dialog(dialog, "Changed on GitHub")
            if answer == wx.ID_CANCEL:
                return None
            if answer == wx.ID_YES:
                theirs.add(change.key)
        return frozenset(theirs)

    def _create(
        self, target: Target, spec: FieldSpec, choices: dict[str, dict[str, object]]
    ) -> str | None:
        """New Label..., New Milestone...: make it on GitHub and use it at once (GH-R-035)."""
        name = self._ask_text(spec.create.rstrip("."), f"{spec.create.rstrip('.')}: name")  # type: ignore[attr-defined]
        if not name:
            return None
        repo = target.ident.get("repo", "")
        path, body = {
            "labels": (f"/repos/{repo}/labels", {"name": name, "color": "ededed"}),
            "milestone": (f"/repos/{repo}/milestones", {"title": name}),
        }.get(spec.key, ("", {}))
        if not path:
            choices.setdefault(spec.key, {})[name] = name
            return name
        try:
            answer = self.github_api().rest("POST", path, body=body)
        except Exception as exc:  # noqa: BLE001
            self._say(f"Could not create {name}: {exc}")
            return None
        data = answer.data if isinstance(answer.data, dict) else {}
        choices.setdefault(spec.key, {})[name] = data.get("number", name)
        self._say(f"Created {name}.")
        return name

    # -- several at once -----------------------------------------------------------

    def _open_many(self, targets: list[Target]) -> None:
        api = self.github_api()
        sheet = targets[0].sheet

        def work() -> tuple[list[Loaded], dict[str, dict[str, object]]]:
            return [load(api, sheet, t.ident) for t in targets], load_options(
                api, sheet, targets[0].ident
            )

        self._background(
            f"load {len(targets)} objects",
            work,
            lambda got: self._show_many(targets, got[0], got[1]),
        )

    def _show_many(
        self, targets: list[Target], loads: list[Loaded], choices: dict[str, dict[str, object]]
    ) -> None:
        from quill.ui.workbench_properties_sheet import PropertiesSheet

        sheet = targets[0].sheet
        objects = [found.values for found in loads]
        merged = merge_values(objects)
        counts = {
            spec.key: list_states(objects, spec.key)
            for spec in sheet.sheet.fields()
            if spec.kind is FieldKind.CHECKLIST
        }
        locked: dict[str, str] = {}
        for target, found in zip(targets, loads, strict=True):
            locked.update(locked_fields(sheet, self._context(target, found)))
        noun = _NOUNS.get(sheet.kind, f"{sheet.sheet.title.lower()}s")
        items = [
            BatchItem(sheet.title(t.ident) or t.kind, t.ident, found.values)
            for t, found in zip(targets, loads, strict=True)
        ]
        holder: dict[str, Any] = {}

        def apply(changes: Sequence[FieldChange], close: bool) -> None:
            self._apply_many(sheet.kind, noun, items, changes, choices, holder["sheet"], close)

        view = PropertiesSheet(
            self.frame.frame,
            sheet.sheet,
            merged,
            title=f"Properties of {len(targets)} {noun}",
            copy_text=self.frame.copy_text,
            on_apply=apply,
            locked=locked,
            choices={k: list(v) for k, v in choices.items()},
            counts=counts,
            total=len(targets),
        )
        holder["sheet"] = view
        view.show()

    def _apply_many(
        self,
        kind: str,
        noun: str,
        items: list[BatchItem],
        changes: Sequence[FieldChange],
        choices: dict[str, dict[str, object]],
        view: Any,
        close: bool,
    ) -> None:
        from quill.core.github.batch import run

        words = preview(noun, items, changes)
        target = Target(kind, items[0].ident)
        tier = max(self.tier_of(target, changes), WriteTier.ACCESS)
        if not self.confirm_tier(tier, words, str(len(items))):
            return
        api = self.github_api()
        sheet = SHEETS[kind]

        def record(item: BatchItem, done: list[FieldChange]) -> None:
            self.record_change(
                Target(kind, item.ident), done, sentence(item.name, SaveOutcome(done)), True
            )

        def work() -> Any:
            return run(
                api,
                sheet,
                items,
                changes,
                choices=choices,
                pace=self.batch_pace,
                done=record,
            )

        def finished(results: Any) -> None:
            text = results_text(results)
            self._say(text.rsplit("\n", 1)[-1] + ".")
            failed = {r.name for r in results if r.status == "Failed"}
            again = [item for item in items if item.name in failed]

            def retry() -> None:
                self._apply_many(kind, noun, again, changes, choices, view, close)

            self.show_results(f"Changed {len(items)} {noun}", text, retry if again else None)
            view.saved({}, text.rsplit("\n", 1)[-1], close=close)

        self._background(f"change {len(items)} {noun}", work, finished)

    def show_results(self, title: str, text: str, retry: Callable[[], None] | None = None) -> None:
        """A result per item, as a list you can read and copy (never a message box)."""
        from quill.ui.github_workbench_results import show_results

        show_results(self.frame.frame, title, text, copy_text=self.frame.copy_text, retry=retry)
