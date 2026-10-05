"""Track 2, second half: stations no directory lists, and what backs them up.

Three lessons about the awkward middle of internet radio. The station you
actually want is often the one nobody indexed -- a church, a school, a reading
service, a community Icecast box -- so the first lesson is about addresses of
your own. The second is about the copy of the directories that lives on your
disk, which is why the app works at all on a train. The third is the one
everybody eventually needs: a station that will not play, and what Quill Radio
does about it before you have to.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="addresses-of-your-own",
        title="Add a station nobody lists",
        track="finding",
        minutes=8,
        surfaces=("Quill Radio", "Find Streams from a Website", "Browse Stations"),
        summary=(
            "Four ways to add a station that is not in any directory: paste its "
            "stream address, scan its website, add the whole server it lives "
            "on, or open a playlist file someone sent you. Before you start, try "
            "typing its web address into a search box. That is quicker, and it "
            "has its own lesson."
        ),
        steps=(
            Step(
                title="Paste a stream address",
                body=(
                    "Add Custom Station asks for a name you choose and a stream "
                    "address. There is a Test button so you can hear it before "
                    "you save. Use this when someone has given you the actual "
                    "audio address rather than a web page."
                ),
                command="radio.add_custom_station",
                hear="Add Custom Station, then the Station name box. Stream URL is next.",
                note=(
                    "If you paste a Live365 station page or player link, Quill "
                    "Radio swaps in the real stream for you and tells you so. A "
                    "YouTube link is kept as the page address, so a recording you "
                    "schedule today still works next week."
                ),
            ),
            Step(
                title="Understand why the website is not the station",
                body=(
                    "A station's home page is not the same as its audio, so "
                    "saving the home page as a stream will not play. The good "
                    "news is that you do not have to hunt for the audio yourself. "
                    "Type the web address into any search box and Quill Radio "
                    "reads the page and finds it for you. Now and then a page "
                    "hides its stream too well, and the next step is for those."
                ),
                hear="Nothing yet. This step just saves you a lot of hunting.",
                note=(
                    "Typing an address into a search box has a lesson of its "
                    "own, Find a station by its web address. The rest of this "
                    "lesson is for when that does not find it."
                ),
            ),
            Step(
                title="Scan a station's page for its stream",
                body=(
                    "Find Streams from a Website reads the page you give it and "
                    "lists the streams it found. Press Test on one to hear it, so "
                    "you can tell which is right. It follows a Listen Live link "
                    "one step, and it recognises Triton, StreamTheWorld, "
                    "SecureNet, iHeart and TuneIn players by name."
                ),
                command="radio.find_streams",
                hear=(
                    "Find Streams from a Website, and the Website address box. After Scan, "
                    "the streams it found, or a plain sentence saying the page had none."
                ),
                note=(
                    "It cannot run a web page's scripts. If a page finds "
                    "nothing, look for a Listen Live link, or search the "
                    "directories. They often have the stream already."
                ),
            ),
            Step(
                title="Add the whole server instead of one stream",
                body=(
                    "My Servers, in Browse Stations, is for whole stream servers. "
                    "Choose Add a Server and paste the address of an Icecast or "
                    "SHOUTcast server, such as one run by a community station, a "
                    "school or a reading service. Every stream on that server "
                    "appears, each one saying what it is playing right now."
                ),
                hear=(
                    "Checking, the address. Then Added, the address, and how many stations it has."
                ),
                note=(
                    "If the server sends back nothing, it is not saved. That "
                    "nearly always means the address is a little wrong, often a "
                    "missing port number, so check it and try again."
                ),
            ),
            Step(
                title="Import a playlist file",
                body=(
                    "Import Stations from Playlist, on the Station menu, opens a "
                    "playlist file of the kind stations and friends share: M3U, "
                    "M3U8, PLS, XSPF or ASX. Choose the file, then choose where "
                    "the stations go. That can be a folder you already have, or a "
                    "new one such as News/Local, which Quill Radio makes for you. "
                    "If you already have some of them, it asks whether to skip "
                    "those."
                ),
                keys=("Ctrl+I",),
                hear="Imported, how many stations, and the folder they went into.",
            ),
            Step(
                title="Export the other way",
                body=(
                    "Export Favorites to Playlist saves every favorite that has a "
                    "stream address into one M3U file, which almost any other "
                    "player can open. Importing that file again brings the "
                    "stations back, so it is also a simple way to take your list "
                    "to another computer."
                ),
                keys=("Ctrl+Shift+X",),
                hear="Exported, how many stations, and the file's name.",
                note=(
                    "An M3U file has no folders, so your folders do not come "
                    "along. To keep everything, folders included, use Back Up "
                    "Stations and Settings instead."
                ),
            ),
        ),
        closing=(
            "With these four, you can bring almost any station into Quill Radio, "
            "even one that only exists as a link in an email. Nicely done."
        ),
        then=("catalog-and-offline", "when-it-wont-play"),
    ),
    Tutorial(
        slug="catalog-and-offline",
        title="The catalog on your own disk",
        track="finding",
        minutes=5,
        surfaces=("Quill Radio", "Station Catalog Status"),
        summary=(
            "Find out why browsing is instant and even works with no internet. "
            "You will check how up to date your station list is, see what is "
            "not stored and why, and update it whenever you like."
        ),
        steps=(
            Step(
                title="Notice what is answering",
                body=(
                    "Open By Country, By Language, By Genre or By Quality. Notice "
                    "how they open instantly. That is because Quill Radio comes "
                    "with a big list of working stations, more than 62,000 from "
                    "240 countries, and keeps it on your computer."
                ),
                keys=("Ctrl+B",),
                hear="The branch opening with no pause at all.",
            ),
            Step(
                title="Ask what is stored and what is not",
                body=(
                    "Station Catalog Status tells you everything in one list. "
                    "You hear each stored source with how many stations it has "
                    "and how fresh it is. Sources that cannot be stored say why, "
                    "for example: iHeart: live only; its terms do not allow "
                    "storing its listings."
                ),
                command="radio.catalog_status",
                keys=("Ctrl+Alt+Shift+S",),
                hear="Each source with its station count and when it was last updated.",
            ),
            Step(
                title="Update it on demand",
                body=(
                    "Update Station Catalog freshens the list right now and tells "
                    "you what changed, for example: Station catalog updated: 174 "
                    "new stations, 431 updated. It also updates itself quietly "
                    "soon after you open Quill Radio, and then on a schedule you "
                    "choose, every 24 hours unless you change it."
                ),
                command="radio.update_catalog",
                keys=("Ctrl+Alt+Shift+G",),
                hear="Station catalog updated, and how many changed.",
            ),
            Step(
                title="Know what an outage costs you",
                body=(
                    "If a directory goes down for a while, you lose nothing. Your "
                    "list just stays a little less fresh until it is back. A "
                    "station that disappears from a directory is hidden straight "
                    "away, but only forgotten after two weeks, in case it comes "
                    "back."
                ),
                hear="Nothing. This is something that just works in the background.",
            ),
            Step(
                title="Try it with the internet off",
                body=(
                    "Disconnect from the internet and open Browse Stations. Quill "
                    "Radio tells you once that you are offline and browsing from "
                    "your catalog, and then carries on as normal. Even on a "
                    "computer that has never been online, you can still browse "
                    "every station."
                ),
                hear=(
                    "You are offline. Browsing from your catalog, updated, and how long "
                    "ago. Then the list working as normal."
                ),
            ),
            Step(
                title="Know that none of it touches your stations",
                body=(
                    "The catalog is a copy of public station directories. Your "
                    "favorites, your own stations, your servers and your YouTube "
                    "channels are kept separately, and nothing you do to the "
                    "catalog touches them. Even Rebuild From Shipped Snapshot, a "
                    "button in Station Catalog Status, leaves your stations "
                    "exactly as they were."
                ),
                hear=(
                    "Catalog rebuilt from the shipped snapshot, and nothing about your favorites."
                ),
                note=(
                    "If you would rather not keep a catalog at all, turn off Keep "
                    "a local station catalog on this computer in Preferences. "
                    "Then nothing is stored, and Quill Radio makes no background "
                    "requests for it."
                ),
            ),
        ),
        closing=(
            "Your catalog is why Quill Radio still works on a train, and why every "
            "folder can tell you its size before you open it."
        ),
    ),
    Tutorial(
        slug="when-it-wont-play",
        title="When a station will not play",
        track="finding",
        minutes=6,
        surfaces=("Browse Stations", "Search Stations", "Audio Health"),
        summary=(
            "Stations sometimes stop working. You will learn what the status "
            "line is telling you, let Quill Radio try to fix a broken address, "
            "check that your computer can play sound, and report a station that "
            "is really gone."
        ),
        steps=(
            Step(
                title="Tell buffering and reconnecting apart",
                body=(
                    "The Now playing line at the top of the main window tells you "
                    "what is happening. Buffering means the station is still "
                    "there and the sound paused for a moment. It usually comes "
                    "back by itself within a few seconds. Reconnecting means the "
                    "connection dropped and Quill Radio is trying again, three "
                    "times, after two, five and fifteen seconds. You hear each "
                    "try. If it still fails, you hear why."
                ),
                hear=(
                    "On the Now playing line: Radio: buffering, or connecting, or playing. "
                    "Spoken: Reconnecting to the station, Attempt 2 of 3. Or Could not play, "
                    "and why."
                ),
            ),
            Step(
                title="Let it repair the address",
                body=(
                    "Sometimes a station's address in a directory has stopped "
                    "working. Quill Radio does not just give up. It tries a few "
                    "things in turn: it looks the player up again, gets a fresh "
                    "address from the directory, and, if the setting is on, looks "
                    "on the station's own website for its Listen Live player. If "
                    "it finds one clear stream, it plays it and remembers it for "
                    "that favorite."
                ),
                hear=(
                    "Either the station starting after a pause, or how many streams were "
                    "found for you to choose from."
                ),
                note=(
                    "The website step is the setting Recover failed streams from "
                    "the station's website, in Preferences. It is on unless you "
                    "turn it off, and off in Safe Mode. It only tries once per "
                    "station each time you run Quill Radio."
                ),
            ),
            Step(
                title="Check whether the problem is this installation",
                body=(
                    "Audio Health answers one question: is this going to work? "
                    "It lists which sound player is in use, whether mpv and "
                    "FFmpeg are there and what you miss without them, where the "
                    "sound is going, and whether a recording could be saved "
                    "right now. It does not play anything or open any device, so "
                    "it is safe to open even while you are recording."
                ),
                keys=("Ctrl+Alt+Shift+M",),
                hear="Each check with its own plain answer.",
            ),
            Step(
                title="Rule out the boring causes",
                body=(
                    "If Quill Radio says playing but you hear nothing, it is "
                    "nearly always one of three things: mute, the volume saved "
                    "for this station, or the Windows volume mixer setting for "
                    "Quill Radio. Check them in that order. It takes ten seconds "
                    "and usually solves it."
                ),
                keys=("Ctrl+M", "Ctrl+Up"),
                hear="Muted, or the volume level. Then the new volume as you change it.",
                note=(
                    "Ctrl+M and Ctrl+Up are the main window's keys. Ctrl+Shift+O "
                    "also mutes, there and in every other window."
                ),
            ),
            Step(
                title="Report a station that is genuinely dead",
                body=(
                    "Report Bad Station, on the station's own menu in Browse or "
                    "Search, opens Get Help from Support with the station's name, "
                    "stream, source and country already filled in. Only the "
                    "station's details are included, never your name, your email "
                    "or anything about your files."
                ),
                keys=("Shift+F10",),
                hear="A report form with the station's details already in it.",
                note=(
                    "Directories hide stations they think are broken. So if a "
                    "station works for the directory but not for you, only you "
                    "can let us know."
                ),
            ),
            Step(
                title="Look up what you missed",
                body=(
                    "If a problem was spoken while you were in another window, "
                    "Recent Problems still has it, with the reason and the time. "
                    "Retry tries the selected one again, and Copy All copies the "
                    "list as text for a message to support."
                ),
                keys=("Ctrl+Alt+Shift+P",),
                hear="The problems, newest first, each with its reason.",
            ),
        ),
        closing=(
            "Most of the time, a station that will not play has simply moved, "
            "and nothing is wrong with Quill Radio. The repair steps catch most "
            "of these before you even notice, and a report catches the rest."
        ),
    ),
)
