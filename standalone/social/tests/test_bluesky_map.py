"""Pure-mapping tests for the Bluesky adapter.

These feed fixture dicts (shaped like the atproto SDK's FeedViewPost/PostView
models after ``model_dump()``) to the module-level mapping functions and assert
the resulting model fields. They import NOTHING from atproto.
"""

from __future__ import annotations

from quill_social.adapters.bluesky import (
    _embed_media,
    _feedview_to_item,
    _post_to_item,
    _to_ms,
)


def _post_fixture(**over) -> dict:
    base = {
        "uri": "at://did:plc:ada/app.bsky.feed.post/abc",
        "cid": "bafycid",
        "author": {
            "did": "did:plc:ada",
            "handle": "ada.bsky.social",
            "display_name": "Ada",
        },
        "record": {
            "text": "hello sky",
            "created_at": "2026-07-18T12:00:00.000Z",
            "langs": ["en"],
        },
        "reply_count": 2,
        "repost_count": 4,
        "like_count": 7,
        "indexed_at": "2026-07-18T12:01:00.000Z",
        "viewer": {"like": "at://did:plc:me/app.bsky.feed.like/1"},
    }
    base.update(over)
    return base


def test_post_maps_core_fields():
    item = _post_to_item(_post_fixture(), account_id="acct_bsky")
    assert item.network == "bluesky"
    assert item.account_id == "acct_bsky"
    assert item.remote_id == "at://did:plc:ada/app.bsky.feed.post/abc"
    assert item.uri == item.remote_id
    assert item.author_handle == "@ada.bsky.social"
    assert item.author_display == "Ada"
    assert item.author_id == "did:plc:ada"
    assert item.text == "hello sky"
    assert item.lang == "en"
    assert item.reply_count == 2
    assert item.reblog_count == 4
    assert item.favourite_count == 7
    assert item.favourited is True  # viewer.like present
    assert item.reblogged is False
    assert item.created_at == 1_784_376_000_000


def test_post_reply_sets_parent_and_root():
    post = _post_fixture(
        record={
            "text": "a reply",
            "created_at": "2026-07-18T12:05:00Z",
            "reply": {
                "parent": {"uri": "at://did:plc:x/app.bsky.feed.post/parent"},
                "root": {"uri": "at://did:plc:x/app.bsky.feed.post/root"},
            },
        }
    )
    item = _post_to_item(post)
    assert item.in_reply_to == "at://did:plc:x/app.bsky.feed.post/parent"
    assert item.thread_root == "at://did:plc:x/app.bsky.feed.post/root"


def test_post_embed_images_become_media():
    post = _post_fixture(
        embed={
            "images": [
                {"fullsize": "https://cdn/full.jpg", "thumb": "t", "alt": "a cat"},
                {"thumb": "https://cdn/only-thumb.jpg", "alt": ""},
            ]
        }
    )
    item = _post_to_item(post)
    assert len(item.media) == 2
    assert item.media[0].uri == "https://cdn/full.jpg"
    assert item.media[0].alt_text == "a cat"
    assert item.media[1].uri == "https://cdn/only-thumb.jpg"
    assert item.missing_alt_count == 1


def test_post_self_labels_mark_sensitive():
    post = _post_fixture(labels=[{"val": "nsfw"}, {"val": "spoiler"}])
    item = _post_to_item(post)
    assert item.sensitive is True
    assert item.moderation_labels == ["nsfw", "spoiler"]


def test_feedview_repost_reason_sets_reblog_by():
    fv = {
        "post": _post_fixture(),
        "reason": {
            "$type": "app.bsky.feed.defs#reasonRepost",
            "by": {"handle": "grace.bsky.social", "did": "did:plc:grace"},
        },
    }
    item = _feedview_to_item(fv, account_id="acct_bsky")
    assert item.reblog_by == "@grace.bsky.social"
    assert item.reblog_of == item.remote_id


def test_feedview_without_post_wrapper_maps_directly():
    item = _feedview_to_item(_post_fixture())
    assert item.text == "hello sky"


def test_embed_media_handles_empty():
    assert _embed_media(None) == []
    assert _embed_media({}) == []


def test_to_ms_iso_and_epoch():
    assert _to_ms("2026-07-18T12:00:00Z") == 1_784_376_000_000
    assert _to_ms(None) == 0
