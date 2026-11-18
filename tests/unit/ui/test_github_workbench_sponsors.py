"""Sponsor at This Tier... and Cancel Sponsorship... (GitHub PRD 14.3)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.core.github.sponsors import fetch_sponsor_page, fetch_sponsorships
from quill.ui.github_workbench_development import DEVELOPMENT_VERBS
from quill.ui.github_workbench_sponsors import GitHubWorkbenchSponsorsMixin
from tests.unit.core.github_workbench.test_sponsors import FakeApi


class _Window(GitHubWorkbenchSponsorsMixin):
    signed_in = True

    def __init__(self, picks: list[int], yes: bool = True) -> None:
        self.api, self.picks, self.yes = FakeApi(), list(picks), yes
        self.said: list[str] = []
        self.asked: list[str] = []
        self.frame = SimpleNamespace(frame=None, reload=lambda: self.said.append("(reloaded)"))

    def github_api(self) -> Any:
        return self.api

    def _say(self, text: str) -> None:
        self.said.append(text)

    def _choose(self, *_a: Any) -> int:
        return self.picks.pop(0)

    def _confirm(self, _title: str, question: str) -> bool:
        self.asked.append(question)
        return self.yes

    def _background(self, _name: str, work: Any, done: Any) -> None:
        done(work())


def _typed(monkeypatch: Any, answer: bool) -> list[str]:
    seen: list[str] = []

    class Typed:
        def __init__(self, _parent: Any, **kw: Any) -> None:
            seen.append(kw["expected"])
            seen.append(kw["message"])

        def show(self) -> bool:
            return answer

    monkeypatch.setattr("quill.ui.github_repo_admin_dialogs.TypedConfirmDialog", Typed)
    return seen


def test_registered() -> None:
    assert {"sponsor", "cancel_sponsorship"} <= set(DEVELOPMENT_VERBS)


def test_sponsoring_names_the_price_and_wants_the_login_typed(monkeypatch: Any) -> None:
    seen = _typed(monkeypatch, True)
    tier = fetch_sponsor_page(FakeApi(), "sam")[1]
    window = _Window([1])
    assert window._fits_sponsor(tier)
    window._do_sponsor(None, tier)
    assert seen[0] == "sam" and "$5 a month" in seen[1] and "each month until you cancel" in seen[1]
    assert window.api.sent[-1][1] == {"login": "sam", "tier": "T5", "privacy": "PRIVATE"}


def test_not_typing_the_login_charges_nothing(monkeypatch: Any) -> None:
    _typed(monkeypatch, False)
    tier = fetch_sponsor_page(FakeApi(), "sam")[2]
    window = _Window([0])
    window._do_sponsor(None, tier)
    assert window.said == ["Cancelled; nothing was charged."]
    assert not any(name == "mutation" or "tier" in vars_ for name, vars_ in window.api.sent)


def test_cancel_asks_first() -> None:
    row = fetch_sponsorships(FakeApi())[0]
    window = _Window([], yes=False)
    window._do_cancel_sponsorship(None, row)
    assert "Stop sponsoring sam? $5 a month, since 2025-02-01" in window.asked[0]
    assert window.api.sent == []
    window = _Window([])
    window._do_cancel_sponsorship(None, row)
    assert window.api.sent[-1][1] == {"login": "sam"}
