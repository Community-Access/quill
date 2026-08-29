"""Track 5, first half: podcasts, books, and YouTube.

All three arrive through the same tree, play with the same keys and favorite
the same way -- which is the point of the track. What differs is what each
source will let you keep, and each lesson says so plainly rather than leaving
you to discover it at the moment you press Download.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="follow-a-podcast",
        title="Follow a podcast",
        track="beyond",
        minutes=8,
        surfaces=("Browse Stations",),
        summary=(
            "Find a show, subscribe to it, find what is unheard, read a transcript "
            "without playing anything, and know where the line between Quill Radio "
            "and QUILL Cast falls."
        ),
        steps=(
            Step(
                title="Open a podcast directory",
                body=(
                    "Two branches of the browse tree list shows: Podcasts (Apple), "
                    "which is a country's storefront plus Apple's whole genre tree, "
                    "and Podcast Index, which is the open directory. Neither needs "
                    "a key, an account or a sign-in at any step."
                ),
                command="radio.browse",
                hear="The branch, then its countries or categories.",
                check="window:Browse Stations",
            ),
            Step(
                title="Look at a show without committing to it",
                body=(
                    "Open a show and its episodes are simply there: play one, "
                    "favorite it, download it, read its transcript. You do not have "
                    "to subscribe to listen, which is how you decide whether to."
                ),
                keys=("Right arrow", "Enter"),
                hear="The episodes, newest first.",
            ),
            Step(
                title="Subscribe",
                body=(
                    "Subscribe to This Podcast, on the show's own menu, files it in "
                    "the shared podcast library -- the same library QUILL Cast "
                    "reads, so the show is simply there the next time Cast opens. "
                    "On a show you already follow the same slot reads Unsubscribe."
                ),
                keys=("Shift+F10",),
                hear="Subscribed, and the show's name.",
            ),
            Step(
                title="Find what you follow",
                body=(
                    "The Podcasts branch leads with a Subscriptions folder -- one "
                    "folder per show, each expanding to its newest episodes. The "
                    "folder wears your follow count, and each show wears its "
                    "unheard count, the same count Cast shows."
                ),
                keys=("Home", "Right arrow"),
                hear="Subscriptions, with a number, then each show with its unheard count.",
                note=(
                    "How many episodes each show lists is a preference -- 25 newest "
                    "by default. It is deliberately Quill Radio's only podcast "
                    "setting; the full archive lives in Cast."
                ),
            ),
            Step(
                title="Ask every show at once",
                body=(
                    "Check All Feeds Now, on the Subscriptions branch, asks every "
                    "subscribed show for new episodes in one go -- including shows "
                    "you have paused, because a pause means leave this show alone, "
                    "not put it out of reach."
                ),
                keys=("Shift+F10",),
                hear="What it found, counted and named -- or nothing at all if there was nothing.",
                note=(
                    "Preferences can have Radio ask on its own, from every 15 "
                    "minutes to once a day, and at launch. Both start off: an app "
                    "that reaches the network on a schedule nobody chose is "
                    "spending somebody else's data allowance."
                ),
            ),
            Step(
                title="Read an episode instead of playing it",
                body=(
                    "An episode whose feed publishes a transcript says transcript "
                    "available on its row, and View Transcript opens it in the "
                    "reader without playing anything. That is the fastest way to "
                    "check whether an hour-long episode is about what you hoped."
                ),
                keys=("Shift+F10",),
                hear="The transcript window, with the episode's title at the top.",
            ),
            Step(
                title="Do the housekeeping",
                body=(
                    "A show's menu carries Move to Folder, Mark All as Played, "
                    "Download All Episodes and Remove All Downloads. Each dims with "
                    "its own reason when there is nothing to do -- nothing to mark, "
                    "all 63 episodes are already played."
                ),
                keys=("Shift+F10",),
                hear="The action's confirmation, and the badges clearing.",
            ),
            Step(
                title="Hand an episode to QUILL Cast",
                body=(
                    "Play Next in QUILL Cast, Add to QUILL Cast Queue and Send to "
                    "the QUILL Cast Inbox are a handoff rather than an instant "
                    "change: Radio notes what you asked for and Cast carries it out "
                    "the next time it opens. The confirmation says so."
                ),
                keys=("Shift+F10",),
                hear="It will be next in the QUILL Cast queue -- the future tense is deliberate.",
            ),
            Step(
                title="Know where the line is",
                body=(
                    "Playback, downloads and per-episode actions work here exactly "
                    "as anywhere else in the tree. The rich side of podcasting -- "
                    "automatic downloads, retention, the play queue, the full "
                    "archive -- is QUILL Cast's job, and a serious podcast habit "
                    "belongs there."
                ),
                hear=(
                    "Nothing: this is the fact that saves you looking for a setting that is not "
                    "here."
                ),
            ),
        ),
        closing=(
            "Your place in an episode follows you between the two apps, and so do "
            "your bookmarks. Neither needs an account or a sync service."
        ),
        then=("books-and-free-music",),
    ),
    Tutorial(
        slug="books-and-free-music",
        title="Audiobooks, archives and free music",
        track="beyond",
        minutes=8,
        surfaces=("Browse Stations", "Downloads"),
        summary=(
            "Find a book, keep your place in it, download a whole one while you go "
            "on listening, and understand exactly which sources will let you save "
            "what -- and why the ones that will not, will not."
        ),
        steps=(
            Step(
                title="Find a book three ways",
                body=(
                    "LibriVox offers Recently Added, By Genre and By Author across "
                    "some seven thousand readers. Project Gutenberg Audiobooks "
                    "holds the 1,124 records that carry human-read audio. The "
                    "Internet Archive holds Old Time Radio, the Live Music Archive, "
                    "radio programmes and more."
                ),
                command="radio.browse",
                hear="The branch's own shelves.",
                check="window:Browse Stations",
                note=(
                    "There is deliberately no By Title in LibriVox: its catalogue "
                    "supports author, genre and date filters and no title filter in "
                    "any form, and a branch that quietly finds nothing is worse "
                    "than one that is not offered."
                ),
            ),
            Step(
                title="Open a book and play a chapter",
                body=(
                    "A book with chapters is a folder of chapters; a book that is "
                    "one single reading is simply playable. Enter plays, and every "
                    "transport key works -- including speed, chapters and Where Am "
                    "I, because unlike a live station a recording has a timeline."
                ),
                keys=("Right arrow", "Enter"),
                hear="The chapter playing, and its position when you ask.",
            ),
            Step(
                title="Stop, and come back tomorrow",
                body=(
                    "Quill Radio saves your place in anything with a timeline -- a "
                    "book chapter, an Old Time Radio episode, a podcast episode -- "
                    "and offers it back the next time you play. A few seconds in is "
                    "not a position and is not offered, and finishing something "
                    "clears its place so replaying starts at the beginning."
                ),
                hear="Picking up where you left off, and the time.",
            ),
            Step(
                title="Save a whole book at once",
                body=(
                    "Download All Files on a book's folder saves every chapter into "
                    "one folder, in order, while you carry on listening. It resumes "
                    "a part-finished file rather than starting again, one bad "
                    "chapter costs only that chapter, and stopping keeps everything "
                    "already saved."
                ),
                keys=("Shift+F10",),
                hear="The download queued, and how many files it holds.",
            ),
            Step(
                title="Watch the queue",
                body=(
                    "Everything you save goes through one queue, one at a time, in "
                    "the order you asked. The Downloads window shows what is "
                    "waiting, downloading, saved and failed, with Open Containing "
                    "Folder, per-row cancel and remove, and Clear Finished."
                ),
                keys=("Ctrl+Shift+J",),
                hear="Entered Downloads, then each row with its state.",
                check="window:Downloads",
                note=(
                    "Close the window with downloads still going and Quill Radio "
                    "either finishes them in the background or stops them -- "
                    "whichever you chose in Download Preferences -- and tells you "
                    "which it did."
                ),
            ),
            Step(
                title="Play a downloaded book as a book",
                body=(
                    "Its chapters are in proper order -- chapter 2 before chapter "
                    "10 -- and when one finishes the next starts on its own, "
                    "announcing where you are: 4 of 40. When the last chapter ends, "
                    "Quill Radio says so rather than simply going quiet."
                ),
                hear="The next chapter starting, with its number and the total.",
            ),
            Step(
                title="Learn what cannot be saved, and why",
                body=(
                    "Quill Radio offers Download only where the source's terms "
                    "clearly allow it, and asking anyway tells you which of four "
                    "reasons applies: a live station has no file to save (that is "
                    "what recording is for), Spotify is copy-protected, YouTube is "
                    "a deliberate exclusion, and for Audius the choice belongs to "
                    "the artist and is not stated in the listing."
                ),
                keys=("Shift+F10",),
                hear="The reason, named specifically rather than a general refusal.",
            ),
            Step(
                title="Find music that is genuinely free",
                body=(
                    "Audius gives you trending overall and within 27 genres, and "
                    "drops pay-gated tracks rather than listing them and refusing. "
                    "ccMixter is Creative Commons by tag, each track's licence on "
                    "its own row. A Creative Commons track you save is written with "
                    "its licence in a text file beside it."
                ),
                hear="The track, and its licence spoken as part of the row.",
                note=(
                    "Mixcloud is metadata only: Quill Radio never extracts a "
                    "Mixcloud stream, so activating a show opens it in your "
                    "browser -- and the row says so before you press Enter."
                ),
            ),
        ),
        closing=(
            "Books, archives and free music behave like every other row in the "
            "tree. The only thing that changes source to source is what you are "
            "allowed to keep, and the app says which every time."
        ),
        then=("youtube-without-an-account",),
    ),
    Tutorial(
        slug="youtube-without-an-account",
        title="YouTube, with no account anywhere",
        track="beyond",
        minutes=7,
        surfaces=("Browse Stations", "Quill Radio"),
        summary=(
            "Turn a link, a playlist or a whole channel into rows you can play, "
            "favorite and record -- and know honestly what this cannot do."
        ),
        steps=(
            Step(
                title="Paste any YouTube link",
                body=(
                    "Add YouTube Link takes whatever you pasted and files it by "
                    "what the link is: a video becomes a playable row, a playlist a "
                    "folder of its videos, a channel page a followed channel. "
                    "@name follows the channel; @name/live saves the broadcast."
                ),
                command="radio.add_youtube_link",
                hear="The row added, under the video's own name.",
                note=(
                    "If the link is already on your clipboard, the box starts "
                    "filled in. The row is saved before the lookup runs, so a video "
                    "whose details will not read is still saved and still plays."
                ),
            ),
            Step(
                title="Answer the one-time question",
                body=(
                    "The first time anything YouTube is added or played, Quill "
                    "Radio asks once whether it may contact YouTube at all, and "
                    "remembers the answer. It asks because a scheduled recording "
                    "firing while nobody is watching should not be the first time "
                    "the app ever touched YouTube."
                ),
                hear="A one-time consent notice, with the rights position stated.",
            ),
            Step(
                title="Add a playlist as a list",
                body=(
                    "Add from YouTube Playlist lists the videos in the uploader's "
                    "own order -- never re-sorted, because a series is meant to be "
                    "worked through in order -- with each row reading as a "
                    "sentence: position, title, length, publisher. Add Selected or "
                    "Add All."
                ),
                command="radio.add_youtube_playlist",
                hear="How many were added, and how many were already yours.",
            ),
            Step(
                title="Follow a channel",
                body=(
                    "Add a Channel takes a channel address and reads it once to "
                    "check it can before saving. Each channel opens into Uploads "
                    "plus any playlists it publishes, and a channel with thousands "
                    "of videos pages with More rather than trying to be one "
                    "enormous level."
                ),
                hear="The channel added, then its Uploads folder.",
            ),
            Step(
                title="Bring across the channels you already follow",
                body=(
                    "Import YouTube Subscriptions reads the subscriptions file you "
                    "export from Google Takeout and adds every channel in it. "
                    "Nothing authenticates, no token is stored, and no request is "
                    "made to Google at all -- it is your data, exported by Google's "
                    "own tool, handed to a program you chose."
                ),
                command="radio.import_youtube_subscriptions",
                hear="Imported 24 channels; 3 you already followed.",
                note=(
                    "It is a one-time import: channels you subscribe to later will "
                    "not appear until you export and import again, and ones you "
                    "already follow are skipped rather than duplicated."
                ),
            ),
            Step(
                title="Read a video instead of watching it",
                body=(
                    "View Transcript on any YouTube row fetches the video's "
                    "captions and opens the reader without playing anything. An "
                    "automatically generated track says so in the heading, so you "
                    "know how much to trust the spelling."
                ),
                keys=("Shift+F10", "Ctrl+Shift+T"),
                hear="The transcript, with its heading saying which kind it is.",
            ),
            Step(
                title="Keep it playing when YouTube changes",
                body=(
                    "The helper that looks up a video's audio is built in, so your "
                    "first link simply plays. YouTube changes how it serves audio "
                    "more often than Quill Radio ships releases, so Update YouTube "
                    "Support fetches the current helper, tells you the version, and "
                    "uses it from then on."
                ),
                hear="The version it ended up with.",
            ),
            Step(
                title="Hear the honest limits",
                body=(
                    "Premium's benefits do not carry into this app and there is no "
                    "exception to ask for; watch history cannot be synchronised by "
                    "any third-party app; and a YouTube row cannot be downloaded, "
                    "which is a deliberate exclusion rather than a missing feature. "
                    "Recording one works, because that is a capture of what you are "
                    "playing."
                ),
                hear="Nothing: this step exists so the limits are not a surprise later.",
            ),
        ),
        closing=(
            "A YouTube row plays, favorites, records and schedules like a station. "
            "What is saved is the page address, never a stream address, which is "
            "why a recording you book today still works next week."
        ),
    ),
)
