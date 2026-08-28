"""What every Quill Inkwell window is *for* -- the F1 help's opening paragraph.

Quill Radio authored the first catalogue (:mod:`quill.core.radio.surface_help`,
2026-08-23), QUILL Cast followed (:mod:`quill.core.podcasts.surface_help`,
2026-08-24), and the F1 engine has been family-wide since Radio's day one --
so Inkwell already answered F1 everywhere, but with the generic sentence,
which is true and useless. This module is Inkwell's half: the wx-free
catalogue of surface purposes keyed by window title, composed by
:mod:`quill.ui.app_context_help` exactly as Radio's and Cast's are.

Keyed by **window title** for the same reasons the others are: the title is
the one identity a window already announces, and it is what a person quotes
back in a bug report. Inkwell is a small app -- one manager window and a
handful of dialogs -- so almost every entry here is exact.

The catalogue is **gated** (GATE-INKWELL-HELP,
``quill/tools/inkwell_help_audit.py``): every ``wx.Frame``/``wx.Dialog``
title constructed in ``quill/apps/inkwell.py`` must resolve here, so a new
surface cannot ship without saying what it is for.

Wording rules, unchanged from Radio's, so the entries stay worth reading:

* One to three sentences. The first says what the window is for; the rest say
  what somebody actually does here or the one fact that saves a support email.
* Address the writer ("your abbreviations"), never the developer.
* No key-by-key tours -- the control section below the purpose covers the
  control under focus.
"""

from __future__ import annotations

#: Surface purposes by exact window title.
PURPOSES: dict[str, str] = {
    # -- the window --------------------------------------------------------------
    "Quill Inkwell": (
        "The manager window for a service that lives in the system tray: "
        "type an abbreviation in any application -- a browser, a mail "
        "client, a form -- and Inkwell replaces it with the text you saved. "
        "The list shows your library, which is the same library QUILL's "
        "editor expands from, so an abbreviation added in either works in "
        "both immediately. Closing this window keeps expansion running in "
        "the tray unless you turn that off in Options."
    ),
    # -- the dialogs -------------------------------------------------------------
    "Manage Abbreviations": (
        "Your whole abbreviation library in one place: create, edit, delete, "
        "and switch entries on or off, with search and a category filter to "
        "find the one you mean. Import and Export move the library as a "
        "file. Every change saves immediately and reaches QUILL's editor "
        "too, because both apps read the same library."
    ),
    "New Abbreviation": (
        "Create one abbreviation: the trigger word you will type, and the "
        "expansion that replaces it. The expansion may carry placeholders -- "
        "${cursor} for where the caret lands, ${date}, ${time}, and "
        "${clipboard} -- and Expand after chooses which keys fire it, "
        "including never, for Quick Insert only. OK saves it into the "
        "shared library at once."
    ),
    "Edit Abbreviation": (
        "Change one abbreviation: its trigger word, its expansion, or how it "
        "behaves -- which keys fire it, what is spoken, whether a sound "
        "plays. The expansion may carry ${cursor}, ${date}, ${time}, and "
        "${clipboard}. OK saves the change into the shared library at once."
    ),
    "Quick Insert": (
        "Pick an abbreviation and Inkwell types its expansion into the "
        "window you were just working in -- the way to use an entry set to "
        "expand only manually, or one whose trigger you cannot recall. "
        "Filter, choose, press Enter; focus returns to where you were and "
        "the text is typed there. If there is nowhere to type, the "
        "expansion is copied to the clipboard instead."
    ),
    "Excluded Applications": (
        "Programs where expansion must never run, one program file name per "
        "line -- notepad.exe, for example. Password managers and Windows "
        "sign-in prompts are always excluded whether or not you list them. "
        "OK saves the list immediately."
    ),
    "Update downloaded": (
        "A new Quill Inkwell is on disk and ready. Install and restart now "
        "applies it and relaunches -- your abbreviations and settings are "
        "kept -- or Open folder shows you the installer to run later."
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
#: keeps this from being reachable from any surface in Inkwell's own tree; it
#: exists so a brand-new window -- or the fill-in prompt, whose title is the
#: abbreviation being expanded -- still answers F1 with something true rather
#: than nothing.
GENERIC_PURPOSE = (
    "A Quill Inkwell window. Tab moves between its controls, Escape closes "
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
