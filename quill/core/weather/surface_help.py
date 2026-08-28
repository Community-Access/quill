"""What every Quill Weather window is *for* -- the F1 help's opening paragraph.

Quill Radio authored this first (:mod:`quill.core.radio.surface_help`,
2026-08-23), QUILL Cast followed (2026-08-24), and the F1 engine has been
family-wide since the start -- but Quill Weather answered F1 with the generic
sentence, which is true and useless. This module is Weather's half: the
wx-free catalogue of surface purposes keyed by window title, composed by
:mod:`quill.ui.app_context_help` exactly as Radio's and Cast's are.

Keyed by **window title** for the same reasons the siblings are: the title is
the one identity a window already announces, and it is what a person quotes
back in a bug report. Weather's titles are static (no live data in them), so
almost everything here resolves exactly.

The catalogue is **gated** (GATE-WEATHER-HELP,
``quill/tools/weather_help_audit.py``): every ``wx.Frame``/``wx.Dialog``
title constructed in the weather UI must resolve here, so a new surface
cannot ship without saying what it is for.

Wording rules, unchanged from Radio's, so the entries stay worth reading:

* One to three sentences. The first says what the window is for; the rest say
  what somebody actually does here or the one fact that saves a support email.
* Address the listener ("your locations"), never the developer.
* No key-by-key tours -- the control section below the purpose covers the
  control under focus, and the menu labels carry every shortcut.
"""

from __future__ import annotations

# Re-exported so Weather's help code and tests need one import, matching the
# Radio and Cast catalogues.
from quill.core.control_help import (
    compose_control_body as compose_control_body,
)
from quill.core.control_help import (
    role_usage as role_usage,
)

#: Surface purposes by exact window title.
PURPOSES: dict[str, str] = {
    # -- the windows -------------------------------------------------------------
    "Quill Weather": (
        "The main window of the weather watcher. Its real work happens in "
        "the background: it monitors official National Weather Service "
        "alerts for your saved locations and speaks new warnings as they "
        "are issued, even from the system tray. The three buttons open the "
        "full Weather Center, start or stop the watch, and add a place to "
        "watch; closing the window keeps monitoring in the tray by default."
    ),
    "Quill Weather Tutorials": (
        "Guided lessons, one step at a time, that can run the step for you and "
        "notice when you have done it. The contents list is grouped by track and "
        "remembers where you stopped; typing 'here' in the filter box narrows it "
        "to the tutorials about the window you came from. Follow me watches what "
        "the app is doing -- never which key you pressed -- and moves you on by "
        "itself."
    ),
    "Weather Center": (
        "The full text weather report for one location at a time, in "
        "reading order: active alerts first, then current conditions, the "
        "period forecast, the hourly forecast, and the extended daily "
        "outlook. Each list pairs with a read-only detail box below it that "
        "follows your selection, so arrowing a list reads the full official "
        "text. The Location chooser switches places, Refresh re-pulls, and "
        "Add Location and Settings open their own windows."
    ),
    "Add Weather Location": (
        "Save a new place to watch. Type a ZIP code, city, county, or "
        "address and press Search; the matching places come back as a list "
        "so same-named towns are told apart, and Add Selected saves the one "
        "you choose. A bare latitude,longitude pair resolves to that exact "
        "point with no search."
    ),
    "Weather Settings": (
        "Every weather preference in one place: temperature and wind units, "
        "how much forecast to show, which alert severities matter, how "
        "often to refresh, what the Quick Weather line includes, and the "
        "alert sound. Save applies everything at once; Cancel changes "
        "nothing."
    ),
    # -- the shared shell dialogs, as this app titles them -----------------------
    "Customize Quill Weather Features": (
        "Turn whole areas of Quill Weather on or off -- alert monitoring, "
        "NOAA Weather Radio. Turning one off removes its menu items at the "
        "next launch; nothing you have saved is deleted."
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
#: keeps this from being reachable from any surface in the weather tree; it
#: exists so a shared-shell or brand-new window still answers F1 with
#: something true rather than nothing.
GENERIC_PURPOSE = (
    "A Quill Weather window. Tab moves between its controls, Escape closes "
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
