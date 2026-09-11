"""Every menu item says how to reach it from the keyboard.

The house rule (CLAUDE.md) is that a listener should never have to walk a menu
to discover there is no faster way in: every enabled item shows a keyboard route
in its label. Quill Radio meets it with 115 items and a global chord each. QUILL
has **757**, and 560 of them had no route at all -- which is not a rule anybody
forgot to apply, it is a rule that cannot be applied that way at this size. There
are not 560 chords. QUILL's one-level QUILL-key namespace (``QUILL Key + <key>``)
is already exhausted; the keymap's own comment says so.

But there is a route to every one of them already, and it costs nothing: the
**Alt path**. ``Alt+F`` opens File, ``I`` opens Import, ``W`` picks Word
Document. It is as global as any chord, it needs no binding, it consumes no
chord space, and it scales to any depth and any number of items. All it was
missing was somebody saying it out loud in the label -- so this module says it,
computed from the menu bar rather than written down, which is why it cannot
drift and why every menu item added after today is covered on the day it lands.

Advertised in parentheses rather than after a tab, following the same decision
#612 recorded for QUILL-key chords: wx parses the text after a tab as a native
accelerator (``wxGetAccelFromString``), and "Alt+F, I, W" is not one. Tab-form
would log "Unrecognized accel key" per item at every build and leave the label
advertising an accelerator that does not exist.

**Two things had to be true first, and neither was.**

*One mnemonic, one item, per popup.* An Alt path is only a route if the letters
resolve. QUILL's menu bar had **119 collisions across 30 popups** -- the File
menu alone had three items on N, three on R and three on S -- and Windows
answers a duplicated letter by cycling rather than pressing, so those paths went
nowhere in particular. GATE-14's access-key checker never saw them: it scopes a
``wx.Dialog``/``wx.Frame`` subclass as one window, and QUILL's menu bar is built
across a dozen mixin methods, so each was scoped separately and every collision
fell between them.

Resolved here, in menu order, by two rules:

1. **An item holding a real accelerator keeps its mnemonic.** A command
   important enough for a global chord is important enough to keep its letter.
   This is what makes the pass safe to run automatically: Save keeps S from
   Snapshots, Print keeps P from New Document from Clipboard, Select All keeps A
   from Copy With Attribution, Bold keeps B from Subscript -- every well-known
   letter survives, and it survives for a reason a reader can check rather than
   because somebody listed it.
2. **Otherwise the earlier item keeps it**, and the later one moves to a free
   letter of its own title: a word-initial first, then any letter. If a popup is
   genuinely full, the loser gets **no** mnemonic rather than a duplicate --
   GATE-14's rule, because a duplicate advertises a key that may not work while
   silence is merely silent.

*Every item has a mnemonic at all.* **166 had none** -- the fonts, the point
sizes, the colours, the 32 braille translation languages, the AI agents. Those
are rows of data rather than commands, which is why nobody wrote a mnemonic for
them, but a row you cannot type a letter at is a row you have to arrow to. They
are assigned the same way as any moved mnemonic.
"""

from __future__ import annotations

import re
from typing import Any, NamedTuple

#: Letters a mnemonic may use. Digits included: the Copy Tray's slots are 1-9
#: and 0, and those are the letters a hand reaches for there.
_CANDIDATES = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

#: A route already advertised in the label -- "(QUILL Key + S)", "(Alt+F, I, W)".
#: Its presence means this item is already answered, and makes the pass
#: idempotent if a menu is rebuilt in place.
_ROUTE_SUFFIX = re.compile(r"\s*\((?:QUILL Key|Alt|Ctrl|Cmd|Shift)[^()]*\)\s*$")

_TAB = "\t"


class RouteReport(NamedTuple):
    """What the pass did, for the gate and for anyone debugging a label."""

    routed: int
    mnemonics_assigned: int
    mnemonics_moved: int
    unroutable: tuple[str, ...]


def split_label(label: str) -> tuple[str, str]:
    """``("Save &As...", "Ctrl+Shift+S")`` -- the title and the accelerator."""
    if _TAB in label:
        title, accel = label.split(_TAB, 1)
        return title, accel.strip()
    return label, ""


def mnemonic_of(title: str) -> str:
    """The item's mnemonic letter, or ``""``. ``&&`` is a literal ampersand."""
    index = 0
    while True:
        index = title.find("&", index)
        if index < 0 or index + 1 >= len(title):
            return ""
        if title[index + 1] == "&":
            index += 2
            continue
        return title[index + 1].upper()


def strip_mnemonic(title: str) -> str:
    """Remove the mnemonic marker, leaving ``&&`` alone."""
    out: list[str] = []
    index = 0
    while index < len(title):
        char = title[index]
        if char == "&" and index + 1 < len(title) and title[index + 1] == "&":
            out.append("&&")
            index += 2
            continue
        if char == "&":
            index += 1
            continue
        out.append(char)
        index += 1
    return "".join(out)


def with_mnemonic(title: str, letter: str) -> str:
    """Mark *letter* as the mnemonic, adding it to the title if it is not there.

    A mnemonic has to be a character of the label, and in a menu as full as
    QUILL's File menu the free letters and the letters of a given title stop
    overlapping -- nine items, and the whole *Open from Remote* subtree behind
    one of them, had no seat left in their own names. Windows has a convention
    for exactly this, borrowed from CJK localisation: put the letter in
    parentheses at the end, ``Print Studio... (&Z)``. Where the item also gets
    an Alt path, the two merge into one parenthetical rather than two --
    ``Print Studio... (Alt+F, &Z)`` -- so the label gains a route, not clutter.
    """
    plain = strip_mnemonic(title)
    target = letter.lower()
    limit = len(plain)
    match = _ROUTE_SUFFIX.search(plain)
    if match:
        limit = match.start()
    for position, char in enumerate(plain.lower()[:limit]):
        if char == target:
            return plain[:position] + "&" + plain[position:]
    return f"{plain} (&{letter.upper()})"


def _preferred_letters(title: str) -> list[str]:
    """Letters to try for a new mnemonic: word-initials first, then the rest.

    Word-initials because "Times New Roman" wants T, N or R long before it wants
    the M in Roman -- a mnemonic a reader can guess is worth more than one that
    merely exists.
    """
    plain = strip_mnemonic(_ROUTE_SUFFIX.sub("", title)).replace("&&", " ")
    initials = [word[0].upper() for word in re.split(r"[^0-9A-Za-z]+", plain) if word]
    rest = [char.upper() for char in plain if char.isalnum()]
    seen: set[str] = set()
    ordered: list[str] = []
    for letter in [*initials, *rest]:
        if letter in _CANDIDATES and letter not in seen:
            seen.add(letter)
            ordered.append(letter)
    return ordered


def _items(menu: Any) -> list[Any]:
    return [item for item in menu.GetMenuItems() if not item.IsSeparator()]


def _match(
    candidates: dict[int, list[str]], taken: set[str], order: list[int] | None = None
) -> dict[int, str]:
    """Seat as many items as possible on distinct letters (Kuhn's algorithm).

    Greedy first-fit is not enough in a menu this full. QUILL's File menu has
    around thirty direct items whose titles between them offer barely more
    letters than that, and taking each item's first free letter in turn stranded
    nine of them -- including *Open from Remote*, whose whole submenu then had
    no path to state. A maximum matching seats them because it is willing to
    move an earlier item to its second choice to free a letter that is some
    later item's only one.
    """
    seated: dict[str, int] = {}
    for letter in taken:
        seated[letter] = -1

    def seat(index: int, seen: set[str]) -> bool:
        for letter in candidates[index]:
            if letter in seen:
                continue
            seen.add(letter)
            holder = seated.get(letter)
            if holder is None or (holder >= 0 and seat(holder, seen)):
                seated[letter] = index
                return True
        return False

    # Kuhn's seats as many as it can whatever the order, but when a popup holds
    # more items than there are letters -- QUILL's Format menu has forty and the
    # alphabet plus the digits gives thirty-six -- the order decides *who* goes
    # without. Submenus first: a parent's letter is the first step of the path
    # for everything inside it, so one unseated parent costs a subtree.
    for index in order or sorted(candidates):
        if index in candidates:
            seat(index, set())
    return {index: letter for letter, index in seated.items() if index >= 0}


def _resolve_popup(menu: Any, report: dict[str, int]) -> None:
    """Give every item in one popup a mnemonic no sibling else holds."""
    entries = []
    for item in _items(menu):
        title, accel = split_label(item.GetItemLabel())
        entries.append((item, title, accel, mnemonic_of(title), item.GetSubMenu() is not None))

    taken: set[str] = set()
    keep: dict[int, str] = {}

    def claim(index: int, letter: str) -> None:
        taken.add(letter)
        keep[index] = letter

    # Round one: an item holding a real accelerator keeps its letter. A command
    # worth a global chord is worth its mnemonic, and this is what lets the pass
    # run unattended -- Save keeps S from Snapshots, Print keeps P, Bold keeps B.
    for index, (_i, _t, accel, letter, _sub) in enumerate(entries):
        if accel and letter and letter not in taken:
            claim(index, letter)
    # Round two: a submenu keeps its letter next. Its mnemonic is the first step
    # of the path for everything inside it, so losing it costs a whole subtree,
    # not one row.
    for index, (_i, _t, _a, letter, has_submenu) in enumerate(entries):
        if has_submenu and letter and index not in keep and letter not in taken:
            claim(index, letter)
    # Round three: in menu order, everyone else keeps theirs if it is still free.
    for index, (_i, _t, _a, letter, _sub) in enumerate(entries):
        if index in keep or not letter or letter in taken:
            continue
        claim(index, letter)
    # Round four: seat the rest, together, on the letters that are left. Their
    # own title's letters come first so the mnemonic is guessable; the rest of
    # the alphabet follows, because a letter the title does not contain can
    # still be given to it (see :func:`with_mnemonic`) and a seat somebody can
    # reach beats a name that reads better.
    unseated = {
        index: [c for c in [*_preferred_letters(entries[index][1]), *_CANDIDATES] if c not in taken]
        for index in range(len(entries))
        if index not in keep
    }
    order = sorted(
        unseated,
        key=lambda index: (
            0 if entries[index][4] else 1 if not entries[index][2] else 2,
            index,
        ),
    )
    keep.update(_match(unseated, taken, order))

    for index, (item, title, accel, letter, _sub) in enumerate(entries):
        chosen = keep.get(index, "")
        if chosen == letter:
            continue
        if not chosen:
            # A full popup: no mnemonic beats a duplicate (GATE-14's rule).
            report["moved"] += 1
            _set_title(item, strip_mnemonic(title), accel)
            continue
        report["moved" if letter else "assigned"] += 1
        _set_title(item, with_mnemonic(title, chosen), accel)


def _set_title(item: Any, title: str, accel: str) -> None:
    item.SetItemLabel(f"{title}{_TAB}{accel}" if accel else title)


def _walk_menus(menu: Any, report: dict[str, int]) -> None:
    _resolve_popup(menu, report)
    for item in _items(menu):
        submenu = item.GetSubMenu()
        if submenu is not None:
            _walk_menus(submenu, report)


def _route_text(keys: list[str]) -> str:
    """``["F", "I", "W"]`` -> ``"Alt+F, I, W"``. Alt opens the menu bar; after
    that the menu is open and the letters are bare."""
    return "Alt+" + keys[0] + "".join(f", {key}" for key in keys[1:])


#: A mnemonic :func:`with_mnemonic` had to append because the title had no free
#: letter of its own. It is folded into the Alt path rather than left standing.
_APPENDED_MNEMONIC = re.compile(r"\s*\(&([0-9A-Za-z])\)\s*$")


def _with_route(title: str, keys: list[str]) -> str:
    """``"Word Document..."`` -> ``"Word Document... (Alt+F, I, W)"``."""
    route = _route_text(keys)
    match = _APPENDED_MNEMONIC.search(title)
    if not match:
        return f"{title} ({route})"
    # One parenthetical, not two: the appended letter becomes the marked letter
    # of the path it is the last step of.
    marked = route[: route.rfind(keys[-1])] + "&" + keys[-1]
    return f"{title[: match.start()]} ({marked})"


def _apply_routes(menu: Any, keys: list[str], report: dict[str, Any]) -> None:
    for item in _items(menu):
        title, accel = split_label(item.GetItemLabel())
        letter = mnemonic_of(title)
        submenu = item.GetSubMenu()
        if submenu is not None:
            if letter and keys and _APPENDED_MNEMONIC.search(title):
                # Never leave a bare "(&Z)" standing: a submenu that had to be
                # given a letter says what the letter is *for*.
                _set_title(item, _with_route(title, [*keys, letter]), accel)
                report["routed"] += 1
            _apply_routes(submenu, [*keys, letter] if letter else [], report)
            continue
        if accel or not item.IsEnabled() or _ROUTE_SUFFIX.search(title):
            continue
        if not keys or not letter:
            # No path to state. A disabled row is exempt; an enabled one is a
            # gap, and the gate names it rather than this pass papering over it.
            report["unroutable"].append(strip_mnemonic(title))
            continue
        _set_title(item, _with_route(title, [*keys, letter]), accel)
        report["routed"] += 1


def reapply_menu_routes(frame: Any) -> RouteReport | None:
    """Re-run the pass over *frame*'s current menu bar. ``None`` if it has none.

    The entry point for a menu that is rebuilt *outside* the menu-bar build:
    Open Recent, the podcast submenu, and the contextual rows that are enabled
    and disabled as the document changes. A rebuilt submenu loses its routes
    silently, and an item that was disabled when the pass last ran was skipped
    on purpose -- so both need the pass again once they have settled.

    The whole bar rather than the one menu: the pass is idempotent by
    construction (an item already advertising a route is left alone), so the
    extra walk costs a traversal and buys never having to decide, at each call
    site, which subtree the change could have reached.
    """
    get_menu_bar = getattr(frame, "GetMenuBar", None)
    if not callable(get_menu_bar):
        return None
    menu_bar = get_menu_bar()
    if menu_bar is None:
        return None
    return apply_menu_routes(menu_bar)


def apply_menu_routes(menu_bar: Any) -> RouteReport:
    """Resolve every mnemonic, then give every keyless item its Alt path.

    Call once, at the end of a menu-bar build. Safe to call again: an item that
    already advertises a route is left exactly as it is.
    """
    report: dict[str, Any] = {"routed": 0, "assigned": 0, "moved": 0, "unroutable": []}

    # The menu bar is a popup of its own: its top-level titles compete for Alt
    # letters with each other and with nothing else.
    taken: set[str] = set()
    for index in range(menu_bar.GetMenuCount()):
        title = menu_bar.GetMenuLabel(index)
        letter = mnemonic_of(title)
        if letter and letter not in taken:
            taken.add(letter)
            continue
        chosen = next((c for c in _preferred_letters(title) if c not in taken), "")
        if not chosen:
            continue
        taken.add(chosen)
        report["moved" if letter else "assigned"] += 1
        menu_bar.SetMenuLabel(index, with_mnemonic(title, chosen))

    for index in range(menu_bar.GetMenuCount()):
        _walk_menus(menu_bar.GetMenu(index), report)

    for index in range(menu_bar.GetMenuCount()):
        letter = mnemonic_of(menu_bar.GetMenuLabel(index))
        _apply_routes(menu_bar.GetMenu(index), [letter] if letter else [], report)

    return RouteReport(
        routed=report["routed"],
        mnemonics_assigned=report["assigned"],
        mnemonics_moved=report["moved"],
        unroutable=tuple(report["unroutable"]),
    )
