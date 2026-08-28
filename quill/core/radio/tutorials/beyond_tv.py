"""Track 5, second half: television, the ACB Media schedule, and weather radio.

Three sources that are unlike the rest. Television is video arriving through a
radio app's tree. ACB Media is the only source in Quill Radio with a published
*schedule*, so it is the only one where "what is on at eight" is a question
the app can answer. NOAA Weather Radio is a directory of transmitters rather
than of stations, and it is bundled, so it works with no connection at all.
"""

from __future__ import annotations

from quill.core.radio.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="watch-television",
        title="Watch television",
        track="beyond",
        minutes=6,
        surfaces=("Browse Stations", "Video"),
        summary=(
            "Find a channel by country, category or postcode, play it with the "
            "same keys as everything else, and give yourself a programme guide if "
            "you want one."
        ),
        steps=(
            Step(
                title="Find the branch",
                body=(
                    "Television sits in Browse Stations just above YouTube. It is "
                    "built on the iptv.org community catalog -- roughly 9,300 "
                    "playable channels after Quill Radio's own filtering, which "
                    "removes adult-flagged channels, closed ones, ones with no "
                    "stream, and streams that would fail the moment you pressed "
                    "Enter."
                ),
                command="radio.browse",
                hear="Television, then By Country and By Category.",
                check="window:Browse Stations",
            ),
            Step(
                title="Open your own country",
                body=(
                    "A country whose feeds declare local coverage opens into "
                    "Nationwide plus its states, and a state's list carries its own "
                    "channels and its cities', each city named on the row. A "
                    "country without local data stays a single list rather than "
                    "making you open folders with nothing in them."
                ),
                keys=("Right arrow",),
                hear="The country, then Nationwide and the states.",
            ),
            Step(
                title="Search by place, not only by name",
                body=(
                    "Anywhere you can search -- Find Stations, Search All Sources, "
                    "the Find box -- television answers by channel name, network, "
                    "country, city, state, or a five-digit ZIP code. Typing 66044 "
                    "answers with Kansas television, because a ZIP is a place."
                ),
                keys=("Ctrl+F",),
                hear="The matching channels.",
                note=(
                    "The ZIP mapping is by postal prefix. It is exact enough to "
                    "narrow a list and claims nothing about what your antenna can "
                    "pull in -- which is what the antennaweb link is for."
                ),
            ),
            Step(
                title="Play a channel",
                body=(
                    "Enter plays it, and the video opens with the same captions, "
                    "audio-track selection and transport every stream gets. Show or "
                    "hide the picture with Ctrl+Shift+V -- the audio carries on "
                    "either way, which is the point on a screen you are not "
                    "looking at."
                ),
                keys=("Enter", "Ctrl+Shift+V"),
                hear="The channel playing, and the video window announced when it opens.",
            ),
            Step(
                title="Turn on captions and read them",
                body=(
                    "Ctrl+Shift+K turns captions on and they open in their own "
                    "window as text you can arrow through: each line joins the ones "
                    "already spoken, and the line being spoken now is marked. It "
                    "never announces itself, so read it whenever you like."
                ),
                keys=("Ctrl+Shift+K",),
                hear="The captions window, and then nothing until you go and read it.",
                note=(
                    "Follow Playback can be switched off so the window holds still "
                    "while you read back. Escape closes it, and closing it turns "
                    "captions off."
                ),
            ),
            Step(
                title="Choose the audio track",
                body=(
                    "Ctrl+Shift+A lists the audio and described-audio tracks, "
                    "leading with the language you read the app in, then the "
                    "video's own original track, then the rest alphabetically -- so "
                    "a channel with two dozen dubs is a list you can find your way "
                    "down."
                ),
                keys=("Ctrl+Shift+A",),
                hear="The track list, your language first.",
            ),
            Step(
                title="Give yourself a programme guide",
                body=(
                    "Drop an XMLTV guide named tv_guide.xml into your Quill Radio "
                    "data folder and every channel it covers gains a Now and Next "
                    "line in its details. It is read locally, works offline, is "
                    "re-read when you replace it, and is never fetched from "
                    "anywhere. Delete the file and the lines disappear."
                ),
                hear="Now, and Next, in the details of a covered channel.",
                note=(
                    "There is no one TV guide feed for the world -- guides are "
                    "published per country and per provider -- so the file is "
                    "deliberately yours to choose rather than the app's to pick."
                ),
            ),
            Step(
                title="Keep the channel list current",
                body=(
                    "The channel list updates itself weekly; it is the largest "
                    "catalog in the app at about 28 MB. Update the channel list "
                    "now, at the top of the branch, fetches today's copy on demand "
                    "and says what it is doing while it works."
                ),
                hear="Progress while it fetches, then how many channels it has.",
            ),
        ),
        closing=(
            "Television is video in a radio app, and it behaves like radio: "
            "favorite it, record it, schedule it, and drive it with the keys you "
            "already know."
        ),
    ),
    Tutorial(
        slug="acb-media-schedule",
        title="The ACB Media schedule",
        track="beyond",
        minutes=7,
        surfaces=("ACB Media Schedule", "Upcoming"),
        summary=(
            "Read a published schedule across ten channels, find a programme, "
            "record it or be reminded about it, and understand why the list "
            "sometimes has nothing in it for today."
        ),
        steps=(
            Step(
                title="Open the schedule",
                body=(
                    "One list, oldest first, each row carrying its date, both its "
                    "times, its programme and its channel. It opens on the next "
                    "programme still to come rather than at the start of a "
                    "fortnight that may already have finished."
                ),
                command="radio.acb_calendar",
                hear="Entered the schedule, then the next programme still to come.",
            ),
            Step(
                title="Read the line above the list",
                body=(
                    "It always says how far the published schedule runs -- 49 "
                    "programmes published; the published schedule runs 1 August to "
                    "15 August -- and says so plainly when that is behind us. ACB "
                    "publishes a fortnight at a time and then stops, so for much of "
                    "a month there is nothing posted for today. That is not a "
                    "fault."
                ),
                keys=("Shift+Tab",),
                hear="The sentence, in a field you can arrow through word by word.",
            ),
            Step(
                title="Check whose clock the times are on",
                body=(
                    "ACB publishes in US Central time and Quill Radio converts "
                    "every programme to your own clock. The line says so when the "
                    "two differ -- because shown a bare 7:00 AM you have no way to "
                    "tell a correct conversion from a missing one."
                ),
                hear="Times are shown in your zone, and the zone ACB publishes in.",
            ),
            Step(
                title="Find one programme",
                body=(
                    "Three filters, all of which narrow what is listed and change "
                    "nothing about what is playing. Search wants every word to "
                    "appear somewhere, in any field, so blues tuesday finds the "
                    "Tuesday blues show. Date jumps to a day that actually has "
                    "programmes. Channel narrows to one of the ten."
                ),
                keys=("Alt+S",),
                hear="The number of programmes left after the filter.",
            ),
            Step(
                title="Do something with a programme",
                body=(
                    "Six verbs, each reachable from the context menu, from the "
                    "buttons in the same order, and -- for Play -- from Enter: "
                    "Play, Record, Remind Me, Add to Queue, Copy Details and Show "
                    "Notes. A verb that cannot run is dimmed and says why."
                ),
                keys=("Shift+F10",),
                hear="The action's own confirmation, naming the programme.",
                note=(
                    "Play tunes in to the programme's channel, and stops it if that "
                    "channel is what you are already listening to. Live radio has "
                    "one thing on it at a time, so Quill Radio tells you whether "
                    "the programme is on now or when it starts."
                ),
            ),
            Step(
                title="Book it, without doing the arithmetic",
                body=(
                    "Record confirms the channel, the date, the time and the length "
                    "-- the four things the schedule already knows -- and schedules "
                    "it. It then appears in Recordings and in Upcoming like any "
                    "other scheduled recording."
                ),
                hear="The four details read back, then the recording scheduled.",
            ),
            Step(
                title="Ask what is on without opening anything",
                body=(
                    "What Is On Now answers in one sentence across all ten "
                    "channels. It answers from the stored schedule so it answers "
                    "straight away -- a key that spends four seconds on a feed "
                    "before speaking is a key nobody presses twice."
                ),
                command="radio.on_now",
                hear="What is on, across the channels, in one sentence.",
            ),
            Step(
                title="Re-read the schedule",
                body=(
                    "Three ways, because one was not enough: the Refresh button, "
                    "Refresh the Schedule on the list's own context menu (offered "
                    "even when nothing is selected, which is exactly when you want "
                    "it), and Refresh the Schedule from anywhere in the app, window "
                    "open or shut."
                ),
                command="radio.refresh_calendar",
                hear=(
                    "Pulled from ACB just now, with the clock time -- and it changes only when the "
                    "fetch lands."
                ),
            ),
            Step(
                title="See everything you have planned",
                body=(
                    "Upcoming is your reminders and your scheduled recordings "
                    "together, soonest first, with the kind written on every row. "
                    "Snooze and Dismiss work on reminders only -- a scheduled "
                    "recording is cancelled where it was made, because Dismiss "
                    "meaning two different mornings would be one button too many."
                ),
                command="radio.upcoming",
                hear="Entered Upcoming, then each item with its kind and time.",
            ),
        ),
        closing=(
            "The schedule is kept on this computer and read again every time you "
            "open the window. With no connection it opens from what it has and "
            "tells you how old that is."
        ),
    ),
    Tutorial(
        slug="weather-radio",
        title="NOAA Weather Radio",
        track="beyond",
        minutes=4,
        surfaces=("Browse Stations",),
        summary=(
            "Find your local weather transmitter by state, by call sign or by "
            "county, and know that the whole directory works with no connection."
        ),
        steps=(
            Step(
                title="Open the branch",
                body=(
                    "Weather / NOAA in the browse tree is the real NOAA Weather "
                    "Radio directory, state by state, each state announcing its "
                    "transmitter count. The complete directory -- 1,035 "
                    "transmitters -- is bundled inside the app, so this branch "
                    "works offline."
                ),
                command="radio.browse",
                hear="The states, each with its count.",
                check="window:Browse Stations",
            ),
            Step(
                title="Find your transmitter",
                body=(
                    "Open a state and you get its actual transmitters, named with "
                    "call sign, frequency and place -- KHB36 162.550 MHz Manassas. "
                    "Enter plays the best available internet re-stream of it."
                ),
                keys=("Right arrow", "Enter"),
                hear="The transmitter's call sign, frequency and place, then the audio.",
            ),
            Step(
                title="Search for it instead",
                body=(
                    "Weather radio is searchable by call sign, by SAME code, or by "
                    "County, ST -- which is usually faster than arrowing a state "
                    "with forty transmitters in it, and is how you find the one "
                    "that actually covers you."
                ),
                keys=("Ctrl+F",),
                hear="The matching transmitters.",
            ),
            Step(
                title="Keep it where you can reach it",
                body=(
                    "Favorite your transmitter and put it in a folder with your "
                    "local news station. In severe weather the thing you want is "
                    "one keystroke, not a directory."
                ),
                command="radio.toggle_playing_favorite",
                hear="Added, and the transmitter's name.",
                check="favorite-added",
            ),
            Step(
                title="Know where the rest of weather went",
                body=(
                    "Forecasts, alerts and background alert monitoring are Quill "
                    "Weather's job now -- a separate app in the same family, opened "
                    "from the QuillVille menu. What stays here is the radio part of "
                    "weather, which is this branch."
                ),
                hear="Nothing: this is the answer to where did the Weather menu go.",
            ),
        ),
        closing=(
            "One favorite, bundled offline, searchable by the three things people "
            "actually know: the call sign, the SAME code, or the county."
        ),
    ),
)
