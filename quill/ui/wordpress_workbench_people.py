"""People, permissions and filters in the WordPress Workbench (PRD 10 and 11, W3 and W4).

A mixin on :class:`quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`.

- **Know before offering** (WP-R-010): :meth:`refusal_for` is checked before
  any command runs and before a context-menu row is enabled. It answers from
  Workbench access (Read Only, Organize, Full; Safe Mode and View As Role are
  Read Only), then from the site's capabilities, in one sentence that names
  the role that would allow it and the role you have.
- **People** (WP-R-011): Change Role and Remove, with the self-lockout guards
  of :mod:`~quill.core.wordpress.workbench_permissions` checked against the
  site's current list; Remove names who gets the posts and how many move.
- **Application passwords** (WP-R-012): New Here in Application Passwords
  makes one and shows its secret once, in a read-only box, never spoken by
  QUILL and never logged; Delete revokes one.
- **Filters** (WP-R-009): the Filter Builder, Show Only and Hide Like This, and
  Only Mine all write the one query in the filter box.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.wordpress import site_admin as admin
from quill.core.wordpress.workbench_actions import command as workbench_command
from quill.core.wordpress.workbench_people import (
    change_role,
    create_app_password,
    people,
    remove_preview,
    remove_user,
)
from quill.core.wordpress.workbench_permissions import (
    ROLE_ORDER,
    Access,
    account_as_role,
    capability_for,
    refusal,
    tier_allowed,
)
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.actions import Tier
from quill.core.workbench.filters import Condition, Operator, Query, render
from quill.ui import wordpress_dialogs as dlg

__all__ = ["WorkbenchPeopleCommands"]

_NODE_NEEDS = {
    "users": "list_users",
    "plugins": "activate_plugins",
    "settings": "manage_options",
    "themes": "switch_themes",
}

_EDIT_NEEDS = {
    "media": "upload_files",
    "comment": "moderate_comments",
    "term": "manage_categories",
    "user": "edit_users",
    "plugin": "activate_plugins",
    "setting": "manage_options",
    "form_entry": "edit_posts",
    "gravity_form": "gravityforms_create_form",
    "menu": "edit_theme_options",
    "template": "edit_theme_options",
    "pattern": "edit_posts",
    "font": "edit_theme_options",
    "sidebar": "edit_theme_options",
}

_BUILDER: dict[str, tuple[tuple[str, str], ...]] = {
    "items": (
        ("status", "Status"),
        ("author", "Author number"),
        ("category", "Category, by name or number"),
        ("tag", "Tag, by name or number"),
        ("after", "Published"),
        ("modified", "Last changed"),
        ("sticky", "Sticky, yes or no"),
        ("parent", "Parent number"),
        ("slug", "Slug"),
        ("search_columns", "Search in: post_title, post_content or post_excerpt"),
    ),
    "media": (
        ("type", "Kind: image, audio, video or application"),
        ("mime", "File type, such as image/png"),
        ("parent", "Attached to number"),
        ("author", "Uploaded by number"),
        ("after", "Uploaded"),
    ),
    "comments": (
        ("status", "Status: approve, hold, spam or trash"),
        ("post", "On the post number"),
        ("author_email", "Commenter's email"),
        ("after", "Written"),
    ),
    "users": (("role", "Role"),),
}

_ROLE_WORDS = dict(admin.ROLES)


class WorkbenchPeopleCommands:
    """Permissions, people, passwords, access, View As Role and the filter commands."""

    frame: Any
    actions: Any
    history: Any
    parent: Any
    safe_mode: bool
    view_as: dict[str, str]
    access_store: Any
    say: Callable[[str], None]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    ensure: Callable[[Any], Any]
    profile: Callable[[str], Any]
    show_modal: Callable[[Any, str], int]
    refresh: Callable[[], None]
    site_of: Callable[[Any], str]
    current_site: Callable[[], str]
    selected_rows: Callable[[], list[WbRow]]

    # -- permissions --------------------------------------------------------------

    def access_for(self, site: str) -> Access:
        if self.safe_mode or self.view_as.get(site):
            return Access.READ_ONLY
        profile = self.profile(site)
        return self.access_store.get(profile.id) if profile is not None else Access.FULL

    def account_for(self, site: str) -> Any:
        ctx = self.ctx(site) if site and self.profile(site) is not None else None
        account = ctx.account if ctx is not None else None
        role = self.view_as.get(site)
        return account_as_role(account, role) if account is not None and role else account

    def _access_sentence(self, site: str) -> str:
        if self.safe_mode:
            return "Safe Mode is on, so the Workbench only reads."
        if self.view_as.get(site):
            role = self.view_as[site].title()
            return (
                f"You are viewing {site} as {role}, which only reads. Site > View As Role ends it."
            )
        words = self.access_for(site).words
        return f"Workbench access on {site} is {words}. Site > Workbench Access changes it."

    def write_refusal(self, row: WbRow, tier: Tier) -> str:
        """Why a sheet save (or any *tier* change) to *row* is refused ("" when allowed)."""
        if not row.site:
            return ""
        if not tier_allowed(tier, self.access_for(row.site)):
            return self._access_sentence(row.site)
        account = self.account_for(row.site)
        if row.kind == "user" and account is not None and row.key == str(account.id):
            return ""
        if row.kind == "item":
            needed = "edit_pages" if row.subkind == "page" else "edit_posts"
        else:
            needed = _EDIT_NEEDS.get(row.kind, "")
        return refusal(needed, account, row.site) if account is not None else ""

    def refusal_for(self, command_id: str, row: WbRow | None) -> str:
        """Why *command_id* may not run on *row* now ("" when it may)."""
        if row is None or not row.site:
            return ""
        if command_id == workbench_command("change_gravity_field_type"):
            if row.kind != "gravity_form" or row.subkind != "gravity":
                return "This is not a Gravity Forms form. QAF fields are changed in Form Outline."
        kind = row.kind if row.kind in self.actions.row_types else "fact"
        action = next((a for a in self.actions.rows_for(kind) if a.command_id == command_id), None)
        if action is None:
            return ""
        tier = action.tier
        if row.kind == "ability" and command_id == workbench_command("run_ability"):
            if not row.raw.get("readonly", False):
                tier = Tier.DESTRUCTIVE if row.raw.get("destructive", False) else Tier.WRITE
        if not tier_allowed(tier, self.access_for(row.site)):
            return self._access_sentence(row.site)
        account = self.account_for(row.site)
        needed = capability_for(action, row.kind, row.subkind)
        return refusal(needed, account, row.site) if account is not None else ""

    def node_refusal(self, ref: Any, node: Any) -> str:
        site = self.site_of(ref)
        needed = _NODE_NEEDS.get(node.key, "")
        if not site or not needed:
            return ""
        account = self.account_for(site)
        return refusal(needed, account, site) if account is not None else ""

    def do_what_can_i_do(self, ref: Any, row: WbRow | None) -> None:
        site = (row.site if row is not None else "") or self.site_of(ref) or self.current_site()
        account = self.account_for(site) if site else None
        kind = row.kind if row is not None and row.kind in self.actions.row_types else "node"
        lines = []
        if account is not None:
            lines.append(f"You are {account.role_name} on {site}. {self._access_sentence(site)}")
        for action in self.actions.rows_for(kind):
            why = self.refusal_for(action.command_id, row) if row is not None else ""
            lines.append(f"{action.label}: {why or 'yes'}")
        dlg.show_report(
            self.parent,
            self.show_modal,
            title="What Can I Do Here?",
            text="\n".join(lines),
            help_text="What your role and the Workbench's access let you do with this row.",
        )

    def do_view_as(self, ref: Any, _row: WbRow | None) -> None:
        site = self.site_of(ref) or self.current_site()
        if not site:
            return
        rows = ["Myself, as I am", *(_ROLE_WORDS[r] for r in ROLE_ORDER)]
        index = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title="View As Role",
            prompt="&See the site as:",
            rows=rows,
            help_text="The Workbench greys and explains everything as this role would meet "
            "it. While you view as a role, nothing can be changed.",
        )
        if index is None:
            return
        if index == 0:
            self.view_as.pop(site, None)
            self.say(f"Viewing {site} as yourself again.")
        else:
            self.view_as[site] = ROLE_ORDER[index - 1]
            self.say(f"Viewing {site} as {rows[index]}. Nothing can be changed until you stop.")
        self.frame.status.refresh()

    def do_access(self, ref: Any, _row: WbRow | None) -> None:
        site = self.site_of(ref) or self.current_site()
        profile = self.profile(site) if site else None
        if profile is None:
            return
        choices = [
            ("Read Only: look, never change", Access.READ_ONLY),
            ("Organize: also Trash, Restore and moderate comments", Access.ORGANIZE),
            ("Full: everything your role allows", Access.FULL),
        ]
        current = self.access_store.get(profile.id)
        index = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title="Workbench Access",
            prompt=f"&How much may the Workbench change on {site}?",
            rows=[c[0] for c in choices],
            initial=[c[1] for c in choices].index(current),
            help_text="A limit on top of your role, kept for this site on this computer.",
        )
        if index is None:
            return
        self.access_store.set(profile.id, choices[index][1])
        self.say(f"Workbench access on {site} is {choices[index][1].words}.")
        self.frame.status.refresh()

    # -- people -------------------------------------------------------------------

    def do_change_role(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "user":
            return
        rows = [_ROLE_WORDS[r] for r in ROLE_ORDER]
        initial = ROLE_ORDER.index(row.status) if row.status in ROLE_ORDER else 0
        index = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title=f"Change Role for {row.title}",
            prompt="&Role:",
            rows=rows,
            initial=initial,
            help_text="What this person may do on the site.",
        )
        if index is None or ROLE_ORDER[index] == row.status:
            return
        role, ctx = ROLE_ORDER[index], self.ctx(row.site)
        old = row.status

        def work() -> object:
            account = self.ensure(ctx).account
            return change_role(ctx.api, account, row.object_id, role, people(ctx.api))

        def done(_user: object) -> None:
            said = f"{row.title} is now {rows[index]} on {row.site}."
            self.say(said)
            undo = None
            if old:
                undo = lambda: (  # noqa: E731
                    admin.update_user(ctx.api, row.object_id, roles=[old]),
                    f"{row.title} is {_ROLE_WORDS.get(old, old)} again.",
                )[1]
            from quill.core.workbench.history import Change

            self.history.record(Change(row.title, said, undo=undo))
            self.refresh()

        self.background("changing a role", work, done)

    def do_remove_user(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "user":
            return
        ctx = self.ctx(row.site)

        def chosen(everyone: list[dict[str, Any]]) -> None:
            others = [p for p in everyone if int(p.get("id", 0)) != row.object_id]
            if not others:
                self.say("There is nobody else to give this person's posts to.")
                return
            index = dlg.ask_choice(
                self.parent,
                self.show_modal,
                title=f"Remove {row.title}",
                prompt="&Give their posts to:",
                rows=[str(p.get("name", "")) for p in others],
                help_text="WordPress needs someone to own what this person wrote.",
            )
            if index is None:
                return
            target = others[index]
            to_id, to_name = int(target.get("id", 0)), str(target.get("name", ""))

            def previewed(sentence: str) -> None:
                if not dlg.confirm(
                    self.parent,
                    self.show_modal,
                    title="Remove",
                    message=sentence,
                    yes_label="Remove",
                ):
                    return

                def work() -> None:
                    account = self.ensure(ctx).account
                    remove_user(ctx.api, account, row.object_id, to_id, everyone)

                def done(_none: object) -> None:
                    said = f"Removed {row.title} from {row.site}; their posts are {to_name}'s."
                    self.say(said)
                    from quill.core.workbench.history import Change

                    self.history.record(Change(row.title, said))
                    self.refresh()

                self.background("removing a person", work, done)

            self.background(
                "counting posts",
                lambda: remove_preview(ctx.api, row.title, row.object_id, to_name),
                previewed,
            )

        self.background("reading people", lambda: people(ctx.api), chosen)

    def do_new_here(self, ref: Any, _row: WbRow | None) -> None:
        site = self.site_of(ref)
        key = ref.key if ref is not None else ""
        if key == "app_passwords" and site:
            self._new_password(site)
        elif key == "users" and site:
            self._new_user(site)
        else:
            self.say("New Here works in Users and Application Passwords in this preview.")

    def _new_password(self, site: str) -> None:
        name = dlg.ask_text(
            self.parent,
            self.show_modal,
            title="New Application Password",
            prompt="&Name:",
            help_text="A name for what will use it, such as QUILL on the laptop.",
        )
        if not name or not name.strip():
            return
        ctx = self.ctx(site)

        def done(made: Any) -> None:
            self.refresh()
            dlg.show_report(
                self.parent,
                self.show_modal,
                title=f"New Password for {site}",
                text=f"{made.name}\n\n{made.secret}\n\nCopy it now: {site} shows it only once.",
                help_text="The new application password. Select it and copy it; once this "
                "closes, the site will not show it again.",
            )

        self.background("making a password", lambda: create_app_password(ctx.api, name), done)

    def _new_user(self, site: str) -> None:
        answers = []
        for prompt, help_text in (
            ("&Username:", "The name they sign in with. It cannot be changed later."),
            ("&Email:", "Where WordPress can reach them."),
            ("&Display name:", "The name shown on what they write."),
        ):
            text = dlg.ask_text(
                self.parent,
                self.show_modal,
                title="Add a Person",
                prompt=prompt,
                help_text=help_text,
            )
            if not text or not text.strip():
                return
            answers.append(text.strip())
        index = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title="Add a Person",
            prompt="&Role:",
            rows=[_ROLE_WORDS[r] for r in ROLE_ORDER],
            help_text="What they may do on the site.",
        )
        if index is None:
            return
        username, email, name = answers
        role = ROLE_ORDER[index]
        if not dlg.confirm(
            self.parent,
            self.show_modal,
            title="Add a Person",
            message=f"Add {name} ({username}) to {site} as {_ROLE_WORDS[role]}? They set "
            "their own password with Lost Your Password on the sign-in page.",
            yes_label="Add",
        ):
            return
        api = self.ctx(site).api
        self.background(
            "adding a person",
            lambda: admin.add_user(api, username=username, email=email, name=name, role=role),
            lambda user: (self.say(f"Added {user.name} to {site}."), self.refresh()),
        )

    # -- filters ------------------------------------------------------------------

    def _family(self) -> str:
        frame = self.frame
        if frame is None or frame.current is None:
            return ""
        return str(frame.node(frame.current).loader.partition(":")[0])

    def _add_condition(self, condition: Condition, *, replace: bool = False) -> None:
        frame = self.frame
        query = frame.query.without(condition.attribute) if replace else frame.query
        frame.filter.ChangeValue(render(query.with_condition(condition)))
        frame.apply_filter()

    def do_filter_builder(self, _ref: Any, _row: WbRow | None) -> None:
        frame = self.frame
        if frame is None or frame.current is None:
            return
        family = self._family()
        attributes = _BUILDER.get(family) or tuple(
            (c, c.replace("_", " ").capitalize()) for c in frame.node(frame.current).columns
        )
        index = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title="Filter Builder",
            prompt="&Filter on:",
            rows=[label for _key, label in attributes],
            help_text="What to filter this list on. Each row you add joins the filter box.",
        )
        if index is None:
            return
        operators = (Operator.IS, Operator.IS_NOT, Operator.AFTER, Operator.BEFORE)
        op_index = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title="Filter Builder",
            prompt="&How:",
            rows=[op.value for op in operators],
            help_text="Is, is not, or for dates after and before.",
        )
        if op_index is None:
            return
        value = dlg.ask_text(
            self.parent,
            self.show_modal,
            title="Filter Builder",
            prompt="&Value:",
            help_text="Several values are separated by commas. Dates are written 2026-11-09.",
        )
        if value and value.strip():
            self._add_condition(Condition(attributes[index][0], operators[op_index], value.strip()))

    def _like(self, row: WbRow | None, operator: Operator) -> None:
        if row is None:
            self.say("Choose a row first.")
            return
        remote = self._family() in ("items", "media", "comments", "users", "terms", "patterns")
        options: list[tuple[str, str, str]] = []
        if row.status:
            options.append(("status", row.status, f"Status: {row.cell('status') or row.status}"))
        if row.raw.get("author"):
            options.append(("author", str(row.raw["author"]), f"Author: {row.cell('author')}"))
        if not remote:
            options += [
                (c, v, f"{c.replace('_', ' ').capitalize()}: {v}")
                for c, v in row.cells.items()
                if v
            ]
        if not options:
            self.say("This list can be narrowed by its words only. Type them in the filter box.")
            return
        index = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title="Show Only" if operator is Operator.IS else "Hide",
            prompt="&Like this row by:",
            rows=[label for _a, _v, label in options],
            help_text="Which of this row's values to keep, or to hide.",
        )
        if index is not None:
            attribute, value, _label = options[index]
            self._add_condition(Condition(attribute, operator, value))

    def do_show_only(self, _ref: Any, row: WbRow | None) -> None:
        self._like(row, Operator.IS)

    def do_hide_like(self, _ref: Any, row: WbRow | None) -> None:
        self._like(row, Operator.IS_NOT)

    def do_only_mine(self, ref: Any, _row: WbRow | None) -> None:
        site = self.site_of(ref)
        account = self.account_for(site) if site else None
        frame = self.frame
        if account is None or frame is None:
            self.say("Only Mine works in a site's lists once the site has said who you are.")
            return
        mine = Condition("author", Operator.IS, str(account.id))
        if mine in frame.query.conditions:
            frame.filter.ChangeValue(
                render(
                    Query(tuple(c for c in frame.query.conditions if c != mine), frame.query.words)
                )
            )
            frame.apply_filter()
            self.say("Showing everyone's.")
            return
        self._add_condition(mine, replace=True)
