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
            "Capture a station you are not listening to, run several captures "
            "side by side, stop them individually or all together, and keep a "
            "bit-for-bit copy when quality matters."
        ),
        steps=(
            Step(
                title="Record a station you are not listening to",
                body=(
                    "Record Station captures a different station for a set number "
                    "of minutes while you listen to something else, or to nothing "
                    "at all. The recorder is its own process and never needed the "
                    "player -- that is why this is possible."
                ),
                command="radio.record_station",
                hear="A dialog asking which station and for how long.",
            ),
            Step(
                title="Start another one",
                body=(
                    "Do it again with a second station. Each recording is fully "
                    "self-contained -- its own connection, its own reconnect "
                    "handling, its own crash-resume -- so one dropping, finishing "
                    "or being stopped never affects the others."
                ),
                command="radio.record_station",
                hear="The second recording confirmed, alongside the first.",
            ),
            Step(
                title="Watch them both in the list",
                body=(
                    "Each running capture is its own Recording row, its size "
                    "growing as you watch, with its own live elapsed time. They "
                    "are counted from the recorder itself, so a recording still "
                    "being written to the temp folder is visible here rather than "
                    "invisible until it lands."
                ),
                command="radio.recordings",
                hear="One Recording row per capture, each with its own time.",
                check="window:Radio Recordings",
            ),
            Step(
                title="Stop one, or stop the lot",
                body=(
                    "Stop Recording stops the one selected in the list. Stop All "
                    "Recordings stops every one at once, and appears as a button "
                    "in this window whenever two or more are running. Record Now "
                    "still only stops the recording of the station you are "
                    "listening to."
                ),
                command="radio.stop_all_recordings",
                hear="Each recording stopped, and its file named.",
            ),
            Step(
                title="Cap it if the machine cannot take it",
                body=(
                    "Maximum simultaneous recordings in Recording Settings is 0 -- "
                    "unlimited -- by default. Set a number on a slower machine or "
                    "a metered connection, and a scheduled recording that would "
                    "exceed the cap is held pending and retried while its window "
                    "is still open rather than lost."
                ),
                command="radio.recording_settings",
                hear="The cap read back.",
            ),
            Step(
                title="Keep exactly what was broadcast",
                body=(
                    "The raw stream format copies the station's own audio packets "
                    "straight to disk with no decoding and no re-encoding, so the "
                    "file is bit-for-bit what the station sent. Choose it when you "
                    "want the cleanest source to edit or convert yourself."
                ),
                hear="The format read back as raw stream.",
                note=(
                    "The file type follows the stream -- .mp3, .aac, .ogg, .opus, "
                    ".flac, and .mka for anything unusual. Bitrate and Apply Sound "
                    "Enhancements have no effect on a raw recording and are "
                    "ignored rather than pretended at."
                ),
            ),
            Step(
                title="Decide whether recordings are filtered",
                body=(
                    "Apply Sound Enhancements to recordings is off by default, so "
                    "your recordings stay an unfiltered archival copy even while "
                    "you listen through EQ and compression. Turn it on and every "
                    "recording method captures the filtered audio instead."
                ),
                hear="The setting read back.",
            ),
        ),
        closing=(
            "Overlapping scheduled recordings all fire too: two shows booked for "
            "the same hour both record, where older versions dropped all but one."
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
            "The Recordings window is a playlist editor by any other name, and it "
            "has Winamp's classic-skin keys on the letter keys you already know. "
            "Learn the dozen that matter."
        ),
        steps=(
            Step(
                title="Open it and read the summary line",
                body=(
                    "The line under the list leads with what is happening: "
                    "Recording, 42 min left. Next: KFI at 11:00 tomorrow. 14 "
                    "recorded. A recording due within the hour is given in "
                    "minutes, one further out by weekday, one past a week by date."
                ),
                command="radio.recordings",
                hear="The summary line, then the list.",
                check="window:Radio Recordings",
            ),
            Step(
                title="Play, pause and stop with one finger",
                body=(
                    "X plays the selected recording or resumes a paused one, C "
                    "pauses and unpauses, V stops. No modifier and no menu -- if "
                    "you came to Windows audio through Winamp these are already in "
                    "your fingers, and every one of them says what it did."
                ),
                keys=("X", "C", "V"),
                hear="Playing, Paused, Stopped -- each spoken.",
            ),
            Step(
                title="Move through the list",
                body=(
                    "B moves down the list and plays; Z goes back. Up and Down "
                    "arrow move through the list without playing, which is what "
                    "Winamp's own Playlist Editor does -- volume stays on Ctrl+Up "
                    "and Ctrl+Down, where it has always been."
                ),
                keys=("B", "Z"),
                hear="The recording that started, named.",
            ),
            Step(
                title="Seek without leaving the row",
                body=(
                    "Left and Right move five seconds; Shift with them moves "
                    "thirty. Seeking needs a recording with a timeline, which "
                    "means the mpv engine -- on a live stream or the classic "
                    "engine the keys say why they cannot move rather than doing "
                    "nothing."
                ),
                keys=("Left", "Right", "Shift+Left", "Shift+Right"),
                hear="The new position, or the reason it cannot move.",
            ),
            Step(
                title="Ask the time, and jump to one",
                body=(
                    "T reads the elapsed time; press it again and it reads the "
                    "time remaining instead. Ctrl+J jumps to a time you type -- 90, "
                    "1:30, or 1:02:03 all work -- and J jumps to a recording by "
                    "any part of its name."
                ),
                keys=("T", "J", "Ctrl+J"),
                hear="The time, or the recording you jumped to.",
                note=(
                    "Ctrl+T stays What's Playing here, which is the more useful "
                    "thing to have on that key in a radio app. Winamp's "
                    "elapsed/remaining toggle is on plain T instead."
                ),
            ),
            Step(
                title="Shuffle, repeat, and stop after this one",
                body=(
                    "R turns shuffle on and off, S cycles repeat -- off, all "
                    "recordings, this recording -- and Ctrl+V stops after the "
                    "current recording. Shuffle is a fixed order rather than a "
                    "fresh roll each time, so every recording plays once before "
                    "any repeats and Z reliably takes you back."
                ),
                keys=("R", "S", "Ctrl+V"),
                hear="The new state, spoken.",
                note=(
                    "Stop-after-current is a one-shot: it clears itself the moment "
                    "it fires and outranks repeat, and it is deliberately not "
                    "remembered between sessions."
                ),
            ),
            Step(
                title="Find the file on disk",
                body=(
                    "Open in Folder takes you to the finished file in Explorer. "
                    "Remove deletes with a confirmation, and Refresh re-reads the "
                    "folder -- worth pressing if something wrote a file there from "
                    "outside the app."
                ),
                keys=("Shift+F10",),
                hear="The action's own confirmation.",
            ),
            Step(
                title="Turn the letters off if you would rather type",
                body=(
                    "Winamp-style playback keys in the Recordings player is on by "
                    "default in Preferences. Turn it off and the letter keys go "
                    "back to list typeahead, which is worth doing if you jump "
                    "through long lists by typing a name. Ctrl+Up and Ctrl+Down "
                    "are unaffected either way."
                ),
                keys=("Ctrl+,",),
                hear="The setting read back.",
            ),
        ),
        closing=(
            "Twelve keys, no modifier, all of them spoken. This window is where a "
            "heavy recording habit actually lives."
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
            "What Quill Radio does about a dropped connection, a stalled stream, "
            "a crash mid-capture and a part file -- and the handful of settings "
            "that decide how hard it tries."
        ),
        steps=(
            Step(
                title="Set how hard it should try",
                body=(
                    "Recording Settings holds an If the connection drops section: "
                    "whether to reconnect at all, how many attempts, and how many "
                    "seconds between them. Reconnect handling is per recording, so "
                    "several running at once each ride out their own hiccups."
                ),
                command="radio.recording_settings",
                hear="The reconnect settings read back.",
            ),
            Step(
                title="Know what a drop actually costs",
                body=(
                    "A truly dead connection is resumed into a numbered part file, "
                    "with each attempt announced. When the recording finishes, the "
                    "parts are stitched back into one file under the name you "
                    "expected -- so a show that dropped twice does not leave you "
                    "three files to play in order."
                ),
                hear=(
                    "Joined 3 parts into one recording -- or Kept 3 separate parts, with the "
                    "reason."
                ),
                note=(
                    "The join is a straight copy, so nothing is re-encoded and "
                    "even a three-hour capture takes seconds. The parts are "
                    "removed only after the joined file is written and checked; a "
                    "failed join never costs you the recording."
                ),
            ),
            Step(
                title="Understand a stall, which is not a drop",
                body=(
                    "A connection can go quiet without disconnecting -- a pulled "
                    "cable, a dropped adaptor -- and used to leave a recording "
                    "wedged: still shown as recording but no longer growing. Quill "
                    "Radio now watches whether the file is growing at all, and "
                    "treats four checks with no new bytes exactly like a dropped "
                    "connection."
                ),
                hear="A reconnection, or a stop that saves what was captured.",
            ),
            Step(
                title="Read a continuation correctly",
                body=(
                    "A continuation records only the remaining time to the "
                    "original scheduled end -- a 60-minute show that drops at "
                    "minute 50 records a ten-minute continuation, not another "
                    "hour. And a part file keeps the original start timestamp in "
                    "its name so the parts group together."
                ),
                hear="The continuation's own length, spoken when it starts.",
            ),
            Step(
                title="Pick a recording back up after a crash",
                body=(
                    "If Quill Radio quits or crashes mid-capture, the next launch "
                    "offers to resume it for the remaining minutes -- one prompt "
                    "for one recording, or a single Resume all? prompt when there "
                    "were several. Resume restarts it; Skip leaves it as it is."
                ),
                hear=(
                    "A dialog naming the station, when it was recording until, and the minutes "
                    "left."
                ),
                note=(
                    "There is a Don't ask me again box that remembers your answer "
                    "-- always resume, or never ask -- and Preferences can change "
                    "it later."
                ),
            ),
            Step(
                title="Tell an empty recording apart from a failed one",
                body=(
                    "A recording that saved nothing says so, names the station, "
                    "and gives the reason -- the connection failed, the station "
                    "refused the connection, that stream address is no longer "
                    "there, the disk is full. No file is kept, because an empty "
                    "one is only something to find later and wonder about."
                ),
                hear="The failure, with the error sound rather than the saved sound.",
            ),
            Step(
                title="Know which failures are worth retrying",
                body=(
                    "Only a genuinely terminal failure gives up: a full disk, or "
                    "an HTTP 404, 410 or 451 that means the stream is truly gone. "
                    "A network hiccup, a 5xx, or a momentary 403 from an expiring "
                    "stream token is transient, and reconnects."
                ),
                hear=(
                    "Either a reconnection attempt, or a plain statement that the stream has gone."
                ),
            ),
        ),
        closing=(
            "Most of this happens without you. The reason to read it once is so "
            "that a part file, a short recording or a resume prompt is a thing "
            "you recognise rather than a thing you have to work out."
        ),
    ),
)
