"""QuillLite, track 2: working in a document.

Four lessons, and every one of them is about the same problem: doing without a
glance. Selecting text you cannot see the extent of, finding your way back to
where you were, skimming something long, and hearing that a word is wrong
without being interrupted while you type it.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="selecting-without-looking",
        title="Selecting more than a few words",
        track="working-in-it",
        minutes=6,
        surfaces=("QuillLite",),
        summary=(
            "Three genuinely different answers to the same problem, and when "
            "each one is the right one."
        ),
        steps=(
            Step(
                title="Take a whole thing in one key",
                body=(
                    "When what you want lines up with a word, a line, a "
                    "paragraph, a sentence or a block, there is a key for it and "
                    "you do not have to know where it starts."
                ),
                command="cmd_select_paragraph",
                hear='"Selected paragraph", and how many words that was.',
            ),
            Step(
                title="Grow and shrink",
                body=(
                    "From whatever you have, step outwards a level at a time -- "
                    "word, line, sentence, paragraph, block, everything -- and "
                    "back in again. Each step says the scope it took."
                ),
                command="cmd_expand_selection",
                hear="The new scope, and its word count.",
            ),
            Step(
                title="Mark a spot and walk to the end of it",
                body=(
                    "For anything that does not line up with a structure. Drop a "
                    "marker, then move however you like -- arrows, Find, Go To "
                    "Line, a bookmark -- and take everything between. No modifier "
                    "held the whole way."
                ),
                command="cmd_start_selection",
                hear="The line and column where the marker went down.",
            ),
            Step(
                title="Finish it, and hear how far it reached",
                body=(
                    "The span is worked out now, from the marker and where you "
                    "actually are. That is why you can use Find in between: its "
                    "own selection does not get in the way."
                ),
                command="cmd_complete_selection",
                hear="How many words, and the lines it ran between.",
                note=(
                    "That line range is the only selection that carries one, "
                    "because it is the only one whose reach you cannot work out "
                    "from its name."
                ),
            ),
            Step(
                title="Or hold the Shift down without holding it",
                body=(
                    "Extend Selection Mode is the third answer: turn it on and "
                    "every arrow extends instead of moving, with no modifier and "
                    'no "selected" from your screen reader on every press.'
                ),
                command="cmd_toggle_extend_selection_mode",
                hear='"Extend selection mode on", and where it started.',
            ),
            Step(
                title="Check what you have before you replace it",
                body=(
                    "There is no glance that confirms a selection is the one you "
                    "meant, and the next character you type replaces it. Say "
                    "Selection reads it back; long ones are summarised rather "
                    "than read in full."
                ),
                command="cmd_say_selection",
                hear="The selection, or a summary of it with its size.",
            ),
        ),
        closing=(
            "Put back the one you just lost with Reselect. It remembers every "
            "way of selecting, not only the marker."
        ),
        then=("finding-your-way-back",),
    ),
    Tutorial(
        slug="finding-your-way-back",
        title="Finding your way back",
        track="working-in-it",
        minutes=5,
        surfaces=("QuillLite",),
        summary=(
            "Bookmarks, marks and the Back key -- three things that sound alike "
            "and answer different questions."
        ),
        steps=(
            Step(
                title="Keep a place you mean to come back to",
                body=(
                    "Nine numbered bookmarks, per file, and they are still there "
                    "tomorrow. A bookmark survives editing: it remembers the words "
                    "around it, so inserting three paragraphs above one does not "
                    "move it off its line."
                ),
                command="cmd_set_bookmark_1",
                hear="The bookmark's number, and the line it went on.",
            ),
            Step(
                title="Drop a pin you will forget",
                body=(
                    "A mark is different: it is where you were standing before you "
                    "went to look something up. No number, no label, no list. Pop "
                    "Mark uses it up getting back."
                ),
                command="cmd_set_mark",
                hear="The line, and how many marks you now have.",
            ),
            Step(
                title="Go and look something up, then come back",
                body=("Move a long way off -- Ctrl+End will do -- and pop the mark."),
                command="cmd_pop_mark",
                hear="The line you came back to, and how many marks are left.",
            ),
            Step(
                title="Undo the jump",
                body=(
                    "Back is the undo for navigation. Every jump in QuillLite "
                    "goes through it -- bookmarks, marks, headings, Go To, search "
                    "results -- so there is no jump it cannot take you back from."
                ),
                command="cmd_back_location",
                hear="Where you were before the jump.",
                note=(
                    "Without this, every jump is one-way: you followed a heading "
                    "and have no way back to the paragraph you were writing except "
                    "a line number nobody told you."
                ),
            ),
        ),
        then=("skimming-something-long",),
    ),
    Tutorial(
        slug="skimming-something-long",
        title="Skimming something long",
        track="working-in-it",
        minutes=5,
        surfaces=("QuillLite",),
        summary=(
            "What a sighted reader gets from scrolling and glancing, and the "
            "three ways to get it without one."
        ),
        steps=(
            Step(
                title="Ask for the shape",
                body=(
                    "The headings list is every heading in the document, in order, "
                    "each reading its level and its text. Enter goes there."
                ),
                command="cmd_list_headings",
                hear="Each heading, with its level.",
            ),
            Step(
                title="Walk it instead",
                body=(
                    "Next and Previous Heading move by structure rather than by "
                    "line, and each arrival says the level and the text."
                ),
                command="cmd_next_heading",
                hear='"Heading 2", and the heading\'s words.',
            ),
            Step(
                title="Skim by section",
                body=(
                    "Walking sections says the heading, whether it is folded, and "
                    "**how many lines are under it**. That last part is the glance: "
                    "it is how you find out a section is enormous without reading "
                    "any of it."
                ),
                command="cmd_next_fold",
                hear="The heading, its state, and its size in lines.",
            ),
            Step(
                title="Mark one as dealt with",
                body=(
                    "Folding a section is a note to yourself. Nothing is hidden "
                    "from the cursor and Find still finds things inside it -- you "
                    "simply hear that it is folded when you pass by."
                ),
                command="cmd_toggle_fold",
                hear="How many lines went with it.",
            ),
            Step(
                title="Rearrange it, if the shape is wrong",
                body=(
                    "The Heading Organizer is every heading as one list. Tab "
                    "demotes, Shift+Tab promotes, and Move Up and Move Down take "
                    "the heading and everything under it."
                ),
                command="cmd_heading_organizer",
                hear="Each heading as you arrow, with a preview of its section.",
                note="Nothing changes until Apply, and one Ctrl+Z puts it all back.",
            ),
        ),
    ),
    Tutorial(
        slug="spelling-without-squiggles",
        title="Spelling, without a red squiggle",
        track="working-in-it",
        minutes=5,
        surfaces=("QuillLite",),
        summary=(
            "How QuillLite tells you a word is wrong without interrupting the "
            "sentence you are writing, and the one key that fixes it."
        ),
        steps=(
            Step(
                title="Type something wrong, and keep going",
                body=(
                    "A moment after you finish the word, the status bar says it "
                    "may be misspelled. It is not spoken over your typing, because "
                    "a spell checker that interrupts the sentence you are writing "
                    "is one people switch off."
                ),
                hear="Nothing, unless you asked for a sound or a sentence in Preferences.",
            ),
            Step(
                title="Fix the word you are standing in",
                body=(
                    "The Applications key is your squiggle. Press it with the "
                    "cursor in the word, and **the first Down arrow lands on a "
                    "suggestion**. Enter replaces it; the cursor does not move and "
                    "no dialog opens."
                ),
                keys=("Applications", "Shift+F10"),
                hear="The suggestions, in order, as you arrow.",
                note=(
                    "Everything else about the word -- ignore, teach, next, "
                    "previous -- is one row below the suggestions, in the same "
                    "place every time."
                ),
            ),
            Step(
                title="Teach it a word",
                body=(
                    "Your own dictionary keeps it for good. The document's own "
                    "keeps it beside the file, so anybody who opens that file gets "
                    "it too -- which is the right home for a product name and the "
                    "wrong one for your surname."
                ),
                hear="Which of the two it was added to, by name.",
            ),
            Step(
                title="Check the whole thing",
                body=(
                    "F7 walks the document one word at a time. It starts where "
                    "your cursor is and offers to carry on from the beginning when "
                    "it reaches the end."
                ),
                command="cmd_spell_review",
                hear="Each word, its suggestions, and a summary of what changed at the end.",
            ),
        ),
        closing=(
            "Spelling stays quiet in source and configuration files whatever the "
            "settings say -- every identifier in one would be a false alarm."
        ),
    ),
)
