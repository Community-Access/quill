"""QUILL Cast, track 2: keeping up -- the first five of its seven lessons.

Playing an episode is easy; deciding which of the four hundred waiting ones to
play is the hard part, and the Inbox, the Play Queue, downloads and playlists
are one system that only makes sense together. Your own audio sits here too,
because a watched folder is one more way new episodes arrive -- they just come
from your own disk.

The track's last two lessons, Episode Filters and schedules, are rules you set
for one podcast at a time, so they live in :mod:`.per_podcast` beside the
other per-podcast lessons. The catalogue orders by track, so they still come
last in this one.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="the-inbox",
        title="The Inbox",
        track="keeping-up",
        minutes=8,
        surfaces=("QUILL Cast", "Notifications"),
        summary=(
            "Choose which podcasts send new episodes to the Inbox, then sort "
            "through it like the morning post. Put some aside for later, keep it "
            "from piling up, and catch a new episode straight from its notice."
        ),
        steps=(
            Step(
                title="Check for anything new",
                body=(
                    "Refresh All Now asks every podcast you follow whether it has "
                    "anything new. Cast tells you how many it is checking, and the "
                    "answers come in one podcast at a time. When you ask, Cast always "
                    "answers, even if nothing is new."
                ),
                keys=("F5",),
                hear="How many podcasts it is checking, then what arrived.",
            ),
            Step(
                title="Choose what goes to the Inbox",
                body=(
                    "Nothing goes to the Inbox until you say so, one podcast at a "
                    "time. On a podcast, open its menu and choose Route New Episodes "
                    "to Inbox. The same row then reads Stop Routing to Inbox, to turn "
                    "it off again."
                ),
                keys=("Shift+F10",),
                hear="The podcast's menu, then Cast confirming the change.",
                note=(
                    "Would you rather have nearly everything in the Inbox? In "
                    "Preferences, under The Inbox, choose Every podcast except the ones "
                    "I mark."
                ),
            ),
            Step(
                title="Open the Inbox",
                body=(
                    "The Inbox holds the unheard episodes of the podcasts you send "
                    "there. When Cast opens and something is waiting, this is where "
                    "it puts you, and the window title tells you how many."
                ),
                command="podcasts.inbox",
                keys=("Ctrl+Shift+I",),
                hear="Inbox, then the first waiting episode.",
            ),
            Step(
                title="Decide about each episode",
                body=(
                    "The Inbox is for deciding. Enter plays an episode now, Space "
                    "adds it to the Play Queue, and Delete takes it out of the Inbox. "
                    "Do not worry: nothing you do here removes an episode from your "
                    "library. One you delete is still there, unheard, in its podcast."
                ),
                keys=("Enter", "Space", "Delete"),
                hear="Added to the Play Queue, or what Delete did.",
                check="queue-grew",
            ),
            Step(
                title="Put one aside for later",
                body=(
                    "A long interview for the weekend? Open its menu and choose File "
                    "to Inbox Folder, then pick a folder or type a new name. Cast "
                    "remembers, and files that podcast's later episodes there too. "
                    "View, Inbox Folder looks in one folder."
                ),
                keys=("Shift+F10", "Ctrl+Shift+O"),
                hear="The folder the episode went to.",
            ),
            Step(
                title="Clear the lot when you start fresh",
                body=(
                    "Back on the Places list, the Applications key on the Inbox "
                    "offers Mark All as Played. Cast asks first, and the question "
                    "starts on No. The episodes stay in your library."
                ),
                keys=("Applications",),
                hear="Cast asking first, then how many it marked.",
            ),
            Step(
                title="Keep the Inbox from piling up",
                body=(
                    "In Preferences, under The Inbox, keep at most a number of "
                    "episodes, or drop ones older than a few hours up to two weeks. "
                    "Trimming never deletes anything, and episodes you started, "
                    "queued or filed are never trimmed."
                ),
                keys=("Ctrl+,",),
                hear="The Inbox section of Preferences.",
                note=(
                    "Any podcast can have its own limits in Settings for This "
                    "Podcast, so a daily news show keeps three while a weekly one "
                    "keeps everything."
                ),
            ),
            Step(
                title="Catch a new episode from its notice",
                body=(
                    "Notifications keeps what Cast has told you, newest first, so the "
                    "episode that arrived while you were in your email is still "
                    "there. On a new-episode notice, Ctrl+Enter plays it straight "
                    "away and Space adds it to the Play Queue."
                ),
                keys=("Ctrl+Shift+N", "Ctrl+Enter", "Space"),
                hear="The newest notice, then the episode playing or queued.",
                check="playing",
            ),
        ),
        closing=(
            "Empty the Inbox each morning and nothing slips past you. Next comes "
            "the Play Queue, where the keepers go."
        ),
        then=("the-play-queue",),
    ),
    Tutorial(
        slug="the-play-queue",
        title="The Queue",
        track="keeping-up",
        minutes=7,
        surfaces=("Play Queue", "Save Lineup", "QUILL Cast"),
        summary=(
            "Fill the Play Queue, play one next, and move through it while it "
            "plays. You will also hear what is coming before it starts, save the "
            "order as a lineup, and get back an episode that waited too long."
        ),
        steps=(
            Step(
                title="Add to the end of the queue",
                body=(
                    "Space on any episode, in any list, adds it to the end of the "
                    "Play Queue. For several at once, select them with Shift and the "
                    "arrows, or Ctrl+Space one at a time, then press Space."
                ),
                keys=("Space", "Ctrl+Space"),
                hear="Added to the Play Queue.",
                check="queue-grew",
            ),
            Step(
                title="Play one next",
                body=(
                    "Shift+Space puts an episode straight after the one that is "
                    "playing, ahead of everything else in the queue. Play Next on an "
                    "episode's menu does the same."
                ),
                keys=("Shift+Space",),
                hear="Cast saying the episode plays next.",
            ),
            Step(
                title="Look at what is lined up",
                body=(
                    "The Play Queue place shows what plays next, in order. Delete "
                    "takes an episode out of the queue; it stays in your library. "
                    "The Applications key on the place offers Clear Entire Queue and "
                    "Play Queue Shuffled."
                ),
                keys=("Ctrl+Shift+Q", "Delete"),
                hear="Play Queue, then the episode at the front.",
            ),
            Step(
                title="Move through it while it plays",
                body=(
                    "From anywhere in Cast, Next in Queue skips to the next episode "
                    "and Previous in Queue goes back one. Mark as Played and Next "
                    "finishes this one for good and moves on, which is handy when "
                    "you have heard enough of the news."
                ),
                command="podcasts.next_in_queue",
                keys=("Ctrl+Alt+Down", "Ctrl+Alt+Up", "Ctrl+Alt+Shift+Down"),
                hear="The next episode's title, then its audio.",
            ),
            Step(
                title="Hear what is up next",
                body=(
                    "Just listen. About ten seconds before an episode ends, Cast tells "
                    "you what comes next. It names the podcast only when it changes, "
                    "says nothing when nothing will follow, and stays quiet during "
                    "Quiet Hours. You do not have to press anything."
                ),
                hear="Next:, then the episode, and the podcast if it changes.",
                note=(
                    "Turn it off with Say what is up next before an episode ends, in "
                    "Preferences under Telling you."
                ),
            ),
            Step(
                title="Send a podcast straight to the queue",
                body=(
                    "For a podcast you never skip, choose Auto-Queue New Episodes on "
                    "its menu. Its new episodes go straight into the Play Queue when "
                    "they arrive and skip the Inbox. Stop Auto-Queueing New Episodes "
                    "turns it off."
                ),
                keys=("Shift+F10",),
                hear="Cast confirming new episodes will be queued.",
            ),
            Step(
                title="Save the order as a lineup",
                body=(
                    "Arrange the queue the way you like it, then choose Save Lineup "
                    "from the Applications key on the Play Queue place and give it a "
                    "name, such as Tuesday. Next Tuesday, Apply Lineup moves its "
                    "unheard episodes to the front in your order."
                ),
                keys=("Applications",),
                hear="The lineup saved; later, how many it applied and skipped.",
            ),
            Step(
                title="Get back what waited too long",
                body=(
                    "Queue Expiry, on a podcast's menu, takes its old episodes out of "
                    "the queue after a day or a week. An expired episode is not "
                    "deleted: it waits in Recently Expired, hidden until you show it "
                    "in View, Places. Restore to the Play Queue brings it back."
                ),
                keys=("Ctrl+Shift+X",),
                hear="Recently Expired, then the episodes waiting there.",
            ),
        ),
        closing=(
            "Fill the queue in the morning and Cast plays one episode after another "
            "until it runs out. Next, let's play audio that is not a podcast at all."
        ),
        then=("your-own-audio", "downloads-and-space"),
    ),
    Tutorial(
        slug="your-own-audio",
        title="Your own audio",
        track="keeping-up",
        minutes=7,
        surfaces=("Watched Folders", "Watched Folder Settings", "QUILL Cast"),
        summary=(
            "Play your own recordings, audiobooks and lectures with every key you "
            "already know. Then let Cast watch a folder, so anything you put there "
            "turns up in Personal Audio by itself."
        ),
        steps=(
            Step(
                title="Add some files",
                body=(
                    "Add Personal Audio, on the Podcasts menu, takes one or more "
                    "audio files -- MP3, M4B, M4A, WAV, FLAC or OGG -- and a name for "
                    "the collection. Each file becomes an episode, and Cast keeps its "
                    "own copy, so moving the originals does no harm."
                ),
                keys=("Ctrl+Alt+L",),
                hear="The collection added, by name.",
            ),
            Step(
                title="Find them in Personal Audio",
                body=(
                    "Personal Audio is a place like any other. Your collections work "
                    "just like a podcast: the same keys, the same bookmarks, and Cast "
                    "remembers your place in each file."
                ),
                command="podcasts.personal_audio",
                keys=("Ctrl+Shift+U",),
                hear="Personal Audio, then your collection.",
            ),
            Step(
                title="Open Watched Folders",
                body=(
                    "Maybe your voice recorder copies its files to a folder, or your "
                    "audiobooks always download to the same place. Tell Cast about "
                    "that folder once, and anything that lands there arrives in "
                    "Personal Audio by itself."
                ),
                keys=("Ctrl+Alt+W",),
                hear="Watched Folders, then your folders, or that there are none yet.",
            ),
            Step(
                title="Add a folder",
                body=(
                    "Press Add Folder and choose the folder the way you would anywhere "
                    "in Windows. A settings page opens for it. The choices it starts "
                    "with are good ones, so you can press Save straight away. Cast "
                    "takes a first look right then."
                ),
                keys=("Alt+A",),
                hear="Cast saying it is watching the folder, then anything already there.",
            ),
            Step(
                title="Decide what happens to each file",
                body=(
                    "First, what to do with the original file: leave it where it is, "
                    "move it into Cast's folder, or play it from where it is. New "
                    "arrivals can also join the Play Queue. Tell me chooses how much "
                    "Cast says. Files shorter than 30 seconds are skipped to begin with."
                ),
                keys=("Alt+O", "Alt+A", "Alt+T", "Alt+I"),
                hear="Each choice, and what it is set to.",
                note=(
                    "Each folder can have its own speed, and Each subfolder is its "
                    "own group turns a folder of audiobooks into one group per book."
                ),
            ),
            Step(
                title="Hear something arrive",
                body=(
                    "Now try it. Copy a recording into the folder, and within a few "
                    "seconds Cast tells you about it. A file still being copied is "
                    "left alone until it has finished, and the same recording never "
                    "arrives twice, even if you rename it."
                ),
                hear="New in, the folder's name, then the file and its length.",
            ),
            Step(
                title="Look again, rest it, or stop watching",
                body=(
                    "In Watched Folders, Scan Now looks at a folder straight away, "
                    "Pause or Resume stops watching for a while, and Remove stops for "
                    "good. Remove asks first. The files Cast already brought in stay, "
                    "and nothing in the folder is touched."
                ),
                keys=("Alt+N", "Alt+U", "Alt+M"),
                hear="What Cast did; for Remove, a question that starts on No.",
            ),
        ),
        closing=(
            "A watched folder is a way in, not a mirror, so deleting a file from it "
            "never deletes the episode. Cast also looks at every folder when it "
            "opens and when your computer wakes."
        ),
        then=("downloads-and-space",),
    ),
    Tutorial(
        slug="downloads-and-space",
        title="Downloads, and the disk they live on",
        track="keeping-up",
        minutes=6,
        surfaces=("Downloads", "QUILL Cast"),
        summary=(
            "Download an episode, keep one you are streaming, and pause what is "
            "downloading. Then let Cast fetch the newest for you, and keep your "
            "disk from filling up."
        ),
        steps=(
            Step(
                title="Download one episode",
                body=(
                    "Every episode plays straight from the internet, so you never have "
                    "to download. A download is a copy on your computer, for when you "
                    "are offline or on a slow connection. Download Episode is on the "
                    "episode's menu, and Remove Downloaded Copy appears once it is here."
                ),
                keys=("Shift+F10",),
                hear="Downloading, then the episode's title.",
            ),
            Step(
                title="Keep what you are streaming",
                body=(
                    "Started streaming something you now want to keep? Keep This "
                    "Episode, on the Episode menu, keeps it as a download, often "
                    "without fetching it again."
                ),
                keys=("Ctrl+Alt+K",),
                hear="Cast saying it is keeping the episode.",
            ),
            Step(
                title="See what is downloaded",
                body=(
                    "The Downloads place holds the episodes kept on this computer and "
                    "the ones on their way. Delete there removes the file, but the "
                    "episode stays, and you can still stream it."
                ),
                command="podcasts.downloads",
                keys=("Ctrl+D",),
                hear="Downloads, then the first episode kept on this computer.",
            ),
            Step(
                title="Pause and resume everything",
                body=(
                    "Need the internet for something else for a while? The Downloads "
                    "menu pauses every download at once, and resumes them again, from "
                    "anywhere in Cast. If a connection drops halfway, Cast reconnects "
                    "and picks up where it stopped."
                ),
                keys=("Ctrl+Alt+Shift+U", "Ctrl+Alt+Shift+V"),
                hear="All downloads paused, or resumed.",
            ),
            Step(
                title="Let Cast fetch the newest for you",
                body=(
                    "In Preferences, under Fetching, Automatically download keeps the "
                    "newest episodes of each podcast ready for you: none, the newest "
                    "1, 3, 5 or 10, or every episode. Another choice there decides "
                    "whether this happens on a metered connection."
                ),
                keys=("Ctrl+,",),
                hear="The Fetching section, then what changed when you save.",
            ),
            Step(
                title="Keep the disk in check",
                body=(
                    "In Preferences, under Data, you can have downloads deleted after "
                    "a number of days, and set a limit on how much space they use. "
                    "Neither ever removes an episode in your queue or one you are "
                    "partway through."
                ),
                keys=("Ctrl+,",),
                hear="The Data section of Preferences.",
                note=(
                    "Never delete this podcast's downloads, in Settings for This "
                    "Podcast, protects one podcast from every cleanup."
                ),
            ),
            Step(
                title="Tidy up now",
                body=(
                    "Free Up Space applies those rules now and tells you how much "
                    "space came back. Run Housekeeping Now does the whole tidy-up at "
                    "once, the queue, the Inbox and your downloads, and tells you what "
                    "it did in one sentence."
                ),
                command="podcasts.free_space",
                keys=("Ctrl+Alt+F", "Ctrl+Alt+H"),
                hear="How much space came back.",
            ),
        ),
        closing=(
            "Downloads are there when you want them, never because you must. "
            "Every episode streams, and a removed file can always be fetched again."
        ),
        then=("playlists",),
    ),
    Tutorial(
        slug="playlists",
        title="Playlists and smart playlists",
        track="keeping-up",
        minutes=5,
        surfaces=("Smart Playlist Rules", "QUILL Cast"),
        summary=(
            "Make a playlist you fill by hand, like a mixtape, and a smart playlist "
            "that fills itself from a few rules you choose, such as anything under "
            "half an hour that you have not heard."
        ),
        steps=(
            Step(
                title="Go to Playlists",
                body=(
                    "Playlists is a place. Enter opens a playlist right there in the "
                    "same list, and Backspace brings you back to the list of "
                    "playlists. Lineups you saved from the Play Queue live here too."
                ),
                keys=("Ctrl+Shift+Y",),
                hear="Playlists, then the first playlist.",
            ),
            Step(
                title="Start with the starters",
                body=(
                    "The easiest way in is to borrow some. The Applications key on "
                    "the Playlists place offers Add Starter Playlists: five ready-made "
                    "smart playlists, such as Quick Listens and New This Week. Open one "
                    "with Edit Rules to see how it works, then change it or delete it."
                ),
                keys=("Applications",),
                hear="The starter playlists, in the list.",
            ),
            Step(
                title="Make one by hand",
                body=(
                    "New Playlist, on the same menu, makes an empty one. Then choose "
                    "Add to Playlist on any episode's menu and pick it. Select several "
                    "episodes first to add them all at once."
                ),
                keys=("Applications", "Shift+F10"),
                hear="The playlist named, then each episode added.",
            ),
            Step(
                title="Write a smart playlist",
                body=(
                    "New Smart Playlist asks for a name, then the rules: which "
                    "podcasts, the episode status, how recent, the shortest and "
                    "longest length, and words in the title or notes. Leave a number "
                    "at 0 if you do not mind. As you go, Cast tells you how many "
                    "episodes match."
                ),
                keys=("Alt+S", "Alt+D", "Alt+M", "Alt+X"),
                hear="How many episodes match, as you change each rule.",
            ),
            Step(
                title="Change one later",
                body=(
                    "On a playlist's own row, the menu offers Open, Edit Rules for a "
                    "smart one, Rename Playlist and Delete Playlist. Delete on the row "
                    "does the same, and Cast asks first."
                ),
                keys=("Shift+F10", "Delete"),
                hear="The playlist's menu.",
            ),
        ),
        closing=(
            "A smart playlist keeps itself up to date, so the one you make today is "
            "still right next month, without you touching it."
        ),
        then=("episode-filters",),
    ),
)
