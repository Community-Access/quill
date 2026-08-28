"""Track 6, first half: the questions that come up while you are listening.

What was that? Keep this bit. Stop in twenty minutes. None of these are
features anybody goes looking for on day one, and all three are the ones
people wish they had known about in week two.
"""

from __future__ import annotations

from quill.core.radio.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="what-was-that-song",
        title="What was that song?",
        track="living",
        minutes=5,
        surfaces=("Now Playing", "Song History", "Quill Radio"),
        summary=(
            "Four ways to answer it: ask out loud, open a copyable snapshot, look "
            "back through what has played, and read what the app can find out "
            "about the track."
        ),
        steps=(
            Step(
                title="Ask, and hear the answer",
                body=(
                    "What's Playing says the station and the track in one sentence "
                    "without opening anything. It reads the metadata from the "
                    "stream you are already playing, and as a last resort the "
                    "station's own public now-playing page -- the same host, never "
                    "a third party."
                ),
                command="radio.whats_playing",
                hear="The station, and the track if the stream carries one.",
            ),
            Step(
                title="Open it as text you can review",
                body=(
                    "Speech is gone the moment it finishes, and a song title is "
                    "exactly the kind of thing you want to spell. The Now Playing "
                    "window is a read-only field you can arrow through character by "
                    "character, with a Copy button."
                ),
                command="radio.whats_playing_details",
                hear="The now-playing text, as ordinary reviewable text.",
                check="window:Now Playing",
            ),
            Step(
                title="Copy it straight to the clipboard",
                body=(
                    "Copy What's Playing skips the window when all you want is the "
                    "text -- for a search, a note, or a message to whoever "
                    "recommended the station."
                ),
                command="radio.copy_whats_playing",
                hear="Copied.",
            ),
            Step(
                title="Look back at what has played",
                body=(
                    "Song History is everything the stations you listened to said "
                    "they were playing, with the station and the time. It answers "
                    "the version of the question you ask ten minutes too late."
                ),
                command="radio.song_history",
                hear="Entered Song History, then the tracks, newest first.",
                check="window:Song History",
            ),
            Step(
                title="Ask about the track itself",
                body=(
                    "Where a track can be identified, Quill Radio can tell you more "
                    "about it than the stream said -- and it says where each fact "
                    "came from rather than presenting a lookup as something the "
                    "station published."
                ),
                keys=("Shift+F10",),
                hear="What is known about the track, with its source named.",
            ),
            Step(
                title="Keep the station instead of the song",
                body=(
                    "If the answer is that you like this station rather than this "
                    "track, add it to your favorites from wherever you are -- the "
                    "command follows what is playing and does not need you to find "
                    "the row it came from."
                ),
                command="radio.toggle_playing_favorite",
                hear="Added, and the station's name.",
                check="favorite-added",
            ),
        ),
        closing=(
            "Ask, review, copy, look back. The first is a key; the rest are for "
            "when a key spoken once is not enough."
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
            "Mark where you are in one keystroke, get back to it later, and move "
            "through a recording by chapter without losing your place."
        ),
        steps=(
            Step(
                title="Mark where you are",
                body=(
                    "Bookmark This Moment marks your place on whatever is playing: "
                    "a station, a recording, a saved YouTube row, an episode. No "
                    "note is required -- I was here is the commonest kind of "
                    "bookmark, and having to type a sentence for it is how a "
                    "bookmark does not get made."
                ),
                command="app.bookmark_moment",
                keys=("Ctrl+Alt+A",),
                hear="Bookmarked, and what it was in.",
            ),
            Step(
                title="Add the note later, if there was one",
                body=(
                    "Open the Bookmarks list and use Edit Note on the row. Share "
                    "copies the place, the note and what it is in together, because "
                    "the note on its own is a fragment nobody can act on."
                ),
                command="app.bookmarks",
                keys=("Ctrl+Alt+Shift+J",),
                hear="Entered Bookmarks, then the list.",
            ),
            Step(
                title="Go back to one",
                body=(
                    "Enter goes to the highlighted bookmark. A recording, a video "
                    "and a podcast episode all seek to the moment; a live station's "
                    "bookmark tunes in now instead, because ten minutes into live "
                    "radio meant ten minutes into your listening and tomorrow it "
                    "means something else entirely."
                ),
                keys=("Enter",),
                hear="Either the position restored, or the station tuning in now.",
            ),
            Step(
                title="Open the chapter list",
                body=(
                    "Chapters works on more than a video's published marks: for a "
                    "recording or a downloaded episode it reads the file's own "
                    "chapter frames, and for an episode QUILL Cast has already "
                    "analysed it reads the result Cast left in the shared cache. "
                    "The list says which of those it is using in its first line."
                ),
                command="radio.transport.chapter_list",
                keys=("Ctrl+Shift+C",),
                hear="The chapter list, and the line saying where the chapters came from.",
            ),
            Step(
                title="Check a mark without losing your place",
                body=(
                    "For a file on this computer, the list offers Preview This "
                    "Mark: ten seconds either side of the boundary, played through "
                    "its own player. Your place does not move, so checking six "
                    "marks costs nothing. Both sides, because the question a "
                    "chapter mark raises is does the programme turn here."
                ),
                hear="Twenty seconds of audio, and then silence -- your own playback is untouched.",
            ),
            Step(
                title="Move by chapter while it plays",
                body=(
                    "Next Chapter and Previous Chapter step through without opening "
                    "the list, and they say where you landed. Like every bounded "
                    "verb, they explain themselves on live radio rather than doing "
                    "nothing."
                ),
                command="radio.transport.next_chapter",
                keys=("Ctrl+Shift+.", "Ctrl+Shift+,"),
                hear="The chapter you moved to -- or why a live stream has none.",
            ),
            Step(
                title="Know that the list travels",
                body=(
                    "Your bookmarks are shared with QUILL Cast: one made here is in "
                    "Cast's list and one made there is here, with no account and no "
                    "sync service. A row this app cannot open still appears, with Go "
                    "There dimmed and a reason -- hiding it would leave you "
                    "wondering where your bookmark went."
                ),
                hear="Nothing here: you will notice it the next time you open Cast.",
            ),
        ),
        closing=(
            "One keystroke to keep a moment, one list to find it again, and a way "
            "to audition a chapter mark that costs you nothing."
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
            "Set the radio to stop by itself, to start by itself, and to stop "
            "talking to you between certain hours -- and know precisely what each "
            "of those does not do."
        ),
        steps=(
            Step(
                title="Set a sleep timer",
                body=(
                    "The status bar's Sleep timer cell is the quickest route: press "
                    "F6, arrow to it and press Enter. The radio stops itself after "
                    "the time you choose, which is the whole point of a radio "
                    "beside a bed."
                ),
                keys=("F6", "Enter"),
                hear="The sleep timer set, and the time it will stop.",
            ),
            Step(
                title="Set a wake-up timer",
                body=(
                    "The Wake-Up Timer starts a station at a time you choose. Quill "
                    "Radio -- or QUILL -- has to be running for it to fire; the tray "
                    "icon counts, and a closed app does not."
                ),
                command="radio.wake_timer",
                hear="Entered the Wake-Up Timer.",
                note=(
                    "It never retro-fires. Opening the app hours after the set time "
                    "stays silent until the next occurrence, rather than starting a "
                    "station at lunchtime because you missed breakfast."
                ),
            ),
            Step(
                title="Stop the app talking overnight",
                body=(
                    "Quiet Hours sets a window -- 22:00 to 07:00 by default, and it "
                    "may cross midnight -- in which the app stops speaking on its "
                    "own. Feeds are still checked, downloads still run, recordings "
                    "still record. Only the announcements about them wait."
                ),
                keys=("Ctrl+Alt+Shift+Z",),
                hear="The window read back.",
            ),
            Step(
                title="Know what quiet hours never silence",
                body=(
                    "Anything you press a key for still answers. Press Play at three "
                    "in the morning and you hear what is playing -- quiet hours hold "
                    "back the speech nobody asked for, not the reply to something you "
                    "asked. Failures always speak too: a recording that stopped at "
                    "3 a.m. is exactly the thing somebody set an alarm clock for."
                ),
                hear="A normal spoken reply, at any hour.",
            ),
            Step(
                title="Set a reminder for something you must not miss",
                body=(
                    "Set a Reminder is on the context menu of any programme in the "
                    "schedule and any station, recording or saved row in the tree. It "
                    "asks when, an optional note, and a priority. High priority is the "
                    "only thing that comes through quiet hours on its own."
                ),
                keys=("Shift+F10",),
                hear="The reminder set, and when it will come.",
                note=(
                    "Once a row has a reminder, the same menu slot reads Remove "
                    "Reminder instead. A menu that cannot tell you what you already "
                    "did is a menu you have to remember for -- which is the job the "
                    "reminder was taking off you."
                ),
            ),
            Step(
                title="Recognise a reminder when it arrives",
                body=(
                    "The reminder sound comes first -- three rising bell tones, "
                    "unlike anything else in the app -- and then the sentence. The "
                    "sound is first on purpose: if you know it, you have already "
                    "turned your attention by the time the words begin."
                ),
                hear="Three rising tones, then what it is and when it starts.",
            ),
            Step(
                title="Keep the machine awake for it",
                body=(
                    "Keep the computer awake while playing or recording is on by "
                    "default, so Windows does not sleep mid-listen. Your screen can "
                    "still turn off, and the moment nothing is playing or recording "
                    "the setting lets the computer sleep normally again."
                ),
                keys=("Ctrl+,",),
                hear="The setting read back.",
            ),
        ),
        closing=(
            "Sleep, wake, quiet, remind. Four separate promises, each one honest "
            "about what it does not cover."
        ),
    ),
)
