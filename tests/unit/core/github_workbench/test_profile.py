"""A person's profile as sentences (GitHub PRD 14.2)."""

from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github import profile as pf

TODAY = date(2026, 11, 18)


def _days() -> list[dict[str, Any]]:
    counts = {TODAY - timedelta(days=n): c for n, c in ((0, 0), (1, 3), (2, 1), (5, 9), (6, 2))}
    start = TODAY - timedelta(days=40)
    return [
        {
            "date": (start + timedelta(days=i)).isoformat(),
            "contributionCount": counts.get(start + timedelta(days=i), 0),
        }
        for i in range(41)
    ]


USER = {
    "login": "jeff",
    "name": "Jeff Bishop",
    "bio": "Accessibility.  ",
    "company": None,
    "location": "Tucson, Arizona",
    "websiteUrl": "https://example.org",
    "followers": {"totalCount": 120},
    "following": {"totalCount": 40},
    "status": {"message": "Back Monday", "emoji": ":palm_tree:"},
    "pinnedItems": {
        "nodes": [
            {
                "nameWithOwner": "community-access/quill",
                "description": "An editor",
                "stargazerCount": 12,
            },
            {"name": "abc", "description": "Notes", "url": "https://gist.github.com/abc"},
        ]
    },
    "contributionsCollection": {
        "totalCommitContributions": 900,
        "totalIssueContributions": 120,
        "totalPullRequestContributions": 200,
        "totalPullRequestReviewContributions": 1,
        "contributionCalendar": {
            "totalContributions": 15,
            "weeks": [{"contributionDays": _days()}],
        },
    },
}


class FakeApi:
    def __init__(self, user: Any = USER) -> None:
        self.user = user
        self.asked: list[str] = []

    def rest(self, *_a: Any, **_k: Any) -> Any:
        raise AssertionError

    def graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        self.asked.append("viewer" if "viewer" in query else variables["login"])
        return {"viewer" if "viewer" in query else "user": self.user}


def test_a_profile_reads_as_sentences_with_the_calendar_as_numbers() -> None:
    rows = pf.fetch_profile(FakeApi(), "@jeff", today=TODAY)
    labels = [row.label for row in rows]
    assert labels[:4] == [
        "jeff (Jeff Bishop): Tucson, Arizona; 120 followers, following 40.",
        "Bio: Accessibility.",
        "Status: Back Monday",
        "Website: https://example.org",
    ]
    assert labels[4] == (
        "15 contributions in the last year: 900 commits, 120 issues, 200 pull requests "
        "and 1 review."
    )
    assert "Busiest day: 2026-11-13, 9 contributions." in labels
    assert "Longest streak: 2 days, ending 2026-11-13." in labels
    assert "Current streak: 2 days." in labels  # today empty does not break it
    assert "November 2026: 15 contributions." in labels
    assert labels.index("November 2026: 15 contributions.") < labels.index(
        "October 2026: 0 contributions."
    )
    assert labels[-2] == "Pinned: community-access/quill, An editor, 12 stars."
    assert rows[-2].kind == "repo" and rows[-2].repo == "community-access/quill"
    assert labels[-1] == "Pinned gist: Notes"


def test_your_own_profile_asks_for_the_viewer_and_a_missing_person_is_said() -> None:
    api = FakeApi()
    pf.fetch_profile(api, "", today=TODAY)
    assert api.asked == ["viewer"]
    with pytest.raises(pf.ProfileError, match="no account called nobody"):
        pf.fetch_profile(FakeApi(None), "nobody")
    assert pf.ProfileError.code == "QUILL-GITHUB-PROFILE"


def test_both_nodes_reach_their_loader(monkeypatch: Any) -> None:
    from quill.core.github.explore_extra_views import fetch_extra_view

    seen: list[str] = []
    monkeypatch.setattr(pf, "fetch_profile", lambda _api, login: seen.append(login) or [])
    provider = SimpleNamespace(token="t", is_authenticated=True)
    for view, person in (("my_profile", ""), ("person_profile", "sam")):
        rows = fetch_extra_view(
            provider, view, repo="", query="", limit=5, warnings=[], person=person
        )
        assert rows == []
    assert seen == ["", "sam"]
