"""Read/interact Mastodon models + parsers, pure parts."""

from __future__ import annotations

import pytest

from quill.core.mastodon import social
from quill.core.mastodon.client import MastodonError


def test_account_parse_and_label() -> None:
    a = social.account_from_json({"id": "1", "acct": "alice@x.social", "display_name": "Alice"})
    assert a is not None and a.label == "Alice (@alice@x.social)"
    b = social.account_from_json({"id": "2", "acct": "bob", "display_name": ""})
    assert b is not None and b.label == "@bob"
    assert social.account_from_json({"acct": "no-id"}) is None


def test_relationship_summary_reads_both_ways() -> None:
    r = social.relationship_from_json({"id": "1", "following": True, "followed_by": True})
    assert r is not None and "follow each other" in r.summary()
    r2 = social.relationship_from_json({"id": "1", "following": False, "followed_by": True})
    assert r2 is not None
    assert "do not follow them" in r2.summary() and "they follow you" in r2.summary()
    r3 = social.relationship_from_json({"id": "1", "following": False, "requested": True})
    assert r3 is not None and "requested to follow" in r3.summary()


def test_filter_parse_v2_and_v1() -> None:
    v2 = social.filter_from_json({"id": "9", "title": "No spoilers", "context": ["home", "public"]})
    assert v2 is not None and v2.title == "No spoilers" and "home" in v2.contexts
    v1 = social.filter_from_json({"id": "3", "phrase": "politics", "context": ["home"]})
    assert v1 is not None and v1.title == "politics"
    assert social.filter_from_json({"id": "4"}) is None  # no title/phrase


def test_users_in_post_collects_author_and_mentions() -> None:
    status = {
        "id": "s1",
        "account": {"id": "author", "acct": "author"},
        "mentions": [{"id": "m1", "acct": "mentioned"}],
    }
    users = social.users_in_post(status)
    assert [u.id for u in users] == ["author", "m1"]


def test_users_in_post_boost_lists_original_then_booster() -> None:
    boost = {
        "id": "b1",
        "account": {"id": "booster", "acct": "booster"},
        "reblog": {
            "id": "orig",
            "account": {"id": "author", "acct": "author"},
            "mentions": [{"id": "author", "acct": "author"}],  # duplicate -> deduped
        },
    }
    users = social.users_in_post(boost)
    assert [u.id for u in users] == ["author", "booster"]  # deduped, useful order


def test_add_to_list_maps_follow_first_error(monkeypatch) -> None:
    def _boom(method, url, *, data=None, token=None):
        raise MastodonError("Server error 404")

    monkeypatch.setattr(social.client, "_http_json", _boom)
    with pytest.raises(MastodonError, match="following an account before"):
        social.add_to_list("mastodon.social", "tok", "7", ["1"])
