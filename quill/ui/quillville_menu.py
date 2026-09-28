"""The shared **QuillVille** menu -- one consistent cross-app switcher.

Every QuillVille app (QUILL, Quill Radio, Quill Weather, Quill Cast, Audio
Studio) carries the same top-level QuillVille menu: a list of "Open <sibling
app>" items that launch a family member in its own window. Same name, same
place, same job everywhere -- so moving around the suite is muscle memory.

This is deliberately *not* a functional menu (it is not "Weather" or "Radio"):
it is the family-navigation menu, which is exactly what a brand name should
label. Functional menus keep their descriptive names.

**Reachable without chords** (3.0.3). Its default keys are long -- Ctrl+Alt+
Shift+F7 and up -- because every shorter chord is taken somewhere in the
family, and a listener on a BrailleNote Evolve, or anybody for whom holding
four keys at once is hard, said so (BITS, 2026-09-28). So:

* every row has an **access letter**: Alt+Q opens this menu, and one more
  letter opens the app -- two single keys, nothing held down (Alt+Q, R is
  Quill Radio);
* every row is a **real command**, ``quillville.open_<app>``, registered with
  the host and bound through its keymap, so Keyboard Shortcuts (Ctrl+Alt+K)
  lists it and it can be rebound to anything; the long chord is only its
  default, merged in memory the way ``app_keymaps`` defaults are.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.app_launcher import APP_NAMES, RELEASED_APPS, is_app_released

#: The order siblings are listed in the QuillVille menu (the current app is
#: skipped via ``exclude``).
QUILLVILLE_APP_ORDER: tuple[str, ...] = (
    "quill",
    "radio",
    "weather",
    "cast",
    "studio",
    "converter",
    "inkwell",
)

#: ``RELEASED_APPS`` is re-exported from ``quill.core.app_launcher`` (the single
#: source of truth). Gating uses :func:`is_app_released`, which also honors a
#: developer build (``QUILL_DEV_BUILD=1``).
__all__ = [
    "MENU_NAMES",
    "QUILLVILLE_APP_ORDER",
    "RELEASED_APPS",
    "build_quillville_menu",
    "command_id",
]

#: Each app's row label, with its access letter. Unique across the whole list,
#: so Alt+Q then that letter opens the app in every app's menu; "Open" itself
#: never carries the letter (it would be O for all of them).
MENU_NAMES: dict[str, str] = {
    "quill": "&QUILL",
    "radio": "Quill &Radio",
    "weather": "Quill &Weather",
    "cast": "Quill &Cast",
    "studio": "&Audio Studio",
    "converter": "Quill Con&verter",
    "inkwell": "Quill &Inkwell",
    "player": "Quill Media &Player",
}


def command_id(app_key: str) -> str:
    """The rebindable command behind a QuillVille row."""
    return f"quillville.open_{app_key}"


def _row(
    key: str,
    position: int,
    on_launch: Callable[[str], None],
    host: Any,
) -> str:
    """The row's label, registering its command with *host* on the way.

    The host (an ``AppShellFrame`` or QUILL's ``MainFrame``) has ``commands``,
    ``keymap`` and ``_binding_for``. The positional chord is merged into its
    keymap only when the listener has not bound the command themselves, so a
    rebinding in Keyboard Shortcuts wins and a reset brings the default back.
    Without a host (the tray's copy in a test) the default is shown as it is.
    """
    from quill.core.app_keymaps import SIBLING_APP_ACCELERATORS

    default = SIBLING_APP_ACCELERATORS[position] if position < len(SIBLING_APP_ACCELERATORS) else ""
    name = MENU_NAMES.get(key, APP_NAMES[key])
    binding = default
    commands = getattr(host, "commands", None)
    keymap = getattr(host, "keymap", None)
    if commands is not None and isinstance(keymap, dict):
        cid = command_id(key)
        if commands.get(cid) is None:
            commands.register(cid, f"QuillVille: Open {APP_NAMES[key]}", lambda k=key: on_launch(k))
        if default and not keymap.get(cid):
            keymap[cid] = default
        binding = host._binding_for(cid) or ""
    # A comma is a chord binding, which a menu label cannot carry (#612).
    accelerator = f"\t{binding}" if binding and "," not in binding else ""
    return f"Open {name}{accelerator}"


def build_quillville_menu(
    wx: Any,
    frame: Any,
    on_launch: Callable[[str], None],
    *,
    exclude: str,
    retain: Callable[[Any], None],
    also_exclude: tuple[str, ...] = (),
    host: Any = None,
) -> Any:
    """Build the QuillVille menu for one app.

    ``on_launch(key)`` opens sibling ``key`` (the app's own launch handler);
    ``exclude`` is this app's key (left off the list); ``retain`` pins each
    menu-item id for the frame's lifetime (a bare ``NewIdRef`` would otherwise
    hand its id to whatever allocates one next). Bindings go on ``frame`` so the
    menu-bar events are caught.

    ``also_exclude`` lets one app leave a sibling off its own menu without
    changing whether that sibling is released for everybody else. A menu item
    that opens an app somebody is not expecting to be shipped alongside this
    release is a promise this release did not mean to make.
    """
    menu = wx.Menu()
    skip = {exclude, *also_exclude}
    # The app shells pass their own bound _keep_menu_ids as *retain*, so the
    # host is recoverable without every call site naming it again.
    host = host if host is not None else getattr(retain, "__self__", None)
    # Every item shows a way to reach it from the keyboard (the house rule):
    # its access letter always, and its key -- numbered in menu order by
    # default, rebindable through the host's keymap.
    position = 0
    for key in QUILLVILLE_APP_ORDER:
        if key in skip or not is_app_released(key):
            continue
        item_id = wx.NewIdRef()
        menu.Append(item_id, _row(key, position, on_launch, host))
        position += 1
        frame.Bind(wx.EVT_MENU, lambda _e, k=key: on_launch(k), id=item_id)
        retain(item_id)
    return menu


def append_sibling_items(
    menu: Any,
    *,
    frame: Any,
    exclude: str,
    on_launch: Callable[[str], None],
    retain: Callable[..., None],
    host: Any = None,
) -> None:
    """Append 'Open <sibling app>' rows to an existing menu (the tray's copy).

    The same list the menu bar's QuillVille menu builds, so the tray cannot
    drift from it -- including the numbered accelerators every item carries
    (the house rule: a menu item always shows a way to reach it).
    """
    import wx

    host = host if host is not None else getattr(retain, "__self__", None)
    position = 0
    for key in ("quill", "radio", "weather"):
        if key == exclude:
            continue
        item_id = wx.NewIdRef()
        menu.Append(item_id, _row(key, position, on_launch, host))
        position += 1
        frame.Bind(wx.EVT_MENU, lambda _e, k=key: on_launch(k), id=item_id)
        retain(item_id)
