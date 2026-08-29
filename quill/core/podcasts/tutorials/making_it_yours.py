"""QUILL Cast, track 4: making it yours, and keeping it safe.

Five lessons: arranging a library that has grown, deciding what a row says and
what Enter does, the settings that differ per show, the feeds and folders that
are yours alone, and the backup you will be glad of exactly once.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="organise-the-library",
        title="Arrange a library that has grown",
        track="yours",
        minutes=6,
        surfaces=("QUILL Cast", "Podcast Manager"),
        summary=(
            "Folders, an order of your own, favorites, and the counts that tell "
            "you what is waiting without your having to open anything."
        ),
        steps=(
            Step(
                title="Read what a row already tells you",
                body=(
                    "A show wears its unplayed count in words -- (3 unheard) -- and "
                    "a folder wears how many podcasts live under it, counting "
                    "everything expanding it would reveal. That is the tree "
                    "answering what is waiting before you open anything."
                ),
                keys=("Down arrow",),
                hear="Each show with its unheard count.",
            ),
            Step(
                title="Make a folder",
                body=(
                    "New Folder creates a library folder without opening the "
                    "Manager. Folders nest, so News/Daily and News/Weekly are both "
                    "possible and both readable."
                ),
                keys=("Alt+S",),
                hear="The folder created, by name.",
            ),
            Step(
                title="File shows into it",
                body=(
                    "Move to Folder on a show's context menu. Deleting a folder "
                    "later dissolves it -- your shows step safely to the top level. "
                    "Nothing is ever unsubscribed by deleting a folder, which is "
                    "the fear that stops people making folders at all."
                ),
                keys=("Shift+F10",),
                hear="Moved, and the folder it landed in.",
            ),
            Step(
                title="Put them in the order you think in",
                body=(
                    "Sort Podcasts offers A to Z, Z to A, or your custom order. "
                    "Alt+Up and Alt+Down nudge a show among its folder's "
                    "neighbours, and the first move switches to custom "
                    "automatically -- starting from the order already on screen, so "
                    "nothing jumps."
                ),
                keys=("Alt+Up", "Alt+Down"),
                hear="The show's new position.",
            ),
            Step(
                title="Order the episode lists too",
                body=(
                    "Sort shows in the Manager orders podcasts within each folder "
                    "-- Title, most unheard first, recently updated first, or your "
                    "custom order. The dropdown opens on whatever the library is "
                    "actually sorted by, so the Manager and the main window never "
                    "disagree."
                ),
                keys=("Ctrl+M",),
                hear="The sort read back.",
            ),
            Step(
                title="Keep the ones you love where you can find them",
                body=(
                    "Add to Favorites on a show puts it in the Favorites pinned "
                    "view. The button on the main window reads Remove from "
                    "Favorites when the playing show is already one, so it never "
                    "shows you the opposite of the truth."
                ),
                keys=("Shift+F10",),
                hear="Added to Favorites, or removed.",
            ),
        ),
        closing=(
            "Do this at twenty shows rather than at two hundred. The tree is the "
            "surface you live in."
        ),
        then=("rows-and-actions",),
    ),
    Tutorial(
        slug="rows-and-actions",
        title="Decide what a row says, and what Enter does",
        track="yours",
        minutes=5,
        surfaces=("Choose Columns", "Quick Actions", "Podcast Manager"),
        summary=(
            "Two windows that change how the app sounds rather than what it can "
            "do -- plus the numbered list of places that never renumbers itself."
        ),
        steps=(
            Step(
                title="Open Choose Columns",
                body=(
                    "An episode list is read one column at a time, so the columns "
                    "are the sentence you hear on every row. This window decides it "
                    "-- for the episode list, for Downloads, and for Add Podcast's "
                    "search results."
                ),
                keys=("Ctrl+Alt+Shift+C",),
                hear="Two lists: shown in the order they are read, and hidden.",
            ),
            Step(
                title="Hear the change before you keep it",
                body=(
                    "A row will read spells out the sentence one row will say with "
                    "the settings exactly as they stand. Move something, listen to "
                    "that line, and only then press OK."
                ),
                keys=("Alt+Up", "Alt+Down"),
                hear="The sample row, rebuilt after every change.",
            ),
            Step(
                title="Turn on the column you have been missing",
                body=(
                    "The episode list can also show Podcast (worth having in a list "
                    "that spans shows, noise in a list of one), Time Left on "
                    "something you started, and Downloaded. Add Podcast's results "
                    "can show the feed address, which tells two same-named shows "
                    "apart."
                ),
                hear="The sample row with the column you added.",
            ),
            Step(
                title="Decide what Enter does",
                body=(
                    "Quick Actions orders the actions on episodes, podcasts and "
                    "queue items. The first action in each list is what Enter does, "
                    "the first nine answer to Ctrl+1 through Ctrl+9, and the whole "
                    "list is the order of the context menu."
                ),
                command="podcasts.quick_actions",
                hear="A combo box naming the list, then the actions in order.",
            ),
            Step(
                title="Put the three-second settings first",
                body=(
                    "Episodes to Keep, Queue Expiry and Playback Speed each open a "
                    "window holding one control with the cursor already in it. They "
                    "are Quick Actions too, so if you adjust speed constantly, put "
                    "it first and reach it with Ctrl+1."
                ),
                keys=("Ctrl+1",),
                hear="The setting's own window, with the cursor in the one control.",
            ),
            Step(
                title="Arrange your places",
                body=(
                    "Go To is a short numbered list of places -- the Manager, "
                    "Continue Listening, the Play Queue, Downloads, Bookmarks, "
                    "Statistics, Add a Podcast, Episode Notes, the Sleep Timer, "
                    "Preferences. The numbering never moves, which is exactly what "
                    "the Window menu cannot promise."
                ),
                command="app.go_to",
                keys=("Ctrl+G",),
                hear="The numbered list, each row with its own direct key.",
            ),
        ),
        closing=(
            "Rows show the place's own key where it has one, so the popup teaches "
            "itself out of a job: use Go To 1 for a month and you will have "
            "learned Ctrl+M."
        ),
        then=("shared-and-per-show",),
    ),
    Tutorial(
        slug="shared-and-per-show",
        title="Shared defaults, and one show's own mind",
        track="yours",
        minutes=6,
        surfaces=("Podcast Settings", "Podcast Manager"),
        summary=(
            "How Cast's settings actually work: a shared default everything "
            "follows until one show disagrees -- and how to make a show stop "
            "disagreeing."
        ),
        steps=(
            Step(
                title="Open the shared defaults",
                body=(
                    "Podcast Settings holds what every show follows unless it sets "
                    "its own: playback mode, retention, download location, the "
                    "reconnect rules, default speed, automatic downloads, the Inbox "
                    "rules and what happens when an episode finishes."
                ),
                keys=("Alt+S",),
                hear="Entered Podcast Settings.",
            ),
            Step(
                title="Set one show's own mind",
                body=(
                    "Settings for This Podcast, on any show's context menu, holds "
                    "the same choices for one show -- plus the ones that only make "
                    "sense per podcast: Auto-Queue, Announce New Episodes, queue "
                    "expiry, the Inbox age limit, Route to Inbox and Favorite."
                ),
                keys=("Shift+F10",),
                hear="The show named, then its own settings.",
            ),
            Step(
                title="Understand what Use the shared default means",
                body=(
                    "Anything left on Use the shared default stores no override at "
                    "all, so changing the global later still reaches that show. "
                    "That is the difference between inheriting a value and having "
                    "silently copied it."
                ),
                hear="The setting read back as following the default.",
            ),
            Step(
                title="Undo every override at once",
                body=(
                    "Follow the Shared Defaults drops every override for a show in "
                    "one go. It is the way out of an hour of fiddling, and worth "
                    "knowing about before you start fiddling."
                ),
                hear="The show back on the shared defaults.",
            ),
            Step(
                title="Choose where the app opens",
                body=(
                    "Start on this view decides what QUILL Cast opens on: New "
                    "Episodes, Continue Listening, the Inbox, Favorites, Recently "
                    "Expired, or the top of the tree. Pick the question you "
                    "actually ask first."
                ),
                hear="The view read back.",
            ),
            Step(
                title="Decide what closing means",
                body=(
                    "When closing the window offers Ask every time, Exit, or "
                    "Minimize to Tray, and governs the titlebar X, Alt+F4 and Exit "
                    "together. Ask every time only actually asks when there is "
                    "something to lose, and names what is at stake."
                ),
                keys=("Ctrl+,",),
                hear=(
                    "An episode is playing and 2 downloads are in progress -- "
                    "when there is something to lose."
                ),
            ),
        ),
        closing=(
            "One shared default, overridden per show only where a show genuinely "
            "differs. Most people set three things globally and two things on one "
            "podcast, forever."
        ),
        then=("private-and-local",),
    ),
    Tutorial(
        slug="private-and-local",
        title="Private feeds, and audio of your own",
        track="yours",
        minutes=5,
        surfaces=("QUILL Cast", "Podcast Manager"),
        summary=(
            "Supporter feeds that need a password, and turning folders of your own "
            "audio into shows -- including folders Cast watches for you."
        ),
        steps=(
            Step(
                title="Subscribe to a feed that asks for a sign-in",
                body=(
                    "Add the feed exactly as any other. If it asks, a small Feed "
                    "Credentials window opens with focus on the username field; "
                    "enter what your provider gave you and the subscription carries "
                    "on. A wrong password reopens the dialog with your username "
                    "kept, and says so."
                ),
                keys=("Alt+S",),
                hear="The show subscribed, or the sign-in failing with the reason.",
            ),
            Step(
                title="Change or clear it later",
                body=(
                    "Feed Credentials on the show's context menu is the same "
                    "dialog, username prefilled. Clear Credentials removes both and "
                    "makes the show public-only again. Every save and clear is "
                    "announced."
                ),
                keys=("Shift+F10",),
                hear="Saved, or cleared.",
            ),
            Step(
                title="Know where the password lives",
                body=(
                    "Never in a plain file: Windows Credential Manager on an "
                    "installed copy, DPAPI-encrypted inside the data folder on a "
                    "portable one. It is never in podcasts.json, never in logs, and "
                    "Export OPML never includes it -- an exported subscription list "
                    "is always safe to share."
                ),
                hear="Nothing: this is the promise behind the dialog.",
                note=(
                    "One deliberate rule: credentials are only ever sent to the "
                    "same host as the feed. If a show serves its audio from a "
                    "different host, those requests carry no credentials."
                ),
            ),
            Step(
                title="Turn your own audio into a show",
                body=(
                    "Add Local Podcast makes a folder of your own audio into a "
                    "podcast -- an audiobook you own, a course, recordings a friend "
                    "sent. It gets episodes, positions and everything else a "
                    "subscribed show has."
                ),
                keys=("Alt+S",),
                hear="The local show added, and how many files it found.",
            ),
            Step(
                title="Have it watch a folder",
                body=(
                    "A watched folder picks up files you drop into it. Scan Watched "
                    "Folders runs the check now. It is the shape to use for "
                    "anything that arrives regularly by a route Cast cannot "
                    "subscribe to."
                ),
                keys=("Alt+S",),
                hear="How many new files it picked up.",
            ),
        ),
        closing=(
            "A private feed and a folder of your own both end up as ordinary "
            "shows -- same keys, same queue, same statistics."
        ),
        then=("keep-it-safe",),
    ),
    Tutorial(
        slug="keep-it-safe",
        title="Back it up, move it, and fix it",
        track="yours",
        minutes=6,
        surfaces=("QUILL Cast",),
        summary=(
            "The backup you will be glad of exactly once, the readable export, "
            "the media-tool check, and where to look when something has gone "
            "wrong."
        ),
        steps=(
            Step(
                title="Back up the whole library",
                body=(
                    "Back Up My Podcasts writes subscriptions, folders, playlists, "
                    "positions, notes, statistics, your Go To order and your "
                    "bookmarks into one file. It offers to include downloaded "
                    "episodes and defaults to leaving them out: they can be tens of "
                    "gigabytes and can always be fetched again, where the 40 KB "
                    "beside them cannot."
                ),
                command="app.backup",
                hear="The file written, and what went into it.",
            ),
            Step(
                title="Restore one, knowing what you are restoring",
                body=(
                    "Restore tells you when the backup was made and how many "
                    "podcasts are in it before it does anything, because the two "
                    "ways to get this wrong are restoring the wrong file and "
                    "restoring a six-month-old one."
                ),
                command="app.restore",
                hear="The backup's date and size, before anything changes.",
            ),
            Step(
                title="Take a readable copy",
                body=(
                    "Export My Data writes everything Cast knows about your "
                    "listening to one readable JSON file -- subscriptions, folders, "
                    "the queue, playlists, notes, statistics, recently played. "
                    "Export OPML covers subscriptions and nothing else; this covers "
                    "the rest."
                ),
                command="podcasts.export_data",
                hear="The file written, and where.",
            ),
            Step(
                title="Move to another machine",
                body=(
                    "Export My Setup writes one file carrying your subscriptions, "
                    "folders, playlists, settings, Go To order, Quick Action order "
                    "and bookmarks; Import My Setup puts them on the other machine. "
                    "Passwords are not in it, and the confirmation says so."
                ),
                command="app.export_setup",
                hear="What the file holds, named, before anything is written.",
            ),
            Step(
                title="Check the media tools",
                body=(
                    "Cast needs FFmpeg for four things -- trimming silence, "
                    "evening out volume, working out chapters, and Sound "
                    "Enhancements. All four fail by producing a plausible result, "
                    "which is why Media Tools answers the question whenever you "
                    "ask, including when the answer is good news."
                ),
                command="app.media_tools",
                hear="Each tool, present or missing, and what its absence costs.",
            ),
            Step(
                title="Find what went wrong while you were elsewhere",
                body=(
                    "Recent Problems lists what has failed recently -- feeds that "
                    "could not be read, downloads that died -- each with its reason "
                    "and the time. It exists because a spoken failure you missed "
                    "used to be gone for good."
                ),
                command="app.recent_problems",
                hear="The failures, newest first, each with its reason.",
            ),
            Step(
                title="Take back the last destructive thing",
                body=(
                    "Undo Last Action brings back the last thing you removed: an "
                    "unsubscribe, a Remove All Episodes, a Mark All as Played. It "
                    "says what it brought back, and it is one step rather than a "
                    "stack, on purpose."
                ),
                command="app.undo_last",
                keys=("Ctrl+Z",),
                hear="Undid, and what came back -- or Nothing to undo.",
            ),
        ),
        closing=(
            "One backup file and one setup file. Between them, nothing you have "
            "built here is difficult to get back."
        ),
    ),
)
