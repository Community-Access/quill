"""Track 3, first half: your stations, your order, and what a row says.

These three lessons are about the difference between a list of stations and a
list that is *yours*. Folders and order come first, because that is the part
people put off and then cannot face doing at two hundred stations. Then the
ten slots that skip the list entirely. Then the two windows that decide what a
row reads out and what pressing Enter on it does -- both of which are speech
settings wearing a list setting's clothes.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="folders-and-order",
        title="Folders, and an order of your own",
        track="yours",
        minutes=8,
        surfaces=("Manage Favorites", "Quill Radio"),
        summary=(
            "Build folders of any depth, move stations around without hunting, "
            "and play a whole folder as a set. Do this while you have twenty "
            "favorites rather than two hundred."
        ),
        steps=(
            Step(
                title="Open the manager",
                body=(
                    "Manage Favorites is the organizer: search, folders, "
                    "reordering, and every action on one screen. The main "
                    "window's tree offers the same actions on one station at a "
                    "time, so the manager is for the heavy lifting rather than a "
                    "required stop."
                ),
                command="radio.manage_favorites",
                hear=(
                    "Manage Favorite Stations, then the Search favorites box, "
                    "which is where focus starts."
                ),
                check="window:Manage Favorites",
            ),
            Step(
                title="Make a folder before you need it",
                body=(
                    "Tab to the tree and press New Folder's key, or use the New "
                    "Folder button. It asks where the folder goes -- top level, or "
                    "inside any existing folder -- and then for a name. It exists "
                    "immediately, empty, ready to be filed into. You can also just "
                    "file a station under News/Morning and the path springs into "
                    "being."
                ),
                keys=("Ctrl+Shift+E",),
                hear=(
                    "New Folder -- Location, then Folder name, then Created folder and its name."
                ),
            ),
            Step(
                title="File a station into it",
                body=(
                    "Move to Folder, on a station's own menu or as the Move to "
                    "Folder button, puts it away. Renaming "
                    "a folder later brings its subfolders along, and deleting a "
                    "folder lets its stations step out to the top level -- nothing "
                    "is ever deleted with a folder."
                ),
                keys=("Shift+F10",),
                hear="Filed, the station, under the folder it landed in.",
            ),
            Step(
                title="Move one station a long way",
                body=(
                    "The Move Up and Move Down buttons are for short hops; on the "
                    "main window's favorites tree the same hop is Alt+Shift+Up and "
                    "Alt+Shift+Down. For a long one, choose Mark for Move on the "
                    "station, arrow to the destination, and choose Move Above or "
                    "Move Below from its menu -- the moved station joins the "
                    "destination's folder."
                ),
                keys=("Alt+U", "Alt+D", "Shift+F10"),
                hear=(
                    "Moved up, now below the station it passed -- or, after Mark for "
                    "Move, Marked, then Moved above and the destination's name."
                ),
                note=(
                    "If the list is currently sorted A to Z, the first move "
                    "switches to your manual order and says Switched to manual "
                    "order. Your hand-arranged order is stored separately and is "
                    "never overwritten by the alphabetical view."
                ),
            ),
            Step(
                title="Choose how folders are ordered",
                body=(
                    "Sort Favorites -- a submenu of the View menu, and Favorites "
                    "sort order in Preferences -- sets the default for every "
                    "folder: Ascending, Descending, or Unsorted, which reveals the "
                    "order you built by hand. Any single folder can override that "
                    "with Sort This Folder, on that folder's menu in the main "
                    "window's tree."
                ),
                keys=("Alt+V",),
                hear=(
                    "The View menu; on its Sort Favorites submenu, the three "
                    "choices with the current one checked."
                ),
            ),
            Step(
                title="Play a folder as a set",
                body=(
                    "A folder's own menu offers Play All in Folder and Shuffle "
                    "Folder. Live radio never ends, so there is nothing for a "
                    "playlist to advance on -- what playing a folder actually "
                    "means is one keystroke to the next station in the set you "
                    "chose. Next Station in Folder and Previous Station in Folder "
                    "are in the command palette."
                ),
                command="radio.folder_next",
                hear="The next station's name, and where it sits: 2 of 6, say.",
                note=(
                    "Shuffle is one fixed order, so Previous walks back through "
                    "the same sequence. Reaching either end says so rather than "
                    "wrapping round: silently looping is how you hear the same "
                    "station twice and cannot work out why."
                ),
            ),
            Step(
                title="Search your own stations",
                body=(
                    "The Search favorites box at the top of the manager filters "
                    "live across names -- including "
                    "the names you gave them -- countries, languages, tags and "
                    "folder names. Results flatten into one arrow-key list with "
                    "each station's folder spoken in its label, so you never lose "
                    "track of where a match lives."
                ),
                keys=("Alt+K",),
                hear=(
                    "The count of matches on the status line below the tree, then "
                    "each match with its folder as you arrow the tree."
                ),
            ),
        ),
        closing=(
            "Folders, order, and a way to play a set. The list is now yours "
            "rather than the order you happened to add things in."
        ),
        then=("ten-slots",),
    ),
    Tutorial(
        slug="ten-slots",
        title="Ten stations, no list at all",
        track="yours",
        minutes=4,
        surfaces=("Quill Radio",),
        summary=(
            "Put your ten most-played stations on ten chords, learn the two "
            "routes back to what you played recently, and decide what the main "
            "window shows in the first place."
        ),
        steps=(
            Step(
                title="Play favorite number one",
                body=(
                    "Ten commands -- Play Favorite 1 through Play Favorite 10, on "
                    "Alt+1 through Alt+0 -- play the first ten stations in your "
                    "favorites, in the order the list shows them, with no menu and "
                    "no arrowing. They are the reason the order you built in the "
                    "last lesson is worth building."
                ),
                command="radio.play_favorite_1",
                hear=(
                    "Playing favorite 1, and the station's name -- or, with no "
                    "favorites yet, No favorite in slot 1."
                ),
                check="playing",
            ),
            Step(
                title="Move a station into a slot",
                body=(
                    "A slot is simply a position in the list, so putting a station "
                    "on Play Favorite 3 means moving it to third. Do that in the "
                    "manager with Move Up, or with Alt+Shift+Up on the main "
                    "window's tree. While the list is sorted A to Z, the slots "
                    "follow the alphabet, so the first move switches you to your "
                    "own order."
                ),
                keys=("Alt+Shift+Up",),
                hear="Moved up, now below the station it passed.",
            ),
            Step(
                title="Rebind the slots if Alt and a digit do not suit you",
                body=(
                    "The slots ship on Alt+1 through Alt+0, one modifier away from "
                    "Ctrl+1 to Ctrl+9, which switch between open windows. If your "
                    "screen reader or another program wants Alt and a digit, "
                    "Keyboard Shortcuts on the Help menu will move any of the ten "
                    "to a key of your choosing."
                ),
                keys=("Ctrl+Alt+K",),
                hear="The keyboard shortcuts editor, with a warning if a key is already in use.",
            ),
            Step(
                title="Go back to something you played once",
                body=(
                    "Recently Played, a submenu of the Station menu, holds your last fifteen "
                    "stations, newest first, playable straight from the menu. It "
                    "is rebuilt just before the menu opens, so it always includes "
                    "what you played five minutes ago."
                ),
                keys=("Alt+S",),
                hear="The submenu, newest station first.",
            ),
            Step(
                title="Decide what the main window shows",
                body=(
                    "The main window can show your favorites, the browse tree, the "
                    "search, the recordings list or the player -- and the frame "
                    "around it does not change. The menu bar, the now-playing "
                    "line, Mute, Volume and the status bar are the same in all "
                    "five, which is the point: the surface you live in is the one "
                    "with the menus on it. The choice is Main Window Shows, a "
                    "submenu of the View menu, one key per view."
                ),
                keys=("Ctrl+Shift+1", "Ctrl+Shift+2"),
                hear=(
                    "Main window now shows, the view's name, and one sentence about what it is for."
                ),
                note=(
                    "The choice takes effect at once, with no restart, and a view "
                    "you have visited keeps its state -- switching away from "
                    "Browse and back finds your tree still expanded."
                ),
            ),
            Step(
                title="Make the choice in Preferences instead",
                body=(
                    "Preferences carries the same setting as Main window shows: "
                    "Favorite stations, Browse Stations, Search Stations, Radio "
                    "Recordings or Player. It is what you open into at every "
                    "launch; nothing else opens beside it, and every other window "
                    "is still one key away."
                ),
                keys=("Ctrl+,", "Alt+M"),
                hear="Main window shows, combo box, and its current value.",
            ),
        ),
        closing=(
            "Between ten chords, Recently Played and Play Last Station, most days "
            "you should never need to open a list at all."
        ),
        then=("rows-that-say-what-you-want",),
    ),
    Tutorial(
        slug="rows-that-say-what-you-want",
        title="Decide what a row says, and what its menu offers first",
        track="yours",
        minutes=6,
        surfaces=("Choose Columns", "Quick Actions", "Search Stations", "Radio Recordings"),
        summary=(
            "Two windows that change how the app sounds rather than what it can "
            "do: the columns a list reads out, and the order of actions on a row."
        ),
        steps=(
            Step(
                title="Open Choose Columns on a list you use",
                body=(
                    "Choose Columns is on the View menu. Its first control, "
                    "Columns for, picks the list you are shaping: Find Stations "
                    "results or Recordings. A list is read one column at a time, "
                    "so the columns are the sentence you hear on every row -- this "
                    "is where you write that sentence."
                ),
                keys=("Ctrl+Alt+Shift+C",),
                hear=(
                    "Choose Columns, then Columns for; Tab reaches the Shown list, "
                    "in the order columns are read, and the Hidden list."
                ),
            ),
            Step(
                title="Hear the change before you accept it",
                body=(
                    "Underneath the lists, A row will read spells out exactly what "
                    "one row will say with the settings as they stand. In the "
                    "Shown list, Alt+Up and Alt+Down move a column; then listen to "
                    "that line again before pressing OK."
                ),
                keys=("Alt+Up", "Alt+Down", "Alt+A"),
                hear="The column's name and where it is now read -- second, say.",
            ),
            Step(
                title="Take a column out rather than moving it down",
                body=(
                    "The Hide button removes a column from the row altogether, not to the end "
                    "of it -- a column that is still there is still spoken. Show "
                    "puts one back where its place in the order says it belongs, "
                    "so hiding something for a week and showing it again does not "
                    "send it to the end."
                ),
                hear="The column moved between the two lists, and the sample row without it.",
                note=(
                    "One column in each list is pinned -- the station's name, the "
                    "recording's name -- because a row with nothing to identify it "
                    "is a row you cannot act on."
                ),
            ),
            Step(
                title="Turn on a column that starts switched off",
                body=(
                    "Find Stations can also read language, genres, popularity and "
                    "bitrate; Recordings can read length. They start off because a "
                    "list that says everything says nothing -- but if bitrate is "
                    "what you choose stations on, put it in."
                ),
                hear="The sample row, now with the column you added.",
            ),
            Step(
                title="Open Quick Actions",
                body=(
                    "Quick Actions, on the Station menu, decides the order of the "
                    "right-click menu on each kind of row. There are two lists -- "
                    "station actions and browse folder actions -- chosen in Actions "
                    "for. Enter on a row still plays or opens it, whatever the order."
                ),
                keys=("Ctrl+Alt+Q",),
                hear="Quick Actions, then Actions for, combo box, naming the list.",
            ),
            Step(
                title="Put your verb first",
                body=(
                    "Move Up, Move Down and Move to Top rearrange, and the whole "
                    "list is the order of the right-click menu, which Shift+F10 "
                    "opens. Reset This List puts one back to how it shipped."
                ),
                keys=("Alt+U", "Alt+D", "Alt+T"),
                hear=(
                    "The action, is now number 2 -- or, from Move to Top, is now first in the menu."
                ),
                note=(
                    "It orders what a row already offers and never adds anything. "
                    "Putting Download at the top does not make a live stream "
                    "downloadable -- it means Download is first on the rows that "
                    "have it."
                ),
            ),
            Step(
                title="Arrange your places while you are at it",
                body=(
                    "Go To Settings -- the Settings button in the Go To window -- "
                    "chooses which ten places are in the numbered menu and in what "
                    "order. Put what you use most at 1. An update will never "
                    "renumber your list: a place added in a later version waits in "
                    "the not-in-the-menu list until you place it."
                ),
                keys=("Ctrl+G", "Alt+S"),
                hear=(
                    "Two lists, In the menu and Not in the menu, each place read with its number."
                ),
            ),
        ),
        closing=(
            "Both windows are worth ten minutes once. A list that reads the four "
            "things you care about is a different list from one that reads nine."
        ),
        then=("keys-that-are-yours",),
    ),
)
