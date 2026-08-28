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
back in a bug report. The Converter is a single-file app, so the catalogue is
small -- the main window, the two shared conversion surfaces it opens, and
the help window itself.

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
    "Quill Converter": (
        "The Universal Audio Converter: queue audio or video files (or whole "
        "folders), choose an output format and a preset, and Convert. "
        "Everything runs on this computer, your originals are never touched, "
        "and converted copies land in the output folder -- existing files "
        "are auto-numbered, never overwritten. Closing to the tray keeps it "
        "running a hotkey away while a batch finishes."
    ),
    "Convert Audio": (
        "The full conversion dialog, seeded with your queue: everything the "
        "main window offers plus the advanced catalog -- bitrate, sample "
        "rate, channels, loudness, and what to do when an output file "
        "already exists. Anything you leave alone keeps the preset's answer; "
        "only what you deliberately change is overridden."
    ),
    "Convert from URL": (
        "Paste a web link -- YouTube and many other sites -- and its audio "
        "is downloaded and handed to the converter. The downloader installs "
        "on demand, once, with your consent; the page's best audio stream is "
        "fetched, and nothing else about the page is kept. Unavailable in "
        "Safe Mode."
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
