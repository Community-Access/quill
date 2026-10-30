"""What every QUILL Studio window is *for* -- the F1 help's opening paragraph.

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
deliberately share the title "QUILL Studio", so that entry speaks to
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
    "Capture screen": (
        "Choose a named window for a whole-window screenshot without entering sizes. "
        "Or choose a display, full desktop, delayed active window or guided region. "
        "For a guided region, choose a source and Whole source, top, bottom, left, "
        "right or middle. Review Capture plan and guidance before starting. "
        "Exact coordinates are optional advanced settings. Review local OCR or "
        "framing afterward. AI sharing requires approval or previously enabled automatic AI."
    ),
    "Screenshot Inspector": (
        "Review the saved screenshot's file evidence, read text locally, or "
        "explicitly send it to your configured AI provider. File checks prove "
        "decode and integrity; observations do not prove privacy or visual correctness."
    ),
    "Record a demonstration": (
        "Record a screen-and-sound demonstration as one video. Choose what to record, "
        "which sounds go in -- your screen reader and microphone start left out -- the "
        "camera, the picture and the folder, then press Check. The result is read once; "
        "Start recording is available when nothing stops it. Nothing you hear changes."
    ),
    "Recording status": (
        "The recording in progress: elapsed time, the sounds being recorded, whether "
        "your screen reader is in it, dropped frames and disk space. Pause, add a "
        "marker, mute the microphone, or stop and save. Closing this window hides it; "
        "recording continues."
    ),
    "Test recording": (
        "The result of a 5-second test with your exact settings: what the check found "
        "in the file. The test file is deleted when this window closes."
    ),
    "Check camera framing": (
        "The camera is open while this window is: Studio says whether your face is in "
        "view and centred, and which way to move. Face detection runs on this computer; "
        "nothing is recorded or saved."
    ),
    "Make a YouTube video from a picture and sound": (
        "Choose a picture and a sound file, the shape of the video, and optionally a slow "
        "zoom, a sound wave and chapters from the recording's markers. The sound is used "
        "exactly as it is. The video and its YouTube title and description are saved beside "
        "the sound."
    ),
    "Ask AI questions about a video": (
        "Choose a video and the whole of it or a stretch. Studio takes frames from that "
        "stretch, lays them out as one labelled picture with the transcript if there is one, "
        "and opens a conversation about it. Nothing is sent until you approve it there."
    ),
    "Make a picture with AI": (
        "Describe the picture you want, choose its shape and press Make the picture. Then ask "
        "for changes in words and press it again; every version is kept with a description "
        "from a separate look by your vision model. Every request is approved first."
    ),
    "Studio Mixer": (
        "Every program's sound and every sound card in one window. Programs: each "
        "program's volume, mute and the sound card it plays on, as Windows Settings does. "
        "Devices: choose the default and communications devices, and set a microphone's "
        "level and mute. Ctrl+Tab moves between the tabs."
    ),
    "Add a program's sound": (
        "Choose a program that is playing sound to add as a sound source of its own."
    ),
    "Add marker": ("Type an optional label for this moment in the recording, then press Enter."),
    "Choose the save folder": "Choose the folder where demonstrations are saved.",
    "Discard this recording": (
        "Confirm deleting the recording in progress. It cannot be recovered."
    ),
    "Recover unfinished recordings": (
        "Recordings interrupted by a crash or power cut were found. Studio can join, "
        "check and save each one beside its folder."
    ),
    "Screen reader speech": (
        "Confirm putting your screen reader's speech in the recording: everything it "
        "says while you record will be in the file."
    ),
    "Choose screenshot control": (
        "Choose a specific part of the selected window by its name or role. "
        "Search filters real accessible controls without AI. Password and offscreen "
        "items are excluded. Use control selects a screenshot area; it does not press the control."
    ),
    "Screenshot editing and evidence": (
        "Edit a copy of your screenshot. Choose a plain-language action and a named area, "
        "then Add edit. Undo and Redo preserve the original. Find text to select offers "
        "recognized text as an anchor. More options reveals specialist geometry, layers, "
        "comparison and evidence exports. Review the edited result before sharing."
    ),
    "Screenshot visual preview": (
        "An optional magnified visual preview. Use scrolling keys to inspect it. "
        "The editing window retains a text plan and object list for nonvisual review."
    ),
    "Add a spoken screenshot note": (
        "Start explicitly opens the shared microphone. Stop and recognize uses an installed "
        "offline speech model. Review and correct the words before Use reviewed note. "
        "Closing stops recording; temporary audio is deleted. No cloud upload occurs."
    ),
    "Tag Editor": (
        "Every tag this audio file can carry, over five pages: the main "
        "fields, the details, publishing credits, sort-order fields, and the "
        "cover art. Control+Tab moves between pages. Nothing is written until "
        "you press OK and then save -- this window hands the edit back, it "
        "never touches the file itself. It is the same editor QUILL Audio "
        "Studio and podHarvest both show, from the same table, so a file "
        "edited in either reads back unchanged in the other."
    ),
    "Edit chapter": (
        "This chapter's title and its exact start and end, typed rather than "
        "set by ear, plus the optional link and image a Podcasting 2.0 player "
        "can show. Moving the start moves the end of the chapter before it, "
        "so the book stays gapless; the sentence at the top tells you the "
        "range this chapter is allowed to occupy."
    ),
    # -- the windows -------------------------------------------------------------
    "QUILL Studio": (
        "The home window and the Studio wizard share this name. The home "
        "window is three big buttons -- narrate documents, build from "
        "recordings, edit a book -- above Your books, the library tree where "
        "Enter opens a book and F6 reaches the status bar. The wizard walks "
        "one of those journeys page by page; answer each page, or Skip to "
        "summary when your saved defaults already fit."
    ),
    "QUILL Studio (Safe Mode)": (
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
        "One audiobook or any recording -- a lecture, a meeting -- open for "
        "surgery: listen with the "
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
        "recording and proposes chapters at the silences, titled Proposed "
        "chapter -- they land in the Workbench list for review, and Restore "
        "original undoes them. Pressing the button again while it runs stops it."
    ),
    "Chapters already here": (
        "This recording already has chapters of its own. Keep mine, add "
        "proposals keeps every one of them and adds only the boundaries that "
        "are new; Replace with the proposal swaps the whole list. Cancel "
        "changes nothing, and Restore original undoes either answer."
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
    "QUILL Studio Preferences": (
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

# Legacy names remain discoverable for old builds and documentation.
for _title in ("QUILL Studio", "QUILL Studio (Safe Mode)", "QUILL Studio Preferences"):
    PURPOSES[_title.replace("QUILL Studio", "QUILL Audio Studio")] = PURPOSES[_title]

#: Purposes for windows whose titles carry live data, matched by prefix.
PREFIX_PURPOSES: tuple[tuple[str, str], ...] = (
    (
        "Demonstration",
        "The demonstration was saved and checked independently. Verified means every "
        "check passed; Needs review means it plays but something may be spoiled; Failed "
        "means a stream is missing or it does not decode. Play it, open its folder, copy "
        "its path or inspect a frame.",
    ),
    (
        "Video:",
        "The video was made and checked. Play it, open its folder or copy its path. The "
        "title and description for YouTube are in the text file beside it.",
    ),
    (
        "Recovered:",
        "An interrupted recording was finished and checked. Play it, open its folder, "
        "copy its path or inspect a frame.",
    ),
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
    "A QUILL Studio window. Tab moves between its controls, Escape "
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
