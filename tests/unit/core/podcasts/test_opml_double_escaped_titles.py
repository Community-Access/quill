"""Titles an exporter escaped twice arrive readable (check.md, Downcast export).

Downcast writes ``text="We&amp;apos;re Alive"``. The XML parser undoes one
layer and leaves the literal ``We&apos;re Alive``, which a screen reader spells
out on every row -- and a refresh never renames a show, so it never heals.
"""

from __future__ import annotations

from quill.core.podcasts.opml import parse_opml

_DOWNCAST = """<?xml version="1.0" encoding="UTF-8"?>
<opml version="1.0">
  <head><title>Downcast Podcasts</title></head>
  <body>
    <outline text="Rock &amp;amp; Roll" title="Rock &amp;amp; Roll">
      <outline text="We&amp;apos;re Alive" type="rss" title="We&amp;apos;re Alive"
               xmlUrl="https://example.com/alive.xml" htmlUrl="https://example.com" />
    </outline>
    <outline text="Hollywood &amp; Crime" type="rss" title="Hollywood &amp; Crime"
             xmlUrl="https://example.com/crime.xml" />
  </body>
</opml>
"""


def test_double_escaped_title_is_unescaped() -> None:
    shows = parse_opml(_DOWNCAST)
    assert shows[0].title == "We're Alive"


def test_double_escaped_folder_name_is_unescaped() -> None:
    shows = parse_opml(_DOWNCAST)
    assert shows[0].folder_path == ["Rock & Roll"]


def test_singly_escaped_title_is_unchanged() -> None:
    shows = parse_opml(_DOWNCAST)
    assert shows[1].title == "Hollywood & Crime"
