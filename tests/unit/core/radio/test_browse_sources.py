"""Tests for the browse registry -- every source, no wx, no network.

Each source's own client is stubbed; what is asserted here is the tree shape
the dialog will render: what is a folder, what is playable, what carries a note,
and that a source failure degrades to an empty branch rather than an exception
that would take the window with it.
"""

from __future__ import annotations

import pytest

from quill.core.radio import browse_sources as bs
from quill.core.radio.browse_nodes import make_id, split_id
from quill.core.radio.favorites import FavoriteStation, RadioFavoritesStore
from quill.core.radio.models import RadioStation


def _station(name: str = "Test FM", url: str = "https://a.example/s") -> RadioStation:
    return RadioStation(name=name, stream_url=url)


# --- ids ----------------------------------------------------------------------


def test_ids_round_trip_through_make_and_split() -> None:
    assert split_id(make_id("iheartletter", "1310", "B")) == ("iheartletter", ["1310", "B"])
    assert split_id(make_id("popular")) == ("popular", [])
    assert split_id("tunein:https://opml.example/Browse.ashx?c=music") == (
        "tunein",
        ["https://opml.example/Browse.ashx?c=music"],
    )


def test_ids_survive_names_with_punctuation() -> None:
    # Country and genre names contain spaces, commas, ampersands and colons.
    tricky = "The United States Of America"
    kind, args = split_id(make_id("rbstate", tricky, "Washington, D.C."))
    assert kind == "rbstate" and args == [tricky, "Washington, D.C."]
    kind2, args2 = split_id(make_id("xiph", "Drum & Bass: Classic"))
    assert kind2 == "xiph" and args2 == ["Drum & Bass: Classic"]


def test_every_root_source_is_expandable() -> None:
    for node_id, _label in bs.ROOT_SOURCES:
        assert bs.is_expandable(node_id), node_id


def test_root_labels_are_unique_so_expand_source_can_find_them() -> None:
    labels = [label for _id, label in bs.ROOT_SOURCES]
    assert len(labels) == len(set(labels))


# --- flat sources --------------------------------------------------------------


def test_flat_sources_yield_playable_leaves(monkeypatch) -> None:
    monkeypatch.setattr(bs.acb_media, "acb_media_stations", lambda: [_station("ACB 1")])
    nodes = bs.browse("acb")
    assert len(nodes) == 1
    assert nodes[0].is_leaf and nodes[0].station is not None
    assert nodes[0].label == "ACB 1"


def test_trending_and_recent_use_their_own_endpoints(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        bs.radio_browser,
        "trending_stations",
        lambda **_kw: (calls.append("trending"), [_station("T")])[1],
    )
    monkeypatch.setattr(
        bs.radio_browser,
        "recently_changed_stations",
        lambda **_kw: (calls.append("recent"), [_station("R")])[1],
    )
    assert bs.browse("trending")[0].label == "T"
    assert bs.browse("recent")[0].label == "R"
    assert calls == ["trending", "recent"]


# --- favorites -----------------------------------------------------------------


def _favorites_store() -> RadioFavoritesStore:
    return RadioFavoritesStore(
        favorites=[
            FavoriteStation(station=_station("Unfiled", "https://a/1")),
            FavoriteStation(station=_station("In Folder", "https://a/2"), folder="News"),
        ]
    )


def test_favorites_lists_unfiled_stations_then_folders() -> None:
    nodes = bs.browse("favorites", favorites=_favorites_store())
    assert nodes[0].is_leaf and nodes[0].label == "Unfiled"
    assert nodes[-1].is_folder and nodes[-1].label == "News"
    assert nodes[-1].child_count == 1


def test_a_favorites_folder_lists_its_stations() -> None:
    nodes = bs.browse(make_id("favorites", "News"), favorites=_favorites_store())
    assert [n.label for n in nodes] == ["In Folder"]


def test_favorites_without_a_store_is_empty_not_an_error() -> None:
    assert bs.browse("favorites") == []


# --- genre protocol ------------------------------------------------------------


def test_a_genre_source_lists_folders_then_stations(monkeypatch) -> None:
    monkeypatch.setattr(bs.xiph, "fetch_genres", lambda **_kw: ["jazz", "rock"])
    monkeypatch.setattr(bs.xiph, "fetch_genre_stations", lambda g, **_kw: [_station(f"{g} FM")])
    folders = bs.browse("xiph")
    assert [n.label for n in folders] == ["Jazz", "Rock"]
    assert all(n.is_folder for n in folders)
    stations = bs.browse(folders[0].node_id)
    assert [n.label for n in stations] == ["jazz FM"]


# --- geography -----------------------------------------------------------------


def test_a_country_with_states_lists_states(monkeypatch) -> None:
    monkeypatch.setattr(bs.radio_browser, "list_states", lambda c, **_kw: ["Arizona", "Texas"])
    nodes = bs.browse(make_id("rbcountry", "The United States Of America"))
    assert [n.label for n in nodes] == ["Arizona", "Texas"]
    assert all(n.is_folder for n in nodes)


def test_a_country_with_no_states_drops_straight_to_stations(monkeypatch) -> None:
    # Showing an empty States folder there would be a dead end.
    monkeypatch.setattr(bs.radio_browser, "list_states", lambda c, **_kw: [])
    monkeypatch.setattr(
        bs.radio_browser, "stations_by_country", lambda c, **_kw: [_station("Radio Malta")]
    )
    nodes = bs.browse(make_id("rbcountry", "Malta"))
    assert [n.label for n in nodes] == ["Radio Malta"]
    assert nodes[0].is_leaf


def test_a_state_node_passes_both_state_and_country(monkeypatch) -> None:
    seen: dict = {}

    def fake(state, *, country="", **_kw):
        seen["state"], seen["country"] = state, country
        return [_station("KJZZ")]

    monkeypatch.setattr(bs.radio_browser, "stations_by_state", fake)
    nodes = bs.browse(make_id("rbstate", "The United States Of America", "Arizona"))
    assert seen == {"state": "Arizona", "country": "The United States Of America"}
    assert nodes[0].label == "KJZZ"


def test_languages_are_title_cased_for_display(monkeypatch) -> None:
    monkeypatch.setattr(bs.radio_browser, "list_languages", lambda **_kw: ["english", "spanish"])
    assert [n.label for n in bs.browse("rblang")] == ["English", "Spanish"]


# --- TuneIn --------------------------------------------------------------------


def test_tunein_folders_drill_and_stations_are_lazy(monkeypatch) -> None:
    from quill.core.radio.tunein import TuneInResult

    monkeypatch.setattr(
        bs.tunein,
        "browse",
        lambda target="", **_kw: [
            TuneInResult(guide_id="c1", title="Music", browse_url="https://opml/x?c=music"),
            TuneInResult(guide_id="s24939", title="BBC Radio 1", is_station=True),
        ],
    )
    nodes = bs.browse("tunein")
    assert nodes[0].is_folder and nodes[0].node_id == "tunein:https://opml/x?c=music"
    assert nodes[1].resolve_lazily and not nodes[1].is_folder
    assert nodes[1].note, "a lazy leaf must say it resolves before the listener presses Enter"


def test_resolve_turns_a_tunein_leaf_into_a_station(monkeypatch) -> None:
    monkeypatch.setattr(
        bs.tunein, "resolve_station_streams", lambda gid, **_kw: ["https://cdn/bbc.mp3"]
    )
    station = bs.resolve(make_id("tuneinstation", "s24939"))
    assert station is not None and station.stream_url == "https://cdn/bbc.mp3"
    assert station.source == "TuneIn"


def test_resolve_returns_none_rather_than_raising(monkeypatch) -> None:
    monkeypatch.setattr(bs.tunein, "resolve_station_streams", lambda gid, **_kw: [])
    assert bs.resolve(make_id("tuneinstation", "s1")) is None
    assert bs.resolve("popular") is None  # not a lazy leaf at all

    def boom(gid, **_kw):
        raise RuntimeError("down")

    monkeypatch.setattr(bs.tunein, "resolve_station_streams", boom)
    assert bs.resolve(make_id("tuneinstation", "s1")) is None


# --- iHeart --------------------------------------------------------------------


def test_iheart_genre_makes_letter_folders_and_letters_make_stations(monkeypatch) -> None:
    from quill.core.radio.iheart import IHeartGenre

    monkeypatch.setattr(bs.iheart, "fetch_genres", lambda **_kw: [IHeartGenre(1310, "Rock")])
    monkeypatch.setattr(
        bs.iheart,
        "fetch_genre_stations",
        lambda gid, **_kw: [
            _station("Alpha FM", "https://a/1"),
            _station("Beta FM", "https://a/2"),
        ],
    )
    genres = [n for n in bs.browse("iheart") if n.label != "By City"]
    assert genres[0].label == "Rock" and genres[0].is_folder
    letters = bs.browse(genres[0].node_id)
    assert [n.label for n in letters] == ["A", "B"]
    assert letters[0].child_count == 1
    stations = bs.browse(letters[0].node_id)
    assert [n.label for n in stations] == ["Alpha FM"]


def test_a_letter_node_id_carries_no_payload_so_it_survives_a_restart() -> None:
    # browse_position remembers a path across sessions, so an id may not embed a
    # fetched payload, a cursor, or a timestamp.
    node_id = make_id("iheartletter", "1310", "B")
    assert node_id == "iheartletter:1310\tB"
    assert "RadioStation" not in node_id


# --- Apple ---------------------------------------------------------------------


def test_apple_lists_storefronts_then_top_and_genres(monkeypatch, tmp_path) -> None:
    from quill.core.podcasts import apple_podcasts as apple

    # The Subscriptions node now reads the shared library for its count
    # badge; isolate so a developer's real follows cannot change the label.
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(apple, "fetch_genres", lambda **_kw: [apple.AppleGenre("1301", "Arts")])
    roots = bs.browse("apple")
    # Subscriptions leads (the shows already followed are the ones a listener
    # comes back for); the storefronts follow.
    assert roots[0].label == "Subscriptions"
    assert roots[1].label == "United States"
    level = bs.browse(roots[1].node_id)
    assert [n.label for n in level] == ["Top Podcasts", "Top Episodes", "Arts"]


def test_an_apple_show_expands_to_its_episodes(monkeypatch) -> None:
    from types import SimpleNamespace

    from quill.core.podcasts import apple_podcasts as apple
    from quill.core.podcasts.models import PodcastEpisode

    monkeypatch.setattr(apple, "resolve_feed_url", lambda cid, **_kw: "https://feeds/x")
    monkeypatch.setattr(
        "quill.core.podcasts.feed_reader.fetch_and_parse_feed",
        lambda url, **_kw: SimpleNamespace(
            episodes=[
                PodcastEpisode(
                    guid="1",
                    title="Ep 1",
                    audio_url="https://a/1.mp3",
                    transcript_url="https://a/1.vtt",
                ),
                PodcastEpisode(guid="2", title="No audio", audio_url=""),
            ]
        ),
    )
    nodes = bs.browse(make_id("appleshow", "123"))
    assert [n.label for n in nodes] == ["Ep 1"]  # the audio-less episode is dropped
    assert nodes[0].station is not None
    assert nodes[0].note == "transcript available"


# --- failure and Safe Mode -----------------------------------------------------


def test_a_source_that_raises_becomes_an_empty_branch(monkeypatch) -> None:
    # A browse branch that throws takes the window with it.
    def boom(**_kw):
        raise RuntimeError("directory down")

    monkeypatch.setattr(bs.radio_browser, "popular_stations", boom)
    assert bs.browse("popular") == []


def test_an_unknown_node_id_is_empty_not_an_error() -> None:
    assert bs.browse("no-such-source") == []
    assert bs.browse("") == []


@pytest.mark.parametrize("node_id", ["favorites", "acb", "nfb", "networks"])
def test_local_sources_do_not_need_the_network(node_id) -> None:
    assert not bs.needs_network(node_id)


@pytest.mark.parametrize("node_id", ["popular", "tunein", "iheart", "apple", "xiph", "wx"])
def test_internet_sources_are_marked_as_needing_the_network(node_id) -> None:
    assert bs.needs_network(node_id)


def test_source_label_finds_root_labels() -> None:
    assert bs.source_label("apple") == "Podcasts (Apple)"
    assert bs.source_label("nope") == ""


# --- the axes rolled in after the live probe (2026-08-13) ---------------------


def test_by_quality_lists_codecs_with_counts_then_stations(monkeypatch) -> None:
    # vTuner sells this classification; the open directory publishes it.
    monkeypatch.setattr(
        bs.radio_browser, "list_codecs", lambda **_kw: [("MP3", 30000), ("AAC", 8002), ("DEAD", 0)]
    )
    monkeypatch.setattr(
        bs.radio_browser, "stations_by_codec", lambda c, **_kw: [_station(f"{c} FM")]
    )
    nodes = bs.browse("rbcodec")
    assert [n.label for n in nodes] == ["MP3", "AAC"]  # a codec with no stations is dropped
    assert nodes[0].child_count == 30000
    assert [n.label for n in bs.browse(nodes[0].node_id)] == ["MP3 FM"]


def test_by_quality_is_a_root_source() -> None:
    assert ("rbcodec", "By Quality") in bs.ROOT_SOURCES


def test_iheart_offers_by_city_before_its_genres(monkeypatch) -> None:
    from quill.core.radio.iheart import IHeartGenre

    monkeypatch.setattr(bs.iheart, "fetch_genres", lambda **_kw: [IHeartGenre(1310, "Rock")])
    nodes = bs.browse("iheart")
    assert nodes[0].label == "By City", "local radio is what people open iHeart for"
    assert nodes[1].label == "Rock"


def test_iheart_markets_group_a_to_z_then_list_cities_with_counts(monkeypatch) -> None:
    from quill.core.radio.iheart import IHeartMarket

    markets = [
        IHeartMarket(1, "Phoenix", "AZ", "United States", 34),
        IHeartMarket(2, "Boston", "MA", "United States", 21),
        IHeartMarket(3, "Baltimore", "MD", "United States", 12),
    ]
    monkeypatch.setattr(bs.iheart, "fetch_markets", lambda **_kw: markets)
    groups = bs.browse("iheartmarkets")
    assert [g.label for g in groups] == ["B", "P"]
    assert groups[0].child_count == 2
    cities = bs.browse(groups[0].node_id)
    assert [c.label for c in cities] == ["Baltimore, MD", "Boston, MA"]
    assert cities[0].child_count == 12


def test_an_iheart_market_lists_its_stations(monkeypatch) -> None:
    seen: dict = {}

    def fake(market_id, **_kw):
        seen["market_id"] = market_id
        return [_station("Alfa 104.5 FM")]

    monkeypatch.setattr(bs.iheart, "fetch_market_stations", fake)
    nodes = bs.browse(make_id("iheartmarket", "566"))
    assert seen["market_id"] == 566
    assert [n.label for n in nodes] == ["Alfa 104.5 FM"]


def test_apple_offers_both_chart_kinds(monkeypatch) -> None:
    from quill.core.podcasts import apple_podcasts as apple

    monkeypatch.setattr(apple, "fetch_genres", lambda **_kw: [])
    nodes = bs.browse(make_id("apple", "us"))
    assert [n.label for n in nodes] == ["Top Podcasts", "Top Episodes"]


def test_an_apple_chart_node_passes_its_kind_through(monkeypatch) -> None:
    from quill.core.podcasts import apple_podcasts as apple

    seen: dict = {}

    def fake(storefront="us", *, genre_id="", kind="podcasts", **_kw):
        seen["storefront"], seen["kind"] = storefront, kind
        return [apple.AppleShow(collection_id="1", name="An Episode")]

    monkeypatch.setattr(apple, "fetch_charts", fake)
    nodes = bs.browse(make_id("applechart", "ie", "podcast-episodes"))
    assert seen == {"storefront": "ie", "kind": "podcast-episodes"}
    assert [n.label for n in nodes] == ["An Episode"]


# --- the six providers ---------------------------------------------------------


def test_all_six_new_providers_are_root_sources() -> None:
    labels = dict(bs.ROOT_SOURCES)
    for node_id in ("archive", "librivox", "gutenberg", "audius", "mixcloud", "ccmixter"):
        assert node_id in labels, node_id


def test_archive_root_lists_curated_collections_then_drills(monkeypatch) -> None:
    from quill.core.radio import internet_archive as ia

    roots = bs.browse("archive")
    assert roots[0].label == "Old Time Radio", "the collection this audience wants is first"
    monkeypatch.setattr(
        ia,
        "children",
        lambda c, *, collections, page=1, **_kw: (
            (2, [ia.ArchiveItem("series-a", "Series A", is_collection=True)])
            if collections
            else (1, [ia.ArchiveItem("ep-1", "Episode 1")])
        ),
    )
    level = bs.browse(roots[0].node_id)
    assert [n.label for n in level] == ["Series A", "Episode 1"]
    assert level[0].is_folder and level[1].is_folder  # an item opens to its files


def test_archive_offers_more_rather_than_truncating_silently(monkeypatch) -> None:
    from quill.core.radio import internet_archive as ia

    monkeypatch.setattr(
        ia,
        "children",
        lambda c, *, collections, page=1, **_kw: (
            (0, [])
            if collections
            else (8710, [ia.ArchiveItem(f"i{n}", f"Item {n}") for n in range(3)])
        ),
    )
    nodes = bs.browse(make_id("archive", "oldtimeradio"))
    more = nodes[-1]
    assert more.label == "More..."
    assert "8710" in more.note, "a truncated folder must say how much it is hiding"


def test_an_archive_item_says_when_no_rights_are_published(monkeypatch) -> None:
    from quill.core.radio import internet_archive as ia

    monkeypatch.setattr(ia, "item_files", lambda i, **_kw: [_station("Part 1")])
    node = bs.browse(make_id("archiveitem", "some-item"))[0]
    assert node.note == "no rights information published"


def test_librivox_offers_only_the_axes_that_exist() -> None:
    # There is no By Title: the API supports no title filter in any form.
    labels = [n.label for n in bs.browse("librivox")]
    assert labels == ["Recently Added", "By Genre", "By Author"]
    assert "By Title" not in labels


def test_a_librivox_book_with_many_sections_is_a_folder(monkeypatch) -> None:
    from quill.core.media.librivox import LibriVoxBook, LibriVoxSection

    book = LibriVoxBook(
        book_id="42",
        title="Moby Dick",
        authors="Melville, Herman",
        sections=(
            LibriVoxSection(0, "Chapter 1", "https://a/1.mp3"),
            LibriVoxSection(1, "Chapter 2", "https://a/2.mp3"),
        ),
    )
    monkeypatch.setattr("quill.core.media.librivox.recent_books", lambda **_kw: [book])
    nodes = bs.browse("librivoxrecent")
    assert nodes[0].is_folder and nodes[0].child_count == 2
    assert nodes[0].note == "Melville, Herman"
    sections = bs.browse(nodes[0].node_id)
    assert [s.label for s in sections] == ["Chapter 1", "Chapter 2"]


def test_a_single_section_librivox_book_is_just_playable(monkeypatch) -> None:
    from quill.core.media.librivox import LibriVoxBook, LibriVoxSection

    book = LibriVoxBook(
        book_id="7",
        title="A Short Poem",
        sections=(LibriVoxSection(0, "The whole thing", "https://a/1.mp3"),),
    )
    monkeypatch.setattr("quill.core.media.librivox.recent_books", lambda **_kw: [book])
    node = bs.browse("librivoxrecent")[0]
    assert node.is_leaf and node.station.name == "A Short Poem"


def test_mixcloud_rows_say_they_open_in_a_browser(monkeypatch) -> None:
    # Mode A: Quill Radio never extracts a Mixcloud stream, and the row must say
    # so before Enter rather than after.
    from quill.core.radio import free_music

    monkeypatch.setattr(
        free_music,
        "mixcloud_shows",
        lambda slug, **_kw: [_station("A Show", "https://www.mixcloud.com/x/y/")],
    )
    node = bs.browse(make_id("mixcloudcat", "business"))[0]
    assert node.note == "opens on Mixcloud in your browser"
    assert node.station.stream_url.startswith("https://www.mixcloud.com/")


def test_mixcloud_splits_music_from_talk(monkeypatch) -> None:
    from quill.core.radio import free_music
    from quill.core.radio.free_music import MixcloudCategory

    monkeypatch.setattr(
        free_music,
        "mixcloud_categories",
        lambda **_kw: [
            MixcloudCategory("jazz", "Jazz", "music"),
            MixcloudCategory("comedy", "Comedy", "talk"),
        ],
    )
    assert [n.label for n in bs.browse("mixcloud")] == ["Music Categories", "Talk Categories"]
    assert [n.label for n in bs.browse(make_id("mixcloudfmt", "talk"))] == ["Comedy"]


def test_ccmixter_rows_carry_their_licence(monkeypatch) -> None:
    from quill.core.radio import free_music

    licensed = RadioStation(
        name="A Track", stream_url="https://a/1.mp3", tags=("Attribution Noncommercial (4.0)",)
    )
    monkeypatch.setattr(free_music, "ccmixter_by_tag", lambda tag, **_kw: [licensed])
    node = bs.browse(make_id("ccmixter", "jazz"))[0]
    assert node.note == "Attribution Noncommercial (4.0)"


def test_gutenberg_offers_topics_and_languages(monkeypatch) -> None:
    labels = [n.label for n in bs.browse("gutenberg")]
    assert labels[0] == "All Audiobooks"
    assert "Fiction" in labels and "In French" in labels


def test_audius_offers_trending_first_then_genres() -> None:
    nodes = bs.browse("audius")
    assert nodes[0].label == "Trending Now"
    assert any(n.label == "Jazz" for n in nodes)


def test_audius_trending_folder_does_not_relist_the_root() -> None:
    """Opening "Trending Now" must ask Audius for tracks, never re-list itself.

    The folder once carried an "audius" id with an empty argument, which parses
    back to no arguments at all -- so expanding it showed "Trending Now" plus
    the genres again, nested endlessly, and the trending tracks were unreachable.
    """
    trending = bs.browse("audius")[0]
    assert trending.node_id == "audiustrending"
    kind, args = bs.split_id(trending.node_id)
    # The id must not round-trip to the argless root listing.
    assert (kind, args) != ("audius", [])
    import quill.core.radio.browse_sources as mod

    assert mod._HANDLERS["audiustrending"] is mod._browse_audius_trending
