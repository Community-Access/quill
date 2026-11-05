"""Every menu item is a palette row: the menu bar's own half of the palette.

The Command Palette lists what is in the command registry, and most of QUILL's
commands are there. Not all: a menu item can be built with a wx id and a
handler and nothing else -- a dynamic row (a recent file, an open window, a
sound pack), a submenu someone added in a mixin without registering it, a
command that lives only in a menu. Those were reachable by the menu and by
their key, and the palette had never heard of them, so typing their name found
nothing. A palette that finds most commands teaches people it cannot be
trusted, which is worse than one that finds none.

:func:`register_menu_items` closes that from the menu bar's side rather than
by finding each missing registration: after the bar is built it walks every
item, and any item whose id no registered command already owns becomes a row
titled by its menu path ("File > Import > Word Document") that runs by posting
the item's own menu event. The handler that runs is the one the menu runs, so
the two cannot drift, and the rows are regenerated whenever the bar is.

QUILL Lite's palette is built from the same table its menus are
(``quill.core.lite.commands.COMMANDS``), so there the walk only adds the rows
the table cannot hold: the open windows and the recent files.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Iterator
from typing import Any

#: Every row this module adds carries this prefix, so a rebuild can remove the
#: previous set in one call.
MENU_COMMAND_PREFIX = "menu."

_TAB = "\t"
#: A keyboard route written into a label rather than after a tab:
#: "(Alt+F, I, W)", "(QUILL Key + S)".
_ROUTE_SUFFIX = re.compile(r"\s*\((?:QUILL Key|Alt|Ctrl|Cmd|Shift)[^()]*\)\s*$")


def plain_menu_text(label: str) -> str:
    """*label* as it should be read: no mnemonic, no key, no route, no dots."""
    text = label.split(_TAB, 1)[0]
    text = _ROUTE_SUFFIX.sub("", text)
    text = text.replace("&&", "\0").replace("&", "").replace("\0", "&")
    text = text.strip()
    if text.endswith("..."):
        text = text[:-3].rstrip()
    return text


def walk_menu_items(menu_bar: Any) -> Iterator[tuple[tuple[str, ...], Any]]:
    """Yield ``(path, item)`` for every runnable item in *menu_bar*.

    *path* is the plain titles from the top-level menu down to the item.
    Separators and submenu titles are not runnable and are skipped; their
    children are walked.
    """
    for index in range(menu_bar.GetMenuCount()):
        top = plain_menu_text(menu_bar.GetMenuLabel(index))
        yield from _walk(menu_bar.GetMenu(index), (top,))


def _walk(menu: Any, path: tuple[str, ...]) -> Iterator[tuple[tuple[str, ...], Any]]:
    for item in menu.GetMenuItems():
        if item.IsSeparator():
            continue
        title = plain_menu_text(item.GetItemLabel())
        if not title:
            continue
        submenu = item.GetSubMenu()
        if submenu is not None:
            yield from _walk(submenu, (*path, title))
            continue
        yield (*path, title), item


def register_menu_items(
    registry: Any,
    menu_bar: Any,
    *,
    covered_ids: Iterable[int] = (),
    covered_paths: Iterable[tuple[str, ...]] = (),
    post_menu_event: Callable[[int], None],
    binding_for_item: Callable[[Any], str | None] | None = None,
) -> int:
    """Add a palette row for every menu item no registered command owns.

    *covered_ids* are the wx ids that already belong to a registered command
    (``_command_to_menu_id_map``); those items are in the palette under their
    own command and are not listed twice. *covered_paths* does the same by
    menu path, for a host whose registry is built from a table rather than
    from wx ids (QUILL Lite). *post_menu_event* runs an item the way choosing
    it in the menu does. Returns how many rows were added.
    """
    registry.unregister_prefix(MENU_COMMAND_PREFIX)
    covered = set(covered_ids)
    known_paths = {tuple(plain_menu_text(part) for part in path) for path in covered_paths}
    added = 0
    for path, item in walk_menu_items(menu_bar):
        item_id = item.GetId()
        if item_id in covered or path in known_paths:
            continue
        covered.add(item_id)
        key = binding_for_item(item) if binding_for_item is not None else _label_key(item)
        command_id = f"{MENU_COMMAND_PREFIX}{item_id}"
        if registry.try_register(
            command_id,
            " > ".join(path),
            (lambda i=item_id: post_menu_event(i)),
            keybinding=key,
            feature_id="core.app",
        ):
            added += 1
    return added


def _label_key(item: Any) -> str | None:
    label = item.GetItemLabel()
    if _TAB in label:
        key = label.split(_TAB, 1)[1].strip()
        return key or None
    return None
