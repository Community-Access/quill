"""The Lineups window: its empty state, rows, keys, menus, moves and refreshes.

Built with real wx (never shown), like the Local Media window's tests: what is
checked is what a listener meets -- the words in a row, where the cursor is
after a refresh, the keys the menus advertise, what is said after a move.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.wx_session import shared_wx_app

wx = pytest.importorskip("wx")

from quill.core.lineups import ops  # noqa: E402
from quill.core.lineups.fields import ItemFacts  # noqa: E402
from quill.core.lineups.merge import Catalogue  # noqa: E402
from quill.core.lineups.refs import KIND_EPISODE, KIND_STATION, ItemRef  # noqa: E402
from quill.core.lineups.rules import Keep, Rule  # noqa: E402
from quill.core.lineups.store import LineupStore  # noqa: E402
from quill.core.radio import transport_commands  # noqa: E402
from quill.ui.lineups import menus  # noqa: E402
from quill.ui.lineups.host import LineupsHost  # noqa: E402
from quill.ui.lineups.window import LineupsWindow  # noqa: E402


def station(key: str, *, minutes: int = 0) -> ItemFacts:
    return ItemFacts(
        ref=ItemRef(KIND_STATION, key),
        name=f"Station {key}",
        facts={"folder": "Morning"},
        length_seconds=minutes * 60,
        payload={"name": f"Station {key}", "stream_url": f"http://{key}"},
    )


class _App:
    def __init__(self) -> None:
        self.said: list[str] = []
        self.frame = None
        self._task_manager = None
        self.undo: list[Any] = []

    def _announce(self, text: str, *_a: object, **_k: object) -> None:
        self.said.append(text)


class _Host(LineupsHost):
    app_key = "test"
    app_name = "Test App"

    def __init__(self, app: _App, data_dir: Path, items: tuple[ItemFacts, ...] = ()) -> None:
        super().__init__(app)
        self._dir = data_dir
        self.items = items
        self.played: list[tuple[list[ItemRef], int]] = []
        self.start = ""

    @property
    def data_dir(self) -> Path:  # type: ignore[override]
        return self._dir

    def catalogue(self, now: float) -> Catalogue:
        return Catalogue({KIND_STATION: self.items, KIND_EPISODE: ()}, frozenset({KIND_EPISODE}))

    def watched_files(self):  # nothing to watch in a test
        return ()

    def remember_undo(self, verb, subject, restores, undo) -> bool:
        self.app.undo.append(undo)
        return True

    def offer_undo(self, sentence: str) -> str:
        return sentence

    # Said at once in a test: the delay exists for a screen reader's focus speech.
    def announce_soon(self, text: str) -> None:
        self.announce(text)

    def say_outcome_soon(self, text: str) -> None:
        self.say_outcome(text)

    def play(self, lineup, refs, start, facts) -> str:
        self.played.append((list(refs), start))
        return ""

    def start_lineup_id(self) -> str:
        return self.start

    def set_start_lineup_id(self, lineup_id: str) -> None:
        self.start = lineup_id


@pytest.fixture
def app(quill_data_dir):
    application = shared_wx_app()
    yield application
    for window in wx.GetTopLevelWindows():
        window.Destroy()
    del application


def _filled(tmp_path: Path, keys: str = "abc") -> tuple[_Host, str]:
    host = _Host(_App(), tmp_path, tuple(station(k, minutes=10) for k in keys))
    store = LineupStore(tmp_path)
    _book, created = store.update(ops.create_lineup("Morning"))
    store.update(ops.add_items(created.lineup_id, [station(k) for k in keys]))
    return host, created.lineup_id


def _window(host: _Host, lineup_id: str = "") -> LineupsWindow:
    window = LineupsWindow(host, lineup_id=lineup_id)
    window._catalogue = host.catalogue(0)
    window.reload()
    return window


# -- what a listener meets ----------------------------------------------------------------


def test_the_empty_state_leads_to_new_lineup(app, tmp_path: Path) -> None:
    window = _window(_Host(_App(), tmp_path))
    assert window._new_btn.IsShown() and window._example_btn.IsShown()
    assert not window._lineups.IsShown() and not window._items.IsShown()
    assert window._status_bar.GetStatusText() == "No lineups yet."
    window._win.Destroy()


def test_rows_read_name_kind_length_source_state_and_the_lineup_row_counts(app, tmp_path) -> None:
    host, lineup_id = _filled(tmp_path)
    window = _window(host, lineup_id)
    assert window._lineups.GetString(0) == "Morning, 3 items, 30 minutes"
    assert window._items.GetItemCount() == 3
    assert window._items.GetItemText(0) == "Station a, station, 10 minutes"
    window._win.Destroy()


def test_a_move_says_where_it_went_and_undo_puts_it_back(app, tmp_path: Path) -> None:
    host, lineup_id = _filled(tmp_path)
    window = _window(host, lineup_id)
    window._select_rows([2])
    window.run("move_top")
    assert host.app.said[-1] == "Moved to 1 of 3."
    assert window.selected_refs() == [ItemRef(KIND_STATION, "c")]
    assert [r.key for r in window.visible_refs()] == ["c", "a", "b"]
    host.app.undo[-1]()
    window._book = window._load_book()
    window.reload()
    assert [r.key for r in window.visible_refs()] == ["a", "b", "c"]
    window._select_rows([0])
    window.run("move_up")
    assert host.app.said[-1] == "Already at the top."
    window._win.Destroy()


def test_an_edit_in_the_other_app_never_moves_the_cursor(app, tmp_path: Path) -> None:
    host, lineup_id = _filled(tmp_path)
    window = _window(host, lineup_id)
    window._select_rows([1])  # Station b
    LineupStore(tmp_path).update(ops.add_items(lineup_id, [station("z")], after=None))
    LineupStore(tmp_path).update(
        ops.move_rows(lineup_id, [ItemRef(KIND_STATION, "z")], to_top=True)
    )
    window._tick()  # notices the file changed
    assert window.selected_refs() == [ItemRef(KIND_STATION, "b")]
    assert window._items.GetItemText(0).startswith("Station z")
    window._win.Destroy()


def test_removing_the_selected_row_selects_the_row_that_took_its_place(app, tmp_path) -> None:
    host, lineup_id = _filled(tmp_path)
    window = _window(host, lineup_id)
    window._select_rows([1])
    window.run("remove")
    assert host.app.said[-1] == "Removed. Removed Items can bring it back."
    assert window.selected_refs() == [ItemRef(KIND_STATION, "c")]
    removed = window.current_lineup().removed  # type: ignore[union-attr]
    assert [entry.ref.key for entry in removed] == ["b"]
    host.app.undo[-1]()
    assert [r.ref.key for r in LineupStore(tmp_path).load().lineups[0].rows] == ["a", "b", "c"]
    window._win.Destroy()


def test_keep_toggles_and_says_what_it_means(app, tmp_path: Path) -> None:
    host, lineup_id = _filled(tmp_path)
    window = _window(host, lineup_id)
    window._select_rows([0])
    window.run("keep")
    assert host.app.said[-1] == "Kept. It stays whatever the rules say."
    assert window._items.GetItemText(0).endswith(", kept")
    window.run("keep")
    assert host.app.said[-1] == "No longer kept: its rules decide again."
    window._win.Destroy()


def test_a_refresh_brings_rule_items_in_and_keeps_the_cursor(app, tmp_path: Path) -> None:
    host = _Host(_App(), tmp_path, (station("a"), station("b")))
    rule = Rule(id="r1", kind=KIND_STATION, keep=Keep())
    _book, created = LineupStore(tmp_path).update(ops.create_lineup("Rules", rules=(rule,)))
    window = _window(host, created.lineup_id)
    assert window._items.GetItemCount() == 0
    window.request_refresh(speak=True)  # inline: the test app has no task manager
    assert [r.key for r in window.visible_refs()] == ["a", "b"]
    window._select_rows([1])
    host.items = (station("a"), station("b"), station("c"))
    window.request_refresh(speak=False)
    assert [r.key for r in window.visible_refs()] == ["a", "b", "c"]
    assert window.selected_refs() == [ItemRef(KIND_STATION, "b")]
    window._win.Destroy()


def test_enter_plays_from_the_row_and_play_all_plays_the_whole_lineup(app, tmp_path) -> None:
    host, lineup_id = _filled(tmp_path)
    window = _window(host, lineup_id)
    window._select_rows([1])
    window.run("play")
    assert host.played[-1] == ([r for r in window.visible_refs()], 1)
    window.run("play_all")
    assert host.played[-1][1] == 0
    window._win.Destroy()


def test_start_here_toggles_and_shows_on_the_lineup_row(app, tmp_path: Path) -> None:
    host, lineup_id = _filled(tmp_path)
    window = _window(host, lineup_id)
    window.run("start_here")
    assert host.start == lineup_id
    assert host.app.said[-1] == "Morning opens when Test App starts."
    assert window._lineups.GetString(0).endswith("start lineup")
    window.run("start_here")
    assert host.start == "" and host.app.said[-1] == "Test App opens as usual."
    window._win.Destroy()


# -- keys and menus --------------------------------------------------------------------------


def test_every_menu_item_shows_a_key_and_no_key_is_claimed_twice(app, tmp_path: Path) -> None:
    from quill.ui.window_menu import WindowManager

    host, lineup_id = _filled(tmp_path)
    host.app._windows = WindowManager(wx)
    window = _window(host, lineup_id)
    bar = window._win.GetMenuBar()
    claimed: dict[str, str] = {}
    for index in range(bar.GetMenuCount()):
        letters = []
        for item in bar.GetMenu(index).GetMenuItems():
            if item.IsSeparator() or item.GetSubMenu() is not None:
                continue
            label = item.GetItemLabel()
            if bar.GetMenuLabel(index).replace("&", "") == "Window":
                continue  # the window manager's own menu
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


def test_the_window_keys_never_shadow_radios_transport_media_or_station_keys() -> None:
    from quill.ui.radio.media_keys import MEDIA_KEYS
    from quill.ui.radio.surface_app_menu import COMMANDS as STATION

    ours = set(menus.key_table())
    theirs = {menus.canonical(command.key) for command in transport_commands.COMMANDS}
    theirs |= {menus.canonical(key) for key, _verb in MEDIA_KEYS}
    theirs |= {menus.canonical(key) for _l, _c, key, _m in STATION if key}
    assert ours & theirs == set()
    assert {menus.canonical(f"Ctrl+{n}") for n in range(1, 10)} & ours == set()
    assert menus.canonical("Ctrl+P") not in ours and menus.canonical("Ctrl+E") not in ours


def test_control_access_keys_do_not_meet_the_menu_bar(app, tmp_path: Path) -> None:
    host, lineup_id = _filled(tmp_path)
    window = _window(host, lineup_id)
    bar = window._win.GetMenuBar()
    titles = [bar.GetMenuLabel(index) for index in range(bar.GetMenuCount())]
    menu_letters = {title[title.index("&") + 1].lower() for title in titles if "&" in title}
    controls = [
        window._lineups_label.GetLabel(),
        window._show_label.GetLabel(),
        window._items_label.GetLabel(),
        window._new_btn.GetLabel(),
        window._example_btn.GetLabel(),
    ]
    letters = [text[text.index("&") + 1].lower() for text in controls]
    assert len(letters) == len(set(letters))
    assert set(letters) & menu_letters == set()
    window._win.Destroy()


def test_every_control_answers_f1(app, tmp_path: Path) -> None:
    from quill.ui.app_context_help import ensure_help_provider

    ensure_help_provider(wx)
    host, lineup_id = _filled(tmp_path)
    window = _window(host, lineup_id)
    for control in (
        window._lineups,
        window._show,
        window._items,
        window._new_btn,
        window._example_btn,
    ):
        assert control.GetHelpText(), control
    window._win.Destroy()


def test_the_refresh_timer_stops_with_its_window(app, tmp_path: Path) -> None:
    window = _window(_Host(_App(), tmp_path))
    window._timer.Start(60_000)
    window._win.Destroy()
    for _ in range(3):
        wx.GetApp().ProcessPendingEvents()
        wx.SafeYield()
    assert not window._timer.IsRunning()


@pytest.mark.parametrize("rows", [menus.ITEM_POPUP, menus.LINEUP_POPUP])
def test_each_context_menu_gives_every_item_its_own_letter(rows) -> None:
    letters = [label[label.index("&") + 1].lower() for verb, label in rows if verb]
    assert len(letters) == len(set(letters))
