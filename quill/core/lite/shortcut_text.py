"""QUILL Lite's Keyboard Shortcuts text, generated from the command table.

Moved out of :mod:`quill.core.lite.commands` on 2026-11-07 (GATE-11) when the
Studio launch row took that module over its ceiling. It reads the table through
:func:`quill.core.lite.command_areas.visible_commands`, so a command the release
gate hides (Open QUILL Studio, before Studio ships) is not listed either.
"""

from __future__ import annotations

from quill.core.lite import APP_NAME, APP_VERSION
from quill.core.lite.command_areas import visible_commands
from quill.core.lite.commands import SUBMENU_SEP, _plain, split_menu

__all__ = ["shortcut_text"]


def shortcut_text(keymap: dict[str, str] | None = None) -> str:
    """The Keyboard Shortcuts window's body, generated from the same table.

    *keymap* is the resolved binding per handler
    (:func:`quill.core.lite.keymap.load_keymap`). Passing None gives the shipped
    keys, which is what a test that predates rebinding is asking for -- but the
    app always passes its own, because a shortcut list that shows the key a
    command *used* to have is the one surface where a wrong key gets learned.

    Two things are appended that the table cannot carry: the Alt+digit window
    switches (built per window, from however many are open) and the heading
    ladder, which is the one fact about rich mode that saves a support email.
    """
    lines = [f"{APP_NAME} {APP_VERSION} keyboard shortcuts", ""]
    current = ""
    for menu, label, default_key, handler, kind in visible_commands(lambda _area: True):
        key = (keymap or {}).get(handler, default_key)
        # A submenu's title row is not a shortcut; the submenu gets its own
        # heading below, from the rows that carry the keys.
        if kind in {"sep", "sub"}:
            continue
        if menu != current:
            current = menu
            parent, child = split_menu(menu)
            lines.append("")
            lines.append(
                f"{_plain(parent)} menu, {_plain(child).replace(SUBMENU_SEP, ' > ')} submenu"
                if child
                else f"{_plain(parent)} menu"
            )
        lines.append(f"  {key}: {_plain(label)}" if key else f"  No key: {_plain(label)}")
    lines += [
        "",
        "Window menu",
        "  Alt+1 to Alt+9: switch to that open window",
        "",
        "File menu, Open Recent",
        "  Alt+Shift+1 to Alt+Shift+8: reopen that recent file",
        "",
        "Status bar (F6)",
        "  Left and Right, Home and End: move between cells",
        "  Enter: act on the cell -- go to a line, switch mode, list headings, save",
        "  Escape: back to the document",
        "",
        "Headings in rich text are bold plus a point size: 20, 16, 14, 12, 11.5",
        "and 10.5 point for levels 1 to 6, and 11 point for body text. That is",
        "QUILL's own ladder, so a document saved here reads as headings in Word.",
    ]
    return "\n".join(lines)
