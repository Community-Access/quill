"""F1 for the Scribe for Documents windows, in every app that opens them (PRD 12).

QUILL and QUILL Lite answer F1 from their help topics; the other apps answer
it from a catalogue of window purposes, by exact title
(:mod:`quill.core.media.surface_help`, :mod:`quill.core.converter_surface_help`,
:mod:`quill.core.audio_studio.surface_help`, :mod:`quill.core.podcasts.surface_help`,
:mod:`quill.apps.beacon.surface_help`). Each of those merges these, so the
shared windows explain themselves the same way wherever they open, and a new
Scribe window is written here once.

wx-free.
"""

from __future__ import annotations

from quill.core.scribe import PRODUCT_NAME

#: Purposes by exact window title.
SCRIBE_PURPOSES: dict[str, str] = {
    "Convert with Scribe for Documents": (
        f"Send a document to {PRODUCT_NAME}, Pneuma Solutions' service, and choose "
        "what you want back: Word, accessible HTML, tagged PDF, EPUB, Kindle, DAISY "
        "with audio, MP3 audio or braille. The first box says exactly what will be "
        "sent and where; nothing is sent until you press Send and Convert. Settings "
        "for language, voice, braille and pictures follow the formats, and Pages says "
        "how many of your Scribe pages it uses."
    ),
    "Scribe Conversions": (
        f"Every {PRODUCT_NAME} job on this computer, from every QUILL app, with its "
        "formats and stage. Details below the list has the percent, time left and "
        "Scribe's latest message. Enter opens the result, Delete removes the row, and "
        "the Applications key lists every command, Next Steps among them. Each stage "
        "is said once, and the rows never move under you. Escape closes it."
    ),
    "My Scribe Documents": (
        "Every document in your Scribe account, and the Trash. Download Formats "
        "(Enter) downloads a format or makes a new one, which uses no pages for a "
        "document already there. Rename, Move to Trash, Recover, Delete Forever, Ask "
        "for Human Review and Copy Details are buttons, and the Applications key lists "
        "them."
    ),
    "Scribe for Documents Options": (
        f"One set of {PRODUCT_NAME} choices for the whole QUILL family: who is signed "
        "in and the pages left, Sign In or Sign Out, your account in the browser, the "
        "default formats, the download folder, whether results open by themselves, "
        "and how much is spoken. OK saves; Cancel leaves things as they were."
    ),
    "Sign In to Scribe for Documents": (
        "Your browser is open at Scribe's own sign-in page; sign in there and come "
        "back. QUILL never sees what you type. Copy Sign-in Link copies the address "
        "for another browser, and Continue closes this once you are signed in."
    ),
    "Convert from a Link": (
        f"The address of a file for {PRODUCT_NAME} to fetch, such as a link to a PDF. "
        "It must start with https:// or http:// and point straight at a file, not a "
        "web page or a page behind a sign-in."
    ),
    "Ask for Human Review": (
        "Tell Scribe's people what is wrong with the document. Human review is "
        "Scribe's paid remediation; Scribe tells you the cost."
    ),
    "Rename": "The document's new title in your Scribe account.",
    "Choose a Linked Document": (
        f"The links here that point straight at a file {PRODUCT_NAME} can take. "
        "Choose one and press OK; the Convert dialog then says what will be sent "
        "before anything goes."
    ),
    "Save a Beacon Place": (
        "Where in the document the Quill Beacon place should point: the start, or "
        "one of its headings. The place remembers the Scribe document, so Beacon can "
        "download it again if the file is gone."
    ),
    "Download Again from Scribe for Documents": (
        "The file this place points to is not on this computer. Yes opens the Convert "
        "dialog for the document already in your Scribe account; nothing is uploaded "
        "and no pages are used."
    ),
    "Turn On Scribe for Documents": (
        f"{PRODUCT_NAME} is off in QUILL Lite. Yes turns it on and opens the Convert "
        "dialog, which still says what will be sent before anything goes. You can turn "
        "it off again in Tools, Customize Features."
    ),
}

#: Purposes for titles that carry a file name, matched by prefix.
SCRIBE_PREFIX_PURPOSES: tuple[tuple[str, str], ...] = (
    (
        "Password for ",
        "The password for this PDF, used for this one upload and never saved. Show "
        "password shows what you typed, for braille or typing echo.",
    ),
)

__all__ = ["SCRIBE_PREFIX_PURPOSES", "SCRIBE_PURPOSES"]
