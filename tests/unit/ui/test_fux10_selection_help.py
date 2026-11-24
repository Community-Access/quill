"""FUX-10: F1 on a list also says what its selected row is, right now.

The engine half (``set_selection_help`` and the paragraph ``topics_for``
composes), then the first two adopters: QUILL Cast's episode list (what is
greyed for the selected episode or podcast, and why) and Quill Radio's
Favorites tree (what Enter does on this row, a station marked for move, your
note). Fakes throughout: ``topics_for`` takes its ``wx`` as an argument, and
the describers read only the host's own names.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.core import control_help, dimmed_reason
from quill.core.radio import favorite_row_help
from quill.ui import app_context_help

# -- the engine -----------------------------------------------------------------


class _Frame:
    def __init__(self, title: str) -> None:
        self._title = title

    def GetTitle(self) -> str:  # noqa: N802 - wx's name
        return self._title

    def GetParent(self) -> None:  # noqa: N802 - wx's name
        return None


class _Dialog:
    pass


class ListCtrl:  # the class name is what picks the role line
    def __init__(self, parent: _Frame, help_text: str) -> None:
        self._parent = parent
        self._help = help_text

    def GetLabel(self) -> str:  # noqa: N802 - wx's name
        return ""

    def GetName(self) -> str:  # noqa: N802 - wx's name
        return "Episodes"

    def GetHelpText(self) -> str:  # noqa: N802 - wx's name
        return self._help

    def GetParent(self) -> _Frame:  # noqa: N802 - wx's name
        return self._parent


def _fake_wx(focused: Any) -> Any:
    return SimpleNamespace(
        Window=SimpleNamespace(FindFocus=lambda: focused),
        Frame=_Frame,
        Dialog=_Dialog,
    )


def test_selection_paragraph_sits_between_the_lists_help_and_its_role_line() -> None:
    body = control_help.compose_control_body(
        accessible_name="",
        help_text="The episodes of the place you chose.",
        usage="A list: Up and Down move between rows.",
        selection="Unavailable for this episode:\nDownload Episode: done.",
    )
    assert body.split("\n\n") == [
        "The episodes of the place you chose.",
        "Unavailable for this episode:\nDownload Episode: done.",
        "A list: Up and Down move between rows.",
    ]


def test_f1_on_a_list_with_a_describer_says_the_selected_rows_situation() -> None:
    frame = _Frame("QUILL Cast")
    episodes = ListCtrl(frame, "The episodes of the place you chose.")
    app_context_help.set_selection_help(episodes, lambda: "This row is special.")
    _surface, control = app_context_help.topics_for(frame, _fake_wx(episodes))
    assert "This row is special." in control.body
    assert control.body.index("The episodes") < control.body.index("This row is special.")


def test_a_list_without_a_describer_answers_as_before() -> None:
    frame = _Frame("QUILL Cast")
    episodes = ListCtrl(frame, "The episodes of the place you chose.")
    _surface, control = app_context_help.topics_for(frame, _fake_wx(episodes))
    assert control.body.split("\n\n")[0] == "The episodes of the place you chose."
    assert app_context_help.selection_help_of(episodes) == ""


def test_a_describer_that_fails_costs_only_its_paragraph() -> None:
    frame = _Frame("QUILL Cast")
    episodes = ListCtrl(frame, "The episodes.")

    def broken() -> str:
        raise RuntimeError("the list is mid-teardown")

    app_context_help.set_selection_help(episodes, broken)
    _surface, control = app_context_help.topics_for(frame, _fake_wx(episodes))
    assert control.body.startswith("The episodes.")


# -- the shared words --------------------------------------------------------------


def test_unavailable_for_names_the_row_and_gives_each_reason_a_line() -> None:
    sentences = [
        dimmed_reason.explain("&Download Episode", dimmed_reason.already_downloaded()),
        "",
    ]
    assert dimmed_reason.unavailable_for("episode", sentences) == (
        "Unavailable for this episode:\nDownload Episode: this episode is already downloaded."
    )
    assert dimmed_reason.unavailable_for("episode", []) == ""


# -- QUILL Cast -------------------------------------------------------------------


def _cast_host(kind: str, *, queued_status: str | None = None) -> Any:
    episode = SimpleNamespace(guid="e1", title="Episode 1")
    show = SimpleNamespace(id="s1", feed_url="", is_local=True)
    queue = {} if queued_status is None else {"e1": SimpleNamespace(status=queued_status)}
    return SimpleNamespace(
        _list_selected_data=lambda: (kind, "e1" if kind == "episode" else "s1"),
        _selected_episode=lambda: (show, episode),
        _download_queue=queue,
        _download_item_id=lambda ep: ep.guid,
        _podcast_library=SimpleNamespace(find_show=lambda _id: show),
    )


def _resolved(label: str, enabled: bool, reason: str = "") -> Any:
    from quill.ui.podcasts.manager_menus import ResolvedAction

    return ResolvedAction(label.lower(), label, enabled, lambda: None, reason)


def test_cast_f1_says_what_is_unavailable_for_the_selected_episode(monkeypatch) -> None:
    from quill.ui.podcasts import context_menus, selection_help

    actions = [
        _resolved("&Play", True),
        _resolved("&Download Episode", False, dimmed_reason.already_downloaded()),
    ]
    monkeypatch.setattr(context_menus, "resolved_episode_actions", lambda _host: actions)
    said = selection_help.describe_selected_row(_cast_host("episode"))
    assert said == (
        "Unavailable for this episode:\nDownload Episode: this episode is already downloaded."
    )


def test_cast_f1_says_nothing_when_nothing_is_dimmed(monkeypatch) -> None:
    from quill.ui.podcasts import context_menus, selection_help

    monkeypatch.setattr(context_menus, "resolved_episode_actions", lambda _host: [])
    assert selection_help.describe_selected_row(_cast_host("episode")) == ""


def test_cast_f1_says_what_is_unavailable_for_a_selected_podcast(monkeypatch) -> None:
    from quill.ui.podcasts import manager_menus, selection_help

    greyed = _resolved("Mark All as &Played", False, dimmed_reason.nothing_unheard(12))
    monkeypatch.setattr(manager_menus, "show_actions", lambda _h, _s: {"mark": greyed})
    monkeypatch.setattr(manager_menus, "ordered_actions", lambda _h, _c, acts: list(acts.values()))
    said = selection_help.describe_selected_row(_cast_host("show"))
    assert said == (
        "Unavailable for this podcast:\nMark All as Played: nothing to mark, all 12 "
        "episodes are already played."
    )


def test_cast_pause_download_says_why_it_is_dimmed(monkeypatch) -> None:
    from quill.ui.podcasts import context_menus, manager_menus

    items: list[Any] = []

    class _Item:
        def __init__(self, label: str) -> None:
            self.label, self.enabled, self.help = label, True, ""
            items.append(self)

        def Enable(self, on: bool) -> None:  # noqa: N802 - wx's name
            self.enabled = on

        def SetHelp(self, text: str) -> None:  # noqa: N802 - wx's name
            self.help = text

    class _Menu:
        def Append(self, _id: int, label: str) -> _Item:  # noqa: N802 - wx's name
            return _Item(label)

        def Bind(self, *_a: Any) -> None:  # noqa: N802 - wx's name
            pass

        def AppendSeparator(self) -> None:  # noqa: N802 - wx's name
            pass

    host = _cast_host("episode")
    host._wx = SimpleNamespace(Menu=_Menu, ID_ANY=-1, EVT_MENU=object())
    host._episodes = SimpleNamespace(GetSelectedItemCount=lambda: 1)
    host._append_transcript_items = lambda *_a: None
    monkeypatch.setattr(context_menus, "_append_selection_items", lambda *_a: None)
    monkeypatch.setattr(context_menus, "resolved_episode_actions", lambda _h: [])
    monkeypatch.setattr(context_menus, "_popup", lambda *_a: None)
    monkeypatch.setattr(manager_menus, "build_menu", lambda *_a: None)
    context_menus.episode_row_menu(host)
    pause = next(item for item in items if item.label.startswith("Pause"))
    assert not pause.enabled
    assert pause.help == "Pause Download: nothing is downloading for this episode."


# -- Quill Radio --------------------------------------------------------------------


def test_radio_says_what_enter_does_on_the_station_the_player_holds() -> None:
    words = favorite_row_help
    assert words.station_situation(held=words.RUNNING) == (
        "This station is playing. Enter or Space pauses it."
    )
    assert words.station_situation(held=words.PAUSED) == (
        "This station is paused. Enter or Space resumes it."
    )
    assert words.station_situation(held=words.HELD) == "Enter or Space starts this station again."


def test_radio_a_plain_station_needs_nothing_beyond_the_trees_help() -> None:
    assert favorite_row_help.station_situation() == ""


def test_radio_words_for_a_folder() -> None:
    assert favorite_row_help.folder_situation(1) == (
        "This folder holds 1 station, counting its subfolders. Enter does not play a "
        "folder: Right Arrow opens it and Left Arrow closes it."
    )


def _radio_host(selected: tuple[str, str], *, state: Any = None, marked: str = "") -> Any:
    from quill.apps.radio_favorites_tree import RadioFavoritesTreeMixin

    stations = {
        "bbc": SimpleNamespace(
            key="bbc", folder="News", display_label="BBC World Service", station="bbc-station"
        ),
        "npr": SimpleNamespace(
            key="npr", folder="News/Morning", display_label="NPR", station="npr-st"
        ),
    }
    favorites = SimpleNamespace(favorites=list(stations.values()), find=stations.get)
    host = SimpleNamespace(
        _radio_favorites=favorites,
        _radio_controller=SimpleNamespace(state=SimpleNamespace(state=state)),
        _marked_favorite_key=marked or None,
        _selected_tree_data=lambda: selected,
        _favorite_is_playing=lambda fav: fav.key == "bbc",
    )
    host._selected_favorite = lambda: RadioFavoritesTreeMixin._selected_favorite(host)
    return lambda: RadioFavoritesTreeMixin._favorites_row_help(host)


def test_radio_f1_on_the_playing_station_says_enter_pauses(monkeypatch) -> None:
    from quill.ui.radio import favorites_details
    from quill.ui.radio.playback_state import RadioPlayerState

    monkeypatch.setattr(favorites_details, "_note_for", lambda _station: "Best at 6 am.")
    said = _radio_host(("station", "bbc"), state=RadioPlayerState.PLAYING)()
    assert said == "This station is playing. Enter or Space pauses it.\nYour note: Best at 6 am."


def test_radio_f1_on_a_station_stopped_in_the_player_says_enter_restarts(monkeypatch) -> None:
    from quill.ui.radio import favorites_details
    from quill.ui.radio.playback_state import RadioPlayerState

    monkeypatch.setattr(favorites_details, "_note_for", lambda _station: "")
    said = _radio_host(("station", "bbc"), state=RadioPlayerState.CONNECTING)()
    assert said == "Enter or Space starts this station again."


def test_radio_f1_names_the_station_marked_for_move(monkeypatch) -> None:
    from quill.ui.radio import favorites_details

    monkeypatch.setattr(favorites_details, "_note_for", lambda _station: "")
    said = _radio_host(("station", "npr"), marked="bbc")()
    assert said.startswith("BBC World Service is marked for move.")


def test_radio_f1_on_a_folder_counts_its_stations() -> None:
    said = _radio_host(("folder", "News"))()
    assert said.startswith("This folder holds 2 stations, counting its subfolders.")
