"""Track 5, continued: keeping a copy, and the picture that comes with a video.

Two lessons the "More than radio" track was missing. Downloads had a single
step inside the audiobook lesson, which is the wrong place to meet it for
somebody who only ever saves podcast episodes; and the Video menu -- the
picture, the described audio track, Video Information -- had no lesson at all,
though it is the part of the app built for the listener who cannot see the
screen the video was made for.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="save-a-copy",
        title="Save a copy, and find it on disk",
        track="beyond",
        minutes=5,
        surfaces=("Browse Stations", "Downloads"),
        summary=(
            "Download one podcast episode or chapter, watch it arrive in the "
            "Downloads window, open the folder it went to, and decide once "
            "where downloads are filed."
        ),
        steps=(
            Step(
                title="Find something that has an end",
                body=(
                    "Open Browse Stations and arrow to a podcast episode, a book "
                    "chapter or an archive recording. Only a thing with a "
                    "beginning and an end can be saved; a live station offers "
                    "Record instead, because there is no file to fetch."
                ),
                keys=("Ctrl+B",),
                hear="Browse Stations, then the row you arrow to.",
                check="window:Browse Stations",
            ),
            Step(
                title="Download it from the row's menu",
                body=(
                    "Press Shift+F10 on the row and choose Download. It joins the "
                    "one download queue, and you can carry on listening to "
                    "something else while it arrives. A podcast episode files "
                    "itself under a folder named for its show."
                ),
                keys=("Shift+F10", "D"),
                hear="Queued, the name, how many are left to go, and You can carry on listening.",
                note=(
                    "A row that cannot be saved has no Download item at all, rather "
                    "than a dimmed one. A row already on disk offers Remove "
                    "Download in its place."
                ),
            ),
            Step(
                title="Hear it land",
                body=(
                    "A single download says where it went the moment it finishes, "
                    "naming the file and the folder. A whole book says its "
                    "progress instead, because forty separate saved sentences "
                    "would not be feedback anybody could use."
                ),
                hear="Saved, the file's name, and the folder it went to.",
            ),
            Step(
                title="Open the Downloads window",
                body=(
                    "The Downloads window lists everything queued, one sentence "
                    "per row with its state last -- waiting, downloading now, "
                    "saved, failed -- so arrowing the list answers where each one "
                    "has got to. Finished rows stay until you clear them."
                ),
                keys=("Ctrl+Shift+J",),
                hear="Downloads, then the first row and its state.",
                check="window:Downloads",
            ),
            Step(
                title="Go to the file",
                body=(
                    "On a saved row, Open Containing Folder shows the file in "
                    "Explorer. Cancel This One stops a download without losing "
                    "what has arrived, Remove From List forgets a row and leaves "
                    "the file alone, and Clear Finished tidies the list."
                ),
                keys=("Tab",),
                hear="Showing, the file's name, in, and its folder. Or Cleared, and a count.",
            ),
            Step(
                title="Decide once where downloads go",
                body=(
                    "Download Preferences sets the downloads folder, whether each "
                    "podcast show and each book gets a folder of its own, whether "
                    "downloads keep going when the window closes to the tray, and "
                    "whether to be asked where to save every time instead."
                ),
                command="radio.download_preferences",
                keys=("Ctrl+Alt+Shift+D",),
                hear="Download Preferences, then Downloads folder, blank uses the default.",
                note=(
                    "The Downloads window has a Preferences button that opens the "
                    "same dialog, because that is where the question occurs to "
                    "people."
                ),
            ),
            Step(
                title="Play it without the internet",
                body=(
                    "Go back to the same row in Browse Stations and press Enter. "
                    "A saved row plays from your disk, with no connection needed, "
                    "and its menu now offers Stop and Remove Download beside the "
                    "usual verbs."
                ),
                keys=("Enter",),
                hear="Playing, and the name -- from the copy on this computer.",
                check="playing",
            ),
        ),
        closing=(
            "Everything you save goes through one queue and lands where you said. "
            "When a download fails, Recent Problems keeps the reason."
        ),
        then=("pick-up-where-you-left-off",),
    ),
    Tutorial(
        slug="picture-and-described-audio",
        title="The picture, captions and described audio",
        track="beyond",
        minutes=6,
        surfaces=("Quill Radio", "Quill Radio Video"),
        summary=(
            "Find out what a YouTube video or a television channel carries, "
            "switch to its described audio track when there is one, and show "
            "or hide the picture for somebody sitting beside you."
        ),
        steps=(
            Step(
                title="Know that the picture never starts on its own",
                body=(
                    "Play a YouTube video or a television channel from Browse "
                    "Stations. It plays as sound only. The picture appears only "
                    "when somebody asks for it, which is both quieter for a "
                    "listener and the honest answer to light sensitivity."
                ),
                keys=("Enter",),
                hear="Playing, and the name -- and no window opening.",
                check="playing",
            ),
            Step(
                title="Ask what the video carries",
                body=(
                    "Video Information, on the Video menu, says the picture's "
                    "size, frame rate and encoding, then the two facts most "
                    "worth hearing, last so they are what you are left on: "
                    "whether captions and described audio were published."
                ),
                keys=("Ctrl+Shift+I",),
                hear=(
                    "Picture, its size, then Captions are available or No captions were "
                    "published, then the same for described audio."
                ),
            ),
            Step(
                title="Switch to described audio in one key",
                body=(
                    "Play Described Audio, on the Audio menu, switches straight "
                    "to the track that narrates what is on screen. When the video "
                    "has none, it says what tracks it does have, so you know the "
                    "video is the reason and not the app."
                ),
                keys=("Ctrl+Alt+D",),
                hear=(
                    "Playing the described audio track -- or This video has one audio "
                    "track, and No described audio was published."
                ),
            ),
            Step(
                title="Choose a track from the list",
                body=(
                    "Audio and Described Audio, on the same menu, lists every "
                    "audio track the video offers -- other languages, "
                    "commentary, description -- with a described track first and "
                    "the one playing marked. Arrow to one and press Enter to switch."
                ),
                keys=("Ctrl+Shift+A",),
                hear=(
                    "Audio and Described Audio, then the first track, and playing now "
                    "on the current one."
                ),
                note=(
                    "A live station has no tracks to choose, and says so rather "
                    "than opening an empty list."
                ),
            ),
            Step(
                title="Show the picture, and take it away",
                body=(
                    "Show Video opens a window titled Quill Radio Video with the "
                    "picture in it. The same key, Ctrl+W or Escape takes it away "
                    "again, and the sound carries on without a stutter -- hiding "
                    "the picture never pauses anything."
                ),
                keys=("Ctrl+Shift+V",),
                hear="Video shown, and its size. Then Video hidden. Audio is still playing.",
                note=(
                    "The picture needs the mpv playback engine, which is the "
                    "default. If you changed the engine in Preferences, Show "
                    "Video says so instead."
                ),
            ),
            Step(
                title="Keep a frame, or fill the screen",
                body=(
                    "With the picture showing, Take a Snapshot saves the current "
                    "frame as a picture file in your recordings folder -- a slide "
                    "to read with OCR, or to send to somebody who can describe "
                    "it. F11 fills the screen, and F11 or Escape leaves."
                ),
                keys=("Ctrl+Shift+Alt+H", "F11"),
                hear=(
                    "Snapshot saved as, and the file name. Full screen. Press F11 or "
                    "Escape to leave."
                ),
            ),
        ),
        closing=(
            "Captions and the transcript have their own steps in Watch television "
            "and in the YouTube lesson; everything here works the same for both."
        ),
        then=("watch-television", "youtube-without-an-account"),
    ),
)
