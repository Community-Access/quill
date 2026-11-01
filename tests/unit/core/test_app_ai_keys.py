"""The QuillVille apps' AI keys, against the editors' (rule 11)."""

from __future__ import annotations

import pytest

from quill.core.app_ai_keys import APP_AI_DIVERGENCES
from quill.core.app_keymaps import APP_KEYMAPS
from quill.core.keymap import DEFAULT_KEYMAP, canonical_binding

_WINDOW_KEYS = {canonical_binding(f"Ctrl+{n}") for n in range(1, 10)}


def _same(left: str, right: str) -> bool:
    return (canonical_binding(left) or left.upper()) == (canonical_binding(right) or right.upper())


#: Apps whose Ctrl+1 to Ctrl+9 are Window menu keys (quill/ui/window_menu.py).
_WINDOW_MENU_APPS = ["radio", "cast", "transcribe", "weather", "converter", "player", "inkwell"]


@pytest.mark.parametrize("app", _WINDOW_MENU_APPS)
def test_no_ai_command_takes_a_window_menu_key(app: str) -> None:
    taken = {
        command: key
        for command, key in APP_KEYMAPS[app].items()
        if command.startswith("tools.hosted_ai_") and canonical_binding(key) in _WINDOW_KEYS
    }
    assert taken == {}


@pytest.mark.parametrize("app", [*_WINDOW_MENU_APPS, "studio", "beacon"])
def test_every_ai_key_that_differs_from_the_editors_has_a_row(app: str) -> None:
    missing = [
        command
        for command, key in APP_KEYMAPS[app].items()
        if command.startswith("tools.hosted_ai_")
        and not _same(key, DEFAULT_KEYMAP.get(command, ""))
        and (app, command) not in APP_AI_DIVERGENCES
    ]
    assert missing == []


def test_every_row_still_diverges_and_gives_a_reason() -> None:
    for (app, command), reason in APP_AI_DIVERGENCES.items():
        assert len(reason) > 40, (app, command)
        key = APP_KEYMAPS[app].get(command, "")
        assert key, f"{app} does not bind {command}; delete the row"
        assert not _same(key, DEFAULT_KEYMAP[command]), f"{app} agrees on {command} now"


def test_radio_and_cast_share_their_ai_keys() -> None:
    for command in ("tools.hosted_ai_which", "tools.hosted_ai_choose"):
        assert APP_KEYMAPS["radio"][command] == APP_KEYMAPS["cast"][command]
    assert (
        APP_KEYMAPS["radio"]["radio.ask_quill_radio"]
        == (APP_KEYMAPS["cast"]["tools.hosted_ai_chat_key"])
    )


def test_transcribe_takes_the_same_fallback_set_as_radio_and_cast() -> None:
    for command in ("tools.hosted_ai_which", "tools.hosted_ai_choose", "tools.hosted_ai_chat_key"):
        assert APP_KEYMAPS["transcribe"][command] == APP_KEYMAPS["cast"][command]


def test_studio_keeps_the_editors_digit_keys() -> None:
    """No Window menu in Studio, so decision 14's keys hold: nothing overrides them."""
    for command in ("tools.hosted_ai_which", "tools.hosted_ai_choose", "tools.hosted_ai_chat_key"):
        assert command not in APP_KEYMAPS["studio"]
        assert (APP_KEYMAPS["studio"].get(command) or DEFAULT_KEYMAP[command]) in (
            "Ctrl+8",
            "Ctrl+4",
            "Ctrl+6",
        )


def test_studio_and_transcribe_menus_have_no_window_menu_keys() -> None:
    """Studio has no Window menu (so Ctrl+4, 6, 8 are free); Transcribe has one."""
    import inspect

    from quill.apps import studio, transcribe

    assert "WindowManager" not in inspect.getsource(studio)
    assert "WindowManager" in inspect.getsource(transcribe)


@pytest.mark.parametrize("app", ["weather", "converter", "player", "inkwell"])
def test_the_small_window_menu_apps_take_the_same_fallback_set(app: str) -> None:
    for command in ("tools.hosted_ai_which", "tools.hosted_ai_choose", "tools.hosted_ai_chat_key"):
        assert APP_KEYMAPS[app][command] == APP_KEYMAPS["cast"][command]


@pytest.mark.parametrize(
    ("app", "module"),
    [
        ("weather", "quill.apps.weather"),
        ("converter", "quill.apps.converter"),
        ("player", "quill.apps.player"),
        ("inkwell", "quill.apps.inkwell"),
    ],
)
def test_the_fallback_apps_really_have_a_window_menu(app: str, module: str) -> None:
    import importlib
    import inspect

    assert "WindowManager" in inspect.getsource(importlib.import_module(module)), app


def test_beacon_keeps_the_editors_digit_keys_and_has_no_window_menu() -> None:
    import inspect

    from quill.apps.beacon import app as beacon_app

    for command, key in (
        ("tools.hosted_ai_which", "Ctrl+8"),
        ("tools.hosted_ai_choose", "Ctrl+4"),
        ("tools.hosted_ai_chat_key", "Ctrl+6"),
    ):
        assert APP_KEYMAPS["beacon"][command] == key == DEFAULT_KEYMAP[command]
    source = inspect.getsource(beacon_app)
    assert "WindowManager" not in source
    # Beacon's labels carry their keys as text: no row may end in a Ctrl+digit.
    assert not any(f'\\tCtrl+{n}"' in source for n in range(1, 10))
