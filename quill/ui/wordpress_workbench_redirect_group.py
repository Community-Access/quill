"""Make the Redirection plugin's first group, when its setup never made one.

A mixin of :class:`quill.ui.wordpress_workbench_sweep.WorkbenchSweepCommands`,
split out for its size budget (GATE-11). The plugin refuses every redirect
without a group ("Invalid group"); a site whose Redirection setup was never
finished has none, so New Redirect offers to make the one setup makes.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.wordpress.workbench_redirects import make_first_group
from quill.ui import wordpress_dialogs as dlg

__all__ = ["WorkbenchRedirectGroup"]


class WorkbenchRedirectGroup:
    """The offer to make a Redirections group, then carry on with the redirect."""

    parent: Any
    say: Callable[[str], None]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    show_modal: Callable[[Any, str], int]

    def _offer_first_group(self, site: str, title: str, then: Callable[[int], None]) -> None:
        """No group yet: offer to make the one the plugin's own setup makes, then go on."""
        if not dlg.confirm(
            self.parent,
            self.show_modal,
            title=title,
            message=(
                f"The Redirection plugin on {site} has no group yet, and every redirect needs "
                "one. Its setup normally makes one called Redirections. Make it now?"
            ),
            yes_label="Make Group",
        ):
            return
        api = self.ctx(site).api

        def make() -> int:
            from quill.core.wordpress.api import WordPressApiError

            try:
                return make_first_group(api)
            except WordPressApiError:
                return 0

        def made(group: int) -> None:
            if not group:
                self.say(
                    f"{site} would not make the group, which usually means the Redirection "
                    "plugin's setup was never finished. Open Tools, Redirection in wp-admin, "
                    "follow its setup, then try again."
                )
                return
            self.say(f"Made the Redirections group on {site}.")
            then(group)

        self.background("making a redirect group", make, made)
