"""Track 4, second half: several at once, living in the list, and breakage.

Three lessons for somebody who records more than occasionally. Recording
several stations at the same time is the feature most people do not know is
there; the Recordings list has a whole keyboard of its own borrowed from
Winamp; and the last lesson is the one to read before a recording goes wrong
rather than after.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="several-at-once",
        title="Record several stations at once",
        track="recording",
        minutes=6,
        surfaces=("Radio Recordings", "Quill Radio"),
        summary=(
            "Record a station you are not listening to, record several at the "
            "same time, stop them one by one or all together, and keep an exact "
            "copy when quality matters to you."
        ),
        steps=(
            Step(
                title="Record a station you are not listening to",
                body=(
                    "Record Station records a different station for as many "
                    "minutes as you choose, while you listen to something else, "
                    "or to nothing at all. Recording and listening are separate, "
                    "so one never gets in the way of the other."
                ),
                command="radio.record_station",
                hear=(
                    "Record Station, asking for the Station and the Duration in minutes. "
                    "After Start Recording, Recording started, the station, and for how "
                    "many minutes."
                ),
            ),
            Step(
                title="Start another one",
                body=(
                    "Do it again with a second station. Each recording looks "
                    "after itself. If one drops out, finishes or is stopped, the "
                    "others carry on as if nothing happened."
                ),
                command="radio.record_station",
                hear="Recording started, the second station, and its minutes.",
            ),
            Step(
                title="Watch them both in the list",
                body=(
                    "Open the Recordings window. Each recording in progress has "
                    "its own Recording row, with its size growing and its own "
                    "running time. You can see a recording here while it is "
                    "still being made, not just once it is finished."
                ),
                command="radio.recordings",
                hear="One Recording row for each recording, each with its own time.",
                check="window:Radio Recordings",
            ),
            Step(
                title="Stop one, or stop the lot",
                body=(
                    "The Stop Recording button stops the one you have selected. "
                    "Stop All Recordings, on the Record menu, stops them all at "
                    "once, and it also shows up as a button in this window "
                    "whenever two or more are running. Record Now only ever "
                    "stops the recording of the station you are listening to."
                ),
                command="radio.stop_all_recordings",
                hear="Stopping all, and how many. Then Recording saved for each file.",
            ),
            Step(
                title="Cap it if the machine cannot take it",
                body=(
                    "Maximum simultaneous recordings, in Recording Settings, "
                    "starts at 0, which means no limit. On a slower computer or "
                    "a limited internet plan, set a number. If a booked "
                    "recording would go over your limit, it waits and tries "
                    "again while the show is still on, rather than being lost."
                ),
                command="radio.recording_settings",
                hear="Recording Settings. Tab to Maximum simultaneous recordings, reading 0.",
            ),
            Step(
                title="Keep exactly what was broadcast",
                body=(
                    "In Recording Settings, the Format called Raw stream saves "
                    "the station's sound exactly as it arrives, with nothing "
                    "changed. Choose it when you want the cleanest possible copy "
                    "to edit or convert yourself later."
                ),
                hear="Format, and Raw stream, exactly as sent, no re-encoding.",
                note=(
                    "The file type matches the station: .mp3, .aac, .ogg, .opus "
                    "or .flac, and .mka for anything unusual. The Quality and "
                    "Apply Sound Enhancements settings do not apply to raw "
                    "recordings."
                ),
            ),
            Step(
                title="Decide whether recordings are filtered",
                body=(
                    "Apply Sound Enhancements to recordings, a checkbox in "
                    "Recording Settings, starts off. So your recordings stay "
                    "just as the station sent them, even if you listen with EQ "
                    "or compression on. Turn it on if you would like recordings "
                    "to sound the way you hear them."
                ),
                hear="Apply Sound Enhancements to recordings, checkbox, not checked.",
            ),
        ),
        closing=(
            "Bookings that overlap all record too. If two shows are booked for "
            "the same hour, you get both. Enjoy your recordings."
        ),
        then=("live-in-the-recordings-list",),
    ),
    Tutorial(
        slug="live-in-the-recordings-list",
        title="Live in the Recordings list",
        track="recording",
        minutes=7,
        surfaces=("Radio Recordings",),
        summary=(
            "The Recordings window works like a music player, and it uses the "
            "classic Winamp letter keys. Here you will learn the dozen keys that "
            "matter most."
        ),
        steps=(
            Step(
                title="Open it and read the summary line",
                body=(
                    "The summary line under the list starts with what is "
                    "happening right now, for example: Recording, 42 min left. "
                    "Next: KFI at 11:00 tomorrow. 14 recorded. In, and the "
                    "folder. A recording coming up within the hour is given in "
                    "minutes, one later in the week by weekday, and one further "
                    "off by date."
                ),
                command="radio.recordings",
                hear="Radio Recordings, then the row you land on. The summary is below the list.",
                check="window:Radio Recordings",
            ),
            Step(
                title="Play, pause and stop with one finger",
                body=(
                    "X plays the selected recording or carries on from a pause. "
                    "C pauses and unpauses. V stops. No Ctrl, no Alt, no menu. "
                    "If you used Winamp, your fingers already know these, and "
                    "every one of them tells you what it did."
                ),
                keys=("X", "C", "V"),
                hear="Playing recording and its name, then Paused, then Stopped.",
            ),
            Step(
                title="Move through the list",
                body=(
                    "B moves to the next recording and plays it. Z goes back to "
                    "the one before. Up and Down Arrow move through the list "
                    "without playing anything. Volume stays on Ctrl+Up and "
                    "Ctrl+Down, just like everywhere else."
                ),
                keys=("B", "Z"),
                hear="The name of the recording that started.",
            ),
            Step(
                title="Seek without leaving the row",
                body=(
                    "Left and Right Arrow skip five seconds back or forward. Add "
                    "Shift to skip thirty. Skipping needs the mpv engine. If you "
                    "cannot skip, for example on a live stream, the key tells "
                    "you why."
                ),
                keys=("Left", "Right", "Shift+Left", "Shift+Right"),
                hear="The new position, or the reason it cannot move.",
            ),
            Step(
                title="Ask the time, and jump to one",
                body=(
                    "T tells you how far in you are. Press it again and it tells "
                    "you how much is left. Ctrl+J jumps to a time you type, and "
                    "90, 1:30 or 1:02:03 all work. J jumps to a recording by any "
                    "part of its name."
                ),
                keys=("T", "J", "Ctrl+J"),
                hear="The time, or the recording you jumped to.",
                note=(
                    "Ctrl+T is still What's Playing here, as it is everywhere in "
                    "Quill Radio. That is why Winamp's time key is plain T "
                    "instead."
                ),
            ),
            Step(
                title="Shuffle, repeat, and stop after this one",
                body=(
                    "R turns shuffle on and off. S steps through repeat: off, "
                    "all recordings, this recording. Ctrl+V stops after the "
                    "current recording. Shuffle picks one order and keeps it, so "
                    "everything plays once before anything repeats, and Z always "
                    "takes you back the way you came."
                ),
                keys=("R", "S", "Ctrl+V"),
                hear="The new setting, spoken.",
                note=(
                    "Stop after this one only happens once. It switches itself "
                    "off as soon as it stops the player, it wins over repeat, "
                    "and it is not remembered next time you open Quill Radio."
                ),
            ),
            Step(
                title="Find the file on disk",
                body=(
                    "The buttons below the list look after the files. Open in "
                    "Folder takes you to the file in File Explorer. Remove "
                    "deletes it after asking you first. Refresh reads the folder "
                    "again, which is handy if you put a file there yourself."
                ),
                keys=("Alt+O", "Alt+F"),
                hear=(
                    "File Explorer, with the file selected. Or the list read again, "
                    "where you left it."
                ),
            ),
            Step(
                title="Turn the letters off if you would rather type",
                body=(
                    "Winamp-style playback keys in the Recordings player is on "
                    "to start with, in Preferences. If you turn it off, typing a "
                    "letter jumps to a recording starting with that letter "
                    "instead, which is handy in a long list. Ctrl+Up and "
                    "Ctrl+Down change the volume either way."
                ),
                keys=("Ctrl+,",),
                hear=(
                    "Quill Radio Preferences. Tab to the Winamp-style checkbox and hear its state."
                ),
            ),
        ),
        closing=(
            "Twelve keys, no Ctrl or Alt needed, and every one tells you what it "
            "did. If you record a lot, this window will soon feel like home."
        ),
        then=("when-a-recording-breaks",),
    ),
    Tutorial(
        slug="when-a-recording-breaks",
        title="When a recording breaks",
        track="recording",
        minutes=6,
        surfaces=("Radio Recordings", "Recording Settings"),
        summary=(
            "What Quill Radio does when the connection drops, a station goes "
            "quiet, or the computer crashes in the middle of a recording, and "
            "the few settings that decide how hard it tries."
        ),
        steps=(
            Step(
                title="Set how hard it should try",
                body=(
                    "Recording Settings has a group called If the connection "
                    "drops, with Reconnect and keep recording automatically, "
                    "Reconnect attempts, and Seconds between attempts. Each "
                    "recording reconnects on its own, so if you are recording "
                    "several at once, each one rides out its own hiccups."
                ),
                command="radio.recording_settings",
                hear="Recording Settings, then each reconnect control as you Tab to it.",
            ),
            Step(
                title="Know what a drop actually costs",
                body=(
                    "If the connection really drops, Quill Radio reconnects and "
                    "carries on in a numbered part file, telling you about each "
                    "try. When the recording ends, the parts are joined back into "
                    "one file with the name you expect. So a show that dropped "
                    "twice still gives you just one file."
                ),
                hear=("Joined 3 parts into one recording. Or Kept 3 separate parts, and why."),
                note=(
                    "Joining is quick, even for a three-hour show, and the sound "
                    "is not changed. The parts are only removed after the joined "
                    "file is saved and checked, so you never lose the recording."
                ),
            ),
            Step(
                title="Understand a stall, which is not a drop",
                body=(
                    "Sometimes a connection goes quiet without actually dropping, "
                    "for example when a cable is pulled out. Quill Radio keeps an "
                    "eye on whether the recording is still growing. If it stops "
                    "growing for a while, Quill Radio treats it just like a "
                    "dropped connection."
                ),
                hear="A reconnection, or a stop that saves what was recorded.",
            ),
            Step(
                title="Read a continuation correctly",
                body=(
                    "After a drop, Quill Radio only records the time left until "
                    "the show was due to end. So if a 60-minute show drops at "
                    "minute 50, you get a ten-minute continuation, not another "
                    "hour. Each part keeps the original start time in its name, "
                    "so the parts sit together in the list."
                ),
                hear="The length of the continuation, spoken when it starts.",
            ),
            Step(
                title="Pick a recording back up after a crash",
                body=(
                    "If Quill Radio closes or crashes in the middle of a "
                    "recording, it offers to carry on next time you open it, for "
                    "the minutes that are left. You get one question for one "
                    "recording, or a single Resume all? question if there were "
                    "several. Resume starts it again, and Skip leaves it as it is."
                ),
                hear=(
                    "A window naming the station, when it was due to record until, and "
                    "the minutes left."
                ),
                note=(
                    "There is a Don't ask me again box that remembers your "
                    "answer: always resume, or never ask. Leave it unchecked if "
                    "you would rather decide each time."
                ),
            ),
            Step(
                title="Tell an empty recording apart from a failed one",
                body=(
                    "If a recording saved nothing, Quill Radio tells you, names "
                    "the station and says why: the connection failed, the "
                    "station refused the connection, that stream address is no "
                    "longer there, or the disk is full. No empty file is kept to "
                    "puzzle you later."
                ),
                hear="What went wrong, with the error sound instead of the saved sound.",
            ),
            Step(
                title="Know which failures are worth retrying",
                body=(
                    "Quill Radio only gives up when there is no point trying "
                    "again: a full disk, or a station that has really gone away. "
                    "Brief hiccups, such as a short network drop or a server "
                    "that is busy for a moment, are retried."
                ),
                hear=(
                    "Either another try at connecting, or a plain sentence that the stream "
                    "has gone."
                ),
            ),
        ),
        closing=(
            "Most of this happens without you lifting a finger. Read it once so "
            "that a part file, a short recording or a question about resuming "
            "feels familiar rather than worrying."
        ),
    ),
)
