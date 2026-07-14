"""Tests for podcast episode/show filtering and Search Everywhere (pure)."""

from __future__ import annotations

from quill.core.podcasts.episode_notes import EpisodeNote
from quill.core.podcasts.filtering import (
    filter_episodes,
    filter_shows,
    filter_shows_by_text,
    search_everywhere,
)
from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary


def _episode(guid: str, *, played: bool = False, downloaded: bool = False) -> PodcastEpisode:
    return PodcastEpisode(
        guid=guid,
        title=guid,
        audio_url=f"https://x/{guid}.mp3",
        played=played,
        downloaded_path=f"/tmp/{guid}.mp3" if downloaded else "",
    )


def test_filter_episodes_unplayed() -> None:
    episodes = [_episode("e1", played=False), _episode("e2", played=True)]
    assert [e.guid for e in filter_episodes(episodes, "unplayed")] == ["e1"]


def test_filter_episodes_played() -> None:
    episodes = [_episode("e1", played=False), _episode("e2", played=True)]
    assert [e.guid for e in filter_episodes(episodes, "played")] == ["e2"]


def test_filter_episodes_downloaded_and_not_downloaded() -> None:
    episodes = [_episode("e1", downloaded=True), _episode("e2", downloaded=False)]
    assert [e.guid for e in filter_episodes(episodes, "downloaded")] == ["e1"]
    assert [e.guid for e in filter_episodes(episodes, "not_downloaded")] == ["e2"]


def test_filter_episodes_all_and_unknown_mode_returns_everything() -> None:
    episodes = [_episode("e1"), _episode("e2")]
    assert filter_episodes(episodes, "all") == episodes
    assert filter_episodes(episodes, "bogus") == episodes


def test_filter_shows_favorites_only() -> None:
    fav = PodcastShow(id="s1", title="Fav", is_favorite=True)
    other = PodcastShow(id="s2", title="Other")
    assert filter_shows([fav, other], "favorites_only") == [fav]


def test_filter_shows_has_unplayed() -> None:
    with_unplayed = PodcastShow(id="s1", title="A", episodes=[_episode("e1", played=False)])
    all_played = PodcastShow(id="s2", title="B", episodes=[_episode("e2", played=True)])
    assert filter_shows([with_unplayed, all_played], "has_unplayed") == [with_unplayed]


def test_search_everywhere_matches_show_titles() -> None:
    library = PodcastLibrary()
    library.add_show(PodcastShow(id="s1", title="Tech Weekly"))
    library.add_show(PodcastShow(id="s2", title="Cooking Hour"))
    results = search_everywhere(library, "tech")
    assert len(results) == 1
    assert results[0].kind == "show"
    assert results[0].show.id == "s1"


def test_search_everywhere_matches_episode_titles() -> None:
    library = PodcastLibrary()
    show = PodcastShow(
        id="s1",
        title="Show",
        episodes=[
            _episode("e1"),
            PodcastEpisode(guid="e2", title="Special Interview", audio_url="https://x/e2.mp3"),
        ],
    )
    library.add_show(show)
    results = search_everywhere(library, "interview")
    assert len(results) == 1
    assert results[0].kind == "episode"
    assert results[0].episode is not None
    assert results[0].episode.guid == "e2"


def test_search_everywhere_matches_notes_when_provided() -> None:
    library = PodcastLibrary()
    show = PodcastShow(id="s1", title="Show", episodes=[_episode("e1")])
    library.add_show(show)
    note = EpisodeNote(
        note_id="n1",
        show_id="s1",
        episode_guid="e1",
        position_ms=1000,
        text="A great quote about gardening",
        created_at="2026-07-13T00:00:00+00:00",
    )
    results = search_everywhere(library, "gardening", episode_notes=[note])
    assert len(results) == 1
    assert results[0].kind == "note"
    assert "gardening" in results[0].note_preview.casefold()


def test_search_everywhere_blank_query_returns_nothing() -> None:
    library = PodcastLibrary()
    library.add_show(PodcastShow(id="s1", title="Show"))
    assert search_everywhere(library, "   ") == []


def test_search_everywhere_is_case_insensitive() -> None:
    library = PodcastLibrary()
    library.add_show(PodcastShow(id="s1", title="UPPERCASE SHOW"))
    results = search_everywhere(library, "uppercase")
    assert len(results) == 1


def test_search_result_label_formats_by_kind() -> None:
    show = PodcastShow(id="s1", title="Show")
    episode = _episode("e1")
    from quill.core.podcasts.filtering import SearchResult

    assert SearchResult("show", show).label == "Show: Show"
    assert SearchResult("episode", show, episode).label == "Episode: e1 (Show)"
    assert SearchResult("note", show, episode, "preview text").label == (
        'Note on "e1": preview text'
    )


def test_search_everywhere_matches_cached_transcripts() -> None:
    library = PodcastLibrary()
    show = PodcastShow(id="s1", title="Tech Show", feed_url="https://a/feed.xml")
    show.episodes.append(
        PodcastEpisode(guid="g1", title="Episode One", audio_url="https://a/1.mp3")
    )
    library.add_show(show)
    transcripts = [("s1", "g1", "Today we discuss the wonders of quantum computing at length.")]

    results = search_everywhere(library, "quantum", transcripts=transcripts)

    assert len(results) == 1
    assert results[0].kind == "transcript"
    assert results[0].episode is not None and results[0].episode.guid == "g1"
    assert "quantum" in results[0].note_preview.casefold()
    assert "Transcript of" in results[0].label


def test_search_everywhere_transcript_for_unknown_show_is_ignored() -> None:
    library = PodcastLibrary()
    results = search_everywhere(library, "x", transcripts=[("nope", "g1", "x marks the spot")])
    assert results == []


def test_filter_episodes_by_text_matches_title_and_description() -> None:
    from quill.core.podcasts.filtering import filter_episodes_by_text

    quantum = PodcastEpisode(guid="g1", title="Quantum Leaps", audio_url="https://x/1")
    described = PodcastEpisode(
        guid="g2",
        title="Plain Title",
        audio_url="https://x/2",
        description="A deep dive into quantum computing.",
    )
    other = PodcastEpisode(guid="g3", title="Gardening", audio_url="https://x/3")

    hits = filter_episodes_by_text([quantum, described, other], "Quantum")
    assert [e.guid for e in hits] == ["g1", "g2"]
    assert filter_episodes_by_text([quantum, other], "") == [quantum, other]


class TestFilterShowsByText:
    def _shows(self) -> list[PodcastShow]:
        return [
            PodcastShow(id="a", title="Double Tap"),
            PodcastShow(id="b", title="Blind Bargains"),
            PodcastShow(id="c", title="Tap Forms Weekly"),
        ]

    def test_empty_query_matches_everything(self) -> None:
        assert len(filter_shows_by_text(self._shows(), "   ")) == 3

    def test_title_substring_case_insensitive(self) -> None:
        assert [s.id for s in filter_shows_by_text(self._shows(), "TAP")] == ["a", "c"]

    def test_no_match(self) -> None:
        assert filter_shows_by_text(self._shows(), "cooking") == []
