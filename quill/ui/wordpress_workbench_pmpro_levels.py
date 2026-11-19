"""New Membership Level... and Edit Membership Level... (complete.md 2.3, Memberships).

The Workbench side of :mod:`quill.core.wordpress.workbench_pmpro_levels`: the
level's name, prices, billing period, expiry and whether new signups are
allowed, asked one at a time, previewed, sent to ``pmpro/v1/membership_level``
and kept as a step in Change History. A new level is undone by deleting it, a
change by sending the old settings back.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.wordpress import workbench_pmpro_levels as lv
from quill.core.wordpress.workbench_rows import WbRow
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_workbench_dialogs as wdlg

__all__ = ["WorkbenchPmproLevels"]


class WorkbenchPmproLevels:
    """Mixed into the membership commands; the provider supplies ctx, background and say."""

    parent: Any
    say: Callable[[str], None]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    step: Callable[..., None]
    refresh: Callable[[], None]
    show_modal: Callable[[Any, str], int]
    site_of: Callable[[Any], str]

    def _level_text(self, title: str, prompt: str, value: str, help_text: str) -> str | None:
        return dlg.ask_text(
            self.parent,
            self.show_modal,
            title=title,
            prompt=prompt,
            value=value,
            help_text=help_text,
        )

    def _level_choice(self, title: str, prompt: str, rows: list[str], initial: int) -> int | None:
        return dlg.ask_choice(
            self.parent,
            self.show_modal,
            title=title,
            prompt=prompt,
            rows=rows,
            initial=initial,
            help_text="",
        )

    def _ask_level(self, title: str, old: lv.LevelSpec) -> lv.LevelSpec | None:
        name = self._level_text(title, "&Name:", old.name, "Such as Gold or Supporter.")
        if name is None:
            return None
        initial = self._level_text(
            title, "&Initial payment:", old.initial_payment, "Paid at signup; 0 for free."
        )
        if initial is None:
            return None
        recurring = self._level_text(
            title, "&Recurring payment:", old.billing_amount, "Paid each period; 0 for none."
        )
        if recurring is None:
            return None
        try:
            initial, recurring = (
                lv.money(initial, "initial payment"),
                lv.money(recurring, "recurring payment"),
            )
        except lv.LevelValueError as exc:
            self.say(f"{exc} Nothing was changed.")
            return None
        cycle_number, cycle_period = old.cycle_number, old.cycle_period
        if float(recurring) > 0:
            every = self._level_text(title, "Every how &many:", str(old.cycle_number), "Such as 1.")
            if every is None:
                return None
            period = self._level_choice(
                title, "&Period:", list(lv.PERIODS), lv.PERIODS.index(old.cycle_period)
            )
            if period is None:
                return None
            cycle_number = int(every) if every.strip().isdigit() and int(every) > 0 else 1
            cycle_period = lv.PERIODS[period]
        expires = self._level_text(
            title,
            "&Expires after how many (0 for never):",
            str(old.expiration_number),
            "Membership ends after this many periods.",
        )
        if expires is None:
            return None
        expiry_number = int(expires) if expires.strip().isdigit() else 0
        expiry_period = old.expiration_period
        if expiry_number:
            picked = self._level_choice(
                title, "Expiry &period:", list(lv.PERIODS), lv.PERIODS.index(old.expiration_period)
            )
            if picked is None:
                return None
            expiry_period = lv.PERIODS[picked]
        signups = self._level_choice(
            title, "New &signups:", ["Allowed", "Not allowed"], 0 if old.allow_signups else 1
        )
        if signups is None:
            return None
        return lv.LevelSpec(
            name.strip(),
            old.description,
            initial,
            recurring,
            cycle_number,
            cycle_period,
            old.billing_limit,
            expiry_number,
            expiry_period,
            signups == 0,
        )

    def do_new_membership_level(self, ref: Any, row: WbRow | None) -> None:
        site = (row.site if row is not None else "") or self.site_of(ref)
        if not site:
            return
        spec = self._ask_level("New Membership Level", lv.LevelSpec(""))
        if spec is None:
            return
        try:
            body = lv.level_body(spec)
        except lv.LevelValueError as exc:
            self.say(f"{exc} Nothing was made.")
            return
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title="New Membership Level",
            summary=f"Make the membership level {spec.name} on {site}.",
            lines=lv.level_preview(spec, site),
            yes="Make Level",
        ):
            return
        api = self.ctx(site).api

        def done(answer: Any) -> None:
            made = int((answer or {}).get("id") or 0) if isinstance(answer, dict) else 0
            said = f"Made the membership level {spec.name} on {site}."

            def undo() -> str:
                api.delete(lv.LEVEL_ROUTE, id=made)
                return f"The membership level {spec.name} on {site} is deleted again."

            self.say(said)
            self.step(site, said.rstrip("."), undo if made else None)
            self.refresh()

        self.background("making a membership level", lambda: api.post(lv.LEVEL_ROUTE, body), done)

    def do_edit_membership_level(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "pmpro" or row.subkind != "level" or not row.object_id:
            self.say("Select a membership level first, in Membership Levels.")
            return
        try:
            old = lv.level_from(row.raw)
        except lv.LevelValueError as exc:
            self.say(str(exc))
            return
        title = f"Edit Membership Level - {old.name}"
        spec = self._ask_level(title, old)
        if spec is None:
            return
        if lv.unchanged(spec, old):
            self.say(f"Nothing about {old.name} would change.")
            return
        try:
            body = lv.level_body(spec, row.object_id)
            back = lv.level_body(old, row.object_id)
        except lv.LevelValueError as exc:
            self.say(f"{exc} Nothing was changed.")
            return
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title=title,
            summary=f"Change the membership level {old.name} on {row.site}.",
            lines=lv.level_preview(spec, row.site, old),
            yes="Save Level",
        ):
            return
        api = self.ctx(row.site).api
        said = f"Saved the membership level {spec.name} on {row.site}."

        def undo() -> str:
            api.post(lv.LEVEL_ROUTE, back)
            return f"The membership level {old.name} on {row.site} is as it was."

        def done(_answer: Any) -> None:
            self.say(said)
            self.step(row.site, said.rstrip("."), undo)
            self.refresh()

        self.background("saving a membership level", lambda: api.post(lv.LEVEL_ROUTE, body), done)
