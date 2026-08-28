"""QUILL Cast, track 1: your first hour.

Four lessons. Subscribe to something, play it, learn the keys that work while
it is playing, and meet the Podcast Manager -- which is where episode-level
life happens and where most people never go until somebody shows them.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="first-podcast",
        title="Subscribe to your first podcast",
        track="first-hour",
        minutes=6,
        surfaces=("QUILL Cast", "Add Podcast"),
        summary=(
            "Four ways in -- search, a feed address, an OPML file from another "
            "app, or ACB Media's whole directory in one step -- and then the "
            "two-keystroke loop that plays what you follow."
        ),
        steps=(
            Step(
                title="Start where the app puts you",
                body=(
                    "QUILL Cast opens with focus in the Library tree. On a fresh "
                    "installation it holds only the pinned views -- Favorites, New "
                    "Episodes, Continue Listening, the Inbox -- and no shows. That "
                    "is what the next few minutes are for."
                ),
                hear="Library, tree -- and the first pinned view.",
            ),
            Step(
                title="Search for a show by name",
                body=(
                    "Add Podcast searches by name and subscribes from the result. "
                    "The results list can show the feed address as a column, which "
                    "is what tells two shows with the same name apart."
                ),
                keys=("Alt+S",),
                hear="A search box, then the matching shows.",
                check="subscriptions-grew",
            ),
            Step(
                title="Or paste a feed address",
                body=(
                    "The same window has an Add by Feed URL field. Use it when "
                    "somebody sent you a link, or when a show is too obscure for a "
                    "directory to list -- a church, a school, a members-only feed."
                ),
                keys=("Tab", "Enter"),
                hear="The show subscribed, by name.",
                note=(
                    "If the feed asks for a sign-in, a small Feed Credentials "
                    "window opens with focus in the username field. Enter what your "
                    "provider gave you and the subscription carries on normally."
                ),
            ),
            Step(
                title="Or bring a whole library across",
                body=(
                    "Import OPML takes the subscription list any other podcast app "
                    "exports. It is the fastest way to move in, and Export OPML is "
                    "how you leave -- which is the same promise read backwards."
                ),
                keys=("Alt+S",),
                hear="How many shows it imported.",
            ),
            Step(
                title="Or take ACB Media's whole directory",
                body=(
                    "Subscribe to ACB Media Podcasts adds ACB's live directory in "
                    "one step -- no search, no addresses, no account. Worth knowing "
                    "about before you go hunting for the shows one at a time."
                ),
                keys=("Alt+S",),
                hear="How many shows it added.",
            ),
            Step(
                title="Play what you follow",
                body=(
                    "Arrow to a show in the Library tree and press Enter: it plays "
                    "that show's next unplayed episode. No detour through the "
                    "Manager. If every episode is already played it plays the most "
                    "recent one and says so."
                ),
                keys=("Down arrow", "Enter"),
                hear="The episode's title, then the audio.",
                check="playing",
            ),
            Step(
                title="Reach one particular episode",
                body=(
                    "Right arrow expands a show into its episodes, newest first, "
                    "right where the show sits. Enter on an episode plays that one. "
                    "Shows start collapsed so the tree reads as a list of shows "
                    "rather than a wall of episodes."
                ),
                keys=("Right arrow", "Enter"),
                hear="Each episode row, then the one you chose playing.",
            ),
            Step(
                title="Make it an appliance",
                body=(
                    "Resume Last Episode on Launch picks up exactly where you left "
                    "off the moment the app opens. Tick it once and launching QUILL "
                    "Cast becomes the whole gesture."
                ),
                keys=("Alt+S",),
                hear="The setting read back.",
            ),
        ),
        closing=(
            "One show, one Enter. Everything after this is about doing more with "
            "less searching -- and about what happens to episodes you have not "
            "got to yet."
        ),
        then=("play-and-move", "the-manager"),
    ),
    Tutorial(
        slug="play-and-move",
        title="Work the player",
        track="first-hour",
        minutes=6,
        surfaces=("QUILL Cast",),
        summary=(
            "Play, pause, skip, speed, chapters and the readout that tells you "
            "everything about what is playing -- all from the keyboard, and all "
            "from whichever window you are standing in."
        ),
        steps=(
            Step(
                title="Play and pause",
                body=(
                    "One transport control that is never dead: the button reads "
                    "Play when nothing is on, Pause while playing and Resume while "
                    "paused, and the key does whichever of those is true."
                ),
                command="podcasts.transport.play_pause",
                keys=("Ctrl+P",),
                hear="Playing, or Paused -- so you never have to guess which way the toggle went.",
                check="playing",
            ),
            Step(
                title="Skip by a fixed amount",
                body=(
                    "Skip Forward and Skip Back jump by a set number of seconds -- "
                    "30 forward and 15 back to begin with. That asymmetry is "
                    "deliberate: forward is for skipping an advert, back is for the "
                    "sentence you missed."
                ),
                keys=("Ctrl+Right", "Ctrl+Left"),
                hear="The new position.",
            ),
            Step(
                title="Change the speed, and hear whose it is",
                body=(
                    "Speed moves in tenths anywhere from 0.5x to 5.0x, and says "
                    "both the new speed and whose it is: the playing podcast's own "
                    "if something is playing, or the shared default when nothing "
                    "is. Speed is per show, because hosts talk at different rates."
                ),
                command="podcasts.speed_up",
                keys=("Ctrl+Shift+Up", "Ctrl+Shift+Down", "Ctrl+Shift+0"),
                hear="1.6x for The Daily -- the number and the show it belongs to.",
            ),
            Step(
                title="Move by chapter",
                body=(
                    "Next Chapter and Previous Chapter jump to the nearest marker "
                    "rather than by a fixed time. On a show with sponsor reads "
                    "marked, that is the difference between skipping an advert and "
                    "guessing at thirty seconds."
                ),
                keys=("Alt+E",),
                hear="The chapter you landed in, by name.",
            ),
            Step(
                title="Ask everything about what is playing",
                body=(
                    "Player Information puts it all in one read-only field you can "
                    "arrow through and copy: title, show, position, duration, time "
                    "remaining, percentage, speed, whether it is streaming or a "
                    "file, how many notes it has, where it will resume, and which "
                    "chapter you are in. A spoken status goes past once; this stays."
                ),
                keys=("Alt+E",),
                hear="The whole readout, as text you can review.",
            ),
            Step(
                title="Stop after this one",
                body=(
                    "Stop After This Episode is a one-off: it stops instead of "
                    "auto-advancing, clears itself when it fires, and never "
                    "survives a restart. A standing preference that outlived the "
                    "reason for it would be a mystery next week."
                ),
                command="podcasts.stop_after_episode",
                hear="Stopping after this episode.",
            ),
            Step(
                title="Use the Winamp letters if you know them",
                body=(
                    "If you came to Windows audio through Winamp, its classic-skin "
                    "letters work here on the keys you already know -- and they can "
                    "be turned off in Preferences if you would rather type a letter "
                    "to jump through a list."
                ),
                keys=("X", "C", "V", "B", "Z"),
                hear="Each one saying what it did.",
            ),
        ),
        closing=(
            "The volume keys match Quill Radio's on purpose: the two apps are "
            "meant to feel like one keyboard."
        ),
        then=("the-manager",),
    ),
    Tutorial(
        slug="the-manager",
        title="Meet the Podcast Manager",
        track="first-hour",
        minutes=7,
        surfaces=("Podcast Manager", "QUILL Cast"),
        summary=(
            "Where episode-level life happens: the four pinned views, the episode "
            "list and its filters, and a search that reaches your notes and "
            "transcripts as well as titles."
        ),
        steps=(
            Step(
                title="Open it",
                body=(
                    "The Manager is one window holding the whole library: a tree on "
                    "one side, episodes on the other. Everything you can do to an "
                    "episode is reachable here, which is why it has a key of its "
                    "own rather than living behind a menu."
                ),
                keys=("Ctrl+M",),
                hear="Entered the Podcast Manager.",
            ),
            Step(
                title="Learn the four pinned views",
                body=(
                    "Favorites, New Episodes, Continue Listening and the Inbox lead "
                    "the tree, above your own folders. They are questions rather "
                    "than places: what do I like, what is new, what did I start, "
                    "what have I not triaged."
                ),
                keys=("Down arrow",),
                hear="Each view, with what it holds.",
            ),
            Step(
                title="Rename a view to what you call it",
                body=(
                    "F2 on any pinned view gives it your own name, and it follows "
                    "you into the main window too. A renamed view's menu gains "
                    "Reset Name. Shows and episodes deliberately refuse F2: their "
                    "names come from the feed."
                ),
                keys=("F2",),
                hear="The view under your name for it.",
            ),
            Step(
                title="Filter the episode list",
                body=(
                    "All, Unplayed, Played, Downloaded, Not downloaded -- and In "
                    "progress, the ones you started and did not finish. That last "
                    "one is the filter people ask for and rarely find."
                ),
                keys=("Tab",),
                hear="The filter, then how many episodes it left.",
            ),
            Step(
                title="Decide how cross-show lists read",
                body=(
                    "View cross-show lists as offers three shapes for the Inbox, "
                    "New Episodes, Continue Listening and Favorites: grouped in "
                    "list (each show's episodes together), flat (one stream by "
                    "date), or folders per podcast (real expandable nodes)."
                ),
                hear="The shape you chose, and the list rebuilt.",
            ),
            Step(
                title="Search everything at once",
                body=(
                    "Search Everywhere reaches shows, episodes, your own notes and "
                    "fetched transcripts, and jumps to the result. Emptying the box "
                    "empties the results at once, so a stale match for a query you "
                    "have deleted never sits there looking current."
                ),
                hear="How many matches, across which kinds of thing.",
                note=(
                    "Press Down arrow in the search box for your last fifteen "
                    "searches, newest first. The list stays on this machine: "
                    "nothing about what you search for leaves it."
                ),
            ),
            Step(
                title="Do something to a whole show",
                body=(
                    "A show's context menu holds the heavy verbs: Download All "
                    "Episodes, Remove All Downloads (the files, and only the "
                    "files), Remove All Episodes, Mark All as Played, Settings for "
                    "This Podcast, and Unsubscribe."
                ),
                keys=("Shift+F10",),
                hear="Each action, and its confirmation when it needs one.",
            ),
        ),
        closing=(
            "The main window is for playing what you follow; the Manager is for "
            "everything else. Most people need it once a week and are glad it is "
            "one key away."
        ),
        then=("what-is-new",),
    ),
)
