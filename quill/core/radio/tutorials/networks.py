"""Track 2: the broadcasters' own channels, and the open public radio directory.

One lesson, because both answer the same wish -- "I know who I want to hear,
take me straight to them" -- from two ends: Networks is a short list of
well-known broadcasters whose channels go straight to their own streams, and
IPRD is a long, open list of public stations from every country.

The idea, and the list of networks and their streams, come from BlindRadio by
serrebidev (MIT), docs/design/blindradio-ideas/networks-and-directories.md.
The lesson is written from Quill Radio's own user guide; no BlindRadio text
was copied.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="networks-and-iprd",
        title="Go straight to a broadcaster, or a public station",
        track="finding",
        minutes=6,
        surfaces=("Browse Stations", "Search Stations"),
        summary=(
            "Open a broadcaster's own channels in Networks, play one straight "
            "from its own stream, and find a public station anywhere in the "
            "world in the open IPRD directory."
        ),
        steps=(
            Step(
                title="Open Browse Stations",
                body=(
                    "Networks and IPRD are both branches of the one big tree in "
                    "Browse Stations, further down than the directories you met "
                    "first. Neither needs an account, and both play with the keys "
                    "you already know."
                ),
                command="radio.browse",
                hear="Browse Stations, and the row you were last on.",
                check="window:Browse Stations",
            ),
            Step(
                title="Find Networks and open it",
                body=(
                    "Arrow down the top-level branches to Networks and press Right "
                    "arrow. It groups well-known broadcasters by type: public "
                    "broadcasters, US public radio, news and talk, sports, music, "
                    "commercial and Christian radio, and syndicators."
                ),
                keys=("Down arrow", "Right arrow"),
                hear="Networks, then the first group, such as Public broadcasters.",
            ),
            Step(
                title="Hear how many channels a folder holds",
                body=(
                    "Open a group and arrow through it. Broadcasters such as the "
                    "BBC, WFMU or Global's Heart say how many channels they hold "
                    "before you open them, and open at once, because that list "
                    "comes with Quill Radio rather than from the internet."
                ),
                keys=("Right arrow", "Down arrow"),
                hear="A broadcaster's name, and how many channels it holds.",
                note=(
                    "A broadcaster without a count searches the station directory "
                    "for its name instead, so it takes a moment to fill."
                ),
            ),
            Step(
                title="Play a channel from its own stream",
                body=(
                    "Open a broadcaster and press Enter on a channel. It goes "
                    "straight to the broadcaster's own stream, with no directory "
                    "in between, and every one was checked to play before it was "
                    "added. Favorite it, record it or schedule it like any station."
                ),
                keys=("Right arrow", "Enter"),
                hear="The channel's name, then the station playing.",
                check="playing",
                note=("Seasonal channels are left out, so a network never goes quiet in January."),
            ),
            Step(
                title="Open the public radio directory",
                body=(
                    "Go back up to the top level and arrow down to IPRD (Public "
                    "Radio Directory), an open, community-kept list of about "
                    "24,000 stations. Open it for By Country and By Genre. The "
                    "first folder you open fetches the whole list, so wait a moment."
                ),
                keys=("Left arrow", "Down arrow", "Right arrow"),
                hear="IPRD (Public Radio Directory), then By Country and By Genre.",
            ),
            Step(
                title="Move through a long list a hundred at a time",
                body=(
                    "Open By Country, then a country. A long list shows a hundred "
                    "stations at a time, and its last row, More, says how many "
                    "there are in all. Press Enter on More to open the next "
                    "hundred. The list is kept for a day, so the rest is quick."
                ),
                keys=("End", "Enter"),
                hear="More, and how many it is showing, such as showing 100 of 4,012.",
            ),
            Step(
                title="Find them from Search Stations too",
                body=(
                    "Search All Sources, at the top of the tree, and Search "
                    "Stations both ask IPRD and Networks along with everything "
                    "else. Networks asks nobody on the internet: it searches the "
                    "channels that came with Quill Radio, so a search for WFMU "
                    "finds its side channels at once."
                ),
                keys=("Home", "Enter"),
                hear="Search All Sources: What are you looking for?",
                note=(
                    "Search Sources, on the Station menu, turns either of them "
                    "off if you would rather not see them in results."
                ),
            ),
        ),
        closing=(
            "Networks is the short way to a broadcaster you already know, and "
            "IPRD is the long way round the world's public radio. The list of "
            "networks and their streams comes from BlindRadio by serrebidev."
        ),
        then=("addresses-of-your-own",),
    ),
)
