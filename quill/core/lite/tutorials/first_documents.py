"""QUILL Lite, track 1: your first documents.

Four lessons. Open a file and be sure it comes back unchanged, learn where the
facts about it live, learn what kind of document you are in, and find your way
between the ones you have open.

Somebody who does only this track can use QUILL Lite as a Notepad replacement all
day, which is the whole of its promise (prd.md §1).
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="open-and-save",
        title="Open a file, and give it back unchanged",
        track="first-documents",
        minutes=5,
        surfaces=("QUILL Lite",),
        summary=(
            "The one promise QUILL Lite makes, and the three things it "
            "remembers about your file in order to keep it."
        ),
        steps=(
            Step(
                title="Open something you already have",
                body=(
                    "Any text file will do, and an old one is a better test than "
                    "a new one. QUILL Lite reads plain text, Markdown, HTML and "
                    "rich text."
                ),
                command="cmd_open",
                hear="The file's name, and the first line of it.",
            ),
            Step(
                title="Look at what it remembered",
                body=(
                    "The status bar is a row of cells you can arrow along, not a "
                    "strip of text. Three of them are the promise: Encoding is "
                    "how the letters are stored, Line Endings is how the lines "
                    "finish, and Format is what kind of document this is. "
                    "QUILL Lite puts all three back exactly as it found them."
                ),
                command="cmd_focus_status_bar",
                hear="Each cell's name and its value as you arrow along.",
                note=(
                    "Escape brings you back to your document. Nothing you do in "
                    "the status bar changes the file unless you press Enter on a "
                    "cell and answer the question it asks."
                ),
            ),
            Step(
                title="Save it without changing anything",
                body=(
                    "Save it straight back. Then compare it with the original, "
                    "however you like to do that -- it is the same file, byte for "
                    "byte."
                ),
                command="cmd_save",
                hear='"Saved" and the file\'s name.',
            ),
            Step(
                title="Type a character the file cannot hold",
                body=(
                    "If your file is stored in an older encoding, type an em dash "
                    "or an emoji into it and save again. QUILL Lite asks before it "
                    "writes: save as UTF-8 and keep it, save as asked and lose it "
                    "knowingly, or cancel."
                ),
                hear=(
                    "A question counting the characters, naming the encoding, and "
                    "offering Yes, No and Cancel."
                ),
                note=(
                    "Before version 1.0 those characters became question marks "
                    'and the app said "Saved". The only way to find out was to '
                    "read that line again."
                ),
            ),
        ),
        closing=(
            "That is the product in four steps. Everything else is convenience "
            "on top of a file that comes back the way you left it."
        ),
        then=("kinds-of-document",),
    ),
    Tutorial(
        slug="kinds-of-document",
        title="Four kinds of document, and how to say which",
        track="first-documents",
        minutes=4,
        surfaces=("QUILL Lite",),
        summary=(
            "Plain text, Markdown, HTML and rich text -- what each changes, and "
            "the one key that rings between them."
        ),
        steps=(
            Step(
                title="Find out what you are in",
                body=(
                    "The Format cell says which of the four this document is, and "
                    "the Language cell says which markup a plain one is written "
                    "in. QUILL Lite guesses from the file's name, and the guess is "
                    "only ever a first guess."
                ),
                command="cmd_focus_status_bar",
                hear='The Format cell, reading "Markdown", "HTML", "Plain text" or "Rich text".',
            ),
            Step(
                title="Ring through the four",
                body=(
                    "One key walks all four, announcing each stop. Press it until "
                    "you hear the one you meant. Moving between plain, Markdown "
                    "and HTML changes nothing in your document -- it changes what "
                    "the formatting keys write from now on."
                ),
                command="cmd_switch_document_kind",
                hear="Each kind naming itself as you land on it.",
            ),
            Step(
                title="Go into rich text, and come back",
                body=(
                    "Rich text is the one stop that really converts. Going in "
                    "turns Markdown into real formatting; coming out turns the "
                    "formatting back into Markdown, and asks first, naming "
                    "anything it cannot carry."
                ),
                hear=('A question before it converts, then "Rich text mode" or "Plain text mode".'),
                note=(
                    "Your file keeps its name. Because a rich document cannot be "
                    "written over a .txt, the next Ctrl+S offers you the right "
                    "suffix already filled in."
                ),
            ),
            Step(
                title="Say otherwise, for this window only",
                body=(
                    "Writing HTML in a scratch .txt is a reasonable thing to do. "
                    "Document Language goes straight to one and tells you what "
                    "each choice will do before you make it. The choice lasts as "
                    "long as the window."
                ),
                command="cmd_set_language",
                hear="Each option described, and the one the file name would have chosen marked.",
            ),
        ),
        then=("moving-between-documents",),
    ),
    Tutorial(
        slug="moving-between-documents",
        title="Your documents are numbered",
        track="first-documents",
        minutes=3,
        surfaces=("QUILL Lite",),
        summary=(
            "Why there are no tabs, what you get instead, and the four ways to "
            "reach the document you want."
        ),
        steps=(
            Step(
                title="Open a second file",
                body=(
                    "It opens inside the same window, as document 2. "
                    '"Document 3" is a name you can hold in your head and say '
                    'out loud; "the other Untitled" is not.'
                ),
                command="cmd_open",
                hear="The new document's number and name, in its title.",
            ),
            Step(
                title="Walk between them",
                body=(
                    "Ctrl+Tab is what most people press and Ctrl+F6 is what "
                    "Windows documents. Both work, and so does the Window menu."
                ),
                command="cmd_next_window",
                hear="The document you arrive at, announcing its number and name.",
            ),
            Step(
                title="Go straight to one",
                body=(
                    "Alt and a digit goes directly to that document. This is the "
                    "fast way once you have more than two open, and it is the "
                    "reason they are numbered at all."
                ),
                keys=("Alt+1", "Alt+2", "Alt+3"),
                hear="The document you asked for.",
                note=(
                    "Documents here are children of one window, so they do not "
                    "appear in Alt+Tab. That is the cost of the numbering, and "
                    "these four routes are how QUILL Lite carries it."
                ),
            ),
        ),
    ),
    Tutorial(
        slug="getting-unlost",
        title="What to press when you are lost",
        track="first-documents",
        minutes=3,
        surfaces=("QUILL Lite",),
        summary="Three keys that answer where you are, what this does, and what exists.",
        steps=(
            Step(
                title="Ask what you are standing on",
                body=(
                    "F1 answers everywhere -- in the document, on a button, in "
                    "any window. It says what the window is for and then what the "
                    "control you are on does."
                ),
                keys=("F1",),
                hear="The window's purpose, then the control's.",
            ),
            Step(
                title="Ask what the facts are",
                body=(
                    "The status bar holds everything QUILL Lite knows about your "
                    "document, and every message it has said. A message you "
                    "missed is still in the first cell."
                ),
                command="cmd_focus_status_bar",
                hear="The last thing QUILL Lite said, and then each fact as you arrow.",
            ),
            Step(
                title="Ask what exists",
                body=(
                    "The Keyboard Shortcuts window lists every key QUILL Lite has, "
                    "built from the live command table -- so it shows your keys, "
                    "including any you have changed."
                ),
                command="cmd_shortcuts",
                hear="A searchable list of every command and its key.",
            ),
        ),
        closing=("Nothing in QUILL Lite is more than these three keys away from being explained."),
    ),
)
