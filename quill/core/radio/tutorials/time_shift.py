"""Track 6: moving song by song through the time-shift buffer, and its length.

Two lessons. The first walks the song marks: back to the start of a song,
on to the next, which song am I in, and saving one to a file of its own. The
second gives one favorite a time-shift length of its own.

Both need the mpv playback engine, which is the default; the lessons say so
where it matters rather than up front, because most listeners already have it.

The ideas -- song marks in the buffer, saving songs from it, and a length per
station -- come from BlindRadio by serrebidev (MIT),
docs/design/blindradio-ideas/time-shift.md. No BlindRadio text was copied.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="jump-between-songs",
        title="Jump between songs, and save one",
        track="living",
        minutes=6,
        surfaces=("Quill Radio", "Now Playing"),
        summary=(
            "Go back to the start of the song you are in, on to the next one, ask "
            "which song you are in, and save a song from the buffer to a file of "
            "its own."
        ),
        steps=(
            Step(
                title="Let a music station run for a while",
                body=(
                    "Quill Radio marks where each song starts, every time the "
                    "station sends a new title. Play a music station that names "
                    "its songs and leave it for ten minutes or so, so the buffer "
                    "holds a few of them. There is nothing to set."
                ),
                command="radio.browse",
                hear="Browse Stations, then the station playing.",
                check="playing",
                note=(
                    "Announcements such as Live or the station's own name mark "
                    "nothing, so the song before keeps the time."
                ),
            ),
            Step(
                title="Go back to the start of this song",
                body=(
                    "Previous Song, on the Playback menu, takes you back to where "
                    "the song you are in began. Press it again within a few seconds "
                    "and you go to the song before. You are now listening behind "
                    "live, from the buffer."
                ),
                command="radio.previous_song",
                hear="The song's title, then how far behind live you are.",
            ),
            Step(
                title="Ask which song you are in",
                body=(
                    "Which Song Is This tells you the song, how far into it you "
                    "are, which song it is of how many in the buffer, and how far "
                    "behind live. It is the question to ask when you have lost "
                    "track of where you are."
                ),
                command="radio.which_song",
                hear="The title, how far in, song 2 of 4 in the buffer, and how far behind live.",
            ),
            Step(
                title="Go on to the next song",
                body=(
                    "Next Song goes on to the start of the next one. After the "
                    "newest song it goes back to live, so pressing it a few times "
                    "is a safe way home."
                ),
                command="radio.next_song",
                hear="The next song's title and how far behind live. Or Back to live.",
            ),
            Step(
                title="Save the song you are in",
                body=(
                    "Save Songs from the Buffer, on the Playback menu, writes songs "
                    "to files of their own in your recordings folder. Save This "
                    "Song saves the one you are in, exactly as the station sent "
                    "it, named with the station, the time and the title."
                ),
                command="radio.save_current_song",
                hear="Saved, the song's title, and the folder it went to.",
                note=(
                    "A song still playing is saved as far as it has got. An "
                    "earlier file is never overwritten."
                ),
            ),
            Step(
                title="Save the one before, the one after, or all of them",
                body=(
                    "The same submenu has Save the Previous Song, Save the Next "
                    "Song and Save All Songs in the Buffer. They are worth knowing "
                    "for the moment you realise the song you loved has just ended."
                ),
                command="radio.save_previous_song",
                keys=("Ctrl+Alt+F7", "Ctrl+Alt+F5"),
                hear="Saved, and the title. For all of them, how many songs were saved.",
            ),
        ),
        closing=(
            "Song marks start again whenever you change station, and a mark can "
            "be a second or two either side of the real change. The idea comes "
            "from BlindRadio by serrebidev."
        ),
        then=("station-timeshift-length",),
    ),
    Tutorial(
        slug="station-timeshift-length",
        title="Give one station a time-shift length of its own",
        track="living",
        minutes=3,
        surfaces=("Quill Radio", "Manage Favorites"),
        summary=(
            "Keep five hours of the station you love and none of the one you only "
            "check for the news, without changing anybody else's."
        ),
        steps=(
            Step(
                title="Make it a favorite first",
                body=(
                    "A station keeps its own length with its favorite, so play the "
                    "station and add it if it is not one already. If it is a "
                    "favorite, skip this step, because the same command takes a "
                    "favorite away again."
                ),
                command="radio.toggle_playing_favorite",
                hear="Added, and the station's name.",
                check="favorite-added",
            ),
            Step(
                title="Open its time-shift length",
                body=(
                    "Time-Shift Length for This Station, on the Playback menu, "
                    "works on the station playing, or on the favorite selected in "
                    "the main window when nothing plays. A list of lengths opens on "
                    "the one it has now."
                ),
                command="radio.station_timeshift",
                hear="How much of the station should the time-shift buffer keep? Then a list.",
            ),
            Step(
                title="Choose a length",
                body=(
                    "Arrow through the list, from in memory only, about 45 "
                    "minutes, up to 5 hours on disk. The first row, Same as "
                    "Preferences, follows the Time-shift buffer setting again, and "
                    "says what that is now. Press Enter on the one you want."
                ),
                keys=("Down arrow", "Enter"),
                hear="The station, the length you chose, and that it takes effect next time.",
                note="Escape leaves the length as it was.",
            ),
            Step(
                title="Hear it take effect",
                body=(
                    "The new length starts the next time the station starts, so "
                    "the buffer you have now is not thrown away. Press Play/Stop "
                    "once to stop and again to start the station afresh, and "
                    "Rewind can reach as far as the new length allows."
                ),
                command="radio.play_pause",
                hear="Stopped, then the station playing again.",
                check="playing",
            ),
        ),
        closing=(
            "Every favorite can keep its own length, and the rest follow "
            "Preferences. The idea comes from BlindRadio by serrebidev."
        ),
    ),
)
