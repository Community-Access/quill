"""What every Quill Media Player window is *for* -- F1's opening paragraph.

Quill Radio authored the first catalogue (:mod:`quill.core.radio.surface_help`,
2026-08-23) and QUILL Cast the second (:mod:`quill.core.podcasts.surface_help`,
2026-08-24); the F1 engine has been family-wide since the first day, so the
Media Player answered F1 everywhere -- but with the generic sentence for every
surface, which is true and useless. This module is the Media Player's half:
the wx-free catalogue of surface purposes keyed by window title, composed by
:mod:`quill.ui.app_context_help` exactly as the other two are.

Keyed by **window title** for the same reasons the others are: the title is
the one identity a window already announces, and it is what a person quotes
back in a bug report.

The catalogue is **gated** (GATE-PLAYER-HELP,
``quill/tools/player_help_audit.py``): every ``wx.Frame``/``wx.Dialog`` title
constructed in the media UI must resolve here, so a new surface cannot ship
without saying what it is for.

Wording rules, unchanged from Radio's, so the entries stay worth reading:

* One to three sentences. The first says what the window is for; the rest say
  what somebody actually does here or the one fact that saves a support email.
* Address the listener ("your book"), never the developer.
* No key-by-key tours -- the control section below the purpose covers the
  control under focus.
"""

from __future__ import annotations

# Re-exported so the Media Player's help code and tests need one import,
# matching Radio and Cast.
from quill.core.control_help import (
    compose_control_body as compose_control_body,
)
from quill.core.control_help import (
    role_usage as role_usage,
)

#: Surface purposes by exact window title.
PURPOSES: dict[str, str] = {
    # -- the windows -------------------------------------------------------------
    "Quill Media Player": (
        "The main window: what is playing, the transport, and three pages "
        "under it -- Chapters, Bookmarks, and the Audio equalizer. Open a "
        "file, a folder, a DAISY book, or a free LibriVox title; your place "
        "is saved as you listen, so a book resumes where you left it. "
        "Nothing here needs an account, and playback stays on this computer."
    ),
    "Mini Player": (
        "A small always-on-top window carrying just the transport -- "
        "Play/Pause and the chapter moves -- so the book stays in reach "
        "while you work somewhere else. It drives the same playback session "
        "as the main window; there is no second audio stream, and closing "
        "it stops nothing."
    ),
    # -- the dialogs -------------------------------------------------------------
    "Go to Position": (
        "Jump to an exact place in the open file. Give it hours, minutes "
        "and seconds, or type a single timecode such as 1:23:45 -- a typed "
        "timecode wins over the three fields. A position beyond the end is "
        "moved back to the end and announced, never refused."
    ),
    "Book Library": (
        "Search LibriVox, the free public-domain audiobook catalog, and "
        "choose a book. Type a title, press Search, pick a result, and Play "
        "streams the book's sections here in order. No account is involved "
        "and nothing is saved to disk."
    ),
    "Player Information": (
        "What is playing, as one read-only report: title, position, chapter "
        "and the engine behind it. Arrow through it as many times as you "
        "like at your own pace -- reviewing it never touches playback -- "
        "and Copy takes the whole report to the clipboard."
    ),
    "Voice Command": (
        "Say or type one natural command -- 'skip back thirty', 'next "
        "chapter', 'go to 1:20:00', 'bookmark this', 'sleep in twenty' -- "
        "and OK carries it out. The same grammar answers the hands-free "
        "Listen for a Command toggle; this field is the way to use it "
        "without a microphone."
    ),
    "Jump to File": (
        "Type any part of a track's title and the first track that matches "
        "starts playing. It searches the open book's own track list, "
        "nothing on disk."
    ),
    "Add Bookmark": (
        "A note to keep with the bookmark being added at the current "
        "position. The note is what the Bookmarks list shows for this "
        "bookmark, and what is read aloud when playback reaches it again."
    ),
    "Edit Bookmark": (
        "Change the note on the highlighted bookmark. Only the words "
        "change -- the bookmark keeps its position."
    ),
    "Quick Actions": (
        "Decide what pressing Enter on a row does, and the order of the "
        "row's right-click menu. The first action in each list is the "
        "default and the whole list is rearranged by position -- Move Up, "
        "Move Down, Make Default -- never by checkbox. Cancel leaves every "
        "list as it was."
    ),
    "Choose Columns": (
        "Decide what a row of the chosen list says, and in what order. A "
        "row is read out one column at a time, so hiding a column removes "
        "it from every spoken row, and the preview line reads exactly what "
        "one row will say. Cancel leaves every list as it was."
    ),
}

#: Purposes for windows whose titles carry live data, matched by prefix.
PREFIX_PURPOSES: tuple[tuple[str, str], ...] = (
    (
        "Help:",
        "This is the help window itself: the purpose of the window you were "
        "in, then the control you were on. Escape returns you to it.",
    ),
)

#: The honest fallback for a surface the catalogue does not know. The gate
#: keeps this from being reachable from any surface in the media tree; it
#: exists so a brand-new window still answers F1 with something true rather
#: than nothing.
GENERIC_PURPOSE: str = (
    "A Quill Media Player window. Tab moves between its controls, Escape "
    "closes it, and F1 on any control explains that control."
)


def purpose_for_title(title: str) -> str:
    """The purpose paragraph for a window titled *title* (never empty)."""
    stripped = title.strip()
    exact = PURPOSES.get(stripped)
    if exact:
        return exact
    for prefix, purpose in PREFIX_PURPOSES:
        if stripped.startswith(prefix):
            return purpose
    return GENERIC_PURPOSE


def is_known_title(title: str) -> bool:
    """True when *title* resolves to an authored purpose (the gate's check)."""
    stripped = title.strip()
    if stripped in PURPOSES:
        return True
    return any(stripped.startswith(prefix) for prefix, _p in PREFIX_PURPOSES)
