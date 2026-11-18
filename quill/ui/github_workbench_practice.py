"""Help > Practice on GitHub...: make, open or delete the practice repository (PRD 22.8).

The first time, it asks, then makes ``quill-practice`` (private) in your
account and fills it with issues, labels, a pull request and a failing run,
saying each part as it goes, and opens it. After that the same command offers
Open It, Delete It and Start Over, or Delete It. The work is
:mod:`quill.core.github.practice_repository`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = ["PRACTICE_REASONS", "PRACTICE_VERBS", "GitHubWorkbenchPracticeMixin"]

PRACTICE_VERBS: dict[str, frozenset[str]] = {"practice": frozenset({"view"})}
PRACTICE_REASONS: dict[str, str] = {
    "practice": "The practice repository is made in your account, so sign in first.",
}


class GitHubWorkbenchPracticeMixin:
    frame: Any
    signed_in: bool
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _choose: Callable[[str, str, list[str]], int]
    _confirm: Callable[[str, str], bool]

    def github_api(self) -> Any:
        raise NotImplementedError

    def _explore_client(self) -> Any:
        raise NotImplementedError

    def _go_repository(self, repository: str) -> None:
        raise NotImplementedError

    def _fits_practice(self, _row: object) -> bool:
        return self.signed_in

    def _do_practice(self, _ref: Any, _row: object) -> None:
        from quill.core.github.practice_repository import find_practice

        api, client = self.github_api(), self._explore_client()

        def work() -> tuple[str, str]:
            login = str(client.account_login())
            return login, find_practice(api, login)

        self._background("look for the practice repository", work, self._practice_found)

    def _practice_found(self, found: tuple[str, str]) -> None:
        from quill.core.github.practice_repository import PRACTICE_NAME

        login, repo = found
        title = "Practice on GitHub"
        if not repo:
            if self._confirm(
                title,
                f"Make a private repository, {login}/{PRACTICE_NAME}, to practise on? QUILL "
                "fills it with three issues, two labels, a pull request and a workflow that "
                "fails on purpose. Nothing else in your account is touched, and you can delete "
                "it from here when you finish.",
            ):
                self._make_practice(login)
            return
        choices = ["Open It", "Delete It and Start Over...", "Delete It..."]
        picked = self._choose(title, f"{repo} is ready to practise on.", choices)
        if picked == 0:
            self._go_repository(repo)
        elif picked > 0 and self._confirm(
            title,
            f"Delete {repo}, with everything in it? This cannot be undone."
            + (" Then QUILL makes a fresh one." if picked == 1 else ""),
        ):
            self._delete_practice(login, again=picked == 1)

    def _make_practice(self, login: str) -> None:
        from quill.core.github.practice_repository import create_practice

        api = self.github_api()

        def done(practice: Any) -> None:
            self._say(f"{practice.sentence} Opening it.")
            self._go_repository(practice.full_name)

        self._background("make the practice repository", lambda: create_practice(api, login), done)

    def _delete_practice(self, login: str, *, again: bool) -> None:
        from quill.core.github.practice_repository import delete_practice

        api = self.github_api()

        def done(said: str) -> None:
            self._say(said)
            if again:
                self._make_practice(login)

        self._background(
            "delete the practice repository", lambda: delete_practice(api, login), done
        )
