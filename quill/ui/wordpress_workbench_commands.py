"""What the WordPress Workbench does to the selected rows (PRD 7, 9, 13a.5, Part C).

A mixin on :class:`quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`:
each ``do_<verb>`` answers one command of
:mod:`quill.core.wordpress.workbench_actions`, given the node and the focused
row; the selection is ``self.selected_rows()``.

- **Open in Editor** is the editor's own open path
  (``WordPressCommands.open_item``), so writing stays in the editor (WP-R-002).
- **Delete is Trash** (WP-R-008): posts, pages, custom items and comments go to
  WordPress's Trash and Ctrl+Z restores them; on a user, Delete is Remove with
  reassignment; on anything without a Trash it says so and points at
  Shift+Delete, which is Delete Permanently, tier 3, always confirmed by name.
- **Moderation and spam** (13a.5): Approve, Unapprove, Spam and Not Spam on
  comments and form entries, one or many, each recorded in Change History so
  Ctrl+Z puts the old status back. Spam and Not Spam go to the site, so its
  spam plugin learns from them.

Every network call runs through ``self.background``; every outcome is one
sentence; confirmations name the site and the count (GATE-13 says nothing else).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from quill.core.wordpress import comments as wc
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.workbench_edit import (
    TRASHABLE,
    delete_permanently,
    restore,
    run_batch,
    set_comment_status,
    trash,
)
from quill.core.wordpress.workbench_forms import (
    set_entry_spam,
)
from quill.core.wordpress.workbench_parity import each, outcome
from quill.core.wordpress.workbench_permissions import (
    deactivate_refusal,
    deactivate_warning,
    revoke_refusal,
)
from quill.core.wordpress.workbench_plugin_actions import PLUGIN_TRASH
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.wordpress.workbench_tree import DYNAMIC_TAXONOMY, DYNAMIC_TYPE
from quill.core.workbench.history import Change
from quill.ui import wordpress_dialogs as dlg
from quill.ui.wordpress_workbench_admin_commands import WorkbenchAdminCommands
from quill.ui.wordpress_workbench_gravity_build import WorkbenchGravityBuildCommands
from quill.ui.wordpress_workbench_gravity_commands import WorkbenchGravityCommands
from quill.ui.wordpress_workbench_gravity_entries import WorkbenchGravityEntryCommands
from quill.ui.wordpress_workbench_gravity_forms import WorkbenchGravityFormCommands
from quill.ui.wordpress_workbench_membership_commands import WorkbenchMembershipCommands

__all__ = ["WorkbenchRowCommands"]

_STATUS_WORDS = {"approve": "approved", "hold": "unapproved", "spam": "marked as spam"}


def _count(rows: Sequence[object], noun: str) -> str:
    return f"{len(rows)} {noun}{'' if len(rows) == 1 else 's'}"


class WorkbenchRowCommands(
    WorkbenchGravityBuildCommands,
    WorkbenchGravityCommands,
    WorkbenchGravityEntryCommands,
    WorkbenchGravityFormCommands,
    WorkbenchMembershipCommands,
    WorkbenchAdminCommands,
):
    """Open, preview, publish, Trash, delete, moderate and reply."""

    frame: Any
    commands: Any
    history: Any
    say: Callable[[str], None]
    selected_rows: Callable[[], list[WbRow]]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    profile: Callable[[str], Any]
    show_modal: Callable[[Any, str], int]
    refresh: Callable[[], None]
    parent: Any

    def _confirm(self, title: str, message: str, yes: str) -> bool:
        return bool(
            dlg.confirm(self.parent, self.show_modal, title=title, message=message, yes_label=yes)
        )

    def _rows(self, row: WbRow | None, kinds: Sequence[str] = ()) -> list[WbRow]:
        rows = self.selected_rows() or ([row] if row is not None else [])
        return [r for r in rows if not kinds or r.kind in kinds]

    def _record(self, summary: str, undo: Callable[[], str] | None, target: str = "") -> None:
        self.history.record(Change(target or summary, summary, undo=undo))

    # -- reading and opening ------------------------------------------------------

    def do_read(self, _ref: Any, _row: WbRow | None) -> None:
        self.frame.details.SetFocus()

    def do_open_in_editor(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "item":
            self.say("Choose a post or page to open in the editor.")
            return
        profile = self.profile(row.site)
        if profile is None:
            self.say(f"{row.site} is no longer in your list of sites.")
            return
        self.commands.open_item(profile, row.subkind, row.object_id)

    def _browser(self, url: str) -> None:
        if not url:
            self.say("This has no address on the site yet.")
            return
        self.commands.host.open_in_browser(url)

    def do_open_on_site(self, ref: Any, row: WbRow | None) -> None:
        self._browser(row.link if row is not None and row.link else self.url(ref, None))  # type: ignore[attr-defined]

    def do_preview(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "item":
            self.say("Preview works on a post or page.")
            return
        link = row.link
        if link and row.status != "publish":
            link += ("&" if "?" in link else "?") + "preview=true"
        self._browser(link)

    def do_visual_review(self, _ref: Any, row: WbRow | None) -> None:
        """Appendix B: the editor's Visual Review, on a published post or page's row."""
        from quill.ui.wordpress_review_commands import NOT_PUBLISHED

        profile = self.profile(row.site) if row is not None and row.kind == "item" else None
        if row is None or profile is None:
            self.say("Visual Review works on a post or page.")
        elif row.status != "publish" or not row.link:
            self.say(NOT_PUBLISHED.format(site=row.site))
        else:
            self.commands.review(profile, row.link)

    def do_open_site(self, _ref: Any, row: WbRow | None) -> None:
        from quill.ui.workbench_frame import NodeRef

        if row is not None and self.frame.select(NodeRef("site", "overview", row.site)):
            self.frame.tree.SetFocus()

    def do_open_kind(self, ref: Any, row: WbRow | None) -> None:
        from quill.ui.wordpress_workbench_window import SEP
        from quill.ui.workbench_frame import NodeRef

        if row is None:
            return
        key = DYNAMIC_TYPE if row.kind == "writing_type" else DYNAMIC_TAXONOMY
        if self.frame.select(NodeRef("site", key, f"{row.site}{SEP}{row.key}")):
            self.frame.tree.SetFocus()
        else:
            self.say("Its node is still being added. Press F5 in a moment.")

    def _show_filtered(self, node: str, site: str, text: str) -> None:
        from quill.ui.workbench_frame import NodeRef

        if not self.frame.select(NodeRef("site", node, site)):
            return
        self.frame.filter.ChangeValue(text)
        self.frame.apply_filter()
        self.frame.list.SetFocus()

    def do_show_posts(self, _ref: Any, row: WbRow | None) -> None:
        if row is None:
            return
        if row.kind == "user":
            self._show_filtered("posts", row.site, f"author:{row.key}")
            return
        base = row.route.rsplit("/", 2)[-2] if row.route.count("/") >= 2 else "categories"
        self._show_filtered("posts", row.site, f"{base}:{row.key}")

    def do_show_entries(self, _ref: Any, row: WbRow | None) -> None:
        if row is not None:
            title = row.cell("form") or row.title  # a form row's title is its plugin
            self._show_filtered("form_entries", row.site, f'form:"{title}"')

    # -- publishing ---------------------------------------------------------------

    def do_publish(self, _ref: Any, row: WbRow | None) -> None:
        rows = [r for r in self._rows(row, ("item",)) if r.status != "publish"]
        if not rows:
            self.say("Nothing selected is waiting to be published.")
            return
        site = rows[0].site
        if any(r.site != site for r in rows):
            self.say("Publish items from one site at a time.")
            return
        names = "\n".join(f"- {r.title}" for r in rows[:20])
        more = f"\nand {len(rows) - 20} more" if len(rows) > 20 else ""
        if not self._confirm(
            "Publish",
            f"Publish {_count(rows, 'item')} on {site}? Visitors will see them.\n{names}{more}",
            "Publish",
        ):
            return
        api = self.ctx(site).api
        before = [{"status": r.status} for r in rows]

        def done(results: Sequence[Any]) -> None:
            good = [result for result in results if result.ok]
            failed = [result.sentence for result in results if not result.ok]
            said = f"Published {_count(good, 'item')} on {site}."
            if failed:
                said += f" {len(failed)} were not: {'; '.join(failed[:3])}"
            self.say(said)
            done_rows = [result.row for result in good]
            undo_bodies = [b for r, b in zip(rows, before, strict=True) if r in done_rows]
            self._record(
                said,
                lambda: (
                    run_batch(api, done_rows, undo_bodies),
                    f"Put {_count(done_rows, 'item')} back as they were.",
                )[1],
            )
            self.refresh()

        self.background(
            "publishing", lambda: run_batch(api, rows, [{"status": "publish"}] * len(rows)), done
        )

    # -- Trash and deleting -------------------------------------------------------

    def do_trash(self, ref: Any, row: WbRow | None) -> None:
        rows = self._rows(row)
        if not rows:
            return
        if rows[0].kind == "user":
            self.do_remove_user(ref, rows[0])  # type: ignore[attr-defined]
            return
        if rows[0].kind == "app_password":
            self.do_revoke(ref, rows[0])
            return
        if rows[0].kind in PLUGIN_TRASH:  # one at a time, through the plugin's own route
            getattr(self, PLUGIN_TRASH[rows[0].kind])(ref, rows[0])
            return
        if any(r.kind not in TRASHABLE for r in rows):
            self.say(
                "WordPress keeps no Trash for this, so it can only be deleted permanently, "
                "with Shift+Delete."
            )
            return
        if any(r.status == "trash" for r in rows):
            self.say("That is already in the Trash. Shift+Delete deletes it permanently.")
            return
        site = rows[0].site
        if len(rows) > 1 and not self._confirm(
            "Move to Trash", f"Move {_count(rows, 'item')} on {site} to the Trash?", "Move to Trash"
        ):
            return
        api = self.ctx(site).api
        statuses = {r.key: r.status for r in rows}

        def work() -> list[Any]:  # one outcome per row (9.18): a refusal never stops the rest
            return each(rows, lambda r: trash(api, r), "moved to the Trash")

        def done(results: list[Any]) -> None:
            moved = [result.row for result in results if result.ok]
            said = outcome(results, "Moved {n} to the Trash", site)
            said += " Ctrl+Z puts them back." if moved else ""
            self.say(said)
            self._record(
                said,
                (
                    lambda: (
                        [restore(api, r, statuses[r.key]) for r in moved],
                        f"Restored {_count(moved, 'item')} from the Trash.",
                    )[1]
                )
                if moved
                else None,
            )
            self.refresh()

        self.background("moving to Trash", work, done)

    def do_restore(self, _ref: Any, row: WbRow | None) -> None:
        rows = [r for r in self._rows(row, tuple(TRASHABLE)) if r.status == "trash"]
        if not rows:
            self.say("Nothing selected is in the Trash.")
            return
        api = self.ctx(rows[0].site).api

        def done(results: list[Any]) -> None:
            back = [result.row for result in results if result.ok]
            said = outcome(
                results, "Restored {n} from the Trash, as drafts or waiting", rows[0].site
            )
            self.say(said)
            self._record(
                said,
                (lambda: ([trash(api, r) for r in back], "Moved them back to the Trash.")[1])
                if back
                else None,
            )
            self.refresh()

        self.background(
            "restoring", lambda: each(rows, lambda r: restore(api, r), "restored"), done
        )

    def do_delete_permanently(self, ref: Any, row: WbRow | None) -> None:
        rows = self._rows(row)
        if not rows:
            return
        if rows[0].kind == "user":
            self.do_remove_user(ref, rows[0])  # type: ignore[attr-defined]
            return
        if rows[0].kind == "app_password":  # Revoke, with its own guard on QUILL's password
            self.do_revoke(ref, rows[0])
            return
        if rows[0].kind == "gravity_feed":
            self.delete_feeds([r for r in rows if r.kind == "gravity_feed"])
            return
        site = rows[0].site
        names = ", ".join(r.title for r in rows[:5]) + (" and more" if len(rows) > 5 else "")
        if not self._confirm(
            "Delete Permanently",
            f"Delete {_count(rows, 'item')} from {site} permanently? This cannot be undone: "
            f"{names}.",
            "Delete Permanently",
        ):
            return
        api = self.ctx(site).api

        def done(results: list[Any]) -> None:
            said = outcome(results, "Deleted {n} permanently", site)
            self.say(said + " This cannot be undone.")
            self._record(said, None)
            self.refresh()

        self.background(
            "deleting",
            lambda: each(rows, lambda r: delete_permanently(api, r), "deleted"),
            done,
        )

    # -- moderation and spam (13a.5) ----------------------------------------------

    def _moderate(self, row: WbRow | None, status: str) -> None:
        rows = self._rows(row, ("comment", "form_entry"))
        if not rows:
            self.say("Choose a comment or a form entry.")
            return
        site = rows[0].site
        api = self.ctx(site).api
        comments = [r for r in rows if r.kind == "comment"]
        entries = [r for r in rows if r.kind == "form_entry"]
        if entries and status in ("approve", "hold"):
            status_for_entries = False
        else:
            status_for_entries = status == "spam"

        def target(r: WbRow) -> str:
            if status == "approve" and r.status == "spam":
                return "hold"  # Not Spam puts a held comment back in the queue
            return status

        previous = {r.key: r.status or "hold" for r in comments}

        def work() -> tuple[list[WbRow], list[str]]:  # one outcome per comment (9.18)
            results = each(comments, lambda r: set_comment_status(api, r, target(r)), "changed")
            failed = [result.sentence for result in results if not result.ok]
            if entries:
                failed += set_entry_spam(self.ctx(site), entries, status_for_entries)
            return [result.row for result in results if result.ok], failed

        def done(answer: tuple[list[WbRow], list[str]]) -> None:
            changed, failed = answer
            done_count = len(rows) - len(failed)
            amount = _count(rows, "item") if not failed else f"{done_count} of {len(rows)} items"
            if status == "approve" and all(r.status == "spam" for r in rows):
                said = f"Not spam: {amount} on {site}, and the site was told."
            else:
                said = f"{amount[:1].upper()}{amount[1:]} {_STATUS_WORDS[status]} on {site}."
            if failed:
                said += f" Not changed: {'; '.join(failed[:3])}"
            self.say(said)
            self._record(
                said,
                lambda: (
                    [set_comment_status(api, r, previous[r.key]) for r in changed],
                    set_entry_spam(self.ctx(site), entries, not status_for_entries),
                    f"Put {_count(changed + entries, 'item')} back as they were.",
                )[2],
            )
            self.refresh()

        self.background("moderating", work, done)

    def do_approve(self, _ref: Any, row: WbRow | None) -> None:
        self._moderate(row, "approve")

    def do_unapprove(self, _ref: Any, row: WbRow | None) -> None:
        self._moderate(row, "hold")

    def do_spam(self, _ref: Any, row: WbRow | None) -> None:
        self._moderate(row, "spam")

    def do_reply(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "comment":
            self.say("Choose a comment to reply to.")
            return
        text = dlg.ask_text(
            self.parent,
            self.show_modal,
            title=f"Reply to {row.cell('author')}",
            prompt="&Reply:",
            help_text=f"Your reply to {row.cell('author')}, posted as you on {row.site}.",
            multiline=True,
        )
        if not text or not text.strip():
            return
        api = self.ctx(row.site).api
        parent = wc.comment_from_payload(row.raw)
        self.background(
            "replying",
            lambda: wc.reply(api, parent, text.strip()),
            lambda _c: (
                self.say(f"Replied to {row.cell('author')} on {row.site}."),
                self.refresh(),
            ),
        )

    # -- plugins, themes, passwords -----------------------------------------------

    def do_toggle_plugin(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "plugin":
            return
        active = row.status in ("active", "network-active")
        verb = "Deactivate" if active else "Activate"
        refused = deactivate_refusal(row.key, row.site) if active else ""
        if refused:
            self.say(refused)
            return
        if not active:
            self._toggle_plugin(row, active, verb, "")
            return

        def depends() -> str:  # what would notice, asked of the site first (D3)
            try:
                return str(self.plugin_dependents(row).sentence())  # type: ignore[attr-defined]
            except WordPressApiError:
                return "The site would not say what depends on it."

        self.background(
            f"asking what depends on {row.title}",
            depends,
            lambda said: self._toggle_plugin(row, active, verb, said),
        )

    def _toggle_plugin(self, row: WbRow, active: bool, verb: str, depends: str) -> None:
        warning = deactivate_warning(row.key) if active else ""
        message = f"{verb} {row.title} on {row.site}?" + (f" {warning}" if warning else "")
        message += f" {depends}" if depends else ""
        if not self._confirm(verb, message, verb):
            return
        api = self.ctx(row.site).api
        body = {"status": "inactive" if active else "active"}

        def done(_raw: object) -> None:
            said = f"{row.title} is now {'inactive' if active else 'active'} on {row.site}."
            self.say(said)
            back = {"status": row.status}
            self._record(said, lambda: (api.post(row.route, back), f"{row.title} put back.")[1])
            self.site_changed(row.site)  # type: ignore[attr-defined]  # types, fields, rights
            self.refresh()

        self.background("changing a plugin", lambda: api.post(row.route, body), done)

    def do_revoke(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "app_password":
            return
        refused = revoke_refusal(row.status == "current", row.site)
        if refused:
            self.say(refused)
            return
        if not self._confirm(
            "Revoke Application Password",
            f"Revoke the application password {row.title} on {row.site}? Anything signing in "
            "with it stops working, and a revoked password cannot be restored.",
            "Revoke",
        ):
            return
        api = self.ctx(row.site).api

        def done(_result: object) -> None:
            said = f"Revoked {row.title} on {row.site}."
            self.say(said)
            self._record(said, None)
            self.refresh()

        self.background("revoking a password", lambda: api.delete(row.route), done)
