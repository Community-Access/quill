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
            "Four routes to a station that is not in any directory: paste its "
            "stream, scan its website, add the whole server it lives on, or "
            "import a playlist file somebody sent you. Try typing its web "
            "address into a search box first -- that is quicker, and it has its "
            "own lesson."
        ),
        steps=(
            Step(
                title="Paste a stream address",
                body=(
                    "Add Custom Station takes a name of your choosing and any "
                    "stream address, with a Test button to hear it before you "
                    "save. This is the direct route when somebody has given you "
                    "the actual audio address rather than a web page."
                ),
                command="radio.add_custom_station",
                hear="Add Custom Station, then the Station name field; Stream URL is next.",
                note=(
                    "A Live365 station page or player link is rewritten to the "
                    "real stream for you, and the dialog says it did. A YouTube "
                    "link is saved as the page address, never a stream address, "
                    "so a recording you schedule today still works next week."
                ),
            ),
            Step(
                title="Understand why the website is not the station",
                body=(
                    "A station's home page is not its audio feed, and saving one "
                    "as a stream address will not play. You no longer have to "
                    "find the feed yourself, though: type the web address into "
                    "any search box and Quill Radio reads the page and hands back "
                    "the feed. What it cannot do is run JavaScript, so a player "
                    "that builds its address in code writes it nowhere -- which "
                    "is what the next step is for."
                ),
                hear="Nothing: this step is the fact that saves the next twenty minutes.",
                note=(
                    "Typing an address into a search box is the short route and "
                    "has a lesson of its own, Find a station by its web address. "
                    "The rest of this lesson is what to do when that is not "
                    "enough."
                ),
            ),
            Step(
                title="Scan a station's page for its stream",
                body=(
                    "Find Streams from a Website reads the one page you give it "
                    "and offers what it found, with a Test button that plays a "
                    "candidate so you can hear which is right. It follows a Listen "
                    "Live link one level, and recognises Triton, StreamTheWorld, "
                    "SecureNet, iHeart and TuneIn players by name rather than "
                    "guessing."
                ),
                command="radio.find_streams",
                hear=(
                    "Find Streams from a Website, and the Website address field; after Scan, "
                    "the candidates found, or a plain statement that the page had none."
                ),
                note=(
                    "It deliberately never runs JavaScript. If a page finds "
                    "nothing, look for a Listen Live link, or search the "
                    "directories -- they usually already have the feed."
                ),
            ),
            Step(
                title="Add the whole server instead of one stream",
                body=(
                    "My Servers, in the browse tree, is the branch no directory "
                    "can give you. Choose Add a Server and paste the address of an "
                    "Icecast or SHOUTcast box -- a community station, a school, a "
                    "reading service -- and every mount on it appears, each with "
                    "what is playing on it right now."
                ),
                hear=(
                    "Checking, the address; then Added, the address, and how many stations it has."
                ),
                note=(
                    "An address that answers with nothing is not saved. A branch "
                    "that is empty the day you add it is nearly always a wrong "
                    "address -- usually a missing port number -- and saving it "
                    "would only hide that from you."
                ),
            ),
            Step(
                title="Import a playlist file",
                body=(
                    "Import Stations from Playlist, on the Station menu, reads an "
                    "M3U, M3U8, PLS, XSPF or ASX file -- whichever kind a station "
                    "or a friend hands out. Choose the file, then choose where the "
                    "stations go -- an existing folder, or a new path like "
                    "News/Local, created for you. If some are already yours, it "
                    "asks whether to skip them."
                ),
                keys=("Ctrl+I",),
                hear="Imported, how many stations, and the folder they went into.",
            ),
            Step(
                title="Export the other way",
                body=(
                    "Export Favorites to Playlist writes every favorite with a "
                    "stream address to one M3U file, which almost any other "
                    "player can open. Importing that file again brings the "
                    "stations back, so it doubles as a simple way to carry your "
                    "list to another computer."
                ),
                keys=("Ctrl+Shift+X",),
                hear="Exported, how many stations, and the file's name.",
                note=(
                    "M3U has no notion of folders, so your folder structure is not "
                    "carried across -- exactly as importing one discards it. Back "
                    "Up Stations and Settings keeps everything, folders included."
                ),
            ),
        ),
        closing=(
            "Between these four you can get almost any station into Quill Radio, "
            "including the ones that exist only as a link somebody emailed you."
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
            "Understand why browsing is instant and works with no internet at "
            "all, how fresh your copy is, what is deliberately not in it, and how "
            "to update or rebuild it."
        ),
        steps=(
            Step(
                title="Notice what is answering",
                body=(
                    "Open By Country, By Language, By Genre or By Quality and time "
                    "it. They answer from your own disk in under a millisecond, "
                    "because Quill Radio ships the whole working-station directory "
                    "inside the app -- more than 62,000 stations across 240 "
                    "countries -- and keeps it in a catalog on this computer."
                ),
                keys=("Ctrl+B",),
                hear="The branch opening with no pause at all.",
            ),
            Step(
                title="Ask what is stored and what is not",
                body=(
                    "Station Catalog Status is the complete answer in one list: "
                    "the stored sources with their counts and freshness, and the "
                    "live-only ones with the honest reason -- iHeart: live only; "
                    "its terms do not allow storing its listings."
                ),
                command="radio.catalog_status",
                keys=("Ctrl+Alt+Shift+S",),
                hear="Each source with its station count and when it was last updated.",
            ),
            Step(
                title="Update it on demand",
                body=(
                    "Update Station Catalog refreshes it now and always answers "
                    "out loud -- Station catalog updated: 174 new stations, 431 "
                    "updated. It also updates itself quietly shortly after launch "
                    "and on a schedule you set, every 24 hours by default."
                ),
                command="radio.update_catalog",
                keys=("Ctrl+Alt+Shift+G",),
                hear="Station catalog updated, and what changed, counted.",
            ),
            Step(
                title="Know what an outage costs you",
                body=(
                    "A directory that is down costs you its freshness, never your "
                    "stations. A source that suddenly answers with nothing is "
                    "treated as an outage rather than as the truth, and a station "
                    "that disappears is hidden at once but only forgotten after "
                    "two weeks."
                ),
                hear="Nothing now: this is what you will not notice going wrong.",
            ),
            Step(
                title="Try it with the internet off",
                body=(
                    "Disconnect and open the tree. Quill Radio says it once -- you "
                    "are offline, browsing from your catalog -- and then keeps "
                    "working. First launch on a machine with no internet at all is "
                    "still a complete radio."
                ),
                hear=(
                    "You are offline. Browsing from your catalog, updated, and how long ago; "
                    "then the tree behaving normally."
                ),
            ),
            Step(
                title="Know that none of it touches your stations",
                body=(
                    "The catalog is a copy of public directories. Your favorites, "
                    "custom stations, servers and YouTube channels live in their "
                    "own files, and no catalog operation reads or writes them. "
                    "Rebuild From Shipped Snapshot, a button in Station Catalog "
                    "Status, leaves your stations byte-for-byte untouched."
                ),
                hear=(
                    "Catalog rebuilt from the shipped snapshot -- and nothing about your favorites."
                ),
                note=(
                    "Turning off Keep a local station catalog on this computer, "
                    "in Preferences, restores "
                    "live-only browsing: nothing stored, and no background "
                    "requests of any kind."
                ),
            ),
        ),
        closing=(
            "The catalog is why this app is usable on a train. It is also why "
            "every folder can tell you its size before you open it."
        ),
    ),
    Tutorial(
        slug="when-it-wont-play",
        title="When a station will not play",
        track="finding",
        minutes=6,
        surfaces=("Browse Stations", "Search Stations", "Audio Health"),
        summary=(
            "Read what the status line is actually telling you, let Quill Radio "
            "try to repair a dead address, check whether this installation can "
            "play at all, and report a station that is genuinely gone."
        ),
        steps=(
            Step(
                title="Tell buffering and reconnecting apart",
                body=(
                    "The Now playing line at the top of the main window says "
                    "which. Buffering means the stream is still there and the "
                    "audio ran out for a moment; it usually comes back on its own "
                    "within a few seconds. Reconnecting means the connection went "
                    "away and is being rebuilt -- three attempts, at two, five and "
                    "fifteen seconds, each spoken. A failure is spoken too, with "
                    "its reason."
                ),
                hear=(
                    "On the Now playing line: Radio: buffering, or connecting, or playing. "
                    "Spoken: Reconnecting to the station, Attempt 2 of 3 -- or Could not play, "
                    "and why."
                ),
            ),
            Step(
                title="Let it repair the address",
                body=(
                    "Some stations are listed with an address that has since died. "
                    "Instead of failing, Quill Radio works down a ladder: it "
                    "re-resolves a moved player address, refreshes the address "
                    "from the directory, and -- with the setting on -- scans the "
                    "station's own website for its Listen Live player. One clear "
                    "stream is played and remembered for that favorite."
                ),
                hear=(
                    "Either the station starting after a pause, or a count of streams found for "
                    "you to choose from."
                ),
                note=(
                    "The website step is Recover failed streams from the station's "
                    "website in Preferences, on by default and off in Safe Mode. "
                    "It only tries once per station per session."
                ),
            ),
            Step(
                title="Check whether the problem is this installation",
                body=(
                    "Audio Health answers is this going to work in one list: which "
                    "engine is actually in use, whether mpv and FFmpeg are present "
                    "and what their absence costs, where the audio is going, and "
                    "whether a recording could be written right now. It tests "
                    "nothing -- no sound played, no device opened -- so it is safe "
                    "to open mid-recording."
                ),
                keys=("Ctrl+Alt+Shift+M",),
                hear="Each check with its own plain-language verdict.",
            ),
            Step(
                title="Rule out the boring causes",
                body=(
                    "No sound while the app says playing is nearly always one of "
                    "three things: mute, this station's own remembered volume, or "
                    "the Windows volume mixer entry for Quill Radio. Check them in "
                    "that order -- it takes ten seconds and saves a bug report."
                ),
                keys=("Ctrl+M", "Ctrl+Up"),
                hear="Muted, or the volume level; then the volume level as you change it.",
                note=(
                    "Ctrl+M and Ctrl+Up are the main window's keys; Mute is "
                    "Ctrl+Shift+O there too, and in every other window."
                ),
            ),
            Step(
                title="Report a station that is genuinely dead",
                body=(
                    "Report Bad Station, on the station's own menu in Browse or "
                    "Search, opens Get Help from Support already filled in with the "
                    "station's name, stream, source and country. What it fills in "
                    "is the station's details only -- never your name, your email "
                    "or any file path."
                ),
                keys=("Shift+F10",),
                hear="A report form with the station's details already in it.",
                note=(
                    "Directories hide stations their own checker believes are "
                    "dead, so a station that plays for the directory but not for "
                    "you is one only you can flag."
                ),
            ),
            Step(
                title="Look up what you missed",
                body=(
                    "If the failure was spoken while you were in another window, "
                    "Recent Problems still has it, with the reason and the time. "
                    "Retry tries the highlighted row again, and Copy All takes the "
                    "list as text for a report."
                ),
                keys=("Ctrl+Alt+Shift+P",),
                hear="The failures, newest first, each with its reason.",
            ),
        ),
        closing=(
            "Most failures here are streams moving, not the app breaking. The "
            "ladder above catches most of them before you notice; the report "
            "catches the ones nobody else can see."
        ),
    ),
)
