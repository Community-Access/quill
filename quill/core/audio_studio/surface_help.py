"""What every QUILL Audio Studio window is *for* -- the F1 help's opening paragraph.

Quill Radio authored the first catalogue (:mod:`quill.core.radio.surface_help`,
2026-08-23), QUILL Cast followed (2026-08-24), and the F1 engine has been
family-wide all along -- so every Audio Studio window already answered F1, but
only with the generic sentence, which is true and useless. This module is the
Studio's half: the wx-free catalogue of surface purposes keyed by window
title, composed by :mod:`quill.ui.app_context_help` exactly as Radio's and
Cast's are.

Keyed by **window title** for the same reasons the others are: the title is
the one identity a window already announces, and it is what a person quotes
back in a bug report. One Studio quirk: the home window and the Studio wizard
deliberately share the title "QUILL Audio Studio", so that entry speaks to
both. Titles that carry live data ("Copy Sections -- interview.mp3") resolve
by prefix.

The catalogue is **gated** (GATE-STUDIO-HELP,
``quill/tools/studio_help_audit.py``): every ``wx.Frame``/``wx.Dialog`` title
constructed in the Audio Studio UI must resolve here, so a new surface cannot
ship without saying what it is for.

Wording rules, unchanged from Radio's, so the entries stay worth reading:

* One to three sentences. The first says what the window is for; the rest say
  what somebody actually does here or the one fact that saves a support email.
* Address the listener ("your books"), never the developer.
* No key-by-key tours -- the control section below the purpose covers the
  control under focus.
"""

from __future__ import annotations

# Re-exported so the Studio's help code and tests need one import, matching
# Radio and Cast.
from quill.core.control_help import (
    compose_control_body as compose_control_body,
)
from quill.core.control_help import (
    role_usage as role_usage,
)

#: Surface purposes by exact window title.
PURPOSES: dict[str, str] = {
    # -- the windows -------------------------------------------------------------
    "QUILL Audio Studio": (
        "The home window and the Studio wizard share this name. The home "
        "window is three big buttons -- narrate documents, build from "
        "recordings, edit a book -- above Your books, the library tree where "
        "Enter opens a book and F6 reaches the status bar. The wizard walks "
        "one of those journeys page by page; answer each page, or Skip to "
        "summary when your saved defaults already fit."
    ),
    "QUILL Audio Studio (Safe Mode)": (
        "The home window, running in Safe Mode: AI, publishing, translation, "
        "and downloading from links politely refuse until you restart "
        "normally. Narrating, building, converting, and editing books all "
        "still work."
    ),
    # -- the dialogs -------------------------------------------------------------
    "Sleep Timer": (
        "Stop playback by itself. Turn the timer on and give it a delay in "
        "minutes, or choose to stop at the end of the current chapter "
        "instead. It fires once and then turns itself off -- arming it again "
        "is a fresh visit here."
    ),
    "Play Queue": (
        "The books lined up to play in order. Add a book, jump to the next "
        "one, remove or clear entries -- Delete on the list removes the "
        "highlighted row. The current book is marked in words, and a row "
        "whose file has moved says missing rather than failing silently."
    ),
    "Chapter Workbench": (
        "One finished audiobook, open for surgery: listen with the "
        "chapter-aware player, rename chapters, split at the playhead, move "
        "a start, merge, or restore the original list. Book tags are "
        "editable below the player, and chapter lists import and export in "
        "Audacity, CUE, timestamp, JSON, and CSV forms. An MP3 saves its "
        "edits in place without touching the audio; an M4B saves as a new "
        "file, losslessly."
    ),
    "Propose chapters from silences": (
        "Two knobs for the silence scan: how quiet counts as silence (dB) "
        "and how long a pause must last (seconds). ffmpeg scans the "
        "recording and proposes chapter boundaries at the silence midpoints "
        "-- the proposal lands in the Workbench list for review, and Restore "
        "original undoes it."
    ),
    "ACX check": (
        "The verdict of measuring this book against Audible's ACX submission "
        "window: loudness, true peak, and noise floor, each with its limit, "
        "plus plain recommendations for anything failing. Read-only -- "
        "Escape closes it and nothing was changed."
    ),
    "Folder Podcast Feed": (
        "One folder of finished audio treated as a whole show: name it, "
        "describe it, say where the audio will live online, and give any "
        "episode its own title or description. Write feed.rss builds the "
        "feed with every episode; everything here is local files -- "
        "uploading is your server's business."
    ),
    "Publish Audiobook": (
        "Three ways to send one finished book out, each behind its own "
        "explicit button: write a podcast feed file next to it, upload it "
        "over SFTP to a saved destination (the password lives in the "
        "system's credential store, never in settings), or send it to your "
        "own Auphonic account for post-production. Nothing happens until "
        "you press the button for it."
    ),
    "Convert Audio": (
        "Convert audio files or whole folders between formats, on this "
        "machine. Build the queue, pick the output format, preset, and "
        "destination folder, and Convert runs in the background with spoken "
        "progress. The Advanced options only override what you deliberately "
        "change; untouched controls leave the preset alone."
    ),
    "Export a Document to Translated Speech": (
        "One document, spoken in other languages: pick the output format, "
        "add each target language with the voice that will read it, and "
        "choose whether your AI provider or a local LibreTranslate does the "
        "translating. Each export lands beside the source, named for its "
        "language."
    ),
    "QUILL Audio Studio Preferences": (
        "The Studio's own window behavior: whether launch checks for "
        "updates, whether Alt+F4 tucks the window into the tray with a run "
        "still going, whether long runs speak their 25, 50, and 75 percent "
        "milestones, and what the titlebar X does. Voices and speech "
        "defaults are not here -- they live in the Speech Hub, shared with "
        "QUILL."
    ),
    "Speech Settings": (
        "The Speech Hub: every speech engine and voice in one place -- "
        "preview them, download the offline ones, and set the defaults. "
        "What you choose here is shared with QUILL and the other Quill "
        "apps, so a voice configured once reads everywhere."
    ),
}

#: Purposes for windows whose titles carry live data, matched by prefix.
PREFIX_PURPOSES: tuple[tuple[str, str], ...] = (
    (
        "Copy Sections",
        "Mark pieces of the file you are listening to and collect them into "
        "one new file. Mark a start and an end at the playhead, preview "
        "exactly what you marked, add it to the list, and keep going -- then "
        "save the collection as a new file or onto an existing one. The "
        "original recording is never changed.",
    ),
    (
        "Help:",
        "This is the help window itself: the purpose of the window you were "
        "in, then the control you were on. Escape returns you to it.",
    ),
)

#: The honest fallback for a surface the catalogue does not know. The gate
#: keeps this from being reachable from any surface in the Audio Studio tree;
#: it exists so a shared or brand-new window still answers F1 with something
#: true rather than nothing.
GENERIC_PURPOSE = (
    "A QUILL Audio Studio window. Tab moves between its controls, Escape "
    "closes it, and F1 on any control explains that control."
)


def purpose_for_title(title: str) -> str:
    """The purpose paragraph for a window titled *title* (never empty)."""
    stripped = title.strip()
    exact = PURPOSES.get(stripped)
    if exact:
        return exact
    for prefix, purpose in PREFIX_PURPOSES:
        if stripped.startswith(prefix):
            return purpose
    return GENERIC_PURPOSE


def is_known_title(title: str) -> bool:
    """True when *title* resolves to an authored purpose (the gate's check)."""
    stripped = title.strip()
    if stripped in PURPOSES:
        return True
    return any(stripped.startswith(prefix) for prefix, _p in PREFIX_PURPOSES)
