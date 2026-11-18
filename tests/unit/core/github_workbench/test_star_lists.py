"""Repositories > Star Lists (GitHub PRD 14.2)."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github import star_lists as sl

LISTS = {
    "viewer": {
        "lists": {
            "nodes": [
                {
                    "id": "UL_2",
                    "name": "Tools I use",
                    "description": "",
                    "isPrivate": True,
                    "items": {"nodes": []},
                },
                {
                    "id": "UL_1",
                    "name": "Screen readers",
                    "description": "The ones I test with",
                    "isPrivate": False,
                    "items": {
                        "nodes": [
                            {"nameWithOwner": "nvaccess/nvda", "description": "NVDA"},
                            {"nameWithOwner": "o/r", "description": None},
                        ]
                    },
                },
            ]
        }
    }
}


class FakeApi:
    def __init__(self) -> None:
        self.sent: list[tuple[str, dict[str, Any]]] = []

    def rest(self, *_a: Any, **_k: Any) -> Any:
        raise AssertionError

    def graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        self.sent.append((query.split("(")[0].split()[-1], variables))
        if "viewer" in query:
            return LISTS
        if "repository(owner" in query:
            return {"repository": {"id": "R_9"}}
        return {}


def test_lists_are_read_and_every_repository_starts_with_its_list() -> None:
    lists = sl.fetch_lists(FakeApi())
    assert [found.label for found in lists] == [
        "Screen readers: 2 repositories, public",
        "Tools I use: 0 repositories, private",
    ]
    warnings: list[str] = []
    rows = sl.list_rows(lists, warnings)
    assert [row.label for row in rows] == [
        "Screen readers: nvaccess/nvda, NVDA",
        "Screen readers: o/r",
    ]
    assert rows[0].kind == "repo" and rows[0].repo == "nvaccess/nvda"
    assert warnings == ["Empty star lists: Tools I use."]
    warnings.clear()
    assert sl.list_rows([], warnings) == [] and "no star lists yet" in warnings[0]


def test_making_changing_and_deleting_a_list() -> None:
    api = FakeApi()
    assert sl.create_list(api, " Reading ", private=True) == "Made the private star list Reading."
    assert api.sent[-1][1] == {"name": "Reading", "description": "", "isPrivate": True}
    with pytest.raises(sl.StarListError, match="needs a name"):
        sl.create_list(api, "  ", private=False)
    with pytest.raises(sl.StarListError, match="32 characters"):
        sl.create_list(api, "x" * 33, private=False)
    found = sl.fetch_lists(api)[0]
    said = sl.update_list(api, found, name="Readers", description="d", private=True)
    assert said == "Changed the star list Screen readers, now called Readers."
    assert sl.delete_list(api, found) == (
        "Deleted the star list Screen readers. Its repositories are still starred."
    )
    assert api.sent[-1][1] == {"listId": "UL_1"}


def test_a_repository_is_put_on_exactly_the_lists_chosen() -> None:
    api = FakeApi()
    lists = sl.fetch_lists(api)
    assert sl.set_lists_for(api, "o/r", lists) == "o/r is now on: Screen readers, Tools I use."
    assert api.sent[-1][1] == {"itemId": "R_9", "listIds": ["UL_1", "UL_2"]}
    assert sl.set_lists_for(api, "o/r", []) == "o/r is on no star lists now."
    assert sl.StarListError.code == "QUILL-GITHUB-STAR-LISTS"
