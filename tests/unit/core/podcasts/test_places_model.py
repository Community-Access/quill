"""The Places list's model: order, hiding, names, counts, empty sentences (qc.md 4.3)."""

from __future__ import annotations

from quill.core.podcasts import places
from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.models_episode import PodcastEpisode
from quill.core.podcasts.subscriptions import PodcastLibrary


def _library() -> PodcastLibrary:
    library = PodcastLibrary()
    show = PodcastShow(id="s1", title="The Daily", feed_url="http://x.invalid/1")
    show.is_favorite = True
    show.route_to_inbox = True
    show.episodes.append(PodcastEpisode(guid="e1", title="One", audio_url="http://x/1.mp3"))
    show.episodes.append(
        PodcastEpisode(guid="e2", title="Two", audio_url="http://x/2.mp3", downloaded_path="c:/x")
    )
    library.add_show(show)
    return library


def test_the_shipped_layout_encodes_to_nothing_and_decodes_back() -> None:
    layout = places.PlacesLayout()
    assert layout.is_default
    assert places.encode(layout) == ""
    assert places.decode("") == layout
    assert places.decode("not json") == layout
    assert places.decode(
        '{"order": ["queue", "bogus"], "hidden": ["inbox"]}'
    ) == places.PlacesLayout(
        ("queue", *[p for p in places.DEFAULT_ORDER if p != "queue"]), frozenset({"inbox"})
    )


def test_moving_skips_hidden_rows_and_says_where_it_landed() -> None:
    layout = places.hide(places.PlacesLayout(), "new_episodes")
    moved = places.move(layout, "inbox", 1)
    shown = [p.id for p in places.visible(moved)]
    assert shown[0] == "continue_listening" and shown[1] == "inbox"
    assert places.move_sentence(moved, "inbox", "Inbox") == "Inbox moved to 2nd."
    assert (
        places.move_sentence(places.move(moved, "inbox", -1), "inbox", "Inbox")
        == "Inbox moved to first."
    )
    assert places.move(layout, "inbox", -1) == layout, "already first"
    assert places.move_sentence(layout, "new_episodes", "New Episodes") == "New Episodes is hidden."


def test_a_feature_off_is_absent_even_from_the_chooser() -> None:
    layout = places.hide(places.PlacesLayout(), "downloads")
    shown = places.visible(layout, enabled=lambda area: area != "queue", include_hidden=True)
    ids = [p.id for p in shown]
    assert "downloads" in ids, "hidden is still listed for the chooser"
    assert "queue" not in ids, "a feature switched off is not a place at all"
    assert "queue" not in [p.id for p in places.visible(layout, enabled=lambda a: a != "queue")]


def test_names_counts_and_empty_sentences_come_from_the_library() -> None:
    library = _library()
    assert places.label(library, "inbox") == "Inbox"
    library.settings.view_names["inbox"] = "Today"
    assert places.label(library, "inbox") == "Today"
    assert places.count(library, "podcasts") == 1
    assert places.count(library, "favorites") == 1
    assert places.count(library, "downloads") == 1
    assert places.count(library, "queue") == 0
    assert places.count(library, "notifications", unread_notices=3) == 3
    assert places.count(library, "new_episodes") == 2
    assert "Space on any episode adds it" in places.empty_state(library, "queue")
    assert "Add to Favorites" in places.empty_state(library, "favorites")
    assert places.empty_state(library, "bogus") == ""


def test_every_place_has_a_kind_the_pane_knows() -> None:
    kinds = {
        places.KIND_EPISODES,
        places.KIND_PODCASTS,
        places.KIND_TREE,
        places.KIND_NOTICES,
        places.KIND_PLAYLISTS,
    }
    for entry in places.PLACES:
        assert entry.kind in kinds, entry.id
        assert entry.empty.endswith("."), entry.id
    assert places.place("podcasts").kind == places.KIND_TREE
    assert places.place("favorites").kind == places.KIND_PODCASTS
