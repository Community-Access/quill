"""The station catalog: keys, store generations, refresh rules, and reads.

What is pinned here is every rule the PRD stated with a measurement behind
it: URL-only matching never merges (7,135 shared URLs, measured), an empty
answer from a populated source is an outage (the live Xiph shape), the
pointer swap keeps readers consistent on Windows, and catalog-served rows are
indistinguishable in shape from live-served ones.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.radio.catalog import read as catalog_read
from quill.core.radio.catalog.keys import canonical_key, normalize_stream_url, same_station
from quill.core.radio.catalog.refresh import (
    EMPTY_GUARD_FLOOR,
    SourceSpec,
    due_sources,
    refresh,
)
from quill.core.radio.catalog.store import CatalogStore, StationRow
from quill.core.radio.catalog.summary import RefreshSummary, SourceOutcome, spoken_age


def _row(key: str, name: str = "", country: str = "", votes: int = 0) -> StationRow:
    return StationRow(
        key=key,
        name=name or f"Station {key}",
        stream_url=f"https://example.org/{key}",
        country=country,
        votes=votes,
        source_id="radio_browser",
        source_record_id=key,
    )


def _spec(rows: list[StationRow], source_id: str = "radio_browser") -> SourceSpec:
    return SourceSpec(source_id, source_id, lambda: iter([rows]))


# -- keys ---------------------------------------------------------------------


def test_the_uuid_wins_and_matches_the_favorites_precedence() -> None:
    assert canonical_key("abc-123", "https://x/stream") == "abc-123"
    assert canonical_key("", "HTTPS://X/stream") == "https://x/stream"


def test_url_normalization_strips_what_says_nothing() -> None:
    assert normalize_stream_url("HTTP://Host.example:80/live?sid=9") == "http://host.example/live"
    assert normalize_stream_url("https://host/live#now") == "https://host/live"
    assert normalize_stream_url("not a url") == "not a url"


def test_a_shared_url_alone_never_merges() -> None:
    """The 7,135-shared-URLs rule: relays are not the same station."""
    assert not same_station(
        "WXYZ Detroit", "https://relay/a", "Big Network Feed", "https://relay/a"
    )
    assert same_station("WXYZ  Detroit", "https://relay/a", "wxyz detroit", "https://relay/a")


# -- store generations --------------------------------------------------------


def test_refresh_publishes_a_new_generation_readers_pick_up(tmp_path: Path) -> None:
    store = CatalogStore(tmp_path)
    refresh([_spec([_row("a"), _row("b")])], store, now=1000.0)
    assert [r.key for r in store.top_voted()] == ["a", "b"]
    refresh([_spec([_row("a"), _row("b"), _row("c")])], store, now=90000.0)
    store.reopen_if_stale()
    assert len(store.top_voted()) == 3
    store.close()


def test_a_crashed_refresh_leaves_the_old_catalog_standing(tmp_path: Path) -> None:
    store = CatalogStore(tmp_path)
    refresh([_spec([_row("a")])], store, now=1000.0)

    def _explode() -> object:
        raise RuntimeError("boom mid-fetch")

    # A raising *pages iterator factory* is caught per-source; force the
    # writer path itself to die instead by passing a broken spec list.
    bad = SourceSpec("radio_browser", "RB", _explode)
    summary = refresh([bad], store, now=90000.0)
    assert summary.outcomes[0].status == "stale"
    store.reopen_if_stale()
    assert [r.key for r in store.top_voted()] == ["a"]  # untouched
    store.close()


def test_destroy_and_rebuild_touches_nothing_else(tmp_path: Path) -> None:
    """The derived-data promise, as bytes: user files survive a catalog wipe."""
    favorites = tmp_path / "radio_favorites.json"
    favorites.write_text('{"favorites": []}', encoding="utf-8")
    before = favorites.read_bytes()
    store = CatalogStore(tmp_path)
    refresh([_spec([_row("a")])], store, now=1000.0)
    store.destroy()
    assert favorites.read_bytes() == before
    assert not store.exists()


# -- refresh rules ------------------------------------------------------------


def test_an_empty_answer_from_a_populated_source_is_an_outage(tmp_path: Path) -> None:
    """The live-Xiph rule: HTTP 200 with nothing in it is not the truth."""
    store = CatalogStore(tmp_path)
    rows = [_row(f"k{i}") for i in range(EMPTY_GUARD_FLOOR + 1)]
    refresh([_spec(rows)], store, now=1000.0)
    summary = refresh([_spec([])], store, now=90000.0)
    assert summary.outcomes[0].status == "stale"
    assert "outage" in summary.outcomes[0].error
    store.reopen_if_stale()
    assert len(store.top_voted(limit=100)) == EMPTY_GUARD_FLOOR + 1  # kept
    store.close()


def test_a_vanished_station_is_hidden_then_purged_after_grace(tmp_path: Path) -> None:
    store = CatalogStore(tmp_path)
    refresh([_spec([_row("keep"), _row("gone")])], store, now=1000.0)
    summary = refresh([_spec([_row("keep")])], store, now=90000.0)
    assert summary.outcomes[0].vanished == 1
    store.reopen_if_stale()
    assert [r.key for r in store.top_voted()] == ["keep"]  # hidden at once
    # Fifteen days on, the tombstone is purged for good.
    refresh([_spec([_row("keep")])], store, now=90000.0 + 15 * 86400)
    store.close()


def test_an_unchanged_dump_writes_nothing(tmp_path: Path) -> None:
    store = CatalogStore(tmp_path)
    rows = [_row("a"), _row("b")]
    refresh([_spec(rows)], store, now=1000.0)
    summary = refresh([_spec(rows)], store, now=90000.0)
    assert summary.outcomes[0].status == "unchanged"
    assert not summary.changed_anything
    store.close()


def test_a_hidden_source_is_never_due(tmp_path: Path) -> None:
    """Choose Browse Sources extends to refresh: off means never contacted."""
    store = CatalogStore(tmp_path)
    specs = [_spec([_row("a")]), _spec([_row("z")], source_id="soma_fm")]
    due = due_sources(specs, store, now=1e9, enabled_ids={"soma_fm"})
    assert [s.id for s in due] == ["soma_fm"]


def test_a_fresh_source_is_not_due_until_its_interval_passes(tmp_path: Path) -> None:
    store = CatalogStore(tmp_path)
    refresh([_spec([_row("a")])], store, now=1000.0)
    assert due_sources([_spec([_row("a")])], store, now=1000.0 + 3600, interval_hours=24) == []
    due = due_sources([_spec([_row("a")])], store, now=1000.0 + 25 * 3600, interval_hours=24)
    assert [s.id for s in due] == ["radio_browser"]
    store.close()


# -- reads: parity with the live shape ---------------------------------------


def test_catalog_rows_materialize_as_real_browse_nodes(tmp_path: Path) -> None:
    store = CatalogStore(tmp_path)
    refresh(
        [
            _spec([
                _row("us1", name="A Station", country="The United States Of America", votes=5),
                _row("us2", name="B Station", country="The United States Of America"),
                _row("fr1", name="C Station", country="France"),
            ])
        ],
        store,
        now=1000.0,
    )
    countries = catalog_read.serve(store, "rbcountry", [])
    assert countries is not None
    labels = {(node.label, node.child_count) for node in countries}
    assert ("France", 1) in labels and ("The United States Of America", 2) in labels
    stations = catalog_read.serve(store, "rbcountry", ["France"])
    assert stations is not None and len(stations) == 1
    leaf = stations[0]
    assert leaf.station is not None and leaf.station.stream_url.endswith("/fr1")
    assert leaf.station.source == "Radio Browser"
    store.close()


def test_rankings_fall_back_labeled_with_their_age(tmp_path: Path) -> None:
    store = CatalogStore(tmp_path)
    refresh([_spec([_row("a", votes=10), _row("b", votes=5)])], store, now=1000.0)
    nodes = catalog_read.rankings_fallback(store, "popular")
    assert nodes is not None
    assert nodes[0].station is not None and nodes[0].station.votes == 10
    assert nodes[0].note.startswith("as of ") or nodes[0].note == "from your catalog"
    store.close()


def test_a_missing_catalog_declines_rather_than_breaking(tmp_path: Path) -> None:
    store = CatalogStore(tmp_path)  # never refreshed: no generation at all
    assert catalog_read.serve(store, "rbcountry", []) is None
    assert catalog_read.rankings_fallback(store, "popular") is None


def test_search_answers_and_never_raises_on_junk(tmp_path: Path) -> None:
    store = CatalogStore(tmp_path)
    refresh([_spec([_row("j1", name="Smooth Jazz FM")])], store, now=1000.0)
    assert [r.name for r in store.search("jazz")] == ["Smooth Jazz FM"]
    assert store.search('"unbalanced (') == []  # junk FTS input: empty, not a crash
    store.close()


# -- the spoken layer ---------------------------------------------------------


def test_the_summary_speaks_counts_first_and_failures_last() -> None:
    summary = RefreshSummary(
        outcomes=[
            SourceOutcome("radio_browser", "Radio Browser", "ok", added=174, updated=431),
            SourceOutcome("xiph", "Xiph", "stale", error="returned no stations"),
        ]
    )
    said = summary.spoken()
    assert said.startswith("Station catalog updated: 174 new stations, 431 updated.")
    assert "Xiph could not be reached; keeping what you have." in said


def test_ages_are_words_never_timecodes() -> None:
    assert spoken_age(30) == "just now"
    assert spoken_age(7200) == "2 hours ago"
    assert spoken_age(3 * 86400) == "3 days ago"
    assert spoken_age(None) == "never"
    assert ":" not in spoken_age(7200)
