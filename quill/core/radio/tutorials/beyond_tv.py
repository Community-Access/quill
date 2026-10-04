"""Track 5, second half: television, the ACB Media schedule, and weather radio.

Three sources that are unlike the rest. Television is video arriving through a
radio app's tree. ACB Media is the only source in Quill Radio with a published
*schedule*, so it is the only one where "what is on at eight" is a question
the app can answer. NOAA Weather Radio is a directory of transmitters rather
than of stations, and it is bundled, so it works with no connection at all.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="watch-television",
        title="Watch television",
        track="beyond",
        minutes=6,
        surfaces=("Browse Stations", "Video"),
        summary=(
            "Find a TV channel by country, category or ZIP code, play it with "
            "the same keys you already know, and add a programme guide if you "
            "would like one."
        ),
        steps=(
            Step(
                title="Find the branch",
                body=(
                    "Television is in Browse Stations, just above YouTube. It "
                    "comes from the iptv.org community list, with about 9,300 "
                    "channels you can play. Quill Radio leaves out adult "
                    "channels, closed ones, and ones that would not play when "
                    "you pressed Enter."
                ),
                keys=("Ctrl+B",),
                hear="Television, then By Country and By Category.",
                check="window:Browse Stations",
            ),
            Step(
                title="Open your own country",
                body=(
                    "Where a country has local channels, it opens into "
                    "Nationwide plus its states. Each state lists its own "
                    "channels and its cities' channels, with the city named on "
                    "the row. A country without local channels is just one "
                    "list, so you never open empty folders."
                ),
                keys=("Right arrow",),
                hear="The country, then Nationwide and the states.",
            ),
            Step(
                title="Search by place, not only by name",
                body=(
                    "Anywhere you can search, such as Find Stations, Search All "
                    "Sources or the Find box, you can find TV by channel name, "
                    "network, country, city, state, or a five-digit ZIP code. "
                    "Type 66044 and you get Kansas television."
                ),
                keys=("Ctrl+F",),
                hear="The matching channels.",
                note=(
                    "A ZIP code gets you close, which is handy for narrowing a "
                    "list. It cannot tell you what your antenna picks up. For "
                    "that, use the antennaweb link."
                ),
            ),
            Step(
                title="Play a channel",
                body=(
                    "Press Enter to play it. The video opens with captions, a "
                    "choice of audio tracks and all the usual player keys. Show "
                    "or hide the picture with Ctrl+Shift+V. The sound keeps "
                    "playing either way."
                ),
                keys=("Enter", "Ctrl+Shift+V"),
                hear="The channel playing, and the video window when it opens.",
            ),
            Step(
                title="Turn on captions and read them",
                body=(
                    "Ctrl+Shift+K turns captions on. They open in their own "
                    "window as text you can arrow through. Each new line is added "
                    "to the ones before, and the line being spoken now is "
                    "marked. The window stays quiet, so read it whenever you like."
                ),
                keys=("Ctrl+Shift+K",),
                hear="The captions window, then quiet until you go and read it.",
                note=(
                    "Turn off Follow Playback if you want the text to hold still "
                    "while you read back. Escape closes the window and turns "
                    "captions off."
                ),
            ),
            Step(
                title="Choose the audio track",
                body=(
                    "Ctrl+Shift+A lists the audio and described audio tracks. "
                    "Your own language comes first, then the original language, "
                    "then the rest in alphabetical order. So even a channel with "
                    "two dozen languages is easy to find your way around."
                ),
                keys=("Ctrl+Shift+A",),
                hear="The track list, your language first.",
            ),
            Step(
                title="Give yourself a programme guide",
                body=(
                    "If you have an XMLTV guide file, name it tv_guide.xml and "
                    "put it in your Quill Radio data folder. Every channel it "
                    "covers then gets a Now and Next line in its details. It "
                    "works offline, updates when you replace the file, and is "
                    "never downloaded from anywhere. Delete the file and the "
                    "lines go away."
                ),
                hear="Now, and Next, in the details of a channel the guide covers.",
                note=(
                    "There is no single TV guide for the whole world. Guides are "
                    "made by each country and provider, so you choose the one "
                    "that suits you."
                ),
            ),
            Step(
                title="Keep the channel list current",
                body=(
                    "The channel list updates itself once a week. It is the "
                    "biggest list in Quill Radio, about 28 MB. To get today's "
                    "list right now, use Update the channel list now, at the top "
                    "of the branch. It tells you what it is doing as it works."
                ),
                hear="Progress while it downloads, then how many channels it has.",
            ),
        ),
        closing=(
            "Television in Quill Radio works just like radio. You can make a "
            "channel a favorite, record it, book it, and use all the keys you "
            "already know. Enjoy the show."
        ),
    ),
    Tutorial(
        slug="acb-media-schedule",
        title="The ACB Media schedule",
        track="beyond",
        minutes=7,
        surfaces=("ACB Media Schedule", "Upcoming"),
        summary=(
            "Browse the ACB Media schedule across ten channels, find a "
            "programme, record it or get a reminder, and understand why there "
            "is sometimes nothing listed for today."
        ),
        steps=(
            Step(
                title="Open the schedule",
                body=(
                    "The schedule is one list, earliest first. Each row gives "
                    "the date, the start and end times, the programme and the "
                    "channel. It opens on the next programme still to come, so "
                    "you do not have to arrow past ones that are over."
                ),
                command="radio.acb_calendar",
                hear="ACB Media Schedule, then the next programme still to come.",
            ),
            Step(
                title="Read the line above the list",
                body=(
                    "This line always tells you how far ahead the schedule goes, "
                    "for example: 49 programmes published; the published "
                    "schedule runs 1 August to 15 August. It tells you plainly "
                    "when those dates have passed. ACB posts two weeks at a time, "
                    "so there are often days with nothing posted yet. Nothing is "
                    "wrong when that happens."
                ),
                keys=("Shift+Tab",),
                hear="The sentence, in a box you can arrow through word by word.",
            ),
            Step(
                title="Check whose clock the times are on",
                body=(
                    "ACB lists its times in US Central time, and Quill Radio "
                    "changes every one to your own time. When the two are "
                    "different, the line says so, so you know the times are "
                    "already right for you."
                ),
                hear="Times are shown in your time zone, and the time zone ACB uses.",
            ),
            Step(
                title="Find one programme",
                body=(
                    "There are three filters. They change what is listed, never "
                    "what is playing. Search finds rows that have all your "
                    "words, so blues tuesday finds the Tuesday blues show. Date "
                    "jumps to a day that has programmes. Channel shows just one "
                    "of the ten channels."
                ),
                keys=("Alt+S",),
                hear="How many programmes are left after the filter.",
            ),
            Step(
                title="Do something with a programme",
                body=(
                    "There are six things you can do, on the context menu and as "
                    "buttons in the same order: Play, Record, Remind Me, Add to "
                    "Queue, Copy Details and Show Notes. Enter also plays. If one "
                    "cannot be used right now, it is dimmed and says why."
                ),
                keys=("Shift+F10",),
                hear="The action confirmed, naming the programme.",
                note=(
                    "Play tunes in to the programme's channel, or stops it if "
                    "you are already listening to that channel. Live radio plays "
                    "one thing at a time, so Quill Radio tells you whether the "
                    "programme is on now or when it starts."
                ),
            ),
            Step(
                title="Book it, without doing the arithmetic",
                body=(
                    "Record opens Schedule Recording with the channel, date, "
                    "time and length already filled in. All you do is check "
                    "them and press OK. It then shows up in Recordings and in "
                    "Upcoming like any other booked recording."
                ),
                hear="Schedule Recording, already filled in with this programme's details.",
            ),
            Step(
                title="Ask what is on without opening anything",
                body=(
                    "What Is On Now tells you, in one sentence, what is on "
                    "across all ten channels. It answers straight away, from the "
                    "schedule already saved on your computer."
                ),
                command="radio.on_now",
                hear="What is on, across the channels, in one sentence.",
            ),
            Step(
                title="Re-read the schedule",
                body=(
                    "There are three ways to fetch the latest schedule. Use the "
                    "Refresh button, or Refresh the Schedule on the list's "
                    "context menu, which is there even when nothing is selected. "
                    "Or use Refresh the Schedule from anywhere in Quill Radio, "
                    "whether the schedule window is open or not."
                ),
                command="radio.refresh_calendar",
                hear=(
                    "Reading the ACB Media schedule again, then how far the schedule runs "
                    "and Pulled from ACB just now, with the time."
                ),
            ),
            Step(
                title="See everything you have planned",
                body=(
                    "Upcoming shows your reminders and your booked recordings "
                    "together, soonest first, and each row says which kind it "
                    "is. Snooze and Dismiss work on reminders only. To cancel a "
                    "booked recording, go to Schedule Recording, where you made "
                    "it."
                ),
                command="radio.upcoming",
                hear="Upcoming, then each item with its kind and time.",
            ),
        ),
        closing=(
            "The schedule is saved on your computer and freshened each time you "
            "open the window. Without an internet connection, it still opens and "
            "tells you how old it is. Happy listening."
        ),
    ),
    Tutorial(
        slug="weather-radio",
        title="NOAA Weather Radio",
        track="beyond",
        minutes=4,
        surfaces=("Browse Stations",),
        summary=(
            "Find your local NOAA weather radio transmitter by state, call sign "
            "or county. The whole list works even without an internet "
            "connection."
        ),
        steps=(
            Step(
                title="Open the branch",
                body=(
                    "Weather / NOAA, in Browse Stations, is the real NOAA "
                    "Weather Radio list, state by state, and each state says how "
                    "many transmitters it has. All 1,035 transmitters come built "
                    "into Quill Radio, so this branch works offline."
                ),
                keys=("Ctrl+B",),
                hear="The states, each with its count.",
                check="window:Browse Stations",
            ),
            Step(
                title="Find your transmitter",
                body=(
                    "Open a state to hear its transmitters, each with its call "
                    "sign, frequency and place, such as KHB36 162.550 MHz "
                    "Manassas. Press Enter to play the best internet stream of "
                    "it that is available."
                ),
                keys=("Right arrow", "Enter"),
                hear="The transmitter's call sign, frequency and place, then the sound.",
            ),
            Step(
                title="Search for it instead",
                body=(
                    "You can search weather radio by call sign, by SAME code, or "
                    "by County, ST, such as Fairfax, VA. That is often quicker "
                    "than arrowing through a state with forty transmitters, and "
                    "it finds the one that covers where you live."
                ),
                keys=("Ctrl+F",),
                hear="The matching transmitters.",
            ),
            Step(
                title="Keep it where you can reach it",
                body=(
                    "Add your transmitter to your favorites, and maybe put it in "
                    "a folder with your local news station. When the weather "
                    "turns bad, you want it one key away, not buried in a list."
                ),
                command="radio.toggle_playing_favorite",
                hear="Added, and the transmitter's name.",
                check="favorite-added",
            ),
            Step(
                title="Know where the rest of weather went",
                body=(
                    "Forecasts, alerts and watching for alerts in the background "
                    "now live in Quill Weather, a separate app in the same "
                    "family. Open it from the QuillVille menu. Quill Radio keeps "
                    "the radio part of weather, which is this branch."
                ),
                hear="Nothing. This answers the question: where did the Weather menu go?",
            ),
        ),
        closing=(
            "One favorite, working offline, that you can find by the things "
            "people actually know: the call sign, the SAME code, or the county. "
            "Stay safe out there."
        ),
    ),
)
