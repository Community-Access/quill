"""Track 6, second half: shaping the sound, counting the hours, keeping it safe.

Three lessons about looking after a setup you have come to rely on. The sound
lesson is the one that makes a badly-mastered station listenable; the
statistics lesson answers a question the recently-played list never could; and
the last one is insurance -- backups, a move to another machine, updates, and
what to do on the day something is genuinely broken.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="shape-the-sound",
        title="Shape the sound",
        track="living",
        minutes=7,
        surfaces=("Sound Enhancements", "Player", "Quill Radio"),
        summary=(
            "Per-station volume, a boost for a quiet stream, EQ and compression, "
            "pausing and rewinding live radio, and a playback speed that sticks."
        ),
        steps=(
            Step(
                title="Fix one station's volume once",
                body=(
                    "Set the volume while a favorite plays and it is remembered for "
                    "that station, coming back the next time it starts. Stations are "
                    "mastered wildly differently and you should only have to fix that "
                    "once per station."
                ),
                command="radio.volume_up",
                hear="The new level -- and the same level again the next time that station starts.",
                check="volume-changed",
                note=(
                    "A favorite's remembered level always wins over the general one. "
                    "Forget Station Volumes clears them all if you would rather start "
                    "again, and Global Volume turns the whole behaviour off."
                ),
            ),
            Step(
                title="Boost a stream that is simply too quiet",
                body=(
                    "Volume Boost lifts a stream beyond the normal ceiling for the "
                    "cases where full volume still is not enough. It needs the mpv "
                    "engine, and says so rather than doing nothing if you are on the "
                    "classic one."
                ),
                command="radio.volume_boost",
                keys=("Ctrl+Shift+B",),
                hear="Volume Boost on, or the reason it cannot.",
            ),
            Step(
                title="Open Sound Enhancements",
                body=(
                    "EQ, a compressor and a channel mode -- the three things that "
                    "make a thin talk station or an over-compressed music station "
                    "listenable. There is a preview, so you can hear a setting before "
                    "you keep it."
                ),
                command="radio.sound_enhancements",
                keys=("Ctrl+E",),
                hear="Entered Sound Enhancements.",
                note=(
                    "Enhancements are off for recordings by default, so your "
                    "recordings stay an unfiltered archival copy. Recording Settings "
                    "has the switch if you want the filtered audio captured instead."
                ),
            ),
            Step(
                title="Pause live radio, and rewind into what you missed",
                body=(
                    "On the mpv engine a live station really pauses -- and you can "
                    "rewind into what went out while you were away. Back to Live "
                    "returns you to the broadcast edge."
                ),
                command="radio.pause",
                keys=("Ctrl+Space", "Ctrl+Shift+Left", "Ctrl+Shift+L"),
                hear="Paused, then the position as you rewind, then back at the live edge.",
                check="paused",
            ),
            Step(
                title="Choose a speed that stays chosen",
                body=(
                    "A speed you choose while a recording plays applies to every "
                    "recording; a speed chosen on a YouTube row applies to YouTube "
                    "rows. Per kind rather than per row, because being asked to set "
                    "it again for each captured hour is the same feature with the "
                    "cost moved onto you."
                ),
                command="radio.transport.speed_up",
                keys=("Ctrl+Shift+Up", "Ctrl+Shift+Down", "Ctrl+Shift+0"),
                hear="The new speed, spoken as a number.",
            ),
            Step(
                title="Shorten the long pauses",
                body=(
                    "Skip Silence shortens the gaps in a recording, a YouTube row or "
                    "an episode as it plays, taking effect on what is already playing "
                    "with no interruption. It has no effect on live radio and says so "
                    "if you turn it on while a station plays, rather than appearing to "
                    "do nothing."
                ),
                command="radio.transport.skip_silence",
                keys=("Ctrl+Shift+9",),
                hear=(
                    "Skip Silence on -- or the sentence explaining why a broadcast has no pauses "
                    "to skip."
                ),
            ),
            Step(
                title="Send the radio somewhere else",
                body=(
                    "Output Device routes the radio to a second sound card or a USB "
                    "headset while your screen reader stays on the system default. "
                    "Switching mid-song reconnects the station on the new device, "
                    "which is where it matters."
                ),
                keys=("Ctrl+Shift+D",),
                hear="The device you chose, read back.",
            ),
        ),
        closing=(
            "Per-station volume is the one to set up now. The rest are worth "
            "knowing about for the day a particular station annoys you."
        ),
        then=("count-the-hours",),
    ),
    Tutorial(
        slug="count-the-hours",
        title="How much did I actually listen?",
        track="living",
        minutes=4,
        surfaces=("Listening Statistics",),
        summary=(
            "Read your listening broken down by station and by network, take it "
            "away as a spreadsheet, and understand exactly what is being counted."
        ),
        steps=(
            Step(
                title="Open the statistics",
                body=(
                    "Choose a period -- this week, this month, this year, all time -- "
                    "and the window reports how long you listened in total, how many "
                    "sessions that was, then a breakdown by station and by network."
                ),
                command="radio.statistics",
                keys=("Ctrl+Shift+Q",),
                hear="Entered Listening Statistics, then the totals.",
            ),
            Step(
                title="Notice how the durations are read",
                body=(
                    "Three hours, 47 minutes -- as language, never as a clock face. "
                    "A screen reader reads 3:47:00 as a time of day, which is the "
                    "wrong sentence entirely for a duration."
                ),
                hear="Durations spoken as hours and minutes.",
            ),
            Step(
                title="Know what counts",
                body=(
                    "Time counts only while audio is actually coming out. Connecting "
                    "does not count. Buffering through dead air does not count. Paused "
                    "does not count. The app sitting stopped overnight does not count."
                ),
                hear="Nothing: this is why the number is lower than you expected, and right.",
            ),
            Step(
                title="Know what is deliberately not there",
                body=(
                    "Anything under ten seconds is not a session -- skipping past a "
                    "station in a list is not listening, and a log full of "
                    "three-second samples would make every per-station total "
                    "meaningless. There is also no time saved by playing faster and no "
                    "silence trimmed, because neither means anything for a broadcast."
                ),
                hear="Nothing: a missing number here is a deliberate omission rather than a gap.",
            ),
            Step(
                title="Take it with you",
                body=(
                    "Copy takes the whole report as text. Save as CSV writes every "
                    "session out for a spreadsheet, which is the one to use if you "
                    "want to do arithmetic the window does not do."
                ),
                hear="Copied, or the file written and where.",
            ),
            Step(
                title="Delete it if you would rather not keep it",
                body=(
                    "Delete My History removes the lot, and asks first with No as the "
                    "default button -- because there is no other copy of it anywhere. "
                    "Your history is kept on this computer and goes nowhere."
                ),
                hear="A confirmation, defaulting to No.",
            ),
        ),
        closing=(
            "It answers the question the recently-played list never could: not "
            "what did I have on, but how much."
        ),
        then=("keep-it-safe",),
    ),
    Tutorial(
        slug="keep-it-safe",
        title="Back it up, move it, and keep it working",
        track="living",
        minutes=8,
        surfaces=("Quill Radio",),
        summary=(
            "Take a copy of everything you have built, move it to another machine, "
            "stay up to date, and know what to do on the day something is genuinely "
            "wrong."
        ),
        steps=(
            Step(
                title="Back up the stations and the settings",
                body=(
                    "Back Up Stations and Settings writes your favorites, settings, "
                    "wake timer and recording schedule into one portable file, and "
                    "asks whether to include your recorded audio -- which can be "
                    "large. Restore from Backup previews it and confirms before "
                    "replacing anything."
                ),
                keys=("Alt+S",),
                hear="The file written, and what went into it.",
            ),
            Step(
                title="Move the whole setup to another machine",
                body=(
                    "Export My Setup writes one file carrying more than a backup "
                    "does: subscriptions, folders and playlists, favorites and saved "
                    "places, settings, your Go To order, your Quick Action order, "
                    "scheduled recordings, bookmarks and any keys you rebound. Import "
                    "My Setup puts them on the other machine."
                ),
                keys=("Ctrl+Alt+Shift+X", "Ctrl+Alt+Shift+N"),
                hear="What the file holds, named, before anything is written.",
                note=(
                    "Passwords are not in it: private-feed sign-ins, server "
                    "credentials and unlock codes stay on the machine that holds "
                    "them. Importing replaces what is on this machine rather than "
                    "merging -- merging two libraries is a different job with "
                    "different questions."
                ),
            ),
            Step(
                title="Or let a sync service do it",
                body=(
                    "The Data Folder button in Preferences points every Quill app at "
                    "a folder of your choosing. Point it at one Dropbox, OneDrive, "
                    "Google Drive or iCloud already syncs and the setup travels by "
                    "itself -- no account, no sign-in, the sync client does the "
                    "moving."
                ),
                keys=("Ctrl+,",),
                hear="The folder, and an offer to restart so it takes effect.",
            ),
            Step(
                title="Stay up to date without being nagged",
                body=(
                    "Check for Updates compares your version with the newest release, "
                    "downloads the edition you are actually running with spoken "
                    "progress, then offers Install now or Open folder. Quill Radio "
                    "also checks quietly once a day at launch -- silent unless it "
                    "finds something."
                ),
                keys=("Ctrl+Alt+U",),
                hear="Either what is available, or a dialog saying you are up to date.",
                note=(
                    "Each installer records which edition it laid down, so an update "
                    "gives you the same kind back -- installer for installer, "
                    "portable for portable."
                ),
            ),
            Step(
                title="Keep it playing while you work",
                body=(
                    "Send to Tray hides the window and keeps everything running. The "
                    "tray icon carries the live now-playing line, play/stop, mute, "
                    "your favorites and recently played nested by folder, recording, "
                    "scheduling and Browse Stations."
                ),
                keys=("Ctrl+W", "Ctrl+Alt+Shift+R"),
                hear="Hidden to the tray -- and Shown when you bring it back.",
            ),
            Step(
                title="Check the installation itself",
                body=(
                    "If playback or recording is misbehaving, Audio Health answers "
                    "whether this installation can do the thing at all: which engine "
                    "is really in use, whether mpv and FFmpeg are present, where the "
                    "audio is going, and whether a recording could be written right "
                    "now."
                ),
                keys=("Ctrl+Alt+Shift+M",),
                hear="Each check with its own verdict.",
                note=(
                    "mpv and FFmpeg ship inside every installer, so a missing one "
                    "means a damaged installation -- antivirus quarantine and a "
                    "half-finished update are the two usual causes. Get FFmpeg and "
                    "Get mpv Playback Engine on the Help menu fetch them back."
                ),
            ),
            Step(
                title="Report it properly",
                body=(
                    "Report a Bug files from inside the app, stamped with this app's "
                    "own version, with no account needed. Paste in Copy All from "
                    "Recent Problems -- it carries addresses and error messages, "
                    "never passwords."
                ),
                keys=("Ctrl+Alt+B", "Ctrl+Alt+Shift+P"),
                hear="A form with most of it filled in already.",
            ),
            Step(
                title="Know the one setting that turns everything off",
                body=(
                    "Safe Mode starts Quill Radio with every network feature "
                    "disabled -- no directories, no catalog refresh, no YouTube, no "
                    "Spotify, no Quillins. It is what to try when something is broken "
                    "enough that you want to know whether the network is involved."
                ),
                hear="The app starting with the online branches simply absent.",
            ),
        ),
        closing=(
            "One backup file, one setup file, one health window and one bug form. "
            "Between them, nothing you have built here is difficult to get back."
        ),
    ),
)
