"""The Station menu on every radio surface, and the warm-up behind fast search.

Two reports, both 2026-08-26. *"alt+s is not bringing up the Station menu"* --
each peer window built a bar of its own menu plus &Window, and the app's
commands lived only on the main window, so the letter that works everywhere in
the main window opened nothing anywhere else. And *"do it async in the
background somehow"* -- the cached directories were only fetched by the first
search that needed them, which is why the first search was the slow one.
"""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

from quill.ui.radio import browse_warmup, surface_app_menu

_RADIO_UI = Path(__file__).resolve().parents[3] / "quill" / "ui" / "radio"

#: Every modeless radio surface with its own menu bar. A new surface that
#: builds one must join this list or wire the menu -- the assertion below says
#: which.
SURFACES = (
    "browse_tree_dialog",
    "favorites_manager_dialog",
    "recordings_manager_dialog",
    "song_history_dialog",
    "download_queue_dialog",
    "station_browser_dialog",
    "schedule_recording_dialog",
    "now_playing_dialog",
    "player_panel",
)


# --- the menu itself ----------------------------------------------------------


class _Menu:
    def __init__(self) -> None:
        self.items: list[tuple[object, str]] = []

    def Append(self, item_id, label):  # noqa: N802
        self.items.append((item_id, label))


class _MenuBar:
    def __init__(self) -> None:
        self.menus: list[tuple[_Menu, str]] = []

    def Append(self, menu, title):  # noqa: N802
        self.menus.append((menu, title))


class _Win:
    def __init__(self) -> None:
        self.bound: list[object] = []

    def Bind(self, _event, _handler, id=None):  # noqa: N802, A002
        self.bound.append(id)


def _wx():
    counter = iter(range(1, 999))
    return SimpleNamespace(Menu=_Menu, EVT_MENU=object(), NewIdRef=lambda: next(counter))


def _host(**overrides):
    host = SimpleNamespace(
        open_browse_stations=lambda: None,
        open_internet_radio=lambda: None,
        open_manage_radio_favorites=lambda: None,
        open_radio_recordings=lambda: None,
        _open_preferences=lambda: None,
        _menu_label=lambda text, _cid: f"{text}\tCtrl+X",
    )
    for name, value in overrides.items():
        setattr(host, name, value)
    return host


def test_the_menu_is_titled_station_and_every_item_shows_a_key() -> None:
    bar = _MenuBar()
    ids = surface_app_menu.install(win=_Win(), host=_host(), menu_bar=bar, wx=_wx())
    assert [title for _m, title in bar.menus] == ["&Station"]
    menu = bar.menus[0][0]
    assert len(ids) == len(menu.items) == len(surface_app_menu.COMMANDS)
    # The house rule: an enabled item names its key, whether from the keymap
    # (_menu_label above) or from the literal fallback.
    assert all("\t" in label for _id, label in menu.items)


def test_a_surface_skips_the_commands_it_already_owns() -> None:
    bar = _MenuBar()
    surface_app_menu.install(
        win=_Win(),
        host=_host(),
        menu_bar=bar,
        wx=_wx(),
        skip=("open_browse_stations", "open_internet_radio"),
    )
    labels = " ".join(label for _id, label in bar.menus[0][0].items)
    assert "Browse Stations" not in labels
    assert "Search Stations" not in labels
    assert "Preferences" in labels


def test_a_host_with_none_of_the_commands_gets_no_menu_at_all() -> None:
    """Cast shares two of these surfaces; its shell has no radio commands."""
    bar = _MenuBar()
    assert (
        surface_app_menu.install(win=_Win(), host=SimpleNamespace(), menu_bar=bar, wx=_wx()) == []
    )
    assert bar.menus == []
    assert surface_app_menu.install(win=_Win(), host=None, menu_bar=bar, wx=_wx()) == []


def test_host_of_resolves_whatever_this_surface_called_its_shell() -> None:
    shell = object()
    for name in ("_host", "_transport_host", "_download_host", "_app_host"):
        dialog = SimpleNamespace(**{name: shell})
        assert surface_app_menu.host_of(dialog) is shell
    assert surface_app_menu.host_of(SimpleNamespace()) is None
    # A dialog that is its own host (browse_tree's default) resolves to None
    # rather than to itself: the commands live on the shell, not the window.
    loner = SimpleNamespace()
    loner._download_host = loner
    assert surface_app_menu.host_of(loner) is None


def test_every_surface_with_a_menu_bar_installs_the_station_menu() -> None:
    """The gate: a new peer window must not reopen the Alt+S hole."""
    missing = []
    for name in SURFACES:
        text = (_RADIO_UI / f"{name}.py").read_text(encoding="utf-8")
        if "surface_app_menu.install(" not in text:
            missing.append(name)
    assert not missing, f"surfaces without the Station menu: {missing}"
    # ...and the list itself is honest: these files really do build a bar.
    for name in SURFACES:
        text = (_RADIO_UI / f"{name}.py").read_text(encoding="utf-8")
        assert re.search(r"menu_bar\.Append\(", text), name


# --- the warm-up --------------------------------------------------------------


def _warm_host(**overrides):
    submitted: list[str] = []
    host = SimpleNamespace(
        _safe_mode=False,
        _visible_sources=None,  # never set -> the defaults, which include all three
        _task_manager=SimpleNamespace(
            submit=lambda name, work, on_success=None, on_failure=None: submitted.append(name)
        ),
        submitted=submitted,
    )
    for name, value in overrides.items():
        setattr(host, name, value)
    return host


def test_the_warmup_runs_once_per_app_run() -> None:
    browse_warmup.reset_for_tests()
    host = _warm_host()
    assert browse_warmup.warm(host) is True
    assert browse_warmup.warm(host) is False
    assert host.submitted == ["radio-directory-warmup"]


def test_safe_mode_never_even_spawns_the_task() -> None:
    browse_warmup.reset_for_tests()
    host = _warm_host(_safe_mode=True)
    assert browse_warmup.warm(host) is False
    assert host.submitted == []


def test_a_source_that_is_off_is_not_warmed() -> None:
    """The browse-visibility contract: off means never contacted."""
    browse_warmup.reset_for_tests()
    host = _warm_host(_visible_sources=("favorites", "rbgenre"))
    assert browse_warmup.warm(host) is False
    assert host.submitted == []
    # ...and having declined for that reason, a later open with the sources on
    # still gets its warm-up: declining did not spend the once-per-run shot.
    host_on = _warm_host()
    assert browse_warmup.warm(host_on) is True


def test_only_locally_cacheable_sources_are_warmable() -> None:
    """Warming a live listing would fetch data stale by the time it is read."""
    assert set(browse_warmup.WARMABLE) == {"live365", "radioparadise", "shoutcast", "tv"}
