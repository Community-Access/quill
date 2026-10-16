"""System-wide keys per favourite, registered and chosen (xradio2 4.9).

Todo P3 "Radio extras" 6. What a key may be is decided in
:mod:`quill.core.radio.favorite_hotkeys` (the family's own conflict check);
this module registers the keys with Windows while Quill Radio runs, plays the
station when one is pressed, and asks for a key from a favourite's context menu
(**System-Wide Key...**, in both favourites trees).

* Empty by default: no favourite has a key until the listener gives it one.
* A key Windows will not give us (another program holds it) is refused when it
  is chosen, with the reason, and never silently kept.
* Pressing it plays the station from anywhere and says so; the window is not
  brought forward, because a key that works from another program is for
  *staying* in that program.

Registration ids live in their own range (0x7C00 up), apart from the media keys
(0x7A00) and the show/hide key (0x7B00) in ``app_shell``.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

__all__ = ["BASE_ID", "choose_key", "register_all", "unregister_all"]

#: First registration id; one per favourite with a key.
BASE_ID = 0x7C00
#: Never more than this many: an id range has to end somewhere.
_MAX = 0x100


def _data_dir() -> Any:
    from quill.core.paths import app_data_dir

    return app_data_dir()


def unregister_all(app: Any) -> None:
    """Release every favourite key this window registered."""
    for hotkey_id in getattr(app, "_favorite_hotkey_ids", []):
        try:
            app.frame.UnregisterHotKey(hotkey_id)
        except Exception:  # noqa: BLE001 - shutdown must never block
            pass
    app._favorite_hotkey_ids = []


def register_all(app: Any, wx: Any, *, platform: str = sys.platform) -> list[str]:
    """(Re-)register every favourite key. Returns the chords Windows refused."""
    from quill.core.radio.favorite_hotkeys import load_hotkeys
    from quill.ui.tray_hotkey import parse_hotkey

    unregister_all(app)
    if not platform.startswith("win"):
        return []
    store = app._radio_favorites
    refused: list[str] = []
    ids: list[int] = []
    for offset, (key, chord) in enumerate(sorted(load_hotkeys(_data_dir()).items())):
        if offset >= _MAX:
            break
        favorite = store.find(key)
        parsed = parse_hotkey(wx, chord)
        if favorite is None or parsed is None:
            continue
        hotkey_id = BASE_ID + offset
        try:
            ok = bool(app.frame.RegisterHotKey(hotkey_id, parsed[0], parsed[1]))
        except Exception:  # noqa: BLE001 - a denied key must never block startup
            ok = False
        if not ok:
            refused.append(chord)
            continue
        app.frame.Bind(wx.EVT_HOTKEY, lambda _e, k=key: play_favorite_by_key(app, k), id=hotkey_id)
        ids.append(hotkey_id)
    app._favorite_hotkey_ids = ids
    if refused:
        logger.info("Favourite keys held by another program: %s", ", ".join(refused))
    return refused


def play_favorite_by_key(app: Any, key: str) -> None:
    """A favourite's key was pressed: play it, or say why not."""
    favorite = app._radio_favorites.find(key)
    if favorite is None:
        app._announce("That favorite is no longer in your favorites.")
        return
    app._radio_controller.play_station(favorite.station)
    app._announce(f"Playing {favorite.display_label}.")


def choose_key(
    app: Any,
    favorite: Any,
    *,
    parent: Any,
    ask: Callable[[str, str], str | None] | None = None,
    claimed: Callable[[str], bool] | None = None,
) -> bool:
    """Ask for this favourite's key, check it, save it and register it.

    *ask(prompt, current)* returns the typed chord or ``None`` on Cancel (a
    ``wx.TextEntryDialog`` by default); *claimed(chord)* says whether another
    program already holds it (Windows' own answer by default). Both are
    injectable so the tests open nothing and probe no real key. Returns
    whether the saved key changed.
    """
    import wx

    from quill.core.family_chords import SHOW_HIDE_DEFAULTS
    from quill.core.radio.favorite_hotkeys import load_hotkeys, problem, set_hotkey

    data_dir = _data_dir()
    hotkeys = load_hotkeys(data_dir)
    current = hotkeys.get(favorite.key, "")
    prompt = (
        f"A key that plays {favorite.display_label} from anywhere, even with another "
        "program in front -- for example Ctrl+Alt+PageUp. It needs Ctrl or Alt. "
        "Leave it empty for no key."
    )
    typed = (ask or _ask_with_dialog(parent))(prompt, current)
    if typed is None:
        return False
    chord = typed.strip()
    if chord == current:
        app._announce("Key unchanged.")
        return False
    store = app._radio_favorites
    if chord:
        names = {f.key: f.display_label for f in store.favorites}
        reason = problem(
            chord,
            favorite_key=favorite.key,
            hotkeys=hotkeys,
            names=names,
            show_hide_key=SHOW_HIDE_DEFAULTS.get("radio", ""),
        )
        if not reason and (claimed or _claimed_by_windows)(chord):
            reason = (
                f"{chord} is already held by another program on this computer, "
                "so Windows would never send it here."
            )
        if reason:
            app._announce(f"{reason} The key was not changed.")
            return False
    set_hotkey(data_dir, favorite.key, chord, keep={f.key for f in store.favorites})
    register_all(app, wx)
    if chord:
        app._announce(f"{chord} now plays {favorite.display_label} from anywhere.")
    else:
        app._announce(f"{favorite.display_label} no longer has a system-wide key.")
    return True


def _claimed_by_windows(chord: str) -> bool:
    import wx

    from quill.ui.hotkey_conflict import claimed_by_another_application

    try:
        return claimed_by_another_application(chord, wx)
    except Exception:  # noqa: BLE001 - "could not tell" is never "taken"
        return False


def _ask_with_dialog(parent: Any) -> Callable[[str, str], str | None]:
    def ask(prompt: str, current: str) -> str | None:
        import wx

        with wx.TextEntryDialog(parent, prompt, "System-Wide Key", value=current) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return None
            return str(dialog.GetValue())

    return ask
