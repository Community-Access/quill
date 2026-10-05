"""Track 5: your own music, audiobooks and video, in playlists.

One lesson, because Local Media is one place with one shape: playlists on the
left, their items on the right, and every verb on the Applications key. It
walks from an empty window to a playlist you have shuffled, rearranged and
left playing while you do something else.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="local-media",
        title="Play your own files in playlists",
        track="beyond",
        minutes=8,
        surfaces=("Quill Radio", "Local Media", "Browse Stations"),
        summary=(
            "Make a playlist from music, audiobooks or video on your computer, "
            "play it, shuffle it, put it in your own order, and move through it "
            "from any window."
        ),
        steps=(
            Step(
                title="Open Local Media",
                body=(
                    "Local Media is its own window, like Radio Recordings. The first "
                    "time, it is empty, and your cursor is already on Add Media Files."
                ),
                command="radio.local_media",
                hear="Local Media, then Add Media Files button.",
            ),
            Step(
                title="Bring in a folder",
                body=(
                    "Add a Folder takes every file in a folder and the folders inside "
                    "it, in the order you would read the names, so track 2 comes "
                    "before track 10. The playlist is named after the folder, and it "
                    "picks up new files you copy there later."
                ),
                keys=("Ctrl+Alt+O",),
                hear="Made a playlist called, then the folder's name.",
                note="Add Media Files (Ctrl+O) is the same, for files you pick one by one.",
            ),
            Step(
                title="Play from anywhere in the list",
                body=(
                    "Arrow through the items and press Enter. Quill Radio plays that "
                    "one and then carries on down the playlist by itself. The row "
                    "that is playing says playing after its title."
                ),
                keys=("Enter", "Space"),
                hear="Playing, the title, and where it is, such as 3 of 12.",
                note="Space pauses and resumes the item that is playing.",
            ),
            Step(
                title="Put things in your own order",
                body=(
                    "Alt+Shift+Up and Alt+Shift+Down move the selected items one "
                    "place, and Quill Radio says where they landed. For a longer "
                    "move, press Ctrl+X, go to where they belong, and press Ctrl+V."
                ),
                keys=("Alt+Shift+Up", "Ctrl+X", "Ctrl+V"),
                hear="Moved to 2 of 12.",
                note="Ctrl+Z takes back the last change. Delete removes an item "
                "from the playlist, never from your computer.",
            ),
            Step(
                title="Shuffle and repeat",
                body=(
                    "Ctrl+H shuffles. The shuffled order stays put until you ask for "
                    "a new one with Ctrl+Shift+H, so Previous always goes back to "
                    "what you just heard. Ctrl+R goes from repeat off, to the whole "
                    "playlist, to this item."
                ),
                keys=("Ctrl+H", "Ctrl+R"),
                hear="Shuffle on.",
            ),
            Step(
                title="Move through it from any window",
                body=(
                    "The next and previous chapter keys move to the next and previous "
                    "item when a playlist is playing, in every Quill Radio window. "
                    "Where Am I adds where you are in the playlist."
                ),
                keys=("Ctrl+Shift+.", "Ctrl+Shift+,"),
                hear="The next item's title, and its place in the playlist.",
            ),
            Step(
                title="Find it in Browse Stations too",
                body=(
                    "Local Media is also the second branch of Browse Stations. Open a "
                    "playlist there and press Enter on an item to play it; the "
                    "Applications key offers Play Next, Remove from Playlist and the "
                    "rest."
                ),
                command="radio.browse",
                hear="Browse Stations.",
            ),
        ),
    ),
)
