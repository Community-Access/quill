"""Every command dictation answers to, with what it does, for the reference.

Moved out of :mod:`~quill.core.windows_dictation.vocabulary` (GATE-11) when
the 2026-10-05 gap plan added the modes, the units, the clips and snippets,
the language switch, and the commands that take words after them. This is
still the one table: the parser matches these phrases, and the in-app
"What can I say?" list and the published command reference are written from
it, so the list somebody reads is the list that works.

Pure and wx-free.
"""

from __future__ import annotations

from quill.core.windows_dictation.vocabulary_types import Command, CommandHelp, PrefixHelp

__all__ = ["COMMAND_HELP", "PREFIX_HELP"]

#: Every whole-phrase command, with what it does, in reference order.
COMMAND_HELP: tuple[CommandHelp, ...] = (
    CommandHelp(
        Command.SCRATCH,
        ("scratch that", "delete that"),
        "Removes the phrase you dictated last. Say it again to remove the one "
        "before. A phrase you have typed into since is left alone.",
        "Correcting",
    ),
    CommandHelp(
        Command.UNDO,
        ("undo that", "undo", "undo last"),
        "The same as pressing Ctrl+Z.",
        "Correcting",
    ),
    CommandHelp(
        Command.SELECT,
        ("select that",),
        "Selects the phrase you dictated last, so you can change or format it "
        "with the keyboard. The next phrase you say replaces it.",
        "Correcting",
    ),
    CommandHelp(
        Command.CAPITALIZE,
        ("capitalize that", "cap that"),
        "Gives every word of the last phrase a capital: meeting notes becomes Meeting Notes.",
        "Correcting",
    ),
    CommandHelp(
        Command.UPPERCASE,
        ("all caps that", "uppercase that"),
        "Puts the last phrase in capitals.",
        "Correcting",
    ),
    CommandHelp(
        Command.LOWERCASE,
        ("no caps that", "lowercase that"),
        "Puts the last phrase in small letters.",
        "Correcting",
    ),
    CommandHelp(
        Command.DELETE_WORD,
        ("delete word", "delete last word"),
        "Deletes the word just before the cursor.",
        "Correcting",
    ),
    CommandHelp(
        Command.DELETE_SENTENCE,
        ("delete sentence", "delete last sentence"),
        "Deletes from the start of the sentence the cursor is in up to the cursor.",
        "Correcting",
    ),
    CommandHelp(
        Command.READ_BACK,
        ("read that", "repeat that"),
        "Reads the last phrase aloud again.",
        "Correcting",
    ),
    CommandHelp(
        Command.CORRECT,
        ("correct that",),
        "Reads the other things the speech engine thought you said, numbered, "
        "when it offers them (Windows speech recognition does). Then say choose "
        "and a number.",
        "Correcting",
    ),
    CommandHelp(
        Command.CHOOSE_1,
        ("choose one", "choose 1"),
        "After correct that, puts the first of the other guesses in place of the last phrase.",
        "Correcting",
    ),
    CommandHelp(
        Command.CHOOSE_2,
        ("choose two", "choose 2"),
        "The same, with the second guess.",
        "Correcting",
    ),
    CommandHelp(
        Command.CHOOSE_3,
        ("choose three", "choose 3"),
        "The same, with the third guess.",
        "Correcting",
    ),
    CommandHelp(
        Command.LINE_START,
        ("go to beginning of line", "go to start of line"),
        "Moves the cursor to the start of the line.",
        "Moving the cursor",
    ),
    CommandHelp(
        Command.LINE_END,
        ("go to end of line",),
        "Moves the cursor to the end of the line.",
        "Moving the cursor",
    ),
    CommandHelp(
        Command.DOCUMENT_START,
        ("go to top", "go to start of document", "go to beginning of document"),
        "Moves the cursor to the start of the document.",
        "Moving the cursor",
    ),
    CommandHelp(
        Command.DOCUMENT_END,
        ("go to bottom", "go to end of document"),
        "Moves the cursor to the end of the document.",
        "Moving the cursor",
    ),
    CommandHelp(
        Command.SPELL_ON,
        ("start spelling", "spell mode", "spelling mode"),
        "Starts spelling mode: every phrase is read as letters until you say "
        "stop spelling. See Spelling below.",
        "Dictation itself",
    ),
    CommandHelp(
        Command.SPELL_OFF,
        ("stop spelling", "end spelling", "spelling off"),
        "Leaves spelling mode.",
        "Dictation itself",
    ),
    CommandHelp(
        Command.HELP,
        ("what can i say", "show commands", "dictation commands"),
        "Opens this list.",
        "Dictation itself",
    ),
    CommandHelp(
        Command.STOP,
        ("stop dictation", "stop dictating", "stop listening"),
        "Stops dictation. With a wake phrase set, dictation goes back to waiting for it.",
        "Dictation itself",
    ),
    # -- 2026-10-05, the gap plan ------------------------------------------- #
    CommandHelp(
        Command.SPELL_THAT,
        ("spell that",),
        "Selects the phrase you dictated last and listens for it spelled out. Say "
        "the letters and they replace it. The fix for a name the engine keeps "
        "getting wrong.",
        "Correcting",
    ),
    CommandHelp(
        Command.PARAGRAPH_START,
        ("go to start of paragraph", "go to beginning of paragraph"),
        "Moves the cursor to the start of the paragraph.",
        "Moving the cursor",
    ),
    CommandHelp(
        Command.PARAGRAPH_END,
        ("go to end of paragraph",),
        "Moves the cursor to the end of the paragraph.",
        "Moving the cursor",
    ),
    CommandHelp(
        Command.SELECT_SENTENCE,
        ("select sentence", "select this sentence"),
        "Selects the sentence the cursor is in.",
        "Selecting",
    ),
    CommandHelp(
        Command.SELECT_LINE,
        ("select line", "select this line"),
        "Selects the line the cursor is on.",
        "Selecting",
    ),
    CommandHelp(
        Command.SELECT_PARAGRAPH,
        ("select paragraph", "select this paragraph"),
        "Selects the paragraph the cursor is in.",
        "Selecting",
    ),
    CommandHelp(
        Command.SELECT_NEXT,
        ("select again", "select next"),
        "After select, go to or correct with words, moves on to the next place those words appear.",
        "Selecting",
    ),
    CommandHelp(
        Command.SELECT_PREVIOUS,
        ("select previous",),
        "The same, going back to the place before.",
        "Selecting",
    ),
    CommandHelp(
        Command.CAPS_ON,
        ("caps on", "capitals on"),
        "Every word you say starts with a capital until you say caps off. Handy "
        "for titles and names.",
        "Capitals and spacing",
    ),
    CommandHelp(
        Command.CAPS_OFF,
        ("caps off", "capitals off"),
        "Words go back to ordinary capitals.",
        "Capitals and spacing",
    ),
    CommandHelp(
        Command.ALL_CAPS_ON,
        ("all caps on",),
        "Everything you say is written in capitals until you say all caps off.",
        "Capitals and spacing",
    ),
    CommandHelp(
        Command.ALL_CAPS_OFF,
        ("all caps off",),
        "Back to ordinary capitals.",
        "Capitals and spacing",
    ),
    CommandHelp(
        Command.NO_SPACE_ON,
        ("no space on",),
        "Words are written joined together with no spaces until you say no space "
        "off. Handy for web addresses and file names.",
        "Capitals and spacing",
    ),
    CommandHelp(
        Command.NO_SPACE_OFF,
        ("no space off",),
        "Spaces between words come back.",
        "Capitals and spacing",
    ),
    CommandHelp(
        Command.COPY_ALL,
        ("copy all", "copy everything", "copy document"),
        "Copies the whole document, the same as Copy All on the Edit menu. Nothing is selected.",
        "Clips, snippets and copying",
    ),
    CommandHelp(
        Command.COPY_THAT,
        ("copy that",),
        "Copies the phrase you dictated last.",
        "Clips, snippets and copying",
    ),
    CommandHelp(
        Command.SHOW_CLIPS,
        ("show clips", "open copy tray", "show copy tray"),
        "Opens the Copy Tray, where you choose a slot to paste.",
        "Clips, snippets and copying",
    ),
    CommandHelp(
        Command.SHOW_SNIPPETS,
        ("show snippets",),
        "Opens the list of snippets to choose from.",
        "Clips, snippets and copying",
    ),
    CommandHelp(
        Command.SWITCH_SPANISH,
        ("switch to spanish", "spanish dictation"),
        "Dictate in Spanish from now on, the same as Switch Dictation Language. "
        "In Spanish, cambiar a inglés or dictado en inglés comes back.",
        "Dictation itself",
    ),
    CommandHelp(
        Command.SWITCH_ENGLISH,
        ("switch to english", "english dictation"),
        "Dictate in English from now on.",
        "Dictation itself",
    ),
)

#: Commands said with words after them, in reference order (dict.md 3.2, 3.3,
#: 3.4 and 3.8). Matched only at the start of a phrase, and only after every
#: whole-phrase command has had its chance.
PREFIX_HELP: tuple[PrefixHelp, ...] = (
    PrefixHelp(
        Command.SELECT_WORDS,
        ("select",),
        "words in your document",
        "Selects those words, looking first just before the cursor and then after "
        "it. Say select, the first words, through, and the last words to select "
        "everything between them. What you say next replaces the selection. If the "
        "words are not there, what you said is written as text instead.",
        "Selecting",
    ),
    PrefixHelp(
        Command.GO_TO_WORDS,
        ("go to", "go before"),
        "words in your document",
        "Puts the cursor just before those words.",
        "Selecting",
    ),
    PrefixHelp(
        Command.GO_AFTER_WORDS,
        ("go after",),
        "words in your document",
        "Puts the cursor just after those words.",
        "Selecting",
    ),
    PrefixHelp(
        Command.CORRECT_WORDS,
        ("correct",),
        "words in your document",
        "Selects those words so that what you say next replaces them.",
        "Selecting",
    ),
    PrefixHelp(
        Command.SPELL_WORDS,
        ("spell",),
        "letters",
        "Spells one word without going into spelling mode: spell bravo alpha delta writes bad.",
        "Correcting",
    ),
    PrefixHelp(
        Command.PASTE_SLOT,
        ("paste clip", "paste slot"),
        "a number from one to twelve",
        "Pastes that slot of the Copy Tray.",
        "Clips, snippets and copying",
    ),
    PrefixHelp(
        Command.INSERT_SNIPPET,
        ("insert snippet",),
        "a snippet's name",
        "Puts in the snippet with that name. If more than one matches, you hear "
        "how many and the snippet list opens.",
        "Clips, snippets and copying",
    ),
    PrefixHelp(
        Command.EXPAND,
        ("insert abbreviation", "expand abbreviation"),
        "an abbreviation",
        "Writes what that abbreviation expands to, as if you had typed it.",
        "Clips, snippets and copying",
    ),
    PrefixHelp(
        Command.USE_CONTEXT,
        ("dictation context",),
        "the name of a saved context",
        "Uses that saved context for this document, as if you had chosen it in "
        "Dictation Context for This Document.",
        "Dictation itself",
    ),
)
