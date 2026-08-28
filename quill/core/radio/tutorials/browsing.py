"""Track 2, first half: the two ways to find a station you do not have yet.

Wandering and searching are different jobs and Quill Radio keeps them in
different windows on purpose, so these are two lessons rather than one. The
tree is for "show me what there is"; Find Stations is for "I know roughly what
I want". The third lesson here is the one that ties them together: a search
across every directory at once, run from inside the tree.
"""

from __future__ import annotations

from quill.core.radio.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="wander-the-tree",
        title="Wander the browse tree",
        track="finding",
        minutes=8,
        surfaces=("Browse Stations",),
        summary=(
            "Learn the tree well enough to explore it: how a branch loads, what a "
            "row is telling you before you press Enter, how to search inside one "
            "folder, and how to put a source's own options where you want them."
        ),
        steps=(
            Step(
                title="Open the tree and notice where it put you",
                body=(
                    "Browse Stations remembers the source you were last in. Open "
                    "it after having played something and you land back on that "
                    "branch, not collapsed at the top with everything closed. "
                    "That is a deliberate saving of the arrowing you already did."
                ),
                command="radio.browse",
                hear="Entered Browse Stations, and the branch you were last in.",
                check="window:Browse Stations",
            ),
            Step(
                title="Open a folder and let it tell you its size",
                body=(
                    "Open By Country and pick one. Every folder announces how many "
                    "stations it holds before you open it -- France, 812 stations. "
                    "The live directory could never afford that, because counting "
                    "used to cost a network round trip; it now costs nothing, "
                    "because the count comes off your own disk."
                ),
                keys=("Right arrow", "Down arrow"),
                hear="The country, then its station count, then its states or regions.",
            ),
            Step(
                title="Read a row before you play it",
                body=(
                    "Arrow onto a station and listen to the whole row. A row that "
                    "probably will not play says may not be playable; a row that "
                    "has to be looked up first -- TuneIn, YouTube -- says resolved "
                    "when you play it, so the pause before the audio starts is "
                    "explained rather than worrying."
                ),
                keys=("Down arrow",),
                hear="The station name, then any marking the row carries.",
                note=(
                    "Only Radio Browser publishes a playability check, so every "
                    "other row is deliberately unmarked. Marking the rest unknown "
                    "would put a word on nearly every row to tell you nothing."
                ),
            ),
            Step(
                title="Ask the row for its details",
                body=(
                    "With the Station Details pane on, arrowing a row fills a "
                    "read-only box with its source, stream, format and country -- "
                    "text you can arrow through and copy. Turn the pane off from "
                    "the View menu if you would rather not Tab past it; every "
                    "station surface honours the choice."
                ),
                keys=("Tab", "Ctrl+D"),
                hear="The details box, read as ordinary text.",
            ),
            Step(
                title="Search inside the folder you are standing in",
                body=(
                    "Find in this folder searches the rows under the folder you "
                    "are on, and matches a row's description as well as its name. "
                    "On a podcast show that makes it episode search, because the "
                    "episodes are the rows and their show notes are searched with "
                    "them. Clearing the box returns the folder."
                ),
                keys=("Ctrl+F",),
                hear="A find box, then the number of rows that matched.",
            ),
            Step(
                title="Open a row's own menu",
                body=(
                    "Shift+F10 -- or the Applications key -- on any row offers "
                    "everything else you can do to it: Play/Stop, add or remove "
                    "the favorite, copy the stream link, open the website, Report "
                    "Bad Station, Refresh, and Set a Reminder. This menu is where "
                    "the depth of the tree lives."
                ),
                keys=("Shift+F10",),
                hear="A context menu, read from the top.",
                note=(
                    "The first item is what Enter does, and the first nine answer "
                    "to Ctrl+1 through Ctrl+9. Quick Actions decides that order -- "
                    "see the lesson called Decide what Enter does."
                ),
            ),
            Step(
                title="Set a source's own options",
                body=(
                    "Some sources have a question of their own. Shift+F10 on the "
                    "source row and choose Source Options where it appears: Radio "
                    "Paradise asks which quality Enter should land on, SHOUTcast "
                    "asks whether to list everything or only stations somebody is "
                    "listening to right now. Your answer is spoken back and the "
                    "branch reloads immediately."
                ),
                keys=("Shift+F10",),
                hear="The option you chose, read back, then the branch reloading.",
            ),
            Step(
                title="Hide a source you will never use",
                body=(
                    "Shift+F10 on a top-level branch offers Hide This Source, and "
                    "Reset Sources to Default beside it. A branch that is off is "
                    "not in the tree at all and is never contacted, so this is a "
                    "speed and a privacy control as much as a tidiness one."
                ),
                command="radio.browse_sources",
                hear="Browse Stations has been updated, and the branch gone from the tree.",
            ),
        ),
        closing=(
            "The tree rewards wandering, and none of it needs a key, an account "
            "or a registration. When you know what you are looking for instead, "
            "the next lesson is faster."
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
            "Run one search across every source you have switched on, understand "
            "what the answer is telling you, and know why a short list is honest "
            "rather than complete."
        ),
        steps=(
            Step(
                title="Start from the top of the tree",
                body=(
                    "Search All Sources sits at the top of the browse tree. It "
                    "asks every enabled directory at the same moment and leaves "
                    "the answer as a Search Results branch at the top of the same "
                    "tree, so the answer arrives where you already are."
                ),
                keys=("Home", "Enter"),
                hear="A box asking what to search for.",
            ),
            Step(
                title="Type something specific enough to be interesting",
                body=(
                    "Search for a genre plus a place -- jazz new orleans -- rather "
                    "than a single word. Every source is asked at once, and the "
                    "whole search is capped at eight seconds, so a narrow query "
                    "gets you a usable list inside that cap."
                ),
                keys=("Enter",),
                hear=(
                    "After about four seconds, a spoken note that it is still going; then the "
                    "results."
                ),
            ),
            Step(
                title="Read what did not answer",
                body=(
                    "Anything that did not answer in time is named in the results "
                    "-- Internet Archive did not answer within 8 seconds -- so a "
                    "short list never pretends to be a complete one. Searching "
                    "again usually finds it there."
                ),
                keys=("Down arrow",),
                hear="The results, and any source that timed out, named.",
            ),
            Step(
                title="Search again from the Find box",
                body=(
                    "Standing on Search All Sources, or anywhere inside the "
                    "results it left, Ctrl+F puts you in the Find box; type and "
                    "press Enter and that runs the cross-source search for what "
                    "you typed, with no second prompt. Anywhere else in the tree, "
                    "the same box filters the branch you are standing in."
                ),
                keys=("Ctrl+F", "Enter"),
                hear="The new results replacing the old ones.",
                note=(
                    "This session's finished answers are remembered for ten "
                    "minutes, so repeating a search shows the full answer "
                    "immediately while a fresh one runs behind it."
                ),
            ),
            Step(
                title="Keep one, then close the results",
                body=(
                    "Add anything worth keeping to your favorites from the row's "
                    "own menu, then press Delete on the Search Results branch to "
                    "close it. It asks nothing, because nothing is lost -- your "
                    "query is still in the Find box."
                ),
                keys=("Delete",),
                hear="The branch gone, and the tree as it was.",
            ),
        ),
        closing=(
            "One search, every directory, one branch of results. If you would "
            "rather search by fields -- name and country and tag together -- the "
            "next lesson is the window for that."
        ),
        then=("find-stations-by-field",),
    ),
    Tutorial(
        slug="find-stations-by-field",
        title="Find stations by name, tag and country",
        track="finding",
        minutes=6,
        surfaces=("Search Stations", "Internet Radio"),
        summary=(
            "Use the field-based search window, get back to a search you ran "
            "before in one keystroke, and decide which directories are asked."
        ),
        steps=(
            Step(
                title="Open the search window",
                body=(
                    "Find Stations is a window of fields rather than one box: a "
                    "station name, a tag, a country. They work as a set, and that "
                    "is the point -- jazz in France and jazz in Brazil are "
                    "different searches."
                ),
                keys=("Ctrl+F",),
                hear="Entered the search window, with focus in the station-name field.",
            ),
            Step(
                title="Search the catalog first, and the internet second",
                body=(
                    "Type a name and press Enter. Matches from the catalog on your "
                    "own disk appear the moment you search; the live directories "
                    "layer in behind them. That is why the first results arrive "
                    "instantly even on a slow connection."
                ),
                keys=("Enter",),
                hear="A count of results, then the list.",
            ),
            Step(
                title="Bring back a search you already ran",
                body=(
                    "Press Down arrow in the station-name box for the searches you "
                    "ran before, newest first. Picking one restores all three "
                    "fields together, because they were one search; a list that "
                    "kept only the word jazz would give you back the wrong one."
                ),
                keys=("Down arrow",),
                hear="Your previous searches, newest first.",
                note=(
                    "The list holds fifteen, running the same search again moves "
                    "it to the top rather than adding a copy, and an empty search "
                    "is never kept."
                ),
            ),
            Step(
                title="Choose which directories are asked",
                body=(
                    "The search sources are yours to pick. A source that is "
                    "switched off is never contacted at all -- not asked and "
                    "ignored, not asked -- so turning off the ones you do not care "
                    "about makes every search faster as well as quieter."
                ),
                keys=("Alt+S",),
                hear="Each source with its own state read out.",
            ),
            Step(
                title="Decide what a result row says",
                body=(
                    "A list is read one column at a time, so the columns are the "
                    "sentence you hear on every row. Choose Columns lets you "
                    "reorder them, hide the ones you do not want spoken, and turn "
                    "on the ones that start switched off -- language, genres, "
                    "popularity, bitrate."
                ),
                keys=("Ctrl+Alt+Shift+C",),
                hear=(
                    "Two lists -- shown and hidden -- and a line spelling out how one row will "
                    "read."
                ),
                note=(
                    "The station's name is pinned and cannot be hidden: a row with "
                    "nothing to identify it is a row you cannot act on. Asking to "
                    "hide it says so rather than quietly refusing."
                ),
            ),
            Step(
                title="Keep the good ones",
                body=(
                    "Play a row with Enter to audition it, and add the keepers to "
                    "your favorites from the row's own menu. Listening before you "
                    "commit is the whole reason the search window plays rows at "
                    "all."
                ),
                keys=("Enter", "Shift+F10"),
                hear="Connecting, then Playing; then Added, and the station's name.",
            ),
        ),
        closing=(
            "You now have both halves: wandering when you do not know, fields "
            "when you do. What remains is the stations no directory lists -- and "
            "that is the next lesson."
        ),
        then=("addresses-of-your-own",),
    ),
)
