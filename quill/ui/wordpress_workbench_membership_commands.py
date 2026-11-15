"""Paid Memberships Pro in the WordPress Workbench: members, access and discount codes.

Abilities first (``wp-abilities/v1``); where a site has none, PMPro's own
``pmpro/v1`` routes (:mod:`quill.core.wordpress.workbench_pmpro_rest`). Check
Membership Access and the discount codes use ``pmpro/v1`` always, because no
ability covers them. Has Access is also the member's Properties page
**Access** (Alt+Enter on a person, on a site with ``pmpro/v1``): Check a Post
or Page asks for one and the page says whether this member can see it.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from quill.core.wordpress import workbench_pmpro_change as pc
from quill.core.wordpress import workbench_pmpro_rest as pr
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.properties import FieldKind, FieldSpec, PageSpec, SheetSpec
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_workbench_dialogs as wdlg


def _read_memberships(api: Any, row: WbRow) -> list[dict[str, Any]]:
    """The person's current and past levels: the ability first, then ``pmpro/v1``."""
    from quill.core.wordpress.abilities import list_abilities, run_ability

    ability = next(
        (a for a in list_abilities(api) if a.name == "pmpro/member-memberships-get"), None
    )
    if ability is None or not ability.readonly:
        try:  # the older pmpro/v1 route: current levels only
            levels = pr.member_levels(api, row.object_id)
        except WordPressApiError:
            raise WordPressApiError(
                f"{row.site} exposes neither the Paid Memberships Pro "
                "member-memberships ability nor its pmpro/v1 routes."
            ) from None
        return [{**level, "status": level.get("status") or "active"} for level in levels]
    answer = run_ability(api, ability, {"user_id": row.object_id, "include_inactive": True})
    memberships = answer.get("memberships", []) if isinstance(answer, dict) else []
    return [pc.without_payment_details(i) for i in memberships if isinstance(i, dict)]


def _current(memberships: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [m for m in memberships if str(m.get("status") or "active").lower() == "active"]


def _level_name(level: dict[str, Any]) -> str:
    return str(level.get("name") or level.get("membership_name") or f"Level {level.get('id', '')}")


def _site_levels(api: Any) -> list[dict[str, Any]] | None:
    """Every level the site offers, through its read-only levels ability (None without one)."""
    from quill.core.wordpress.abilities import list_abilities, run_ability

    ability = next((a for a in list_abilities(api) if a.name == "pmpro/levels-query"), None)
    if ability is None or not ability.readonly:
        return None
    answer = run_ability(api, ability, {"limit": 50, "page": 1})
    items = answer.get("items", []) if isinstance(answer, dict) else []
    return [i for i in items if isinstance(i, dict) and i.get("id")]


_ACCESS = FieldSpec(
    "pmpro_access",
    "Can this member see it (Paid Memberships Pro)",
    FieldKind.MULTILINE,
    readonly=True,
    help="Paid Memberships Pro's answer for the post or page you check: whether this member "
    "can see it, and which levels would let them. Check a Post or Page asks for one.",
)

_ACCESS_FIRST = (
    "Choose Check a Post or Page, then type a post or page's number or words from its title. "
    "Paid Memberships Pro says whether this member can see it."
)

_ASK_POST = "&Post or page (its number, or words from its title):"
_ASK_HELP = (
    "The post or page to check. Paid Memberships Pro says whether this person may see it, "
    "and which levels would let them."
)


class WorkbenchMembershipCommands:
    # -- pmpro/v1: Change Membership Level and Cancel Membership (WP-C) ----------------

    def _membership_refused(self, verb: str, row: WbRow) -> bool:
        refusal = self.refusal_for(f"wordpress.workbench.{verb}", row)
        if refusal:
            self.say(refusal)
        return bool(refusal)

    def do_cancel_membership(self, _ref: Any, row: WbRow | None) -> None:
        """Cancel one level after a preview naming the subscription it stops. Every run."""
        if row is None or row.kind != "user" or self._membership_refused("cancel_membership", row):
            return
        api = self.ctx(row.site).api

        def read() -> tuple[Any, ...]:
            current = _current(_read_memberships(api, row))
            return current, pc.member_subscriptions(api, row.object_id)

        def chosen(found: tuple[Any, ...]) -> None:
            current, subscriptions = found
            if not current:
                self.say(f"{row.title} has no current membership on {row.site}.")
                return
            index = 0
            if len(current) > 1:
                picked = dlg.ask_choice(
                    self.parent,
                    self.show_modal,
                    title=f"Cancel Membership - {row.title}",
                    prompt="&Level to cancel:",
                    rows=[_level_name(level) for level in current],
                    help_text="The membership level that ends now.",
                )
                if picked is None:
                    return
                index = picked
            level = current[index]
            name = _level_name(level)
            if not wdlg.ask_preview(
                self.parent,
                self.show_modal,
                title="Cancel Membership",
                summary=f"Cancel {row.title}'s {name} membership on {row.site}.",
                lines=pc.cancel_preview(row.title, row.site, level, subscriptions),
                yes="Cancel Membership",
            ):
                return

            def done(_answer: Any) -> None:
                self.say(f"Cancelled {row.title}'s {name} membership on {row.site}.")
                self.refresh()

            self.background(
                f"cancelling {row.title}'s membership",
                lambda: pc.cancel_membership(api, row.object_id, int(level.get("id") or 0)),
                done,
            )

        self.background(f"reading {row.title}'s memberships", read, chosen)

    def do_change_membership(self, _ref: Any, row: WbRow | None) -> None:
        """Give another level after a preview of what ends and which payments stop. Every run."""
        if row is None or row.kind != "user" or self._membership_refused("change_membership", row):
            return
        api = self.ctx(row.site).api

        def read() -> tuple[Any, ...]:
            current = _current(_read_memberships(api, row))
            return current, _site_levels(api), pc.member_subscriptions(api, row.object_id)

        def chosen(found: tuple[Any, ...]) -> None:
            current, levels, subscriptions = found
            if levels:
                picked = dlg.ask_choice(
                    self.parent,
                    self.show_modal,
                    title=f"Change Membership Level - {row.title}",
                    prompt="&New level:",
                    rows=[f"{_level_name(level)} (level {level['id']})" for level in levels],
                    help_text="The level this person has from now on.",
                )
                if picked is None:
                    return
                new_level = levels[picked]
            else:
                typed = dlg.ask_text(
                    self.parent,
                    self.show_modal,
                    title=f"Change Membership Level - {row.title}",
                    prompt="&Level number:",
                    help_text="From Memberships > Membership Levels in wp-admin.",
                )
                if typed is None:
                    return
                if not typed.strip().isdigit():
                    self.say("A level is a number, so nothing changed.")
                    return
                new_level = {"id": int(typed.strip())}
            new_id = int(new_level["id"])
            name = _level_name(new_level)
            if any(str(level.get("id")) == str(new_id) for level in current):
                self.say(f"{row.title} already has {name}. Nothing changed.")
                return
            if not wdlg.ask_preview(
                self.parent,
                self.show_modal,
                title="Change Membership Level",
                summary=f"Give {row.title} {name} on {row.site}.",
                lines=pc.change_preview(row.title, row.site, current, new_level, subscriptions),
                yes="Change Level",
            ):
                return

            def done(_answer: Any) -> None:
                self.say(f"{row.title} now has {name} on {row.site}.")
                self.refresh()

            self.background(
                f"changing {row.title}'s membership",
                lambda: pc.change_membership(api, row.object_id, new_id),
                done,
            )

        self.background(f"reading {row.title}'s memberships", read, chosen)

    def do_pmpro_memberships(self, _ref: Any, row: WbRow | None) -> None:
        """Read the selected user's current and past Paid Memberships Pro levels."""
        if row is None or row.kind != "user":
            return
        api = self.ctx(row.site).api

        def read_memberships() -> list[dict[str, Any]]:
            return _read_memberships(api, row)

        def done(memberships: list[dict[str, Any]]) -> None:
            lines = []
            for membership in memberships:
                name = str(
                    membership.get("name")
                    or membership.get("membership_name")
                    or f"Level {membership.get('id', '')}"
                )
                status = str(membership.get("status") or "unknown").replace("_", " ")
                start = str(membership.get("startdate") or "")
                end = str(membership.get("enddate") or "")
                dates = ", ".join(
                    value
                    for value in (f"started {start}" if start else "", f"ends {end}" if end else "")
                    if value
                )
                lines.append(f"{name}: {status}" + (f", {dates}" if dates else ""))
            text = "\n".join(lines) or "No current or past memberships were returned."
            dlg.show_report(
                self.parent,
                self.show_modal,
                title=f"Paid Memberships Pro - {row.title}",
                text=text,
                help_text=(
                    "Current and past membership levels returned by the site. Payment card "
                    "details are not included."
                ),
            )

        self.background(f"reading memberships for {row.title}", read_memberships, done)

    # -- pmpro/v1: Has Access ---------------------------------------------------------

    def do_check_access(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "user":
            return
        answer = dlg.ask_text(
            self.parent,
            self.show_modal,
            title=f"Check Membership Access - {row.title}",
            prompt=_ASK_POST,
            help_text=_ASK_HELP,
        )
        if not answer or not answer.strip():
            return
        wanted = answer.strip()
        self.background(
            f"checking {row.title}'s access",
            lambda: self._pmpro_access_sentence(row, wanted),
            self.say,
        )

    def _pmpro_access_sentence(self, row: WbRow, wanted: str) -> str:
        """Off the UI thread: PMPro's answer for *wanted* (a number or title words)."""
        api = self.ctx(row.site).api
        post_id, name = (int(wanted), f"item {wanted}") if wanted.isdigit() else (0, wanted)
        if not post_id:
            found = api.get("wp/v2/search", search=wanted, per_page=1)
            first = found[0] if isinstance(found, list) and found else None
            if not isinstance(first, dict) or not first.get("id"):
                raise WordPressApiError(f"Nothing on {row.site} matches {wanted}.")
            post_id, name = int(first["id"]), str(first.get("title") or wanted)
        return pr.has_access(api, row.object_id, post_id).sentence(row.title, name, row.site)

    # -- the member's Access page (Properties) -------------------------------------------

    def with_access_page(self, ctx: Any, sheet: SheetSpec, values: dict[str, Any]) -> SheetSpec:
        """A person's sheet with an Access page, on a site with Paid Memberships Pro's routes."""
        info = getattr(ctx, "info", None)
        if info is None or not info.supports("pmpro/v1"):
            return sheet
        values["pmpro_access"] = _ACCESS_FIRST
        return replace(sheet, pages=(*sheet.pages, PageSpec("access", "Access", (_ACCESS,))))

    def access_buttons(self, row: WbRow) -> dict[str, Any]:
        """The Access page's Check a Post or Page: only a read, so read-only sheets have it too."""
        from quill.ui.workbench_sheet_editor import FieldButton

        def run(setter: Any, _text: str) -> None:
            answer = dlg.ask_text(
                self.parent,
                self.show_modal,
                title=f"Check Membership Access - {row.title}",
                prompt=_ASK_POST,
                help_text=_ASK_HELP,
            )
            if not answer or not answer.strip():
                return
            wanted = answer.strip()
            # The answer lands in the page's box; a failure is said by the window.
            self.background(
                f"checking {row.title}'s access",
                lambda: self._pmpro_access_sentence(row, wanted),
                setter,
            )

        help_text = "Ask Paid Memberships Pro whether this member can see a post or page."
        return {"pmpro_access": (FieldButton("&Check a Post or Page...", help_text, run, True),)}

    # -- pmpro/v1: discount codes -----------------------------------------------------

    def _discount_site(self, ref: Any, row: WbRow | None) -> str:
        return (row.site if row is not None else "") or self.site_of(ref)

    def do_look_up_discount(self, ref: Any, row: WbRow | None) -> None:
        site = self._discount_site(ref, row)
        if not site:
            return
        code = dlg.ask_text(
            self.parent,
            self.show_modal,
            title="Look Up a Discount Code",
            prompt="&Code:",
            help_text="The discount code exactly as members type it.",
        )
        if not code or not code.strip():
            return
        api = self.ctx(site).api

        def done(raw: dict[str, Any]) -> None:
            self.say(pr.discount_row(site, raw).detail)

        self.background(
            f"reading discount code {code.strip()}",
            lambda: pr.read_discount_code(api, code.strip()),
            done,
        )

    def do_new_discount_code(self, ref: Any, row: WbRow | None) -> None:
        site = self._discount_site(ref, row)
        if not site:
            return
        answers: list[str] = []
        for prompt, help_text in (
            ("&Code:", "What members type at checkout, such as SPRING. Letters and numbers."),
            ("&Level numbers (a comma between):", "From Memberships > Membership Levels."),
            ("&Initial payment with the code:", "The price at checkout, such as 10.00, or 0."),
            ("&How many uses (0 for unlimited):", "How many times the code may be used."),
            ("&Expires (YYYY-MM-DD, or blank for never):", "The last day the code works."),
        ):
            text = dlg.ask_text(
                self.parent,
                self.show_modal,
                title="New Discount Code",
                prompt=prompt,
                help_text=help_text,
            )
            if text is None:
                return
            answers.append(text.strip())
        code, levels_text, payment, uses_text, expires = answers
        levels = tuple(int(p) for p in levels_text.replace(" ", "").split(",") if p.isdigit())
        if not code or not levels:
            self.say("A discount code needs a code and at least one level, so nothing was made.")
            return
        spec = pr.DiscountSpec(
            code=code.upper(),
            levels=levels,
            initial_payment=payment or "0",
            uses=int(uses_text) if uses_text.isdigit() else 0,
            expires=expires,
        )
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title="New Discount Code",
            summary=f"Paid Memberships Pro on {site} gets this discount code.",
            lines=pr.discount_preview(spec, site, {}),
            yes="Make the Code",
        ):
            return
        api = self.ctx(site).api

        def done(_raw: object) -> None:
            self.say(f"Made the discount code {spec.code} on {site}.")
            self.refresh()

        self.background(
            f"making discount code {spec.code}", lambda: pr.create_discount_code(api, spec), done
        )
