"""Each app's half of the Command Key: QUILL, QUILL Lite and Quill Radio.

docs/design/command-key.md 16.4 (PR 2b). The Command Key itself is shared --
the policy in :mod:`quill.core.command_catalogue.policy`, the windows in
:mod:`quill.ui.command_key_ui` -- and an app only says four things about
itself: which registry runs its commands, how it speaks, how it shows a modal
window, and how it knows a command is switched off here. These functions are
those four answers, one per app, so no app grows a command key of its own.

"Switched off here" is the menu's own answer wherever the app has one: a dimmed
menu row is a command this window cannot do right now, and the Command Key asks
exactly the same question rather than guessing (section 3.2).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.command_catalogue import CommandSpec, rows_for_app
from quill.ui.command_key_ui import WxCommandKeyHost, run_command_key

__all__ = [
    "hint_shown",
    "lite_command_key",
    "lite_what_can_i_say_here",
    "quill_command_key",
    "quill_what_can_i_say_here",
    "radio_command_key",
    "radio_what_can_i_say_here",
]

_APP_NAMES = {"quill": "QUILL", "radio": "Quill Radio"}
_STATE_FILE = "command-key.json"


def _load_state() -> dict[str, Any]:
    from quill.core.paths import app_data_dir
    from quill.core.storage import read_json

    try:
        state = read_json(app_data_dir() / _STATE_FILE, default={})
    except Exception:  # noqa: BLE001 - an unreadable file is a fresh start, not a crash
        return {}
    return dict(state) if isinstance(state, dict) else {}


def _save_state(**changes: Any) -> None:
    from quill.core.paths import app_data_dir
    from quill.core.storage import write_json_atomic

    state = {**_load_state(), **changes}
    try:
        write_json_atomic(app_data_dir() / _STATE_FILE, state, base=app_data_dir())
    except Exception:  # noqa: BLE001 - a read-only profile is asked again, nothing worse
        pass


def hint_shown() -> bool:
    """Whether the one-time hint has been said (11.4). Marks it said as it answers."""
    if _load_state().get("hint_shown"):
        return True
    _save_state(hint_shown=True)
    return False


def _other_apps(app: str) -> tuple[tuple[str, CommandSpec], ...]:
    """Other apps' offered rows, only to say "That's in Quill Radio" (11.5)."""
    others = ("radio",) if app in {"quill", "lite"} else ("quill",)
    return tuple(
        (_APP_NAMES[other], spec)
        for other in others
        for spec in rows_for_app(other)
        if spec.offered
    )


def _dimmed(item: Any, spec: CommandSpec) -> str:
    try:
        if item is not None and not item.IsEnabled():
            return f"{spec.title} isn't available here right now."
    except Exception:  # noqa: BLE001 - a menu that cannot say is a menu that did not dim
        return ""
    return ""


def _keys(registry: Any) -> Callable[[str], str]:
    def key_for(command_id: str) -> str:
        try:
            return str(registry.keybinding_for(command_id) or "")
        except Exception:  # noqa: BLE001 - a row without its key is still a row
            return ""

    return key_for


# -- QUILL ----------------------------------------------------------------------


def _quill_host(frame: Any) -> WxCommandKeyHost:
    import wx

    menu_ids = frame._command_to_menu_id_map()
    menu_bar = frame.frame.GetMenuBar()

    def probe(spec: CommandSpec) -> str:
        item_id = menu_ids.get(spec.id)
        if item_id is None or menu_bar is None:
            return ""
        return _dimmed(menu_bar.FindItemById(item_id), spec)

    return WxCommandKeyHost(
        wx=wx,
        parent=frame.frame,
        app="quill",
        registry=frame.commands,
        show_modal=frame._show_modal_dialog,
        announce=frame._announce,
        key_for=_keys(frame.commands),
        probe=probe,
        other_apps=_other_apps("quill"),
    )


def quill_command_key(frame: Any) -> None:
    """F11 in QUILL."""
    host = _quill_host(frame)
    frame._command_key_session = run_command_key(
        host,
        getattr(frame, "_command_key_session", None),
        first_time=not hint_shown(),
    )


def quill_what_can_i_say_here(frame: Any) -> None:
    """Help, What Can I Say Here (Ctrl+Alt+Shift+F1) in QUILL."""
    host = _quill_host(frame)
    picked = host.show_help("")
    if picked is not None:
        session = getattr(frame, "_command_key_session", None)
        _run_picked(host, session, picked, frame)


def _run_picked(host: WxCommandKeyHost, session: Any, picked: Any, owner: Any) -> None:
    from quill.core.command_catalogue.policy import CommandKeySession

    session = session or CommandKeySession(host)
    session.host = host
    session.run_candidate(picked)
    owner._command_key_session = session


# -- QUILL Lite ----------------------------------------------------------------


def _lite_host(window: Any) -> WxCommandKeyHost:
    import wx

    from quill.ui.dialog_contract import show_modal_dialog

    registry = window.app.command_registry(window)
    sync = getattr(window, "_sync_enabled_items", None)
    if callable(sync):
        sync()
    items = getattr(window, "_menu_items", {})

    def probe(spec: CommandSpec) -> str:
        return _dimmed(items.get(spec.id.removeprefix("lite.")), spec)

    return WxCommandKeyHost(
        wx=wx,
        parent=window,
        app="lite",
        registry=registry,
        show_modal=lambda dialog, label: int(show_modal_dialog(dialog, label)),
        announce=window._announce,
        key_for=_keys(registry),
        probe=probe,
        other_apps=_other_apps("lite"),
    )


def lite_command_key(window: Any) -> None:
    """F11 in QUILL Lite."""
    host = _lite_host(window)
    window._command_key_session = run_command_key(
        host,
        getattr(window, "_command_key_session", None),
        first_time=not hint_shown(),
    )


def lite_what_can_i_say_here(window: Any) -> None:
    """Help, What Can I Say Here (Ctrl+Alt+Shift+F1) in QUILL Lite."""
    host = _lite_host(window)
    picked = host.show_help("")
    if picked is not None:
        _run_picked(host, getattr(window, "_command_key_session", None), picked, window)


# -- Quill Radio ------------------------------------------------------------------


def _radio_host(frame: Any) -> WxCommandKeyHost:
    import wx

    return WxCommandKeyHost(
        wx=wx,
        parent=frame,
        app="radio",
        registry=frame.commands,
        show_modal=frame._show_modal_dialog,
        announce=frame._announce,
        key_for=_keys(frame.commands),
        other_apps=_other_apps("radio"),
    )


def radio_command_key(frame: Any) -> None:
    """F11 in Quill Radio's player window."""
    host = _radio_host(frame)
    frame._command_key_session = run_command_key(
        host,
        getattr(frame, "_command_key_session", None),
        first_time=not hint_shown(),
    )


def radio_what_can_i_say_here(frame: Any) -> None:
    """Help, What Can I Say Here (Ctrl+Alt+Shift+F1) in Quill Radio."""
    host = _radio_host(frame)
    picked = host.show_help("")
    if picked is not None:
        _run_picked(host, getattr(frame, "_command_key_session", None), picked, frame)
