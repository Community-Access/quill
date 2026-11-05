"""Asking the site first: the shared plumbing of the 9.16 commands (wordpress.md 9.16).

Each 9.16 command reads the site's REST index and the account once a session
per site (the same cache the 9.15 commands use), asks
:func:`quill.core.wordpress.routes.unavailable`, and only then does the work,
all on one background task. A site without the route is never sent the
request: the person hears the one sentence that says why, and no window opens.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from quill.core.wordpress import routes as rt
from quill.core.wordpress import site as wp
from quill.core.wordpress import site_features as sf

if TYPE_CHECKING:
    from quill.core.wordpress import sites as st


class _Refused:
    def __init__(self, why: str) -> None:
        self.why = why


class WordPressRouteBase:
    # Provided by WordPressCommands.
    host: Any

    def route_facts(self, profile: st.SiteProfile, api: Any) -> tuple[sf.SiteIndex, wp.Account]:
        """The index and the account, read once a session per site (off the UI thread)."""
        cache: dict[str, tuple[sf.SiteIndex, wp.Account]] = self.__dict__.setdefault(
            "_wp_site_facts", {}
        )
        if profile.id not in cache:
            cache[profile.id] = (sf.read_index(api), wp.load_account(api))
        return cache[profile.id]

    def route_why_not(self, profile: st.SiteProfile, api: Any, *features: str) -> str:
        """Off the UI thread: "" when every *feature* is offered, else the first reason."""
        index, account = self.route_facts(profile, api)
        for feature in features:
            why = rt.unavailable(feature, index, account, profile.name)
            if why:
                return why
        return ""

    def with_route(
        self,
        profile: st.SiteProfile,
        features: str | tuple[str, ...],
        doing: str,
        work: Callable[[Any], Any],
        done: Callable[[Any], None],
    ) -> None:
        """Run *work(api)* only when *profile* offers every feature, then *done(result)*."""
        wanted = (features,) if isinstance(features, str) else features
        api = self.api(profile)  # type: ignore[attr-defined]

        def job() -> Any:
            why = self.route_why_not(profile, api, *wanted)
            return _Refused(why) if why else work(api)

        def finish(result: Any) -> None:
            if isinstance(result, _Refused):
                self.host.announce(result.why)
                return
            done(result)

        self.background(doing, job, finish)  # type: ignore[attr-defined]

    def route_site(self, title: str) -> st.SiteProfile | None:
        """The open WordPress document's site, or the one the person picks."""
        store = self.need_site()  # type: ignore[attr-defined]
        if store is None:
            return None
        copy = self.local.copy_for_path(self.host.current_path())  # type: ignore[attr-defined]
        profile = store.get(copy.site_id) if copy is not None else None
        return profile or self.pick_site(store, title)  # type: ignore[attr-defined,no-any-return]

    def then_next(self, step: Callable[[], None]) -> None:
        """Run *step* on the next turn of the event loop (after a window closes)."""
        self.host.run_task("WordPress: next step", lambda: None, lambda _r: step(), lambda _e: None)
