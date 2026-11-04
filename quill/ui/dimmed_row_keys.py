"""A dimmed menu row's key still reaches something that says why it did nothing.

Reported against QUILL Lite on 2026-11-02: in a blank document, "issuing commands
produces no feedback at all". A new document is plain text, and a plain text
document dims the Format rows and the markup rows -- Bold, the six headings,
alignment, the section moves -- because none of them can do anything there.
Dimming a row is right for somebody walking the menu: the reader says
"unavailable" and moves on. It is wrong for the *key*. Windows does not deliver
an accelerator whose menu item is disabled, and wx drops the command of a
disabled item too, so Ctrl+B in a blank document did nothing and nothing said
why -- which a listener cannot tell apart from a broken key or a hung program.
The owner's rule is that a command is never silent.

The cure keeps the row dimmed and gives its key a second, menu-less id. No menu
carries that id, so nothing can be disabled about it, and its handler is the
caller's choice: QUILL Lite runs the command itself, whose own refusal ("This
document has no formatting...") is already written; QUILL says a sentence of
its own, because some of its dimmed commands would otherwise act.

Takes the wx module and the window rather than importing wx, like
:mod:`quill.ui.markdown_tag_row`, so it costs nothing where wx is not wanted.
"""

from __future__ import annotations

from collections.abc import Callable, Hashable, Iterable, Mapping
from typing import Any

__all__ = ["DimmedRowKeys", "routed_entries"]


def _key_of(entry: Any) -> tuple[int, int]:
    return int(entry.GetFlags()), int(entry.GetKeyCode())


def routed_entries(
    wx_module: Any,
    base: Iterable[Any],
    dimmed: Mapping[int, Any],
    shadow_for: Callable[[int], int],
) -> list[Any]:
    """*base*, with every key of a dimmed row pointed at that row's shadow id.

    *dimmed* maps a dimmed row's menu id to the row itself. A key in *base* that
    names a dimmed id (a shipped alias, or every key in QUILL's table) is moved;
    the row's own label key, which lives in the menu bar's table rather than the
    window's, is added. The window's table is consulted first, so the moved key
    wins over the menu bar's dead copy of it.
    """
    entries: list[Any] = []
    taken: set[tuple[int, int]] = set()
    for entry in base:
        command = int(entry.GetCommand())
        if command in dimmed:
            command = shadow_for(command)
        entries.append(wx_module.AcceleratorEntry(entry.GetFlags(), entry.GetKeyCode(), command))
        taken.add(_key_of(entry))
    for item_id, item in dimmed.items():
        get_accel = getattr(item, "GetAccel", None)
        accel = get_accel() if callable(get_accel) else None
        if accel is None or not accel.GetKeyCode() or _key_of(accel) in taken:
            continue
        entries.append(
            wx_module.AcceleratorEntry(accel.GetFlags(), accel.GetKeyCode(), shadow_for(item_id))
        )
        taken.add(_key_of(accel))
    return entries


class DimmedRowKeys:
    """One window's accelerator table, with its dimmed rows' keys kept alive.

    *run* takes the stable name of a row (QUILL Lite's handler name, QUILL's menu
    id) and returns the ``EVT_MENU`` handler its key should reach while the row
    is dimmed. The shadow id is made and bound once per name, so a menu bar that
    is rebuilt -- new item ids every time -- does not stack up bindings.
    """

    def __init__(
        self, wx_module: Any, window: Any, run: Callable[[Hashable], Callable[[Any], None]]
    ) -> None:
        self._wx = wx_module
        self._window = window
        self._run = run
        self._shadows: dict[Hashable, int] = {}
        #: The id refs themselves: wx frees an id when its last ref goes.
        self._refs: list[Any] = []
        self._base: list[Any] = []
        self._applied: tuple[int, ...] | None = None

    def shadow_id(self, name: Hashable) -> int:
        shadow = self._shadows.get(name)
        if shadow is None:
            ref = self._wx.NewIdRef()
            self._refs.append(ref)
            shadow = int(ref.GetId())
            self._window.Bind(self._wx.EVT_MENU, self._run(name), id=shadow)
            self._shadows[name] = shadow
        return shadow

    def set_base(self, entries: Iterable[Any]) -> None:
        """The table the window would have with nothing dimmed."""
        self._base = list(entries)
        self._applied = None

    def apply(self, dimmed: Mapping[Hashable, Any]) -> None:
        """Install the table for the rows in *dimmed* (``{name: wx.MenuItem}``).

        Skipped when neither the base nor the dimmed set moved since last time:
        the sweep that calls this runs on every caret-free state change, and
        rebuilding an accelerator table there is churn for nothing.
        """
        by_id = {int(item.GetId()): (name, item) for name, item in dimmed.items()}
        signature = tuple(sorted(by_id))
        if signature == self._applied:
            return
        entries = routed_entries(
            self._wx,
            self._base,
            {item_id: item for item_id, (_name, item) in by_id.items()},
            lambda item_id: self.shadow_id(by_id[item_id][0]),
        )
        self._window.SetAcceleratorTable(self._wx.AcceleratorTable(entries))
        self._applied = signature
