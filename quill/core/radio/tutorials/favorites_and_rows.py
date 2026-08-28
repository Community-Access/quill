"""Track 3, first half: your stations, your order, and what a row says.

These three lessons are about the difference between a list of stations and a
list that is *yours*. Folders and order come first, because that is the part
people put off and then cannot face doing at two hundred stations. Then the
ten slots that skip the list entirely. Then the two windows that decide what a
row reads out and what pressing Enter on it does -- both of which are speech
settings wearing a list setting's clothes.
"""

from __future__ import annotations

from quill.core.radio.tutorials.model import Step, Tutorial

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
                hear="Entered Manage Favorites.",
                check="window:Manage Favorites",
            ),
            Step(
                title="Make a folder before you need it",
                body=(
                    "New Folder asks where it goes -- top level, or inside any "
                    "existing folder -- and then for a name. It exists "
                    "immediately, empty, ready to be filed into. You can also just "
                    "file a station under News/Morning and the path springs into "
                    "being."
                ),
                keys=("Ctrl+Shift+E",),
                hear="The folder created, and its name.",
            ),
            Step(
                title="File a station into it",
                body=(
                    "Move to Folder on a station's own menu puts it away. Renaming "
                    "a folder later brings its subfolders along, and deleting a "
                    "folder lets its stations step out to the top level -- nothing "
                    "is ever deleted with a folder."
                ),
                keys=("Shift+F10",),
                hear="Moved, the station, and the folder it landed in.",
            ),
            Step(
                title="Move one station a long way",
                body=(
                    "Move Up and Move Down are for short hops. For a long one, "
                    "choose Mark for Move on the station, arrow to the "
                    "destination, and choose Move Above or Move Below -- the moved "
                    "station joins the destination's folder."
                ),
                keys=("Alt+Shift+Up", "Alt+Shift+Down"),
                hear="The new position, spoken as you move.",
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
                    "Sort Favorites -- on the View menu and in Preferences -- sets "
                    "the default for every folder: Ascending, Descending, or "
                    "Unsorted, which reveals the order you built by hand. Any "
                    "single folder can override that from its own menu."
                ),
                keys=("Alt+V",),
                hear="The three choices, with a bullet on the current one.",
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
                hear="The next station in the folder, named.",
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
                    "The manager's search filters live across names -- including "
                    "the names you gave them -- countries, languages, tags and "
                    "folder names. Results flatten into one arrow-key list with "
                    "each station's folder spoken in its label, so you never lose "
                    "track of where a match lives."
                ),
                hear="A count of matches, then each one with its folder.",
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
                    "Ten commands -- Play Favorite 1 through Play Favorite 10 -- "
                    "play the first ten stations in your favorites directly, with "
                    "no menu and no arrowing. They are the reason the order you "
                    "built in the last lesson is worth building."
                ),
                command="radio.play_favorite_1",
                hear="Connecting, then Playing, and the station's name.",
                check="playing",
            ),
            Step(
                title="Move a station into a slot",
                body=(
                    "A slot is simply a position in the list, so putting a station "
                    "on Play Favorite 3 means moving it to third. Do that in the "
                    "manager with Move Up, or with Alt+Shift+Up on the main "
                    "window's tree."
                ),
                keys=("Alt+Shift+Up",),
                hear="The station's new position.",
            ),
            Step(
                title="Rebind the slots to shorter keys",
                body=(
                    "The default chords are deliberately long, because the plain "
                    "number keys are already taken by window switching. If you do "
                    "not use those, the Keyboard Manager will happily put these "
                    "ten on Alt+1 through Alt+0 instead."
                ),
                hear="The Keyboard Manager, with a warning if a key is already in use.",
            ),
            Step(
                title="Go back to something you played once",
                body=(
                    "Recently Played, on the Station menu, holds your last fifteen "
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
                    "with the menus on it."
                ),
                keys=("Ctrl+Shift+1", "Ctrl+Shift+2"),
                hear="The new surface announced, with focus in its main control.",
                note=(
                    "The choice takes effect at once, with no restart, and a view "
                    "you have visited keeps its state -- switching away from "
                    "Browse and back finds your tree still expanded."
                ),
            ),
            Step(
                title="Open one window at startup, if you want one",
                body=(
                    "Preferences chooses the single window Quill Radio opens for "
                    "you at launch: none, Browse Stations, Search Stations, Manage "
                    "Favorites, Recordings, or the Player. It opens over the main "
                    "window rather than instead of it, and everything else stays "
                    "closed."
                ),
                keys=("Ctrl+,",),
                hear="The setting read back with its current value.",
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
        title="Decide what a row says, and what Enter does",
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
                    "Stand in Find Stations results or the Recordings list and "
                    "open Choose Columns. A list is read one column at a time, so "
                    "the columns are the sentence you hear on every row -- this is "
                    "where you write that sentence."
                ),
                keys=("Ctrl+Alt+Shift+C",),
                hear="Two lists: shown in the order they are read, and hidden.",
            ),
            Step(
                title="Hear the change before you accept it",
                body=(
                    "Underneath the lists, A row will read spells out exactly what "
                    "one row will say with the settings as they stand. Move "
                    "something and listen to that line again before pressing OK."
                ),
                keys=("Alt+Up", "Alt+Down"),
                hear="The sample row, rebuilt after every change.",
            ),
            Step(
                title="Take a column out rather than moving it down",
                body=(
                    "Hide removes a column from the row altogether, not to the end "
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
                    "Quick Actions decides what each kind of row offers and in "
                    "what order. There are three lists -- station actions, "
                    "recording actions, browse folder actions -- and in each, the "
                    "first action is what Enter does."
                ),
                keys=("Ctrl+Alt+Q",),
                hear="A combo box naming the list, then the actions in order.",
            ),
            Step(
                title="Put your verb first",
                body=(
                    "Move Up, Move Down and Make Default rearrange; the first nine "
                    "answer to Ctrl+1 through Ctrl+9, and the whole list is the "
                    "order of the right-click menu. Reset This List puts one back "
                    "to how it shipped."
                ),
                hear="The action's new position in the list.",
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
                    "Go To Settings -- the Settings button in the Go To list -- "
                    "chooses which ten places are in the numbered menu and in what "
                    "order. Put what you use most at 1. An update will never "
                    "renumber your list: a place added in a later version waits in "
                    "the not-in-the-menu list until you place it."
                ),
                keys=("Ctrl+G",),
                hear="Two lists, and each place with its own direct shortcut.",
            ),
        ),
        closing=(
            "Both windows are worth ten minutes once. A list that reads the four "
            "things you care about is a different list from one that reads nine."
        ),
        then=("keys-that-are-yours",),
    ),
)
