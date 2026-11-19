"""Redirects > Redirect Options: the Redirection plugin's options as a Properties sheet.

A mixin of :class:`quill.ui.wordpress_workbench_redirect_group.WorkbenchRedirectGroup`
(GATE-11). The words and the route are wx-free in
:mod:`quill.core.wordpress.workbench_redirect_options`.

- **The node** lists each option QUILL knows, with its value, and one more
  row naming how many options stay in Tools > Redirection > Options. On a
  site whose Redirection has no ``redirection/v1/setting`` route, its one row
  says so plainly and Enter opens that wp-admin screen.
- **Change Options...** (Enter on an option) and **Alt+Enter** open the
  options as a Properties sheet, read again first. OK or Apply previews only
  the options that changed, sends only those, checks the answer, and puts the
  change in Change History; Ctrl+Z sends the old values back.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.wordpress import workbench_redirect_options as ro
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.properties import SheetState
from quill.ui import wordpress_workbench_dialogs as wdlg

__all__ = ["WorkbenchRedirectOptions"]

_NOT_LISTED = (
    "Redirection on {site} does not offer its options route ({route}) to REST, so QUILL "
    "cannot read or change them."
)


class WorkbenchRedirectOptions:
    """Read and change Redirection's options; the provider supplies the plumbing."""

    parent: Any
    say: Callable[[str], None]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    ensure: Callable[[Any], Any]
    step: Callable[..., None]
    refresh: Callable[[], None]
    show_modal: Callable[[Any, str], int]

    def redirect_option_rows(self, site: str, ctx: Any, site_url: str) -> list[WbRow]:
        """Off the UI thread: Redirects > Redirect Options."""
        routes = ctx.info.routes if ctx.info is not None else ()
        missing = _NOT_LISTED.format(site=site, route=ro.OPTIONS_ROUTE)
        if ro.options_offered(routes) is False:
            return [ro.missing_row(site, site_url, missing)]
        settings = ro.read_options(ctx.api)
        if settings is None:
            return [ro.missing_row(site, site_url, missing)]
        return ro.option_rows(site, site_url, settings)

    def redirect_options_sheet(
        self, row: WbRow
    ) -> tuple[Any, dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
        """Off the UI thread: the sheet, read again now (what the shared sheet loader returns)."""
        api = self.ensure(self.ctx(row.site)).api
        settings = ro.read_options(api)
        if settings is None:
            raise WordPressApiError(_NOT_LISTED.format(site=row.site, route=ro.OPTIONS_ROUTE))
        sheet, values = ro.options_sheet(row.site, settings)
        return sheet, values, settings, {}, {}

    def do_redirect_options(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "redirect_option":
            self.say("Change Options works on a row of Redirects > Redirect Options.")
            return
        self._one_sheet(row)  # type: ignore[attr-defined]

    def save_redirect_options(self, row: WbRow, state: SheetState) -> bool:
        """The sheet's OK or Apply: preview the changed options, send them, check the answer."""
        pending = state.pending()
        body = ro.body_for(pending)
        if not body:
            self.say("Nothing changed in Redirection's options.")
            return True
        site = row.site
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title="Change Redirection Options",
            summary=f"Change Redirection's options on {site}.",
            lines=ro.options_preview(pending, site),
            yes="Save Options",
        ):
            return False
        before = ro.undo_body(pending)
        api = self.ctx(site).api

        def undo() -> str:
            api.post(ro.OPTIONS_ROUTE, before)
            return f"Redirection's options on {site} are as they were."

        def done(answer: Any) -> None:
            said = ro.verified(site, body, answer)
            self.say(said)
            self.step(site, said, undo if before else None)
            self.refresh()

        self.background(
            f"saving Redirection's options on {site}",
            lambda: api.post(ro.OPTIONS_ROUTE, body),
            done,
        )
        return True
