"""Plain-language batches (WP-R-021): how old, Trash with Undo, and questions that change nothing.

The grammar is fixed and read without AI; a fake site filters by status and
by WordPress's ``before`` and ``after`` (the item's date), as the REST API does.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from quill.core.wordpress.workbench_plain_age import find_age
from quill.core.wordpress.workbench_plain_batch import (
    PhraseError,
    answer,
    parse_request,
    resolve,
    run_site,
    undo_trash,
)

TODAY = date(2026, 11, 14)
SITES = ["Radio", "Shop"]


class _Address:
    wpcom_site = ""
    site_url = "https://radio.example"


class Site:
    def __init__(self, posts: list[dict[str, Any]]) -> None:
        self.address = _Address()
        self.posts = posts
        self.writes: list[tuple[str, str, Any]] = []
        self.asked: list[dict[str, Any]] = []

    def get(self, route: str, **params: Any) -> Any:
        base, _sep, tail = route.rpartition("/")
        if tail.isdigit():
            return dict(next(p for p in self.posts if p["id"] == int(tail)))
        return []

    def iter_collection(self, route: str, params: Any = None, **_kw: Any):
        params = dict(params or {})
        self.asked.append(params)
        for post in self.posts:
            if params.get("status") not in (None, "any") and post["status"] != params["status"]:
                continue
            if params.get("status") == "any" and post["status"] == "trash":
                continue
            if "before" in params and not post["date"] < params["before"]:
                continue
            if "after" in params and not post["date"] > params["after"]:
                continue
            yield dict(post)

    def post(self, route: str, body: Any = None, **_p: Any) -> Any:
        self.writes.append(("POST", route, body))
        ident = int(route.rsplit("/", 1)[1])
        for post in self.posts:
            if post["id"] == ident:
                post.update(body or {})
        return {"id": ident, **(body or {})}

    def delete(self, route: str, **params: Any) -> Any:
        self.writes.append(("DELETE", route, params))
        ident = int(route.rsplit("/", 1)[1])
        for post in self.posts:
            if post["id"] == ident:
                post["status"] = "trash"
        return {"id": ident, "status": "trash"}


def _post(ident: int, day: str, status: str = "draft") -> dict[str, Any]:
    return {
        "id": ident,
        "type": "post",
        "status": status,
        "date": f"{day}T12:00:00",
        "modified_gmt": f"{day}T12:00:00",
        "title": {"raw": f"Post {ident}"},
    }


def _site() -> Site:
    return Site([
        _post(1, "2024-02-10"),
        _post(2, "2025-06-01"),
        _post(3, "2026-10-30"),
        _post(4, "2023-05-05", status="publish"),
    ])


@pytest.mark.parametrize(
    ("words", "before", "after"),
    [
        ("older than a year", "2025-11-14T00:00:00", ""),
        ("older than six months", "2026-05-14T00:00:00", ""),
        ("older than 30 days", "2026-10-15T00:00:00", ""),
        ("older than 2 weeks", "2026-10-31T00:00:00", ""),
        ("newer than two weeks", "", "2026-10-31T00:00:00"),
        ("before March 2024", "2024-03-01T00:00:00", ""),
        ("before 2024", "2024-01-01T00:00:00", ""),
        ("before 15 March 2024", "2024-03-15T00:00:00", ""),
        ("before 2024-03-15", "2024-03-15T00:00:00", ""),
        ("after March 2024", "", "2024-03-31T23:59:59"),
        ("since 2025", "", "2024-12-31T23:59:59"),
    ],
)
def test_every_age_shape_becomes_wordpress_dates(words: str, before: str, after: str) -> None:
    age, rest = find_age(words, TODAY)
    assert (age.before, age.after, rest) == (before, after, "")


def test_an_age_qualifies_any_batch_and_unreadable_ages_are_said_not_guessed() -> None:
    asked = parse_request("move all drafts older than a year to pending on Radio", SITES,
                          today=TODAY)  # fmt: skip
    assert (asked.action, asked.value, asked.status, asked.age.before) == (
        "status", "pending", "draft", "2025-11-14T00:00:00",
    )  # fmt: skip
    assert asked.words == "Set draft posts older than a year to pending, on Radio."
    tagged = parse_request("add tag Archive to posts by Sam before March 2024", SITES, "Shop",
                           today=TODAY)  # fmt: skip
    assert (tagged.author, tagged.age.before) == ("Sam", "2024-03-01T00:00:00")
    for words, said in (
        ("move drafts older than a while to Trash", "does not read 'a while' as an age"),
        ("trash drafts before Smarch 2024", "does not read 'Smarch 2024' as a date"),
    ):
        with pytest.raises(PhraseError, match=said):
            parse_request(words, SITES, "Radio", today=TODAY)


def test_trash_is_previewed_sent_one_by_one_and_undone_with_each_status() -> None:
    site = _site()
    for words in (
        "Move every draft older than a year to Trash.",
        "move all drafts older than a year to the trash",
        "trash all drafts older than a year",
        "put every draft older than a year in the Trash",
    ):
        request = parse_request(words, SITES, "Radio", today=TODAY)
        assert request.action == "trash", words
    assert request.words == "Move draft posts older than a year to the Trash, on Radio."
    plan = resolve(request, "Radio", site)
    assert [r.key for r in plan.rows] == ["1", "2"], "only drafts from before 14 November 2025"
    assert site.asked[-1]["before"] == "2025-11-14T00:00:00"
    assert site.writes == [], "resolving sends nothing"
    said = run_site(site, plan, [1])  # the person unchecked the first
    assert said == ["Radio, Post 2: moved to the Trash"]
    assert site.writes == [("DELETE", "wp/v2/posts/2", {})]
    assert undo_trash(lambda _s: site, [plan]) == "Restored 1 item from the Trash."
    assert site.writes[-1] == ("POST", "wp/v2/posts/2", {"status": "draft"})


def test_a_question_counts_on_each_site_and_changes_nothing() -> None:
    radio, shop = _site(), Site([_post(9, "2020-01-01")])
    request = parse_request("How many drafts are older than six months on every site?", SITES,
                            today=TODAY)  # fmt: skip
    assert (request.action, request.status, request.changes) == ("count", "draft", False)
    plans = [resolve(request, "Radio", radio), resolve(request, "Shop", shop)]
    assert answer(request, plans) == (
        "Draft posts older than six months: 2 on Radio; 1 on Shop; 3 in all."
    )
    assert radio.writes == shop.writes == []
    pages = parse_request("how many pages are pending", SITES, "Radio", today=TODAY)
    assert (pages.kind, pages.status, pages.sites) == ("page", "pending", ("Radio",))
    there = parse_request("how many published posts are there before 2024?", SITES, "Shop",
                          today=TODAY)  # fmt: skip
    assert (there.status, there.age.before) == ("publish", "2024-01-01T00:00:00")
    assert answer(there, [resolve(there, "Shop", radio)]) == (
        "Published posts before 2024: 1 on Shop."
    )


def test_a_question_uses_wordpress_s_own_total_when_the_site_sends_one() -> None:
    class _Response:
        total = 42

    site = _site()
    site.request = lambda method, route, params=None: _Response()  # type: ignore[attr-defined]
    request = parse_request("how many posts are older than a year", SITES, "Radio", today=TODAY)
    assert resolve(request, "Radio", site).count == 42
