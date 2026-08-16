"""AudioPub v1 (Discover) and the branch-smart Find routes.

Pinned here: the AudioPub parser never raises on junk and never stores
anything (the rows are live URLs, uploaders keep their rights); Find anchored
on the Podcasts branch asks the real search API and answers with show
folders (the Double Tap report, 2026-08-16); Find anchored on a
catalog-served axis answers scoped and instant from the local store.
"""

from __future__ import annotations

import json
from pathlib import Path

from quill.core.radio import audiopub, branch_find
from quill.core.radio.catalog.refresh import SourceSpec, refresh
from quill.core.radio.catalog.store import CatalogStore, StationRow

_FEED = {
    "audios": [
        {
            "id": "abc-1",
            "title": "Playing windows 7 minesweeper.",
            "path": "audio/abc-1",
            "plays": 42,
            "user": {"name": "keoku", "displayName": "keoku"},
        },
        {"id": "no-title", "path": "audio/x"},
        "junk",
        {"id": "no-path", "title": "Orphan"},
    ],
    "count": 2990,
    "hasMore": True,
}


def test_audiopub_parser_keeps_good_rows_and_shrugs_at_junk() -> None:
    rows = audiopub.parse_discover(json.dumps(_FEED))
    assert len(rows) == 1
    row = rows[0]
    assert row.stream_url == "https://audiopub.site/audio/abc-1"
    assert row.source == "AudioPub"
    assert row.is_recording is True  # a finished work: timeline + resume
    assert row.tags == ("by keoku", "played 42 times")
    assert audiopub.parse_discover("not json at all") == []


def test_audiopub_browse_offers_discover_and_more(monkeypatch) -> None:
    from quill.core.radio import browse_sources

    monkeypatch.setattr(audiopub, "_fetch", lambda url: json.dumps(_FEED))
    roots = dict(browse_sources.visible_roots(None))
    assert roots["audiopub"] == "AudioPub (Community Audio)"
    shelf = browse_sources.browse("audiopub", safe_mode=False, favorites=None)
    assert [n.label for n in shelf] == ["Discover"]
    rows = browse_sources.browse(shelf[0].node_id, safe_mode=False, favorites=None)
    assert rows[0].station is not None and rows[-1].label == "More to discover"
    assert rows[-1].node_id == "audiopubdiscover:2"


def test_find_on_the_podcasts_branch_asks_the_real_search_api(monkeypatch) -> None:
    from quill.core.podcasts import itunes_search

    shows = [
        itunes_search.PodcastSearchResult(
            title="Double Tap", feed_url="https://f/1", artist="AMI", collection_id="123"
        ),
        itunes_search.PodcastSearchResult(title="No Id", feed_url="https://f/2"),
    ]
    monkeypatch.setattr(
        "quill.core.podcasts.itunes_search.search_podcasts", lambda q, safe_mode=False: shows
    )
    fast = branch_find.fast_find("apple", "double tap", safe_mode=False)
    assert fast is not None
    nodes, provenance = fast
    assert [n.label for n in nodes] == ["Double Tap"]  # no collection id, no folder
    assert nodes[0].node_id == "appleshow:123" and nodes[0].is_folder
    assert "podcast directory" in provenance


def _rb_row(key: str, name: str, country: str = "", language: str = "") -> StationRow:
    return StationRow(
        key=key,
        name=name,
        stream_url=f"https://example.org/{key}",
        country=country,
        language=language,
        source_id="radio_browser",
        source_record_id=key,
    )


def test_find_on_a_catalog_axis_answers_scoped_and_local(tmp_path: Path) -> None:
    store = CatalogStore(tmp_path)
    rows = [
        _rb_row("fr1", "Jazz Paris", country="France"),
        _rb_row("us1", "Jazz Kansas", country="The United States Of America"),
    ]
    refresh([SourceSpec("radio_browser", "RB", lambda: iter([rows]))], store, now=1000.0)
    fast = branch_find.fast_find("rbcountry:France", "jazz", safe_mode=False, catalog=store)
    assert fast is not None
    nodes, provenance = fast
    assert [n.label for n in nodes] == ["Jazz Paris (France)"]  # scoped: Kansas stays out
    assert provenance == "from your catalog"
    # The axis root is unscoped -- the whole directory, still instant.
    all_fast = branch_find.fast_find("rbcountry", "jazz", safe_mode=False, catalog=store)
    assert all_fast is not None and len(all_fast[0]) == 2
    store.close()


def test_find_everywhere_else_falls_back_to_the_crawl(tmp_path: Path) -> None:
    assert branch_find.fast_find("m3u", "jazz", safe_mode=False) is None
    assert branch_find.fast_find("youtube", "jazz", safe_mode=False) is None
    assert branch_find.fast_find("rbcountry", "jazz", safe_mode=False, catalog=None) is None


def test_ccmixter_streams_get_their_referer() -> None:
    """ccMixter's content host 403s without a Referer (measured 2026-08-16);
    the one place that knowledge lives feeds both mpv and the recorder."""
    from quill.core.radio.recording_commands import build_record_command
    from quill.core.radio.stream_headers import referrer_for

    assert referrer_for("https://ccmixter.org/content/A/B.mp3") == "https://ccmixter.org/"
    assert referrer_for("https://example.org/live.mp3") == ""
    assert referrer_for("not a url") == ""
    args = build_record_command(
        "ffmpeg",
        "https://ccmixter.org/content/A/B.mp3",
        Path("out.mp3"),
        format="mp3",
        bitrate_kbps=128,
        duration_seconds=60,
    )
    assert "-referer" in args and args[args.index("-referer") + 1] == "https://ccmixter.org/"
    plain = build_record_command(
        "ffmpeg",
        "https://example.org/live.mp3",
        Path("out.mp3"),
        format="mp3",
        bitrate_kbps=128,
        duration_seconds=60,
    )
    assert "-referer" not in plain


def test_gutenberg_topics_page_with_an_honest_more_row(monkeypatch) -> None:
    """One page of 32 used to masquerade as the whole topic (2026-08-16)."""
    from quill.core.radio import browse_sources, gutendex
    from quill.core.radio.models import RadioStation

    calls: list[tuple[str, int]] = []

    def fake_audiobooks(*, topic="", language="", page=1, safe_mode=False, **_k):
        calls.append((topic or language, page))
        count = 32 if page == 1 else 5
        return [
            RadioStation(name=f"Book {page}-{i}", stream_url=f"https://g/{page}/{i}")
            for i in range(count)
        ]

    monkeypatch.setattr(gutendex, "audiobooks", fake_audiobooks)
    page1 = browse_sources.browse("gutenbergtopic:fiction", safe_mode=False, favorites=None)
    assert len(page1) == 33 and page1[-1].label == "More audiobooks"
    page2 = browse_sources.browse(page1[-1].node_id, safe_mode=False, favorites=None)
    assert len(page2) == 5  # short page: the end, no More row
    assert calls == [("fiction", 1), ("fiction", 2)]


def test_find_reaches_every_branch_with_a_search_engine(monkeypatch) -> None:
    """LibriVox answers with book folders; TuneIn with resolved rows; a route
    that blows up answers honestly instead of raising into the task."""
    from quill.core.media import librivox as lv
    from quill.core.media.librivox import LibriVoxBook
    from quill.core.radio import directory_search
    from quill.core.radio.models import RadioStation

    monkeypatch.setattr(
        lv, "search", lambda q, **_k: [LibriVoxBook("77", "Middlemarch", authors="Eliot")]
    )
    fast = branch_find.fast_find("librivoxauthors:E", "middlemarch", safe_mode=False)
    assert fast is not None
    nodes, provenance = fast
    assert nodes[0].node_id == "librivoxbook:77" and nodes[0].is_folder
    assert provenance == "searched LibriVox"

    monkeypatch.setattr(
        directory_search,
        "tunein_search_stations",
        lambda q, safe_mode=False: [RadioStation(name="BBC", stream_url="https://t/1")],
    )
    fast = branch_find.fast_find("tunein", "bbc", safe_mode=False)
    assert fast is not None and fast[0][0].station is not None
    assert fast[1] == "searched TuneIn"

    def _boom(q, **_k):
        raise RuntimeError("down")

    monkeypatch.setattr(lv, "search", _boom)
    nodes, provenance = branch_find.fast_find("librivox", "x", safe_mode=False)
    assert nodes == [] and "could not be reached" in provenance


def test_safe_mode_leaves_network_routes_to_the_crawl(tmp_path: Path) -> None:
    assert branch_find.fast_find("apple", "x", safe_mode=True) is None
    assert branch_find.fast_find("tunein", "x", safe_mode=True) is None
    store = CatalogStore(tmp_path)
    refresh(
        [SourceSpec("radio_browser", "RB", lambda: iter([[_rb_row("a", "Alpha FM")]]))],
        store,
        now=1000.0,
    )
    # The catalog route is local data and still answers in Safe Mode.
    fast = branch_find.fast_find("rbcountry", "alpha", safe_mode=True, catalog=store)
    assert fast is not None and len(fast[0]) == 1
    store.close()
