"""The widened smart-playlist rules: one case per new field, plus the two rules.

The two rules being: a rule left at its "does not narrow" value contributes
nothing at all (which is what makes ``any`` mode behave), and the item limit is
applied **after** sorting, so "the ten newest" is the ten newest.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

from quill.core.podcasts.models import Playlist, PodcastEpisode, PodcastFolder, PodcastShow
from quill.core.podcasts.models_playlists import PlaylistRules
from quill.core.podcasts.playlists import (
    STARTERS,
    add_starter_playlists,
    resolve_playlist,
)
from quill.core.podcasts.subscriptions import PodcastLibrary


def _episode(guid: str, **fields: object) -> PodcastEpisode:
    episode = PodcastEpisode(
        guid=guid,
        title=f"Episode {guid}",
        audio_url=f"https://cdn.example.com/{guid}.mp3",
        # RFC 2822, which is what an RSS pubDate is and what sorting parses.
        published=format_datetime(datetime.now(UTC) - timedelta(days=1)),
        duration_seconds=1800,
    )
    for name, value in fields.items():
        setattr(episode, name, value)
    return episode


def _library() -> PodcastLibrary:
    library = PodcastLibrary()
    library.folders = [PodcastFolder(id="news", name="News")]
    news = PodcastShow(id="s1", title="News Show", feed_url="https://f/1", folder_id="news")
    news.episodes = [
        _episode("short", duration_seconds=600),
        _episode("long", duration_seconds=5400),
        _episode("done", played=True),
        _episode("started", position_ms=60_000),
        _episode("downloaded", downloaded_path="C:/audio/x.mp3"),
        _episode("old", published=format_datetime(datetime.now(UTC) - timedelta(days=90))),
        _episode("braille", description="A demonstration of a braille display."),
    ]
    other = PodcastShow(id="s2", title="Music Show", feed_url="https://f/2")
    other.episodes = [_episode("jazz")]
    library.shows = [news, other]
    return library


def _resolve(library: PodcastLibrary, **rules: object) -> list[str]:
    playlist = Playlist(
        id="p", name="Test", kind="smart", rules=PlaylistRules.from_dict(dict(rules))
    )
    return [episode.guid for _show, episode in resolve_playlist(library, playlist)]


# -- one case per new field --------------------------------------------------


def test_no_rules_at_all_matches_everything() -> None:
    """A brand-new playlist must look unfiltered, not broken."""
    assert len(_resolve(_library())) == 8


def test_a_folder_rule_is_subtree_aware() -> None:
    found = _resolve(_library(), folder_ids=["news"])
    assert "jazz" not in found
    assert "short" in found


def test_download_state() -> None:
    assert _resolve(_library(), download_state="downloaded") == ["downloaded"]
    assert "downloaded" not in _resolve(_library(), download_state="not_downloaded")


def test_progress_is_not_the_played_mark() -> None:
    """An episode can be marked played and still hold a position."""
    assert _resolve(_library(), progress="started") == ["started"]
    assert _resolve(_library(), progress="finished") == ["done"]
    unstarted = _resolve(_library(), progress="unstarted")
    assert "started" not in unstarted and "done" not in unstarted


def test_text_matches_the_title_or_the_show_notes() -> None:
    assert _resolve(_library(), text_contains="braille") == ["braille"]
    assert _resolve(_library(), text_contains="BRAILLE") == ["braille"]
    assert _resolve(_library(), text_contains="episode short") == ["short"]


def test_the_item_limit_applies_after_sorting() -> None:
    """ "The two newest" has to be the two newest, not two arbitrary matches."""
    library = _library()
    everything = _resolve(library, sort_mode="duration_longest")
    limited = _resolve(library, sort_mode="duration_longest", item_limit=2)
    assert limited == everything[:2]
    assert limited[0] == "long"


def test_match_any_is_a_union_not_an_intersection() -> None:
    """Expressible only with OR: downloaded things, plus anything long."""
    found = _resolve(
        _library(),
        match_mode="any",
        download_state="downloaded",
        min_duration_minutes=60,
    )
    assert set(found) == {"downloaded", "long"}


def test_an_unset_rule_contributes_nothing_under_any() -> None:
    """Otherwise every 'any' playlist would match the whole library."""
    found = _resolve(_library(), match_mode="any", download_state="downloaded")
    assert found == ["downloaded"]


def test_scope_is_always_and_even_under_any() -> None:
    """ "Any of these rules, but only in this folder" is what naming one means."""
    found = _resolve(
        _library(),
        match_mode="any",
        folder_ids=["news"],
        download_state="downloaded",
        min_duration_minutes=60,
    )
    assert set(found) == {"downloaded", "long"}
    assert "jazz" not in found


def test_the_rules_round_trip_and_tolerate_junk() -> None:
    rules = PlaylistRules.from_dict({
        "match_mode": "any",
        "folder_ids": ["news"],
        "download_state": "downloaded",
        "has_note": "has_note",
        "text_contains": "braille",
        "progress": "started",
        "item_limit": 10,
    })
    restored = PlaylistRules.from_dict(rules.to_dict())
    assert restored == rules

    junk = PlaylistRules.from_dict({
        "match_mode": "sometimes",
        "download_state": "maybe",
        "progress": "sideways",
        "has_note": "possibly",
        "item_limit": -5,
    })
    assert junk.match_mode == "all"
    assert junk.download_state == "any"
    assert junk.progress == "any"
    assert junk.has_note == "any"
    assert junk.item_limit == 0


def test_an_old_rules_file_still_reads() -> None:
    """Every new field must default to 'does not narrow'."""
    old = PlaylistRules.from_dict({"episode_status": "unplayed", "sort_mode": "date_newest"})
    assert old.match_mode == "all"
    assert old.folder_ids == []
    assert old.item_limit == 0


# -- the starters ------------------------------------------------------------


def test_the_starters_arrive_as_ordinary_editable_playlists() -> None:
    library = _library()
    added = add_starter_playlists(library)
    assert added == [name for name, _rules in STARTERS]
    assert all(playlist.kind == "smart" for playlist in library.playlists)
    # Editable means editable: nothing marks them as built in.
    assert all(playlist.id for playlist in library.playlists)


def test_adding_them_twice_adds_nothing_the_second_time() -> None:
    library = _library()
    add_starter_playlists(library)
    assert add_starter_playlists(library) == []
    assert len(library.playlists) == len(STARTERS)


def test_a_starter_somebody_renamed_is_not_recreated_under_its_old_name() -> None:
    """The name is theirs now."""
    library = _library()
    add_starter_playlists(library)
    library.playlists[0].name = "My Continue List"
    added = add_starter_playlists(library)
    assert added == ["Continue Listening"]


def test_every_starter_actually_resolves() -> None:
    """A starter that matched nothing on any library would be a broken example."""
    library = _library()
    add_starter_playlists(library)
    resolved = {
        playlist.name: resolve_playlist(library, playlist) for playlist in library.playlists
    }
    assert resolved["Continue Listening"]
    assert resolved["New This Week"]
    assert resolved["Quick Listens"]
    assert resolved["Downloaded and Unplayed"]
    assert resolved["Long Reads"]
