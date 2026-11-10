"""Users, Application Passwords, and Sign Out This Site (wordpress.md 9.10, 9.13).

A mixin of :class:`~quill.ui.wordpress_commands.WordPressCommands`, gathered
by :class:`~quill.ui.wordpress_admin_commands.WordPressAdminCommands`.
Passwords are never shown: a new user's is generated and thrown away (they
set their own with "Lost your password?"), and an application password is
only ever listed by name and revoked.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from quill.core.wordpress import site as wp
from quill.core.wordpress import site_admin as sa
from quill.core.wordpress import sites as st
from quill.ui import wordpress_dialogs as dlg
from quill.ui.wordpress_admin_base import WordPressAdminBase


class WordPressPeopleCommands(WordPressAdminBase):
    # ------------------------------------------------------------------ #
    # Users

    def cmd_users(self) -> None:
        if self.workbench_door("wordpress.users"):
            return  # the developer flag sends this door to the WordPress Workbench
        profile = self.admin_site("Users")
        if profile is None:
            return

        def work(api: Any, account: wp.Account) -> list[sa.User] | None:
            return sa.list_users(api) if sa.can(account, "users") else None

        def show(api: Any, account: wp.Account, users: list[sa.User] | None) -> None:
            if users is None:
                self.host.announce(
                    sa.cannot_sentence(profile.name, account, "users")
                    + " Your own profile is still yours to change."
                )
                self._my_profile(profile, api)
                return
            self._show_users(profile, api, account, users)

        self.admin_load(profile, f"reading users on {profile.name}", None, work, show)

    def _my_profile(self, profile: st.SiteProfile, api: Any) -> None:
        def ask(me: sa.User) -> None:
            fields: dict[str, object] = {}
            for key, label, help_text, multiline in (
                ("name", "&Display name:", "The name visitors see on your posts.", False),
                ("description", "&Biography:", "A few words about you for your author page.", True),
                ("url", "&Website:", "Your own website's address, if you want it shown.", False),
            ):
                value = dlg.ask_text(
                    self.host.parent,
                    self.host.show_modal,
                    title="My Profile",
                    prompt=label,
                    value=str(getattr(me, key)),
                    multiline=multiline,
                    help_text=help_text,
                )
                if value is None:
                    return
                if value.strip() != str(getattr(me, key)).strip():
                    fields[key] = value.strip()
            if not fields:
                return
            self.site_job(
                "saving your profile",
                lambda: sa.update_user(api, "me", **fields),
                lambda _u: f"Your profile on {profile.name} is saved.",
            )

        self.background(  # type: ignore[attr-defined]
            "reading your profile",
            lambda: sa.user_from_payload(api.get("wp/v2/users/me", context="edit")),
            ask,
        )

    def _show_users(
        self, profile: st.SiteProfile, api: Any, account: wp.Account, users: list[sa.User]
    ) -> None:
        live = list(users)

        def rows() -> list[str]:
            return [u.spoken() + (", you" if u.id == account.id else "") for u in live]

        def at(index: int | None) -> sa.User | None:
            return live[index] if index is not None and index < len(live) else None

        def pick_role(title: str, current: str = "") -> str | None:
            names = [label for _r, label in sa.ROLES]
            slugs = [r for r, _l in sa.ROLES]
            picked = dlg.ask_choice(
                self.host.parent,
                self.host.show_modal,
                title=title,
                prompt="&Role:",
                rows=names,
                initial=slugs.index(current) if current in slugs else 1,
                help_text=(
                    "A Subscriber can only read; a Contributor writes but cannot publish; an "
                    "Author publishes their own posts; an Editor publishes and manages everyone's; "
                    "an Administrator runs the whole site."
                ),
            )
            return None if picked is None else slugs[picked]

        def ask(title: str, prompt: str, help_text: str, value: str = "") -> str | None:
            answer = dlg.ask_text(
                self.host.parent,
                self.host.show_modal,
                title=title,
                prompt=prompt,
                value=value,
                help_text=help_text,
            )
            return answer.strip() if answer and answer.strip() else None

        def add(_index: int | None) -> object:
            username = ask(
                "Add User", "&Username:", "The name they sign in with. It cannot change later."
            )
            if username is None:
                return None
            email = ask("Add User", "&Email:", "Where WordPress sends their password reset link.")
            if email is None:
                return None
            name = ask("Add User", "&Name:", "Their name as visitors see it.", username) or username
            role = pick_role("Add User")
            if role is None:
                return None
            role_name = dict(sa.ROLES)[role]
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title="Add User",
                message=f"Add {name} ({username}) to {profile.name} as {role_name}?",
                yes_label=f"Add {name}",
            ):
                return None

            def done(user: sa.User) -> None:
                live.append(user)
                self.host.announce(
                    f"{user.name} added to {profile.name} as {role_name}. They choose their own "
                    "password with Lost your password on the sign-in page."
                )

            self.background(  # type: ignore[attr-defined]
                "adding a user",
                lambda: sa.add_user(api, username=username, email=email, name=name, role=role),
                done,
            )
            return None

        def edit(index: int | None) -> object:
            user = at(index)
            if user is None:
                return None
            name = ask(f"Edit {user.name}", "&Name:", "Their name as visitors see it.", user.name)
            if name is None:
                return None
            email = ask(f"Edit {user.name}", "&Email:", "Their email address.", user.email)
            if email is None:
                return None
            changed = {k: v for k, v in (("name", name), ("email", email)) if v != getattr(user, k)}
            if not changed:
                return None
            self.site_job(
                "saving a user",
                lambda: sa.update_user(api, user.id, **changed),
                lambda _u: f"{name} saved on {profile.name}.",
            )
            live[live.index(user)] = replace(user, name=name, email=email)
            return rows()

        def change_role(index: int | None) -> object:
            user = at(index)
            if user is None:
                return None
            if user.id == account.id:
                self.host.announce(
                    "You cannot change your own role from here: you could lock yourself out. "
                    "Ask another administrator."
                )
                return None
            role = pick_role(f"Role for {user.name}", user.roles[0] if user.roles else "")
            if role is None or (user.roles and role == user.roles[0]):
                return None
            role_name = dict(sa.ROLES)[role]
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title="Change Role",
                message=f"Make {user.name} {role_name} on {profile.name}?",
                yes_label=f"Make {role_name}",
            ):
                return None
            self.site_job(
                "changing a role",
                lambda: sa.update_user(api, user.id, roles=[role]),
                lambda _u: f"{user.name} is now {role_name} on {profile.name}.",
            )
            live[live.index(user)] = replace(user, roles=(role,))
            return rows()

        def delete(index: int | None) -> object:
            user = at(index)
            if user is None:
                return None
            if user.id == account.id:
                self.host.announce(
                    "You cannot delete your own account: the site would lose the person "
                    "managing it. Ask another administrator."
                )
                return None
            others = [u for u in live if u.id != user.id]
            picked = dlg.ask_choice(
                self.host.parent,
                self.host.show_modal,
                title=f"Delete {user.name}",
                prompt="&Give their posts and pages to:",
                rows=[u.spoken() for u in others],
                help_text="WordPress keeps everything they wrote, under the person you choose.",
            )
            if picked is None:
                return None
            heir = others[picked]

            def confirm_delete(count: int) -> None:
                if not dlg.confirm(
                    self.host.parent,
                    self.host.show_modal,
                    title="Delete User",
                    message=(
                        f"Delete {user.name} from {profile.name}? Their {count} posts move to "
                        f"{heir.name}. This cannot be undone."
                    ),
                    yes_label=f"Delete {user.name}",
                ):
                    return
                self.site_job(
                    "deleting a user",
                    lambda: sa.delete_user(api, user.id, heir.id),
                    lambda _r: f"{user.name} deleted; their posts are now {heir.name}'s.",
                )
                if user in live:
                    live.remove(user)

            self.background(
                "counting their posts", lambda: sa.post_count(api, user.id), confirm_delete
            )  # type: ignore[attr-defined]
            return None

        def passwords(index: int | None) -> object:
            user = at(index)
            if user is not None:
                self._load_app_passwords(profile, only=user)
            return None

        actions: list[dlg.Action] = []
        if sa.can(account, "add_user"):
            actions.append(
                dlg.Action("&Add User...", "Add a new account to the site.", add, needs_row=False)
            )
        if sa.can(account, "edit_users"):
            actions.append(
                dlg.Action("&Edit...", "Change the selected person's name and email.", edit)
            )
        if sa.can(account, "promote_users"):
            actions.append(
                dlg.Action(
                    "Change &Role...", "Change what the selected person may do.", change_role
                )
            )
        if sa.can(account, "delete_users"):
            actions.append(dlg.Action("De&lete...", "Delete the selected account.", delete))
        if sa.can(account, "edit_users"):
            actions.append(
                dlg.Action(
                    "Application &Passwords...",
                    "List and revoke the selected person's application passwords.",
                    passwords,
                )
            )
        actions.append(
            dlg.Action(
                "&My Profile...",
                "Your own display name, biography and website.",
                lambda _i: self._my_profile(profile, api),
                needs_row=False,
            )
        )
        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title=f"Users, {profile.name}",
            purpose=f"Everyone with an account on {profile.name}, and their role.",
            list_label="&Users:",
            list_help="Each person's name, username, role and email.",
            rows=rows(),
            actions=actions,
        )
        window.Destroy()

    # ------------------------------------------------------------------ #
    # Application Passwords

    def cmd_app_passwords(self) -> None:
        if self.workbench_door("wordpress.app_passwords"):
            return  # the developer flag sends this door to the WordPress Workbench
        profile = self.admin_site("Application Passwords")
        if profile is not None:
            self._load_app_passwords(profile)

    def _load_app_passwords(self, profile: st.SiteProfile, only: sa.User | None = None) -> None:
        def work(api: Any, account: wp.Account) -> tuple[str, list[sa.AppPassword]]:
            current = sa.current_password_uuid(api)
            if only is not None and only.id != account.id:
                return current, sa.list_app_passwords(api, str(only.id), only.name)
            found = sa.list_app_passwords(api, "me", account.name)
            if only is None and sa.can(account, "edit_users"):
                for user in sa.list_users(api):
                    if user.id != account.id:
                        found.extend(sa.list_app_passwords(api, str(user.id), user.name))
            return current, found

        self.admin_load(
            profile,
            f"reading application passwords on {profile.name}",
            None,
            work,
            lambda api, _account, data: self._show_app_passwords(profile, api, *data),
        )

    def _show_app_passwords(
        self, profile: st.SiteProfile, api: Any, current: str, found: list[sa.AppPassword]
    ) -> None:
        live = list(found)

        def rows() -> list[str]:
            return [p.spoken(current) for p in live]

        def revoke(index: int | None) -> object:
            if index is None or index >= len(live):
                return None
            entry = live[index]
            if entry.uuid == current:
                self.host.announce(
                    "That is the password this computer uses. Use Sign Out This Site to revoke it "
                    "and forget it here together."
                )
                return None
            whose = f"{entry.user_name}'s " if entry.user_name else ""
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title="Revoke Application Password",
                message=(
                    f"Revoke {whose}application password {entry.name} on {profile.name}? "
                    "Whatever app or computer uses it is signed out at once."
                ),
                yes_label=f"Revoke {entry.name}",
            ):
                return None
            user = str(entry.user_id) if entry.user_id else "me"
            self.site_job(
                "revoking a password",
                lambda: sa.revoke_app_password(api, entry.uuid, user),
                lambda _r: f"{entry.name} revoked on {profile.name}.",
            )
            live.remove(entry)
            return rows()

        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title=f"Application Passwords, {profile.name}",
            purpose=(
                f"The application passwords on {profile.name}: one per app or computer. Revoke "
                "one to shut off an old app or a lost laptop."
            ),
            list_label="&Passwords:",
            list_help="Each password's owner, name, when it was made and when it was last used.",
            rows=rows(),
            actions=[dlg.Action("&Revoke...", "Revoke the selected password.", revoke)],
        )
        window.Destroy()

    # ------------------------------------------------------------------ #
    # Sign Out This Site (9.10)

    def cmd_sign_out(self) -> None:
        store = self.need_site()  # type: ignore[attr-defined]
        if store is None:
            return
        profile = self.pick_site(store, "Sign Out This Site")  # type: ignore[attr-defined]
        if profile is None:
            return
        choice = dlg.ask_choice(
            self.host.parent,
            self.host.show_modal,
            title="Sign Out This Site",
            prompt="&After signing out:",
            rows=[
                f"Remove {profile.name} from QUILL",
                f"Keep {profile.name} in the list, to connect again later",
            ],
            help_text=(
                f"Signing out revokes QUILL's application password on {profile.name} itself and "
                "forgets it on this computer. Your local drafts are kept either way."
            ),
        )
        if choice is None:
            return
        remove = choice == 0
        api = self.api(profile)  # type: ignore[attr-defined]

        def work() -> str | None:
            # Exactly the password this computer signs with (introspect, 9.15).
            from quill.core.wordpress.site_features import which_password

            found = which_password(api) if profile.kind != "wpcom" else None
            if found is not None:
                sa.revoke_app_password(api, found.uuid)
            return None if found is None else found.name

        def done(name: str | None) -> None:
            revoked = name is not None
            st.forget_secret(profile.id)
            if remove:
                fresh = self.sites()  # type: ignore[attr-defined]
                fresh.remove(profile.id)
                self.save_sites(fresh)  # type: ignore[attr-defined]
            where = "revoked on the site and " if revoked else ""
            which = f" {name}" if name else ""
            kept = "removed from QUILL" if remove else "kept in your list"
            note = (
                ""
                if revoked
                else " The site did not say which password QUILL used, so revoke it in "
                "Application Passwords or the dashboard if you want it gone there too."
            )
            self.host.announce(
                f"Signed out of {profile.name}: the password{which} is {where}forgotten here, "
                f"and the site is {kept}.{note}"
            )

        self.background(f"signing out of {profile.name}", work, done)  # type: ignore[attr-defined]
