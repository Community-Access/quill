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
            "Find a podcast, subscribe to it, see what you have not heard yet, "
            "and read a transcript without playing anything. You will also find "
            "out what Quill Radio does with podcasts and what QUILL Cast does."
        ),
        steps=(
            Step(
                title="Open a podcast directory",
                body=(
                    "Two branches in Browse Stations list podcasts. Podcasts "
                    "(Apple) has each country's top shows and all of Apple's "
                    "categories. Podcast Index is the open podcast directory. "
                    "Neither one needs an account or a sign-in."
                ),
                keys=("Ctrl+B",),
                hear="The branch, then its countries or categories.",
                check="window:Browse Stations",
            ),
            Step(
                title="Look at a show without committing to it",
                body=(
                    "Open a show and its episodes are right there. You can play "
                    "one, add it to favorites, download it or read its "
                    "transcript. You do not have to subscribe to listen, so try "
                    "an episode and see if you like it."
                ),
                keys=("Right arrow", "Enter"),
                hear="The episodes, newest first.",
            ),
            Step(
                title="Subscribe",
                body=(
                    "Subscribe to This Podcast, on the show's own menu, adds it "
                    "to your podcasts. QUILL Cast shares the same list, so the "
                    "show will be there next time you open Cast too. On a show "
                    "you already follow, the same item says Unsubscribe."
                ),
                keys=("Shift+F10",),
                hear="Subscribing, then Subscribed to, and the show's name.",
            ),
            Step(
                title="Find what you follow",
                body=(
                    "The Podcasts branch starts with a Subscriptions folder. "
                    "Inside, each show has its own folder of its newest "
                    "episodes. The Subscriptions folder says how many shows you "
                    "follow, and each show says how many episodes you have not "
                    "heard yet, just as Cast does."
                ),
                keys=("Home", "Right arrow"),
                hear="Subscriptions, with a number, then each show with its unheard count.",
                note=(
                    "You can choose in Preferences how many episodes each show "
                    "lists. It starts at the newest 25. Automatic downloads, "
                    "keeping or clearing old episodes, and the full archive are "
                    "in QUILL Cast."
                ),
            ),
            Step(
                title="Ask every show at once",
                body=(
                    "Check All Feeds Now, on the Subscriptions branch, checks "
                    "every show you follow for new episodes in one go. That "
                    "includes shows you have paused, so they are never out of "
                    "reach."
                ),
                keys=("Shift+F10",),
                hear=(
                    "Checking subscribed feeds, then what it found, counted and named. "
                    "Or No new episodes."
                ),
                note=(
                    "In Preferences, you can have Quill Radio check by itself, "
                    "anywhere from every 15 minutes to once a day, and when it "
                    "opens. Both start off, so Quill Radio never uses your "
                    "internet on a schedule you did not choose."
                ),
            ),
            Step(
                title="Read an episode instead of playing it",
                body=(
                    "If an episode comes with a transcript, its row says "
                    "transcript available. View Transcript opens it to read, "
                    "without playing anything. It is a quick way to find out "
                    "whether an hour-long episode is about what you hoped."
                ),
                keys=("Shift+F10",),
                hear="The transcript window, with the episode's title at the top.",
            ),
            Step(
                title="Do the housekeeping",
                body=(
                    "A show's menu has Move to Folder, Mark All as Played, "
                    "Download All Episodes and Remove All Downloads. If there is "
                    "nothing to do, the item is dimmed and says why, for "
                    "example: nothing to mark, all 63 episodes are already played."
                ),
                keys=("Shift+F10",),
                hear="The action confirmed, and the counts updating.",
            ),
            Step(
                title="Hand an episode to QUILL Cast",
                body=(
                    "Play Next in QUILL Cast, Add to QUILL Cast Queue and Send to "
                    "the QUILL Cast Inbox pass an episode over to Cast. Quill "
                    "Radio makes a note of it, and Cast does it the next time "
                    "you open Cast. The message you hear says so."
                ),
                keys=("Shift+F10",),
                hear="It will be next in the QUILL Cast queue.",
            ),
            Step(
                title="Know where the line is",
                body=(
                    "Playing, downloading and the actions on each episode work "
                    "here just like everywhere else in Browse Stations. The rest, "
                    "such as automatic downloads, tidying old episodes, the play "
                    "queue and the full archive, is what QUILL Cast is for. If "
                    "podcasts become a big part of your day, Cast is worth a try."
                ),
                hear=(
                    "Nothing. This step just saves you looking for a setting that is in "
                    "Cast instead."
                ),
            ),
        ),
        closing=(
            "Your place in an episode follows you between Quill Radio and QUILL "
            "Cast, and so do your bookmarks. No account or sync service needed."
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
            "Find an audiobook, keep your place in it, and download a whole book "
            "while you keep listening. You will also learn which sources let you "
            "save things, and why some do not."
        ),
        steps=(
            Step(
                title="Find a book three ways",
                body=(
                    "LibriVox offers Recently Added, By Genre and By Author, read "
                    "by about seven thousand volunteers. Project Gutenberg "
                    "Audiobooks has 1,124 books read by people. The Internet "
                    "Archive has Old Time Radio, the Live Music Archive, radio "
                    "programmes and more."
                ),
                keys=("Ctrl+B",),
                hear="The branch's own shelves.",
                check="window:Browse Stations",
                note=(
                    "LibriVox has no By Title, because LibriVox itself does not "
                    "offer a way to search by title. Try By Author or By Genre "
                    "instead."
                ),
            ),
            Step(
                title="Open a book and play a chapter",
                body=(
                    "A book with chapters opens as a folder of chapters. A book "
                    "that is one long reading just plays. Press Enter to play, "
                    "and every player key works, including speed, chapters and "
                    "Where Am I."
                ),
                keys=("Right arrow", "Enter"),
                hear="The chapter playing, and its position when you ask.",
            ),
            Step(
                title="Stop, and come back tomorrow",
                body=(
                    "Quill Radio remembers your place in a book chapter, an Old "
                    "Time Radio episode or a podcast episode, and carries on "
                    "from there next time you play it. If you only listened for "
                    "a few seconds, it starts from the beginning. When you "
                    "finish something, the next play starts from the beginning "
                    "too."
                ),
                hear="Resuming at, and the time. 12 minutes 8 seconds, say.",
            ),
            Step(
                title="Save a whole book at once",
                body=(
                    "Download All Files on a book's folder says how many files "
                    "there are, for example Download All 40 Files. It saves every "
                    "chapter into one folder, in order, while you carry on "
                    "listening. If a download is interrupted, it carries on "
                    "where it left off. One bad chapter only costs that chapter, "
                    "and if you stop, everything already saved is kept."
                ),
                keys=("Shift+F10",),
                hear="The download added, and how many files it has.",
            ),
            Step(
                title="Watch the queue",
                body=(
                    "Everything you save waits in one queue and downloads one at "
                    "a time, in the order you asked. The Downloads window shows "
                    "what is waiting, downloading, saved and failed. It has Open "
                    "Containing Folder, cancel and remove for each row, and Clear "
                    "Finished."
                ),
                keys=("Ctrl+Shift+J",),
                hear="Downloads, then each row with how it is doing.",
                check="window:Downloads",
                note=(
                    "If you close the window while downloads are still going, "
                    "Quill Radio either finishes them in the background or stops "
                    "them, whichever you chose in Download Preferences, and tells "
                    "you which."
                ),
            ),
            Step(
                title="Play a downloaded book as a book",
                body=(
                    "The chapters are in the right order, so chapter 2 comes "
                    "before chapter 10. When one ends, the next starts by itself "
                    "and tells you where you are, such as 4 of 40. When the last "
                    "chapter ends, Quill Radio tells you, so you are not left "
                    "wondering why it went quiet."
                ),
                hear="The next chapter starting, with its number and the total.",
            ),
            Step(
                title="Learn what cannot be saved, and why",
                body=(
                    "Download only appears where the source clearly allows it. "
                    "If you try anyway, Quill Radio tells you why not. A live "
                    "station has no file to save, so record it instead. Spotify "
                    "is copy-protected. YouTube downloads are left out on "
                    "purpose. And on Audius, it is up to each artist, and the "
                    "listing does not say."
                ),
                keys=("Shift+F10",),
                hear="The reason, in plain words.",
            ),
            Step(
                title="Find music that is genuinely free",
                body=(
                    "Audius has what is popular now, overall and in 27 genres, "
                    "and leaves out tracks you would have to pay for. ccMixter "
                    "has Creative Commons music by tag, with each track's "
                    "licence on its row. When you save a Creative Commons track, "
                    "its licence is saved next to it in a text file."
                ),
                hear="The track, with its licence read as part of the row.",
                note=(
                    "Mixcloud shows are listed but not played inside Quill "
                    "Radio. Pressing Enter opens the show in your web browser, "
                    "and the row tells you so before you press it."
                ),
            ),
        ),
        closing=(
            "Books, archives and free music work just like every other row. The "
            "only difference from one source to the next is what you can keep, "
            "and Quill Radio always tells you."
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
            "Turn a YouTube link, playlist or channel into rows you can play, "
            "keep as favorites and record. You will also hear plainly what this "
            "cannot do."
        ),
        steps=(
            Step(
                title="Paste any YouTube link",
                body=(
                    "Add YouTube Link takes whatever link you paste and works out "
                    "what it is. A video becomes a row you can play. A playlist "
                    "becomes a folder of its videos. A channel page becomes a "
                    "channel you follow. @name follows the channel, and "
                    "@name/live saves its live broadcast."
                ),
                command="radio.add_youtube_link",
                hear=(
                    "Added the video. Find it under Browse Stations, YouTube. A moment "
                    "later, That video is, and its own name."
                ),
                note=(
                    "If the link is already on your clipboard, the box is filled "
                    "in for you. The row is saved straight away, so even if the "
                    "video's details cannot be read, it is still saved and still "
                    "plays."
                ),
            ),
            Step(
                title="Answer the one-time question",
                body=(
                    "The first time you add or play anything from YouTube, Quill "
                    "Radio asks you once whether it may contact YouTube, and "
                    "remembers your answer. Asking now means a booked recording "
                    "will never reach YouTube without you having said yes."
                ),
                hear="A one-time question, explaining what YouTube allows.",
            ),
            Step(
                title="Add a playlist as a list",
                body=(
                    "Add from YouTube Playlist lists the videos in the order the "
                    "playlist's owner chose, so a series stays in order. Each row "
                    "reads like a sentence: position, title, length, and who "
                    "published it. Choose Add Selected or Add All."
                ),
                command="radio.add_youtube_playlist",
                hear="How many were added, and how many you already had.",
            ),
            Step(
                title="Follow a channel",
                body=(
                    "Add a Channel takes a channel address and checks it works "
                    "before saving it. Each channel opens into Uploads, plus any "
                    "playlists it has. A channel with thousands of videos shows "
                    "them a page at a time, with More to load the next page."
                ),
                hear="Checking that channel, then Added, and the channel's name.",
            ),
            Step(
                title="Bring across the channels you already follow",
                body=(
                    "Import YouTube Subscriptions reads the subscriptions file "
                    "you download from Google Takeout and adds every channel in "
                    "it. You do not sign in, and Quill Radio does not contact "
                    "Google at all. It simply reads the file you give it."
                ),
                command="radio.import_youtube_subscriptions",
                hear="Imported 24 channels; 3 you already followed.",
                note=(
                    "This brings in your list as it is today. Channels you "
                    "subscribe to later only appear if you export and import "
                    "again. Channels you already follow are skipped, so you "
                    "never get two copies."
                ),
            ),
            Step(
                title="Read a video instead of watching it",
                body=(
                    "View Transcript, on any YouTube row, gets the video's "
                    "captions and opens them to read, without playing anything. "
                    "If the captions were made automatically, the heading says "
                    "so, so you know the spelling may be a bit off. For the "
                    "video that is playing, Transcript on the Playback menu does "
                    "the same."
                ),
                keys=("Shift+F10", "Ctrl+Shift+T"),
                hear="The transcript, with its heading saying which kind it is.",
            ),
            Step(
                title="Keep it playing when YouTube changes",
                body=(
                    "Everything YouTube needs comes built in, so your first link "
                    "just plays. But YouTube changes things often. If videos "
                    "stop playing, use Repair YouTube Support on the Station "
                    "menu. It gets the newest version of the YouTube helper, "
                    "tells you the version, and uses it from then on."
                ),
                keys=("Ctrl+Alt+Y",),
                hear=(
                    "Updating YouTube support, then YouTube support is now version, and the number."
                ),
            ),
            Step(
                title="Hear the honest limits",
                body=(
                    "YouTube Premium benefits do not carry over into Quill "
                    "Radio. Your YouTube watch history cannot be updated by any "
                    "app other than YouTube's own. And YouTube rows cannot be "
                    "downloaded, on purpose. You can record one, though, just "
                    "like recording a station."
                ),
                hear="Nothing. This step is here so the limits never surprise you.",
            ),
        ),
        closing=(
            "A YouTube row plays, records and can be a favorite or a booked "
            "recording, just like a station. Quill Radio saves the page address, "
            "so a recording you book today still works next week."
        ),
    ),
)
