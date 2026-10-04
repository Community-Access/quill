"""Track 2, first half: the two ways to find a station you do not have yet.

Wandering and searching are different jobs and Quill Radio keeps them in
different windows on purpose, so these are two lessons rather than one. The
tree is for "show me what there is"; Find Stations is for "I know roughly what
I want". The third lesson ties them together -- a search across every directory
at once, run from inside the tree -- and the fourth is the one for when every
directory is the wrong place to look, because the station is in none of them
and only its own website has it.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="wander-the-tree",
        title="Wander the browse tree",
        track="finding",
        minutes=8,
        surfaces=("Browse Stations",),
        summary=(
            "Get comfortable exploring Browse Stations. You will open folders, "
            "learn what a row tells you before you play it, search inside one "
            "folder, and tidy away the sources you do not want."
        ),
        steps=(
            Step(
                title="Open the tree and notice where it put you",
                body=(
                    "Open Browse Stations. It remembers where you were last time. "
                    "If you have played something from here before, you land "
                    "right back on that branch instead of at the top, so you do "
                    "not have to arrow all the way there again."
                ),
                keys=("Ctrl+B",),
                hear="Browse Stations, and the row you were last on.",
                check="window:Browse Stations",
            ),
            Step(
                title="Open a folder and let it tell you its size",
                body=(
                    "Open By Country and arrow through it. Each country says how "
                    "many stations it has before you open it: France, then a "
                    "number in brackets. The numbers come straight from your own "
                    "computer, so they appear instantly."
                ),
                keys=("Right arrow", "Down arrow"),
                hear="How many items By Country holds, then each country with its station count.",
            ),
            Step(
                title="Read a row before you play it",
                body=(
                    "Arrow onto a station and listen to the whole row. If a "
                    "station probably will not play, the row says may not be "
                    "playable. Some stations, such as ones from TuneIn or "
                    "YouTube, need looking up first, and their rows say resolves "
                    "when you play it. Then you know why there is a short pause "
                    "before the sound starts."
                ),
                keys=("Down arrow",),
                hear="The station name, then any note the row carries.",
                note=(
                    "Only stations from Radio Browser come with a may not be "
                    "playable warning. Rows from other sources have no warning "
                    "either way, which does not mean anything is wrong."
                ),
            ),
            Step(
                title="Ask the row for its details",
                body=(
                    "When the Station Details pane is on, each row you arrow to "
                    "fills a box with its source, stream, format and country. "
                    "Press Tab from the list to read it, arrow through it, and "
                    "copy from it. If you would rather not Tab past it, turn it "
                    "off with Show Station Details on the main window's View "
                    "menu. Every station list follows your choice."
                ),
                keys=("Tab",),
                hear="The details box, read as ordinary text.",
                note="Show Station Details is Ctrl+D in the main window.",
            ),
            Step(
                title="Search inside the folder you are standing in",
                body=(
                    "Find in this folder searches only the rows inside the "
                    "folder you are on. It looks at each row's description as "
                    "well as its name. On a podcast, that means it searches the "
                    "episodes and their show notes. Clear the box to see the "
                    "whole folder again."
                ),
                keys=("Ctrl+F",),
                hear=("Find in this folder. Then, when you press Enter, how many rows matched."),
            ),
            Step(
                title="Open a row's own menu",
                body=(
                    "Press Shift+F10, or the Applications key, on any row. You "
                    "get everything else you can do with it: Play/Stop, add or "
                    "remove the favorite, copy the stream link, open the website, "
                    "Report Bad Station, Refresh, and Set a Reminder. Whenever "
                    "you wonder what else you can do, try this menu."
                ),
                keys=("Shift+F10",),
                hear="A context menu, read from the top.",
                note=(
                    "Quick Actions, on the Station menu, lets you choose the "
                    "order of this menu. The lesson called Decide what a row "
                    "says, and what its menu offers first shows you how."
                ),
            ),
            Step(
                title="Set a source's own options",
                body=(
                    "A few sources have a question of their own. Press Shift+F10 "
                    "on the source and choose Source Options if you see it. Radio "
                    "Paradise asks which sound quality you want. SHOUTcast asks "
                    "whether to show every station or only ones people are "
                    "listening to right now. Quill Radio reads your answer back "
                    "and reloads the branch straight away."
                ),
                keys=("Shift+F10",),
                hear="The option you chose, read back, then the branch reloading.",
            ),
            Step(
                title="Hide a source you will never use",
                body=(
                    "Press Shift+F10 on a top-level branch and choose Hide This "
                    "Source. Reset Sources to Default is right beside it if you "
                    "change your mind. A hidden source leaves the list completely "
                    "and is never contacted, so the list is shorter and quicker "
                    "to get around."
                ),
                keys=("Shift+F10",),
                hear="The source's name, hidden, and how to bring it back.",
                note=(
                    "Choose Browse Sources, on the main window's Station menu, "
                    "does the same thing as one checklist of every source "
                    "(Ctrl+Alt+Shift+O)."
                ),
            ),
        ),
        closing=(
            "Browse Stations is a lovely place to wander, and you never need an "
            "account or a sign-up to use any of it. When you know what you are "
            "after, the next lesson gets you there faster."
        ),
        then=("search-every-directory", "find-stations-by-field"),
    ),
    Tutorial(
        slug="search-every-directory",
        title="Search every directory at once",
        track="finding",
        minutes=5,
        surfaces=("Browse Stations",),
        summary=(
            "Run one search across every source you have turned on. You will "
            "learn how to read the answer, and what it means when a source does "
            "not reply in time."
        ),
        steps=(
            Step(
                title="Start from the top of the tree",
                body=(
                    "Search All Sources is the very first row in Browse "
                    "Stations. It asks every source you have turned on, all at "
                    "once. The answer appears as a Search Results branch at the "
                    "top of the same list, right where you are."
                ),
                keys=("Home", "Enter"),
                hear=(
                    "Search All Sources: What are you looking for? Every source is searched "
                    "at once."
                ),
            ),
            Step(
                title="Type something specific enough to be interesting",
                body=(
                    "Try a style of music plus a place, such as jazz new "
                    "orleans, rather than a single word. The whole search takes "
                    "no more than eight seconds, and a more specific search gives "
                    "you a list that is easier to use."
                ),
                keys=("Enter",),
                hear=(
                    "Searching every source, and your words. After about four seconds, "
                    "Still searching. Then the results."
                ),
            ),
            Step(
                title="Read what did not answer",
                body=(
                    "If a source did not reply in time, the results tell you, "
                    "for example: Internet Archive did not answer within 8 "
                    "seconds. That way you know a short list might not be the "
                    "whole story. Searching again usually brings it in."
                ),
                keys=("Down arrow",),
                hear="The results, and the name of any source that did not answer.",
            ),
            Step(
                title="Search again from the Find box",
                body=(
                    "When you are on Search All Sources or anywhere in its "
                    "results, press Ctrl+F, type, and press Enter. That searches "
                    "every source again for what you typed, with no extra "
                    "questions. Anywhere else in the list, the same box searches "
                    "just the branch you are in. The one exception is a web "
                    "address, which is looked up wherever you are."
                ),
                keys=("Ctrl+F", "Enter"),
                hear="The new results replacing the old ones.",
                note=(
                    "Quill Radio remembers your search answers for ten minutes. "
                    "If you search for the same thing again, you get the full "
                    "answer at once while a fresh search runs in the background."
                ),
            ),
            Step(
                title="Keep one, then close the results",
                body=(
                    "Add anything you like to your favorites from the row's own "
                    "menu. Then press Delete on the Search Results branch to "
                    "close it. It does not ask you to confirm, because nothing is "
                    "lost. Run the same search again and the answer comes "
                    "straight back."
                ),
                keys=("Delete",),
                hear="Search results closed, and you are back on Search All Sources.",
            ),
        ),
        closing=(
            "One search, every directory, one tidy list of results. If you would "
            "rather search by name, country and tag together, the next lesson "
            "covers that window. And if a station you know exists never turns "
            "up, the lesson after that is the one for you."
        ),
        then=("find-stations-by-field", "find-a-station-by-its-address"),
    ),
    Tutorial(
        slug="find-a-station-by-its-address",
        title="Find a station by its web address",
        track="finding",
        minutes=4,
        surfaces=("Browse Stations", "Search Stations", "Internet Radio"),
        summary=(
            "Some stations are not in any directory. Here you will type the "
            "station's own web address into a search box and let Quill Radio "
            "find the stream on its page. It is the answer to: I know this "
            "station exists, so why can I not find it?"
        ),
        steps=(
            Step(
                title="Know when to reach for this",
                body=(
                    "No directory has every station. If a station is not in any "
                    "of them, searching for its name will not find it, however "
                    "you spell it. So if you know a station is real and the "
                    "search keeps coming up empty, look for its website instead."
                ),
                hear="Nothing yet. This step just saves you trying a name twenty ways.",
            ),
            Step(
                title="Type the address instead of the name",
                body=(
                    "In any search box, type the station's home page the way you "
                    "would in a web browser, such as oj991.com, and press Enter. "
                    "Quill Radio sees that it is a web address, opens that one "
                    "page, finds the stream the station's own player uses, and "
                    "gives it to you as a row. You do not need to type https://."
                ),
                keys=("Ctrl+B",),
                hear=(
                    "One stream found on the website, and a row with the station's name "
                    "rather than a web address."
                ),
                note=(
                    "This works in all three places you can search: the Find box "
                    "in Browse Stations, Search All Sources, and the Search "
                    "Stations window. It does not matter where you are when you "
                    "type it."
                ),
            ),
            Step(
                title="Play it, and keep it",
                body=(
                    "What you get is an ordinary station row. Press Enter to play "
                    "it, and add it to your favorites from the row's own menu. "
                    "Same keys, same menu, just like a station you found by "
                    "browsing."
                ),
                keys=("Enter", "Shift+F10"),
                hear="Playing, and the station's name. Then Added, the name, to Favorites.",
                check="favorite-added",
            ),
            Step(
                title="Know what it is not",
                body=(
                    "This reads one web page. It is not a web search, and typing "
                    "a name still searches the directories as usual. If the page "
                    "has no stream, you hear that nothing was found rather than a "
                    "guess. It cannot run the page's scripts, but it does "
                    "recognise the common station players by name, such as "
                    "Triton, StreamTheWorld, SecureNet, iHeart and TuneIn."
                ),
                hear="Nothing found on that website, when the page really has no stream.",
                note=(
                    "If the home page finds nothing, try the page behind the "
                    "station's Listen Live link. That is usually where the player "
                    "is."
                ),
            ),
        ),
        closing=(
            "One address, one row, and a station you could not reach five "
            "minutes ago. If a station has no player page either, the next "
            "lesson shows you four more ways in: a stream address, a whole "
            "server, or a playlist file someone sent you."
        ),
        then=("addresses-of-your-own",),
    ),
    Tutorial(
        slug="find-stations-by-field",
        title="Find stations by name, tag and country",
        track="finding",
        minutes=6,
        surfaces=("Search Stations", "Internet Radio"),
        summary=(
            "Use the search window with separate boxes for name, tag and "
            "country. You will also bring back an earlier search in one key, and "
            "choose which directories get asked."
        ),
        steps=(
            Step(
                title="Open the search window",
                body=(
                    "Search Stations, on the Station menu, opens a window with a "
                    "few boxes instead of one: station name, tag and country. "
                    "They work together, so you can search for jazz in France or "
                    "jazz in Brazil and get different answers."
                ),
                keys=("Ctrl+F",),
                hear="Internet Radio, then the Station name box.",
            ),
            Step(
                title="Search the catalog first, and the internet second",
                body=(
                    "Type a name and press Enter. Stations already saved on your "
                    "computer show up straight away, and results from the "
                    "internet join them a moment later. So you get answers "
                    "quickly, even on a slow connection."
                ),
                keys=("Enter",),
                hear="How many results there are, then the list.",
            ),
            Step(
                title="Bring back a search you already ran",
                body=(
                    "In the station name box, press Down Arrow to hear your "
                    "earlier searches, newest first. Pick one and all three "
                    "boxes are filled in again just as you had them."
                ),
                keys=("Down arrow",),
                hear="Your earlier searches, newest first.",
                note=(
                    "The list keeps your last fifteen searches. Running one "
                    "again moves it to the top instead of adding a copy, and an "
                    "empty search is never kept."
                ),
            ),
            Step(
                title="Choose which directories are asked",
                body=(
                    "You decide which directories are searched, with Search "
                    "Sources on the main window's Station menu. A directory you "
                    "turn off is never contacted at all. Turning off the ones you "
                    "do not care about makes every search quicker and the "
                    "results less cluttered."
                ),
                keys=("Ctrl+Alt+Shift+U",),
                hear="A checklist of directories, each read as checked or not checked.",
            ),
            Step(
                title="Decide what a result row says",
                body=(
                    "Each result row is read out column by column, so the "
                    "columns decide what you hear. Choose Columns, on the main "
                    "window's View menu, lets you change their order, hide the "
                    "ones you do not want read, and turn on extras such as "
                    "language, genres, popularity and bitrate. The next search "
                    "window you open uses your new layout."
                ),
                keys=("Ctrl+Alt+Shift+C",),
                hear=(
                    "Two lists, shown and hidden, and a line that tells you how a row will sound."
                ),
                note=(
                    "The station's name always stays, so every row can be told "
                    "apart. If you try to hide it, Quill Radio tells you why it "
                    "has to stay."
                ),
            ),
            Step(
                title="Keep the good ones",
                body=(
                    "Press Enter on a row to have a listen, and add the ones you "
                    "like to your favorites from the row's own menu. Try before "
                    "you keep: that is what this window is for."
                ),
                keys=("Enter", "Shift+F10"),
                hear="Playing, and the station's name. Then Added, the name, to Favorites.",
            ),
        ),
        closing=(
            "Now you have both ways to find stations: wandering when you are not "
            "sure, and searching when you are. Next, find out how to add the "
            "stations no directory lists."
        ),
        then=("find-a-station-by-its-address", "addresses-of-your-own"),
    ),
)
