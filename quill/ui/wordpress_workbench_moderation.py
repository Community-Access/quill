"""Comments in the WordPress Workbench: the rest of wp-admin's screen (wordpress.md 9.18, 4).

A mixin on :class:`quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`.
The status views, moderation, Reply, Trash and Delete Permanently are in
:mod:`quill.ui.wordpress_workbench_commands`; this adds:

- **Comment Counts** (Site menu, Ctrl+Alt+Shift+C): wp-admin's count line, said
  as one sentence, with Mine.
- **Show Its Comments** (Item menu, Ctrl+Alt+Shift+M) on a post or page: the
  Comments list filtered to it, and how many it has, the number in wp-admin's
  comment bubble.
- **Empty Comment Trash** (Site menu, Ctrl+Alt+Shift+E): wp-admin's Empty Trash
  button on the Comments screen, after a confirmation naming the count. It
  cannot be undone, and the confirmation says so.

Every request runs through ``self.background``; every outcome is one sentence.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.wordpress.workbench_create import empty_spam
from quill.core.wordpress.workbench_moderation import (
    comment_counts,
    counts_sentence,
    mine_count,
    post_comment_count,
    trashed_comments,
)
from quill.core.wordpress.workbench_rows import WbRow
from quill.ui import wordpress_dialogs as dlg

__all__ = ["WorkbenchModerationCommands"]


class WorkbenchModerationCommands:
    """Comment Counts, Show Its Comments and Empty Comment Trash."""

    parent: Any
    say: Callable[[str], None]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    ensure: Callable[[Any], Any]
    show_modal: Callable[[Any, str], int]
    refresh: Callable[[], None]
    site_of: Callable[[Any], str]
    current_site: Callable[[], str]

    def _site_for(self, ref: Any) -> str:
        site = self.site_of(ref) or self.current_site()
        if not site:
            self.say("Choose a site first.")
        return site

    def do_comment_counts(self, ref: Any, _row: WbRow | None) -> None:
        site = self._site_for(ref)
        if not site:
            return
        ctx = self.ctx(site)

        def work() -> str:
            account = self.ensure(ctx).account
            counts = comment_counts(ctx.api)
            mine = mine_count(ctx.api, account.id) if account is not None else None
            return counts_sentence(site, counts, mine)

        self.background("counting comments", work, self.say)

    def do_show_comments(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "item":
            self.say("Show Its Comments works on a post or page.")
            return
        api = self.ctx(row.site).api

        def done(count: int) -> None:
            self._show_filtered("comments", row.site, f"post:{row.key}")  # type: ignore[attr-defined]
            noun = "comment" if count == 1 else "comments"
            self.say(f"{count} {noun} on {row.title}, approved and waiting together.")

        self.background("counting comments", lambda: post_comment_count(api, row.object_id), done)

    def do_empty_comment_trash(self, ref: Any, _row: WbRow | None) -> None:
        site = self._site_for(ref)
        if not site:
            return
        api = self.ctx(site).api

        def counted(ids: list[int]) -> None:
            if not ids:
                self.say(f"The comment Trash on {site} is empty.")
                return
            noun = "comment" if len(ids) == 1 else "comments"
            if not dlg.confirm(
                self.parent,
                self.show_modal,
                title="Empty Comment Trash",
                message=f"Delete all {len(ids)} {noun} in the Trash on {site} permanently? "
                "This cannot be undone.",
                yes_label="Delete All",
            ):
                return

            def done(failed: list[int]) -> None:
                gone = len(ids) - len(failed)
                more = f" {len(failed)} could not be deleted." if failed else ""
                self.say(f"Deleted {gone} {noun} from the Trash on {site}.{more}")
                self.refresh()

            self.background("emptying the comment Trash", lambda: empty_spam(api, ids), done)

        self.background("counting the comment Trash", lambda: trashed_comments(api), counted)
