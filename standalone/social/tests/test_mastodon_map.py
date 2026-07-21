"""Pure-mapping tests for the Mastodon adapter.

These feed fixture dicts (shaped like Mastodon.py's status/poll/media responses)
to the module-level mapping functions and assert the resulting model fields.
They import NOTHING from Mastodon.py.
"""

from __future__ import annotations

from datetime import UTC, datetime

from quill_social.adapters.mastodon import (
    _html_to_text,
    _media_to_model,
    _poll_to_model,
    _status_to_item,
    _to_ms,
)


def _status_fixture(**over) -> dict:
    base = {
        "id": "109340",
        "uri": "https://example.social/users/ada/statuses/109340",
        "url": "https://example.social/@ada/109340",
        "content": "<p>Hello <b>world</b><br>second line</p>",
        "created_at": "2026-07-18T12:00:00.000Z",
        "visibility": "unlisted",
        "spoiler_text": "CW here",
        "sensitive": True,
        "language": "en",
        "in_reply_to_id": "109000",
        "replies_count": 3,
        "reblogs_count": 5,
        "favourites_count": 9,
        "favourited": True,
        "bookmarked": False,
        "reblogged": False,
        "account": {"id": "1", "acct": "ada@example.social", "display_name": "Ada"},
        "media_attachments": [
            {
                "type": "image",
                "url": "https://cdn/img.png",
                "mime_type": "image/png",
                "description": "an alt text",
            }
        ],
        "poll": None,
    }
    base.update(over)
    return base


def test_status_maps_all_core_fields():
    item = _status_to_item(_status_fixture(), account_id="acct_1")
    assert item.network == "mastodon"
    assert item.account_id == "acct_1"
    assert item.remote_id == "109340"
    assert item.uri == "https://example.social/@ada/109340"
    assert item.author_handle == "@ada@example.social"
    assert item.author_display == "Ada"
    assert item.author_id == "1"
    assert item.text == "Hello world\nsecond line"
    assert item.lang == "en"
    assert item.visibility == "unlisted"
    assert item.content_warning == "CW here"
    assert item.sensitive is True
    assert item.in_reply_to == "109000"
    assert item.reply_count == 3
    assert item.reblog_count == 5
    assert item.favourite_count == 9
    assert item.favourited is True
    assert item.created_at == 1_784_376_000_000


def test_status_media_maps_to_model_with_alt():
    item = _status_to_item(_status_fixture())
    assert len(item.media) == 1
    assert item.media[0].kind == "image"
    assert item.media[0].uri == "https://cdn/img.png"
    assert item.media[0].alt_text == "an alt text"
    assert item.media[0].has_alt
    assert item.missing_alt_count == 0


def test_status_boost_records_reblog_by_and_of():
    inner = _status_fixture(id="200", content="<p>boosted body</p>")
    boost = {
        "id": "999",
        "account": {"acct": "grace@example.social", "display_name": "Grace"},
        "reblog": inner,
    }
    item = _status_to_item(boost)
    assert item.text == "boosted body"
    assert item.remote_id == "200"
    assert item.reblog_of == "200"
    assert item.reblog_by == "@grace@example.social"


def test_poll_maps_options_and_totals():
    poll = _poll_to_model(
        {
            "multiple": False,
            "votes_count": 122,
            "voted": True,
            "own_votes": [0],
            "expires_at": "2026-07-20T00:00:00Z",
            "options": [
                {"title": "A", "votes_count": 42},
                {"title": "B", "votes_count": 80},
            ],
        }
    )
    assert poll is not None
    assert [(o.title, o.votes) for o in poll.options] == [("A", 42), ("B", 80)]
    assert poll.total_votes == 122
    assert poll.voted is True
    assert poll.own_votes == [0]


def test_poll_none_stays_none():
    assert _poll_to_model(None) is None
    assert _status_to_item(_status_fixture(poll=None)).poll is None


def test_media_helper_handles_missing_description():
    media = _media_to_model([{"type": "image", "url": "u", "description": ""}])
    assert media[0].alt_text == ""
    assert not media[0].has_alt


def test_html_to_text_strips_tags_and_unescapes():
    assert _html_to_text("<p>a &amp; b</p><p>c</p>") == "a & b\n\nc"
    assert _html_to_text("") == ""


def test_to_ms_accepts_datetime_and_iso_and_epoch():
    dt = datetime(2026, 7, 18, 12, 0, 0, tzinfo=UTC)
    assert _to_ms(dt) == 1_784_376_000_000
    assert _to_ms("2026-07-18T12:00:00Z") == 1_784_376_000_000
    assert _to_ms(1_784_376_000_000) == 1_784_376_000_000
    assert _to_ms(None) == 0
    assert _to_ms("") == 0
