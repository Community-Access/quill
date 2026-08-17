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
