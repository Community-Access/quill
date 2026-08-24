"""The Podcast Index as a branch of the browse tree.

The point of the branch, and the thing every test here is really checking: a
show can be *looked at* without being subscribed to. Before it, a show was a
name, and the only way to find out what it published was to subscribe and then
go and read the list -- a commitment made in order to ask a question.

No network: the catalogue client is replaced, because what is being tested is
the shape of the rows, not the directory.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.radio import browse_podcast_index as branch
from quill.core.radio import browse_sources
from quill.core.radio.browse_nodes import make_id


class _Show:
    def __init__(self, **facts: Any) -> None:
        self.feed_url = facts.get("feed_url", "https://feed.test/rss")
        self.title = facts.get("title", "A Show")
        self.display_name = self.title or self.feed_url
        self.author = facts.get("author", "A Publisher")
        self.description = facts.get("description", "")
        self.homepage = facts.get("homepage", "")
        self.artwork_url = facts.get("artwork_url", "")
        self.language = facts.get("language", "")
        self.categories = facts.get("categories", ("News",))
        self.episode_count = facts.get("episode_count", 12)
        self.last_published = facts.get("last_published", 0)
        self.explicit = facts.get("explicit", False)
        self.dead = facts.get("dead", False)
        self.funding_url = facts.get("funding_url", "")
        self.funding_label = facts.get("funding_label", "")

    @property
    def summary(self) -> str:
        parts = [self.author, f"{self.episode_count} episodes", ", ".join(self.categories)]
        if self.dead:
            parts.append("the index can no longer read this feed")
        return ", ".join(part for part in parts if part)


class _Episode:
    def __init__(self, **facts: Any) -> None:
        self.title = facts.get("title", "Episode One")
        self.display_name = self.title
        self.audio_url = facts.get("audio_url", "https://media.test/1.mp3")
        self.description = facts.get("description", "What happened.")
        self.duration_seconds = facts.get("duration_seconds", 1800)
        self.published = facts.get("published", 1_787_500_000)
        self.transcript_url = facts.get("transcript_url", "")


def test_the_branch_offers_trending_the_taxonomy_and_a_search() -> None:
    rows = branch.browse_root([], safe_mode=False)

    assert [row.label for row in rows] == [
        "Trending Now",
        "By Category",
        "Search the Podcast Index...",
    ]
    # The search is an action, not a folder: Enter *does* the thing.
    assert rows[-1].is_action


def test_a_show_row_says_what_it_is_before_you_open_it(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.podcasts import podcast_index_catalog as catalog

    monkeypatch.setattr(catalog, "trending", lambda **_kw: [_Show()])

    row = branch.browse_trending([], safe_mode=False)[0]

    assert row.is_folder
    assert row.label == "A Show"
    # Author, how much there is, and what it is about -- the facts somebody
    # choosing a show wants, before they commit to anything.
    assert "A Publisher" in row.note
    assert "12 episodes" in row.note
    assert "News" in row.note
    assert row.child_count == 12


def test_a_feed_the_index_cannot_read_says_so_on_the_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Found out now, rather than by subscribing to a show that never publishes."""
    from quill.core.podcasts import podcast_index_catalog as catalog

    monkeypatch.setattr(catalog, "trending", lambda **_kw: [_Show(dead=True)])

    assert "no longer read" in branch.browse_trending([], safe_mode=False)[0].note


def test_a_shows_episodes_are_playable_rows_without_subscribing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The whole reason the branch exists."""
    from quill.core.podcasts import podcast_index_catalog as catalog

    monkeypatch.setattr(catalog, "show_facts", lambda *_a, **_kw: _Show())
    monkeypatch.setattr(catalog, "episodes_for_feed", lambda *_a, **_kw: [_Episode()])

    rows = branch.browse_show(["https://feed.test/rss"], safe_mode=False)

    assert len(rows) == 1
    row = rows[0]
    station = row.station
    assert station is not None
    assert station.stream_url == "https://media.test/1.mp3"
    # A published episode is a finished recording: it seeks, reports a position
    # and remembers where you stopped, like every other recording in the tree.
    assert station.is_recording is True
    # The feed, so Subscribe on this row needs no second lookup.
    assert station.homepage == "https://feed.test/rss"
    assert station.notes == "What happened."


def test_an_episode_row_speaks_its_length_and_its_date(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from quill.core.podcasts import podcast_index_catalog as catalog

    monkeypatch.setattr(catalog, "show_facts", lambda *_a, **_kw: _Show())
    monkeypatch.setattr(catalog, "episodes_for_feed", lambda *_a, **_kw: [_Episode()])

    note = branch.browse_show(["https://feed.test/rss"], safe_mode=False)[0].note

    assert "30 minutes" in note  # words, never "30:00" -- read aloud that is a guess
    assert "2026" in note


def test_an_episode_with_no_audio_is_not_offered(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.podcasts import podcast_index_catalog as catalog

    monkeypatch.setattr(catalog, "show_facts", lambda *_a, **_kw: _Show())
    monkeypatch.setattr(catalog, "episodes_for_feed", lambda *_a, **_kw: [_Episode(audio_url="")])

    assert branch.browse_show(["https://feed.test/rss"], safe_mode=False) == []


def test_the_categories_are_the_index_own_taxonomy(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.podcasts import podcast_index_catalog as catalog

    class _Category:
        def __init__(self, name: str) -> None:
            self.category_id = 1
            self.name = name

    monkeypatch.setattr(catalog, "categories", lambda **_kw: [_Category("Arts"), _Category("News")])

    rows = branch.browse_categories([], safe_mode=False)

    assert [row.label for row in rows] == ["Arts", "News"]
    # Each one is a trending list narrowed to it, so opening one costs the
    # same single request as Trending Now itself.
    assert rows[0].node_id == make_id("pitrending", "Arts")


def test_the_show_fact_sheet_stops_rather_than_padding() -> None:
    """A field the index has nothing for is a line that is not there."""
    text = branch.show_details(_Show(language="", episode_count=0, categories=()))

    assert "By: A Publisher" in text
    assert "Language" not in text
    assert "Episodes" not in text
    assert "Categories" not in text


def test_the_fact_sheet_names_the_support_link_and_the_warnings() -> None:
    text = branch.show_details(
        _Show(
            explicit=True,
            dead=True,
            funding_url="https://give.test",
            funding_label="Buy us a coffee",
            description="A show about things.",
        )
    )

    assert "Buy us a coffee: https://give.test" in text
    assert "Marked explicit" in text
    assert "can no longer read this feed" in text
    assert text.endswith("A show about things.")


# -- registered in the tree, like every other source ------------------------------


def test_the_branch_is_a_root_source_and_routes_through_browse() -> None:
    assert ("podcastindex", "Podcast Index") in browse_sources.ROOT_SOURCES
    assert browse_sources.is_expandable("podcastindex")
    assert browse_sources.is_expandable(make_id("pishow", "https://feed.test/rss"))
    assert [row.label for row in browse_sources.browse("podcastindex")] == [
        "Trending Now",
        "By Category",
        "Search the Podcast Index...",
    ]


def test_it_can_be_switched_off_like_any_other_source() -> None:
    from quill.core.radio import browse_visibility

    info = browse_visibility.source("podcastindex")
    assert info is not None
    assert info.default_on is True
    assert "podcastindex" in browse_visibility.default_enabled()


def test_a_podcast_index_show_is_a_podcast_show_to_the_menu() -> None:
    """So Subscribe appears on it -- and needs no feed lookup to work."""
    from quill.core.radio import row_actions

    assert row_actions.is_podcast_show("pishow")
    assert row_actions.contents_noun("pishow") == "Episodes"


def test_both_podcast_directories_are_asked_together() -> None:
    from quill.core.radio import federated_browse

    podcast_sources = [t.label for t in federated_browse.targets_of_type("Podcast")]

    assert "Apple Podcasts" in podcast_sources
    assert "Podcast Index" in podcast_sources


# -- a branch added later must actually reach people -------------------------------


def test_a_saved_source_list_gains_a_branch_added_after_it_was_saved() -> None:
    """The bug that made this feature invisible.

    A stored "these are my browse sources" list can only name branches that
    existed when it was saved, and ``normalize`` drops everything it does not
    name -- so the Podcast Index branch shipped and appeared for nobody who had
    ever opened Choose Browse Sources (reported 2026-08-23: "I ran it and do not
    see any difference in the radio app").
    """
    from quill.core.radio import browse_visibility

    # A list saved before the branch existed.
    saved = tuple(s for s in browse_visibility.default_enabled() if s != "podcastindex")
    assert "podcastindex" not in saved

    shown = browse_visibility.with_new_sources(saved, 0)

    assert "podcastindex" in shown


def test_a_branch_the_listener_hid_stays_hidden_once_they_have_seen_it() -> None:
    """The other half: shown once, then their answer stands."""
    from quill.core.radio import browse_visibility

    hidden = browse_visibility.toggle(browse_visibility.default_enabled(), "podcastindex")
    assert "podcastindex" not in hidden

    still_hidden = browse_visibility.with_new_sources(hidden, browse_visibility.SOURCES_EPOCH)

    assert "podcastindex" not in still_hidden


def test_a_branch_that_ships_switched_off_is_never_switched_on_for_anybody() -> None:
    """Adding one to somebody's list would be turning something on under them."""
    from quill.core.radio import browse_visibility

    off_by_default = [s.id for s in browse_visibility.BROWSE_SOURCES if not s.default_on]
    added = browse_visibility.introduced_since(0)

    assert all(source_id not in added for source_id in off_by_default)


def test_never_having_chosen_still_answers_with_the_defaults() -> None:
    from quill.core.radio import browse_visibility

    assert browse_visibility.with_new_sources(None, 0) == browse_visibility.default_enabled()


def test_loading_a_profile_stamps_it_forward(tmp_path) -> None:
    """So the catch-up happens once rather than on every launch."""
    from quill.core.radio import browse_visibility
    from quill.core.radio.history import RadioHistory, load_history, save_history

    history = RadioHistory()
    history.browse_sources_enabled = tuple(
        s for s in browse_visibility.default_enabled() if s != "podcastindex"
    )
    history.browse_sources_epoch = 0
    save_history(tmp_path, history)

    reloaded = load_history(tmp_path)

    assert reloaded.browse_sources_enabled is not None
    assert "podcastindex" in reloaded.browse_sources_enabled
    assert reloaded.browse_sources_epoch == browse_visibility.SOURCES_EPOCH
