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
            "Make every station sound its best: a volume for each station, a "
            "boost for quiet ones, tone and loudness controls, pausing and "
            "rewinding live radio, and a playback speed that stays put."
        ),
        steps=(
            Step(
                title="Fix one station's volume once",
                body=(
                    "Set the volume while a favorite is playing, and Quill Radio "
                    "remembers it for that station. Next time it starts, the "
                    "volume comes back just as you left it. Some stations are "
                    "much louder than others, and this way you only fix each "
                    "one once."
                ),
                command="radio.volume_up",
                keys=("Ctrl+Up", "Ctrl+Down"),
                hear="The new level, and the same level again next time that station starts.",
                check="volume-changed",
                note=(
                    "A favorite's own volume always wins over the general "
                    "volume. Forget Every Station's Own Volume, on the Audio "
                    "menu, clears them all if you want a fresh start. Use One "
                    "Volume for All Stations, right beside it, turns the whole "
                    "idea off."
                ),
            ),
            Step(
                title="Boost a stream that is simply too quiet",
                body=(
                    "Volume Boost makes a station louder than full volume, for "
                    "those stations that are still too quiet. It needs the mpv "
                    "engine. If you are using the classic engine, it tells you "
                    "so."
                ),
                command="radio.volume_boost",
                keys=("Ctrl+Shift+B",),
                hear="Volume Boost on: up to 50 percent louder. Or the reason it cannot.",
            ),
            Step(
                title="Open Sound Enhancements",
                body=(
                    "Sound Enhancements has an equaliser, Even Out Volume, a "
                    "channel mode and Night mode. They help a thin talk station "
                    "or a harsh music station sound much better. You hear each "
                    "change straight away, and Cancel puts everything back the "
                    "way it was."
                ),
                command="radio.sound_enhancements",
                keys=("Ctrl+E",),
                hear="Sound Enhancements, then its Quick preset list.",
                note=(
                    "These are not applied to recordings unless you ask, so your "
                    "recordings stay exactly as the station sent them. To record "
                    "what you hear, turn on Apply Sound Enhancements to "
                    "recordings in Recording Settings."
                ),
            ),
            Step(
                title="Rewind live radio into what you missed",
                body=(
                    "With the mpv engine, Quill Radio keeps about the last "
                    "three-quarters of an hour of a live station. Rewind 30 "
                    "Seconds, on the Playback menu, takes you back into what you "
                    "missed. Forward 30 Seconds comes forward again, and Back to "
                    "Live takes you right back to the live broadcast."
                ),
                command="radio.rewind",
                keys=("Ctrl+Shift+Left", "Ctrl+Shift+Right", "Ctrl+Shift+L"),
                hear="30 seconds behind live, then how far behind you are, then Back to live.",
                note=(
                    "Pause on the Playback menu is dimmed on a live station and "
                    "tells you why. It is for recordings, episodes and files. On "
                    "the classic engine, the rewind keys tell you they need mpv."
                ),
            ),
            Step(
                title="Choose a speed that stays chosen",
                body=(
                    "Change the speed while a recording is playing, and every "
                    "recording plays at that speed. Change it on a YouTube video, "
                    "and every YouTube video does. So you set it once for each "
                    "kind of thing, not over and over."
                ),
                command="radio.transport.speed_up",
                keys=("Ctrl+Shift+Up", "Ctrl+Shift+Down", "Ctrl+Shift+0"),
                hear="The new speed, spoken as a number.",
            ),
            Step(
                title="Shorten the long pauses",
                body=(
                    "Skip Silence shortens the gaps in a recording, a YouTube "
                    "video or an episode while it plays, with no interruption. "
                    "It does not work on live radio, and if you turn it on while "
                    "a station is playing, Quill Radio tells you why."
                ),
                command="radio.transport.skip_silence",
                keys=("Ctrl+Shift+9",),
                hear=(
                    "Skip Silence on. Or a sentence explaining why a live broadcast has "
                    "no pauses to skip."
                ),
            ),
            Step(
                title="Send the radio somewhere else",
                body=(
                    "Output Device sends the radio to a second sound card or a "
                    "USB headset, while your screen reader stays where it is. If "
                    "you switch in the middle of a song, the station carries on "
                    "through the new device."
                ),
                keys=("Ctrl+Shift+D",),
                hear="The device you chose, read back.",
            ),
        ),
        closing=(
            "A volume for each station is the one worth setting up today. Keep "
            "the rest in mind for the day a station gets on your nerves."
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
            "Find out how much you have listened, by station and by network, "
            "save it as a spreadsheet, and learn exactly what counts as "
            "listening."
        ),
        steps=(
            Step(
                title="Open the statistics",
                body=(
                    "Choose a time period, such as this week, this month, this "
                    "year or all time. The window tells you how long you "
                    "listened in total and how many times, then breaks it down "
                    "by station and by network."
                ),
                command="radio.statistics",
                keys=("Ctrl+Shift+Q",),
                hear="Listening Statistics, then the totals.",
            ),
            Step(
                title="Notice how the durations are read",
                body=(
                    "Times are written in words, such as three hours, 47 "
                    "minutes. They are never written like a clock, because a "
                    "screen reader would read 3:47:00 as a time of day."
                ),
                hear="Times spoken as hours and minutes.",
            ),
            Step(
                title="Know what counts",
                body=(
                    "Only time when you can actually hear something counts. "
                    "Connecting does not count. Waiting for a stream to come "
                    "back does not count. Paused does not count. And Quill Radio "
                    "sitting stopped all night certainly does not count."
                ),
                hear="Nothing. This is why the number may be lower than you expected.",
            ),
            Step(
                title="Know what is deliberately not there",
                body=(
                    "Anything under ten seconds is not counted, because flicking "
                    "past a station is not really listening. There is also no "
                    "time saved by faster playback or by trimming silence, "
                    "because those do not apply to live radio."
                ),
                hear="Nothing. If a number is missing here, it is missing on purpose.",
            ),
            Step(
                title="Take it with you",
                body=(
                    "Copy copies the whole report as text. Save as CSV saves "
                    "every listening session for a spreadsheet, which is the one "
                    "to use if you want to do your own sums."
                ),
                hear="Copied. Or Saved, the number of sessions, and the file's name.",
            ),
            Step(
                title="Delete it if you would rather not keep it",
                body=(
                    "Delete My History removes all of it. It asks first, with No "
                    "as the default, because there is no other copy anywhere. "
                    "Your history stays on your computer and is never sent "
                    "anywhere."
                ),
                hear="A question, with No chosen to start with.",
            ),
        ),
        closing=(
            "Now you know not just what you listened to, but how much. It is "
            "always fun to find out."
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
            "Keep a copy of everything you have set up, move it to another "
            "computer, stay up to date, and know what to do if something ever "
            "goes wrong."
        ),
        steps=(
            Step(
                title="Back up the stations and the settings",
                body=(
                    "Back Up Stations and Settings saves your favorites, "
                    "settings, wake-up timer and recording schedule into one "
                    "file. It asks whether to include your recordings too, which "
                    "can be large. Both commands are on the Station menu. "
                    "Restore from Backup shows you what is in the file and asks "
                    "before replacing anything."
                ),
                keys=("Ctrl+Shift+U", "Ctrl+Alt+Shift+W"),
                hear="Backing up Quill Radio, then Backup saved to, and the file's name.",
            ),
            Step(
                title="Move the whole setup to another machine",
                body=(
                    "Export My Setup saves even more than a backup, in one file: "
                    "your podcasts, folders and playlists, favorites and saved "
                    "places, settings, your Go To order, your Quick Actions "
                    "order, booked recordings, bookmarks and any keys you "
                    "changed. Import My Setup, next to it on the Help menu, puts "
                    "it all on the other computer."
                ),
                command="app.export_setup",
                keys=("Ctrl+Alt+Shift+N",),
                hear="What the file holds, named, before anything is saved.",
                note=(
                    "Passwords are not included. Sign-ins for private podcasts, "
                    "server passwords and unlock codes stay on the computer they "
                    "are on. Importing replaces what is on the new computer "
                    "rather than mixing the two together."
                ),
            ),
            Step(
                title="Or let a sync service do it",
                body=(
                    "The Data Folder button in Preferences, on the Station menu, "
                    "lets you choose where every Quill app keeps your things. "
                    "Choose a folder that Dropbox, OneDrive, Google Drive or "
                    "iCloud already syncs, and your setup travels with you by "
                    "itself. No extra account and no sign-in."
                ),
                keys=("Ctrl+,",),
                hear="The Data Folder window, and afterwards an offer to Restart Now or Later.",
            ),
            Step(
                title="Stay up to date without being nagged",
                body=(
                    "Check for Updates, on the Help menu, checks whether there "
                    "is a newer version and tells you what changed. It downloads "
                    "it, telling you how far along it is, then offers Install "
                    "now or Open folder. Quill Radio also checks quietly when it "
                    "opens, no more than once a day, and only speaks up if it "
                    "finds something."
                ),
                keys=("Ctrl+Alt+U",),
                hear=(
                    "Either the new version and what changed, or You are up to date, and "
                    "your version."
                ),
                note=(
                    "Quill Radio comes in two downloads: the installer, "
                    "Quill-Radio-Setup-Shared, and the portable zip, "
                    "Quill-Radio-Portable. Check for Updates knows which one you "
                    "have and offers you the same kind again."
                ),
            ),
            Step(
                title="Keep it playing while you work",
                body=(
                    "Send to Tray, on the Station menu, hides the window and "
                    "keeps everything running. Ctrl+Alt+Shift+R shows or hides "
                    "it from anywhere in Windows. The tray icon's menu has what "
                    "is playing now, play and stop, mute, your favorites and "
                    "recently played stations in their folders, recording, "
                    "scheduling and Browse Stations."
                ),
                keys=("Ctrl+W", "Ctrl+Alt+Shift+R"),
                hear=(
                    "Quill Radio hidden to the tray. Then Quill Radio shown when you bring it back."
                ),
            ),
            Step(
                title="Check the installation itself",
                body=(
                    "If playing or recording is not working properly, Audio "
                    "Health tells you whether Quill Radio can do it at all. It "
                    "shows which sound player is in use, whether mpv and FFmpeg "
                    "are there, where the sound is going, and whether a "
                    "recording could be saved right now."
                ),
                keys=("Ctrl+Alt+Shift+M",),
                hear="Audio Health, then each check with its own answer.",
                note=(
                    "mpv and FFmpeg come with every installer, so if one is "
                    "missing, something has removed it. Antivirus programs and "
                    "unfinished updates are the usual reasons. Repair FFmpeg and "
                    "Repair mpv Playback Engine, on the Help menu, bring them "
                    "back."
                ),
            ),
            Step(
                title="Report it properly",
                body=(
                    "Get Help from Support writes to a real person from inside "
                    "Quill Radio, and includes which version you have. Paste in "
                    "the list from Copy All in Recent Problems. It has web "
                    "addresses and error messages in it, but never passwords."
                ),
                keys=("Ctrl+Alt+F2", "Ctrl+Alt+Shift+P"),
                hear="A form with most of it already filled in.",
            ),
            Step(
                title="Know the one setting that turns everything off",
                body=(
                    "Safe Mode starts Quill Radio with everything that uses the "
                    "internet turned off: no directories, no catalog updates, no "
                    "YouTube, no Spotify and no Quillins. To use it, add "
                    "--safe-mode after the program's name when you start it. Try "
                    "it when something is badly wrong and you want to know "
                    "whether the internet is part of the problem."
                ),
                hear="Internet commands saying they are off in Safe Mode, rather than failing.",
            ),
        ),
        closing=(
            "One backup file, one setup file, one health check and one way to "
            "ask for help. With those, everything you have set up is safe."
        ),
    ),
)
