"""Nested OPML import/export round-trips."""

from __future__ import annotations

import pytest

from quill_social.services.opml_io import (
    OpmlError,
    OpmlFeedEntry,
    export_opml,
    parse_opml,
)

NESTED = """<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <head><title>Subs</title></head>
  <body>
    <outline text="News">
      <outline text="Tech">
        <outline type="rss" text="The Verge" title="The Verge"
                 xmlUrl="https://theverge.com/rss" htmlUrl="https://theverge.com"/>
      </outline>
      <outline type="rss" text="AP" xmlUrl="https://ap.example/rss"/>
    </outline>
    <outline type="rss" text="Top-level feed" xmlUrl="https://root.example/feed"/>
  </body>
</opml>
"""


def test_parse_nested_folders():
    feeds = parse_opml(NESTED)
    by_url = {f.feed_url: f for f in feeds}
    assert len(feeds) == 3
    assert by_url["https://theverge.com/rss"].folder_path == ["News", "Tech"]
    assert by_url["https://theverge.com/rss"].site_url == "https://theverge.com"
    assert by_url["https://ap.example/rss"].folder_path == ["News"]
    assert by_url["https://root.example/feed"].folder_path == []


def test_parse_rejects_dtd():
    hostile = '<?xml version="1.0"?><!DOCTYPE opml [<!ENTITY x "y">]><opml></opml>'
    with pytest.raises(OpmlError):
        parse_opml(hostile)


def test_parse_empty():
    assert parse_opml("") == []
    assert parse_opml("<opml><head/></opml>") == []


def test_export_then_parse_round_trip():
    entries = [
        OpmlFeedEntry(
            title="The Verge",
            feed_url="https://theverge.com/rss",
            site_url="https://theverge.com",
            folder_path=["News", "Tech"],
        ),
        OpmlFeedEntry(
            title="AP", feed_url="https://ap.example/rss", folder_path=["News"]
        ),
        OpmlFeedEntry(title="Root", feed_url="https://root.example/feed"),
    ]
    xml = export_opml(entries)
    assert xml.startswith("<?xml")
    reparsed = parse_opml(xml)
    by_url = {f.feed_url: f for f in reparsed}
    assert by_url["https://theverge.com/rss"].folder_path == ["News", "Tech"]
    assert by_url["https://ap.example/rss"].folder_path == ["News"]
    assert by_url["https://root.example/feed"].folder_path == []


def test_export_shares_folder_elements():
    # Two feeds in the same folder must nest under one folder outline, not two.
    entries = [
        OpmlFeedEntry(title="One", feed_url="https://one.example/f", folder_path=["A"]),
        OpmlFeedEntry(title="Two", feed_url="https://two.example/f", folder_path=["A"]),
    ]
    xml = export_opml(entries)
    assert xml.count('text="A"') == 1


def test_category_round_trip():
    entries = [
        OpmlFeedEntry(
            title="Tagged",
            feed_url="https://t.example/feed",
            categories=["tech", "ai"],
        )
    ]
    xml = export_opml(entries)
    assert 'category="tech,ai"' in xml
    reparsed = parse_opml(xml)
    assert reparsed[0].categories == ["tech", "ai"]


def test_import_parses_category_attribute():
    opml = (
        '<opml version="2.0"><body>'
        '<outline type="rss" text="X" xmlUrl="https://x.example/f" '
        'category="news, world"/></body></opml>'
    )
    feeds = parse_opml(opml)
    assert feeds[0].categories == ["news", "world"]
