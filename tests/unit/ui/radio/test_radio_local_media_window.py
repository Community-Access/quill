"""The Local Media window: its empty state, its keys, its menus, its rows.

Built with real wx (never shown), the same way the menu accelerator gate builds
Quill Radio's own frame: what is checked is the thing a listener meets -- the
control the cursor lands on, the keys the menus advertise, the words in a row.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

wx = pytest.importorskip("wx")

from quill.core.radio import transport_commands  # noqa: E402
from quill.core.radio.local_media import LocalMediaLibrary  # noqa: E402
from quill.ui.radio import local_media_playback as playback  # noqa: E402
from quill.ui.radio import local_media_window_menu as menus  # noqa: E402
from quill.ui.radio.local_media_window import LocalMediaWindow  # noqa: E402
from quill.ui.radio.playback_state import RadioPlayerState  # noqa: E402


class _Player:
    def __init__(self) -> None:
        self._state = SimpleNamespace(state=RadioPlayerState.STOPPED, station=None)

    @property
    def state(self) -> SimpleNamespace:
        return self._state

    def play_station(self, station: object) -> None:
        self._state = SimpleNamespace(state=RadioPlayerState.PLAYING, station=station)

    def caption_track(self) -> None:  # a Radio player, for the media keys
        return None


class _Host:
    def __init__(self, library: LocalMediaLibrary) -> None:
        self._radio_controller = _Player()
        self._radio_history = SimpleNamespace()
        self._local_media_library = library
        self._task_manager = None
        self.frame = None
        self.said: list[str] = []

    def _announce(self, text: str, *_args: object, **_kwargs: object) -> None:
        self.said.append(text)


@pytest.fixture
def app(quill_data_dir):
    application = wx.App()
    yield application
    for window in wx.GetTopLevelWindows():
        window.Destroy()
    del application


def _library(tmp_path: Path, count: int = 3) -> LocalMediaLibrary:
    library = LocalMediaLibrary()
    playlist = library.add_playlist("Road Trip")
    for index in range(1, count + 1):
        path = tmp_path / f"song{index}.mp3"
        path.write_bytes(b"x")
        playlist.items.append(playlist.make_item(path, title=f"Song {index}", artist="Band"))
    return library


def _window(host: _Host, *, modeless: bool = False) -> LocalMediaWindow:
    windows = None
    if modeless:
        from quill.ui.window_menu import WindowManager

        windows = WindowManager(wx)
    return LocalMediaWindow(None, host=host, windows=windows)


def test_the_empty_state_leads_to_add_media_files(app, tmp_path: Path, monkeypatch) -> None:
    host = _Host(LocalMediaLibrary())
    window = _window(host)
    assert window.is_empty()
    assert not window._playlists.IsShown() and not window._items.IsShown()
    focused: list[object] = []
    monkeypatch.setattr(window._add_files_btn, "SetFocus", lambda: focused.append("add"))
    window.focus_default_control()
    assert focused == ["add"]
    labels = [window._add_files_btn.GetLabel(), window._add_folder_btn.GetLabel()]
    assert labels == ["Add &Media Files...", "Add a &Folder..."]
    window._win.Destroy()


def test_rows_say_title_then_state_and_marking_never_moves_focus(app, tmp_path: Path) -> None:
    host = _Host(_library(tmp_path))
    playback.remember_app(host)
    window = _window(host)
    assert window._items.GetItemCount() == 3
    assert window._items.GetItemText(0) == "Song 1"
    window._select_rows([0])
    playlist = host._local_media_library.playlists[0]
    playback.play_item(host, playlist.id, playlist.items[2].id)
    window._tick()
    assert window._items.GetItemText(2) == "Song 3, playing"
    assert window._rows() == [0], "the cursor stays where the listener left it"
    assert window._items.GetFocusedItem() == 0
    Path(playlist.items[1].path).unlink()
    window.reload()
    assert window._items.GetItemText(1) == "Song 2, missing"
    window._win.Destroy()


def test_a_move_from_the_keyboard_says_where_it_went(app, tmp_path: Path) -> None:
    host = _Host(_library(tmp_path))
    window = _window(host)
    window._select_rows([2])
    window._items.Focus(2)
    window.run("move_top")
    assert host.said[-1] == "Moved to 1 of 3."
    assert window._rows() == [0]
    assert window._items.GetItemText(0) == "Song 3"
    window._win.Destroy()


def test_every_menu_item_shows_a_key_and_no_key_is_claimed_twice(app, tmp_path: Path) -> None:
    host = _Host(_library(tmp_path))
    window = _window(host, modeless=True)
    bar = window._win.GetMenuBar()
    claimed: dict[str, str] = {}
    for index in range(bar.GetMenuCount()):
        letters = []
        for item in bar.GetMenu(index).GetMenuItems():
            if item.IsSeparator():
                continue
            label = item.GetItemLabel()
            assert "\t" in label, f"{label} has no keyboard route"
            assert "&" in label, f"{label} has no access key"
            letters.append(label[label.index("&") + 1].lower())
            key = menus.canonical(label.split("\t", 1)[1])
            assert key not in claimed, f"{key} claimed by {claimed.get(key)} and {label}"
            claimed[key] = label
        assert len(letters) == len(set(letters)), bar.GetMenuLabel(index)
    entry = wx.AcceleratorEntry()
    for key in claimed:
        assert entry.FromString("\t" + key), f"wx cannot bind {key}"
    window._win.Destroy()


def test_the_window_keys_never_shadow_the_transport_or_the_media_keys() -> None:
    from quill.ui.radio.media_keys import MEDIA_KEYS
    from quill.ui.radio.surface_app_menu import COMMANDS as STATION

    ours = set(menus.key_table(modeless=True))
    theirs = {menus.canonical(command.key) for command in transport_commands.COMMANDS}
    theirs |= {menus.canonical(key) for key, _verb in MEDIA_KEYS}
    theirs |= {menus.canonical(key) for _l, _c, key, method in STATION if key}
    theirs -= {menus.canonical("Ctrl+O")}  # the window opens on its own key
    assert ours & theirs == set()
    assert {menus.canonical(f"Ctrl+{n}") for n in range(1, 10)} & ours == set()


def test_control_access_keys_do_not_meet_the_menu_bar(app, tmp_path: Path) -> None:
    host = _Host(_library(tmp_path))
    window = _window(host, modeless=True)
    bar = window._win.GetMenuBar()
    menu_letters = set()
    for index in range(bar.GetMenuCount()):
        title = bar.GetMenuLabel(index)
        menu_letters.add(title[title.index("&") + 1].lower())
    controls = [
        window._playlists_label.GetLabel(),
        window._items_label.GetLabel(),
        window._add_files_btn.GetLabel(),
        window._add_folder_btn.GetLabel(),
        window._new_btn.GetLabel(),
    ]
    letters = [text[text.index("&") + 1].lower() for text in controls]
    assert len(letters) == len(set(letters))
    assert set(letters) & menu_letters == set()
    window._win.Destroy()


def test_every_control_answers_f1(app, tmp_path: Path) -> None:
    from quill.ui.app_context_help import ensure_help_provider

    ensure_help_provider(wx)  # SetHelpText stores nothing without one
    host = _Host(_library(tmp_path))
    window = _window(host)
    for control in (
        window._playlists,
        window._items,
        window._add_files_btn,
        window._add_folder_btn,
        window._new_btn,
    ):
        assert control.GetHelpText(), control
    window._win.Destroy()


def test_the_item_menu_offers_paste_only_when_something_is_held(app, tmp_path: Path) -> None:
    from quill.ui.radio import local_media_edit_ui as edit_ui

    host = _Host(_library(tmp_path))
    window = _window(host)
    playlist = host._local_media_library.playlists[0]
    assert edit_ui.clip(host) is None
    edit_ui.cut_items(host, playlist, [1])
    assert edit_ui.clip(host) is not None
    letters = [label[label.index("&") + 1].lower() for _verb, label in menus.ITEM_POPUP if label]
    assert len(letters) == len(set(letters)), "the item menu's access keys are unique"
    window._win.Destroy()
