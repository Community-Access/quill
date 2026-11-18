"""GitHub Pages in the Workbench: turn on or off, rebuild, check (GitHub PRD section 19).

The code is in :mod:`quill.core.github.pages_tools`; this mixin asks and says.
Turn On Pages is Ctrl+N in a repository's GitHub Pages, because a repository
without a site has no row to act on.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.explore_models import ExploreRow

__all__ = ["PAGES_REASONS", "PAGES_VERBS", "GitHubWorkbenchPagesMixin"]

_SITE = frozenset({"pages_site"})

PAGES_VERBS: dict[str, frozenset[str]] = {
    "pages_turn_on": frozenset({"view"}),
    "pages_rebuild": _SITE,
    "pages_check": _SITE,
    "pages_turn_off": _SITE,
}

PAGES_REASONS: dict[str, str] = {
    "pages_turn_on": "Turn On Pages is Ctrl+N in a repository's GitHub Pages.",
    "pages_rebuild": "Rebuild is for a repository's Pages site, while you are signed in.",
    "pages_check": "Check Site is for a repository's Pages site, while you are signed in.",
    "pages_turn_off": "Turn Off Pages is for a repository's Pages site, while you are signed in.",
}


class GitHubWorkbenchPagesMixin:
    frame: Any
    signed_in: bool
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _choose: Callable[[str, str, list[str]], int]
    _confirm: Callable[[str, str], bool]
    _ask_text: Callable[..., str]

    def github_api(self) -> Any:
        raise NotImplementedError

    @staticmethod
    def _site(row: object) -> str:
        if isinstance(row, ExploreRow) and row.kind == "pages" and row.repo:
            return row.repo
        return ""

    def _fits_site(self, row: object) -> bool:
        return self.signed_in and bool(self._site(row))

    _fits_pages_rebuild = _fits_site
    _fits_pages_check = _fits_site
    _fits_pages_turn_off = _fits_site

    def _fits_pages_turn_on(self, _row: object) -> bool:
        current = getattr(getattr(self.frame, "current", None), "key", "")
        return self.signed_in and current == "pages"

    def _said_reload(self, said: object) -> None:
        self._say(str(said))
        self.frame.reload()

    def _do_pages_turn_on(self, ref: Any, _row: object) -> None:
        from quill.core.github.pages_tools import turn_on

        repo, title = ref.instance, "Turn On Pages"
        how = self._choose(
            title,
            "How should GitHub publish the site?",
            ["From a branch", "By a GitHub Actions workflow"],
        )
        if how < 0:
            return
        branch, folder = "", "/"
        if how == 0:
            branch = self._ask_text(title, "Publish which branch?", value="main")
            if not branch:
                return
            picked = self._choose(title, "From which folder?", ["The top of the branch", "/docs"])
            if picked < 0:
                return
            folder = "/" if picked == 0 else "/docs"
        api = self.github_api()
        self._background(
            "turn Pages on",
            lambda: turn_on(api, repo, workflow=how == 1, branch=branch, folder=folder),
            self._said_reload,
        )

    def _do_pages_rebuild(self, _ref: Any, row: object) -> None:
        from quill.core.github.pages_tools import rebuild

        repo, api = self._site(row), self.github_api()
        self._background("ask for a new build", lambda: rebuild(api, repo), self._said_reload)

    def _do_pages_check(self, _ref: Any, row: object) -> None:
        from quill.core.github.pages_tools import check

        repo, api = self._site(row), self.github_api()
        self._background("check the site", lambda: check(api, repo), lambda s: self._say(str(s)))

    def _do_pages_turn_off(self, _ref: Any, row: object) -> None:
        from quill.core.github.pages_tools import turn_off

        repo = self._site(row)
        if not self._confirm(
            "Turn Off Pages",
            f"Stop publishing {repo}'s GitHub Pages site? The repository is not changed, and "
            "the site can be turned on again.",
        ):
            return
        api = self.github_api()
        self._background("turn Pages off", lambda: turn_off(api, repo), self._said_reload)
