"""Every key this app answers to, in one list you can read without leaving it.

WHY THIS EXISTS
---------------
Quill Radio 3.0 made every menu item name its own key -- all 115 of them --
which fixed the discovery problem *while you are in a menu*. It did nothing for
the question people actually ask, which is "what can I press?", because
answering it still meant opening six menus and arrowing to the end of each.

The documentation route is worse, not better: the User Guide lists the
defaults, and a listener who rebound anything is then reading a document that
describes somebody else's keyboard.

WHERE THE ROWS COME FROM, AND WHY IT IS THE MENU BAR
-----------------------------------------------------
This does not read the keymap. It reads **the menu bar the listener is looking
at**, which is a stronger source for three reasons:

* it is what is actually bound, including the items whose keys are literals
  rather than keymap entries (F1, Shift+F1, the Recently Played rows);
* it cannot drift, because it is the same text the menus speak -- there is no
  second copy to keep in step, which is the failure mode that put a stale
  shortcut list in every manual ever written;
* the menu-accelerator gate already guarantees every enabled item carries a
  key and that no two items share one, so the list is complete and unambiguous
  by construction rather than by hope.

KEYS THAT ARE NOT ON A MENU
---------------------------
A few real keys have no menu item to carry them -- F6 into the status strip,
the Winamp transport letters in the Recordings player, Escape's various
returns. They are listed here as data, and marked with the surface they work
in, because "where does this key work?" is the first thing you need to know
about a key that only works in one window. This is the one part of the sheet
that *is* a second copy, and it is deliberately tiny.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Rows for keys with no menu item. Each is (surface, key, what it does).
#: Kept short on purpose: every entry here is a hand-maintained copy of
#: something, and the cost of a wrong row is somebody pressing a key that does
#: nothing and concluding the app is broken.
OFF_MENU_KEYS: tuple[tuple[str, str, str], ...] = (
    ("Main window", "F6", "Move into the status bar; Escape hands focus back"),
    ("Status bar", "Left and Right", "Move cell to cell; Home and End jump to the ends"),
    ("Status bar", "Enter", "Act on the cell you are on"),
    ("Recordings", "X", "Play the selected recording, or resume a paused one"),
    ("Recordings", "C", "Pause or unpause"),
    ("Recordings", "V", "Stop"),
    ("Recordings", "B", "Next recording"),
    ("Recordings", "Z", "Previous recording"),
    ("Recordings", "R", "Shuffle on or off"),
    ("Recordings", "S", "Repeat: off, all recordings, this recording"),
    ("Recordings", "T", "Elapsed time, or time remaining"),
    ("Recordings", "J", "Jump to a recording by name"),
    ("Recordings", "Ctrl+J", "Jump to a time"),
    ("Browse Stations", "Ctrl+F", "Jump to the Find box from anywhere in the window"),
    ("Browse Stations", "Shift+F10", "All actions for the row you are on"),
    ("Any list", "Applications key", "The same actions as Shift+F10"),
)


@dataclass(frozen=True, slots=True)
class CheatRow:
    """One key and what it does, with the place it belongs to."""

    #: The menu it lives on ("Playback"), or the surface it works in
    #: ("Recordings") for a key with no menu item.
    group: str
    #: The command, with wx's mnemonic ampersands and any trailing "..." gone.
    action: str
    key: str

    def spoken(self) -> str:
        """The whole row as one sentence, the way the house ListBox reads.

        The action leads and the key follows, because somebody scanning this
        list is looking for a *thing they want to do*. A list led by keys would
        be sorted by an answer to a question nobody asked first.
        """
        return f"{self.group}: {self.action} -- {self.key}"


def clean_label(label: str) -> str:
    """A menu label as a person would say it.

    wx labels carry an ampersand marking the mnemonic letter (``&Play``), a tab
    and the accelerator, and often a trailing ellipsis meaning "this opens a
    window". None of that belongs in a sentence read aloud, and a doubled
    ``&&`` is a literal ampersand that must survive.
    """
    text = label.split("\t", 1)[0]
    text = text.replace("&&", "\x00").replace("&", "").replace("\x00", "&")
    return text.strip().rstrip(".").strip()


def rows_from_menu_items(items: list[tuple[str, str]]) -> list[CheatRow]:
    """Build rows from ``(menu title, item label)`` pairs off the live menu bar.

    Items with no accelerator are dropped rather than listed as blank: the gate
    means an *enabled* item always has one, so anything without a key here is a
    disabled status readout, which is exactly the thing a cheat sheet should
    not offer as something to press.
    """
    rows: list[CheatRow] = []
    for menu_title, label in items:
        if "\t" not in label:
            continue
        action, key = label.split("\t", 1)
        key = key.strip()
        if not key:
            continue
        rows.append(CheatRow(group=clean_label(menu_title), action=clean_label(action), key=key))
    return rows


def off_menu_rows() -> list[CheatRow]:
    """The hand-kept rows for keys with no menu item."""
    return [CheatRow(group=group, action=action, key=key) for group, key, action in OFF_MENU_KEYS]


def build_sheet(menu_items: list[tuple[str, str]]) -> list[CheatRow]:
    """The whole sheet: menu keys first, then the ones with no menu item.

    Menu order is kept rather than sorted alphabetically. The menus are already
    grouped by what things *are* -- everything about playing is on Playback --
    and re-sorting by name would scatter that into an index, which is a worse
    object to arrow through when you do not yet know the name of the thing you
    want.
    """
    return [*rows_from_menu_items(menu_items), *off_menu_rows()]


def filter_rows(rows: list[CheatRow], query: str) -> list[CheatRow]:
    """Rows matching *query* across all three fields, or every row when empty.

    Matching the key as well as the action is the point: "what is Ctrl+B?" is
    as common a question as "how do I browse?", and a sheet that could only be
    searched one way would answer half of them.
    """
    text = query.strip().casefold()
    if not text:
        return list(rows)
    return [
        row
        for row in rows
        if text in row.action.casefold()
        or text in row.key.casefold()
        or text in row.group.casefold()
    ]


def summary(rows: list[CheatRow], total: int) -> str:
    """The line above the list, which says whether a filter is hiding anything.

    A filtered list that does not say it is filtered is how somebody concludes
    a key does not exist when it is simply not matching what they typed.
    """
    if not rows:
        return "No keys match. Clear the box to see all of them."
    if len(rows) == total:
        return f"{total} keys."
    return f"{len(rows)} of {total} keys."
