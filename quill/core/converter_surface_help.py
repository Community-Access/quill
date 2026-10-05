"""What every Quill Converter window is *for* -- the F1 help's opening paragraph.

Quill Radio authored the first catalogue (:mod:`quill.core.radio.surface_help`,
2026-08-23), QUILL Cast followed (:mod:`quill.core.podcasts.surface_help`,
2026-08-24), and the F1 engine has been family-wide since Radio's day one --
so Quill Converter answered F1 everywhere, but always with the generic
sentence. This module is the Converter's half: the wx-free catalogue of
surface purposes keyed by window title, composed by
:mod:`quill.ui.app_context_help` exactly as its siblings' are.

Keyed by **window title** for the same reasons the siblings are: the title is
the one identity a window already announces, and it is what a person quotes
back in a bug report. The Converter is three modules --
``quill/apps/converter.py`` (the window), ``converter_menu.py`` (the menu bar)
and ``converter_actions.py`` (what the commands do) -- plus its own windows in
``quill/ui/converter_dialogs.py``. The catalogue covers the main window, the
two shared conversion surfaces it opens, its own windows (Custom Effects, and
the read-only report window under three titles: File Properties, Conversion
Report and Keyboard Shortcuts), and the help window itself.

The catalogue is **gated** (GATE-CONVERTER-HELP,
``quill/tools/converter_help_audit.py``): every ``wx.Frame``/``wx.Dialog``
title constructed in ``quill/apps/converter.py`` must resolve here, so a new
surface cannot ship without saying what it is for.

Wording rules, unchanged from Radio's, so the entries stay worth reading:

* One to three sentences. The first says what the window is for; the rest say
  what somebody actually does here or the one fact that saves a support email.
* Address the listener ("your files"), never the developer.
* No key-by-key tours -- the control section below the purpose covers the
  control under focus, and the app's menus advertise their own keys.
"""

from __future__ import annotations

#: Surface purposes by exact window title.
PURPOSES: dict[str, str] = {
    "Show and Hide Key": (
        "Choose one key that shows and hides Quill Converter from any program. Type it, "
        "for example with Ctrl, Alt and Shift held, or leave the box empty for "
        "no key. A key another QuillVille app already uses is refused, and you "
        "are told whose it is."
    ),
    "Find a Setting or Command": (
        "Every menu command in this app, searchable by name. Type part of a "
        "name; Down moves into the matches; Enter does the highlighted one, exactly "
        "as choosing it from its menu would. An option says whether it is on, and "
        "doing it switches it and says the new state."
    ),
    "Tag Editor": (
        "Every tag of one MP3, M4A, M4B or MP4 file, over five pages -- title, "
        "artist and album, the people, the dates and numbers, sorting, and the "
        "cover art. Control+Tab moves between pages. OK writes the tags into "
        "the file; the sound itself is not touched."
    ),
    "Chapter Workbench": (
        "Edit the chapters of an MP3, M4B or M4A: hear it, then add, rename, "
        "move, split and merge chapters at the playhead, find them at the "
        "pauses, or import and export a chapter list. Save writes them into "
        "the file itself, and every later conversion carries them."
    ),
    "Quill Converter": (
        "Convert audio and video between formats: sound to sound, video to "
        "sound, or video to video. Queue your files or folders, choose a "
        "format, a preset and any effects -- Preview lets you hear fifteen "
        "seconds of the result first -- and Convert. Everything runs on this "
        "computer, your originals are never touched, and a file already in "
        "the output folder is numbered around, never overwritten."
    ),
    "Convert Audio": (
        "The full conversion dialog, seeded with your queue: every format the "
        "main window offers, video included, plus exact settings -- bit rate, "
        "sample rate, channels, loudness -- and what to do when an output file "
        "already exists. It converts with its own settings, so the main "
        "window's effects do not apply here; anything you leave alone keeps "
        "the preset's answer."
    ),
    "Convert from URL": (
        "Paste a web link -- YouTube and many other sites -- and its audio "
        "is downloaded and handed to the converter. The page's best audio "
        "stream is fetched and nothing else about the page is kept; only "
        "download what you have the right to use. A playlist or a channel "
        "link asks how much of it to take. Unavailable in Safe Mode."
    ),
    "Download a Playlist or Channel": (
        "The link is a playlist or a YouTube channel. Choose how much of it to "
        "download -- the whole playlist or the first few, a channel's newest "
        "videos, Shorts or live streams, from any date or only recent ones. "
        "Every video's audio joins the queue in order, tagged as one album, "
        "and pasting the same link later fetches only what is new."
    ),
    "Custom Effects": (
        "Every effect on one page, starting from the effect recipe you had "
        "chosen: cleanup, tone, leveling, a loudness target, gain, speed, "
        "fades, and keeping only part of each file. OK makes these your "
        "Custom effects for the next conversion and for Preview; Cancel "
        "changes nothing."
    ),
    "File Properties": (
        "What is inside the file you highlighted, in plain words: its length "
        "and size, its tags, each video, audio and subtitle track, whether it "
        "has cover art, and its chapters. It is read-only, and Copy All puts "
        "it on the clipboard."
    ),
    "Conversion Report": (
        "Your last conversion, file by file: the settings used, where the files "
        "went, what converted, and why anything failed -- in plain words, then "
        "FFmpeg's own message. Copy All puts it on the clipboard, ready to "
        "paste into an email to support."
    ),
    "Keyboard Shortcuts": (
        "Every key in Quill Converter, grouped by menu, in one read-only list "
        "you can arrow through or copy. It is a reference; nothing here "
        "changes a key."
    ),
}

#: Purposes for windows whose titles carry live data, matched by prefix.
PREFIX_PURPOSES: tuple[tuple[str, str], ...] = (
    (
        "Help:",
        "This is the help window itself: the purpose of the window you were "
        "in, then the control you were on. Escape returns you to it.",
    ),
)

#: The honest fallback for a surface the catalogue does not know. The gate
#: keeps this from being reachable from any surface the Converter builds; it
#: exists so a shared or brand-new window still answers F1 with something
#: true rather than nothing.
GENERIC_PURPOSE = (
    "A Quill Converter window. Tab moves between its controls, Escape closes "
    "it, and F1 on any control explains that control."
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
