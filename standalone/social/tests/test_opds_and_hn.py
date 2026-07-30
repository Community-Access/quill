"""OPDS book-browse bridge and Hacker News adapters."""

from __future__ import annotations

import json

import pytest

from quill_social.adapters.base import AdapterError, PublishRequest
from quill_social.adapters.hackernews import HackerNewsAdapter
from quill_social.adapters.opds import OpdsAdapter, parse_catalog
from quill_social.adapters.registry import adapter_for
from quill_social.capabilities import default_for
from quill_social.model import Account

OPDS = b"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Standard Ebooks</title>
  <entry>
    <title>Frankenstein</title>
    <id>url:frankenstein</id>
    <author><name>Mary Shelley</name></author>
    <summary>A novel.</summary>
    <link rel="http://opds-spec.org/acquisition"
          type="application/epub+zip" href="/ebooks/frankenstein.epub"/>
    <link rel="alternate" href="https://standardebooks.org/ebooks/frankenstein"/>
  </entry>
</feed>
"""


def test_opds_parse_and_link_resolution():
    items = parse_catalog(
        OPDS, account_id="acc", base_url="https://standardebooks.org/feeds/opds/all"
    )
    assert len(items) == 1
    it = items[0]
    assert it.network == "opds"
    assert it.author_display == "Mary Shelley"
    assert "Frankenstein" in it.text
    # acquisition (download) link resolved and used as the item uri
    assert it.uri == "https://standardebooks.org/ebooks/frankenstein.epub"


def test_opds_adapter_read_only_and_registry():
    adapter = OpdsAdapter(
        catalog_url="https://standardebooks.org/feeds/opds/all",
        account_id="acc",
        fetch=lambda u: OPDS,
    )
    assert adapter.home_timeline()[0].author_display == "Mary Shelley"
    with pytest.raises(AdapterError) as exc:
        adapter.publish(PublishRequest(text="x"))
    assert exc.value.kind == "permission"
    routed = adapter_for(Account(network="opds", instance="https://x/opds"))
    assert isinstance(routed, OpdsAdapter)
    assert default_for("opds").supports_bookmarks is True


# --- Hacker News ---

_HN_ITEMS = {
    "https://hacker-news.firebaseio.com/v0/topstories.json": b"[1, 2, 3]",
    "https://hacker-news.firebaseio.com/v0/item/1.json": json.dumps(
        {
            "id": 1,
            "type": "story",
            "title": "Show HN: An accessible RSS reader",
            "by": "ada",
            "url": "https://example.com/reader",
            "time": 1767378602,
            "score": 128,
            "descendants": 42,
        }
    ).encode(),
    "https://hacker-news.firebaseio.com/v0/item/2.json": json.dumps(
        {"id": 2, "type": "comment", "by": "bob", "text": "no title"}
    ).encode(),
    "https://hacker-news.firebaseio.com/v0/item/3.json": json.dumps(
        {"id": 3, "type": "story", "title": "Ask HN: Best braille display?", "by": "cara",
         "time": 1767378000, "score": 55, "descendants": 20}
    ).encode(),
}


def _hn_fetch(url):
    return _HN_ITEMS[url]


def test_hn_reads_stories_and_skips_titleless():
    adapter = HackerNewsAdapter(account_id="acc", listing="top", fetch=_hn_fetch)
    items = adapter.home_timeline()
    # story 1 and story 3 kept; comment 2 (no title) skipped.
    assert [it.remote_id for it in items] == ["1", "3"]
    first = items[0]
    assert first.network == "hackernews"
    assert first.author_display == "ada"
    assert "Show HN" in first.text
    assert first.uri == "https://example.com/reader"
    assert first.favourite_count == 128
    assert first.reply_count == 42
    assert first.created_at == 1767378602000


def test_hn_read_only_and_registry():
    adapter = HackerNewsAdapter(fetch=_hn_fetch)
    with pytest.raises(AdapterError) as exc:
        adapter.publish(PublishRequest(text="x"))
    assert exc.value.kind == "permission"
    routed = adapter_for(Account(network="hackernews", instance="best"))
    assert isinstance(routed, HackerNewsAdapter)
    assert routed._listing == "best"
    assert default_for("hackernews").char_limit == 0
