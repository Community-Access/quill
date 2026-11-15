"""Roles through a role plugin, and Who Has Never Signed In, in the WordPress Workbench (15.11).

A mixin on :class:`quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`,
ahead of :class:`~quill.ui.wordpress_workbench_lists.WorkbenchListCommands`:

- **Roles and What They May Do** (Ctrl+Alt+R): on a site whose role plugin
  publishes REST routes for roles (:mod:`quill.core.wordpress.role_plugin`),
  each of the site's own roles is listed with its capabilities, and one can
  be changed (its capabilities edited one a line, then previewed: what it
  gains, what it loses) or a new role made. Ctrl+Z puts the old set back, or
  takes the new role away. On every other site this is the read-only report
  it always was.
- **Who Has Never Signed In**: only where the site gives sign-in times over
  REST; otherwise the sentence that says it does not, and what would.

Every request runs through ``self.background``; every outcome is one sentence.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.wordpress import role_plugin as rp
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.actions import Tier
from quill.core.workbench.history import Change
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_workbench_dialogs as wdlg

__all__ = ["WorkbenchRolesCommands"]

_NEW = "New Role..."


class WorkbenchRolesCommands:
    """Roles through a role plugin's REST routes, and who has never signed in."""

    history: Any
    parent: Any
    say: Callable[[str], None]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    ensure: Callable[[Any], Any]
    show_modal: Callable[[Any, str], int]
    site_of: Callable[[Any], str]
    current_site: Callable[[], str]
    write_refusal: Callable[[WbRow, Tier], str]

    def _roles_site(self, ref: Any, row: WbRow | None) -> str:
        return (row.site if row is not None else "") or self.site_of(ref) or self.current_site()

    # -- roles --------------------------------------------------------------------------

    def do_roles(self, ref: Any, row: WbRow | None) -> None:
        site = self._roles_site(ref, row)
        if not site:
            super().do_roles(ref, row)  # type: ignore[misc]
            return

        def work() -> tuple[str, list[rp.SiteRole]] | None:
            ctx = self.ensure(self.ctx(site))
            info = getattr(ctx, "info", None)
            namespace = rp.role_namespace(getattr(info, "namespaces", ()) or ())
            if not namespace:
                return None
            return namespace, rp.read_roles(ctx.api, namespace)

        def done(found: tuple[str, list[rp.SiteRole]] | None) -> None:
            if found is None:
                super(WorkbenchRolesCommands, self).do_roles(ref, row)  # type: ignore[misc]
                return
            self._choose_role(site, *found)

        self.background(f"reading {site}'s roles", work, done)

    def _choose_role(self, site: str, namespace: str, roles: list[rp.SiteRole]) -> None:
        plugin = rp.ROLE_NAMESPACES.get(namespace, namespace)
        index = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title=f"Roles on {site}",
            prompt="&Role:",
            rows=[r.line for r in roles] + [_NEW],
            help_text=(
                f"{site}'s own roles, read through {plugin}. Choose one to change what it may "
                "do, or New Role to make one. Every change is previewed first."
            ),
        )
        if index is None:
            return
        refused = self.write_refusal(WbRow("item", site, "0", {}, ""), Tier.WRITE)
        if refused:
            self.say(refused)
            return
        if index == len(roles):
            self._new_role(site, namespace, roles)
        else:
            self._change_role(site, namespace, roles[index])

    def _change_role(self, site: str, namespace: str, role: rp.SiteRole) -> None:
        text = dlg.ask_text(
            self.parent,
            self.show_modal,
            title=f"What {role.name} May Do",
            prompt="&Capabilities, one a line:",
            value="\n".join(sorted(role.capabilities)),
            multiline=True,
            help_text=(
                "Each capability the role has, one a line. Delete a line to take it away, add "
                "a line to give one. Nothing is sent before the preview."
            ),
        )
        if text is None:
            return
        wanted, bad = rp.parse_capabilities(text)
        if bad:
            self.say(f"{bad[0]} is not a capability name: lower-case letters, digits and _.")
            return
        plan = rp.plan_capabilities(
            role,
            [c for c in wanted if c not in role.capabilities],
            [c for c in role.capabilities if c not in wanted],
        )
        if plan.empty:
            self.say(f"{role.name} keeps what it may do; nothing changed.")
            return
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title=f"Change {role.name}",
            summary=(
                f"On {site}, {role.name} gains {len(plan.added)} and loses {len(plan.removed)} "
                "capabilities. Everyone with the role is affected at once. Ctrl+Z puts it back."
            ),
            lines=plan.lines(),
            yes="Change Role",
        ):
            return
        api = self.ctx(site).api

        def done(_answer: Any) -> None:
            said = f"{role.name} on {site} now has {len(plan.after)} capabilities."

            def undo() -> str:
                rp.save_capabilities(api, namespace, role.slug, plan.before)
                return f"{role.name} on {site} has its {len(plan.before)} capabilities back."

            self.history.record(Change(f"{site}: {role.name}", said, undo=undo))
            self.say(said)

        self.background(
            f"changing {role.name}",
            lambda: rp.save_capabilities(api, namespace, role.slug, plan.after),
            done,
        )

    def _new_role(self, site: str, namespace: str, roles: list[rp.SiteRole]) -> None:
        name = dlg.ask_text(
            self.parent,
            self.show_modal,
            title="New Role",
            prompt="Role &name:",
            help_text="Such as Volunteer. Its slug is made from the name.",
        )
        if not name or not name.strip():
            return
        slug = "_".join(name.strip().lower().split())
        why = rp.valid_slug(slug, (r.slug for r in roles))
        if why:
            self.say(why)
            return
        text = dlg.ask_text(
            self.parent,
            self.show_modal,
            title=f"What {name.strip()} May Do",
            prompt="&Capabilities, one a line:",
            value="read",
            multiline=True,
            help_text="Each capability the new role has, one a line, such as read or edit_posts.",
        )
        if text is None:
            return
        caps, bad = rp.parse_capabilities(text)
        if bad:
            self.say(f"{bad[0]} is not a capability name: lower-case letters, digits and _.")
            return
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title="New Role",
            summary=f"Make the role {name.strip()} ({slug}) on {site}. Ctrl+Z takes it away.",
            lines=[f"{name.strip()} may: {c}" for c in caps] or [f"{name.strip()} may do nothing"],
            yes="Make Role",
        ):
            return
        api = self.ctx(site).api
        title = name.strip()

        def done(_answer: Any) -> None:
            said = f"Made the role {title} on {site}, with {len(caps)} capabilities."

            def undo() -> str:
                rp.delete_role(api, namespace, slug)
                return f"Took the role {title} away from {site}."

            self.history.record(Change(f"{site}: {title}", said, undo=undo))
            self.say(said)

        self.background(
            f"making the role {title}",
            lambda: rp.create_role(api, namespace, slug, title, caps),
            done,
        )

    # -- who has never signed in ------------------------------------------------------

    def do_never_signed_in(self, ref: Any, row: WbRow | None) -> None:
        site = self._roles_site(ref, row)
        if not site:
            self.say("Choose a site's Users first.")
            return
        api = self.ctx(site).api

        def work() -> tuple[str, list[str]]:
            users = list(api.iter_collection("wp/v2/users", {"context": "edit"}, max_pages=20))
            return rp.never_signed_in(users)

        def done(found: tuple[str, list[str]]) -> None:
            source, names = found
            if not source:
                self.say(rp.NO_SIGN_IN_TIMES)
                return
            if not names:
                self.say(f"Everyone on {site} has signed in at least once.")
                return
            count = len(names)
            said = (
                f"{count} {'person has' if count == 1 else 'people have'} never signed in to "
                f"{site}, as its {source} field records it."
            )
            self.say(said)
            dlg.show_report(
                self.parent,
                self.show_modal,
                title=f"Never Signed In, {site}",
                text="\n".join([said, "", *names]),
                help_text="Each person with no sign-in recorded, one a line.",
            )

        self.background(f"reading who has signed in to {site}", work, done)
