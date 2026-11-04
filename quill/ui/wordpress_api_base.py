"""Knowing what a site offers before trying it (wordpress.md 9.2, 9.15).

The shared plumbing of the 9.15 commands: read the site's REST index and the
account once a session per site, ask :func:`site_features.unavailable`, and
only then do the work, all on one background task. When the site or the
account cannot do it, the person hears the one sentence that says why, and
no window opens.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from quill.core.wordpress import site as wp
from quill.core.wordpress import site_features as sf

if TYPE_CHECKING:
    from quill.core.wordpress import sites as st


class _Refused:
    def __init__(self, why: str) -> None:
        self.why = why


class WordPressApiBase:
    # Provided by WordPressCommands.
    host: Any

    def site_facts(self, profile: st.SiteProfile, api: Any) -> tuple[sf.SiteIndex, wp.Account]:
        """The index and the account, read once a session per site (off the UI thread)."""
        cache: dict[str, tuple[sf.SiteIndex, wp.Account]] = self.__dict__.setdefault(
            "_wp_site_facts", {}
        )
        if profile.id not in cache:
            cache[profile.id] = (sf.read_index(api), wp.load_account(api))
        return cache[profile.id]

    def with_feature(
        self,
        profile: st.SiteProfile,
        feature: str,
        doing: str,
        work: Callable[[Any, sf.SiteIndex, wp.Account], Any],
        done: Callable[[Any], None],
    ) -> None:
        """Run *work* only when *profile* offers *feature* to this account, then *done*."""
        api = self.api(profile)  # type: ignore[attr-defined]

        def job() -> Any:
            index, account = self.site_facts(profile, api)
            why = sf.unavailable(
                feature, index, account, profile.name, known_version=profile.wp_version
            )
            if why:
                return _Refused(why)
            return work(api, index, account)

        def finish(result: Any) -> None:
            if isinstance(result, _Refused):
                self.host.announce(result.why)
                return
            done(result)

        self.background(doing, job, finish)  # type: ignore[attr-defined]
