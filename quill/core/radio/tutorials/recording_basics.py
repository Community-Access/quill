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
            "Start and stop a recording of the station you are listening to, find "
            "the file, play it back, and understand what the status bar's Record "
            "cell is counting."
        ),
        steps=(
            Step(
                title="Put something on first",
                body=(
                    "Record Now follows what you are listening to, so it needs "
                    "something to follow. Play a station -- any station -- and "
                    "leave it running."
                ),
                command="radio.play_last",
                hear="The station's name as it starts playing.",
                check="playing",
            ),
            Step(
                title="Start the recording",
                body=(
                    "Record Now begins a capture of the station on now, and says "
                    "so with the station's name. More than one place agrees it is "
                    "happening: the status bar's Record cell changes to Stop "
                    "Recording with a time, and the now-playing line notes it."
                ),
                command="radio.record_toggle",
                hear="Recording started, and the station's name, over the start-recording sound.",
                check="recording-started",
            ),
            Step(
                title="Read what the Record cell is counting",
                body=(
                    "Press F6 in the main window and arrow to the Record cell. "
                    "Started with Record "
                    "Now, it counts up -- 18 min so far -- because you asked for "
                    "no length at all. Asked for an hour, it counts down. The only "
                    "number the app has in the first case is a disk-safety cap, "
                    "and counting down to that would be telling you about a plan "
                    "you never made."
                ),
                keys=("F6", "Right arrow"),
                hear="Stop Recording, and the elapsed time in brackets: 18 min so far.",
            ),
            Step(
                title="Stop it, and hear where it went",
                body=(
                    "The same command stops the recording of the station you are "
                    "listening to, and names the file once it has been written. A "
                    "recording of a "
                    "different station running in the background is never stopped "
                    "by this -- those are stopped from the Recordings window."
                ),
                command="radio.record_toggle",
                hear="Stopping recording, then Recording saved and the file's name.",
                check="recording-finished",
            ),
            Step(
                title="Open the recordings list",
                body=(
                    "Radio Recordings lists what you have recorded, newest first, "
                    "so yours is near the top. Its summary line leads with what is "
                    "happening rather than with counts: recording or not, next "
                    "scheduled, how many recorded, and the folder they are in."
                ),
                command="radio.recordings",
                hear="Radio Recordings, then the list and the row you land on.",
                check="window:Radio Recordings",
            ),
            Step(
                title="Play it back",
                body=(
                    "Press Enter on the row. It plays through the app's own "
                    "player, so every transport key you already know works on it "
                    "-- including volume, which many programs quietly reserve for "
                    "live audio only."
                ),
                keys=("Enter",),
                hear="Playing recording, the recording's name, then the recording itself.",
            ),
            Step(
                title="Throw it away",
                body=(
                    "Press Delete and confirm. Focus lands on the recording that "
                    "took its place in the list -- not at the top and not nowhere, "
                    "which is what makes deleting several in a row bearable."
                ),
                keys=("Delete",),
                hear=(
                    "A confirmation naming the recording, then Removed recording and "
                    "its name, and the row that took its place."
                ),
                note=(
                    "A recording deleted here can be brought back with Undo Last "
                    "Action, which restores the file and not merely its name in the "
                    "list."
                ),
            ),
            Step(
                title="Decide where recordings live",
                body=(
                    "Recording Settings, on the Record menu, holds the format -- "
                    "MP3, OGG Vorbis, FLAC, WAV or the raw stream -- the quality, the "
                    "filename pattern, and the destination "
                    "folder. Recordings land in Music\\Quill Radio Recordings "
                    "under your user folder unless you point them somewhere else."
                ),
                command="radio.recording_settings",
                hear="Recording Settings, then Format and the format chosen now.",
                note=(
                    "Set a temporary folder as well and a recording is written "
                    "there and moved when it finishes, so a half-written file "
                    "never appears among your finished recordings."
                ),
            ),
        ),
        closing=(
            "One key starts it, the same key stops it, and the file is somewhere "
            "you can actually find. The next lesson is the one that records "
            "something while you are out."
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
            "Fill in a scheduled recording correctly the first time, including the "
            "time-zone trap, then edit, duplicate, disable and delete entries "
            "without starting again."
        ),
        steps=(
            Step(
                title="Learn the one rule before you open the window",
                body=(
                    "You fill in the details first and choose Add Schedule last. "
                    "Add is the button that commits the entry you have just "
                    "described -- it is not a button that starts a new form. "
                    "Nearly every confused first attempt at this window is that "
                    "one misunderstanding."
                ),
                hear="Nothing: read this one twice instead.",
            ),
            Step(
                title="Open the schedule",
                body=(
                    "Schedule Recording is a list above a form. The list, "
                    "Scheduled recordings, is what you have booked, ordered by when "
                    "each one next occurs -- soonest first, not the order you "
                    "entered them. The form below it, Add a new schedule, is where "
                    "you describe the next one."
                ),
                command="radio.schedule_recording",
                hear="Schedule Recording, then the Scheduled recordings list.",
                check="window:Schedule Recording",
            ),
            Step(
                title="Pick the station from your favorites",
                body=(
                    "Tab to Favorite station and arrow to one: choosing a favorite "
                    "fills in both Station name and Stream URL. If the station you "
                    "want is not listed, add it to "
                    "your favorites first -- or, for a one-off stream, type the "
                    "name and paste the address by hand instead. Both fields stay "
                    "editable either way."
                ),
                keys=("Tab", "Down arrow"),
                hear="The station name and stream filled in for you.",
            ),
            Step(
                title="Enter the time the way you think of it",
                body=(
                    "In the Time field, 7:30 PM and 19:30 are both understood, so "
                    "use whichever you have in your head. Then pin the entry with "
                    "Time zone: leave it at (local time) for a show quoted in your "
                    "own clock, and choose the zone when the show is quoted in "
                    "somebody else's."
                ),
                hear="Time (7:30 PM or 19:30), edit; then Time zone, reading (local time).",
                note=(
                    "The list shows every entry's time with its zone, so two "
                    "similar bookings in different zones can be told apart at a "
                    "glance -- which is exactly when this goes wrong."
                ),
            ),
            Step(
                title="Choose how often, and how long",
                body=(
                    "Repeats offers Once (with a date), Daily, or Weekly (with a "
                    "day). Then the length, as Duration hours and minutes -- a "
                    "three-hour show is "
                    "simply 3 and 0, with no arithmetic and no counting zeroes in "
                    "a seconds field."
                ),
                hear="Repeats, combo box, then each duration field with its number.",
            ),
            Step(
                title="Commit it",
                body=(
                    "Choose Add Schedule. Your entry appears in the list, focus "
                    "moves to it, and the form clears for the next one -- so you "
                    "are never left standing on the Add button wondering whether "
                    "it worked."
                ),
                hear=(
                    "Scheduled recording added for, and the station, then the entry "
                    "itself as focus lands on it."
                ),
            ),
            Step(
                title="Change one without deleting it",
                body=(
                    "Select an entry and choose Edit: the form fills in, the Add "
                    "button relabels to Save Changes and the status line names the "
                    "entry you are editing, so it is always clear you are changing "
                    "that one rather than adding a new one. New abandons the edit."
                ),
                keys=("Alt+E",),
                hear="Station name, holding the entry's name, where focus lands to edit it.",
            ),
            Step(
                title="Make a similar one",
                body=(
                    "Duplicate, beside Edit, starts a new, independent entry "
                    "pre-filled from the "
                    "selected one, with (copy) on its name -- a starting point for "
                    "another day or a second slot. It keeps the original's stream "
                    "until you change it, so pick a different favorite if you "
                    "meant a different station."
                ),
                keys=("Alt+P",),
                hear="Station name, holding the original name with (copy) after it.",
            ),
            Step(
                title="Turn one off without losing it",
                body=(
                    "The Disable button turns an entry off rather than deleting "
                    "it -- a disabled entry reads (disabled) in the list and does "
                    "not fire, and the same button then reads Enable. Remove names "
                    "the schedule it will delete, and Delete in the list does the "
                    "same."
                ),
                keys=("Alt+L",),
                hear="The station's name, and disabled -- or enabled.",
            ),
            Step(
                title="Know what a schedule needs from you",
                body=(
                    "Quill Radio has to be running for a scheduled recording to "
                    "fire -- the tray icon counts. A schedule is due from its "
                    "start time through the end of its duration, so a late start "
                    "still records the remaining minutes, and a launch catches up "
                    "anything whose window is still open. A show whose whole "
                    "window passed while the app was closed is missed, and the "
                    "next launch tells you."
                ),
                hear="At the next launch: what was missed, up to three named and the rest counted.",
                note=(
                    "Three Preferences, all on by default, cover a sleeping "
                    "computer: Keep the computer awake before a scheduled "
                    "recording, Wake the computer for a scheduled recording, and "
                    "Keep the computer awake while playing or recording."
                ),
            ),
        ),
        closing=(
            "A booked show records itself while you are out. The next lesson is "
            "about recording three of them at once, and about what happens when "
            "the connection does not hold."
        ),
        then=("several-at-once", "when-a-recording-breaks"),
    ),
)
