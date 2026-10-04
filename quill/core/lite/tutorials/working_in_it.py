"""QUILL Lite, track 2: working in a document.

Five lessons, and the first four are about the same problem: doing without a
glance. Selecting text you cannot see the extent of, finding your way back to
where you were, skimming something long, and hearing that a word is wrong
without being interrupted while you type it.

The fifth is the odd one out and says so: asking the AI about a document is the
only thing in this product that sends anything off the computer, so it is
taught rather than discovered -- what has to be true before it will send, what
goes when it does, and what is recorded afterwards.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="selecting-without-looking",
        title="Selecting more than a few words",
        track="working-in-it",
        minutes=6,
        surfaces=("QUILL Lite",),
        summary=(
            "Three different ways to select a stretch of text without seeing it, "
            "and when each one is the easiest."
        ),
        steps=(
            Step(
                title="Take a whole thing in one key",
                body=(
                    "If what you want is a whole word, line, sentence, paragraph "
                    "or block, there is a key for it. You do not need to find "
                    "where it starts. Try it now on the paragraph you are in."
                ),
                command="cmd_select_paragraph",
                hear='"Selected paragraph", and how many words that was.',
            ),
            Step(
                title="Grow and shrink",
                body=(
                    "Starting from whatever you have, you can grow the selection "
                    "one step at a time: word, line, sentence, paragraph, block, "
                    "then everything. You can shrink it back the same way. Each "
                    "step tells you what it took."
                ),
                command="cmd_expand_selection",
                hear="The new scope, and its word count.",
            ),
            Step(
                title="Mark a spot and walk to the end of it",
                body=(
                    "For anything that is not a neat word, line or paragraph. Drop "
                    "a marker where the selection should start. Then move any way "
                    "you like, with the arrows, Find, Go To Line or a bookmark. "
                    "You do not have to hold any key down while you go."
                ),
                command="cmd_start_selection",
                hear="The line and column where the marker went down.",
            ),
            Step(
                title="Finish it, and hear how far it reached",
                body=(
                    "When you reach the end, finish the selection. Everything "
                    "between the marker and where you are now is selected. You "
                    "can even use Find on the way, and it will not spoil it."
                ),
                command="cmd_complete_selection",
                hear="How many words, and the lines it ran between.",
                note=(
                    "Hearing the line numbers is a quick way to check you caught "
                    "the stretch you meant."
                ),
            ),
            Step(
                title="Or hold the Shift down without holding it",
                body=(
                    "Here is a third way. Turn on Extend Selection Mode, and every "
                    "arrow key selects as it moves, just as if you were holding "
                    'Shift. Your screen reader does not say "selected" on every '
                    "press, either. Turn it off the same way when you are done."
                ),
                command="cmd_toggle_extend_selection_mode",
                hear='"Extend selection mode on", and where it started.',
            ),
            Step(
                title="Check what you have before you replace it",
                body=(
                    "Before you type over a selection, it is worth checking it is "
                    "the one you meant, because the next key you type replaces it. "
                    "Say Selection reads it back to you. A long one is summed up "
                    "instead of read in full."
                ),
                command="cmd_say_selection",
                hear="The selection, or a summary of it with its size.",
            ),
        ),
        closing=(
            "Lost a selection by accident? Reselect Last Selection puts it back, "
            "however you made it."
        ),
        then=("finding-your-way-back",),
    ),
    Tutorial(
        slug="finding-your-way-back",
        title="Finding your way back",
        track="working-in-it",
        minutes=5,
        surfaces=("QUILL Lite",),
        summary=(
            "Bookmarks, marks and Go Back. They sound alike, but each one helps "
            "you in a different moment."
        ),
        steps=(
            Step(
                title="Keep a place you mean to come back to",
                body=(
                    "You have nine numbered bookmarks in every file, and they are "
                    "still there tomorrow. A bookmark stays with its words, so if "
                    "you add three paragraphs above it, it is still on the right "
                    "line."
                ),
                command="cmd_set_bookmark_1",
                hear="The bookmark's number, and the line it went on.",
            ),
            Step(
                title="Drop a pin you will forget",
                body=(
                    "A mark is quicker and lighter. It just remembers where you "
                    "were before you went to look something up. There is no number "
                    "and no list. Pop Mark takes you back and then forgets it."
                ),
                command="cmd_set_mark",
                hear="The line, and how many marks you now have.",
            ),
            Step(
                title="Go and look something up, then come back",
                body=(
                    "Move a long way off. Ctrl+End, the end of the document, will "
                    "do. Now pop the mark, and you are back where you were."
                ),
                command="cmd_pop_mark",
                hear="The line you came back to, and how many marks are left.",
            ),
            Step(
                title="Undo the jump",
                body=(
                    "Go Back works like the Back button in a web browser. Every "
                    "jump in QUILL Lite can be undone with it: bookmarks, marks, "
                    "headings, Go To and search results. So you can always get "
                    "back to where you were."
                ),
                command="cmd_back_location",
                hear="Where you were before the jump.",
                note=(
                    "This is handy after following a heading. One key brings you "
                    "back to the paragraph you were writing."
                ),
            ),
        ),
        closing=(
            "Bookmarks are for places you will come back to tomorrow. A mark is "
            "for right now. Go Back is for any jump you did not mean."
        ),
        then=("skimming-something-long",),
    ),
    Tutorial(
        slug="skimming-something-long",
        title="Skimming something long",
        track="working-in-it",
        minutes=5,
        surfaces=("QUILL Lite",),
        summary=(
            "Get a feel for a long document the way a sighted reader does by "
            "scrolling, using its headings instead."
        ),
        steps=(
            Step(
                title="Ask for the shape",
                body=(
                    "The headings list shows every heading in the document, in "
                    "order. Each one tells you its level and its words. Press "
                    "Enter on one to go there."
                ),
                command="cmd_list_headings",
                hear="Each heading, with its level.",
            ),
            Step(
                title="Walk it instead",
                body=(
                    "Next Heading and Previous Heading move from heading to "
                    "heading instead of line by line. Each time you arrive, you "
                    "hear the level and the words."
                ),
                command="cmd_next_heading",
                hear='"Heading 2", and the heading\'s words.',
            ),
            Step(
                title="Skim by section",
                body=(
                    "Moving by section tells you the heading, whether it is "
                    "folded, and **how many lines are under it**. That last part "
                    "is your glance. It tells you a section is huge without "
                    "reading any of it."
                ),
                command="cmd_next_fold",
                hear="The heading, its state, and its size in lines.",
            ),
            Step(
                title="Mark one as dealt with",
                body=(
                    "Folding a section is a note to yourself that you are done "
                    "with it. Nothing is hidden: your cursor still goes in and "
                    "Find still finds things there. You just hear that it is "
                    "folded as you pass."
                ),
                command="cmd_toggle_fold",
                hear="How many lines went with it.",
            ),
            Step(
                title="Rearrange it, if the shape is wrong",
                body=(
                    "The Heading Organizer shows every heading as one list. Tab "
                    "makes a heading one level lower, Shift+Tab one level higher, "
                    "and Move Up and Move Down carry the heading along with "
                    "everything under it."
                ),
                command="cmd_heading_organizer",
                hear="Each heading as you arrow, with a preview of its section.",
                note="Nothing changes until you press Apply, and one Ctrl+Z puts it all back.",
            ),
        ),
        closing=(
            "With headings, a long document becomes something you can move around "
            "in quickly, a section at a time."
        ),
    ),
    Tutorial(
        slug="spelling-without-squiggles",
        title="Spelling, without a red squiggle",
        track="working-in-it",
        minutes=5,
        surfaces=("QUILL Lite",),
        summary=(
            "How QUILL Lite lets you know a word looks wrong without breaking "
            "into your sentence, and the one key that fixes it."
        ),
        steps=(
            Step(
                title="Type something wrong, and keep going",
                body=(
                    "Type a word wrong on purpose and carry on. A moment after you "
                    "finish the word, the status bar notes that it may be "
                    "misspelled. Nothing is spoken over your typing, so you can "
                    "finish your thought first."
                ),
                hear="Nothing, unless you asked for a sound or a sentence in Preferences.",
            ),
            Step(
                title="Fix the word you are standing in",
                body=(
                    "The Applications key is your red squiggle. Put the cursor in "
                    "the word and press it. **The first Down arrow lands on a "
                    "suggestion**. Press Enter to use it. Your cursor stays put and "
                    "no dialog opens."
                ),
                keys=("Applications", "Shift+F10"),
                hear="The suggestions, in order, as you arrow.",
                note=(
                    "Everything else you can do with the word, like ignore it, "
                    "add it, or go to the next or previous one, is in the same "
                    "menu just below the suggestions."
                ),
            ),
            Step(
                title="Teach it a word",
                body=(
                    "You can add a word to your own dictionary, and it is known "
                    "for good. Or add it to the document's dictionary, which "
                    "travels with that file, so anyone who opens it gets the word "
                    "too. That suits a product name better than your surname."
                ),
                hear="Which of the two it was added to, by name.",
            ),
            Step(
                title="Check the whole thing",
                body=(
                    "F7 goes through the document one word at a time. It starts "
                    "where your cursor is, and when it reaches the end it offers "
                    "to carry on from the beginning."
                ),
                command="cmd_spell_review",
                hear="Each word, its suggestions, and a summary of what changed at the end.",
            ),
        ),
        closing=(
            "One more thing: spelling stays quiet in program code and settings "
            "files, whatever your settings say, so you are not told about every "
            "made-up name in them."
        ),
    ),
    Tutorial(
        slug="asking-about-a-document",
        title="Asking a question about a document",
        track="working-in-it",
        minutes=6,
        surfaces=("QUILL Lite",),
        summary=(
            "AI help is the one feature that sends anything off your computer. "
            "Here is how to turn it on, what is sent when you use it, and what "
            "it will not do."
        ),
        steps=(
            Step(
                title="Turn it on, and agree to it separately",
                body=(
                    "AI help stays off until two things are true: the feature is "
                    "switched on, and you have said yes to the privacy agreement. "
                    "These are two separate steps, so nothing is ever sent just "
                    "because a profile, a settings file or someone else switched "
                    "the feature on. Only your own yes counts."
                ),
                command="cmd_ai_privacy",
                hear="The agreement, read out in full before you are asked.",
                note=(
                    "You can reach the agreement three ways: this command, a "
                    "check box in Preferences, or switching AI help on in "
                    "Customize Features. You can always open it to read it, "
                    "whether or not you have agreed."
                ),
            ),
            Step(
                title="Connect this computer, once",
                body=(
                    "There is no account, no password and no email address. You "
                    "are given an eight-character code. Open the web page on "
                    "anything with a browser, this computer or your phone, and "
                    "type the code in. Asking for the code is the first moment "
                    "anything is sent."
                ),
                command="cmd_ai_sign_in",
                hear=(
                    "The code, character by character, and the window confirming "
                    "in place rather than opening another one."
                ),
                note=(
                    "Each computer connects on its own. Signing one out leaves "
                    "the others connected."
                ),
            ),
            Step(
                title="Ask about what is in front of you",
                body=(
                    "Type a question about the open document, like 'what does "
                    "this say about the deadline'. The answer comes back along "
                    "with the part of the document it came from, so you can go "
                    "and read that part yourself."
                ),
                command="cmd_ai_ask_document",
                hear=("The passages it chose, before anything is sent, and then the answer."),
                note=(
                    "Long documents are fine. It does not send the whole file. It "
                    "picks the three passages most likely to answer you and sends "
                    "only those."
                ),
            ),
            Step(
                title="Or hand it a job",
                body=(
                    "The AI pad has five rows. Four of them work on what you have "
                    "selected, or on the paragraph or section you pick with Send "
                    "this much: summarize it, rewrite it clearer and shorter, "
                    "proofread it, or explain a tricky passage. The fifth is the "
                    "question you just asked. Nothing changes in your document by "
                    "itself. The answer comes with Replace My Selection, Insert "
                    "Below and Copy underneath, and you choose."
                ),
                command="cmd_ai_assistant",
                hear="What is about to be sent, before it goes.",
            ),
            Step(
                title="Know what you have left",
                body=(
                    "The service is free, so it has limits. One question can carry "
                    "about two thousand two hundred and fifty words of your "
                    "document, and you get a hundred requests a month. If what you "
                    "asked about is too big, you are told in plain words before "
                    "anything is sent, so you can select less and try again."
                ),
                command="cmd_ai_usage",
                hear="What you have used and what is left.",
                note=(
                    "The limits can change from time to time. Usage always shows "
                    "the numbers that apply to you right now."
                ),
            ),
        ),
        closing=(
            "What is kept is how many requests you made and how big they were. "
            "What you wrote, and what came back, is not kept."
        ),
    ),
)
