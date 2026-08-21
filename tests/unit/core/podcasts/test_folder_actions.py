"""A folder as a listening lens: the subtree walk, the guards, the grouping.

The three that carry the design are the subtree walk (a folder means everything
beneath it), the cycle guard on ``move_folder`` (a folder that becomes its own
descendant is a tree nothing can render and nobody can undo), and the rule that
"play all unplayed" means one episode per show.
"""

from __future__ import annotations

from quill.core.podcasts import folder_actions
from quill.core.podcasts import queue as queue_ops
from quill.core.podcasts.models import PodcastEpisode, PodcastFolder, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary


def _episode(guid: str, *, played: bool = False, position_ms: int = 0) -> PodcastEpisode:
    return PodcastEpisode(
        guid=guid,
        title=f"Episode {guid}",
        audio_url=f"https://cdn.example.com/{guid}.mp3",
        played=played,
        position_ms=position_ms,
    )


def _library() -> PodcastLibrary:
    library = PodcastLibrary()
    library.folders = [
        PodcastFolder(id="news", name="News"),
        PodcastFolder(id="local", name="Local", parent_folder_id="news"),
        PodcastFolder(id="music", name="Music"),
    ]
    top = PodcastShow(id="s1", title="Top News", feed_url="https://f/1", folder_id="news")
    top.episodes = [_episode("a"), _episode("b")]
    nested = PodcastShow(id="s2", title="Local News", feed_url="https://f/2", folder_id="local")
    nested.episodes = [_episode("c")]
    other = PodcastShow(id="s3", title="Jazz", feed_url="https://f/3", folder_id="music")
    other.episodes = [_episode("d")]
    loose = PodcastShow(id="s4", title="Unfiled", feed_url="https://f/4")
    loose.episodes = [_episode("e")]
    library.shows = [top, nested, other, loose]
    return library


# -- the walk ----------------------------------------------------------------


def test_a_folder_means_its_whole_subtree() -> None:
    library = _library()
    assert folder_actions.subtree_folder_ids(library, "news") == ["news", "local"]
    assert folder_actions.subtree_show_ids(library, "news") == ["s1", "s2"]


def test_a_leaf_folder_is_just_itself() -> None:
    assert folder_actions.subtree_show_ids(_library(), "music") == ["s3"]


def test_an_unknown_folder_holds_nothing() -> None:
    assert folder_actions.subtree_show_ids(_library(), "nope") == []
    assert folder_actions.subtree_show_ids(_library(), "") == []


def test_a_ring_in_the_tree_does_not_hang_the_walk() -> None:
    """A hand-edited file can produce one, and it must not take the app with it."""
    library = _library()
    library.find_folder("news").parent_folder_id = "local"
    assert folder_actions.subtree_folder_ids(library, "news") == ["news", "local"]


# -- what to play ------------------------------------------------------------


def test_play_all_unplayed_is_one_episode_per_show() -> None:
    """A folder of forty shows holds hundreds; a queue of hundreds is not a queue."""
    library = _library()
    chosen = folder_actions.latest_unplayed_per_show(library, "news")
    assert [show.id for show, _episode in chosen] == ["s1", "s2"]


def test_a_part_played_episode_is_a_decision_already_made() -> None:
    library = _library()
    library.shows[0].episodes[0].position_ms = 60_000
    unplayed = folder_actions.unplayed_in_folder(library, "news")
    assert [episode.guid for _show, episode in unplayed] == ["b", "c"]


def test_a_finished_episode_is_not_offered() -> None:
    library = _library()
    for episode in library.shows[0].episodes:
        episode.played = True
    assert [show.id for show, _e in folder_actions.latest_unplayed_per_show(library, "news")] == [
        "s2"
    ]


def test_a_folder_row_says_what_it_holds() -> None:
    said = folder_actions.describe_folder(_library(), "news")
    assert said == "News, folder, 2 podcasts, 3 new"


# -- moving and reordering ---------------------------------------------------


def test_a_folder_cannot_become_its_own_descendant() -> None:
    library = _library()
    assert folder_actions.move_folder(library, "news", "local") is False
    assert folder_actions.move_folder(library, "news", "news") is False
    assert library.find_folder("news").parent_folder_id is None


def test_a_folder_moves_to_a_real_parent() -> None:
    library = _library()
    assert folder_actions.move_folder(library, "music", "news") is True
    assert library.find_folder("music").parent_folder_id == "news"
    assert folder_actions.subtree_show_ids(library, "news") == ["s1", "s2", "s3"]


def test_moving_to_a_folder_that_does_not_exist_changes_nothing() -> None:
    library = _library()
    assert folder_actions.move_folder(library, "music", "ghost") is False
    assert library.find_folder("music").parent_folder_id is None


def test_reorder_reports_the_new_position_and_stops_at_the_edges() -> None:
    library = _library()
    # Two top-level folders. With no order set yet they read alphabetically,
    # so Music is first and News second until somebody says otherwise.
    assert folder_actions.reorder_folder(library, "music", -1) == -1
    assert folder_actions.reorder_folder(library, "music", 1) == 1
    assert folder_actions.reorder_folder(library, "music", 1) == -1
    assert folder_actions.reorder_folder(library, "music", -1) == 0


def test_a_chosen_order_outranks_the_alphabet() -> None:
    """Once somebody has arranged the folders, the names stop deciding."""
    library = _library()
    folder_actions.reorder_folder(library, "music", 1)
    order = sorted(
        (row for row in library.folders if row.parent_folder_id is None),
        key=lambda row: row.sort_order,
    )
    assert [row.name for row in order] == ["News", "Music"]


def test_the_order_survives_a_save(tmp_path: object) -> None:
    from quill.core.podcasts.models import PodcastFolder as Folder

    folder = Folder(id="f", name="News", sort_order=3)
    restored = Folder.from_dict(folder.to_dict())
    assert restored is not None
    assert restored.sort_order == 3
    # And a folder saved before the field existed simply starts at zero.
    older = Folder.from_dict({"id": "f", "name": "News"})
    assert older is not None
    assert older.sort_order == 0


# -- OPML --------------------------------------------------------------------


def test_a_folder_exports_as_its_own_tree() -> None:
    from quill.core.podcasts.opml import export_subtree, parse_opml

    text = export_subtree(_library(), "news")
    imported = parse_opml(text)
    assert {row.title for row in imported} == {"Top News", "Local News"}
    # The chosen folder is the outermost outline, so importing recreates it.
    assert [row.folder_path for row in imported if row.title == "Local News"] == [["News", "Local"]]


def test_exporting_nothing_is_an_empty_string() -> None:
    from quill.core.podcasts.opml import export_subtree

    assert export_subtree(_library(), "ghost") == ""


# -- grouping the queue (C5) -------------------------------------------------


def _queued(library: PodcastLibrary) -> None:
    queue_ops.add_to_queue(library, "s1", "a")
    queue_ops.add_to_queue(library, "s3", "d")
    queue_ops.add_to_queue(library, "s2", "c")
    queue_ops.add_to_queue(library, "s4", "e")


def test_ungrouped_is_one_unlabelled_group() -> None:
    """One shape to render, not two."""
    library = _library()
    _queued(library)
    assert queue_ops.group_queue_by(library, "none") == [("", [0, 1, 2, 3])]


def test_grouping_by_folder_uses_the_folder_names() -> None:
    library = _library()
    _queued(library)
    groups = queue_ops.group_queue_by(library, "folder")
    assert [label for label, _indices in groups] == ["News", "Music", "Local", "Not in a folder"]
    assert [indices for _label, indices in groups] == [[0], [1], [2], [3]]


def test_grouping_by_show_keeps_play_order() -> None:
    """Whatever the mode, the first group is what plays next."""
    library = _library()
    _queued(library)
    groups = queue_ops.group_queue_by(library, "show")
    assert [label for label, _indices in groups] == ["Top News", "Jazz", "Local News", "Unfiled"]


def test_a_podcast_with_no_folder_is_not_uncategorised() -> None:
    """It has not failed to be filed; it simply is not in a folder."""
    library = _library()
    queue_ops.add_to_queue(library, "s4", "e")
    assert queue_ops.group_queue_by(library, "folder")[0][0] == "Not in a folder"


def test_an_unknown_mode_reads_as_ungrouped() -> None:
    library = _library()
    _queued(library)
    assert queue_ops.group_queue_by(library, "spiral") == [("", [0, 1, 2, 3])]
