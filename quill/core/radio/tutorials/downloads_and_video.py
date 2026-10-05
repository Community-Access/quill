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
            "Download a podcast episode or a book chapter, watch it arrive in "
            "the Downloads window, open the folder it went to, and choose where "
            "your downloads are kept."
        ),
        steps=(
            Step(
                title="Find something that has an end",
                body=(
                    "Open Browse Stations and arrow to a podcast episode, a book "
                    "chapter or an archive recording. You can only download "
                    "something with a beginning and an end. A live station "
                    "offers Record instead, because there is no file to save."
                ),
                keys=("Ctrl+B",),
                hear="Browse Stations, then the row you arrow to.",
                check="window:Browse Stations",
            ),
            Step(
                title="Download it from the row's menu",
                body=(
                    "Press Shift+F10 on the row and choose Download. It joins "
                    "the download queue, and you can carry on listening to "
                    "something else while it downloads. A podcast episode goes "
                    "into a folder named after its show."
                ),
                keys=("Shift+F10", "D"),
                hear="Queued, the name, how many are left to go, and You can carry on listening.",
                note=(
                    "If a row cannot be saved, it has no Download item at all. "
                    "If it is already saved, it offers Remove Download instead."
                ),
            ),
            Step(
                title="Hear it land",
                body=(
                    "When a single download finishes, Quill Radio tells you the "
                    "file's name and the folder it went into. For a whole book, "
                    "you hear how far along it is instead, rather than forty "
                    "separate messages."
                ),
                hear="Saved, the file's name, and the folder it went to.",
            ),
            Step(
                title="Open the Downloads window",
                body=(
                    "The Downloads window lists everything in the queue. Each "
                    "row ends with how it is doing: waiting, downloading now, "
                    "saved or failed. So arrowing down the list tells you where "
                    "each one is up to. Finished rows stay until you clear them."
                ),
                keys=("Ctrl+Shift+J",),
                hear="Downloads, then the first row and how it is doing.",
                check="window:Downloads",
            ),
            Step(
                title="Go to the file",
                body=(
                    "On a saved row, Open Containing Folder shows the file in "
                    "File Explorer. Cancel This One stops a download and keeps "
                    "what has arrived so far. Remove From List takes a row off "
                    "the list but leaves the file alone. Clear Finished tidies "
                    "up the list."
                ),
                keys=("Tab",),
                hear="Showing, the file's name, in, and its folder. Or Cleared, and a count.",
            ),
            Step(
                title="Decide once where downloads go",
                body=(
                    "Download Preferences sets your downloads folder. It also "
                    "lets you choose whether each podcast and each book gets its "
                    "own folder, whether downloads carry on when the window goes "
                    "to the tray, and whether to be asked where to save each time."
                ),
                command="radio.download_preferences",
                keys=("Ctrl+Alt+Shift+D",),
                hear="Download Preferences, then Downloads folder, blank uses the default.",
                note=(
                    "The Downloads window also has a Preferences button that "
                    "opens the same settings, right where you are likely to want "
                    "them."
                ),
            ),
            Step(
                title="Play it without the internet",
                body=(
                    "Go back to the same row in Browse Stations and press Enter. "
                    "A saved row plays from your computer, so you do not need an "
                    "internet connection. Its menu now also has Stop and Remove "
                    "Download."
                ),
                keys=("Enter",),
                hear="Playing, and the name, from the copy on your computer.",
                check="playing",
            ),
        ),
        closing=(
            "Everything you save goes through one queue and lands where you "
            "chose. If a download ever fails, Recent Problems keeps the reason "
            "for you."
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
            "Find out what a YouTube video or TV channel offers, switch to "
            "described audio when there is some, and show or hide the picture "
            "for someone sitting next to you."
        ),
        steps=(
            Step(
                title="Know that the picture never starts on its own",
                body=(
                    "Play a YouTube video or a TV channel from Browse Stations. "
                    "You hear the sound only. The picture only appears when you "
                    "ask for it, so nothing pops up unexpectedly on your screen."
                ),
                keys=("Enter",),
                hear="Playing, and the name, and no window opening.",
                check="playing",
            ),
            Step(
                title="Ask what the video carries",
                body=(
                    "Video Information, on the Video menu, tells you the "
                    "picture's size, frame rate and format. Last of all, so you "
                    "remember them, it tells you whether the video has captions "
                    "and whether it has described audio."
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
                    "to the track that describes what is on screen. If the video "
                    "does not have one, Quill Radio tells you which tracks it "
                    "does have, so you know it is the video and not you."
                ),
                keys=("Ctrl+Alt+D",),
                hear=(
                    "Playing the described audio track. Or This video has one audio "
                    "track, and No described audio was published."
                ),
            ),
            Step(
                title="Choose a track from the list",
                body=(
                    "Audio and Described Audio, on the same menu, lists every "
                    "sound track the video has, such as other languages, "
                    "commentary and description. A described track comes first, "
                    "and the one playing is marked. Arrow to one and press Enter "
                    "to switch."
                ),
                keys=("Ctrl+Shift+A",),
                hear=(
                    "Audio and Described Audio, then the first track, and playing now on "
                    "the current one."
                ),
                note=(
                    "A live station has no tracks to choose from, and Quill "
                    "Radio tells you so instead of opening an empty list."
                ),
            ),
            Step(
                title="Show the picture, and take it away",
                body=(
                    "Show Video opens a window called Quill Radio Video with the "
                    "picture in it. Press the same key, Ctrl+W or Escape to close "
                    "it again. The sound carries on smoothly. Hiding the picture "
                    "never pauses anything."
                ),
                keys=("Ctrl+Shift+V",),
                hear="Video shown, and its size. Then Video hidden. Audio is still playing.",
                note=(
                    "The picture needs the mpv playback engine, which is the "
                    "usual setting. If you changed the engine in Preferences, "
                    "Show Video tells you."
                ),
            ),
            Step(
                title="Keep a frame, or fill the screen",
                body=(
                    "While the picture is showing, Take a Snapshot saves what is "
                    "on screen as a picture file in your recordings folder. You "
                    "could read a slide with OCR, or send it to someone who can "
                    "describe it. F11 fills the screen, and F11 or Escape goes "
                    "back."
                ),
                keys=("Ctrl+Shift+Alt+H", "F11"),
                hear=(
                    "Snapshot saved as, and the file name. Full screen. Press F11 or "
                    "Escape to leave."
                ),
            ),
        ),
        closing=(
            "Captions and transcripts have their own steps in Watch television "
            "and in the YouTube lesson. Everything here works the same for both."
        ),
        then=("watch-television", "youtube-without-an-account"),
    ),
)
