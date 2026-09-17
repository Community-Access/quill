"""Which QuillLite commands belong to which switchable area, and what that hides.

Split out of :mod:`quill.core.lite.commands` under GATE-11. The table there is
the menu bar; this is the *other* question about every row -- whether Tools >
Customize Features can take it away -- and the two have different shapes: the
table is one long literal, and this is three small maps plus the tidying that
has to happen once rows start disappearing from it.

Turning an area off removes its commands from the menus, from the keyboard, and
from the Command Palette -- not just from the menus. A key that still fires for
a feature somebody has switched off is the feature not being off.

Two granularities, because that is how the areas actually fall: some are a whole
menu or submenu (Format is rich text; Edit > Lines is the line tools), and some
are a handful of items scattered through menus that stay (printing, bookmarks,
the editor font).

Submenu *titles* need no entry of their own. A submenu whose rows have all gone
is dropped along with the row that names it (see :func:`visible_commands`), so a
title cannot outlive its contents.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.lite.commands import _MENU_ORDER, COMMANDS, SUBMENU_SEP, CommandRow

__all__ = ["COMMAND_AREA", "MENU_AREA", "area_for", "visible_commands"]


# ---------------------------------------------------------------------- #
# Which commands belong to which switchable area
# ---------------------------------------------------------------------- #
#
# Turning an area off in Tools > Customize Features removes its commands from the
# menus, from the keyboard, and from the Command Palette -- not just from the
# menus. A key that still fires for a feature somebody has switched off is the
# feature not being off.
#
# Two granularities, because that is how the areas actually fall: some are a
# whole menu or submenu (Format is rich text; Edit > Lines is the line tools),
# and some are a handful of items scattered through menus that stay (printing,
# bookmarks, the editor font).
#
# Submenu *titles* need no entry of their own. A submenu whose rows have all
# gone is dropped along with the row that names it (see visible_commands), so
# the title cannot outlive its contents.

#: Menus and submenus that belong entirely to one area.
MENU_AREA: dict[str, str] = {
    "F&ormat": "rich_text",
    # Spelled out rather than inherited from the parent: a submenu's rows are
    # looked up by their *own* path, so a submenu left out of this map is a
    # submenu no switch can reach -- which is how Structure survived rich text
    # being turned off, offering to promote headings a plain text document
    # cannot have.
    "F&ormat|Structur&e": "rich_text",
    "F&ormat|&Headings": "rich_text",
    "F&ormat|Line Spacin&g": "rich_text",
    # Not "&Tools" as a whole: since the line work moved to Edit > Lines, what
    # is left directly in Tools is Preferences and Customize Features, which
    # must never be switchable -- switching off the menu that contains the
    # switch is a door that locks from the inside.
    "&Edit|&Lines": "tools",
    "&Tools|&Change Case": "tools",
    "&Edit|Clip&board": "clipboard",
    "&Tools|&Spelling": "spelling",
    "&Edit|Selectio&n": "selection",
    # The half of Find that answers "how many" and "where else". Find, Find
    # Next and Replace are in Edit itself and are not switchable: an editor
    # that cannot find is not a small editor.
    "&Edit|&Matches": "matches",
}

#: Individual handlers whose area is not their menu's.
COMMAND_AREA: dict[str, str] = {
    "cmd_page_setup": "printing",
    "cmd_print": "printing",
    # With the rest of the spelling submenu, which is one switchable area.
    "cmd_misspelling_list": "spelling",
    "cmd_next_heading": "headings",
    "cmd_previous_heading": "headings",
    "cmd_list_headings": "headings",
    "cmd_set_bookmark": "bookmarks",
    "cmd_list_bookmarks": "bookmarks",
    "cmd_next_bookmark": "bookmarks",
    "cmd_previous_bookmark": "bookmarks",
    "cmd_clear_bookmarks": "bookmarks",
    "cmd_set_temp_bookmark": "bookmarks",
    "cmd_go_to_temp_bookmark": "bookmarks",
    "cmd_paste_from_tray": "clipboard",
    "cmd_copy_to_tray": "clipboard",
    "cmd_copy_to_tray_slot": "clipboard",
    "cmd_clear_copy_tray": "clipboard",
    "cmd_collect_selection": "clipboard",
    "cmd_paste_collected": "clipboard",
    "cmd_clear_collected": "clipboard",
    "cmd_remember_clip": "clipboard",
    "cmd_paste_clip": "clipboard",
    # In the Tools menu, but its own area: somebody can keep the tools and drop
    # expansion, or the other way round. The Expand Abbreviations *switch* has
    # no area at all, deliberately -- a switch that disappears with the thing it
    # switches can only ever be moved one way.
    "cmd_manage_abbreviations": "abbreviations",
    # Not the line tools' any more. It sat there because it was the last row
    # left in the old Tools menu, and the Notepad profile is what made the cost
    # visible: encoding and line endings are the two facts that decide whether
    # a file round-trips byte-for-byte, which for a Notepad replacement is most
    # of the job, and they are invisible everywhere else in the app except the
    # status bar that reads them. Losing that dialog along with Sort Lines was
    # never a trade anybody would have chosen. "" is "always present"; see
    # area_for on why the empty string has to be written down.
    "cmd_file_format": "",
    # In the Format menu and *not* rich text: it sets the face the whole editor
    # draws in, plain text included, which is why it is the one item the Format
    # menu keeps when rich text is switched off. "" means always present; the
    # membership test in area_for is what makes an explicit empty string mean
    # "asked and answered" rather than "not listed".
    "cmd_editor_font": "",
    # In the Edit menu and always present. It is not a clipboard *feature*, it
    # is Copy over the whole document, and an editor that cannot copy its own
    # text because somebody switched off the numbered slots would be broken
    # rather than small -- the same argument that keeps Select All in Edit.
    "cmd_copy_all": "",
    "cmd_go_to_anything": "go_to_anything",
    # The Insert menu belongs to no single area, so its rows say so one at a
    # time. The two tag pickers ride with rich_text's opposite number -- they are
    # markup, which is what a *plain* document has instead of formatting -- and
    # the emoji picker is neither: it inserts a character, and a character is
    # available in every document there is.
    "cmd_insert_markdown_tag": "markup",
    "cmd_insert_html_tag": "markup",
    "cmd_set_language": "markup",
    "cmd_insert_emoji": "",
    # Both caret cues are always present. They are the app's answer to something
    # the screen reader cannot do, and each already has its own toggle one
    # keystroke away -- putting them behind a second switch in Customize
    # Features would be two ways to turn off one thing and no way to discover
    # either.
    "cmd_toggle_heading_announcements": "",
    "cmd_toggle_list_announcements": "",
    # Five areas that used to belong to none, which is what "not everything is
    # in the list" meant: each is a real feature somebody may not want, and
    # each was unreachable from the Customize Features dialog because the menu
    # it sits in is not switchable as a whole.
    "cmd_back_location": "history",
    "cmd_forward_location": "history",
    "cmd_command_palette": "command_palette",
    "cmd_describe_character": "character_info",
    "cmd_describe_character_detail": "character_info",
    "cmd_zoom_in": "zoom",
    "cmd_zoom_out": "zoom",
    "cmd_zoom_reset": "zoom",
    # Reading a backup belongs to the same switch that writes them: an area that
    # is off must own nothing, and a browser over a store nothing is writing to
    # would only ever be able to say "no earlier versions".
    "cmd_browse_backups": "backups",
}
COMMAND_AREA.update({f"cmd_set_bookmark_{n}": "bookmarks" for n in range(1, 10)})


def area_for(menu: str, handler: str) -> str:
    """The area a row belongs to, or "" when it is always present.

    Membership rather than truthiness: a handler mapped to ``""`` is saying
    "always present, whatever menu it is in", which is how Editor Font sits in
    the rich-text Format menu without being rich text.
    """
    if handler in COMMAND_AREA:
        return COMMAND_AREA[handler]
    return MENU_AREA.get(menu, "")


def visible_commands(is_enabled: Callable[[str], bool]) -> list[CommandRow]:
    """The table with every switched-off area removed, and tidied afterwards.

    Tidying is the part that is easy to forget and obvious when missing: taking
    rows out leaves separators with nothing between them, separators at the top
    or bottom of a menu, and -- when a whole menu goes -- a menu with nothing in
    it at all. Each of those is a thing a screen reader dutifully reads out.
    """
    kept: list[CommandRow] = []
    for row in COMMANDS:
        menu, _label, _key, handler, kind = row
        if kind not in {"sep", "sub"}:
            area = area_for(menu, handler)
            if area and not is_enabled(area):
                continue
        if kind == "sep" and not is_enabled(MENU_AREA.get(menu, "")) and MENU_AREA.get(menu):
            continue
        kept.append(row)
    # Two passes, because a submenu's title lives in its parent and its rows do
    # not: the first tidy is what decides whether the submenu has anything left,
    # and only then can a title with nothing behind it be dropped -- which may
    # in turn leave the separator that framed it doubled, hence the second.
    tidied = _tidy(kept)
    live = {row[0] for row in tidied}
    pruned = [r for r in tidied if r[4] != "sub" or f"{r[0]}{SUBMENU_SEP}{r[1]}" in live]
    return _tidy(pruned)


def _tidy(rows: list[CommandRow]) -> list[CommandRow]:
    """Drop empty menus, leading and trailing separators, and doubled ones."""
    by_menu: dict[str, list[CommandRow]] = {}
    for row in rows:
        by_menu.setdefault(row[0], []).append(row)
    out: list[CommandRow] = []
    for menu in _MENU_ORDER:
        items = by_menu.get(menu, [])
        cleaned: list[CommandRow] = []
        for row in items:
            if row[4] == "sep" and (not cleaned or cleaned[-1][4] == "sep"):
                continue
            cleaned.append(row)
        while cleaned and cleaned[-1][4] == "sep":
            cleaned.pop()
        if any(row[4] != "sep" for row in cleaned):
            out.extend(cleaned)
    return out
