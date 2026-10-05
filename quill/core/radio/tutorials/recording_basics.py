"""Track 4, first half: capture what is on, and book what is not on yet.

Two lessons. The first is one keypress and its consequences -- where the file
went, what the status bar was telling you, how to play it back and how to
throw it away. The second is the form people get wrong exactly once, because
Add Schedule is the button that commits the entry you have just described and
not the button that starts a new one.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="record-what-is-on",
        title="Record what is on now",
        track="recording",
        minutes=6,
        surfaces=("Quill Radio", "Radio Recordings"),
        summary=(
            "Record the station you are listening to, stop it, find the file and "
            "play it back. You will also learn what the Record item in the "
            "status bar is telling you."
        ),
        steps=(
            Step(
                title="Put something on first",
                body=(
                    "Record Now records whatever you are listening to, so you "
                    "need something playing first. Play any station you like and "
                    "leave it on."
                ),
                command="radio.play_last",
                hear="The station's name as it starts playing.",
                check="playing",
            ),
            Step(
                title="Start the recording",
                body=(
                    "Record Now starts recording the station that is on, and "
                    "says so with the station's name. You will also find the "
                    "Record item in the status bar now says Stop Recording with "
                    "a time, and the now playing line mentions it too."
                ),
                command="radio.record_toggle",
                hear="Recording started, and the station's name, over the start-recording sound.",
                check="recording-started",
            ),
            Step(
                title="Read what the Record cell is counting",
                body=(
                    "Press F6 in the main window and arrow to the Record item. "
                    "When you start with Record Now, it counts up, such as 18 "
                    "min so far, because you did not set a length. If you had "
                    "asked for an hour, it would count down instead."
                ),
                keys=("F6", "Right arrow"),
                hear="Stop Recording, and the time so far in brackets: 18 min so far.",
            ),
            Step(
                title="Stop it, and hear where it went",
                body=(
                    "Use the same command to stop recording the station you are "
                    "listening to. Once the file is saved, Quill Radio tells you "
                    "its name. If you are also recording a different station in "
                    "the background, this does not stop that one. You stop those "
                    "from the Recordings window."
                ),
                command="radio.record_toggle",
                hear="Stopping recording, then Recording saved and the file's name.",
                check="recording-finished",
            ),
            Step(
                title="Open the recordings list",
                body=(
                    "Radio Recordings lists everything you have recorded, newest "
                    "first, so yours is near the top. The summary line tells you "
                    "what is happening first: whether anything is recording, "
                    "what is scheduled next, how many recordings you have, and "
                    "which folder they are in."
                ),
                command="radio.recordings",
                hear="Radio Recordings, then the list and the row you land on.",
                check="window:Radio Recordings",
            ),
            Step(
                title="Play it back",
                body=(
                    "Press Enter on the row. It plays in Quill Radio's own "
                    "player, so all the player keys you already know work on it, "
                    "volume included."
                ),
                keys=("Enter",),
                hear="Playing recording, the recording's name, then the recording itself.",
            ),
            Step(
                title="Throw it away",
                body=(
                    "Press Delete and confirm. You land on the next recording in "
                    "the list, so deleting several in a row is quick and easy."
                ),
                keys=("Delete",),
                hear=(
                    "A question naming the recording, then Removed recording and its "
                    "name, and the row that took its place."
                ),
                note=(
                    "Changed your mind? Undo Last Action brings a deleted "
                    "recording back, the file itself and not just its name in "
                    "the list."
                ),
            ),
            Step(
                title="Decide where recordings live",
                body=(
                    "Recording Settings, on the Record menu, is where you choose "
                    "the format (MP3, OGG Vorbis, FLAC, WAV or the raw stream), "
                    "the quality, how files are named, and which folder they go "
                    "in. Unless you change it, recordings go in Music\\Quill "
                    "Radio Recordings in your user folder."
                ),
                command="radio.recording_settings",
                hear="Recording Settings, then Format and the format chosen now.",
                note=(
                    "You can also set a temporary folder. Recordings are made "
                    "there and moved when they finish, so you never find a half "
                    "finished file among your recordings."
                ),
            ),
        ),
        closing=(
            "One key starts it, the same key stops it, and the file is easy to "
            "find. Next, learn how to record a show while you are out."
        ),
        then=("book-a-show",),
    ),
    Tutorial(
        slug="book-a-show",
        title="Book a show that has not started yet",
        track="recording",
        minutes=8,
        surfaces=("Schedule Recording", "Quill Radio"),
        summary=(
            "Set up a recording for later and get it right the first time, time "
            "zones included. Then change, copy, pause and remove your bookings "
            "without starting over."
        ),
        steps=(
            Step(
                title="Learn the one rule before you open the window",
                body=(
                    "Fill in the details first, and choose Add Schedule last. "
                    "Add Schedule saves the booking you have just described. It "
                    "does not start a new blank form. Keep that in mind and this "
                    "window is easy."
                ),
                hear="Nothing yet. Just keep this one in mind.",
            ),
            Step(
                title="Open the schedule",
                body=(
                    "Schedule Recording has a list above a form. The list, "
                    "Scheduled recordings, shows what you have booked, with the "
                    "soonest first. The form underneath, Add a new schedule, is "
                    "where you describe the next one."
                ),
                command="radio.schedule_recording",
                hear="Schedule Recording, then the Scheduled recordings list.",
                check="window:Schedule Recording",
            ),
            Step(
                title="Pick the station from your favorites",
                body=(
                    "Tab to Favorite station and arrow to one. Choosing a "
                    "favorite fills in both Station name and Stream URL for you. "
                    "If the station you want is not there, add it to your "
                    "favorites first. Or, for a one-off, type the name and paste "
                    "the address yourself. You can still edit both boxes either "
                    "way."
                ),
                keys=("Tab", "Down arrow"),
                hear="The station name and stream filled in for you.",
            ),
            Step(
                title="Enter the time the way you think of it",
                body=(
                    "In the Time box, 7:30 PM and 19:30 both work, so type it "
                    "whichever way feels natural. Then check Time zone. Leave it "
                    "on (local time) for a show at a time on your own clock. If "
                    "the show's time is given in another time zone, choose that "
                    "zone instead."
                ),
                hear="Time (7:30 PM or 19:30), edit. Then Time zone, reading (local time).",
                note=(
                    "The list shows each booking's time with its time zone, so "
                    "you can tell two similar bookings apart easily."
                ),
            ),
            Step(
                title="Choose how often, and how long",
                body=(
                    "Repeats offers Once (with a date), Daily, or Weekly (with a "
                    "day). Then set the length in Duration hours and minutes. A "
                    "three-hour show is just 3 and 0. No sums needed."
                ),
                hear="Repeats, combo box, then each duration box with its number.",
            ),
            Step(
                title="Commit it",
                body=(
                    "Choose Add Schedule. Your booking appears in the list, you "
                    "land on it, and the form clears ready for the next one. So "
                    "you always know it worked."
                ),
                hear=(
                    "Scheduled recording added for, and the station. Then the booking "
                    "itself as you land on it."
                ),
            ),
            Step(
                title="Change one without deleting it",
                body=(
                    "Select a booking and choose Edit. The form fills in, the Add "
                    "button changes to Save Changes, and the status line names "
                    "the booking you are changing. So you always know you are "
                    "editing, not adding. New cancels the edit."
                ),
                keys=("Alt+E",),
                hear="Station name, holding the booking's name, ready for you to edit.",
            ),
            Step(
                title="Make a similar one",
                body=(
                    "Duplicate, next to Edit, starts a new booking filled in "
                    "from the selected one, with (copy) after its name. It is a "
                    "handy start for another day or a second time. It keeps the "
                    "same stream until you change it, so pick a different "
                    "favorite if you want a different station."
                ),
                keys=("Alt+P",),
                hear="Station name, holding the original name with (copy) after it.",
            ),
            Step(
                title="Turn one off without losing it",
                body=(
                    "The Disable button turns a booking off without deleting "
                    "it. It then reads (disabled) in the list and will not "
                    "record, and the button changes to Enable. Remove deletes a "
                    "booking and names it first. The Delete key in the list does "
                    "the same."
                ),
                keys=("Alt+L",),
                hear="The station's name, and disabled. Or enabled.",
            ),
            Step(
                title="Know what a schedule needs from you",
                body=(
                    "Quill Radio needs to be running for a booked recording to "
                    "happen. Running in the tray is fine. If Quill Radio starts "
                    "late, it still records the rest of the show, and when you "
                    "open it, it catches up on anything still on the air. If a "
                    "whole show passed while Quill Radio was closed, it is "
                    "missed, and Quill Radio tells you next time you open it."
                ),
                hear=(
                    "Next time you open Quill Radio: what was missed, up to three by name "
                    "and the rest counted."
                ),
                note=(
                    "Three settings in Preferences help with a sleeping computer, "
                    "and all three are on to start with: Keep the computer awake "
                    "before a scheduled recording, Wake the computer for a "
                    "scheduled recording, and Keep the computer awake while "
                    "playing or recording."
                ),
            ),
        ),
        closing=(
            "Your show will now record itself while you are out. Well done. The "
            "next lesson shows you how to record several at once, and what "
            "happens if the connection drops."
        ),
        then=("several-at-once", "when-a-recording-breaks"),
    ),
)
