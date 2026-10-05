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
            "Make folders for your stations, put stations in the order you "
            "like, and play a whole folder as a set. It is much easier to do "
            "this now, while you have twenty favorites, than later when you "
            "have two hundred."
        ),
        steps=(
            Step(
                title="Open the manager",
                body=(
                    "Manage Favorites is where you organize: search, folders, "
                    "order, and every action, all on one screen. The favorites "
                    "list in the main window can do the same things one station "
                    "at a time, so you only need the manager for bigger tidy-ups."
                ),
                command="radio.manage_favorites",
                hear=("Manage Favorite Stations, then the Search favorites box, where you start."),
                check="window:Manage Favorites",
            ),
            Step(
                title="Make a folder before you need it",
                body=(
                    "Tab to the list and press the New Folder key, or use the "
                    "New Folder button. It asks where the folder should go, at "
                    "the top or inside another folder, and then asks for a name. "
                    "The folder is ready straight away. You can also just file a "
                    "station under News/Morning, and those folders are made for "
                    "you."
                ),
                keys=("Ctrl+Shift+E",),
                hear=("New Folder, Location. Then Folder name. Then Created folder and its name."),
            ),
            Step(
                title="File a station into it",
                body=(
                    "Move to Folder, on a station's own menu or as a button, "
                    "puts the station in a folder. If you rename a folder later, "
                    "the folders inside it come along. If you delete a folder, "
                    "its stations move up to the top level. Deleting a folder "
                    "never deletes your stations."
                ),
                keys=("Shift+F10",),
                hear="Filed, the station, under the folder it went into.",
            ),
            Step(
                title="Move one station a long way",
                body=(
                    "Move Up and Move Down are for small moves. In the main "
                    "window's favorites list, the same moves are Alt+Shift+Up and "
                    "Alt+Shift+Down. For a big move, choose Mark for Move on the "
                    "station, arrow to where you want it, and choose Move Above "
                    "or Move Below from that row's menu. The station joins that "
                    "row's folder."
                ),
                keys=("Alt+U", "Alt+D", "Shift+F10"),
                hear=(
                    "Moved up, now below the station it passed. Or, after Mark for Move, "
                    "Marked, then Moved above and the other station's name."
                ),
                note=(
                    "If the list is sorted A to Z, your first move switches it "
                    "to your own order and says Switched to manual order. Your "
                    "own order is always kept safe, even while you look at the "
                    "list alphabetically."
                ),
            ),
            Step(
                title="Choose how folders are ordered",
                body=(
                    "Sort Favorites, on the View menu, sets the order for every "
                    "folder: Ascending, Descending, or Unsorted, which shows the "
                    "order you arranged yourself. The same choice is Favorites "
                    "sort order in Preferences. Any one folder can have its own "
                    "order too, with Sort This Folder on that folder's menu in "
                    "the main window's list."
                ),
                keys=("Alt+V",),
                hear=(
                    "The View menu. On its Sort Favorites submenu, the three choices with "
                    "the current one checked."
                ),
            ),
            Step(
                title="Play a folder as a set",
                body=(
                    "A folder's own menu has Play All in Folder and Shuffle "
                    "Folder. Live radio never ends, so playing a folder means "
                    "you can hop to the next station in that folder with one key "
                    "whenever you like. Next Station in Folder and Previous "
                    "Station in Folder are in the command palette."
                ),
                command="radio.folder_next",
                hear="The next station's name, and where it is in the folder. 2 of 6, say.",
                note=(
                    "Shuffle picks one order and sticks to it, so Previous takes "
                    "you back the same way. When you reach the first or last "
                    "station, Quill Radio tells you, instead of starting again "
                    "from the other end."
                ),
            ),
            Step(
                title="Search your own stations",
                body=(
                    "The Search favorites box at the top of the manager filters "
                    "as you type. It looks at station names, including names you "
                    "gave them, and countries, languages, tags and folder names. "
                    "The matches appear as one simple list, and each one says "
                    "which folder it is in."
                ),
                keys=("Alt+K",),
                hear=(
                    "How many matched, on the status line below the list. Then each match "
                    "with its folder as you arrow."
                ),
            ),
        ),
        closing=(
            "You have folders, your own order, and a way to play a set. Your "
            "favorites now feel like your own collection, not just a pile of "
            "things you added."
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
            "Put your ten favorite stations on ten keys, find your way back to "
            "what you played recently, and choose what the main window shows."
        ),
        steps=(
            Step(
                title="Play favorite number one",
                body=(
                    "Play Favorite 1 to Play Favorite 10, on Alt+1 to Alt+0, play "
                    "the first ten stations in your favorites, in the order the "
                    "list shows them. No menu and no arrowing. This is why it is "
                    "worth putting your favorites in order."
                ),
                command="radio.play_favorite_1",
                hear=(
                    "Playing favorite 1, and the station's name. Or, with no favorites yet, "
                    "No favorite in slot 1."
                ),
                check="playing",
            ),
            Step(
                title="Move a station into a slot",
                body=(
                    "Each key simply plays whatever is at that spot in the list. "
                    "So to put a station on Play Favorite 3, move it to third "
                    "place, with Move Up in the manager or Alt+Shift+Up in the "
                    "main window's list. If the list is sorted A to Z, your first "
                    "move switches you to your own order."
                ),
                keys=("Alt+Shift+Up",),
                hear="Moved up, now below the station it passed.",
            ),
            Step(
                title="Rebind the slots if Alt and a digit do not suit you",
                body=(
                    "These keys start on Alt+1 to Alt+0. Ctrl+1 to Ctrl+9 are "
                    "different: they switch between open windows. If your screen "
                    "reader or another program already uses Alt with a number, "
                    "open Keyboard Shortcuts on the Help menu and move any of the "
                    "ten to a key you prefer."
                ),
                keys=("Ctrl+Alt+K",),
                hear="The keyboard shortcuts editor, with a warning if a key is already in use.",
            ),
            Step(
                title="Go back to something you played once",
                body=(
                    "Recently Played, on the Station menu, lists your last "
                    "fifteen stations, newest first. Choose one to play it "
                    "straight from the menu. It always includes what you played "
                    "five minutes ago."
                ),
                keys=("Alt+S",),
                hear="The submenu, newest station first.",
            ),
            Step(
                title="Decide what the main window shows",
                body=(
                    "The main window can show your favorites, Browse Stations, "
                    "Search, your recordings or the Player. Whichever you pick, "
                    "the menus, the now playing line, Mute, Volume and the status "
                    "bar stay the same. So you can live in the view you use most "
                    "and still have everything to hand. Choose it with Main "
                    "Window Shows on the View menu. Each view has its own key."
                ),
                keys=("Ctrl+Shift+1", "Ctrl+Shift+2"),
                hear=(
                    "Main window now shows, the view's name, and one sentence about what it is for."
                ),
                note=(
                    "The change happens straight away, with no restart. Each "
                    "view remembers where you were, so if you leave Browse and "
                    "come back, your folders are still open."
                ),
            ),
            Step(
                title="Make the choice in Preferences instead",
                body=(
                    "Preferences has the same setting, called Main window shows: "
                    "Favorite stations, Browse Stations, Search Stations, Radio "
                    "Recordings or Player. That is the view you open into every "
                    "time. Every other window is still just one key away."
                ),
                keys=("Ctrl+,", "Alt+M"),
                hear="Main window shows, combo box, and its current setting.",
            ),
        ),
        closing=(
            "With ten keys, Recently Played and Play Last Station, most days you "
            "will not need to open a list at all. Enjoy that."
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
            "Two windows that change how Quill Radio sounds to you: which "
            "details a list reads out, and which actions come first on a row's "
            "menu."
        ),
        steps=(
            Step(
                title="Open Choose Columns on a list you use",
                body=(
                    "Choose Columns is on the View menu. The first control, "
                    "Columns for, picks the list you want to change: Find "
                    "Stations results or Recordings. Each row is read out column "
                    "by column, so this is where you decide what you hear on "
                    "every row."
                ),
                keys=("Ctrl+Alt+Shift+C",),
                hear=(
                    "Choose Columns, then Columns for. Tab reaches the Shown list, in the "
                    "order the columns are read, and then the Hidden list."
                ),
            ),
            Step(
                title="Hear the change before you accept it",
                body=(
                    "Under the lists, A row will read tells you exactly what one "
                    "row will sound like with your choices. In the Shown list, "
                    "Alt+Up and Alt+Down move a column. Listen to that line again "
                    "before you press OK."
                ),
                keys=("Alt+Up", "Alt+Down", "Alt+A"),
                hear="The column's name and where it is read now. Second, say.",
            ),
            Step(
                title="Take a column out rather than moving it down",
                body=(
                    "The Hide button takes a column out of the row completely, "
                    "so it is not read at all. Show puts it back in its usual "
                    "place, so if you hide something for a week and then show it "
                    "again, it goes back where it was."
                ),
                hear="The column moving between the two lists, and the sample row without it.",
                note=(
                    "One column in each list always stays: the station's name, "
                    "or the recording's name. That way every row can be told "
                    "apart."
                ),
            ),
            Step(
                title="Turn on a column that starts switched off",
                body=(
                    "Find Stations can also read language, genres, popularity and "
                    "bitrate, and Recordings can read length. They start off to "
                    "keep rows short. But if bitrate is how you choose stations, "
                    "go ahead and turn it on."
                ),
                hear="The sample row, now with the column you added.",
            ),
            Step(
                title="Open Quick Actions",
                body=(
                    "Quick Actions, on the Station menu, sets the order of the "
                    "menu you get on each kind of row. There are two lists, "
                    "station actions and browse folder actions, and you choose "
                    "between them with Actions for. Enter on a row still plays or "
                    "opens it, whatever order you choose."
                ),
                keys=("Ctrl+Alt+Q",),
                hear="Quick Actions, then Actions for, combo box, naming the list.",
            ),
            Step(
                title="Put your verb first",
                body=(
                    "Move Up, Move Down and Move to Top change the order. The "
                    "list you see is the order of the menu Shift+F10 opens on a "
                    "row. Reset This List puts it back the way it was when you "
                    "installed Quill Radio."
                ),
                keys=("Alt+U", "Alt+D", "Alt+T"),
                hear=(
                    "The action, is now number 2. Or, from Move to Top, is now first in the menu."
                ),
                note=(
                    "This only changes the order of what a row already offers. "
                    "Putting Download first does not let you download a live "
                    "station. It just means Download comes first on rows that "
                    "have it."
                ),
            ),
            Step(
                title="Arrange your places while you are at it",
                body=(
                    "Go To Settings, the Settings button in the Go To window, "
                    "lets you choose which ten places are in the numbered list "
                    "and in what order. Put the one you use most at 1. Updates "
                    "never renumber your list. If a new version adds a place, it "
                    "waits in the Not in the menu list until you add it."
                ),
                keys=("Ctrl+G", "Alt+S"),
                hear=(
                    "Two lists, In the menu and Not in the menu, each place read with its number."
                ),
            ),
        ),
        closing=(
            "Both windows are worth ten minutes, just once. A list that reads "
            "only the four things you care about feels very different from one "
            "that reads nine."
        ),
        then=("keys-that-are-yours",),
    ),
)
