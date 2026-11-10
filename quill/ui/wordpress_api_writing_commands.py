"""Custom fields, which password QUILL uses, and bulk moderation (wordpress.md 9.15).

A mixin of :class:`~quill.ui.wordpress_commands.WordPressCommands`;
:class:`WordPressApiWritingCommands` also gathers the Notes and picture
mixins, so the commands class needs only this one name.

- **Custom fields:** the post meta a site registers for the REST API, as
  labelled fields after Properties (and on their own row), kept with the
  working copy and sent with the next Save Draft to Site or Publish.
- **Which password:** an action for the Sites window that says which of the
  account's application passwords QUILL is signing with.
- **Bulk moderation:** Mark, Mark Everything and Do with Marked for the
  Comments window, one confirmation that gives the count.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any

from quill.core.wordpress import comments as cm
from quill.core.wordpress import custom_fields as cf
from quill.core.wordpress import site_features as sf
from quill.ui import wordpress_block_dialogs as bdlg
from quill.ui import wordpress_dialogs as dlg
from quill.ui.wordpress_custom_field_lists import WordPressCustomFieldLists
from quill.ui.wordpress_notes_commands import WordPressNotesCommands
from quill.ui.wordpress_picture_edit_commands import WordPressPictureEditCommands

if TYPE_CHECKING:
    from quill.core.wordpress import local as lc
    from quill.core.wordpress import sites as st

#: One moderation button: (label, help, new status, what was done).
Moderation = tuple[str, str, str, str]


class WordPressApiWritingCommands(
    WordPressNotesCommands, WordPressPictureEditCommands, WordPressCustomFieldLists
):
    # ------------------------------------------------------------------ #
    # custom fields (9.15)

    def cmd_custom_fields(self) -> None:
        found = self.current("Custom Fields")  # type: ignore[attr-defined]
        if found is not None:
            self._custom_fields(*found, quiet=False)

    def custom_fields_after_properties(self, copy: lc.WorkingCopy, profile: st.SiteProfile) -> None:
        """Called by Properties once it closes with OK: the site's fields, if it has any."""
        self._custom_fields(copy, profile, quiet=True)

    def _custom_fields(self, copy: lc.WorkingCopy, profile: st.SiteProfile, *, quiet: bool) -> None:
        kind, item_id = copy.kind, int(copy.remote_id or 0)

        def work(api: Any, _index: Any, _account: Any) -> tuple[dict[str, Any], dict[str, Any]]:
            schema = cf.meta_schema(api, kind)
            return schema, cf.site_values(api, kind, item_id) if schema else {}

        def show(found: tuple[dict[str, Any], dict[str, Any]]) -> None:
            schema, values = found
            fresh = self.local.copy_for_path(self.host.current_path()) or copy  # type: ignore[attr-defined]
            kept = dict(fresh.properties.get("meta") or {})
            form = cf.build_form(schema, values, kept)
            if not form.fields and not form.structured:
                if not quiet:
                    self.host.announce(f"{profile.name} has no custom fields for a {kind}.")
                return
            if not form.fields:
                self.edit_lists_and_groups(form, fresh, profile)
                return
            more = (
                f" {form.left_alone} more are lists or groups QUILL leaves as they are."
                if form.left_alone
                else ""
            )
            if form.structured:
                lists = len(form.structured)
                noun = "list or group comes" if lists == 1 else "lists and groups come"
                more += f" {lists} {noun} next, one at a time."
            answers = bdlg.ask_fields(
                self.host.parent,
                self.host.show_modal,
                title="Custom Fields",
                purpose=(
                    f"The fields {profile.name} adds to a {kind}, from its plugins and theme, "
                    f"such as an SEO title or an event date.{more} Changes go to the site with "
                    "your next Save Draft to Site or Publish."
                ),
                fields=form.fields,
            )
            if answers is None:
                return
            try:
                changed = cf.changes(form, answers)
            except cf.FieldValueError as exc:
                self.host.announce(
                    f"{exc.field_label} needs a number. Nothing was kept; try again."
                )
                return
            fresh.properties["meta"] = cf.merge_kept(kept, form, changed)
            self.local.save(fresh)  # type: ignore[attr-defined]
            count = len(changed)
            if not count:
                self.host.announce("No custom fields changed.")
            else:
                noun = "field" if count == 1 else "fields"
                self.host.announce(
                    f"{count} custom {noun} kept with your copy. They go to {profile.name} when "
                    "you next send."
                )
            self.edit_lists_and_groups(form, fresh, profile)

        self.with_feature(
            profile, "custom_fields", f"reading {profile.name}'s custom fields", work, show
        )

    # ------------------------------------------------------------------ #
    # which application password (9.15)

    def which_password_action(self) -> dlg.Action:
        """The Sites window's Which Password button (wired by ``cmd_sites``)."""

        def run(index: int | None) -> object:
            sites = self.sites().sites  # type: ignore[attr-defined]
            if index is None or index >= len(sites):
                return None
            self.say_which_password(sites[index])
            return None

        return dlg.Action(
            "&Which Password",
            "Say which of your application passwords QUILL signs in to the selected site with. "
            "Sign Out This Site revokes exactly that one.",
            run,
        )

    def say_which_password(self, profile: st.SiteProfile) -> None:
        if profile.kind == "wpcom" and not profile.username:
            self.host.announce(
                f"QUILL signs in to {profile.name} with a WordPress.com token, not an "
                "application password."
            )
            return
        self.with_feature(
            profile,
            "which_password",
            f"asking {profile.name} which password QUILL uses",
            lambda api, _index, _account: sf.which_password(api),
            lambda found: self.host.announce(sf.password_sentence(profile.name, found)),
        )

    # ------------------------------------------------------------------ #
    # bulk moderation in the Comments window (9.15)

    def comment_marks(
        self, profile: st.SiteProfile, api: Any, live: list[cm.Comment]
    ) -> CommentMarks:
        return CommentMarks(self, profile, api, live)


class CommentMarks:
    """Marked comments in one Comments window, and what to do with them together."""

    def __init__(
        self, owner: Any, profile: st.SiteProfile, api: Any, live: list[cm.Comment]
    ) -> None:
        self.owner = owner
        self.profile = profile
        self.api = api
        self.live = live
        self.marked: set[int] = set()

    def label(self, shown: Sequence[tuple[int, cm.Comment]], plain: Sequence[str]) -> list[str]:
        """The window's rows, each marked one saying so first."""
        return [
            ("Marked, " if c.id in self.marked else "") + row
            for (_d, c), row in zip(shown, plain, strict=True)
        ]

    def actions(
        self,
        rows: Callable[[], list[str]],
        shown: Sequence[tuple[int, cm.Comment]],
        moderation: Sequence[Moderation],
    ) -> list[dlg.Action]:
        host = self.owner.host
        site = self.profile.name

        def mark(index: int | None) -> object:
            if index is None or index >= len(shown):
                return None
            self.marked.symmetric_difference_update({shown[index][1].id})
            return rows()

        def mark_everything(_index: int | None) -> object:
            ids = {c.id for c in self.live}
            self.marked = set() if ids and ids <= self.marked else ids
            host.announce(f"{len(self.marked)} comments marked.")
            return rows()

        def with_marked(_index: int | None) -> object:
            chosen = [c for c in self.live if c.id in self.marked]
            if not chosen:
                host.announce("Mark the comments first, with Mark.")
                return None
            labels = [label.replace("&", "") for label, _h, _s, _d in moderation]
            picked = dlg.ask_choice(
                host.parent,
                host.show_modal,
                title="Do with Marked",
                prompt="&Do:",
                rows=labels,
                help_text=f"What to do with the {len(chosen)} marked comments, all at once.",
            )
            if picked is None:
                return None
            _label, _help, new_status, said = moderation[picked]
            verb = labels[picked]
            count = len(chosen)
            noun = "comment" if count == 1 else "comments"
            if not dlg.confirm(
                host.parent,
                host.show_modal,
                title="Do with Marked",
                message=f"{verb}: {count} marked {noun} on {site}?",
                yes_label=f"{verb} {count}",
            ):
                return None
            ids = [c.id for c in chosen]
            self.owner.site_job(
                "moderating marked comments",
                lambda: cm.set_many(self.api, ids, new_status),
                lambda n: f"{n} {'comment' if n == 1 else 'comments'} {said} on {site}.",
            )
            self.live[:] = [c for c in self.live if c.id not in self.marked]
            self.marked.clear()
            return rows()

        return [
            dlg.Action("Mar&k", "Mark or unmark the selected comment.", mark),
            dlg.Action(
                "Mark Ever&ything",
                "Mark every comment in the list, or none when all are marked.",
                mark_everything,
            ),
            dlg.Action(
                "&Do with Marked...",
                "Approve, spam or trash every marked comment at once, after one confirmation.",
                with_marked,
                needs_row=False,
            ),
        ]
