"""Track 6: what the station says it played, sending what you heard, and AudD.

Three lessons that grow out of "what was that song?": the station's own list
of what it played, which reaches back before you tuned in; scrobbling, which
keeps a list of what you heard on a service of your choice; and the choice
between AcoustID and AudD for Identify This Song.

The scrobbling and AudD lessons stop short of anything that needs a real
account. Every step can be done, and heard, without a token: the token box is
named and left alone, and the lesson says what happens either way.

The ideas -- a station's own published playlist, scrobbling, and AudD as a
second recogniser -- come from BlindRadio by serrebidev (MIT),
docs/design/blindradio-ideas/song-history-sources.md and
scrobbling-and-recognition.md. No BlindRadio text was copied.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="what-the-station-played",
        title="Ask the station what it played",
        track="living",
        minutes=5,
        surfaces=("What the Station Played", "Quill Radio", "Browse Stations"),
        summary=(
            "Open the list a station publishes of the songs it played, with the "
            "time each one started, reaching back before you tuned in. Then copy "
            "a song or look it up."
        ),
        steps=(
            Step(
                title="Play a station that publishes a list",
                body=(
                    "Not every station publishes one. Radio Paradise does, and so "
                    "do KEXP, the BBC, Live365, laut.fm, AzuraCast stations and "
                    "many US stations streamed by Triton Digital. In Browse "
                    "Stations, open Radio Paradise and press Enter on a channel."
                ),
                command="radio.browse",
                keys=("Enter",),
                hear="Browse Stations, then the channel playing.",
                check="playing",
            ),
            Step(
                title="Ask what the station played",
                body=(
                    "What the Station Played, on the Playback menu, asks the "
                    "station for its own list. It sits beside Song History on the "
                    "same letter, because Song History is what Quill Radio heard "
                    "and this is what the station says it sent."
                ),
                command="radio.station_playlist",
                hear=(
                    "Asking Radio Paradise for the playlist, then the window, on the newest song."
                ),
                note=(
                    "On a station that publishes no list you hear that in one "
                    "sentence, and nothing opens. Nothing is fetched until you ask."
                ),
            ),
            Step(
                title="Read the list, newest first",
                body=(
                    "Arrow down through the songs. Each one says when it started, "
                    "or playing now for the one on the air. The BBC only says how "
                    "long ago, so its songs read like 3 minutes ago."
                ),
                keys=("Down arrow",),
                hear="A song by its artist, and the time it started.",
            ),
            Step(
                title="Check who published it",
                body=(
                    "Tab past the list to Where this list comes from. It names who "
                    "published the list, so you know the times came from the "
                    "station and not from Quill Radio guessing."
                ),
                keys=("Tab",),
                hear="Where this list comes from, and the publisher's name.",
            ),
            Step(
                title="Copy a song, or find out more",
                body=(
                    "With a song selected, the buttons work exactly as they do in "
                    "Song History: Copy, Send to Clip Library, Song Details and "
                    "Lyrics. Song Details asks MusicBrainz for the album and year, "
                    "and only when you press it."
                ),
                keys=("Alt+C", "Alt+D", "Alt+Y"),
                hear="Copied, and the song.",
            ),
            Step(
                title="Close it",
                body=(
                    "Escape closes the window and takes you back where you were. "
                    "The list is fetched fresh each time you open it, so open it "
                    "again later for the songs played since."
                ),
                keys=("Escape",),
                hear="The window you came from.",
            ),
        ),
        closing=(
            "Song History remembers what you heard, and What the Station Played "
            "fills in what you missed. The idea, and the list of where to look, "
            "come from BlindRadio by serrebidev."
        ),
        then=("scrobble-to-listenbrainz",),
    ),
    Tutorial(
        slug="scrobble-to-listenbrainz",
        title="Keep a list of what you heard on ListenBrainz",
        track="living",
        minutes=4,
        surfaces=("Quill Radio Preferences", "Preferences"),
        summary=(
            "Find where scrobbling is turned on, learn exactly what it sends, and "
            "where your ListenBrainz token goes. Nothing here needs an account to "
            "follow."
        ),
        steps=(
            Step(
                title="Open Preferences",
                body=(
                    "Scrobbling adds the songs you hear to your listening history "
                    "on ListenBrainz, last.fm or Libre.fm. It is off until you turn "
                    "it on, separately for each service, in Preferences."
                ),
                keys=("Ctrl+,",),
                hear="Quill Radio Preferences, and its first check box.",
            ),
            Step(
                title="Find the Scrobbling group",
                body=(
                    "Tab down to the Scrobbling group. Its first control is the "
                    "check box for ListenBrainz, followed by last.fm and Libre.fm. "
                    "Leave it as it is for now; the next step says what it sends."
                ),
                keys=("Tab",),
                hear="Send the songs I hear to ListenBrainz, check box, not checked.",
            ),
            Step(
                title="Hear exactly what is sent",
                body=(
                    "Press F1 on the check box. Scrobbling sends the artist, title "
                    "and album of each song you hear for a minute or more, and when "
                    "you heard it. Nothing about the station or about you is sent, "
                    "and nothing at all in Safe Mode."
                ),
                keys=("F1",),
                hear="The check box's help, ending with what is sent.",
            ),
            Step(
                title="Find where the token goes",
                body=(
                    "Tab on to ListenBrainz user token. ListenBrainz gives every "
                    "account a user token on its settings page; it goes here, and "
                    "Quill Radio keeps it in the Windows credential store, not in "
                    "a settings file. Without an account, leave the box empty."
                ),
                keys=("Tab",),
                hear="ListenBrainz user token, edit.",
                note=(
                    "last.fm and Libre.fm sign in through their own web page "
                    "instead, with the Sign In buttons further down. You never "
                    "type their password into Quill Radio."
                ),
            ),
            Step(
                title="Turn it on, or leave without changing anything",
                body=(
                    "With a token pasted in, check Send the songs I hear to "
                    "ListenBrainz and press Enter for OK. Without one, press "
                    "Escape: a check box on with no token only keeps the songs "
                    "waiting, for up to two weeks, until a token arrives."
                ),
                keys=("Space", "Escape"),
                hear="Preferences saved, or the window you came from after Escape.",
                note=(
                    "If you choose OK with the check box on and no token, you hear "
                    "ListenBrainz is on, but there is no user token yet."
                ),
            ),
        ),
        closing=(
            "A song counts once you have heard a minute of it, and the station's "
            "own name, adverts and titles with no artist are never sent. The idea "
            "comes from BlindRadio by serrebidev."
        ),
        then=("choose-audd",),
    ),
    Tutorial(
        slug="choose-audd",
        title="AcoustID or AudD: which one names the song",
        track="living",
        minutes=3,
        surfaces=("Quill Radio Preferences", "Preferences"),
        summary=(
            "Learn the difference between the two services Identify This Song "
            "can ask, and where the choice lives. A lesson to read: it changes "
            "nothing."
        ),
        steps=(
            Step(
                title="Know what Identify This Song does",
                body=(
                    "Identify This Song, on the Playback menu, listens to the last "
                    "minute of what you are hearing and asks a recognition service "
                    "what the song is. You do not need to press it for this lesson."
                ),
                command="radio.identify_song",
                hear="Nothing yet. This step only names the key.",
            ),
            Step(
                title="Know what each service is sent",
                body=(
                    "AcoustID is free and is sent only a fingerprint, a summary of "
                    "the sound that cannot be played back. AudD needs an account "
                    "of your own and is sent about twenty seconds of the audio "
                    "itself, but copes better when a presenter talks over a song."
                ),
                hear="Nothing. This step is one to read.",
                note=(
                    "Either way, nothing is sent until you press the key, and "
                    "nothing at all in Safe Mode."
                ),
            ),
            Step(
                title="Find the choice in Preferences",
                body=(
                    "Open Preferences and Tab down to the Song recognition group. "
                    "Song recognition service says which one Ctrl+K asks. It is "
                    "AcoustID unless you have chosen otherwise."
                ),
                keys=("Ctrl+,",),
                hear="Song recognition service, AcoustID.",
            ),
            Step(
                title="Leave without changing it",
                body=(
                    "Press Escape to close Preferences as it was. To use AudD "
                    "later, choose AudD here and paste your token into AudD API "
                    "token. The token is kept in the Windows credential store."
                ),
                keys=("Escape",),
                hear="The window you came from.",
                note=(
                    "AudD also needs no fpcalc program, which AcoustID does. The "
                    "user guide's Choosing AudD instead of AcoustID has the steps."
                ),
            ),
        ),
        closing=(
            "Fingerprint or audio, free or your own account: that is the whole "
            "choice. The idea of offering AudD comes from BlindRadio by serrebidev."
        ),
    ),
)
