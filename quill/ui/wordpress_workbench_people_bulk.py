"""People in the WordPress Workbench, the rest of wp-admin's Users screens (9.18, package 5).

A mixin on :class:`quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`,
ahead of :class:`~quill.ui.wordpress_workbench_people.WorkbenchPeopleCommands`
in its bases, so Change Role and Remove on one person stay that mixin's:

- **Change Role and Remove on several people**: wp-admin's bulk "Change role
  to..." and Delete. Every person is checked by the self-lockout guards against
  the site's list as it will be after the ones before; the preview names who is
  left out and why; the send says each that failed. A role change is undone
  with Ctrl+Z; a removal cannot be, which the confirmation says.
- **Add a Person** (New Here in Users): wp-admin's Add New User as one sheet,
  previewed, saying that REST sends no email.
- **Set New Password** on a person: a strong one offered, shown as text the
  way wp-admin shows it, previewed, sent once, never said or kept.
- **Your Profile** (Site menu, Ctrl+Alt+Shift+P): your own sheet on
  ``wp/v2/users/me``, without the Role page, so nobody demotes themselves here.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from quill.core.wordpress import site_admin as admin
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.workbench_edit import EditRefused
from quill.core.wordpress.workbench_moderation import version_of
from quill.core.wordpress.workbench_people import people
from quill.core.wordpress.workbench_people_bulk import (
    NEW_USER_SHEET,
    PASSWORD_NOTE,
    change_roles,
    new_user_body,
    new_user_preview,
    password_problem,
    plan_lines,
    remove_each,
    remove_plan,
    role_plan,
    set_password,
)
from quill.core.wordpress.workbench_permissions import ROLE_ORDER
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.history import Change
from quill.core.workbench.properties import SheetSpec, SheetState
from quill.ui import wordpress_dialogs as dlg

__all__ = ["WorkbenchPeopleBulkCommands"]

_ROLE_WORDS = dict(admin.ROLES)


def _names(rows: Sequence[WbRow]) -> str:
    shown = ", ".join(r.title for r in rows[:10])
    return shown + (f" and {len(rows) - 10} more" if len(rows) > 10 else "")


def _people(count: int) -> str:
    return f"{count} {'person' if count == 1 else 'people'}"


class WorkbenchPeopleBulkCommands:
    """Bulk Change Role and Remove, Add a Person, Set New Password and Your Profile."""

    parent: Any
    history: Any
    say: Callable[[str], None]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    ensure: Callable[[Any], Any]
    show_modal: Callable[[Any, str], int]
    refresh: Callable[[], None]
    site_of: Callable[[Any], str]
    current_site: Callable[[], str]
    selected_rows: Callable[[], list[WbRow]]

    def _people_rows(self, row: WbRow | None) -> list[WbRow]:
        rows = self.selected_rows() or ([row] if row is not None else [])
        return [r for r in rows if r.kind == "user"]

    def _confirm(self, title: str, message: str, yes: str) -> bool:
        return bool(
            dlg.confirm(self.parent, self.show_modal, title=title, message=message, yes_label=yes)
        )

    # -- Change Role, several at once ---------------------------------------------

    def do_change_role(self, ref: Any, row: WbRow | None) -> None:
        rows = self._people_rows(row)
        if len(rows) <= 1:
            super().do_change_role(ref, row)  # type: ignore[misc]
            return
        site = rows[0].site
        if any(r.site != site for r in rows):
            self.say("Change roles on one site at a time.")
            return
        index = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title=f"Change Role for {_people(len(rows))}",
            prompt="&Role:",
            rows=[_ROLE_WORDS[r] for r in ROLE_ORDER],
            help_text="What these people may do on the site. Anyone the change would lock "
            "out is left as they are, and the preview says why.",
        )
        if index is None:
            return
        role = ROLE_ORDER[index]
        ctx = self.ctx(site)

        def plan() -> list[tuple[WbRow, str]]:
            return role_plan(self.ensure(ctx).account, rows, role, people(ctx.api))

        def previewed(found: list[tuple[WbRow, str]]) -> None:
            going, left = plan_lines(found)
            if not going:
                self.say(f"Nobody selected changes: {'; '.join(left[:3])}.")
                return
            message = f"Make {_people(len(going))} {_ROLE_WORDS[role]} on {site}? {_names(going)}."
            if left:
                message += f"\nLeft as they are: {'; '.join(left)}."
            if not self._confirm("Change Role", message, "Change Role"):
                return
            old = {r.key: r.status for r in going}

            def done(answer: tuple[list[WbRow], list[str]]) -> None:
                changed, failed = answer
                said = f"{_people(len(changed))} now {_ROLE_WORDS[role]} on {site}."
                if failed:
                    said += f" Not changed: {'; '.join(failed[:3])}."
                self.say(said)
                undo = None
                if changed:
                    undo = lambda: (  # noqa: E731
                        [
                            admin.update_user(ctx.api, r.object_id, roles=[old[r.key]])
                            for r in changed
                            if old[r.key]
                        ],
                        f"Put {_people(len(changed))} back in their old roles.",
                    )[1]
                self.history.record(Change(f"Roles on {site}", said, undo=undo))
                self.refresh()

            self.background("changing roles", lambda: change_roles(ctx.api, going, role), done)

        self.background("checking who can change", plan, previewed)

    # -- Remove, several at once --------------------------------------------------

    def do_remove_user(self, ref: Any, row: WbRow | None) -> None:
        rows = self._people_rows(row)
        if len(rows) <= 1:
            super().do_remove_user(ref, row)  # type: ignore[misc]
            return
        site = rows[0].site
        ctx = self.ctx(site)
        chosen_ids = {r.object_id for r in rows}

        def chosen(everyone: list[dict[str, Any]]) -> None:
            others = [p for p in everyone if int(p.get("id", 0)) not in chosen_ids]
            if not others:
                self.say("There is nobody left to give these people's posts to.")
                return
            index = dlg.ask_choice(
                self.parent,
                self.show_modal,
                title=f"Remove {_people(len(rows))}",
                prompt="&Give their posts to:",
                rows=[str(p.get("name", "")) for p in others],
                help_text="WordPress needs someone to own what these people wrote.",
            )
            if index is None:
                return
            to_id, to_name = int(others[index].get("id", 0)), str(others[index].get("name", ""))

            def plan() -> tuple[list[WbRow], list[str], int]:
                found = remove_plan(self.ensure(ctx).account, rows, to_id, everyone)
                going, left = plan_lines(found)
                moving = sum(admin.post_count(ctx.api, r.object_id) for r in going)
                return going, left, moving

            self.background(
                "counting posts",
                plan,
                lambda found: self._confirm_removal(site, to_id, to_name, *found),
            )

        self.background("reading people", lambda: people(ctx.api), chosen)

    def _confirm_removal(
        self, site: str, to_id: int, to_name: str, going: list[WbRow], left: list[str], moving: int
    ) -> None:
        if not going:
            self.say(f"Nobody selected can be removed: {'; '.join(left[:3])}.")
            return
        noun = "post moves" if moving == 1 else "posts move"
        message = (
            f"Remove {_people(len(going))} from {site}? {_names(going)}. {moving} {noun} to "
            f"{to_name}. This cannot be undone."
        )
        if left:
            message += f"\nKept: {'; '.join(left)}."
        if not self._confirm("Remove", message, "Remove"):
            return
        api = self.ctx(site).api

        def done(answer: tuple[list[WbRow], list[str]]) -> None:
            removed, failed = answer
            said = f"Removed {_people(len(removed))} from {site}; their posts are {to_name}'s."
            if failed:
                said += f" Not removed: {'; '.join(failed[:3])}."
            self.say(said + " This cannot be undone.")
            self.history.record(Change(f"People on {site}", said))
            self.refresh()

        self.background("removing people", lambda: remove_each(api, going, to_id), done)

    # -- Add a Person -------------------------------------------------------------

    def add_person(self, site: str) -> None:
        """wp-admin's Add New User as one sheet; Save previews, then sends."""
        api = self.ctx(site).api

        def on_save(state: SheetState) -> bool:
            try:
                body = new_user_body({**state.loaded, **state.edited})
            except EditRefused as exc:
                self.say(str(exc.args[0]))
                return False
            if not self._confirm("Add a Person", new_user_preview(body, site), "Add"):
                return False

            def done(user: Any) -> None:
                said = f"Added {user.name or body['username']} to {site}."
                self.say(said)
                self.history.record(Change(body["username"], said))
                self.refresh()

            self.background(
                "adding a person",
                lambda: admin.user_from_payload(api.post("wp/v2/users", body, context="edit")),
                done,
            )
            return True

        self._editor(  # type: ignore[attr-defined]
            NEW_USER_SHEET, {"roles": "subscriber"}, title=f"Add a Person - {site}", on_save=on_save
        ).show()

    # -- Set New Password ---------------------------------------------------------

    def do_set_password(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "user":
            self.say("Set New Password works on a person.")
            return
        text = dlg.ask_text(
            self.parent,
            self.show_modal,
            title=f"Set New Password for {row.title}",
            prompt="&New password:",
            value=admin.generated_password(),
            help_text="A strong password is offered; change it if you like. " + PASSWORD_NOTE,
        )
        if text is None:
            return
        problem = password_problem(text)
        if problem:
            self.say(problem)
            return
        ctx = self.ctx(row.site)
        account = ctx.account
        yours = account is not None and row.object_id == account.id
        message = (
            f"Set a new password for {row.title} on {row.site}? Their old one stops working "
            "at once and their browser sign-ins end. Application passwords keep working. "
            "WordPress sends no email for this, so give it to them yourself. It cannot be "
            "put back."
        )
        if yours:
            message += " This is your own account: QUILL keeps working, because it signs in "
            message += "with an application password."
        if not self._confirm("Set New Password", message, "Set Password"):
            return

        def done(_none: object) -> None:
            said = f"New password set for {row.title} on {row.site}."
            self.say(said)
            self.history.record(Change(row.title, said))

        self.background(
            "setting a password", lambda: set_password(ctx.api, row.object_id, text), done
        )

    # -- Your Profile -------------------------------------------------------------

    def do_your_profile(self, ref: Any, _row: WbRow | None) -> None:
        site = self.site_of(ref) or self.current_site()
        if not site:
            self.say("Choose a site first.")
            return
        ctx = self.ctx(site)

        def work() -> tuple[WbRow, Any]:
            account = self.ensure(ctx).account
            if account is None:
                raise WordPressApiError(f"{site} has not said who you are yet.")
            me = WbRow(
                "user",
                site,
                str(account.id),
                {"name": account.name, "username": account.username},
                f"{account.name}, you.",
                route="wp/v2/users/me",
                status=account.roles[0] if account.roles else "",
                subkind="user",
            )
            return me, self._load_sheet(me)  # type: ignore[attr-defined]

        def shown(answer: tuple[WbRow, Any]) -> None:
            me, (sheet, values, fresh, names, meta) = answer
            mine = SheetSpec(
                sheet.kind, "Your Profile", tuple(p for p in sheet.pages if p.key != "role")
            )
            locked, can_save = self._locked(mine, me)  # type: ignore[attr-defined]
            loaded = version_of("user", fresh)

            def on_save(state: SheetState) -> bool:
                return bool(
                    self._save_one(mine, me, state, fresh, names, meta, loaded)  # type: ignore[attr-defined]
                )

            self._editor(  # type: ignore[attr-defined]
                mine,
                values,
                title=f"Your Profile - {site}",
                on_save=on_save if can_save else None,
                locked=locked,
            ).show()

        self.background("reading your profile", work, shown)
