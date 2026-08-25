"""Picks land in Subscriptions and Favorites, in the order you arranged them.

Asked for on 2026-08-25: *"create it as a folder in their Favorites as well as
in subscriptions"*, and *"Favorites should expose podcasts as well richly with
episodes like the podcast views"*.

The second half needed no new browse code: a favorite may be a **place**
(``browse:<node id>``), and ``mypodcastshow:<feed-url>`` is a node the browse
tree already expands into that show's episodes. So the test that matters is
that a podcast pick becomes *that* node -- get it wrong and the favorite is an
inert name that plays nothing.
"""

from __future__ import annotations

from quill.core.podcasts.pick_apply import PickToApply, apply_picks
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.core.radio.favorites import RadioFavoritesStore, is_place, place_node_id

_FOLDER = "ACB Media Podcasts"


def _podcast(title: str, feed: str) -> PickToApply:
    return PickToApply(title=title, feed_url=feed)


def test_a_podcast_reaches_both_stores() -> None:
    library, favorites = PodcastLibrary(), RadioFavoritesStore()

    outcome = apply_picks(
        [_podcast("ACB Community", "https://example.com/a")],
        library=library,
        favorites=favorites,
        folder=_FOLDER,
    )

    assert (outcome.subscribed, outcome.favorited) == (1, 1)
    assert [show.title for show in library.shows] == ["ACB Community"]
    assert [f.station.name for f in favorites.favorites] == ["ACB Community"]


def test_a_podcast_favorite_opens_into_its_episodes() -> None:
    """The whole "expose podcasts richly" requirement, in one assertion.

    ``mypodcastshow:<feed-url>`` is what the browse tree renders as Episodes.
    A favorite that stored the feed URL as a stream would be unplayable.
    """
    library, favorites = PodcastLibrary(), RadioFavoritesStore()

    apply_picks(
        [_podcast("ACB Community", "https://example.com/a")],
        library=library,
        favorites=favorites,
        folder=_FOLDER,
    )

    station = favorites.favorites[0].station
    assert is_place(station)
    assert place_node_id(station) == "mypodcastshow:https://example.com/a"
    # A place has no stream_url on purpose: nothing can try to play it.
    assert station.stream_url == ""


def test_a_station_stays_a_playable_favorite_and_is_not_subscribed() -> None:
    """There is no feed to subscribe to, and it must remain playable."""
    library, favorites = PodcastLibrary(), RadioFavoritesStore()

    outcome = apply_picks(
        [PickToApply(title="ACB Media 1", stream_url="https://example.com/live")],
        library=library,
        favorites=favorites,
        folder=_FOLDER,
    )

    assert (outcome.subscribed, outcome.favorited) == (0, 1)
    assert library.shows == []
    assert favorites.favorites[0].station.stream_url == "https://example.com/live"
    assert not is_place(favorites.favorites[0].station)


def test_the_order_you_arranged_is_the_order_that_is_saved() -> None:
    """Not re-sorted on the way in: the picker's arrangement is the answer."""
    library, favorites = PodcastLibrary(), RadioFavoritesStore()
    picks = [
        _podcast("Zoom Call", "https://example.com/z"),
        _podcast("ACB Community", "https://example.com/a"),
        _podcast("Marketplace", "https://example.com/m"),
    ]

    apply_picks(picks, library=library, favorites=favorites, folder=_FOLDER)

    assert [f.station.name for f in favorites.favorites] == [
        "Zoom Call",
        "ACB Community",
        "Marketplace",
    ]
    assert [s.title for s in library.shows] == ["Zoom Call", "ACB Community", "Marketplace"]


def test_everything_lands_in_the_named_folder_in_both_stores() -> None:
    library, favorites = PodcastLibrary(), RadioFavoritesStore()

    apply_picks(
        [_podcast("A", "https://example.com/a")],
        library=library,
        favorites=favorites,
        folder=_FOLDER,
    )

    assert [folder.name for folder in library.folders] == [_FOLDER]
    assert favorites.favorites[0].folder == _FOLDER


def test_running_it_twice_adds_nothing_and_says_so() -> None:
    """Re-opening the picker and pressing Add again must be safe."""
    library, favorites = PodcastLibrary(), RadioFavoritesStore()
    picks = [_podcast("ACB Community", "https://example.com/a")]
    apply_picks(picks, library=library, favorites=favorites, folder=_FOLDER)

    second = apply_picks(picks, library=library, favorites=favorites, folder=_FOLDER)

    assert second.subscribed == 0
    assert second.already_subscribed == 1
    assert len(library.shows) == 1
    assert len(favorites.favorites) == 1


def test_the_feed_metadata_travels_into_the_subscription() -> None:
    """So the library is as rich as the catalogue that fed it."""
    library, favorites = PodcastLibrary(), RadioFavoritesStore()

    apply_picks(
        [
            PickToApply(
                title="ACB Community",
                feed_url="https://example.com/a",
                homepage="https://example.com",
                description="Community events.",
                language="en-US",
                category="/Blindness",
            )
        ],
        library=library,
        favorites=favorites,
        folder=_FOLDER,
    )

    show = library.shows[0]
    assert show.description == "Community events."
    assert show.language == "en-US"
    assert show.category == "/Blindness"
    assert show.homepage == "https://example.com"


def test_a_bulk_subscribe_never_queues_downloads() -> None:
    """Choosing forty shows must not start forty transfers."""
    library, favorites = PodcastLibrary(), RadioFavoritesStore()

    apply_picks(
        [_podcast("A", "https://example.com/a")],
        library=library,
        favorites=favorites,
        folder=_FOLDER,
    )

    assert library.shows[0].settings.playback_mode == "stream"


def test_an_app_with_no_podcast_library_still_gets_its_favorites() -> None:
    favorites = RadioFavoritesStore()

    outcome = apply_picks(
        [PickToApply(title="ACB Media 1", stream_url="https://example.com/live")],
        library=None,
        favorites=favorites,
        folder=_FOLDER,
    )

    assert outcome.favorited == 1
    assert len(favorites.favorites) == 1


def test_a_pick_with_nothing_to_point_at_is_skipped_rather_than_stored() -> None:
    """A catalogue entry missing its URL must not become an unplayable row."""
    library, favorites = PodcastLibrary(), RadioFavoritesStore()

    outcome = apply_picks(
        [PickToApply(title="Broken")], library=library, favorites=favorites, folder=_FOLDER
    )

    assert outcome.nothing_happened
    assert favorites.favorites == []


def test_a_place_pick_keeps_the_node_it_was_given() -> None:
    """Catalogues may offer a browse branch (a shelf, a library) as a pick."""
    favorites = RadioFavoritesStore()

    apply_picks(
        [PickToApply(title="LibriVox Audiobooks", node_id="librivox")],
        library=None,
        favorites=favorites,
        folder=_FOLDER,
    )

    assert place_node_id(favorites.favorites[0].station) == "librivox"
