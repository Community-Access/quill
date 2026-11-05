"""The shared plumbing of File > WordPress > Running the Site (wordpress.md 9.2).

Every Running the Site window opens the same way: choose the site (the open
document's, or ask), then read the account and the window's data together on
one background task. The account comes first so the window **knows before it
tries** (9.2): when this role cannot use the window at all, the person hears
one sentence saying so and no window opens; when it can use only part of it,
the buttons it would be refused are never built.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from quill.core.wordpress import site as wp
from quill.core.wordpress import site_admin as sa

if TYPE_CHECKING:
    from quill.core.wordpress import sites as st

_REFUSED = object()


class WordPressAdminBase:
    # Provided by WordPressCommands.
    host: Any

    def admin_site(self, title: str) -> st.SiteProfile | None:
        """The open WordPress document's site, or the one the person picks."""
        store = self.need_site()  # type: ignore[attr-defined]
        if store is None:
            return None
        copy = self.local.copy_for_path(self.host.current_path())  # type: ignore[attr-defined]
        profile = store.get(copy.site_id) if copy is not None else None
        return profile or self.pick_site(store, title)  # type: ignore[attr-defined,no-any-return]

    def admin_load(
        self,
        profile: st.SiteProfile,
        doing: str,
        need: str | None,
        work: Callable[[Any, wp.Account], Any],
        show: Callable[[Any, wp.Account, Any], None],
    ) -> None:
        """Read the account and *work*'s data off the UI thread, then *show* them.

        When the account lacks *need*, *work* never runs and the person is told
        what this role cannot do (9.2).
        """
        api = self.api(profile)  # type: ignore[attr-defined]

        def job() -> tuple[wp.Account, Any]:
            account = wp.load_account(api)
            if need is not None and not sa.can(account, need):
                return account, _REFUSED
            return account, work(api, account)

        def done(result: tuple[wp.Account, Any]) -> None:
            account, data = result
            if data is _REFUSED:
                assert need is not None
                self.host.announce(sa.cannot_sentence(profile.name, account, need))
                return
            show(api, account, data)

        self.background(doing, job, done)  # type: ignore[attr-defined]

    def after_close(self, then: Callable[[], None]) -> None:
        """Run *then* once the window that asked for it has closed.

        An action that swaps one window for another returns ``CLOSE`` and calls
        this; the host's task runner hands *then* back through the event loop,
        so the new window never opens on top of the one still closing.
        """
        self.host.run_task(
            "WordPress: next window", lambda: None, lambda _r: then(), lambda _e: None
        )

    def site_job(self, doing: str, work: Callable[[], Any], said: Callable[[Any], str]) -> None:
        """A change on the site; when it lands, speak what *said* makes of the answer."""
        self.background(doing, work, lambda r: self.host.announce(said(r)))  # type: ignore[attr-defined]
