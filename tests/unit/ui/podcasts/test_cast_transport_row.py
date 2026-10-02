"""Cast's button row names its objects in its labels (qc.md 4.5).

Driven with a fake host and fake buttons, the way the status bar tests drive
the bar: the refresh methods are plain functions of the frame's attributes,
so the row can be exercised without a window. What is pinned is the contract
from the Screen-Reader Testing Handoff: stopped offers Play for the selected
thing, playing offers Pause for the playing thing, paused offers Resume, and
the separate Stop is unavailable when nothing is playing -- never an enabled
dead action.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.apps.podcasts import PodcastsAppFrame
from quill.ui.podcasts.places import CastPlacesMixin
from quill.ui.podcasts.player_controller import PodcastPlayerState


class _Button:
    def __init__(self, label: str = "") -> None:
        self.label = label
        self.enabled = True
        self.labels: list[str] = []

    def GetLabel(self) -> str:  # noqa: N802 - wx API shape
        return self.label

    def SetLabel(self, label: str) -> None:  # noqa: N802
        self.label = label
        self.labels.append(label)

    def Enable(self, on: bool) -> None:  # noqa: N802
        self.enabled = bool(on)


class _Show:
    def __init__(self, title: str, episodes: list[Any] | None = None) -> None:
        self.show_id = title.lower()
        self.title = title
        self.episodes = list(episodes or [])
        self.is_favorite = False

    def find_episode(self, guid: str) -> Any:
        return next((e for e in self.episodes if e.guid == guid), None)


class _Library:
    def __init__(self, shows: list[_Show]) -> None:
        self.shows = shows

    def find_show(self, show_id: str) -> _Show | None:
        return next((s for s in self.shows if s.show_id == show_id), None)

    def find_folder(self, folder_id: str) -> Any:
        return SimpleNamespace(folder_id=folder_id, name=folder_id.title())


def _host(
    *,
    state: PodcastPlayerState = PodcastPlayerState.STOPPED,
    playing: tuple[str, str] | None = None,
    selected: tuple[str, str] | None = None,
) -> SimpleNamespace:
    episode = SimpleNamespace(guid="e4", title="Episode 4", played=False)
    daily = _Show("The Daily", [episode])
    library = _Library([daily, _Show("Empty Show")])
    show_id, guid = playing or (None, None)
    host = SimpleNamespace(
        _podcast_controller=SimpleNamespace(
            state=SimpleNamespace(state=state, show_id=show_id, episode_guid=guid)
        ),
        _podcast_library=library,
        _play_pause_btn=_Button("Pla&y -- nothing selected"),
        _stop_btn=_Button("S&top"),
        _unfollow_btn=_Button("&Unfollow"),
        _favorite_toggle_btn=_Button("Add to &Favorites"),
        _cast_status_bar=None,
        spoken=[],
        _selected_tree_data=lambda: selected,
    )
    host._announce = host.spoken.append
    # The two mixins' methods, bound to the fake exactly as the frame would have them.
    for name in ("_transport_button_face", "_selected_playable", "_unfollow_target"):
        setattr(host, name, getattr(CastPlacesMixin, name).__get__(host))
    host._selected_show = PodcastsAppFrame._selected_show.__get__(host)
    host._selected_episode = PodcastsAppFrame._selected_episode.__get__(host)
    host._refresh_selection_buttons = CastPlacesMixin._refresh_selection_buttons.__get__(host)
    host._play_selection_or_say_why = CastPlacesMixin._play_selection_or_say_why.__get__(host)
    host._refresh_transport_controls = PodcastsAppFrame._refresh_transport_controls.__get__(host)
    host._refresh_favorite_toggle = PodcastsAppFrame._refresh_favorite_toggle.__get__(host)
    host._refresh_cast_status_bar = lambda: None
    return host


# -- the primary button ------------------------------------------------------- #


def test_stopped_with_a_podcast_selected_offers_to_play_it_by_name() -> None:
    host = _host(selected=("show", "the daily"))
    host._refresh_transport_controls()
    assert host._play_pause_btn.label == "Pla&y The Daily"
    assert host._stop_btn.enabled is False


def test_stopped_with_an_episode_selected_names_the_episode() -> None:
    host = _host(selected=("episode", "the daily\x00e4"))
    host._refresh_transport_controls()
    assert host._play_pause_btn.label.startswith("Pla&y ")
    assert "Episode 4" in host._play_pause_btn.label


def test_a_folder_or_an_empty_show_under_the_cursor_is_not_offered() -> None:
    for selected in (("folder", "news"), ("show", "empty show"), None):
        host = _host(selected=selected)
        host._refresh_transport_controls()
        assert host._play_pause_btn.label == "Pla&y -- nothing selected", selected
        assert host._stop_btn.enabled is False


def test_playing_offers_to_pause_the_playing_episode_whatever_is_selected() -> None:
    host = _host(
        state=PodcastPlayerState.PLAYING,
        playing=("the daily", "e4"),
        selected=("show", "empty show"),
    )
    host._refresh_transport_controls()
    assert host._play_pause_btn.label == "Pau&se The Daily, Episode 4"
    assert host._stop_btn.enabled is True


def test_loading_already_offers_pause_so_an_opening_stream_can_be_held() -> None:
    host = _host(state=PodcastPlayerState.LOADING, playing=("the daily", "e4"))
    host._refresh_transport_controls()
    assert host._play_pause_btn.label.startswith("Pau&se ")


def test_paused_offers_resume_and_stop_stays_available() -> None:
    host = _host(state=PodcastPlayerState.PAUSED, playing=("the daily", "e4"))
    host._refresh_transport_controls()
    assert host._play_pause_btn.label == "Re&sume The Daily, Episode 4"
    assert host._stop_btn.enabled is True


def test_the_label_follows_the_selection_without_a_player_change() -> None:
    """The report: "play what?" went stale every time the cursor moved."""
    host = _host(selected=("show", "the daily"))
    host._refresh_transport_controls()
    host._selected_tree_data = lambda: ("show", "empty show")
    host._refresh_transport_controls()
    assert host._play_pause_btn.labels[-1] == "Pla&y -- nothing selected"


def test_an_unchanged_label_is_not_rewritten() -> None:
    """SetLabel fires a name change through UIA; a reader has no use for being
    told the button was renamed to the same thing."""
    host = _host(selected=("show", "the daily"))
    host._refresh_transport_controls()
    host._refresh_transport_controls()
    assert host._play_pause_btn.labels == ["Pla&y The Daily"]


# -- the dead state explains itself when pressed ------------------------------- #


def test_pressing_play_with_a_folder_selected_says_what_would_work() -> None:
    host = _host(selected=("folder", "news"))
    host._play_selection_or_say_why()
    assert host.spoken == [
        "Play. Nothing is selected that can be played -- choose a podcast or an "
        "episode in the library first, or use Continue Listening"
    ]


# -- Unfollow names its podcast ------------------------------------------------ #


def test_unfollow_names_the_selected_podcast_in_its_label() -> None:
    host = _host(selected=("show", "the daily"))
    host._refresh_selection_buttons()
    assert host._unfollow_btn.label == "&Unfollow The Daily"
    assert host._unfollow_btn.enabled is True


def test_unfollow_with_an_episode_selected_names_that_episodes_podcast() -> None:
    host = _host(selected=("episode", "the daily\x00e4"))
    host._refresh_selection_buttons()
    assert host._unfollow_btn.label == "&Unfollow The Daily"


def test_unfollow_with_nothing_selected_is_bare_and_disabled() -> None:
    host = _host(selected=("folder", "news"))
    host._refresh_selection_buttons()
    assert host._unfollow_btn.label == "&Unfollow"
    assert host._unfollow_btn.enabled is False


# -- the favorites toggle ------------------------------------------------------ #


def test_the_favorites_toggle_carries_its_state_in_the_label() -> None:
    host = _host(state=PodcastPlayerState.PLAYING, playing=("the daily", "e4"))
    host._refresh_favorite_toggle()
    assert host._favorite_toggle_btn.label == "Add to &Favorites"
    assert host._favorite_toggle_btn.enabled is True
    host._podcast_library.find_show("the daily").is_favorite = True
    host._refresh_favorite_toggle()
    assert host._favorite_toggle_btn.label == "Remove from &Favorites"
