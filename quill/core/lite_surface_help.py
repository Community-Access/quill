"""What every QuillLite window is *for* -- the F1 help's opening paragraph.

Every app in the family answers F1 the same way: what this window is for, then
what the control you are on does. The engine is shared
(:mod:`quill.ui.app_context_help` + :mod:`quill.core.control_help`); this module
is QuillLite's half of it, the wx-free catalogue of window purposes, keyed by
window title exactly as Radio's, Cast's, Converter's and Inkwell's are.

Keyed by **title** for the reason the siblings are: the title is the one
identity a window already announces, and it is what somebody quotes back in a
bug report. QuillLite adds one wrinkle none of the siblings have -- its main
window is titled after the *document*, not after the app ("3: Notes.txt -
QuillLite (plain text)"), because the number and the file name are what a
listener needs from the one string a reader announces on arrival. So the
document window is matched by the ``" - QuillLite"`` that every one of those
titles contains, and the fixed windows are matched exactly.

The catalogue is **gated** (GATE-LITE-HELP,
:mod:`quill.tools.lite_help_audit`): every ``wx.Frame`` / ``wx.Dialog`` title
constructed in QuillLite's modules must resolve here, so a new surface cannot
ship without saying what it is for.

Wording rules, unchanged from Radio's, so the entries stay worth hearing:

* One to three sentences. The first says what the window is for; the rest say
  what somebody actually does here, or the one fact that saves a support email.
* Address the listener ("your document"), never the developer.
* No key-by-key tours. The control section below the purpose covers the control
  under focus, the menus advertise their own keys, and Ctrl+F1 lists them all.
"""

from __future__ import annotations

__all__ = [
    "CONTAINS_PURPOSES",
    "GENERIC_PURPOSE",
    "PREFIX_PURPOSES",
    "PURPOSES",
    "is_known_title",
    "purpose_for_title",
]

#: Surface purposes by exact window title.
PURPOSES: dict[str, str] = {
    "QuillLite": (
        "Your document. This is the whole editor: type, and Control S saves. The "
        "title bar leads with this document's number, then its name, whether it "
        "is plain text or rich text, and whether there is anything unsaved. "
        "Control N opens another document beside this one, numbered; Alt+1 to "
        "Alt+9 go straight to one, Control Tab and Control F6 move to the next, "
        "and the Window menu lists them all. Documents live inside one QuillLite "
        "window, so Alt+Tab will not step between them -- those four are how you "
        "move. Press F6 for the status bar, which carries the position, the word "
        "count, the encoding and the line endings."
    ),
    "Find": (
        "Find text in this document. Enter finds the next match and Shift Enter "
        "the previous one; the search wraps around the end and says so when it "
        "does. The window stays open while you work, so F3 and Shift F3 keep "
        "moving through the matches after you have gone back to the text."
    ),
    "Replace": (
        "Find text and put something else in its place. Replace changes the match "
        "you are on and moves to the next; Replace All changes every one and tells "
        "you how many. In a rich text document Replace All asks first, because "
        "replaced text takes the formatting of the run it lands in."
    ),
    "Go to line": (
        "Jump straight to a line by number. The prompt says how many lines the "
        "document has, and a number past the end takes you to the last line "
        "rather than refusing."
    ),
    "Headings": (
        "Every heading in this document, in the order they appear. Choose one and "
        "the cursor lands at the start of it. Headings exist in rich text only: "
        "they are the bold-plus-point-size ladder QUILL uses, so this list is "
        "also what Word will show in its navigation pane."
    ),
    "Preferences": (
        "Every setting QuillLite has, in one window. Two of them live only here: "
        "what Control N creates, and how often unsaved work is copied aside. The "
        "rest -- theme, word wrap, and the editor font -- are also on the View "
        "menu, where you will reach them faster."
    ),
    "File format": (
        "How this document will be written back to disk: which character "
        "encoding, and which line endings. QuillLite normally writes back "
        "exactly what it read, so these only change when you change them here -- "
        "and the change happens at the next save, not now."
    ),
    "Bookmarks": (
        "The places you marked in this document, in the order they appear. "
        "Choose one and press Enter to go there; Remove takes one out of the "
        "list without touching the document. Bookmarks last for the session and "
        "move with the text as you edit around them."
    ),
    "Copy Tray": (
        "Twelve numbered clipboard slots that outlive a restart. Copy into a "
        "slot, and paste from it an hour later -- the system clipboard holds one "
        "thing, and this is what to do when that is one fewer than you need."
    ),
    "Clip Library": (
        "Everything you have copied recently, newest first, whether or not you "
        "decided at the time that it mattered. Choose one and press Enter to "
        "paste it back."
    ),
    "Character at the cursor": (
        "Exactly which character the cursor is on: its name, its code point, "
        "and what it does to a search. A screen reader says 'space' for four "
        "different characters, and this is how you tell which one you have."
    ),
    "Marks": (
        "The places you have passed through, newest first, with the line each "
        "one is on. Choose one and press Enter to go there. A mark is not a "
        "bookmark: a bookmark is somewhere you meant to keep, a mark is where "
        "you were standing before you went to look something up."
    ),
    "Spelling Review": (
        "Every word in this document that is not in the dictionary, one at a "
        "time, with suggestions you can arrow through. Change it, change every "
        "one like it, ignore it, or add it to your dictionary so it is never "
        "questioned again."
    ),
    "Spelling Suggestions": (
        "Better spellings for the word the cursor was in, closest first. Choose "
        "one and press Enter to replace the word; press Escape to leave it as "
        "you wrote it. Alt F7 adds it to your dictionary instead, if it was "
        "right all along."
    ),
    "Manage Abbreviations": (
        "Your abbreviations: type the short form and a space, and the long form "
        "appears. This is QuillLite's own list unless you asked it, in "
        "Preferences, to share the one QUILL and Quill Inkwell use."
    ),
    "Customize QuillLite Features": (
        "Turn whole parts of QuillLite on or off. Unchecking an area removes its "
        "menu and its keys entirely, which is how this stays a small editor "
        "without being a poor one. Three areas start switched off and are found "
        "here rather than hidden: autocorrect, timestamped backups, and Go To "
        "Anything."
    ),
    "Command Palette": (
        "Every command QuillLite has, searchable, with its key beside it. A menu "
        "answers 'what is under Format?'; this answers 'how do I sort lines?', "
        "which is the question you actually have."
    ),
    "Go to Anything": (
        "One box that searches commands, headings and bookmarks together. Type "
        "part of what you want; a hash sign at the front restricts the results "
        "to headings."
    ),
    "Keyboard shortcuts": (
        "Every key QuillLite binds, menu by menu. It is generated from the same "
        "table that builds the menus, so it cannot drift from what is actually "
        "bound. Read it with the arrow keys; Escape closes it."
    ),
    "About QuillLite": (
        "What this copy is, and where it keeps your settings and your recovered "
        "work. QuillLite is a small companion to QUILL for All, not a replacement "
        "for it: anything to do with AI, dictation, conversion, comparison or "
        "publishing lives in QUILL."
    ),
}

#: Purposes for windows whose titles carry live data, matched by prefix.
PREFIX_PURPOSES: tuple[tuple[str, str], ...] = (
    (
        "Help:",
        "This is the help window itself: the purpose of the window you were in, "
        "then the control you were on. Escape returns you to it.",
    ),
)

#: Purposes for windows titled after their content. QuillLite's document window
#: is titled "<file> - QuillLite (<mode>)", so the app's own name inside the
#: title is what identifies it -- there is no fixed prefix to match on.
CONTAINS_PURPOSES: tuple[tuple[str, str], ...] = ((" - QuillLite", PURPOSES["QuillLite"]),)

#: The honest fallback for a surface the catalogue does not know. The gate keeps
#: this unreachable from any window QuillLite builds; it exists so a shared or
#: brand-new window still answers F1 with something true rather than nothing.
GENERIC_PURPOSE = (
    "A QuillLite window. Tab moves between its controls, Escape closes it, and "
    "F1 on any control explains that control."
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
    for marker, purpose in CONTAINS_PURPOSES:
        if marker in stripped:
            return purpose
    return GENERIC_PURPOSE


def is_known_title(title: str) -> bool:
    """True when *title* resolves to an authored purpose (the gate's check)."""
    stripped = title.strip()
    if stripped in PURPOSES:
        return True
    if any(stripped.startswith(prefix) for prefix, _purpose in PREFIX_PURPOSES):
        return True
    return any(marker in stripped for marker, _purpose in CONTAINS_PURPOSES)
