"""Track 6, continued: picking things up again, and the help that ships.

Two lessons "Living with it" was missing. Continue Listening and Go to
Position are the pair somebody needs the first evening they come back to a
half-heard episode, and neither had a step anywhere. The Help menu's own doors
-- these tutorials included -- were only ever mentioned in passing, which left
the one window that can walk somebody through the rest untaught.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="pick-up-where-you-left-off",
        title="Pick up where you left off",
        track="living",
        minutes=5,
        surfaces=("Quill Radio", "Continue Listening"),
        summary=(
            "Find everything you started and did not finish in one list, carry "
            "on from the exact place, and move to a time you name rather than "
            "one you skip towards."
        ),
        steps=(
            Step(
                title="Open Continue Listening",
                body=(
                    "Continue Listening, on the Playback menu, is one list of "
                    "everything you started and did not finish: podcast "
                    "episodes, recordings and files on this computer, most "
                    "recent first. A line above the list says how many, and "
                    "across what."
                ),
                keys=("Ctrl+Alt+Shift+L",),
                hear=(
                    "Continue Listening, then how many things you did not finish, or "
                    "Nothing unfinished. Everything you started, you finished."
                ),
            ),
            Step(
                title="Read a row before you choose it",
                body=(
                    "Arrow down the list. Each row is one sentence: the title, "
                    "where it came from, what kind of thing it is, how far in you "
                    "got in words rather than a timecode, and how much of it that "
                    "is."
                ),
                keys=("Down arrow",),
                hear="A title, then recording or podcast, then 12 minutes in, 40% through.",
            ),
            Step(
                title="Resume it",
                body=(
                    "Press Enter, or the Resume button. It starts from where you "
                    "stopped, through the same player as everything else, so the "
                    "speed you chose and the volume you set come back with it."
                ),
                keys=("Enter",),
                hear="Resuming at, and the place -- 12 minutes 8 seconds, say.",
                check="playing",
            ),
            Step(
                title="Forget one you will never finish",
                body=(
                    "Forget This One drops the saved place and takes the row out "
                    "of the list. It deletes nothing -- the episode or the "
                    "recording is still where it was -- it only stops being "
                    "offered here."
                ),
                keys=("Alt+F",),
                hear="Forgot where you were in, and the title.",
            ),
            Step(
                title="Ask where you are now",
                body=(
                    "Where Am I says the position, the whole length and the "
                    "chapter, from any window. Words, never a timecode, because "
                    "a pair of numbers read aloud is ambiguous until you already "
                    "know it is a time."
                ),
                command="radio.transport.announce_position",
                keys=("Ctrl+Shift+W",),
                hear=(
                    "3 minutes 10 seconds of 18 minutes 40 seconds, and the chapter "
                    "if there is one."
                ),
            ),
            Step(
                title="Go to a time you name",
                body=(
                    "Go to Position, on the Playback menu, asks for Hours, "
                    "Minutes and Seconds, already filled with where you are now. "
                    "Change the one you mean and press Enter. A timecode such as "
                    "1:23:45 typed in the box below wins over the three fields."
                ),
                keys=("Ctrl+Alt+J",),
                hear="Go to Position, then Hours, and the current hour.",
            ),
            Step(
                title="Skip when you only need to get near",
                body=(
                    "Skip Back and Skip Forward move thirty seconds either way "
                    "through a recording, an episode or a file, from any window, "
                    "and say where they landed. On live radio the same keys in the "
                    "main window rewind into what was just broadcast instead."
                ),
                keys=("Ctrl+Shift+Left", "Ctrl+Shift+Right"),
                hear="The new position, in words: 3 minutes 40 seconds of 18 minutes 40 seconds.",
                note=(
                    "Rewinding live radio, and getting back to live, has its own "
                    "step in the lesson called Shape the sound."
                ),
            ),
        ),
        closing=(
            "Anything with a timeline keeps its place on its own; this list is "
            "how you get back to all of them without remembering where each "
            "one lives."
        ),
        then=("keep-a-moment",),
    ),
    Tutorial(
        slug="help-that-ships",
        title="The help that comes with it",
        track="living",
        minutes=4,
        surfaces=("Quill Radio", "Quill Radio Tutorials"),
        summary=(
            "Get the most out of this tutorial window, and know which Help "
            "menu door answers which question: the control under your "
            "fingers, the guide, what changed, and what is new."
        ),
        steps=(
            Step(
                title="Open the tutorials from anywhere",
                body=(
                    "Tutorials, on the Help menu, opens this window, or brings it "
                    "to the front. It is a real window rather than a dialog, so it "
                    "can stay open beside the one you are practising in, and "
                    "Ctrl+Tab moves between them."
                ),
                command="radio.tutorials",
                keys=("Ctrl+Alt+F1",),
                hear=(
                    "Quill Radio Tutorials, then the tutorials tree -- and, when some "
                    "lessons are about the window you came from, a sentence saying so."
                ),
            ),
            Step(
                title="Find a lesson by what you want to do",
                body=(
                    "Press Alt+F for the Find a tutorial box and type. Every word "
                    "has to appear somewhere in a lesson, so record tuesday finds "
                    "the scheduling lesson; the word here lists only the lessons "
                    "about the window you came from. Enter takes you to the tree."
                ),
                keys=("Alt+F", "Enter"),
                hear="How many tutorials are showing, then the first one in the tree.",
            ),
            Step(
                title="Let a lesson do a step, or watch you do it",
                body=(
                    "Inside a lesson, Try it runs the step's command exactly as "
                    "its key would. With Follow me ticked, the lesson notices "
                    "when you have done a step yourself -- a station playing, a "
                    "favorite added -- and moves you on."
                ),
                keys=("Alt+T", "Alt+N"),
                hear="Done, and what it noticed, then the next step read out.",
                note=(
                    "Nothing is graded. A step the lesson cannot watch for costs "
                    "you one press of Next, and your place in every lesson is "
                    "kept until you ask it to forget."
                ),
            ),
            Step(
                title="Ask about the control you are on",
                body=(
                    "F1 in any window says what that window is for and then what "
                    "the focused control does. It is the fastest answer to what "
                    "is this, and it never takes you away from where you were."
                ),
                keys=("F1",),
                hear="The window's purpose, then the control's own help.",
            ),
            Step(
                title="Open the guide and the release notes",
                body=(
                    "The User Guide is the whole app written down; the Release "
                    "Notes say what changed in this version. Each opens in your "
                    "web browser, where your screen reader's heading keys move "
                    "through it."
                ),
                keys=("Ctrl+F1", "Shift+F1"),
                hear="Your browser, with the document's title.",
            ),
            Step(
                title="Keep the whole book of lessons",
                body=(
                    "On the tutorial contents, The whole book as a document opens "
                    "every lesson as one page in your browser -- to read straight "
                    "through, print, or keep on another device. It is made from "
                    "these same lessons, so it never says anything they do not."
                ),
                keys=("Alt+D",),
                hear="Your browser, with Quill Radio Tutorials as the page title.",
            ),
        ),
        closing=(
            "Between F1, the tutorials and the guide, the answer to how do I is "
            "always inside the app. Getting unstuck, in the first track, covers "
            "what to do when the answer is that something is wrong."
        ),
        then=("getting-unstuck",),
    ),
)
