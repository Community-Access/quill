"""Reading a site's claims again when it changed (complete.md WP-B, never stale permissions).

A mixin of :class:`~quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`.
:meth:`recheck` runs inside ``ensure`` (off the UI thread): the first time it
keeps a stamp of the index and the account; after
:data:`~quill.core.wordpress.workbench_site_stamp.RECHECK_SECONDS` it reads
them again, with the plugins and the theme where allowed, and the fresh
account and index always replace the old ones. When anything changed, the
site's types and taxonomies are discovered again, the tree is rebuilt and the
change is said once. :meth:`site_changed` does the same at once after the
Workbench itself turns a plugin on or off.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from quill.core.wordpress.workbench_site_stamp import (
    RECHECK_SECONDS,
    SiteStamp,
    forget_site,
    read_stamp,
    stamp_changes,
    stamp_of,
)

__all__ = ["WorkbenchSiteCheck"]


class WorkbenchSiteCheck:
    """Notices a plugin, theme, WordPress or role change and forgets what depended on it."""

    frame: Any
    _contexts: dict[str, Any]
    say: Callable[[str], None]
    background: Callable[..., None]
    discover: Callable[[str], None]

    def _stamp_book(self) -> dict[str, tuple[float, SiteStamp]]:
        book = getattr(self, "_site_stamps", None)
        if book is None:
            book = self._site_stamps = {}
        return book

    def recheck(self, ctx: Any, *, now: float | None = None) -> list[str]:
        """Off the UI thread: what changed on *ctx*'s site since its stamp, if it is due."""
        clock = time.monotonic() if now is None else now
        book = self._stamp_book()
        last = book.get(ctx.name)
        if last is None:
            book[ctx.name] = (clock, stamp_of(ctx.info, ctx.account))
            return []
        if clock - last[0] < RECHECK_SECONDS:
            return []
        stamp, info, account = read_stamp(ctx.api)
        book[ctx.name] = (clock, stamp)
        ctx.info, ctx.account = info, account  # the claims are always the fresh ones
        changes = stamp_changes(last[1], stamp)
        if changes:
            forget_site(ctx.api)
            self.discover(ctx.name)
            self._after_ui(lambda: self._site_moved(ctx.name, changes))
        return changes

    @staticmethod
    def _after_ui(job: Callable[[], None]) -> None:
        import wx

        wx.CallAfter(job)

    def _site_moved(self, site: str, changes: list[str]) -> None:
        if self.frame is not None:
            self.frame.rebuild_tree()
        self.say(
            f"{site} changed since QUILL last looked: {'; '.join(changes)}. Its permissions, "
            "types and fields were read again."
        )

    def site_changed(self, site: str) -> None:
        """The Workbench changed *site*'s plugins: forget its claims and discover it again."""
        ctx = self._contexts.get(site)
        if ctx is not None:
            ctx.account = ctx.info = None
            forget_site(ctx.api)
        self._stamp_book().pop(site, None)

        def done(_result: object) -> None:
            if self.frame is not None:
                self.frame.rebuild_tree()

        self.background(f"reading {site} again", lambda: self.discover(site), done)
