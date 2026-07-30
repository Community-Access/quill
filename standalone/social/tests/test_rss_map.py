"""RSS/Atom parsing, entry mapping, and the read-only adapter contract."""

from __future__ import annotations

import gzip
import zlib

import pytest

from quill_social.adapters.base import AdapterError, PublishRequest
from quill_social.adapters.registry import adapter_for
from quill_social.adapters.rss import (
    FetchResult,
    RssAdapter,
    _decode_body,
    default_fetch,
    entry_to_item,
    parse_feed,
    parse_json_feed,
    strip_html,
)
from quill_social.capabilities import default_for
from quill_social.model import Account

RSS_2 = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/"
     xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>Accessible Tech Weekly</title>
    <link>https://example.com/</link>
    <description>News</description>
    <item>
      <title>Screen readers in 2026</title>
      <link>https://example.com/sr-2026</link>
      <guid isPermaLink="false">post-0001</guid>
      <dc:creator>Ada Lovelace</dc:creator>
      <pubDate>Tue, 10 Jun 2003 04:00:00 GMT</pubDate>
      <description>&lt;p&gt;A &lt;b&gt;great&lt;/b&gt; year.&lt;/p&gt;</description>
      <enclosure url="https://example.com/ep1.mp3" length="123" type="audio/mpeg"/>
    </item>
    <item>
      <title>Older post</title>
      <link>https://example.com/older</link>
      <guid>post-0000</guid>
      <pubDate>Mon, 09 Jun 2003 04:00:00 GMT</pubDate>
      <description>plain summary</description>
    </item>
  </channel>
</rss>
"""

ATOM = b"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Example</title>
  <link rel="alternate" href="https://atom.example/"/>
  <entry>
    <title>Atom Entry One</title>
    <link rel="alternate" href="https://atom.example/one"/>
    <id>urn:uuid:1</id>
    <updated>2026-01-02T18:30:02Z</updated>
    <author><name>Grace Hopper</name></author>
    <summary>Summary text.</summary>
  </entry>
</feed>
"""


def test_parse_rss_channel_and_entries():
    feed = parse_feed(RSS_2)
    assert feed.title == "Accessible Tech Weekly"
    assert feed.home_url == "https://example.com/"
    assert len(feed.entries) == 2
    first = feed.entries[0]
    assert first.title == "Screen readers in 2026"
    assert first.link == "https://example.com/sr-2026"
    assert first.guid == "post-0001"
    assert first.author == "Ada Lovelace"
    assert first.published_ms > 0
    assert first.summary == "A great year."  # HTML stripped
    assert len(first.enclosures) == 1
    assert first.enclosures[0].kind == "audio"
    assert first.enclosures[0].uri == "https://example.com/ep1.mp3"


def test_parse_atom():
    feed = parse_feed(ATOM)
    assert feed.title == "Atom Example"
    assert feed.home_url == "https://atom.example/"
    assert len(feed.entries) == 1
    entry = feed.entries[0]
    assert entry.title == "Atom Entry One"
    assert entry.link == "https://atom.example/one"
    assert entry.guid == "urn:uuid:1"
    assert entry.author == "Grace Hopper"
    assert entry.published_ms > 0


def test_entry_to_item_mapping():
    entry = parse_feed(RSS_2).entries[0]
    item = entry_to_item(entry, account_id="acct_rss", feed_url="https://example.com/feed")
    assert item.network == "rss"
    assert item.account_id == "acct_rss"
    assert item.remote_id == "post-0001"
    assert item.uri == "https://example.com/sr-2026"
    assert item.author_display == "Ada Lovelace"
    assert "Screen readers in 2026" in item.text
    assert "great year" in item.text
    assert len(item.media) == 1


def test_strip_html():
    assert strip_html("<p>Hello <b>world</b></p>") == "Hello world"
    assert strip_html("plain") == "plain"
    assert strip_html("") == ""


def test_reject_dtd():
    hostile = b'<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY a "x">]><rss></rss>'
    with pytest.raises(AdapterError) as exc:
        parse_feed(hostile)
    assert exc.value.kind == "validation"


def test_parse_rejects_garbage():
    with pytest.raises(AdapterError):
        parse_feed(b"not xml at all")
    with pytest.raises(AdapterError):
        parse_feed(b"")


def test_adapter_home_timeline_newest_first():
    adapter = RssAdapter(
        feed_url="https://example.com/feed",
        account_id="acct_rss",
        fetch=lambda url: RSS_2,
    )
    items = adapter.home_timeline()
    assert [it.remote_id for it in items] == ["post-0001", "post-0000"]  # newest first
    assert all(it.network == "rss" for it in items)


def test_adapter_limit_and_since_id():
    adapter = RssAdapter(feed_url="u", account_id="a", fetch=lambda url: RSS_2)
    assert len(adapter.home_timeline(limit=1)) == 1


def test_adapter_is_read_only():
    adapter = RssAdapter(feed_url="u", fetch=lambda url: RSS_2)
    for call in (
        lambda: adapter.publish(PublishRequest(text="hi")),
        lambda: adapter.set_favourite("x"),
        lambda: adapter.set_reblog("x"),
        lambda: adapter.delete("x"),
    ):
        with pytest.raises(AdapterError) as exc:
            call()
        assert exc.value.kind == "permission"


def test_adapter_available_and_capabilities():
    assert RssAdapter.available() is True
    caps = RssAdapter(feed_url="u").capabilities()
    assert caps.network == "rss"
    assert caps.supports_edit is False
    assert caps.supports_polls is False
    assert caps.max_media_attachments == 0
    assert caps.supports_bookmarks is True


def test_default_fetch_rejects_non_https():
    with pytest.raises(AdapterError) as exc:
        default_fetch("http://insecure.example/feed")
    assert exc.value.kind == "validation"


def test_registry_builds_rss_adapter():
    account = Account(network="rss", instance="https://example.com/feed")
    adapter = adapter_for(account)
    assert isinstance(adapter, RssAdapter)
    assert adapter.feed_url == "https://example.com/feed"


def test_rss_capability_profile_is_read_only():
    caps = default_for("rss")
    assert caps.supports_delete is False
    assert caps.supports_direct_messages is False
    assert caps.char_limit == 0


# -- JSON Feed ----------------------------------------------------------------

JSON_FEED = b"""{
  "version": "https://jsonfeed.org/version/1.1",
  "title": "JSON Feed Example",
  "home_page_url": "https://jf.example/",
  "items": [
    {
      "id": "jf-2",
      "url": "https://jf.example/2",
      "title": "Second",
      "content_html": "<p>Hello <b>HTML</b></p>",
      "date_published": "2026-02-02T10:00:00Z",
      "authors": [{"name": "Radia Perlman"}],
      "attachments": [
        {"url": "https://jf.example/2.mp3", "mime_type": "audio/mpeg"}
      ]
    },
    {
      "id": "jf-1",
      "url": "https://jf.example/1",
      "title": "First",
      "content_text": "Just text.",
      "date_published": "2026-02-01T10:00:00Z"
    }
  ]
}
"""


def test_parse_json_feed():
    feed = parse_json_feed(JSON_FEED)
    assert feed.title == "JSON Feed Example"
    assert feed.home_url == "https://jf.example/"
    assert len(feed.entries) == 2
    first = feed.entries[0]
    assert first.guid == "jf-2"
    assert first.link == "https://jf.example/2"
    assert first.title == "Second"
    assert first.author == "Radia Perlman"
    assert first.summary == "Hello HTML"  # HTML stripped
    assert first.published_ms > 0
    assert len(first.enclosures) == 1
    assert first.enclosures[0].kind == "audio"
    # content_text item keeps its plain text
    assert feed.entries[1].summary == "Just text."


def test_parse_feed_sniffs_json():
    feed = parse_feed(JSON_FEED)  # detected as JSON, not XML
    assert feed.title == "JSON Feed Example"
    assert len(feed.entries) == 2


def test_parse_feed_sniffs_json_with_bom_and_whitespace():
    feed = parse_feed(b"\xef\xbb\xbf\n  " + JSON_FEED)
    assert len(feed.entries) == 2


def test_parse_json_feed_rejects_non_jsonfeed_object():
    with pytest.raises(AdapterError) as exc:
        parse_feed(b'{"hello": "world"}')  # valid JSON, not a JSON Feed
    assert exc.value.kind == "validation"


def test_adapter_serves_json_feed():
    adapter = RssAdapter(feed_url="u", account_id="a", fetch=lambda url: JSON_FEED)
    items = adapter.home_timeline()
    assert [it.remote_id for it in items] == ["jf-2", "jf-1"]  # newest first


# -- gzip / deflate decode ----------------------------------------------------


def test_decode_body_gzip():
    assert _decode_body(gzip.compress(RSS_2), "gzip") == RSS_2


def test_decode_body_deflate_zlib_wrapped():
    assert _decode_body(zlib.compress(RSS_2), "deflate") == RSS_2


def test_decode_body_deflate_raw():
    comp = zlib.compressobj(wbits=-zlib.MAX_WBITS)
    raw = comp.compress(RSS_2) + comp.flush()
    assert _decode_body(raw, "deflate") == RSS_2


def test_decode_body_identity_passthrough():
    assert _decode_body(RSS_2, "") == RSS_2
    assert _decode_body(RSS_2, "identity") == RSS_2


# -- conditional GET / poll ---------------------------------------------------


def test_poll_falls_back_without_conditional_fetch():
    adapter = RssAdapter(feed_url="u", account_id="a", fetch=lambda url: RSS_2)
    poll = adapter.poll()
    assert poll.not_modified is False
    assert [it.remote_id for it in poll.items] == ["post-0001", "post-0000"]


def test_poll_sends_validators_and_returns_new_ones():
    seen = {}

    def cond(url, *, etag="", last_modified=""):
        seen["etag"] = etag
        seen["last_modified"] = last_modified
        return FetchResult(
            body=RSS_2, status=200, etag='"new-tag"', last_modified="Wed, 21 Oct 2026 07:28:00 GMT"
        )

    adapter = RssAdapter(feed_url="u", account_id="a", conditional_fetch=cond)
    poll = adapter.poll(etag='"old-tag"', last_modified="Mon, 01 Jan 2026 00:00:00 GMT")
    assert seen["etag"] == '"old-tag"'
    assert seen["last_modified"] == "Mon, 01 Jan 2026 00:00:00 GMT"
    assert poll.not_modified is False
    assert poll.etag == '"new-tag"'
    assert poll.last_modified == "Wed, 21 Oct 2026 07:28:00 GMT"
    assert len(poll.items) == 2


def test_poll_reports_not_modified_on_304():
    def cond(url, *, etag="", last_modified=""):
        return FetchResult(status=304, etag=etag, last_modified=last_modified)

    adapter = RssAdapter(feed_url="u", account_id="a", conditional_fetch=cond)
    poll = adapter.poll(etag='"tag"')
    assert poll.not_modified is True
    assert poll.items == []
    assert poll.etag == '"tag"'


# -- categories / tags --------------------------------------------------------

RSS_CATS = b"""<?xml version="1.0"?>
<rss version="2.0"><channel>
  <title>Cats</title><link>https://c.example/</link>
  <atom:link xmlns:atom="http://www.w3.org/2005/Atom"
             rel="hub" href="https://hub.example/"/>
  <atom:link xmlns:atom="http://www.w3.org/2005/Atom"
             rel="self" href="https://c.example/feed"/>
  <item>
    <title>Tagged</title><link>https://c.example/1</link><guid>1</guid>
    <category>Tech</category><category>AI</category><category>Tech</category>
  </item>
</channel></rss>
"""

ATOM_CATS = b"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Cats</title>
  <link rel="hub" href="https://hub.example/"/>
  <entry>
    <title>Tagged</title><link rel="alternate" href="https://a.example/1"/>
    <id>1</id>
    <category term="Science"/><category term="Space"/>
  </entry>
</feed>
"""


def test_rss_categories_and_hub():
    feed = parse_feed(RSS_CATS)
    assert feed.hub_url == "https://hub.example/"
    assert feed.self_url == "https://c.example/feed"
    assert feed.entries[0].categories == ["Tech", "AI"]  # deduped, order kept


def test_atom_categories_and_hub():
    feed = parse_feed(ATOM_CATS)
    assert feed.hub_url == "https://hub.example/"
    assert feed.entries[0].categories == ["Science", "Space"]


def test_json_feed_tags_become_categories():
    doc = (
        b'{"version":"https://jsonfeed.org/version/1.1","title":"T","items":['
        b'{"id":"1","title":"x","content_text":"y","tags":["news","world"]}]}'
    )
    feed = parse_feed(doc)
    assert feed.entries[0].categories == ["news", "world"]


def test_entry_to_item_carries_tags():
    entry = parse_feed(RSS_CATS).entries[0]
    item = entry_to_item(entry, account_id="a", feed_url="u")
    assert item.tags == ["Tech", "AI"]


def test_poll_surfaces_hub_url():
    def cond(url, *, etag="", last_modified=""):
        return FetchResult(body=RSS_CATS, status=200)

    poll = RssAdapter(feed_url="u", account_id="a", conditional_fetch=cond).poll()
    assert poll.hub_url == "https://hub.example/"
