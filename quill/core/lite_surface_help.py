"""What every QUILL Lite window is *for* -- the F1 help's opening paragraph.

Every app in the family answers F1 the same way: what this window is for, then
what the control you are on does. The engine is shared
(:mod:`quill.ui.app_context_help` + :mod:`quill.core.control_help`); this module
is QUILL Lite's half of it, the wx-free catalogue of window purposes, keyed by
window title exactly as Radio's, Cast's, Converter's and Inkwell's are.

Keyed by **title** for the reason the siblings are: the title is the one
identity a window already announces, and it is what somebody quotes back in a
bug report. QUILL Lite adds one wrinkle none of the siblings have -- its main
window is titled after the *document*, not after the app ("3: Notes.txt -
QUILL Lite (plain text)"), because the number and the file name are what a
listener needs from the one string a reader announces on arrival. So the
document window is matched by the ``" - QUILL Lite"`` that every one of those
titles contains, and the fixed windows are matched exactly.

The catalogue is **gated** (GATE-LITE-HELP,
:mod:`quill.tools.lite_help_audit`): every ``wx.Frame`` / ``wx.Dialog`` title
constructed in QUILL Lite's modules must resolve here, so a new surface cannot
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
    # -- The AI windows. Off until somebody turns the area on, so most people
    # will never meet these; the ones who do are meeting them for the first
    # time, which is what the wording is for.
    "AI Assistant": (
        "Ask QUILL's free AI to summarize, rewrite, proofread or explain the "
        "passage shown here, or to answer a question about this document. "
        "What you see in 'What will be sent' is exactly what leaves your "
        "computer -- nothing else from the document goes with it. Each answer "
        "uses one of your free requests, and you keep typing while it works."
    ),
    "QUILL AI Sign-In": (
        "Connect this computer to QUILL's free AI. There is no account, no "
        "password and no email address. The window opens on an eight-character "
        "code: choose Open the Connect Page to confirm it in your browser with "
        "the code already filled in, or type it into the web page on any other "
        "device. This window says when you are connected."
    ),
    "AI Usage": (
        "How many free AI requests you have left this month and today, and "
        "when the count starts again. Your support ID is here too -- that is "
        "what QUILL support will ask for. You can also sign this computer out "
        "from here, and connect it again whenever you like."
    ),
    # Keyed by the value of quill.core.ai.gateway_privacy.AGREEMENT_TITLE. The
    # window sets its title from that constant rather than from a literal, so
    # the title and the agreement text cannot drift apart -- and so this key
    # has to be kept in step by hand if the constant ever changes, which is
    # what the TITLE_EXEMPT note in lite_help_audit.py says out loud.
    "QUILL AI: what is sent, and what is kept": (
        "The agreement, in full, before anything is sent. Read it with the "
        "arrow keys. I Agree turns AI help on; No Thanks leaves it off and "
        "changes nothing else. You can read this again, or withdraw it, from "
        "Tools, AI, Privacy Agreement at any time."
    ),
    "Summary": (
        "What the AI sent back. It is read-only on purpose: nothing goes into "
        "your document until you choose Replace My Selection or Insert Below, "
        "and either of those is a single edit that Control Z takes back."
    ),
    "QUILL Lite": (
        "Your document. This is the whole editor: type, and Control S saves. The "
        "title bar leads with this document's number, then its name, whether it "
        "is plain text or rich text, and whether there is anything unsaved. "
        "Control N opens another document beside this one, numbered; Alt+1 to "
        "Alt+9 go straight to one, Control Tab and Control F6 move to the next, "
        "and the Window menu lists them all. Documents live inside one QUILL Lite "
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
    "Insert Special Character": (
        "Put in a character the keyboard has no key for. Search by name -- dash, "
        "quote, euro, acute, arrow -- or by Unicode code point, or clear the search "
        "box and browse one of the fifteen groups: whitespace, dashes, quotes, "
        "invisibles, typography, marks, currency, maths, fractions, superscripts, "
        "arrows, accented letters, Greek and punctuation from other languages. "
        "Arrow through the characters to hear each one described and press Enter to "
        "insert the one you are on. QUILL Lite reads back what it put in, because "
        "most of this list is invisible on the page. QUILL has the same picker on "
        "Shift+F2."
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
        "Every setting QUILL Lite has, in one window. Two of them live only here: "
        "what Control N creates, and how often unsaved work is copied aside. The "
        "rest -- theme, word wrap, and the editor font -- are also on the View "
        "menu, where you will reach them faster."
    ),
    "Spelling Announcements": (
        "How a misspelled word is reported to you. A misspelling is the one "
        "thing an editor cannot convey by speech alone -- receive and recieve "
        "sound identical -- so the letters are the answer, and this window "
        "decides when you get them and how they are said. Three groups: what "
        "happens while you type, how letters are spoken, and how long each "
        "pause is before the spelling follows."
    ),
    "Document language": (
        "Which markup this document is written in. It decides what Bold writes, "
        "what the heading keys write, which of the two tag pickers the Insert "
        "menu offers, and whether the cursor can tell you what list you are in. "
        "QUILL Lite reads it from the file name; this is where you say otherwise. "
        "Nothing in your document changes -- only what the keys write from now "
        "on. The choice lasts as long as this window is open."
    ),
    "Insert Markdown Tag": (
        "Every piece of Markdown QUILL Lite can write, in one searchable list: "
        "bold, italic, code, the six heading levels, bullet, numbered and task "
        "lists, blockquote, link, image, table and footnote. Type to narrow it. "
        "Anything selected in your document is wrapped; with nothing selected "
        "the markup goes in empty and the cursor lands in the middle of it."
    ),
    "Insert HTML Tag": (
        "Forty HTML tags, searchable by what they do as well as by what they are "
        "called -- dropdown finds select, checkbox finds input, collapsible "
        "finds details. Choose the tag, then give it attributes if it needs any, "
        "or press Enter on the empty box to skip that. Anything selected in your "
        "document is wrapped by the tag."
    ),
    "Insert Link": (
        "Where the link points. Leave the address as it is to put a placeholder "
        "in and fill it in later -- the link text is whatever you had selected."
    ),
    "Insert Image": (
        "Where the image lives. Leave the address as it is to put a placeholder "
        "in and fill it in later -- the description is whatever you had selected, "
        "and it is what somebody using a screen reader will hear instead of the "
        "picture, so it is worth writing."
    ),
    "File format": (
        "How this document will be written back to disk: which character "
        "encoding, and which line endings. QUILL Lite normally writes back "
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
        "appears. This is QUILL Lite's own list unless you asked it, in "
        "Preferences, to share the one QUILL and Quill Inkwell use."
    ),
    "Customize QUILL Lite Features": (
        "Turn whole parts of QUILL Lite on or off. Unchecking an area removes its "
        "menu and its keys entirely, which is how this stays a small editor "
        "without being a poor one. Type in the search box to narrow the list, or "
        "choose a profile -- Notepad, WordPad, Recommended, Everything -- to set "
        "them all at once. Three areas start switched off and are found here "
        "rather than hidden: autocorrect, timestamped backups, and Go To "
        "Anything."
    ),
    "Keyboard Manager": (
        "Every command QUILL Lite has, with the key it answers to. Type part of a "
        "command's name to find it, or press Record a Key and press a "
        "combination to be told what that key already does. Assigning a key "
        "somebody else has names them and asks before moving it. Insert is never "
        "bindable: it is the key NVDA and JAWS use as their own modifier."
    ),
    "Key for": (
        "Press the key combination you want, and it appears in the box. Pressing "
        "another replaces it. Escape leaves the command on the key it has now."
    ),
    "Command Palette": (
        "Every command QUILL Lite has, searchable, with its key beside it. A menu "
        "answers 'what is under Format?'; this answers 'how do I sort lines?', "
        "which is the question you actually have."
    ),
    "Go to Anything": (
        "One box that searches commands, headings and bookmarks together. Type "
        "part of what you want; a hash sign at the front restricts the results "
        "to headings."
    ),
    "Keyboard shortcuts": (
        "Every key QUILL Lite binds, menu by menu. It is generated from the same "
        "table that builds the menus, so it cannot drift from what is actually "
        "bound. Read it with the arrow keys; Escape closes it."
    ),
    "About QUILL Lite": (
        "What this copy is, and where it keeps your settings and your recovered "
        "work. QUILL Lite is a small companion to QUILL for All, not a replacement "
        "for it: anything to do with AI, dictation, conversion, comparison or "
        "publishing lives in QUILL."
    ),
}

#: Purposes for windows whose titles carry live data, matched by prefix.
# The result window is titled after what was asked for, so every one of its
# titles needs an entry. Same sentence for all five: the window is the same
# window, and a different paragraph per verb would be five things to keep in
# step for no gain to anybody listening.
for _result_title in ("Rewrite", "Proofread", "Explanation", "Answer", "AI Result"):
    PURPOSES[_result_title] = PURPOSES["Summary"]


PREFIX_PURPOSES: tuple[tuple[str, str], ...] = (
    (
        "Help:",
        "This is the help window itself: the purpose of the window you were in, "
        "then the control you were on. Escape returns you to it.",
    ),
)

#: Purposes for windows titled after their content. QUILL Lite's document window
#: is titled "<file> - QUILL Lite (<mode>)", so the app's own name inside the
#: title is what identifies it -- there is no fixed prefix to match on.
CONTAINS_PURPOSES: tuple[tuple[str, str], ...] = ((" - QUILL Lite", PURPOSES["QUILL Lite"]),)

#: The honest fallback for a surface the catalogue does not know. The gate keeps
#: this unreachable from any window QUILL Lite builds; it exists so a shared or
#: brand-new window still answers F1 with something true rather than nothing.
GENERIC_PURPOSE = (
    "A QUILL Lite window. Tab moves between its controls, Escape closes it, and "
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
