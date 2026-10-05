"""Five more dictation lessons, the same in QUILL and QUILL Lite.

dict.md 3.10 (gap 12): one lesson for each thing the 2026-10-05 gap plan
added -- punctuation and symbols, fixing a word by voice, snippets and clips by
voice, switching to Spanish, and a live transcript. Written once, because the
two editors teach the same dictation on the same keys; each editor passes its
own command ids, so the lesson renders whatever key the person has bound.

The wording follows :mod:`quill.core.tutorials.model`: one action a step, the
reason as well as the instruction, what you should hear, and no key promised in
prose.
"""

from __future__ import annotations

from collections.abc import Mapping

from quill.core.tutorials.model import Step, Tutorial

__all__ = ["dictation_lessons"]


def dictation_lessons(
    ids: Mapping[str, str], *, track: str, surfaces: tuple[str, ...]
) -> tuple[Tutorial, ...]:
    """The five lessons. *ids* maps ``toggle``, ``language``, ``transcript``
    and ``status`` to this editor's command ids."""
    toggle = ids["toggle"]
    return (
        Tutorial(
            slug="dictation-punctuation",
            title="Punctuation and symbols by voice",
            track=track,
            minutes=5,
            surfaces=surfaces,
            summary=(
                "Say punctuation, start a bulleted list and a heading, and spell a web "
                "address, and hear every mark read back so you know it went in."
            ),
            steps=(
                Step(
                    title="Start dictation",
                    body=(
                        "Open a new document, so nothing you care about is in the way, "
                        "and turn dictation on."
                    ),
                    command=toggle,
                    hear='Two rising tones, and "Dictation on".',
                ),
                Step(
                    title="Say a sentence with its punctuation",
                    body=(
                        "Say: dear Sam comma thank you for the letter period. Then pause. "
                        "Saying a mark always wins over the one the engine would add."
                    ),
                    hear="Dear Sam comma thank you for the letter period.",
                    note=(
                        "The marks are read back by name whatever your screen reader's "
                        "punctuation level is. Say punctuation marks in the read-back, in "
                        "More Dictation Settings turns that off."
                    ),
                ),
                Step(
                    title="Start a heading and a list",
                    body=(
                        "Say heading two, then the heading's words, and pause. Then say "
                        "bullet and an item. These marks count only at the start of what "
                        "you say, so ordinary sentences are never turned into lists."
                    ),
                    hear="Hash sign hash sign, then your heading; hyphen, then your item.",
                ),
                Step(
                    title="Spell a web address",
                    body=(
                        "Say spell, then the letters with dot and at sign between them: "
                        "spell sierra alpha mike at sign echo dot charlie oscar. Spelling "
                        "writes punctuation with no spaces."
                    ),
                    hear="The address, read back with its marks.",
                ),
            ),
            closing=(
                "Say what can I say at any time for every mark and symbol, including "
                "the Markdown ones: backtick, vertical bar and block quote."
            ),
        ),
        Tutorial(
            slug="dictation-fix-a-word",
            title="Fix a word by voice",
            track=track,
            minutes=5,
            surfaces=surfaces,
            summary=(
                "Find words you said earlier, select them or put the cursor beside them, "
                "and correct them without touching the keyboard."
            ),
            steps=(
                Step(
                    title="Dictate a couple of sentences",
                    body=(
                        "Turn dictation on and say two short sentences, pausing after "
                        "each, so there are words to find."
                    ),
                    command=toggle,
                    hear="Each sentence read back.",
                ),
                Step(
                    title="Select a word you said",
                    body=(
                        "Say select, then a word from the first sentence. The nearest one "
                        "before the cursor is found first, because that is usually the "
                        "one you are fixing."
                    ),
                    hear='"Selected:" and the words.',
                ),
                Step(
                    title="Say the right word",
                    body=(
                        "Just say the word you meant. What you say next replaces the "
                        "selection, in one step that Undo or scratch that takes back."
                    ),
                    hear="The new word read back.",
                ),
                Step(
                    title="Correct and spell a name",
                    body=(
                        "Say correct and a name the engine got wrong, then spell it, or say "
                        "spell that straight after dictating it: the letters you say next "
                        "replace it."
                    ),
                    hear='"Correcting" and the words, then the spelled word.',
                    note=(
                        "If the words are not in the document, what you said is written "
                        "as text and you hear Not found, written as text. Scratch that "
                        "removes it."
                    ),
                ),
            ),
            closing=(
                "Go to and go after put the cursor beside words instead of selecting them, "
                "and select again moves on to the next place the words appear."
            ),
        ),
        Tutorial(
            slug="dictation-snippets-and-clips",
            title="Snippets and clips by voice",
            track=track,
            minutes=4,
            surfaces=surfaces,
            summary=(
                "Copy the whole document, paste a Copy Tray slot and put in a snippet, all "
                "by saying so."
            ),
            steps=(
                Step(
                    title="Copy the whole document",
                    body=(
                        "With dictation on, say copy all. Nothing is selected, so nothing "
                        "can be typed over by accident."
                    ),
                    command=toggle,
                    hear='"Copied the whole document" and how many characters.',
                ),
                Step(
                    title="Paste a slot from the Copy Tray",
                    body=(
                        "Say paste clip and a slot number, like paste clip one. It goes "
                        "in as one phrase, so scratch that takes it out again."
                    ),
                    hear='"Pasted slot 1", or that the slot is empty.',
                ),
                Step(
                    title="Put in a snippet by name",
                    body=(
                        "Say insert snippet and its name. If more than one snippet matches "
                        "you hear how many, and the list opens so you can choose."
                    ),
                    hear='"Snippet" and its name.',
                ),
            ),
            closing="Say show clips or show snippets to open either list by voice.",
        ),
        Tutorial(
            slug="dictation-spanish",
            title="Switch to Spanish and back",
            track=track,
            minutes=3,
            surfaces=surfaces,
            summary="Move between English and Spanish dictation without opening a window.",
            steps=(
                Step(
                    title="Switch the language",
                    body=(
                        "Use Switch Dictation Language. The choice is remembered, so the "
                        "next time you dictate it starts in the language you used last."
                    ),
                    command=ids["language"],
                    hear='"Español".',
                ),
                Step(
                    title="Come back by voice",
                    body=(
                        "While dictating in Spanish, say cambiar a inglés. In English, say "
                        "switch to Spanish to go the other way."
                    ),
                    hear='"English".',
                    note=(
                        "The first switch can take a moment while the Spanish model loads; "
                        "after that it stays ready for the session."
                    ),
                ),
            ),
            closing="Dictation Status tells you which language and engine are in use.",
        ),
        Tutorial(
            slug="dictation-live-transcript",
            title="Make a live transcript",
            track=track,
            minutes=4,
            surfaces=surfaces,
            summary=(
                "Write down a talk or a meeting as it happens, in its own document, while "
                "you keep working."
            ),
            steps=(
                Step(
                    title="Start a live transcript",
                    body=(
                        "A new document opens and everything the microphone hears is "
                        "written into it, quietly. Please record other people only when "
                        "they have agreed."
                    ),
                    command=ids["transcript"],
                    hear='"Live transcript on, in a new document".',
                ),
                Step(
                    title="Ask how it is going",
                    body=(
                        "Use Dictation Status at any time; the status bar and a braille "
                        "display show the same thing."
                    ),
                    command=ids["status"],
                    hear="How many minutes and how many words.",
                ),
                Step(
                    title="Stop and save",
                    body=(
                        "Use the same command again to stop. The document stays open, "
                        "unsaved, for you to name."
                    ),
                    command=ids["transcript"],
                    hear='"Live transcript stopped" and the number of words.',
                ),
            ),
            closing=(
                "Time stamps in live transcripts, in More Dictation Settings, puts the time "
                "at the start of each paragraph."
            ),
        ),
    )
