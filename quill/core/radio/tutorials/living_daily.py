"""Track 6, first half: the questions that come up while you are listening.

What was that? Keep this bit. Stop in twenty minutes. None of these are
features anybody goes looking for on day one, and all three are the ones
people wish they had known about in week two.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="what-was-that-song",
        title="What was that song?",
        track="living",
        minutes=5,
        surfaces=("Now Playing", "Song History", "Quill Radio"),
        summary=(
            "Heard a song you loved? Here are four ways to find out what it was: "
            "ask out loud, open the details as text you can copy, look back "
            "through what has played, and find out more about the song."
        ),
        steps=(
            Step(
                title="Ask, and hear the answer",
                body=(
                    "What's Playing tells you the station and the song in one "
                    "sentence, without opening anything. It gets the details "
                    "from the station you are listening to, or if needed from "
                    "the station's own now playing web page. It has no key of "
                    "its own in Quill Radio, so type what's playing in the "
                    "command palette."
                ),
                command="radio.whats_playing",
                hear="The station, and the song if the station sends one.",
            ),
            Step(
                title="Open it as text you can review",
                body=(
                    "Speech is gone as soon as it is spoken, and a song title is "
                    "just the kind of thing you might want to spell out. The Now "
                    "Playing window shows it in a box you can arrow through "
                    "letter by letter, with a Copy button. What's Playing on the "
                    "Playback menu opens this window."
                ),
                command="radio.whats_playing_details",
                keys=("Ctrl+T",),
                hear="The now playing text, ready to read at your own pace.",
                check="window:Now Playing",
            ),
            Step(
                title="Copy it straight to the clipboard",
                body=(
                    "Copy What's Playing skips the window when all you want is "
                    "the text, for a search, a note, or a message to whoever "
                    "told you about the station. It is in the command palette, "
                    "and the Copy button in the Now Playing window does the same."
                ),
                command="radio.copy_whats_playing",
                hear="Copied, and the text that went to the clipboard.",
            ),
            Step(
                title="Look back at what has played",
                body=(
                    "Song History lists every song the stations you listened to "
                    "said they were playing, with the station and the time. It "
                    "is perfect for when you think of the question ten minutes "
                    "too late."
                ),
                command="radio.song_history",
                keys=("Ctrl+Shift+H",),
                hear="Song History, then the songs, newest first.",
                check="window:Song History",
            ),
            Step(
                title="Ask about the track itself",
                body=(
                    "In Song History, arrow to a song and press the Song Details "
                    "button. Quill Radio looks the song up on MusicBrainz and "
                    "tells you the album, the year and how long it is. It only "
                    "looks it up when you ask, and it always tells you the "
                    "details came from MusicBrainz, not the station."
                ),
                keys=("Alt+D",),
                hear=(
                    "Looking up, and the song, then its album, year and length. Or that "
                    "nothing more is known."
                ),
            ),
            Step(
                title="Keep the station instead of the song",
                body=(
                    "If what you really like is the station, add it to your "
                    "favorites from wherever you are. This command always saves "
                    "whatever is playing, so you do not need to find its row."
                ),
                command="radio.toggle_playing_favorite",
                hear="Added, and the station's name.",
                check="favorite-added",
            ),
        ),
        closing=(
            "Ask, read, copy, look back. Asking is one key, and the rest are "
            "there for when hearing it once is not enough. You will never lose a "
            "song again."
        ),
        then=("keep-a-moment",),
    ),
    Tutorial(
        slug="keep-a-moment",
        title="Keep a moment, and move around inside one",
        track="living",
        minutes=6,
        surfaces=("Bookmarks", "Chapters", "Quill Radio"),
        summary=(
            "Mark your place with one key, come back to it later, and move "
            "through a recording chapter by chapter without losing your place."
        ),
        steps=(
            Step(
                title="Mark where you are",
                body=(
                    "Bookmark This Moment marks your place in whatever is "
                    "playing: a station, a recording, a saved YouTube video or a "
                    "podcast episode. You do not need to type a note. Most of "
                    "the time, I was here is all a bookmark needs to say."
                ),
                command="app.bookmark_moment",
                keys=("Ctrl+Alt+A",),
                hear="Bookmarked, the position in words, and what it was in.",
            ),
            Step(
                title="Add the note later, if there was one",
                body=(
                    "Open the Bookmarks list and press the Edit Note button on "
                    "the row if you want to add a note. Share copies the place, "
                    "the note and what it was in, all together, so whoever gets "
                    "it can find the moment too."
                ),
                command="app.bookmarks",
                keys=("Ctrl+Alt+Shift+J",),
                hear="Bookmarks, then the list.",
            ),
            Step(
                title="Go back to one",
                body=(
                    "Press Enter on a bookmark to go to it. A recording, a video "
                    "or a podcast episode jumps straight to that moment. A live "
                    "station's bookmark tunes in to the station now, because "
                    "live radio cannot go back to yesterday."
                ),
                keys=("Enter",),
                hear="Either your place, back again, or the station tuning in now.",
            ),
            Step(
                title="Open the chapter list",
                body=(
                    "Chapters lists the chapters in what is playing. That might "
                    "be chapters the video came with, chapters stored in a "
                    "recording or downloaded episode, or chapters QUILL Cast has "
                    "already worked out for an episode. The first line of the "
                    "list tells you where the chapters came from."
                ),
                command="radio.transport.chapter_list",
                keys=("Ctrl+Shift+C",),
                hear="The chapter list, and the line saying where the chapters came from.",
            ),
            Step(
                title="Check a mark without losing your place",
                body=(
                    "For a file on your computer, the list offers Preview This "
                    "Mark. It plays ten seconds before and ten seconds after the "
                    "chapter mark, in a separate player, so you can hear whether "
                    "the programme really changes there. Your own place does not "
                    "move, so try as many as you like."
                ),
                keys=("Alt+P",),
                hear=(
                    "Previewing, and the mark, then twenty seconds of sound. Your own "
                    "place stays where it was."
                ),
            ),
            Step(
                title="Move by chapter while it plays",
                body=(
                    "Next Chapter and Previous Chapter move through the chapters "
                    "without opening the list, and tell you where you landed. On "
                    "live radio, they tell you there are no chapters, so you are "
                    "never left wondering."
                ),
                command="radio.transport.next_chapter",
                keys=("Ctrl+Shift+.", "Ctrl+Shift+,"),
                hear="The chapter you moved to. Or why a live stream has none.",
            ),
            Step(
                title="Know that the list travels",
                body=(
                    "Your bookmarks are shared with QUILL Cast. One you make here "
                    "shows up in Cast, and one you make in Cast shows up here, "
                    "with no account or sync service. If Quill Radio cannot open "
                    "one, it still shows it, with Go There dimmed and a reason, "
                    "so you never wonder where it went."
                ),
                hear="Nothing here. You will notice it next time you open Cast.",
            ),
        ),
        closing=(
            "One key to keep a moment, one list to find it again, and a way to "
            "check a chapter without losing your place. Lovely."
        ),
        then=("sleep-and-quiet",),
    ),
    Tutorial(
        slug="sleep-and-quiet",
        title="Sleeping, waking, and being left alone",
        track="living",
        minutes=6,
        surfaces=("Quill Radio", "Wake-Up Timer", "Quiet Hours"),
        summary=(
            "Set the radio to switch off by itself, to switch on by itself, and "
            "to stop talking to you at night. You will also learn exactly what "
            "each one leaves alone."
        ),
        steps=(
            Step(
                title="Set a sleep timer",
                body=(
                    "Sleep Timer, on the Playback menu, asks how long. You can "
                    "also press F6, arrow to the Sleep timer item in the status "
                    "bar and press Enter. The radio switches itself off after "
                    "the time you choose, perfect for drifting off to sleep."
                ),
                keys=("Ctrl+Shift+Z", "F6", "Enter"),
                hear="Sleep timer set for, and the number of minutes.",
            ),
            Step(
                title="Set a wake-up timer",
                body=(
                    "The Wake-Up Timer starts a station at a time you choose. "
                    "Quill Radio, or QUILL, needs to be running for it to work. "
                    "Running in the tray is fine, but if the app is closed, it "
                    "cannot wake you."
                ),
                command="radio.wake_timer",
                hear="Wake-Up Timer, and its first control.",
                note=(
                    "It never goes off late. If you open Quill Radio hours after "
                    "the time you set, it waits until next time, rather than "
                    "starting your morning station at lunchtime."
                ),
            ),
            Step(
                title="Stop the app talking overnight",
                body=(
                    "Quiet Hours, on the Help menu, sets a stretch of time when "
                    "Quill Radio stops speaking on its own. It starts as 22:00 to "
                    "07:00, and it can run past midnight. Podcasts are still "
                    "checked, downloads still run, and recordings still record. "
                    "Only the messages about them wait until morning."
                ),
                command="app.quiet_hours",
                hear=(
                    "Quiet Hours, with its on switch, its From and To times, and the "
                    "times read back."
                ),
            ),
            Step(
                title="Know what quiet hours never silence",
                body=(
                    "Anything you press a key for still answers you. Press Play "
                    "at three in the morning and you hear what is playing. Quiet "
                    "hours only hold back messages you did not ask for. Problems "
                    "are always spoken too, because if a recording stops at 3 "
                    "a.m., you want to know."
                ),
                hear="A normal spoken answer, at any hour.",
            ),
            Step(
                title="Set a reminder for something you must not miss",
                body=(
                    "Set a Reminder is on the context menu of any programme in "
                    "the schedule, and of any station, recording or saved row in "
                    "Browse Stations. It asks when, an optional note, and a "
                    "priority. Only a high priority reminder comes through quiet "
                    "hours by itself."
                ),
                keys=("Shift+F10",),
                hear="Reminder set for, the name, and when it will come.",
                note=(
                    "Once a row has a reminder, the same menu item says Remove "
                    "Reminder instead. So the menu always tells you what you "
                    "have already set."
                ),
            ),
            Step(
                title="Recognise a reminder when it arrives",
                body=(
                    "First you hear the reminder sound, three rising bell tones "
                    "that sound like nothing else in Quill Radio. Then you hear "
                    "the message. Once you know the sound, you are already "
                    "listening by the time the words begin."
                ),
                hear="Three rising tones, then what it is and when it starts.",
            ),
            Step(
                title="Keep the machine awake for it",
                body=(
                    "Keep the computer awake while playing or recording is on to "
                    "start with, so Windows does not go to sleep while you "
                    "listen. Your screen can still turn off. As soon as nothing "
                    "is playing or recording, your computer can sleep as usual."
                ),
                keys=("Ctrl+,",),
                hear="The setting read back.",
            ),
        ),
        closing=(
            "Sleep, wake, quiet and remind. Four handy helpers, each one clear "
            "about what it does and what it leaves alone. Sleep well."
        ),
    ),
)
