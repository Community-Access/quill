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
            "What to do when something is not where you expected, you missed "
            "what was said, or a menu item will not work. Read it once now, so "
            "it feels familiar on the day you need it."
        ),
        steps=(
            Step(
                title="Escape steps back to where you were",
                body=(
                    "Escape closes the window you are in, such as Browse "
                    "Stations, the Player or any list, and your screen reader "
                    "tells you where you landed. Ctrl+W and Ctrl+F4 close those "
                    "windows too. Closing a window never stops the sound, and "
                    "you never lose anything you did not choose to delete."
                ),
                keys=("Escape",),
                hear="The name of the window you are back in, and where you are in it.",
                note=(
                    "The main window works a little differently. There, Ctrl+W "
                    "tucks Quill Radio away in the system tray, and Alt+F4 "
                    "closes it. If you like, you can turn on a setting in "
                    "Preferences so Quill Radio says Entered and Exited as "
                    "windows open and close."
                ),
            ),
            Step(
                title="Hear the last announcement again",
                body=(
                    "Missed what Quill Radio just said? It happens to everyone. "
                    "Repeat Last Announcement says it again. It has no key to "
                    "start with. Find it in the command palette by typing "
                    "repeat, or give it a key of your own in the Keyboard Manager."
                ),
                command="app.repeat_last_announcement",
                hear=(
                    "Whatever Quill Radio last told you, in full. Or No announcement to repeat yet."
                ),
            ),
            Step(
                title="Ask what is playing",
                body=(
                    "What's Playing opens a small Now Playing window. It tells "
                    "you the station, and the song when the station sends one, "
                    "in a box you can arrow through and copy. Press Escape to "
                    "close it. It is the quickest way to find out what is on "
                    "when you come back to the computer."
                ),
                command="radio.whats_playing_details",
                keys=("Ctrl+T",),
                hear="Now Playing, the station's name, then the song if there is one.",
                note=(
                    "If you would rather just hear one sentence with no window, "
                    "type what's playing in the command palette."
                ),
            ),
            Step(
                title="Read the list of what has failed",
                body=(
                    "Recent Problems lists what has gone wrong lately: podcasts "
                    "that could not be checked, downloads that stopped, stations "
                    "that dropped out. Each one says why and when. So if you "
                    "missed a message while it was being spoken, you can still "
                    "find it here."
                ),
                command="app.recent_problems",
                keys=("Ctrl+Alt+Shift+P",),
                hear="Recent Problems, and a count of each kind. Or No recent problems.",
                note=(
                    "Copy All copies the whole list as text, ready to paste into "
                    "a message to support. It includes web addresses and error "
                    "messages, but never passwords, and nothing in it leaves "
                    "your computer unless you send it."
                ),
            ),
            Step(
                title="Find out why a menu item is dimmed",
                body=(
                    "A dimmed item on a row's menu is not a dead end. Each one "
                    "comes with a reason, such as Remove All Downloads: nothing "
                    "is downloaded for this show. You see it in the status bar, "
                    "and screen readers that read menu help will say it. Player "
                    "keys explain themselves too. Where Am I on live radio tells "
                    "you a live stream has no position."
                ),
                keys=("Shift+F10",),
                hear="The item, the word dimmed, and a sentence saying what would make it work.",
            ),
            Step(
                title="Take back the last destructive thing",
                body=(
                    "Undo Last Action brings back what you just removed: an "
                    "unsubscribe, a deleted recording, a Mark All as Played. It "
                    "tells you what came back. Press it again to go back one "
                    "more step, newest first, up to ten steps."
                ),
                command="app.undo_last",
                keys=("Ctrl+Z",),
                hear=("Undid, the action, Brought back, and what came back. Or Nothing to undo."),
                note=(
                    "Anything you can undo ends its message with Ctrl+Z undoes "
                    "this, so you never have to wonder. To pick one particular "
                    "step from the last ten, use Undo History on the Edit menu."
                ),
            ),
            Step(
                title="Report it rather than working around it",
                body=(
                    "If something does not work the way a lesson says it should, "
                    "please tell us. Get Help from Support writes to a real "
                    "person from inside Quill Radio, and includes which version "
                    "you have. Your own email program opens with the message "
                    "ready. Nothing is sent until you send it."
                ),
                keys=("Ctrl+Alt+F2",),
                hear="A form with most of it already filled in.",
            ),
        ),
        closing=(
            "That is your first hour, and you did it. From here you can take the "
            "tracks in any order. Try Finding something to listen to if you want "
            "more stations, or Recording if there is a show you want to catch."
        ),
    ),
)
