"""Lemmy adapter mapping + fediverse-sibling routing."""

from __future__ import annotations

import json

import pytest

from quill_social.adapters.base import AdapterError, PublishRequest
from quill_social.adapters.lemmy import LemmyAdapter, parse_posts
from quill_social.adapters.mastodon import MastodonAdapter
from quill_social.adapters.registry import adapter_for
from quill_social.capabilities import default_for
from quill_social.model import Account

LEMMY = json.dumps(
    {
        "posts": [
            {
                "post": {
                    "id": 1,
                    "name": "Accessible aggregators",
                    "body": "A good read.",
                    "ap_id": "https://lemmy.ml/post/1",
                    "published": "2026-01-02T18:30:02Z",
                },
                "creator": {
                    "name": "alice",
                    "actor_id": "https://lemmy.ml/u/alice",
                    "display_name": "Alice",
                },
                "community": {"name": "technology"},
                "counts": {"comments": 3, "score": 42},
            }
        ]
    }
).encode("utf-8")


def test_parse_posts_maps_fields():
    items = parse_posts(LEMMY, account_id="acc")
    assert len(items) == 1
    it = items[0]
    assert it.network == "lemmy"
    assert it.remote_id == "https://lemmy.ml/post/1"
    assert it.uri == "https://lemmy.ml/post/1"
    assert it.author_display == "Alice"
    assert "[technology]" in it.text
    assert "Accessible aggregators" in it.text
    assert it.reply_count == 3
    assert it.favourite_count == 42
    assert it.created_at > 0


def test_adapter_home_timeline_and_read_only():
    adapter = LemmyAdapter(instance="https://lemmy.ml/", account_id="acc", fetch=lambda u: LEMMY)
    assert adapter.instance == "lemmy.ml"  # normalized
    items = adapter.home_timeline()
    assert items[0].remote_id == "https://lemmy.ml/post/1"
    with pytest.raises(AdapterError) as exc:
        adapter.publish(PublishRequest(text="hi"))
    assert exc.value.kind == "permission"
    assert LemmyAdapter.available() is True


def test_registry_routes_lemmy():
    adapter = adapter_for(Account(network="lemmy", instance="lemmy.ml"))
    assert isinstance(adapter, LemmyAdapter)


def test_registry_routes_mastodon_compatible_siblings():
    for network in ("pixelfed", "gotosocial", "firefish"):
        adapter = adapter_for(Account(network=network, instance=f"{network}.example"))
        assert isinstance(adapter, MastodonAdapter)


def test_capability_profiles():
    lemmy = default_for("lemmy")
    assert lemmy.supports_bookmarks is True
    assert lemmy.max_media_attachments == 0
    # Siblings inherit the Mastodon baseline but keep their own network name.
    pixelfed = default_for("pixelfed")
    assert pixelfed.network == "pixelfed"
    assert pixelfed.supports_edit is True  # mastodon-like
