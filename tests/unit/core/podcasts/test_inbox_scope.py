"""The Inbox narrowed to one library folder (ear.md R4), and Remove from Inbox (R3).

Two features in one file because they are the same seam from two sides: what the
Inbox shows, and what leaves it. The tests that matter most are the ones about
**not lying about an empty list** -- an Inbox that is empty because of a filter,
and says only "empty", is how somebody concludes their episodes are gone.
"""

from __future__ import annotations

from quill.core.podcasts import inbox_scope
from quill.core.podcasts.inbox import REMOVED_MARKER, inbox_pairs
from quill.core.podcasts.inbox_removal import is_removed, remove_from_inbox, restore
from quill.core.podcasts.models import PodcastEpisode, PodcastFolder, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary


def _episode(guid: str, **kwargs) -> PodcastEpisode:
    base = {
        "guid": guid,
        "title": guid.upper(),
        "audio_url": f"https://e/{guid}.mp3",
        "published": "2026-09-01T00:00:00",
    }
    base.update(kwargs)
    return PodcastEpisode(**base)


def _show(show_id: str, title: str, folder: str | None, *guids: str, **kwargs) -> PodcastShow:
    return PodcastShow(
        id=show_id,
        title=title,
        feed_url=f"https://e/{show_id}.xml",
        folder_id=folder,
        route_to_inbox=True,
        episodes=[_episode(g) for g in guids],
        **kwargs,
    )


def _library() -> PodcastLibrary:
    """News > Mornings, plus an unfiled show, all routed to the Inbox."""
    return PodcastLibrary(
        folders=[
            PodcastFolder(id="news", name="News"),
            PodcastFolder(id="morn", name="Mornings", parent_folder_id="news"),
            PodcastFolder(id="hist", name="History"),
        ],
        shows=[
            _show("s1", "The Daily", "news", "a1"),
            _show("s2", "Breakfast", "morn", "b1", "b2"),
            _show("s3", "Loose", None, "c1"),
            _show("s4", "Long Ago", "hist", "d1"),
        ],
    )


# -- the scope ---------------------------------------------------------------- #


def test_no_scope_is_the_whole_inbox() -> None:
    library = _library()
    assert len(inbox_scope.inbox_pairs_in_library_folder(library, inbox_scope.ALL)) == 5
    assert len(inbox_scope.inbox_pairs_in_library_folder(library, None)) == 5


def test_a_folder_includes_its_subfolders() -> None:
    """Somebody who filed Morning News under News and asked for the News Inbox
    means both. A filter answering only the immediate shows would look broken."""
    pairs = inbox_scope.inbox_pairs_in_library_folder(_library(), "news")
    assert sorted(ep.guid for _s, ep in pairs) == ["a1", "b1", "b2"]


def test_a_subfolder_on_its_own_is_only_itself() -> None:
    pairs = inbox_scope.inbox_pairs_in_library_folder(_library(), "morn")
    assert sorted(ep.guid for _s, ep in pairs) == ["b1", "b2"]


def test_unfiled_is_its_own_scope_and_is_not_the_same_as_no_filter() -> None:
    """``None`` already means "the library's top level" for a folder id, and two
    different nothings in one parameter is how a filter shows the wrong rows."""
    pairs = inbox_scope.inbox_pairs_in_library_folder(_library(), inbox_scope.UNFILED)
    assert [ep.guid for _s, ep in pairs] == ["c1"]


def test_a_deleted_folder_shows_nothing_rather_than_everything() -> None:
    """A filter pointing at a deleted folder is a filter that is on, and showing
    the whole Inbox as though it were off would misreport what is on screen."""
    assert inbox_scope.inbox_pairs_in_library_folder(_library(), "gone") == []


def test_the_chooser_only_offers_folders_that_have_something() -> None:
    """A chooser listing forty folders of which three have anything makes the
    listener find the three by trying them."""
    library = _library()
    library.shows = [show for show in library.shows if show.id != "s4"]
    offered = inbox_scope.folder_ids_with_inbox(library)
    assert "hist" not in offered
    assert set(offered) == {"news", "morn"}


def test_the_scope_label_reads_as_a_path() -> None:
    library = _library()
    assert inbox_scope.scope_label(library, "morn") == "News > Mornings"
    assert inbox_scope.scope_label(library, inbox_scope.ALL) == "All podcasts"
    assert inbox_scope.scope_label(library, inbox_scope.UNFILED) == "Not in a folder"
    assert "no longer exists" in inbox_scope.scope_label(library, "gone")


# -- the three different empties ---------------------------------------------- #


def test_an_empty_filtered_inbox_says_the_rest_is_still_there() -> None:
    library = _library()
    library.shows = [show for show in library.shows if show.folder_id != "hist"]
    library.folders.append(PodcastFolder(id="empty", name="Sport"))

    text = inbox_scope.empty_state(library, "empty")
    assert "Nothing in the Inbox for Sport" in text
    assert "All podcasts to see it" in text


def test_an_entirely_empty_inbox_says_how_episodes_get_here() -> None:
    library = PodcastLibrary()
    text = inbox_scope.empty_state(library, inbox_scope.ALL)
    assert "Route to Inbox" in text


def test_an_empty_inbox_under_a_filter_does_not_blame_the_filter() -> None:
    library = PodcastLibrary(folders=[PodcastFolder(id="news", name="News")])
    assert inbox_scope.empty_state(library, "news") == (
        "The Inbox is empty, for News and everywhere else."
    )


def test_a_full_scope_has_no_empty_state() -> None:
    assert inbox_scope.empty_state(_library(), "news") == ""


# -- Remove from Inbox (R3) --------------------------------------------------- #


def test_removing_takes_it_out_of_the_inbox_and_leaves_it_in_its_show() -> None:
    library = _library()
    show = library.find_show("s1")
    assert show is not None
    episode = show.episodes[0]

    result = remove_from_inbox(library, [(show, episode)])

    assert result.removed == 1
    assert is_removed(library, show, episode)
    assert episode.guid not in [ep.guid for _s, ep in inbox_pairs(library)]
    assert episode in show.episodes
    assert episode.played is False, "removing is not listening"


def test_removing_deletes_the_download_only_when_the_setting_says_so() -> None:
    library = _library()
    keep, clear = library.find_show("s1"), library.find_show("s2")
    assert keep is not None and clear is not None
    keep.episodes[0].downloaded_path = "C:/d/keep.mp3"
    clear.episodes[0].downloaded_path = "C:/d/clear.mp3"
    library.apply_show_override(clear, delete_after_play=True)

    result = remove_from_inbox(library, [(keep, keep.episodes[0]), (clear, clear.episodes[0])])

    assert result.delete_paths == ["C:/d/clear.mp3"]
    assert keep.episodes[0].downloaded_path == "C:/d/keep.mp3"
    assert clear.episodes[0].downloaded_path == "", "the record must not claim a deleted file"


def test_a_republished_episode_the_listener_dismissed_stays_dismissed() -> None:
    """The reason there are two markers. ``resurface_republished`` deliberately
    brings a *cap-trimmed* episode back when it is re-cut; an episode somebody
    dismissed by hand coming back would read as Cast forgetting the decision."""
    from quill.core.podcasts.inbox import resurface_republished

    library = _library()
    show = library.find_show("s1")
    assert show is not None
    episode = show.episodes[0]
    remove_from_inbox(library, [(show, episode)])

    assert resurface_republished(library, show, [episode.guid]) == []
    assert is_removed(library, show, episode)


def test_a_cap_trim_is_still_reversible_by_the_app() -> None:
    """The other half of the same rule: the cap's marker is the app's to clear."""
    from quill.core.podcasts.inbox import TRIMMED_MARKER, inbox_key, resurface_republished

    library = _library()
    show = library.find_show("s1")
    assert show is not None
    episode = show.episodes[0]
    library.inbox_assignments[inbox_key(show.id, episode.guid)] = TRIMMED_MARKER

    assert resurface_republished(library, show, [episode.guid]) == [episode]


def test_removing_twice_reports_the_second_as_skipped() -> None:
    library = _library()
    show = library.find_show("s1")
    assert show is not None
    episode = show.episodes[0]
    remove_from_inbox(library, [(show, episode)])

    again = remove_from_inbox(library, [(show, episode)])
    assert again.removed == 0
    assert again.skipped == 1


def test_one_removal_says_nothing_and_several_say_a_count() -> None:
    """The row disappearing from a list the reader is on *is* the feedback; a
    listener cannot see how much shorter a list of forty got."""
    library = _library()
    show = library.find_show("s2")
    assert show is not None

    one = remove_from_inbox(library, [(show, show.episodes[0])])
    assert one.announcement() == ""

    library2 = _library()
    show2 = library2.find_show("s2")
    assert show2 is not None
    many = remove_from_inbox(library2, [(show2, ep) for ep in show2.episodes])
    assert many.announcement() == "2 episodes removed from the Inbox"


def test_the_announcement_counts_deleted_downloads_too() -> None:
    library = _library()
    show = library.find_show("s2")
    assert show is not None
    library.apply_show_override(show, delete_after_play=True)
    for index, episode in enumerate(show.episodes):
        episode.downloaded_path = f"C:/d/{index}.mp3"

    result = remove_from_inbox(library, [(show, ep) for ep in show.episodes])
    assert result.announcement() == "2 episodes removed from the Inbox, 2 downloads deleted"


def test_restore_puts_it_back_and_only_for_a_hand_removal() -> None:
    library = _library()
    show = library.find_show("s1")
    assert show is not None
    episode = show.episodes[0]
    remove_from_inbox(library, [(show, episode)])

    assert restore(library, show, episode) is True
    assert episode.guid in [ep.guid for _s, ep in inbox_pairs(library)]
    assert restore(library, show, episode) is False


def test_a_removed_episode_is_not_reported_as_cap_trimmed() -> None:
    """The two markers have to stay distinguishable in both directions."""
    from quill.core.podcasts.inbox import is_trimmed

    library = _library()
    show = library.find_show("s1")
    assert show is not None
    episode = show.episodes[0]
    remove_from_inbox(library, [(show, episode)])

    assert is_trimmed(library, show, episode) is False
    assert is_removed(library, show, episode) is True


def test_the_marker_is_not_a_folder_id_anything_could_collide_with() -> None:
    assert REMOVED_MARKER.startswith("\x00")
