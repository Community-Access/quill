"""What each kind of browse row offers.

The old context menu knew three kinds of row -- playable, lazily playable, and
folder -- which was right when the tree held radio stations and quietly wrong
once it held podcasts, audiobooks, followed channels and community uploads.
The consequence was not a missing nicety: a listener who found a podcast show
while browsing **could not subscribe to it**, because the menu had no concept
of a show.

Pinned here is that each row type offers what suits it, and does not offer what
does not: no "Report Bad Station" on a book chapter, no "Subscribe" on a genre
folder, no "Stop Following" on anything the listener did not choose to follow.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.radio import row_actions
from quill.core.radio.row_actions import FolderState, actions_for


@dataclass
class _Row:
    homepage: str = ""
    is_recording: bool = False


def _ids(actions) -> list[str]:
    return [action.id for action in actions]


def _label(actions, action_id: str) -> str:
    return next(action.label for action in actions if action.id == action_id)


# -- playable rows -------------------------------------------------------------


def test_a_live_station_offers_the_station_actions() -> None:
    ids = _ids(
        actions_for(
            "rbcountry",
            station=_Row(homepage="https://example.org"),
            can_download=False,
            can_report=True,
        )
    )
    assert ids[0] == row_actions.PLAY
    assert row_actions.FAVORITE_ADD in ids
    assert row_actions.REPORT_BAD in ids
    assert row_actions.DOWNLOAD not in ids  # a live stream has no file to save


def test_a_recording_can_be_downloaded_and_is_not_a_bad_station() -> None:
    """A podcast episode or book chapter is a work, not a stream: reporting it
    as a bad *station* would file something nobody can act on."""
    ids = _ids(
        actions_for(
            "appleshow",
            station=_Row(is_recording=True),
            can_download=True,
            can_report=True,
        )
    )
    assert row_actions.DOWNLOAD in ids
    assert row_actions.REPORT_BAD not in ids


def test_copy_says_link_for_a_recording_and_stream_for_a_station() -> None:
    recording = actions_for("archiveitem", station=_Row(is_recording=True))
    live = actions_for("rbgenre", station=_Row())
    assert _label(recording, row_actions.COPY_LINK) == "&Copy Link"
    assert _label(live, row_actions.COPY_LINK) == "&Copy Stream Link"


def test_a_playing_row_offers_stop_rather_than_play() -> None:
    assert _ids(actions_for("soma", station=_Row(), playing=True))[0] == row_actions.STOP


def test_a_saved_row_offers_removal() -> None:
    ids = _ids(actions_for("soma", station=_Row(), saved=True))
    assert row_actions.FAVORITE_REMOVE in ids and row_actions.FAVORITE_ADD not in ids


def test_a_row_with_no_homepage_does_not_offer_to_open_one() -> None:
    assert row_actions.OPEN_SITE not in _ids(actions_for("soma", station=_Row()))


def test_a_lazily_resolved_row_can_still_be_favorited() -> None:
    """TuneIn works out its stream on play; it can be followed before that."""
    ids = _ids(actions_for("tuneinstation", resolve_lazily=True))
    assert ids == [row_actions.PLAY, row_actions.FAVORITE_ADD]


# -- folders -------------------------------------------------------------------


def test_a_podcast_show_can_be_subscribed_to() -> None:
    """The gap this module was written for."""
    ids = _ids(actions_for("appleshow", is_folder=True, folder_state=FolderState()))
    assert row_actions.SUBSCRIBE_PODCAST in ids
    assert row_actions.COPY_FEED in ids


def test_an_already_followed_show_offers_unsubscribe_instead() -> None:
    # "Already Subscribed" was a menu item whose only power was to repeat
    # itself; subscribed, the slot is now a real Unsubscribe.
    actions = actions_for("appleshow", is_folder=True, folder_state=FolderState(subscribed=True))
    ids = _ids(actions)
    assert row_actions.UNSUBSCRIBE_PODCAST in ids
    assert row_actions.SUBSCRIBE_PODCAST not in ids
    assert "Unsu" in _label(actions, row_actions.UNSUBSCRIBE_PODCAST)


def test_a_subscribed_show_in_the_subscriptions_branch_is_a_show_too() -> None:
    # Subscriptions rows carry the feed in the node id; the menu must offer
    # the same show actions the Apple directory rows get.
    ids = _ids(actions_for("mypodcastshow", is_folder=True, folder_state=FolderState()))
    assert row_actions.SUBSCRIBE_PODCAST in ids  # unsubscribed until state says otherwise
    assert row_actions.COPY_FEED in ids


def test_an_expanded_folder_offers_close_rather_than_open() -> None:
    collapsed = _ids(actions_for("rbcountry", is_folder=True, folder_state=FolderState()))
    expanded = _ids(
        actions_for("rbcountry", is_folder=True, folder_state=FolderState(expanded=True))
    )
    assert collapsed[0] == row_actions.OPEN_FOLDER
    assert expanded[0] == row_actions.CLOSE_FOLDER
    assert row_actions.OPEN_FOLDER not in expanded


def test_an_ordinary_folder_offers_no_subscription() -> None:
    ids = _ids(actions_for("rbcountry", is_folder=True, folder_state=FolderState()))
    assert row_actions.SUBSCRIBE_PODCAST not in ids
    assert row_actions.UNFOLLOW_CHANNEL not in ids
    assert ids[:2] == [row_actions.OPEN_FOLDER, row_actions.REFRESH]


def test_a_followed_channel_can_be_unfollowed_from_the_same_menu() -> None:
    ids = _ids(actions_for("youtubechannel", is_folder=True, folder_state=FolderState()))
    assert row_actions.UNFOLLOW_CHANNEL in ids


def test_a_folder_counts_what_it_already_holds() -> None:
    actions = actions_for(
        "librivoxgenre", is_folder=True, folder_state=FolderState(loaded_stations=12)
    )
    assert "12" in _label(actions, row_actions.FAVORITE_FOLDER)


def test_an_unloaded_folder_offers_no_add_all() -> None:
    # With nothing under the row yet, "Add All Episodes to Favorites" adds
    # nothing; the honest menu leaves it out until Open loads the rows.
    ids = _ids(actions_for("appleshow", is_folder=True, folder_state=FolderState()))
    assert row_actions.FAVORITE_FOLDER not in ids


def test_download_all_appears_only_when_something_is_savable() -> None:
    without = _ids(
        actions_for("rbcountry", is_folder=True, folder_state=FolderState(loaded_stations=5))
    )
    assert row_actions.DOWNLOAD_ALL not in without
    with_files = actions_for(
        "librivoxbook", is_folder=True, folder_state=FolderState(loaded_stations=9, savable=9)
    )
    assert "9" in _label(with_files, row_actions.DOWNLOAD_ALL)


def test_a_row_that_is_neither_playable_nor_a_folder_offers_nothing() -> None:
    assert actions_for("placeholder") == []


# --- every branch, not just the ones someone remembered ------------------------


def _mnemonics(labels: list[str]) -> list[str]:
    import re

    return [m.group(1).lower() for label in labels if (m := re.search(r"&(.)", label))]


def _every_menu() -> list[tuple[str, list]]:
    """Each menu the browse tree can build, across every registered kind."""
    from quill.core.radio import browse_sources

    states = [
        FolderState(),
        FolderState(loaded_stations=5, savable=3),
        FolderState(subscribed=True, loaded_stations=5, savable=3),
        FolderState(is_podcast_show=True, is_followed_channel=True, loaded_stations=2),
        # Expanded variants too: "&Close" claims a key the collapsed menus
        # never showed, and it must not collide with anything (it did --
        # "Stop Following This &Channel" also said C).
        FolderState(expanded=True, loaded_stations=5, savable=3),
        FolderState(expanded=True, subscribed=True, is_followed_channel=True, loaded_stations=2),
    ]
    menus = [
        (kind, row_actions.folder_actions(kind, state))
        for kind in browse_sources._HANDLERS
        for state in states
    ]
    for playing in (True, False):
        for saved in (True, False):
            for recording in (True, False):
                menus.append((
                    "station",
                    row_actions.station_actions(
                        playing=playing,
                        saved=saved,
                        has_homepage=True,
                        can_download=True,
                        can_report=True,
                        is_recording=recording,
                    ),
                ))
    menus.append(("lazy", row_actions.lazy_leaf_actions(saved=False)))
    return menus


def test_no_menu_claims_one_access_key_twice() -> None:
    # Two items answering the same key means one of them silently never fires.
    # "Station &Details" and "&Download" both claimed D, and on a podcast show
    # "Copy &Feed Address" collided with "to &Favorites" -- the one menu the
    # rich-menu work existed to build (found by sweeping all branches
    # 2026-08-16, after Shift+F10 was reported dead on podcasts).
    for kind, actions in _every_menu():
        keys = _mnemonics([a.label for a in actions])
        duplicates = {k for k in keys if keys.count(k) > 1}
        assert not duplicates, f"{kind} claims {duplicates} twice: {[a.label for a in actions]}"


def test_every_item_in_every_menu_offers_an_access_key() -> None:
    for kind, actions in _every_menu():
        for action in actions:
            assert "&" in action.label, f"{kind}: {action.label!r} has no access key"


def test_every_browsable_kind_gets_a_usable_folder_menu() -> None:
    from quill.core.radio import browse_sources

    for kind in browse_sources._HANDLERS:
        ids = _ids(actions_for(kind, is_folder=True, folder_state=FolderState()))
        assert row_actions.OPEN_FOLDER in ids, f"{kind} cannot be opened from its menu"
        assert row_actions.REFRESH in ids, f"{kind} cannot be refreshed from its menu"


def test_a_folder_menu_names_what_the_folder_actually_holds() -> None:
    # "Add All Stations to Favorites" on a book, a show and a channel was the
    # wording 39 of 41 branches shipped with.
    def label_for(kind: str) -> str:
        return _label(
            actions_for(kind, is_folder=True, folder_state=FolderState(loaded_stations=4)),
            row_actions.FAVORITE_FOLDER,
        )

    assert "Chapters" in label_for("librivoxbook")
    assert "Episodes" in label_for("appleshow")
    assert "Videos" in label_for("youtubechannel")
    assert "Books" in label_for("gutenberg")
    assert "Tracks" in label_for("audius")
    assert "Stations" in label_for("rbcountry"), "a radio branch still says stations"


def test_the_contents_vocabulary_only_names_real_branches() -> None:
    from quill.core.radio import browse_sources

    unknown = set(row_actions.FOLDER_CONTENTS) - set(browse_sources._HANDLERS)
    assert not unknown, f"{unknown} name no browsable kind"


def test_a_root_source_can_be_hidden_in_place_and_reset() -> None:
    """Hide This Source / Reset Sources to Default live on top-level branches
    only -- the rows Choose Browse Sources governs."""
    root = _ids(actions_for("popular", is_folder=True, folder_state=FolderState(root_source=True)))
    assert row_actions.HIDE_SOURCE in root
    assert row_actions.RESET_SOURCES in root
    nested = _ids(actions_for("rbcountry", is_folder=True, folder_state=FolderState()))
    assert row_actions.HIDE_SOURCE not in nested
    assert row_actions.RESET_SOURCES not in nested


def test_a_transcript_bearing_episode_offers_view_transcript() -> None:
    # The podepisode node id carries the feed's transcript address, so the
    # transcript is readable without playing the episode.
    ids = _ids(actions_for("podepisode", station=_Row(is_recording=True)))
    assert row_actions.VIEW_TRANSCRIPT in ids


def test_a_youtube_row_offers_view_transcript_without_playing() -> None:
    @dataclass
    class _Video(_Row):
        stream_url: str = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    ids = _ids(actions_for("ytvideo", station=_Video(is_recording=True)))
    assert row_actions.VIEW_TRANSCRIPT in ids
    assert row_actions.REMOVE_SAVED in ids


def test_an_ordinary_station_offers_no_transcript() -> None:
    ids = _ids(actions_for("station", station=_Row()))
    assert row_actions.VIEW_TRANSCRIPT not in ids


# -- the 2026-08-18 round: downloads on the show, record on the row, search --


def test_a_subscribed_show_offers_the_download_pair_from_the_library() -> None:
    """Download All Episodes counts from the shared library, so it works
    before the branch is ever expanded; Remove All Downloads dims (never
    vanishes) when the downloads folder is empty -- same rule as Mark All."""
    actions = actions_for(
        "mypodcastshow",
        is_folder=True,
        folder_state=FolderState(
            is_podcast_show=True, subscribed=True, library_episodes=12, downloaded_files=0
        ),
    )
    ids = _ids(actions)
    assert row_actions.DOWNLOAD_ALL_EPISODES in ids
    assert "12" in _label(actions, row_actions.DOWNLOAD_ALL_EPISODES)
    remove = next(a for a in actions if a.id == row_actions.REMOVE_DOWNLOADS)
    assert remove.enabled is False  # nothing on disk yet: dimmed, present

    with_files = actions_for(
        "mypodcastshow",
        is_folder=True,
        folder_state=FolderState(
            is_podcast_show=True, subscribed=True, library_episodes=12, downloaded_files=3
        ),
    )
    assert next(a for a in with_files if a.id == row_actions.REMOVE_DOWNLOADS).enabled is True


def test_a_subscribed_show_never_carries_two_download_all_rows() -> None:
    """The loaded-rows Download All is suppressed on a show: the library-backed
    Download All Episodes already owns the verb, and two rows would disagree
    about the count."""
    ids = _ids(
        actions_for(
            "mypodcastshow",
            is_folder=True,
            folder_state=FolderState(
                is_podcast_show=True, subscribed=True, library_episodes=5, savable=5
            ),
        )
    )
    assert row_actions.DOWNLOAD_ALL_EPISODES in ids
    assert row_actions.DOWNLOAD_ALL not in ids


def test_searchable_roots_offer_search_this_source_and_others_do_not() -> None:
    podcasts = _ids(
        actions_for("apple", is_folder=True, folder_state=FolderState(root_source=True))
    )
    assert row_actions.SEARCH_SOURCE in podcasts
    # NOAA has no search engine to hand the query to: no lying menu row.
    noaa = _ids(actions_for("wx", is_folder=True, folder_state=FolderState(root_source=True)))
    assert row_actions.SEARCH_SOURCE not in noaa


def test_every_searchable_source_maps_to_a_real_facet() -> None:
    """A facet string that drifts from the search dialog's dropdown opens the
    dialog silently on All sources -- pin the vocabulary."""
    known = {
        "Radio Browser",
        "iHeart",
        "TuneIn",
        "Podcasts",
        "SomaFM",
        "ACB Media",
        "Community M3U",
        "Xiph",
        "YouTube",
    }
    assert set(row_actions.SEARCHABLE_SOURCES.values()) <= known


def test_a_live_station_offers_record_and_schedule_when_the_host_can() -> None:
    ids = _ids(
        actions_for("rbgenre", station=_Row(), can_record=True),
    )
    assert row_actions.RECORD_STATION in ids
    assert row_actions.SCHEDULE_RECORDING in ids
    # A recording has an end: Download is its verb, Record is not.
    episode = _ids(actions_for("appleshow", station=_Row(is_recording=True), can_record=True))
    assert row_actions.RECORD_STATION not in episode


def test_a_saved_row_offers_rename_favorite() -> None:
    saved = _ids(actions_for("soma", station=_Row(), saved=True))
    assert row_actions.RENAME_FAVORITE in saved
    unsaved = _ids(actions_for("soma", station=_Row(), saved=False))
    assert row_actions.RENAME_FAVORITE not in unsaved


def test_a_subscribed_episode_offers_the_played_toggle_one_way_at_a_time() -> None:
    unplayed = _ids(
        actions_for("podepisode", station=_Row(is_recording=True), episode_played=False)
    )
    assert row_actions.MARK_EPISODE_PLAYED in unplayed
    assert row_actions.MARK_EPISODE_UNPLAYED not in unplayed
    played = _ids(actions_for("podepisode", station=_Row(is_recording=True), episode_played=True))
    assert row_actions.MARK_EPISODE_UNPLAYED in played
    assert row_actions.MARK_EPISODE_PLAYED not in played
    # Not a subscribed episode: no mark item in either direction.
    plain = _ids(actions_for("archiveitem", station=_Row(is_recording=True)))
    assert row_actions.MARK_EPISODE_PLAYED not in plain
    assert row_actions.MARK_EPISODE_UNPLAYED not in plain


def test_a_streaming_row_toggles_one_transport_verb() -> None:
    # A live station has two states, so Stop replaces Play rather than joining
    # it: two transport items where one applies is two items to read past.
    playing = row_actions.transport_actions(playing=True, downloaded=False)
    stopped = row_actions.transport_actions(playing=False, downloaded=False)

    assert [a.id for a in playing] == [row_actions.STOP]
    assert [a.id for a in stopped] == [row_actions.PLAY]


def test_a_downloaded_row_offers_play_pause_and_stop() -> None:
    # A saved file has a middle you can stand still in, so pausing to answer
    # the door is not the same verb as abandoning the episode.
    playing = row_actions.transport_actions(playing=True, downloaded=True)
    stopped = row_actions.transport_actions(playing=False, downloaded=True)

    assert [a.id for a in playing] == [row_actions.PAUSE, row_actions.STOP]
    assert [a.id for a in stopped] == [row_actions.PLAY, row_actions.STOP]


def test_download_becomes_remove_download_once_the_file_is_here() -> None:
    saved = row_actions.station_actions(
        playing=False,
        saved=False,
        has_homepage=False,
        can_download=True,
        can_report=False,
        is_recording=True,
        downloaded=True,
    )
    unsaved = row_actions.station_actions(
        playing=False,
        saved=False,
        has_homepage=False,
        can_download=True,
        can_report=False,
        is_recording=True,
        downloaded=False,
    )

    assert row_actions.REMOVE_DOWNLOAD in [a.id for a in saved]
    assert row_actions.DOWNLOAD not in [a.id for a in saved]
    assert row_actions.DOWNLOAD in [a.id for a in unsaved]
    assert row_actions.REMOVE_DOWNLOAD not in [a.id for a in unsaved]


def test_a_downloaded_row_keeps_one_accelerator_per_key() -> None:
    # The fullest downloaded-episode menu there is. A popup with two items
    # answering the same key means one of them silently never fires.
    actions = row_actions.station_actions(
        playing=True,
        saved=True,
        has_homepage=True,
        can_download=True,
        can_report=True,
        is_recording=True,
        episode_played=False,
        downloaded=True,
    )

    keys = [
        label.split("&", 1)[1][0].lower() for label in (a.label for a in actions) if "&" in label
    ]
    assert len(keys) == len(set(keys)), sorted(keys)
