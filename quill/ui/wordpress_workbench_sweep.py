"""The third sweep in the WordPress Workbench, core REST first (PRD 15.11).

A mixin on :class:`quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`:

- **Privacy Requests**, **Content Audit** and **Media > Housekeeping** list
  their rows from :mod:`quill.core.wordpress.workbench_sweep`, the last two
  from the same site scan By Name reads.
- **A redirect when the address changes**: after a sheet saves a new slug,
  on a site whose index has the Redirection plugin's namespace, the Workbench
  offers to add a redirect from the old address, naming both; nothing is sent
  before Add Redirect. Elsewhere nothing is offered.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.wordpress.workbench_rows import WbRow
from quill.core.wordpress.workbench_sweep import (
    REDIRECTION_NAMESPACE,
    content_audit,
    media_housekeeping,
    privacy_rows,
    redirect_body,
    redirect_offered,
)
from quill.ui import wordpress_dialogs as dlg

__all__ = ["WorkbenchSweepCommands"]


class WorkbenchSweepCommands:
    """Privacy Requests, Content Audit, Housekeeping and the redirect offer."""

    parent: Any
    say: Callable[[str], None]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    ensure: Callable[[Any], Any]
    profile: Callable[[str], Any]
    show_modal: Callable[[Any, str], int]

    def sweep_rows(self, site: str, what: str) -> list[WbRow]:
        """Off the UI thread: one of the third sweep's lists."""
        if what == "privacy":
            ctx = self.ensure(self.ctx(site))
            routes = ctx.info.routes if ctx.info is not None else ()
            return privacy_rows(site, self.profile(site).site_url, routes)
        scan = self.site_scan(site)  # type: ignore[attr-defined]
        if what == "audit":
            return content_audit(scan)
        return media_housekeeping(scan)

    def offer_redirect(self, row: WbRow, old_link: str) -> None:
        """After a new slug is saved: offer a redirect where the Redirection plugin is."""
        ctx = self.ctx(row.site)
        namespaces = ctx.info.namespaces if ctx.info is not None else ()
        if not old_link or not redirect_offered(namespaces):
            return
        api = ctx.api

        def got(fresh: Any) -> None:
            new_link = str(fresh.get("link", "") if isinstance(fresh, dict) else "")
            if not new_link or new_link == old_link:
                return
            if not dlg.confirm(
                self.parent,
                self.show_modal,
                title="Add a Redirect",
                message=f"{row.title} moved from {old_link} to {new_link}. Add a redirect on "
                f"{row.site}, so links to the old address still arrive?",
                yes_label="Add Redirect",
            ):
                return
            self.background(
                "adding a redirect",
                lambda: api.post(
                    f"{REDIRECTION_NAMESPACE}/redirect", redirect_body(old_link, new_link)
                ),
                lambda _r: self.say(f"Redirect added: {old_link} now leads to {new_link}."),
            )

        self.background("reading the new address", lambda: api.get(row.route, _fields="link"), got)
