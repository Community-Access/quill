"""Read/interact Mastodon models + parsers, pure parts."""

from __future__ import annotations

from datetime import UTC

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


# -- speech-shaped text: the API speaks HTML, QUILL must not ------------------
#
# Every human-authored field the Mastodon API returns is HTML. Nothing in the
# client decodes it, so before these parsers existed a status's content reached
# the display and the screen reader as literal "<p>...</p>". These tests are the
# guard: no parser output may contain markup, entities, or emoji.

_RAW_STATUS = {
    "id": "s1",
    "created_at": "2026-08-02T11:57:00.000Z",
    "url": "https://x.social/@alice/1",
    "account": {
        "id": "a1",
        "acct": "alice@x.social",
        "display_name": "Alice \U0001f33b",
        "note": "<p>Writer &amp; cook.</p><p>She/her \U0001f389</p>",
    },
    "content": (
        "<p>@bob @carol @dave Actually, that&#39;s wrong.</p>"
        '<p>See <a href="https://x.test/a/b">'
        '<span class="invisible">https://</span>'
        '<span class="ellipsis">x.test/a</span>'
        '<span class="invisible">/b</span></a></p>'
    ),
}


def _has_markup(value: str) -> bool:
    return "<" in value or ">" in value or "&amp;" in value or "&#" in value


def test_status_content_never_reaches_the_reader_as_html() -> None:
    status = social.status_from_json(_RAW_STATUS)
    assert status is not None
    assert not _has_markup(status.text), status.text
    assert "Actually, that's wrong." in status.text
    assert "x.test/a" in status.text  # the link's visible part survives
    assert "https://" not in status.text  # the hidden scheme does not


def test_status_content_condenses_the_leading_mention_pile() -> None:
    status = social.status_from_json(_RAW_STATUS)
    assert status is not None
    assert status.text.startswith("@bob and 2 more Actually,")


def test_account_bio_and_name_are_text_not_markup() -> None:
    status = social.status_from_json(_RAW_STATUS)
    assert status is not None and status.author is not None
    assert not _has_markup(status.author.note), status.author.note
    assert status.author.note == "Writer & cook.\nShe/her"
    assert status.author.display_name == "Alice"  # the sunflower is gone


def test_an_all_emoji_display_name_falls_back_to_the_handle() -> None:
    account = social.account_from_json({
        "id": "9",
        "acct": "sunny",
        "display_name": "\U0001f33b\U0001f33b",
    })
    assert account is not None and account.label == "@sunny"


def test_status_summary_is_one_sentence_with_a_relative_time() -> None:
    from datetime import datetime

    status = social.status_from_json(_RAW_STATUS)
    assert status is not None
    now = datetime(2026, 8, 2, 12, 0, 0, tzinfo=UTC)
    assert status.summary(now) == "3 minutes ago: @bob and 2 more Actually, that's wrong."


def test_a_content_warning_replaces_the_body_in_a_summary() -> None:
    status = social.status_from_json({
        "id": "s2",
        "created_at": "",
        "spoiler_text": "<b>spoilers</b>",
        "content": "<p>The butler did it.</p>",
    })
    assert status is not None
    assert status.summary() == "Content warning: spoilers"
    assert "butler" not in status.summary()


def test_a_boost_reports_the_original_text_and_who_shared_it() -> None:
    status = social.status_from_json({
        "id": "b1",
        "created_at": "",
        "account": {"id": "booster", "acct": "booster"},
        "reblog": {
            "id": "orig",
            "account": {"id": "author", "acct": "author"},
            "content": "<p>Original words.</p>",
            "url": "https://x.social/@author/1",
        },
    })
    assert status is not None
    assert status.text == "Original words."
    assert status.author is not None and status.author.acct == "author"
    assert status.boosted_by is not None and status.boosted_by.acct == "booster"
    assert status.summary().startswith("Boosted: Original words.")


def test_status_needs_an_id() -> None:
    assert social.status_from_json({"content": "<p>hi</p>"}) is None
    assert social.status_from_json("not a dict") is None


def test_an_unparseable_timestamp_leaves_the_time_out_rather_than_raising() -> None:
    status = social.status_from_json({"id": "s3", "created_at": "yesterday", "content": "hi"})
    assert status is not None
    assert status.relative_time() == ""
    assert status.summary() == "hi"


def test_account_statuses_parses_the_endpoint_rows(monkeypatch) -> None:
    captured: dict[str, str] = {}

    def _rows(method, url, *, data=None, token=None):
        captured["url"] = url
        return [_RAW_STATUS, {"no": "id"}]

    monkeypatch.setattr(social.client, "http_json_list", _rows)
    statuses = social.account_statuses("x.social", "tok", "a1", limit=5)
    assert captured["url"] == "https://x.social/api/v1/accounts/a1/statuses?limit=5"
    assert [s.id for s in statuses] == ["s1"]
    assert not _has_markup(statuses[0].text)
