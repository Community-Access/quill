"""The desk behind Find a Person or Organization: every action, as a sentence, with no window.

:class:`AccountDesk` joins the three things the window offers and keeps their
meanings apart:

* what only this computer remembers (:mod:`quill.core.github.tracked_accounts`):
  Track, and Favorite for an account or a repository;
* what is said to GitHub and is public (:mod:`quill.core.github.account_discovery`):
  Follow a person and Star a repository, each read back from GitHub;
* what GitHub organizes for you (:mod:`quill.core.github.star_lists`): a GitHub List.

Each method returns the one sentence to say and never raises for an expected
refusal (the account's Workbench level, Safe Mode, an organization asked to be
followed); it raises :class:`~quill.core.github.account_discovery.AccountError`
only when GitHub itself failed, and the message is already a sentence. The
window runs the ones that reach GitHub on a worker thread.

*refuse* is the Workbench's level check for one write: it is given what the
person tried ("follow a person") and answers "" when allowed, else the sentence
that says what level is needed. Safe Mode answers through the same check, so
no write is sent from it, and a search is refused outright (:meth:`search`).

wx-free and strict-typed.
"""

from __future__ import annotations

import os
from collections.abc import Callable

from quill.core.github.account_discovery import (
    KIND_ORGANIZATION,
    AccountError,
    AccountHit,
    RepositoryHit,
    disambiguate,
    is_following,
    is_starred,
    list_repositories,
    search_accounts,
    set_following,
    set_starred,
)
from quill.core.github.tracked_accounts import TrackedAccounts
from quill.core.github.workbench_api import GitHubApi

__all__ = ["SAFE_MODE_SENTENCE", "AccountDesk"]

SAFE_MODE_SENTENCE = (
    "Safe Mode is on, so QUILL does not contact GitHub. Start QUILL normally to search."
)


def _safe_mode() -> bool:
    return os.environ.get("QUILL_SAFE_MODE", "").strip() in {"1", "true", "yes"}


class AccountDesk:
    def __init__(
        self,
        api: GitHubApi,
        store: TrackedAccounts,
        *,
        refuse: Callable[[str], str] = lambda _what: "",
        safe_mode: Callable[[], bool] = _safe_mode,
    ) -> None:
        self.api = api
        self.store = store
        self._refuse = refuse
        self._safe_mode = safe_mode

    # -- reading GitHub ----------------------------------------------------------

    def search(self, text: str) -> tuple[list[AccountHit], list[str]]:
        """Matching accounts and one row of words for each; raises in Safe Mode."""
        if self._safe_mode():
            raise AccountError(SAFE_MODE_SENTENCE)
        hits = search_accounts(self.api, text)
        return hits, disambiguate(hits)

    def repositories(self, hit: AccountHit) -> list[RepositoryHit]:
        if self._safe_mode():
            raise AccountError(SAFE_MODE_SENTENCE)
        return list_repositories(self.api, hit.login, hit.kind)

    def following(self, hit: AccountHit) -> bool | None:
        """Whether you follow a person; None for an organization (QUILL does not ask)."""
        if hit.kind == KIND_ORGANIZATION or self._safe_mode():
            return None
        return is_following(self.api, hit.login)

    def starred(self, repo: str) -> bool | None:
        if self._safe_mode():
            return None
        return is_starred(self.api, repo)

    # -- writing to GitHub (public) ------------------------------------------------

    def toggle_follow(self, hit: AccountHit) -> str:
        """Follow a person you do not follow, unfollow one you do; GitHub confirms."""
        if hit.kind == KIND_ORGANIZATION:
            return (
                f"QUILL does not follow organizations; GitHub documents that only as a "
                f"public preview. Use Open on GitHub for {hit.login} and press Follow there."
            )
        if said := self._refuse("follow or unfollow a person"):
            return said
        now = is_following(self.api, hit.login)
        return set_following(self.api, hit, not now)

    def toggle_star(self, repo: str) -> str:
        """Star a repository you have not starred, remove the star from one you have."""
        if said := self._refuse("star or unstar a repository"):
            return said
        now = is_starred(self.api, repo)
        return set_starred(self.api, repo, not now)

    # -- writing to this computer only ----------------------------------------------

    def toggle_track(self, hit: AccountHit) -> str:
        if self.store.is_tracked(hit.login):
            return self.store.untrack(hit.login)
        return self.store.track(hit)

    def toggle_favorite(self, hit: AccountHit) -> str:
        return self.store.set_favorite(hit, not self.store.is_favorite(hit.login))

    def toggle_favorite_repository(self, repo: str) -> str:
        return self.store.set_favorite_repository(repo, not self.store.is_favorite_repository(repo))
