"""Track 1, concluded: getting unstuck.

The last lesson of "Your first hour", in its own module only so that
:mod:`first_hour` stays under the 600-line cap (split 2026-09-25). It is listed
straight after :mod:`first_hour` in the catalogue, so the track reads in the
same order it always did: the lesson somebody reads at the moment they need it
most, and can least afford a long one, still comes last.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="getting-unstuck",
        title="Getting unstuck",
        track="first-hour",
        minutes=4,
        surfaces=("Quill Radio",),
        summary=(
            "The short list to reach for when something is not where you expected, "
            "you missed what was said, or a menu item will not press. Read it once "
            "now so it is familiar when you need it."
        ),
        steps=(
            Step(
                title="Escape steps back to where you were",
                body=(
                    "Escape closes the window you are in -- Browse Stations, the "
                    "Player, any list -- and your screen reader names the window "
                    "you land back in. Ctrl+W and Ctrl+F4 close those windows too. "
                    "Closing one never stops playback and never loses anything "
                    "you have not deliberately deleted."
                ),
                keys=("Escape",),
                hear="The name of the window you are back in, and the control that has focus.",
                note=(
                    "The main window is the exception: there Ctrl+W sends Quill "
                    "Radio to the tray, and Alt+F4 exits. Preferences can make "
                    "Quill Radio say Entered and Exited as windows open and close, "
                    "if you want that as well."
                ),
            ),
            Step(
                title="Hear the last announcement again",
                body=(
                    "Speech disappears the moment it finishes, which is right "
                    "almost always and wrong the one time the sentence you needed "
                    "went past. Repeat Last Announcement says it again. It has no "
                    "key out of the box: find it in the command palette by typing "
                    "repeat, or give it one in the Keyboard Manager."
                ),
                command="app.repeat_last_announcement",
                hear=(
                    "Whatever Quill Radio last told you, in full -- or No announcement to repeat "
                    "yet."
                ),
            ),
            Step(
                title="Ask what is playing",
                body=(
                    "What's Playing opens a small Now Playing window: the station, "
                    "and the track when the stream carries one, in a box you can "
                    "arrow through and copy. Escape closes it. It is the fastest "
                    "way to work out what you are listening to after coming back "
                    "to the machine."
                ),
                command="radio.whats_playing_details",
                keys=("Ctrl+T",),
                hear="Now Playing, the station's name, then the track if there is one.",
                note=(
                    "For one spoken sentence and no window, type what's playing in "
                    "the command palette."
                ),
            ),
            Step(
                title="Read the list of what has failed",
                body=(
                    "Recent Problems is a list of what has gone wrong recently -- "
                    "feeds that could not be read, downloads that died, streams "
                    "that dropped -- each with its reason and the time. It exists "
                    "because a spoken failure you missed used to be gone for good."
                ),
                command="app.recent_problems",
                keys=("Ctrl+Alt+Shift+P",),
                hear="Recent Problems, and a count by kind -- or No recent problems.",
                note=(
                    "Copy All takes the list as text, which is what to paste into "
                    "a bug report. It carries addresses and error messages, never "
                    "passwords, and nothing in it leaves this computer."
                ),
            ),
            Step(
                title="Find out why a menu item is dimmed",
                body=(
                    "A greyed item on a row's own menu is not a dead end. Each "
                    "dimmed item carries its reason -- Remove All Downloads: "
                    "nothing is downloaded for this show -- shown in the status "
                    "bar and spoken by readers that voice menu help. A transport "
                    "key that cannot act says why, too: Where Am I on live radio "
                    "explains that a live stream has no position."
                ),
                keys=("Shift+F10",),
                hear="The item, the word dimmed, and the sentence saying what would un-dim it.",
            ),
            Step(
                title="Take back the last destructive thing",
                body=(
                    "Undo Last Action brings back the last thing you removed: an "
                    "unsubscribe, a deleted recording, a Mark All as Played. It "
                    "says what it brought back. It is one step and not a stack, on "
                    "purpose -- an undo you have to count presses of is a puzzle."
                ),
                command="app.undo_last",
                keys=("Ctrl+Z",),
                hear="Undid, the action, Brought back, and what came back -- or Nothing to undo.",
                note=(
                    "Every action that can be undone ends its own announcement "
                    "with Ctrl+Z undoes this, so you never have to remember "
                    "whether this particular verb was one of them."
                ),
            ),
            Step(
                title="Report it rather than working around it",
                body=(
                    "If something does not happen the way a lesson says it should, "
                    "that is worth reporting. Get Help from Support writes to a "
                    "person from inside the app, stamped with this app's "
                    "version. Your own mail program opens with it ready; "
                    "nothing is sent until you send it."
                ),
                keys=("Ctrl+Alt+F2",),
                hear="A form with most of it already filled in.",
            ),
        ),
        closing=(
            "That is the first hour. From here the tracks are independent: go to "
            "Finding something to listen to if you want more stations, or to "
            "Recording if you have a show to catch."
        ),
    ),
)
