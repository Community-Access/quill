"""Know before you try, for the 9.15 site commands (wordpress.md 9.2, 9.15).

The style, pattern, plugin and ability commands each check the site's REST
index first, read once a session per site through
:meth:`~quill.ui.wordpress_api_base.WordPressApiBase.site_facts`. A site
without the route or namespace never gets the request; the person hears one
sentence saying what is missing, and no window opens.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from quill.core.wordpress import site as wp
from quill.core.wordpress import site_features as sf
from quill.ui.wordpress_api_base import WordPressApiBase

if TYPE_CHECKING:
    from quill.core.wordpress import sites as st

#: Why not: (index, account) -> "" when offered, else one sentence.
WhyNot = Callable[[sf.SiteIndex, wp.Account], str]


class _Refused:
    def __init__(self, why: str) -> None:
        self.why = why


class WordPressApiSiteBase(WordPressApiBase):
    # Provided by WordPressCommands.
    host: Any

    def when_offered(
        self,
        profile: st.SiteProfile,
        doing: str,
        why_not: WhyNot,
        work: Callable[[Any, sf.SiteIndex, wp.Account], Any],
        done: Callable[[Any], None],
    ) -> None:
        """Run *work* off the UI thread only when *why_not* finds nothing, then *done*."""
        api = self.api(profile)  # type: ignore[attr-defined]

        def job() -> Any:
            index, account = self.site_facts(profile, api)
            why = why_not(index, account)
            return _Refused(why) if why else work(api, index, account)

        def finish(result: Any) -> None:
            if isinstance(result, _Refused):
                self.host.announce(result.why)
                return
            done(result)

        self.background(doing, job, finish)  # type: ignore[attr-defined]

    def chosen_site(self, title: str) -> st.SiteProfile | None:
        """The open WordPress document's site, or the one the person picks."""
        store = self.need_site()  # type: ignore[attr-defined]
        if store is None:
            return None
        copy = self.local.copy_for_path(self.host.current_path())  # type: ignore[attr-defined]
        profile = store.get(copy.site_id) if copy is not None else None
        return profile or self.pick_site(store, title)  # type: ignore[attr-defined,no-any-return]


def role_cannot(site_name: str, account: wp.Account, capability: str, what: str) -> str:
    """ "" when the account has *capability*, else the sentence that says it cannot."""
    if account.can(capability):
        return ""
    role = account.role_name
    article = "an" if role[:1].lower() in "aeiou" else "a"
    return f"Your account on {site_name} is {article} {role}, which cannot {what}."


def plain_error(exc: BaseException) -> str:
    """A value error's own sentence, without the support code in front."""
    return str(exc.args[0]) if exc.args else str(exc)
