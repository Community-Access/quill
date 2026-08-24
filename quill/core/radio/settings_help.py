"""What every Quill Radio recording setting does, and the misreading it prevents.

The same rule QUILL Cast's help follows
(:mod:`quill.core.podcasts.settings_help`): **what it does, then the misreading
it prevents, in that order, in one added sentence.**

Recording has its own family of misreads, and they are all about *when* a
setting takes effect and *what it costs if it does not*:

* *does this change anything I have already recorded?* (format, bitrate, the
  destination folder, the filename pattern -- no, none of them, and none of
  them said so)
* *does stopping mean losing?* (the length cap, the reconnect attempt limit --
  both keep what was captured, which is the difference between a safety net
  and a trapdoor)
* *is this what I hear, or what gets written?* (the sound-enhancement filter --
  the one place where the two are deliberately different)

That last one is why these live in a table rather than beside their controls:
a recording setting is read once, at the moment somebody is deciding whether
to trust the app with an hour of live radio they cannot get again. Being wrong
about it costs the hour.

wx-free, strict-typed, pure data.
"""

from __future__ import annotations

HELP: dict[str, str] = {
    "format": (
        "Audio format for new recordings. Raw stream saves exactly what the "
        "station sends, with no re-encoding -- the most lossless capture, for "
        "your own editing. It applies from the next recording on; nothing "
        "already recorded is converted or re-encoded."
    ),
    "bitrate": (
        "Bitrate for MP3 and OGG recordings; ignored for lossless and raw "
        "stream, which have nothing to choose. Like the format, it applies to "
        "new recordings only."
    ),
    "folder": (
        "Where recordings are saved; blank uses the default recordings folder. "
        "Changing it applies to recordings from now on -- files already on disk "
        "stay where they are, and the Recordings list still finds them."
    ),
    "folder_button": "Choose a destination folder",
    "temp_folder": (
        "Where a recording is written while it is running, then moved to the "
        "destination folder when it finishes; blank records straight to the "
        "destination. Useful when the destination is a network or sync folder "
        "-- what moves is a finished file rather than one being written to."
    ),
    "temp_folder_button": "Choose a temporary folder",
    "filename": (
        "Filename pattern for new recordings; use {station}, {date} and {time} "
        "as placeholders. It names files as they are made and renames nothing "
        "already recorded."
    ),
    "max_minutes": (
        "Safety cap: every recording stops automatically after this many "
        "minutes, so a schedule that starts and is forgotten cannot fill a "
        "disk. Stopping is not losing -- everything captured up to that point "
        "is saved as a finished recording."
    ),
    "concurrent": (
        "How many recordings may run at the same time. Zero means unlimited -- "
        "every recording you or the schedule asks for starts. Set a number to "
        "cap it on a slower machine or a metered connection; a recording over "
        "the cap is refused with a reason rather than started and starved."
    ),
    "reconnect": (
        "When the connection drops mid-recording, ride it out and resume into "
        "a continuation part file instead of losing the rest of the show. What "
        "was already captured is never discarded, whether or not the reconnect "
        "succeeds."
    ),
    "reconnect_attempts": (
        "How many times to try reconnecting before giving up on a recording. "
        "Giving up ends the recording and keeps every part already written -- "
        "it never throws away what was captured before the drop."
    ),
    "reconnect_wait": (
        "How long to wait before each reconnect attempt; also how long ffmpeg "
        "itself rides out short gaps. It never delays a recording that is "
        "running normally."
    ),
    "filters": (
        "Record the EQ and compressor from Playback > Sound Enhancements, "
        "instead of an unfiltered archival copy. This is the one place where "
        "what you hear and what gets written are deliberately different: off, "
        "the file is what the station sent, whatever your playback settings "
        "are doing."
    ),
    "status": "Status",
    "save_button": "Save these recording settings",
}


#: Download Preferences. Five checkboxes that carried no help at all -- the
#: labels said what each one did and nothing said what it did *not* do, which
#: for filing rules is the whole question: does turning this on move what I
#: have already saved?
DOWNLOAD_HELP: dict[str, str] = {
    "folder": (
        "Where saved audio goes; blank uses the default downloads folder. It "
        "applies to what you save from now on -- files already on disk stay "
        "where they are and keep playing."
    ),
    "folder_button": "Choose the downloads folder",
    "per_show": (
        "File a podcast episode into a folder named after its show. It "
        "arranges new downloads; it never moves or renames what is already "
        "saved."
    ),
    "per_book": (
        "File an audiobook into a folder of its own, so its parts stay "
        "together. New downloads only -- books already saved are left exactly "
        "as they are."
    ),
    "by_author": (
        "Once an author has more than one book, group their books under an "
        "author folder. It takes effect on the next book by that author; the "
        "earlier ones stay where they were saved."
    ),
    "keep_going": (
        "Let downloads finish after the window closes to the tray. With this "
        "off they are stopped rather than paused, so a part-finished file is "
        "discarded and starts again next time."
    ),
    "always_ask": (
        "Ask where to save every download instead of filing it by the rules "
        "above. The rules stay saved while this is on -- turning it off puts "
        "them straight back."
    ),
}


def describe(key: str, *, downloads: bool = False) -> str:
    """The help text for *key*, or an empty string if there is none.

    The table is chosen, not searched: both tables define ``folder`` and
    ``folder_button`` -- recordings and downloads each have a destination --
    and a lookup that fell through from one to the other would hand a
    downloads control the sentence about recordings, which is the exact kind
    of wrong that reads as right.
    """
    table = DOWNLOAD_HELP if downloads else HELP
    return table.get(key, "")


__all__ = ["DOWNLOAD_HELP", "HELP", "describe"]
