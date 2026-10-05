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
            "on from exactly where you stopped, and jump to a time you choose."
        ),
        steps=(
            Step(
                title="Open Continue Listening",
                body=(
                    "Continue Listening, on the Playback menu, is one list of "
                    "everything you started and did not finish: podcast "
                    "episodes, recordings and files on your computer, most "
                    "recent first. A line above the list tells you how many "
                    "there are, and what kinds."
                ),
                keys=("Ctrl+Alt+Shift+L",),
                hear=(
                    "Continue Listening, then how many things you did not finish. Or "
                    "Nothing unfinished. Everything you started, you finished."
                ),
            ),
            Step(
                title="Read a row before you choose it",
                body=(
                    "Arrow down the list. Each row is one sentence: the title, "
                    "where it came from, what kind of thing it is, how far in "
                    "you got, in words, and how much of the whole that is."
                ),
                keys=("Down arrow",),
                hear="A title, then recording or podcast, then 12 minutes in, 40% through.",
            ),
            Step(
                title="Resume it",
                body=(
                    "Press Enter, or the Resume button. It carries on from where "
                    "you stopped, in the same player as everything else, so the "
                    "speed and volume you chose come back with it."
                ),
                keys=("Enter",),
                hear="Resuming at, and the place. 12 minutes 8 seconds, say.",
                check="playing",
            ),
            Step(
                title="Forget one you will never finish",
                body=(
                    "Forget This One forgets your place and takes the row off "
                    "the list. It does not delete anything. The episode or "
                    "recording is still where it was. It just stops being "
                    "offered here."
                ),
                keys=("Alt+F",),
                hear="Forgot where you were in, and the title.",
            ),
            Step(
                title="Ask where you are now",
                body=(
                    "Where Am I tells you how far in you are, how long the whole "
                    "thing is, and which chapter you are in, from any window. "
                    "It always uses words, so you never have to work out what a "
                    "string of numbers means."
                ),
                command="radio.transport.announce_position",
                keys=("Ctrl+Shift+W",),
                hear=(
                    "3 minutes 10 seconds of 18 minutes 40 seconds, and the chapter if "
                    "there is one."
                ),
            ),
            Step(
                title="Go to a time you name",
                body=(
                    "Go to Position, on the Playback menu, asks for Hours, "
                    "Minutes and Seconds, already filled in with where you are "
                    "now. Change the one you want and press Enter. Or type a time "
                    "such as 1:23:45 in the box below, and that is used instead."
                ),
                keys=("Ctrl+Alt+J",),
                hear="Go to Position, then Hours, and the current hour.",
            ),
            Step(
                title="Skip when you only need to get near",
                body=(
                    "Skip Back and Skip Forward move thirty seconds back or "
                    "forward through a recording, an episode or a file, from any "
                    "window, and tell you where you landed. On live radio, the "
                    "same keys in the main window rewind into what was just on "
                    "air."
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
            "Anything you can move around in remembers your place by itself. "
            "This list gets you back to all of them, without having to remember "
            "where each one is."
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
            "Make the most of this tutorials window, and learn which part of the "
            "Help menu to use for which question: the control you are on, the "
            "user guide, what changed, and what is new."
        ),
        steps=(
            Step(
                title="Open the tutorials from anywhere",
                body=(
                    "Tutorials, on the Help menu, opens this window, or brings it "
                    "to the front if it is already open. It can stay open beside "
                    "the window you are practising in, and Ctrl+Tab moves you "
                    "between them."
                ),
                command="radio.tutorials",
                keys=("Ctrl+Alt+F1",),
                hear=(
                    "Quill Radio Tutorials, then the list of tutorials. If some lessons "
                    "are about the window you came from, a sentence saying so."
                ),
            ),
            Step(
                title="Find a lesson by what you want to do",
                body=(
                    "Press Alt+F for the Find a tutorial box and type. A lesson "
                    "shows up if it has all your words, so record tuesday finds "
                    "the lesson on booking recordings. Type here to see only the "
                    "lessons about the window you came from. Enter takes you to "
                    "the list."
                ),
                keys=("Alt+F", "Enter"),
                hear="How many tutorials are showing, then the first one in the list.",
            ),
            Step(
                title="Let a lesson do a step, or watch you do it",
                body=(
                    "Inside a lesson, Try it does the step for you, exactly as "
                    "its key would. With Follow me checked, the lesson notices "
                    "when you have done a step yourself, such as a station "
                    "playing or a favorite added, and moves you on."
                ),
                keys=("Alt+T", "Alt+N"),
                hear="Done, and what it noticed, then the next step read out.",
                note=(
                    "There is no test and no score. If a lesson cannot tell "
                    "whether you did a step, just press Next. Your place in "
                    "every lesson is kept until you ask it to forget."
                ),
            ),
            Step(
                title="Ask about the control you are on",
                body=(
                    "Press F1 in any window to hear what that window is for, and "
                    "then what the control you are on does. It is the quickest "
                    "answer to what is this, and it never takes you away from "
                    "where you were."
                ),
                keys=("F1",),
                hear="What the window is for, then help for the control you are on.",
            ),
            Step(
                title="Open the guide and the release notes",
                body=(
                    "The User Guide covers all of Quill Radio. The Release Notes "
                    "tell you what changed in this version. Each opens in your "
                    "web browser, where your screen reader's heading keys take "
                    "you from section to section."
                ),
                keys=("Ctrl+F1", "Shift+F1"),
                hear="Your browser, with the document's title.",
            ),
            Step(
                title="Keep the whole book of lessons",
                body=(
                    "In the tutorials list, The whole book as a document opens "
                    "every lesson as one page in your browser. You can read it "
                    "straight through, print it, or keep it on another device. "
                    "It is made from these same lessons, so the two always match."
                ),
                keys=("Alt+D",),
                hear="Your browser, with Quill Radio Tutorials as the page title.",
            ),
        ),
        closing=(
            "With F1, the tutorials and the user guide, the answer to how do I "
            "is always right inside Quill Radio. And if something seems wrong, "
            "the lesson Getting unstuck, in the first track, is there for you."
        ),
        then=("getting-unstuck",),
    ),
)
