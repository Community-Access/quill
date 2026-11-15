"""People > Users, the rest, in the WordPress Workbench (WP-G; core in workbench_people_admin).

A mixin on :class:`quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`
for three commands on a person's row:

- **Their Application Passwords...**: the person's passwords from
  ``wp/v2/users/{id}/application-passwords``, each with when it was made and
  last used; choosing one offers Revoke, confirmed by name.
- **Sign Out Everywhere...**: WordPress has no REST route for sessions, so
  this says so and opens the person's wp-admin screen.
- **Invite from a Spreadsheet...**: a CSV of email, role and name, previewed
  row by row (with every row left out and why), then one ``POST wp/v2/users``
  per person and one sentence for the outcome.

Every request runs through ``self.background``; every outcome is one sentence.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.wordpress import site_admin as admin
from quill.core.wordpress import workbench_people_admin as people
from quill.core.wordpress.workbench_permissions import revoke_refusal
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.actions import Tier
from quill.core.workbench.history import Change
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_workbench_dialogs as wdlg

__all__ = ["WorkbenchPeopleAdminCommands"]


class WorkbenchPeopleAdminCommands:
    """Others' application passwords, signing out everywhere, and invites from a CSV."""

    commands: Any
    history: Any
    parent: Any
    say: Callable[[str], None]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    ensure: Callable[[Any], Any]
    profile: Callable[[str], Any]
    show_modal: Callable[[Any, str], int]
    refresh: Callable[[], None]
    site_of: Callable[[Any], str]
    current_site: Callable[[], str]

    # -- their application passwords ---------------------------------------------------

    def do_user_app_passwords(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "user":
            self.say("Choose a person in Users first.")
            return
        ctx = self.ctx(row.site)
        user_id, name = int(row.key or 0), row.title
        signed_in: list[str] = []

        def work() -> list[Any]:
            account = self.ensure(ctx).account
            refusal = people.passwords_refusal(account, user_id, name, row.site)
            if refusal:
                raise PermissionError(refusal)
            if account is not None and account.id == user_id:
                signed_in.append(admin.current_password_uuid(ctx.api))
            return admin.list_app_passwords(ctx.api, str(user_id), name)

        def shown(passwords: list[Any]) -> None:
            if not passwords:
                self.say(f"{name} has no application passwords on {row.site}.")
                return
            index = dlg.ask_choice(
                self.parent,
                self.show_modal,
                title=f"Application Passwords for {name}",
                prompt="&Passwords:",
                rows=people.password_lines(passwords),
                help_text=(
                    f"{name}'s application passwords on {row.site}, with when each was made "
                    "and last used. OK offers to revoke the one chosen; Cancel only reads."
                ),
            )
            if index is None:
                return
            mine = bool(signed_in and signed_in[0]) and passwords[index].uuid == signed_in[0]
            refused = revoke_refusal(mine, row.site) or self.access_refusal(  # type: ignore[attr-defined]
                row.site, Tier.DESTRUCTIVE
            )
            if refused:
                self.say(refused)
                return
            self._revoke_theirs(row, passwords[index])

        self.background(f"reading {name}'s passwords", work, shown)

    def _revoke_theirs(self, row: WbRow, password: Any) -> None:
        name = row.title
        if not dlg.confirm(
            self.parent,
            self.show_modal,
            title="Revoke Application Password",
            message=(
                f"Revoke {password.name} for {name} on {row.site}? Whatever signs in with it "
                "stops working, and it cannot be brought back."
            ),
            yes_label="Revoke",
        ):
            return
        api = self.ctx(row.site).api

        def done(_none: object) -> None:
            said = f"Revoked {password.name} for {name} on {row.site}."
            self.say(said)
            self.history.record(Change(password.name, said))

        self.background(
            "revoking a password",
            lambda: admin.revoke_app_password(api, password.uuid, row.key),
            done,
        )

    # -- sign out everywhere -----------------------------------------------------------

    def do_sign_out_everywhere(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "user":
            self.say("Choose a person in Users first.")
            return
        profile = self.profile(row.site)
        account = self.ctx(row.site).account
        yourself = account is not None and str(account.id) == row.key
        address, sentence = people.sign_out_pointer(
            str(getattr(profile, "site_url", "") or ""),
            int(row.key or 0),
            row.title,
            yourself=yourself,
        )
        if not address:
            self.say(f"{people.SESSIONS_NOTE} {row.site} has no address QUILL knows.")
            return
        self.say(sentence)
        self.commands.host.open_in_browser(address)

    # -- invite from a spreadsheet -------------------------------------------------------

    def do_invite_spreadsheet(self, ref: Any, row: WbRow | None) -> None:
        site = (row.site if row is not None else "") or self.site_of(ref) or self.current_site()
        if not site:
            self.say("Choose a site's Users first.")
            return
        path = wdlg.choose_spreadsheet(
            self.parent, self.show_modal, title="Invite from a Spreadsheet"
        )
        if path is None:
            return
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError) as exc:
            self.say(f"Could not read {path.name}: {exc}. Save it from the spreadsheet as CSV.")
            return
        ctx = self.ctx(site)

        def plan() -> people.InvitePlan:
            emails, names = people.existing_people(ctx.api)
            return people.parse_invites(text, existing_emails=emails, existing_usernames=names)

        def previewed(found: people.InvitePlan) -> None:
            if not found.invites:
                problems = " ".join(found.problems[:3])
                self.say(f"Nobody in {path.name} can be added. {problems}".strip())
                return
            count = len(found.invites)
            if not wdlg.ask_preview(
                self.parent,
                self.show_modal,
                title="Invite from a Spreadsheet",
                summary=(
                    f"Add {count} {'person' if count == 1 else 'people'} to {site}"
                    + (f"; {len(found.problems)} rows left out" if found.problems else "")
                    + f". {people.INVITE_NOTE}"
                ),
                lines=people.preview_lines(found),
                yes=f"Add {count}",
            ):
                return
            self._send_invites(site, found)

        self.background(f"reading people on {site}", plan, previewed)

    def _send_invites(self, site: str, found: people.InvitePlan) -> None:
        api = self.ctx(site).api

        def done(results: list[tuple[people.Invite, str]]) -> None:
            made = [invite for invite, why in results if not why]
            failed = [(invite, why) for invite, why in results if why]
            said = f"Added {len(made)} of {len(results)} people to {site}."
            if failed:
                first, why = failed[0]
                said += f" {len(failed)} failed; the first, {first.email}: {why}"
            self.say(said)
            self.history.record(Change(f"Invites on {site}", said))
            self.refresh()

        self.background(
            f"adding people to {site}", lambda: people.send_invites(api, found.invites), done
        )
