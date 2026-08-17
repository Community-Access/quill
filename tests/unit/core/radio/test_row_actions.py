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


def test_an_already_followed_show_says_so_rather_than_offering_again() -> None:
    actions = actions_for("appleshow", is_folder=True, folder_state=FolderState(subscribed=True))
    assert "Already" in _label(actions, row_actions.SUBSCRIBE_PODCAST)


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
