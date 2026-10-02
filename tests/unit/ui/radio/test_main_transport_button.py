"""Quill Radio's main-window transport button says what it will do, and to what.

The report (2026-10-01): "The stop button now always shows up in the app and
doesn't change to a play button when stopped. Should that happen or should it
change to play?" It should. These pin the handoff contract (qc.md, "Radio and
Cast Transport State"): stopped offers Play for the selected favorite, active
offers Stop for what is playing, paused offers Resume; and the one dead state
is enabled and explains itself rather than sitting there as a dead Stop.

Driven with a fake host and a fake wx, so every state can be reached without a
stream.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.ui.radio import main_transport_button as mtb
from quill.ui.radio.playback_state import RadioPlayerState


class _Button:
    def __init__(self, parent: Any = None, label: str = "") -> None:
        self.label = label
        self.labels: list[str] = []
        self.help = ""
        self.bound: list[Any] = []
        self.min_size: tuple[int, int] | None = None

    def GetLabel(self) -> str:  # noqa: N802 - wx API shape
        return self.label

    def SetLabel(self, label: str) -> None:  # noqa: N802
        self.label = label
        self.labels.append(label)

    def SetHelpText(self, text: str) -> None:  # noqa: N802
        self.help = text

    def Bind(self, event: Any, handler: Any) -> None:  # noqa: N802
        self.bound.append((event, handler))

    def GetTextExtent(self, text: str) -> tuple[int, int]:  # noqa: N802
        return (7 * len(text), 16)

    def SetMinSize(self, size: tuple[int, int]) -> None:  # noqa: N802
        self.min_size = size


class _Tree:
    def __init__(self) -> None:
        self.bound: list[Any] = []

    def Bind(self, event: Any, handler: Any) -> None:  # noqa: N802
        self.bound.append((event, handler))


class _Row:
    def __init__(self) -> None:
        self.added: list[Any] = []

    def Add(self, item: Any, *args: Any) -> None:  # noqa: N802
        self.added.append(item)


_WX = SimpleNamespace(
    Button=_Button,
    EVT_BUTTON="EVT_BUTTON",
    EVT_TREE_SEL_CHANGED="EVT_TREE_SEL_CHANGED",
    ALIGN_CENTER_VERTICAL=1,
    RIGHT=2,
)


def _favorite(name: str, uuid: str = "") -> SimpleNamespace:
    station = SimpleNamespace(
        station_uuid=uuid or name.lower(), stream_url=f"http://{name.lower()}", display_name=name
    )
    return SimpleNamespace(display_label=name, station=station, key=station.station_uuid)


def _host(
    *,
    state: RadioPlayerState = RadioPlayerState.STOPPED,
    playing: SimpleNamespace | None = None,
    selected: SimpleNamespace | None = None,
    favorites: list[SimpleNamespace] | None = None,
) -> SimpleNamespace:
    known = {f.key: f for f in (favorites or [])}
    host = SimpleNamespace(
        _radio_controller=SimpleNamespace(
            state=SimpleNamespace(state=state, station=playing.station if playing else None)
        ),
        _radio_favorites=SimpleNamespace(find=lambda key: known.get(key)),
        _selected_favorite=lambda: selected,
        _favorites_tree=_Tree(),
        calls=[],
        spoken=[],
    )
    host.radio_stop = lambda: host.calls.append("stop")
    host.radio_toggle_play_pause = lambda: host.calls.append("toggle")
    host._play_selected_favorite = lambda: host.calls.append("play_selected")
    host._announce = host.spoken.append
    return host


# -- what it says -------------------------------------------------------------- #


def test_stopped_with_a_station_selected_offers_to_play_it_by_name() -> None:
    face = mtb.current_face(_host(selected=_favorite("KSPN")))
    assert face.label == "P&lay KSPN"
    assert face.verb == "play"


def test_stopped_with_a_folder_or_nothing_selected_is_not_a_dead_stop() -> None:
    """This was the report: a Stop button with nothing to stop."""
    face = mtb.current_face(_host())
    assert face.label == "P&lay -- nothing selected"
    assert face.enabled
    assert "Favorites" in face.spoken and "Ctrl+B" in face.spoken


def test_active_offers_to_stop_what_is_playing_by_its_favorite_name() -> None:
    """The listener's own name for the station, when they gave it one."""
    renamed = _favorite("ACB Radio Mainstream")
    renamed.display_label = "Mainstream"
    for state in (
        RadioPlayerState.CONNECTING,
        RadioPlayerState.BUFFERING,
        RadioPlayerState.PLAYING,
        RadioPlayerState.RECONNECTING,
    ):
        host = _host(state=state, playing=renamed, favorites=[renamed], selected=_favorite("Other"))
        face = mtb.current_face(host)
        assert face.label == "S&top Mainstream", state
        assert face.verb == "stop"


def test_a_station_that_is_not_a_favorite_is_named_by_its_own_name() -> None:
    host = _host(state=RadioPlayerState.PLAYING, playing=_favorite("KSPN"))
    assert mtb.current_face(host).label == "S&top KSPN"


def test_paused_offers_resume_by_name() -> None:
    host = _host(state=RadioPlayerState.PAUSED, playing=_favorite("A Podcast"))
    face = mtb.current_face(host)
    assert face.label == "Res&ume A Podcast"
    assert face.verb == "resume"


def test_an_unreadable_player_reads_as_stopped_rather_than_raising() -> None:
    host = _host(selected=_favorite("KSPN"))
    host._radio_controller = None
    assert mtb.current_face(host).label == "P&lay KSPN"


# -- what it does -------------------------------------------------------------- #


def test_pressing_it_runs_the_verb_it_shows() -> None:
    playing = _favorite("KSPN")
    cases = [
        (_host(state=RadioPlayerState.PLAYING, playing=playing), "stop"),
        (_host(state=RadioPlayerState.PAUSED, playing=playing), "toggle"),
        (_host(selected=_favorite("KSPN")), "play_selected"),
    ]
    for host, expected in cases:
        mtb.press(host)
        assert host.calls == [expected]


def test_pressing_the_dead_state_explains_itself_instead_of_doing_nothing() -> None:
    host = _host()
    mtb.press(host)
    assert host.calls == []
    assert host.spoken == [
        "Play. Nothing is selected that can be played -- choose a station in Favorites "
        "first, or press Ctrl+B to browse for one"
    ]


# -- how it is built and kept current ------------------------------------------ #


def test_the_button_is_built_first_in_the_row_with_inline_help_and_follows_the_tree() -> None:
    host = _host(selected=_favorite("KSPN"))
    row = _Row()
    button = mtb.add_transport_button(host, None, row, _WX)
    assert row.added == [button]
    assert host._transport_btn is button
    assert button.label == "P&lay KSPN"
    assert "Ctrl+Period" in button.help
    # Wide enough for its longest label, so Volume and Mute never move.
    assert button.min_size is not None and button.min_size[0] > 7 * 40
    # Selection changes re-read the label.
    assert [event for event, _ in host._favorites_tree.bound] == ["EVT_TREE_SEL_CHANGED"]
    host._selected_favorite = lambda: None
    event = SimpleNamespace(Skip=lambda: None)
    host._favorites_tree.bound[0][1](event)
    assert button.label == "P&lay -- nothing selected"


def test_refresh_does_not_rewrite_an_unchanged_label() -> None:
    host = _host(selected=_favorite("KSPN"))
    mtb.add_transport_button(host, None, _Row(), _WX)
    mtb.refresh(host)
    mtb.refresh(host)
    assert host._transport_btn.labels == []


def test_refresh_before_build_is_a_no_op() -> None:
    mtb.refresh(_host())  # must not raise
