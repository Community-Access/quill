"""YouTube rows: Follow / Subscribe on YouTube / the bell / Read Comments, and the
branches they open (found channels, live tabs, My YouTube) -- no network."""

from __future__ import annotations

import re

import pytest

from quill.core.radio import browse_youtube_more as more
from quill.core.radio import row_actions
from quill.core.radio import row_actions_youtube as yt
from quill.core.radio.browse_nodes import split_id
from quill.core.radio.models import RadioStation
from quill.core.radio.row_state import FolderState


def _ids(actions) -> list[str]:
    return [a.id for a in actions]


def _keys(actions) -> list[str]:
    return [m.group(1).lower() for a in actions if (m := re.search(r"&(.)", a.label))]


def test_a_found_channel_offers_follow_and_subscribe_not_stop() -> None:
    ids = _ids(row_actions.actions_for("ytchannel", is_folder=True, folder_state=FolderState()))
    assert yt.FOLLOW_CHANNEL in ids and yt.SUBSCRIBE_ON_YOUTUBE in ids
    assert row_actions.UNFOLLOW_CHANNEL not in ids and yt.NOTIFY_CHANNEL not in ids


def test_a_found_channel_already_followed_offers_stop_and_the_bell() -> None:
    state = FolderState(is_followed_channel=True)
    ids = _ids(row_actions.actions_for("ytchannel", is_folder=True, folder_state=state))
    assert row_actions.UNFOLLOW_CHANNEL in ids and yt.NOTIFY_CHANNEL in ids
    assert yt.FOLLOW_CHANNEL not in ids


def test_a_followed_channel_rings_or_stops_ringing() -> None:
    quiet = row_actions.actions_for("youtubechannel", is_folder=True, folder_state=FolderState())
    ringing = row_actions.actions_for(
        "youtubechannel", is_folder=True, folder_state=FolderState(channel_notify=True)
    )
    assert yt.NOTIFY_CHANNEL in _ids(quiet)
    assert yt.STOP_NOTIFY_CHANNEL in _ids(ringing)
    labels = [a.label.replace("&", "") for a in quiet + ringing]
    assert "Notify Me About New Videos" in labels
    assert "Stop Notifying About New Videos" in labels
    assert "Subscribe on YouTube..." in labels


@pytest.mark.parametrize("kind", ["ytchannel", "youtubechannel"])
@pytest.mark.parametrize(
    "state",
    [
        FolderState(),
        FolderState(is_followed_channel=True, channel_notify=True, loaded_stations=3, savable=2),
        FolderState(expanded=True, loaded_stations=3),
    ],
)
def test_no_channel_menu_claims_a_letter_twice(kind, state) -> None:
    keys = _keys(row_actions.actions_for(kind, is_folder=True, folder_state=state))
    assert len(keys) == len(set(keys)), keys


def test_a_youtube_video_row_offers_read_comments_without_a_letter_clash() -> None:
    station = RadioStation(
        name="Bristol",
        stream_url="https://www.youtube.com/watch?v=abcdefghijk",
        homepage="https://www.youtube.com/watch?v=abcdefghijk",
        source="YouTube",
        is_recording=True,
    )
    actions = row_actions.actions_for("station", station=station, can_download=True)
    assert yt.READ_COMMENTS in _ids(actions)
    keys = _keys(actions)
    assert len(keys) == len(set(keys)), keys


def test_a_radio_station_offers_no_comments() -> None:
    station = RadioStation(name="KEXP", stream_url="https://kexp.example/stream")
    assert yt.READ_COMMENTS not in _ids(row_actions.actions_for("station", station=station))


def test_subscribe_opens_youtubes_own_confirm_page() -> None:
    assert (
        yt.subscribe_url("https://www.youtube.com/channel/UCabc", "https://www.youtube.com/@Rick")
        == "https://www.youtube.com/@Rick?sub_confirmation=1"
    )
    assert (
        yt.subscribe_url("https://www.youtube.com/channel/UCabc")
        == "https://www.youtube.com/channel/UCabc?sub_confirmation=1"
    )
    assert yt.subscribe_url("not a channel") == ""


# --- the branches -------------------------------------------------------------


@pytest.fixture
def recorded(monkeypatch):
    answers: dict[str, dict] = {}
    asked: list[tuple[str, dict]] = []

    def fetch(target, options):
        asked.append((target, dict(options)))
        return answers.get(target, {"entries": []})

    monkeypatch.setattr(more, "FETCH", fetch)
    return answers, asked


@pytest.fixture
def signed_in(quill_data_dir):
    from quill.core.radio import youtube_signin

    youtube_signin.save(youtube_signin.SignInSettings(enabled=True, source="firefox"))
    return quill_data_dir


def test_a_found_channel_opens_uploads_live_and_playlists(monkeypatch) -> None:
    from quill.core.radio import youtube_channels

    monkeypatch.setattr(
        youtube_channels,
        "playlists",
        lambda url, safe_mode=False: [("Walks", "https://www.youtube.com/playlist?list=PL1")],
    )
    nodes = more.browse_channel(["https://www.youtube.com/channel/UCabc", ""], safe_mode=False)
    # Shorts follows Live (browse_youtube_extra); then the playlists.
    assert [n.label for n in nodes] == ["Uploads", "Live", "Shorts", "Walks"]
    assert split_id(nodes[1].node_id)[0] == "ytstreams"


def test_the_live_tab_puts_live_now_first(recorded) -> None:
    answers, _asked = recorded
    answers["https://www.youtube.com/@Rick/streams"] = {
        "entries": [
            {"id": "aaaaaaaaaaa", "url": "https://www.youtube.com/watch?v=aaaaaaaaaaa",
             "title": "Last week", "duration": 3600},
            {"id": "bbbbbbbbbbb", "url": "https://www.youtube.com/watch?v=bbbbbbbbbbb",
             "title": "On now", "live_status": "is_live"},
        ]
    }  # fmt: skip
    nodes = more.browse_streams(["https://www.youtube.com/@Rick", "1"], safe_mode=False)
    assert [n.label for n in nodes] == ["On now", "Last week"]


def test_a_channel_that_never_streamed_is_an_empty_folder(monkeypatch) -> None:
    def fetch(target, options):
        raise RuntimeError("This channel does not have a streams tab -- unavailable")

    monkeypatch.setattr(more, "FETCH", fetch)
    assert more.browse_streams(["https://www.youtube.com/@Rick"], safe_mode=False) == []


def test_my_youtube_is_absent_while_sign_in_is_off(quill_data_dir, recorded) -> None:
    from quill.core.radio import browse_yours

    assert more.browse_my_youtube([], safe_mode=False) == []
    labels = [n.label for n in browse_yours.browse_youtube([], safe_mode=False)]
    assert "My YouTube" not in labels and labels[0] == "Search YouTube..."


def test_my_youtube_appears_with_its_rows_when_sign_in_is_on(signed_in, recorded) -> None:
    from quill.core.radio import browse_yours

    labels = [n.label for n in browse_yours.browse_youtube([], safe_mode=False)]
    assert labels[:2] == ["Search YouTube...", "My YouTube"]
    rows = [n.label for n in more.browse_my_youtube([], safe_mode=False)]
    assert rows == [
        "Home",
        "Subscriptions",
        "Watch Later",
        "Liked Videos",
        "Your Playlists",
        "History",  # browse_youtube_extra
    ]
    assert more.browse_my_youtube([], safe_mode=True) == []


@pytest.mark.parametrize(
    ("key", "target"),
    [("home", ":ytrec"), ("subs", ":ytsubs"), ("watchlater", ":ytwatchlater"), ("liked", ":ytfav")],
)
def test_each_feed_asks_yt_dlp_with_its_own_keyword(signed_in, recorded, key, target) -> None:
    answers, asked = recorded
    answers[target] = {
        "entries": [
            {"id": f"v{i:010d}", "url": f"https://www.youtube.com/watch?v=v{i:010d}",
             "title": f"Video {i}"}
            for i in range(more.PAGE_SIZE + 1)
        ]
    }  # fmt: skip
    nodes = more.browse_feed([key, "1"], safe_mode=False)
    assert asked[0][0] == target
    assert asked[0][1]["playlistend"] == more.PAGE_SIZE + 1
    assert len(nodes) == more.PAGE_SIZE + 1 and nodes[-1].label == "More..."


def test_your_channels_and_playlists_become_openable_rows(signed_in, recorded) -> None:
    answers, _asked = recorded
    answers[more.CHANNELS_PAGE] = {
        "entries": [
            {"url": "https://www.youtube.com/channel/UCa", "title": "A channel",
             "channel_id": "UCa"}
        ]
    }  # fmt: skip
    answers[more.PLAYLISTS_PAGE] = {
        "entries": [{"url": "https://www.youtube.com/playlist?list=PLz", "title": "Mine"}]
    }
    (channel,) = more.browse_my_channels([], safe_mode=False)
    (playlist,) = more.browse_my_playlists([], safe_mode=False)
    assert split_id(channel.node_id)[0] == "ytchannel"
    assert split_id(playlist.node_id)[0] == "youtubevideos"


def test_every_new_kind_is_registered_with_the_browse_tree() -> None:
    from quill.core.radio import browse_sources

    for kind in more.HANDLERS:
        assert browse_sources.is_expandable(f"{kind}:x"), kind
