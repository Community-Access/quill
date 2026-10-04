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
            "Start here. You open a file you already have, hear the three things "
            "QUILL Lite remembers about it, and save it back exactly as it was."
        ),
        steps=(
            Step(
                title="Open something you already have",
                body=(
                    "Pick any text file you already have. An older one is a good "
                    "test. QUILL Lite opens plain text, Markdown, HTML and rich "
                    "text, so whatever you choose will be fine."
                ),
                command="cmd_open",
                hear="The file's name, and the first line of it.",
            ),
            Step(
                title="Look at what it remembered",
                body=(
                    "Now go to the status bar. It is a row of cells, and you move "
                    "along it with the arrow keys. Listen for three of them: "
                    "Encoding is how the letters are stored, Line Endings is how "
                    "each line finishes, and Format is the kind of document. "
                    "QUILL Lite keeps all three just as it found them."
                ),
                command="cmd_focus_status_bar",
                hear="Each cell's name and its value as you arrow along.",
                note=(
                    "Press Escape to go back to your document. Looking around is "
                    "safe: nothing changes unless you press Enter on a cell and "
                    "answer the question it asks."
                ),
            ),
            Step(
                title="Save it without changing anything",
                body=(
                    "Save the file straight back without typing anything. If you "
                    "like, compare it with a copy of the original afterwards. You "
                    "will find they are the same, byte for byte."
                ),
                command="cmd_save",
                hear='"Saved" and the file\'s name.',
            ),
            Step(
                title="Type a character the file cannot hold",
                body=(
                    "This one is optional. If your file uses an older encoding, "
                    "type an em dash or an emoji and save again. QUILL Lite stops "
                    "and asks you first: save as UTF-8 and keep the character, "
                    "save as it was and lose it, or cancel. You decide."
                ),
                hear=(
                    "A question counting the characters, naming the encoding, and "
                    "offering Yes, No and Cancel."
                ),
                note=(
                    "Not sure which encoding your file uses? The Encoding cell in "
                    "the status bar tells you."
                ),
            ),
        ),
        closing=(
            "That is the heart of QUILL Lite. Your file comes back the way you "
            "left it, and everything else is built on top of that."
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
            "Plain text, Markdown, HTML and rich text: what each one means for "
            "you, and the one key that moves between them."
        ),
        steps=(
            Step(
                title="Find out what you are in",
                body=(
                    "Go to the status bar and arrow to the Format cell. It tells "
                    "you which kind of document this is. QUILL Lite guesses from "
                    "the file's name, and you can always change its mind."
                ),
                command="cmd_focus_status_bar",
                hear='The Format cell, reading "Markdown", "HTML", "Plain text" or "Rich text".',
            ),
            Step(
                title="Ring through the four",
                body=(
                    "One key steps through all four kinds, and each one says its "
                    "name as you land on it. Keep pressing until you hear the one "
                    "you want. Moving between plain text, Markdown and HTML does "
                    "not touch your words. It only changes what the formatting "
                    "keys type from now on."
                ),
                command="cmd_switch_document_kind",
                hear="Each kind naming itself as you land on it.",
            ),
            Step(
                title="Go into rich text, and come back",
                body=(
                    "Rich text is the one stop that really converts. Going in "
                    "turns Markdown into real bold, headings and lists. Coming "
                    "back out turns them into Markdown again, and QUILL Lite asks "
                    "you first, naming anything it cannot carry across."
                ),
                hear=('A question before it converts, then "Rich text mode" or "Plain text mode".'),
                note=(
                    "Your file keeps its name. A rich document cannot be saved "
                    "over a .txt file, so the next Ctrl+S offers you the right "
                    "ending already filled in."
                ),
            ),
            Step(
                title="Say otherwise, for this window only",
                body=(
                    "Sometimes you want to write HTML in a scratch .txt file, and "
                    "that is fine. Document Language lets you pick the kind "
                    "yourself, and tells you what each choice will do before you "
                    "choose. Your choice lasts as long as this window is open."
                ),
                command="cmd_set_language",
                hear="Each option described, and the one the file name would have chosen marked.",
            ),
        ),
        closing=(
            "Now you know what kind of document you are in, and how to change it "
            "when QUILL Lite guessed wrong."
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
            "Instead of tabs, every open document gets a number. Here are the "
            "ways to get to the one you want."
        ),
        steps=(
            Step(
                title="Open a second file",
                body=(
                    "It opens inside the same window, as document 2. A number is "
                    'easy to remember and easy to say: "document 3" is much '
                    'clearer than "the other Untitled".'
                ),
                command="cmd_open",
                hear="The new document's number and name, in its title.",
            ),
            Step(
                title="Walk between them",
                body=(
                    "Ctrl+Tab is what most people press, and Ctrl+F6 is the key "
                    "Windows uses for this. Both work. The Window menu lists them "
                    "too."
                ),
                command="cmd_next_window",
                hear="The document you arrive at, announcing its number and name.",
            ),
            Step(
                title="Go straight to one",
                body=(
                    "Hold Alt and press a document's number to go straight to it. "
                    "Once you have more than two open, this is the quickest way "
                    "around, and it is why they have numbers."
                ),
                keys=("Alt+1", "Alt+2", "Alt+3"),
                hear="The document you asked for.",
                note=(
                    "Your documents all live inside one QUILL Lite window, so they "
                    "do not appear in Alt+Tab. Use the keys in this lesson to move "
                    "between them instead."
                ),
            ),
        ),
        closing=(
            "Open as many as you like. Each one has a number, and Alt with that "
            "number takes you straight there."
        ),
    ),
    Tutorial(
        slug="getting-unlost",
        title="What to press when you are lost",
        track="first-documents",
        minutes=3,
        surfaces=("QUILL Lite",),
        summary=(
            "Three keys that tell you where you are, what something does, and "
            "what QUILL Lite can do."
        ),
        steps=(
            Step(
                title="Ask what you are standing on",
                body=(
                    "F1 works everywhere: in your document, on a button, in any "
                    "window. It tells you what the window is for, and then what "
                    "the thing you are on does."
                ),
                keys=("F1",),
                hear="The window's purpose, then the control's.",
            ),
            Step(
                title="Ask what the facts are",
                body=(
                    "The status bar holds everything QUILL Lite knows about your "
                    "document, plus the last thing it said. Missed a message? It "
                    "is waiting in the last cell, Status Message. Press End to "
                    "jump there."
                ),
                command="cmd_focus_status_bar",
                hear='"Status bar" and the cell you land on, then each fact as you arrow.',
            ),
            Step(
                title="Ask what exists",
                body=(
                    "The Keyboard Shortcuts window lists every key QUILL Lite has. "
                    "It shows your keys, including any you have changed, and you "
                    "can type part of a name to find one."
                ),
                command="cmd_shortcuts",
                hear="A searchable list of every command and its key.",
            ),
        ),
        closing=("Whenever you are unsure, one of these three keys will explain where you are."),
    ),
)
