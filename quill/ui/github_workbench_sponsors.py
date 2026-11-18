"""Sponsoring someone, and cancelling a sponsorship (GitHub PRD 14.3).

The lists are Explore views (:mod:`quill.core.github.sponsors`). **Sponsor at
This Tier...** says the price and asks public or private, then has you type
the person's login before GitHub charges anything. **Cancel Sponsorship...**
asks first.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.explore_models import ExploreRow

__all__ = ["SPONSOR_REASONS", "SPONSOR_VERBS", "GitHubWorkbenchSponsorsMixin"]

SPONSOR_VERBS: dict[str, frozenset[str]] = {
    "sponsor": frozenset({"sponsor_tier"}),
    "cancel_sponsorship": frozenset({"sponsorship"}),
}

SPONSOR_REASONS: dict[str, str] = {
    "sponsor": "Sponsor at This Tier is for one of a person's tiers, while you are signed in.",
    "cancel_sponsorship": "Cancel Sponsorship is for someone you sponsor.",
}


class GitHubWorkbenchSponsorsMixin:
    frame: Any
    signed_in: bool
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _choose: Callable[[str, str, list[str]], int]
    _confirm: Callable[[str, str], bool]

    def github_api(self) -> Any:
        raise NotImplementedError

    def _fits_sponsor(self, row: object) -> bool:
        return self.signed_in and isinstance(row, ExploreRow) and row.kind == "sponsor_tier"

    def _fits_cancel_sponsorship(self, row: object) -> bool:
        return self.signed_in and isinstance(row, ExploreRow) and row.kind == "sponsorship"

    def _do_sponsor(self, _ref: Any, row: object) -> None:
        from quill.core.github.sponsors import sponsor
        from quill.ui.github_repo_admin_dialogs import TypedConfirmDialog

        if not isinstance(row, ExploreRow):
            return
        login, price = row.repo, row.label.split(":", 1)[0]
        privacy = self._choose(
            "Sponsor",
            f"Sponsor {login}, {price}. Who may see it?",
            ["Everyone (public)", f"Only {login} (private)"],
        )
        if privacy < 0:
            return
        if not TypedConfirmDialog(
            self.frame.frame,
            title="Sponsor",
            message=(
                f"Sponsor {login}, {price}. GitHub charges the payment method on your account "
                f"now{' and each month until you cancel' if 'a month' in price else ''}. "
                f"Type {login} to confirm."
            ),
            expected=login,
            confirm_label="Sponsor",
        ).show():
            self._say("Cancelled; nothing was charged.")
            return
        api, tier = self.github_api(), row.key
        self._background(
            "sponsor them",
            lambda: sponsor(api, login, tier, price, public=privacy == 0),
            lambda said: (self._say(str(said)), self.frame.reload()),
        )

    def _do_cancel_sponsorship(self, _ref: Any, row: object) -> None:
        from quill.core.github.sponsors import cancel_sponsorship

        if not isinstance(row, ExploreRow) or not self._confirm(
            "Cancel Sponsorship",
            f"Stop sponsoring {row.key}? {row.label.split(': ', 1)[-1].rstrip('.')}. "
            "Nothing more is charged for it.",
        ):
            return
        api, login = self.github_api(), row.key
        self._background(
            "cancel the sponsorship",
            lambda: cancel_sponsorship(api, login),
            lambda said: (self._say(str(said)), self.frame.reload()),
        )
