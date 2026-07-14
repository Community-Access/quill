"""Tests for podcast OPML import/export (nested folders, local-show
exclusion, duplicate detection) -- pure, no network."""

from __future__ import annotations

import pytest

from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.opml import OpmlError, export_opml, import_opml, parse_opml
from quill.core.podcasts.subscriptions import PodcastLibrary


def test_export_opml_excludes_local_shows() -> None:
    library = PodcastLibrary()
    library.add_show(PodcastShow(id="s1", title="Real Show", feed_url="https://x/feed.xml"))
    library.add_show(PodcastShow(id="s2", title="Local Show", is_local=True))
    xml = export_opml(library)
    assert "Real Show" in xml
    assert "Local Show" not in xml


def test_export_opml_nests_shows_under_folders() -> None:
    library = PodcastLibrary()
    folder = library.add_folder("News")
    library.add_show(
        PodcastShow(id="s1", title="Show A", feed_url="https://a/feed.xml", folder_id=folder.id)
    )
    xml = export_opml(library)
    news_index = xml.index('text="News"')
    show_index = xml.index('xmlUrl="https://a/feed.xml"')
    closing_after_show = xml.index("</outline>", show_index)
    assert news_index < show_index < closing_after_show


def test_export_import_round_trip_preserves_folder_structure() -> None:
    library = PodcastLibrary()
    tech = library.add_folder("Tech")
    deep_dives = library.add_folder("Deep Dives", parent_folder_id=tech.id)
    library.add_show(
        PodcastShow(id="s1", title="Show A", feed_url="https://a/feed.xml", folder_id=deep_dives.id)
    )
    xml = export_opml(library)

    fresh = PodcastLibrary()
    added, skipped = import_opml(fresh, xml)
    assert len(added) == 1
    assert skipped == 0
    imported_show = fresh.find_show_by_feed_url("https://a/feed.xml")
    assert imported_show is not None
    folder = fresh.find_folder(imported_show.folder_id)  # type: ignore[arg-type]
    assert folder is not None and folder.name == "Deep Dives"
    parent = fresh.find_folder(folder.parent_folder_id)  # type: ignore[arg-type]
    assert parent is not None and parent.name == "Tech"


def test_import_opml_skips_duplicate_feed_urls() -> None:
    library = PodcastLibrary()
    library.add_show(PodcastShow(id="s1", title="Existing", feed_url="https://a/feed.xml"))
    opml_text = (
        '<opml version="2.0"><body>'
        '<outline type="rss" text="Existing" xmlUrl="https://a/feed.xml"/>'
        '<outline type="rss" text="New" xmlUrl="https://b/feed.xml"/>'
        "</body></opml>"
    )
    added, skipped = import_opml(library, opml_text)
    assert len(added) == 1
    assert added[0].feed_url == "https://b/feed.xml"
    assert skipped == 1
    assert len(library.shows) == 2


def test_parse_opml_ignores_outlines_without_xml_url() -> None:
    opml_text = '<opml version="2.0"><body><outline text="No Feed Here"/></body></opml>'
    assert parse_opml(opml_text) == []


def test_parse_opml_raises_on_malformed_xml() -> None:
    with pytest.raises(OpmlError):
        parse_opml("<not-valid-xml")


def test_parse_opml_returns_empty_list_without_body() -> None:
    assert parse_opml('<opml version="2.0"></opml>') == []
