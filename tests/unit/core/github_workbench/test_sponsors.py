"""People > Sponsorships and a person's Sponsor node (GitHub PRD 14.3)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github import sponsors as sp

MINE = {
    "viewer": {
        "sponsorshipsAsSponsor": {
            "nodes": [
                {
                    "createdAt": "2025-02-01T00:00:00Z",
                    "sponsorable": {"login": "sam"},
                    "tier": {"id": "T1", "monthlyPriceInDollars": 5, "isOneTime": False},
                }
            ]
        },
        "sponsorshipsAsMaintainer": {
            "nodes": [
                {
                    "createdAt": "2026-03-04T00:00:00Z",
                    "sponsorEntity": {"login": "jo"},
                    "tier": {"monthlyPriceInDollars": 25, "isOneTime": True},
                }
            ]
        },
    }
}
PAGE = {
    "repositoryOwner": {
        "hasSponsorsListing": True,
        "viewerIsSponsoring": False,
        "sponsorsListing": {
            "shortDescription": "Free screen reader tools.",
            "tiers": {
                "nodes": [
                    {
                        "id": "T5",
                        "name": "Coffee",
                        "description": "Keeps the lights on.\nThanks!",
                        "monthlyPriceInDollars": 5,
                        "isOneTime": False,
                    },
                    {
                        "id": "TC",
                        "name": "Custom",
                        "isCustomAmount": True,
                        "monthlyPriceInDollars": 1,
                    },
                    {
                        "id": "T100",
                        "name": "Big thanks",
                        "description": "",
                        "monthlyPriceInDollars": 100,
                        "isOneTime": True,
                    },
                ]
            },
        },
    }
}


class FakeApi:
    def __init__(self, page: Any = PAGE) -> None:
        self.page = page
        self.sent: list[tuple[str, dict[str, Any]]] = []

    def rest(self, *_a: Any, **_k: Any) -> Any:
        raise AssertionError

    def graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        self.sent.append((query.split("(")[0].split()[-1], variables))
        if "sponsorshipsAsSponsor" in query:
            return MINE
        if "repositoryOwner" in query:
            return self.page
        return {}


def test_your_sponsorships_both_ways() -> None:
    rows = sp.fetch_sponsorships(FakeApi())
    assert [row.label for row in rows] == [
        "You sponsor sam: $5 a month, since 2025-02-01.",
        "jo sponsors you: $25 once, since 2026-03-04.",
    ]
    assert [row.kind for row in rows] == ["sponsorship", "person"]


def test_a_persons_tiers_with_prices_and_no_custom_amount() -> None:
    rows = sp.fetch_sponsor_page(FakeApi(), "sam")
    assert rows[0].label == (
        "sam takes sponsorships. You do not sponsor them yet. Free screen reader tools."
    )
    assert [row.label for row in rows[1:]] == [
        "$5 a month: Coffee. Keeps the lights on.",
        "$100 once: Big thanks.",
    ]
    assert rows[1].kind == "sponsor_tier" and rows[1].repo == "sam" and rows[1].key == "T5"
    none = sp.fetch_sponsor_page(FakeApi({"repositoryOwner": {"hasSponsorsListing": False}}), "x")
    assert none[0].label == "x does not take sponsorships on GitHub Sponsors."
    with pytest.raises(sp.SponsorError, match="no account called y"):
        sp.fetch_sponsor_page(FakeApi({"repositoryOwner": None}), "y")


def test_sponsoring_and_cancelling_send_what_was_chosen() -> None:
    api = FakeApi()
    said = sp.sponsor(api, "sam", "T5", "$5 a month", public=False)
    assert said == "You now sponsor sam privately, $5 a month. GitHub sends you a receipt."
    assert api.sent[-1][1] == {"login": "sam", "tier": "T5", "privacy": "PRIVATE"}
    assert sp.cancel_sponsorship(api, "sam").startswith("Cancelled your sponsorship of sam.")
    assert sp.SponsorError.code == "QUILL-GITHUB-SPONSORS"


def test_both_views_reach_their_loader(monkeypatch: Any) -> None:
    from quill.core.github.explore_extra_views import fetch_extra_view

    monkeypatch.setattr(sp, "fetch_sponsorships", lambda _api, warnings: ["mine"])
    monkeypatch.setattr(sp, "fetch_sponsor_page", lambda _api, login: [login])
    provider = SimpleNamespace(token="t", is_authenticated=True)
    ask = {"repo": "", "query": "", "limit": 5, "warnings": []}
    assert fetch_extra_view(provider, "sponsorships", **ask) == ["mine"]
    assert fetch_extra_view(provider, "person_sponsor", person="@sam", **ask) == ["sam"]
