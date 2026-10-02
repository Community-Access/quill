"""Simple or Advanced: how much of QUILL Cast's menu bar a listener meets.

Jeff, 2026-09-30: "The multiple backup options and things are confusing, opml,
backups, not that they aren't good, we just have a bit of a UI mess here from a
basic user perspective... Perhaps we should add a View menu and start with basic
features and allow an advanced mode."

**The diagnosis, and it is not "too many features".** Cast's menus are organised
by *machinery*, and Earshot's are organised by *places you go* -- Inbox, Queue,
Subscriptions, Library, Downloads, Stats, Settings (Earshot PRD 5.2). That is why
the Subscriptions menu reads as a mess: Add Podcast, Back Up My Podcasts, Export
My Data, Podcast Index Credentials, Choose Columns and Delete All Podcast Data all
sit in one list, and only the first of them is something a listener does in their
first month. Nothing there is a bad feature. The list is simply not sorted by how
often anybody needs it, so a newcomer reads twenty rows to find the two they came
for -- and a screen-reader user reads them one at a time, out loud.

So: two modes, and the mode decides which rows are *built*.

* **Simple** is the default, and it is not a crippled mode. Everything a listener
  does weekly is in it: follow a podcast, find one, play, queue, Inbox, folders,
  downloads, sleep timer, speed, settings, help. A newcomer should be able to
  learn the whole menu bar in one sitting.
* **Advanced** adds the things you go looking for once you know they exist:
  backups and restore, OPML, data export and deletion, directory credentials,
  column layouts, quick-action editing, chapter analysis, per-surface tools.

**Rows are omitted, not disabled.** A disabled row still costs a screen-reader
user a stop and a sentence, and still has to be explained; the whole point is a
shorter list. The one thing the modes must never do is hide the switch itself, so
View > Advanced Features is present in both and says which mode is in force.

**Nothing is ever hidden that cannot be reached another way.** Every advanced row
is also a command, so the Command Palette and Go To reach all of them in Simple
mode -- which is what makes omitting them safe rather than merely tidy. A feature
you cannot find and cannot reach is gone; a feature you cannot find and can reach
by name is a feature with a shorter menu in front of it.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

__all__ = [
    "ADVANCED",
    "ADVANCED_ROWS",
    "MODES",
    "SIMPLE",
    "mode_label",
    "normalize_mode",
    "shows",
    "switch_announcement",
]

SIMPLE = "simple"
ADVANCED = "advanced"

#: Both, in the order a chooser offers them.
MODES: tuple[tuple[str, str], ...] = (
    (SIMPLE, "Simple -- the everyday menus"),
    (ADVANCED, "Advanced -- everything Cast can do"),
)

#: The rows Simple mode leaves out, each with why it is not an everyday row.
#:
#: Keyed by a short stable name rather than by menu label, because a label is a
#: wording decision that will change and a key is a contract. The comment on each
#: is the review: a row added here has to justify itself, and a row somebody moves
#: out of here has to say why it became everyday.
ADVANCED_ROWS: dict[str, str] = {
    # Two different things that both sound like "keep a copy", which is exactly
    # the confusion reported. Both stay; neither is a first-month action.
    "backup": "Backing up the whole library is something you set up once.",
    "restore": "Restoring is rare and frightening, and belongs beside Back Up.",
    "import_opml": "OPML is how you arrive from another app, not how you use this one.",
    "export_opml": "OPML is for leaving or moving, not for listening.",
    "export_data": "A readable JSON snapshot, for support and for your own records.",
    "delete_all_data": "Irreversible, and nobody's second week needs it in a menu.",
    # Configuration of configuration.
    "directory_credentials": "Only for somebody who wants their own Podcast Index key.",
    "choose_columns": "Worth having, and only once you know what a column is.",
    "quick_actions": "Reordering the row actions presumes you have opinions about them.",
    # Machinery a listener should not have to think about.
    "media_tools": "A diagnostic readout about ffmpeg, not a thing you do.",
    "housekeeping": "Runs itself; the manual row is for when you suspect it has not.",
    "free_space": "Downloads already expire on their own schedule.",
    "get_ffmpeg": "Offered when something actually needs it.",
    "unlock_code": "For a signed code somebody has been sent, and nobody else.",
    # Keyboard Shortcuts and Global Hotkeys were here until 2026-10-01 and
    # left on purpose (qc.md section 8): every key is the listener's, and a
    # keyboard user who cannot find where keys are changed has been told
    # the keyboard is not theirs. Radio and QUILL Lite keep both editors
    # in plain sight; so does Cast.
    "prd": "The product requirements document is for us, not for a listener.",
    # A whole menu, not a row -- the only one the mode hides entirely.
    "quillins": "An extensions menu is a thing you go looking for once you know it exists.",
}


def normalize_mode(value: object) -> str:
    """A stored mode, or :data:`SIMPLE` for anything unrecognised.

    Simple rather than Advanced for a junk value, on the same principle the rest
    of Cast follows: the fallback should be the answer that cannot surprise
    anybody. A hand-edited file that reads as Advanced would silently hand
    somebody twenty extra menu rows they never asked for.
    """
    text = str(value or "").strip().lower()
    return ADVANCED if text == ADVANCED else SIMPLE


def shows(mode: object, row: str) -> bool:
    """Whether *row* is built in *mode*.

    A row this module has never heard of is **shown**, which is the deliberate
    direction: a new menu row added by somebody who did not read this file
    appears for everybody, rather than vanishing from Simple mode with nothing to
    say it had gone. The failure mode of the other default is a feature that
    silently does not exist for most listeners.
    """
    if normalize_mode(mode) == ADVANCED:
        return True
    return row not in ADVANCED_ROWS


def mode_label(mode: object) -> str:
    """What the View menu's check item says about itself."""
    return "Advanced" if normalize_mode(mode) == ADVANCED else "Simple"


def switch_announcement(mode: object) -> str:
    """What to say when the mode changes.

    Spoken, and it has to be: the menu bar is not focused when this is pressed,
    so the thing that changed is something the screen reader will not mention.
    It names the count, because "Advanced features on" does not tell a listener
    whether anything actually happened, and it names where the switch lives, so
    the way back is in the sentence that got them here.
    """
    if normalize_mode(mode) == ADVANCED:
        return (
            f"Advanced features on. {len(ADVANCED_ROWS)} more menu rows, including "
            "backups, OPML and your own directory key. Turn them off again in the "
            "View menu."
        )
    return (
        "Simple menus on. The everyday rows only -- everything else is still "
        "there by name in the Command Palette, and in the View menu when you want "
        "it back."
    )
