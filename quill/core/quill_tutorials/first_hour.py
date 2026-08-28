"""QUILL, track 1: your first hour.

Five lessons. Make a document and save it, learn the four ways of getting
anywhere, meet the QUILL key, and learn what to press when you are lost.
Somebody who does only this track can write in QUILL all day.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="first-document",
        title="Write and save your first document",
        track="first-hour",
        minutes=5,
        surfaces=("QUILL",),
        summary=(
            "New, type, save, and know where it went -- plus the two things "
            "QUILL does at startup that you should not be surprised by."
        ),
        steps=(
            Step(
                title="Start where the app puts you",
                body=(
                    "There is no splash screen. The window appears with a menu "
                    "bar, an editor and a status bar, and focus is in the editor. "
                    "If QUILL detects a screen reader it adjusts its hints and its "
                    "announcement style to match."
                ),
                hear="Your screen reader announcing the editor.",
            ),
            Step(
                title="Make a document",
                body=(
                    "New opens an empty document in its own tab. QUILL is "
                    "multi-document: every file you open lives in a notebook tab, "
                    "and Ctrl+Tab moves between them."
                ),
                command="file.new",
                hear="A new, empty document.",
            ),
            Step(
                title="Type a few lines",
                body=(
                    "Just write. QUILL's editor is plain text that is aware of "
                    "Markdown and HTML when your document is one of those -- it "
                    "does not impose a format on a file that has none."
                ),
                hear="Your screen reader's own typing echo, and nothing from QUILL on top of it.",
            ),
            Step(
                title="Save it",
                body=(
                    "Save writes the file; Save As chooses the name and the "
                    "format. If you prefer a smaller, screen-reader-friendly file "
                    "picker, turn on Use simple file open dialog in Settings > "
                    "General."
                ),
                command="file.save",
                hear="The file saved, and its name.",
            ),
            Step(
                title="Ask where you are",
                body=(
                    "Press F6 to move into the status bar. It is a working "
                    "surface rather than a strip of text: line and column, word "
                    "count, insert or overwrite, selection size, encoding, line "
                    "endings, spell state, background tasks, autosave timing, and "
                    "the file path all live there, and each cell can be activated."
                ),
                keys=("F6", "Left arrow", "Right arrow"),
                hear="The cell you landed on, then each cell as you arrow across.",
                note=(
                    "Shift+F6 cycles back. The regions are Editor, the document "
                    "tabs when they are shown, the preview when it is open, and "
                    "the status bar."
                ),
            ),
            Step(
                title="Know what QUILL does about a crash",
                body=(
                    "If QUILL notices an earlier crash or an autosave state, it "
                    "offers recovery rather than silently hoping you forgot. And "
                    "if your screen reader disappears mid-session, QUILL "
                    "snapshots every open document to autosave first and then "
                    "explains what happened through whatever can still speak."
                ),
                hear="At the next launch: an offer to recover, naming what it found.",
            ),
        ),
        closing=(
            "That is the whole loop: new, type, save. The rest of QUILL is about "
            "not having to hunt for anything."
        ),
        then=("get-around", "do-it-by-name"),
    ),
    Tutorial(
        slug="get-around",
        title="Get around a long document",
        track="first-hour",
        minutes=6,
        surfaces=("QUILL",),
        summary=(
            "Line, heading, structure, bookmark and history -- the movement that "
            "makes a two-hundred-page document feel small."
        ),
        steps=(
            Step(
                title="Jump to a line",
                body=(
                    "Go to Line is the plainest jump and the one you will use "
                    "when somebody quotes a line number at you. QUILL says where "
                    "it landed rather than leaving you to check."
                ),
                command="navigate.go_to_line",
                hear="The line number, and the line itself.",
            ),
            Step(
                title="Move by structure",
                body=(
                    "Next Structure and Previous Structure move by the document's "
                    "own shape -- headings, blocks, regions -- rather than by "
                    "characters. In a long document this is the difference between "
                    "reading and searching."
                ),
                command="navigate.next_structure",
                hear="The structure you landed on, named.",
            ),
            Step(
                title="Open the outline",
                body=(
                    "The Outline Navigator and the Heading Organizer give you the "
                    "document's headings as a list you can move through and jump "
                    "from -- and the organizer can reorder sections, not just "
                    "visit them."
                ),
                command="navigate.outline_navigator",
                hear="The headings, with their levels.",
            ),
            Step(
                title="Drop a bookmark and come back",
                body=(
                    "Set a temporary bookmark before you go and look at something "
                    "else, and go back to it when you are done. For places you "
                    "return to often, named marks are worth learning."
                ),
                command="navigate.set_temp_bookmark",
                hear="Bookmark set -- then, later, the line you left.",
            ),
            Step(
                title="Retrace your steps",
                body=(
                    "Back Location and Forward Location walk your movement "
                    "history, the way a browser's back button does. It is the "
                    "answer to where was I before I followed that link."
                ),
                command="navigate.back_location",
                hear="The place you came from.",
            ),
            Step(
                title="Ask where you are, at any time",
                body=(
                    "Speak Status Summary says where the cursor is and what state "
                    "the document is in; Speak Full Path says which file you are "
                    "actually in, which matters when two drafts have the same "
                    "name."
                ),
                command="navigate.speak_status_summary",
                hear="Line, column, and the document's state, in one sentence.",
            ),
            Step(
                title="Move between documents",
                body=(
                    "Ctrl+Tab and Ctrl+Shift+Tab move between open documents, and "
                    "Ctrl+W closes the one you are in. QUILL opens generated "
                    "things -- the keyboard reference, a compare summary -- as "
                    "ordinary tabs too, so artifacts stay close to the work that "
                    "made them."
                ),
                command="window.next_document",
                hear="The document you moved to, by name.",
            ),
        ),
        closing=(
            "Structure, outline, bookmarks and history. Between them, you should "
            "never have to arrow through a document to find something again."
        ),
        then=("do-it-by-name",),
    ),
    Tutorial(
        slug="do-it-by-name",
        title="Do anything by name",
        track="first-hour",
        minutes=4,
        surfaces=("QUILL",),
        summary=(
            "The command palette, Go to Anything, and the keyboard reference that "
            "is generated from your own keymap rather than written down "
            "somewhere."
        ),
        steps=(
            Step(
                title="Open the command palette",
                body=(
                    "Type what you want rather than remembering where it lives. "
                    "The palette is the fastest route to anything QUILL can do, "
                    "and it teaches you the key while you use it: every entry "
                    "shows its own shortcut."
                ),
                command="app.command_palette",
                hear="A search box, then the commands as you narrow them.",
            ),
            Step(
                title="Learn what an unavailable command means",
                body=(
                    "When a command cannot run, the palette says why rather than "
                    "showing a bare unavailable. A menu item disabled by a safety "
                    "advisory carries the same reason in its help text."
                ),
                hear="The reason, in a sentence.",
            ),
            Step(
                title="Go to anything",
                body=(
                    "Go to Anything is the other door: one box that reaches "
                    "files, headings, symbols and places rather than commands. Use "
                    "the palette when you want to *do* something and this when you "
                    "want to *reach* something."
                ),
                command="navigate.go_to_anything",
                hear="A search box, then matches grouped by what they are.",
            ),
            Step(
                title="Read the keys you actually have",
                body=(
                    "The keyboard reference is generated from your current feature "
                    "profile and your own keybindings, so it always describes the "
                    "QUILL in front of you -- not the one in a manual written a "
                    "year ago."
                ),
                keys=("Ctrl+F1",),
                hear="The reference, opening as an ordinary document tab.",
            ),
            Step(
                title="Find one key fast",
                body=(
                    "The key cheat sheet is the filtered version: type what you "
                    "want to do and it narrows. It is the quickest way to answer "
                    "what is the key for this without leaving what you are doing."
                ),
                command="help.key_cheatsheet",
                hear="A filter box, then the matching keys.",
            ),
        ),
        closing=(
            "Palette to do, Go to Anything to reach, cheat sheet to remember. "
            "None of the three asks you to have memorised anything."
        ),
        then=("the-quill-key",),
    ),
    Tutorial(
        slug="the-quill-key",
        title="The QUILL key",
        track="first-hour",
        minutes=5,
        surfaces=("QUILL",),
        summary=(
            "One chord that opens most of QUILL's power features, and the browse "
            "mode that turns single letters into document navigation."
        ),
        steps=(
            Step(
                title="Press it once, and listen",
                body=(
                    "The QUILL key is Ctrl+Shift+Grave -- the back-tick key above "
                    "Tab. Pressed once it arms a short-lived prefix: the next key "
                    "you press runs a chord command, and then the prefix expires. "
                    "A short two-tone earcon confirms it armed, so you know before "
                    "any speech arrives."
                ),
                keys=("Ctrl+Shift+Grave",),
                hear="A quick double-ping, unlike any other sound in the app.",
            ),
            Step(
                title="Run one chord",
                body=(
                    "With the prefix armed, press G for Go to Anything or R for "
                    "Read Aloud. Menus and the cheat sheet write these as QUILL "
                    "Key + G, which is the same thing said in words."
                ),
                keys=("Ctrl+Shift+Grave, G",),
                hear="Whatever that command announces.",
            ),
            Step(
                title="Ask the chord list",
                body=(
                    "QUILL Key + ? opens the full cheat sheet of chords. Every "
                    "chord is data from the keymap, which means every chord is "
                    "remappable in the Keymap Editor -- and the sheet shows what "
                    "you have, not what shipped."
                ),
                keys=("Ctrl+Shift+Grave, ?"),
                hear="The chord list, filterable.",
            ),
            Step(
                title="Lock browse mode on",
                body=(
                    "Press the QUILL key twice and Quick Nav (browse) mode locks "
                    "on: single letters move the cursor through the document's "
                    "structure -- H for headings, P for paragraphs, S for "
                    "sentences. Escape leaves."
                ),
                keys=("Ctrl+Shift+Grave", "Ctrl+Shift+Grave", "Escape"),
                hear="Browse mode on, then each structure as you move.",
            ),
            Step(
                title="Know why it is a chord and not a modifier",
                body=(
                    "A prefix chord costs one extra keystroke and buys a whole "
                    "alphabet of commands that never collide with your screen "
                    "reader's keys or the editor's. That trade is the reason it "
                    "exists."
                ),
                hear="Nothing: this is the design, not an action.",
                note=(
                    "On some keyboards Windows reports the grave key oddly, so "
                    "QUILL detects it three independent ways -- by character, by "
                    "virtual key, and by physical scan code."
                ),
            ),
        ),
        closing=(
            "Armed once for one command, pressed twice for a mode. Everything it "
            "reaches is also in the palette, so the chord is a shortcut rather "
            "than a requirement."
        ),
        then=("getting-unstuck",),
    ),
    Tutorial(
        slug="getting-unstuck",
        title="Getting unstuck",
        track="first-hour",
        minutes=4,
        surfaces=("QUILL",),
        summary=(
            "F1, the echo of what QUILL just said, why a thing is unavailable, "
            "and the undo that covers more than typing."
        ),
        steps=(
            Step(
                title="Ask what the thing under your cursor is",
                body=(
                    "F1 on any focusable control -- a field, a button, a menu "
                    "item, the editor itself -- opens help that says what the "
                    "control does and which keys apply to it, all in one "
                    "read-only field so your reader announces it in one pass."
                ),
                keys=("F1",),
                hear="The window's purpose, then the control's own help.",
            ),
            Step(
                title="Ask what you can do here",
                body=(
                    "Shift+F1 answers What Can I Do Here for the document you are "
                    "in, which is a different question from what is this control: "
                    "it is about the work rather than the widget."
                ),
                keys=("Shift+F1",),
                hear="What this kind of document supports, in context.",
            ),
            Step(
                title="Re-read what QUILL just said",
                body=(
                    "Speech is fleeting: an indent depth, a save result, a no "
                    "matches. The Spoken Echo remembers the last twenty things "
                    "QUILL announced, newest first, in a dialog you can arrow "
                    "through, review by character, select and copy."
                ),
                keys=("Alt+Shift+E",),
                hear="The last things QUILL said, as text.",
                note=(
                    "Double-pressing an informational command -- Describe "
                    "Formatting, Document Summary, Context Help -- opens the Echo "
                    "instead of repeating itself, the screen-reader convention. "
                    "Alt+Shift+E always works."
                ),
            ),
            Step(
                title="Find out why something is unavailable",
                body=(
                    "Why Unavailable answers for the command you were reaching "
                    "for. QUILL's rule is that a refusal carries its reason -- in "
                    "the palette, in a dimmed menu item's help text, and in error "
                    "messages, which increasingly end with the concrete next step."
                ),
                command="help.why_unavailable",
                hear="The reason, and what would change it.",
            ),
            Step(
                title="Take back the last thing",
                body=(
                    "Undo covers editing; Undo Last Action covers the destructive "
                    "verbs elsewhere in the app. And every confirmation that would "
                    "destroy something defaults to No, so pressing Enter "
                    "reflexively can never cost you data."
                ),
                command="edit.undo",
                hear="What came back.",
            ),
            Step(
                title="Know the promise underneath",
                body=(
                    "Anything that closes or degrades QUILL without your asking "
                    "persists your work first. That rule is why the screen-reader "
                    "watchdog snapshots your documents before it explains itself, "
                    "and it applies everywhere in the app."
                ),
                hear="Nothing: this is the sentence to remember on a bad day.",
            ),
        ),
        closing=(
            "F1 for here, Shift+F1 for this work, Alt+Shift+E for what was just "
            "said. Between them there is no state you can be in without a way "
            "out."
        ),
    ),
)
