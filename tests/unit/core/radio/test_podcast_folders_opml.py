"""Radio's side of the shared podcast library: folders, OPML, unheard counts.

The store is Quill Cast's own JSON library, so everything here is really a
contract test between the two apps: a folder Radio creates must be a folder
Cast shows, an OPML file imported in Radio must be subscriptions in Cast, and
Mark All as Played from a Radio row must clear the same badge Cast displays.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.opml_import import import_opml_file
from quill.core.podcasts.sorting import unheard_count_for_folder
from quill.core.podcasts.subscriptions import load_library, new_id, save_library
from quill.core.radio import podcast_follow, row_actions
from quill.core.radio.browse_libraries import _my_podcast_level
from quill.core.radio.browse_nodes import split_id


def _episode(guid: str, *, played: bool = False) -> PodcastEpisode:
    return PodcastEpisode(guid=guid, title=guid, audio_url=f"https://x/{guid}.mp3", played=played)


def _seed_library(tmp_path: Path) -> Path:
    """A library with one folder (two shows, one unheard each) and one loose show."""
    library = load_library(tmp_path)
    news = library.add_folder("News")
    for title, folder_id, episodes in (
        ("Morning Brief", news.id, [_episode("m1"), _episode("m2", played=True)]),
        ("Evening Wrap", news.id, [_episode("e1")]),
        ("Loose Show", None, [_episode("l1", played=True)]),
    ):
        show = PodcastShow(
            id=new_id(), title=title, feed_url=f"https://feeds.example/{title.replace(' ', '')}"
        )
        show.folder_id = folder_id
        show.episodes = episodes
        library.shows.append(show)
    save_library(tmp_path, library)
    return tmp_path


# -- the browse tree mirrors the shared folders -------------------------------


def test_subscriptions_level_shows_folders_first_with_recursive_badges(tmp_path: Path) -> None:
    library = load_library(_seed_library(tmp_path))
    nodes = _my_podcast_level(library, None)

    kinds = [split_id(n.node_id)[0] for n in nodes]
    assert kinds == ["mypodcastfolder", "mypodcastshow"]
    # The folder badge counts its whole subtree: m1 + e1 unheard.
    assert nodes[0].label == "News (2 unheard)"
    # The loose show is fully played, so it is simply unbadged.
    assert nodes[1].label == "Loose Show"


def test_a_folder_level_lists_its_own_shows_with_their_badges(tmp_path: Path) -> None:
    library = load_library(_seed_library(tmp_path))
    folder_id = library.folders[0].id
    nodes = _my_podcast_level(library, folder_id)

    assert [n.label for n in nodes] == ["Evening Wrap (1 unheard)", "Morning Brief (1 unheard)"]


def test_unheard_count_for_folder_recurses_subfolders(tmp_path: Path) -> None:
    library = load_library(_seed_library(tmp_path))
    parent = library.folders[0]
    child = library.add_folder("Deep", parent_folder_id=parent.id)
    show = PodcastShow(id=new_id(), title="Nested", feed_url="https://feeds.example/nested")
    show.folder_id = child.id
    show.episodes = [_episode("n1"), _episode("n2")]
    library.shows.append(show)

    assert unheard_count_for_folder(library, parent.id) == 4


# -- Radio's folder verbs write the shared store ------------------------------


def test_create_rename_delete_folder_round_trip(tmp_path: Path) -> None:
    spoken = podcast_follow.create_podcast_folder(tmp_path, "Tech")
    assert "Created folder Tech" in spoken and "Quill Cast" in spoken
    folder = load_library(tmp_path).folders[0]

    spoken = podcast_follow.rename_podcast_folder(tmp_path, folder.id, "Technology")
    assert spoken == "Renamed Tech to Technology."
    assert load_library(tmp_path).folders[0].name == "Technology"

    spoken = podcast_follow.delete_podcast_folder(tmp_path, folder.id)
    assert "nothing was unsubscribed" in spoken
    assert load_library(tmp_path).folders == []


def test_deleting_a_folder_promotes_its_shows(tmp_path: Path) -> None:
    _seed_library(tmp_path)
    library = load_library(tmp_path)
    folder_id = library.folders[0].id

    podcast_follow.delete_podcast_folder(tmp_path, folder_id)

    reloaded = load_library(tmp_path)
    assert reloaded.folders == []
    assert len(reloaded.shows) == 3  # every subscription survived
    assert all(s.folder_id is None for s in reloaded.shows)


def test_move_show_to_folder_and_back(tmp_path: Path) -> None:
    _seed_library(tmp_path)
    feed = "https://feeds.example/LooseShow"
    folder_id = load_library(tmp_path).folders[0].id

    spoken = podcast_follow.move_show_to_folder(tmp_path, feed, folder_id)
    assert spoken == "Moved Loose Show to News."
    assert load_library(tmp_path).find_show_by_feed_url(feed).folder_id == folder_id

    spoken = podcast_follow.move_show_to_folder(tmp_path, feed, None)
    assert spoken == "Moved Loose Show to the top level."


def test_mark_show_played_clears_the_shared_badge(tmp_path: Path) -> None:
    _seed_library(tmp_path)
    feed = "https://feeds.example/MorningBrief"
    assert podcast_follow.unheard_for_feed(tmp_path, feed) == 1

    spoken = podcast_follow.mark_show_played(tmp_path, feed)
    assert spoken == "Marked 1 episode of Morning Brief as played."
    assert podcast_follow.unheard_for_feed(tmp_path, feed) == 0
    # Saying it twice is an answer, not a re-run.
    assert "already marked played" in podcast_follow.mark_show_played(tmp_path, feed)


# -- OPML import, permanent by construction -----------------------------------

_DOWNCAST_SHAPED = """<?xml version="1.0" encoding="UTF-8"?>
<opml version="1.0">
  <head><title>Downcast Podcasts</title></head>
  <body>
    <outline text="TED Talks Daily" type="rss" title="TED Talks Daily"
             xmlUrl="http://feeds.feedburner.com/TEDTalks_audio" htmlUrl="https://www.ted.com" />
    <outline text="The Moth" type="rss" title="The Moth"
             xmlUrl="http://feeds.feedburner.com/themothpodcast" htmlUrl="http://themoth.org/" />
    <outline text="TED again, https flavour" type="rss" title="TED (dup)"
             xmlUrl="https://feeds.feedburner.com/TEDTalks_audio" />
    <outline text="Shows I love">
      <outline text="Nested Show" type="rss" title="Nested Show"
               xmlUrl="https://feeds.example/nested.xml" />
    </outline>
  </body>
</opml>
"""


def test_import_opml_file_adds_dedupes_and_persists(tmp_path: Path) -> None:
    opml = tmp_path / "downcast.opml"
    opml.write_text(_DOWNCAST_SHAPED, encoding="utf-8")

    outcome = import_opml_file(tmp_path, opml)

    # http/https flavours of one feed are one feed: 3 added, 1 file-dup.
    assert outcome.added == 3
    assert outcome.duplicates_in_file == 1
    assert "Quill Cast" in outcome.spoken

    library = load_library(tmp_path)  # a fresh read IS the permanence check
    assert {s.title for s in library.shows} == {"TED Talks Daily", "The Moth", "Nested Show"}
    # The OPML folder became a real library folder, and the show is filed in it.
    assert [f.name for f in library.folders] == ["Shows I love"]
    nested = library.find_show_by_feed_url("https://feeds.example/nested.xml")
    assert nested.folder_id == library.folders[0].id


def test_reimporting_the_same_file_adds_nothing(tmp_path: Path) -> None:
    opml = tmp_path / "downcast.opml"
    opml.write_text(_DOWNCAST_SHAPED, encoding="utf-8")
    import_opml_file(tmp_path, opml)

    outcome = import_opml_file(tmp_path, opml)

    assert outcome.added == 0
    # All four entries -- including the https twin of the TED feed -- now
    # match the library, so the library check claims them before the
    # in-file dedup ever sees a second copy.
    assert outcome.already_followed == 4
    assert len(load_library(tmp_path).shows) == 3


_REAL_OPML = Path("D:/downcast.opml")


@pytest.mark.skipif(not _REAL_OPML.exists(), reason="the real Downcast export is machine-local")
def test_the_real_downcast_export_imports(tmp_path: Path) -> None:
    """The file this feature was asked for: 1307 flat entries, no folders."""
    outcome = import_opml_file(tmp_path, _REAL_OPML)

    assert outcome.added > 1000
    assert outcome.unusable == 0
    library = load_library(tmp_path)
    assert len(library.shows) == outcome.added
    assert library.folders == []  # the export is flat, so no folders appear


# -- the row actions offer the new verbs --------------------------------------


def _labels(actions: list[row_actions.RowAction]) -> list[str]:
    return [a.label.replace("&", "") for a in actions]


def test_subscribed_show_rows_offer_move_and_mark_all_played() -> None:
    state = row_actions.FolderState(is_podcast_show=True, subscribed=True, unheard=3)
    labels = _labels(row_actions.folder_actions("mypodcastshow", state))
    assert "Move to Folder..." in labels
    assert "Mark All as Played..." in labels
    mark = next(
        a
        for a in row_actions.folder_actions("mypodcastshow", state)
        if a.id == row_actions.MARK_ALL_PLAYED
    )
    assert mark.enabled


def test_mark_all_played_is_dimmed_with_nothing_unheard() -> None:
    state = row_actions.FolderState(is_podcast_show=True, subscribed=True, unheard=0)
    mark = next(
        a
        for a in row_actions.folder_actions("mypodcastshow", state)
        if a.id == row_actions.MARK_ALL_PLAYED
    )
    assert not mark.enabled  # dimmed, not hidden


def test_folder_rows_offer_the_folder_verbs() -> None:
    labels = _labels(row_actions.folder_actions("mypodcastfolder", row_actions.FolderState()))
    assert "New Folder Inside..." in labels
    assert "Rename Folder..." in labels
    assert "Delete Folder..." in labels


def test_import_opml_lives_on_the_podcasts_branch_itself() -> None:
    on_root = _labels(
        row_actions.folder_actions("apple", row_actions.FolderState(root_source=True))
    )
    assert "Import Podcasts from OPML..." in on_root
    # ...and only there: not on Subscriptions, not on a storefront.
    for kind, state in (
        ("mypodcasts", row_actions.FolderState()),
        ("apple", row_actions.FolderState(root_source=False)),
    ):
        assert "Import Podcasts from OPML..." not in _labels(
            row_actions.folder_actions(kind, state)
        )


def test_subscriptions_root_offers_new_folder() -> None:
    labels = _labels(row_actions.folder_actions("mypodcasts", row_actions.FolderState()))
    assert "New Folder..." in labels
