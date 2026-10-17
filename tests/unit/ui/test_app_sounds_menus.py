"""Every QUILL app has App Sounds on Alt+Shift+M, built from its real menu bar.

The family rule this pins (ui/app_sounds): one item, one key, in every app --
because "make it stop" is reached for without thinking about which app is in
front. Built from the real frames rather than read from source, because a
label assembled from a keymap is only proven by the menu it ends up in.
"""

from __future__ import annotations

import collections
import importlib
import re

import pytest

from tests.wx_session import shared_wx_app

wx = pytest.importorskip("wx")

_APPS = [
    ("quill.apps.radio", "RadioAppFrame"),
    ("quill.apps.podcasts", "PodcastsAppFrame"),
    ("quill.apps.player", "QuillMediaPlayerFrame"),
    ("quill.apps.studio", "StudioAppFrame"),
    ("quill.apps.weather", "WeatherAppFrame"),
    ("quill.apps.inkwell", "QuillInkwellFrame"),
    ("quill.apps.converter", "QuillConverterFrame"),
    ("quill.apps.transcribe", "QuillTranscribeFrame"),
]


def _walk(menu: object, path: str = ""):  # type: ignore[no-untyped-def]
    for item in menu.GetMenuItems():  # type: ignore[attr-defined]
        sub = item.GetSubMenu()
        label = item.GetItemLabel()
        if sub is not None:
            yield from _walk(sub, f"{path}{label}>")
        elif not item.IsSeparator():
            yield path, item


@pytest.fixture
def menu_items(quill_data_dir, request):  # type: ignore[no-untyped-def]
    module_name, class_name = request.param
    app = shared_wx_app()
    frame_cls = getattr(importlib.import_module(module_name), class_name)
    shell = frame_cls()
    bar = shell.frame.GetMenuBar()
    items = []
    for index in range(bar.GetMenuCount()):
        title = bar.GetMenuLabel(index)
        items.extend((title, path, item) for path, item in _walk(bar.GetMenu(index)))
    yield class_name, items, shell
    _stop_timers(request)
    from quill.ui.dialog_contract import set_transition_announcement_policy

    set_transition_announcement_policy(None)
    shell.frame.Destroy()
    del app


def _stop_timers(request) -> None:  # type: ignore[no-untyped-def]
    """Stop what the app started: these frames are built, not run, so their
    own close paths -- which stop every timer -- never happen. The registry is
    tests/conftest.py's, reached as the plugin it is."""
    for plugin in request.config.pluginmanager.get_plugins():
        watched = getattr(plugin, "_WATCHED_WX_TIMERS", None)
        if watched is None:
            continue
        for timer in list(watched):
            try:
                if timer.IsRunning():
                    timer.Stop()
            except Exception:  # noqa: BLE001 - a dead timer is a stopped one
                pass


@pytest.mark.machine_global
@pytest.mark.parametrize("menu_items", _APPS, indirect=True, ids=[name for _m, name in _APPS])
def test_app_sounds_is_on_alt_shift_m_and_claims_nothing_twice(menu_items) -> None:  # type: ignore[no-untyped-def]
    name, items, _shell = menu_items
    sounds = [
        item
        for _t, _p, item in items
        if item.GetItemLabelText().startswith("App Sounds")
        and "Play" not in item.GetItemLabelText()
    ]
    assert len(sounds) == 1, f"{name}: App Sounds appears {len(sounds)} times"
    assert sounds[0].GetItemLabel().endswith("\tAlt+Shift+M"), sounds[0].GetItemLabel()
    assert sounds[0].IsCheckable()
    keys = collections.Counter(
        item.GetItemLabel().split("\t", 1)[1].lower()
        for _t, _p, item in items
        if "\t" in item.GetItemLabel() and item.IsEnabled()
    )
    assert keys["alt+shift+m"] == 1, f"{name}: Alt+Shift+M claimed {keys['alt+shift+m']} times"
    # Its access letter is its own in the menu it lives in (GATE-14's rule, for
    # menus): a duplicate means one of the pair is never reached by its letter.
    home = next((title, path) for title, path, item in items if item is sounds[0])
    own = re.search(r"&(\w)", sounds[0].GetItemLabel().split("\t")[0])
    if own is None:
        return  # no letter at all, where every letter in the name was spent
    mine = own.group(1).lower()
    letters = [
        found.group(1).lower()
        for title, path, item in items
        if (title, path) == home
        and (found := re.search(r"&(\w)", item.GetItemLabel().split("\t")[0]))
    ]
    assert letters.count(mine) == 1, (
        f"{name} {home[0]}: '{mine}' is claimed {letters.count(mine)} times; "
        f"taken: {sorted(set(letters))}"
    )
