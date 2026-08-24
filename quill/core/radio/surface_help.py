"""What every Quill Radio window is *for* -- the F1 help's opening paragraph.

QUILL's editor answers F1 with two things: what the window you are standing in
is for, and what the control under focus does. Quill Radio models that here
(2026-08-23, requested directly: "every control and every surface having great
help when F1 is pressed"). This module is the wx-free half: a catalogue of
surface purposes keyed by window title, and the pure text helpers the F1
dialog composes with. The wx half -- finding the focused control, showing the
dialog -- lives in :mod:`quill.ui.radio.context_help`.

Keyed by **window title** rather than by class or module: the title is the one
identity a window already announces to the listener, it is stable (the
raise-if-open guards key on it too), and it is what a person would quote back
in a bug report. Dynamic titles ("Now Playing: WQXR") resolve by prefix.

The catalogue is **gated** (GATE-RADIO-HELP, ``quill/tools/radio_help_audit.py``):
every ``wx.Frame``/``wx.Dialog`` title constructed in the radio UI must
resolve here, so a new surface cannot ship without saying what it is for.

Wording rules, so the entries stay worth reading:

* One to three sentences. The first says what the window is for; the rest say
  what somebody actually does here or the one fact that saves a support email.
* Address the listener ("your favorites"), never the developer.
* No key-by-key tours -- the control section below the purpose covers the
  control under focus, and the Keyboard Shortcuts Sheet covers the rest.
"""

from __future__ import annotations

# The app-agnostic pieces -- the role sentences and the body composition --
# moved to quill.core.control_help when F1 went family-wide (2026-08-23);
# re-exported here so this module stays the one import Radio's help code and
# tests need.
from quill.core.control_help import (
    compose_control_body as compose_control_body,
)
from quill.core.control_help import (
    role_usage as role_usage,
)

#: Surface purposes by exact window title.
PURPOSES: dict[str, str] = {
    # -- the windows -------------------------------------------------------------
    "Quill Radio": (
        "The main window: your favorite stations as a folder tree you play "
        "from. The line at the top says what is playing, the tree is yours to "
        "arrange, and Mute and Volume sit below it. Everything else is one "
        "key away: Ctrl+B browses, Ctrl+G opens the Go To list of places, and "
        "F6 reaches the status bar's transport buttons."
    ),
    "Browse Stations": (
        "A search-free tree for wandering: every source Quill Radio knows -- "
        "your favorites, world directories, podcasts, audiobooks, NOAA "
        "weather, free music -- as branches you expand to reveal stations. "
        "Enter plays the highlighted row, Shift+F10 offers everything else "
        "you can do to it, and Ctrl+F finds within the folder you are in."
    ),
    "Internet Radio": (
        "Field-based station search across every enabled directory at once. "
        "Type a name, narrow by country, language or genre, and play or save "
        "what comes back. Browse Stations (Ctrl+B) is the wandering "
        "counterpart; this window is for when you can already name what you "
        "want."
    ),
    "Search Stations": (
        "Field-based station search across every enabled directory at once. "
        "Type a name, narrow by country, language or genre, and play or save "
        "what comes back."
    ),
    "Manage Favorite Stations": (
        "Your whole favorites collection in one place: search it, play from "
        "it, rename, remove, and arrange stations into folders. Changes save "
        "immediately and the main window's tree follows along."
    ),
    "Schedule Recording": (
        "Record a station at a time you choose, once or on repeat. Add an "
        "entry with a station, a start time and a length; Quill Radio wakes "
        "for it, captures it, and files the recording where the Recordings "
        "window will list it."
    ),
    "Radio Recordings": (
        "Everything you have recorded, live: the capture being written right "
        "now with its size growing, every finished file newest first, and "
        "upcoming scheduled recordings. Enter plays a finished recording; "
        "the Winamp letter keys (X, C, V, B, Z) drive playback if you have "
        "them on."
    ),
    "Downloads": (
        "The download queue, and everything you can do to it. Finished rows "
        'stay until you clear them so "did that actually download?" always '
        "has an answer, and Enter on a saved row opens the folder it landed "
        "in."
    ),
    "Song History": (
        "What each station has played while you listened: every title the "
        "stream reported, newest first, with the time it was heard. From a "
        "song you can copy it, keep it in the Clip Library, or ask for "
        "background on it."
    ),
    "Player": (
        "The whole transport in one small window: what is playing, where you "
        "are in it, and buttons for play, stop, skipping, speed, chapters and "
        "volume. Ctrl+Shift+G opens it from anywhere -- or brings it to the "
        "front if it is already open -- and Escape puts you back where you "
        "came from."
    ),
    "Quill Radio Captions": (
        "The captions for what is playing, as text you can read at your own "
        "pace. Each line joins the ones already spoken and the line being "
        "spoken now is marked with a greater-than sign, so arrowing up "
        "re-reads what you missed. It never announces itself. Turn off Follow "
        "Playback to hold the view still while you read back; Escape closes "
        "the window and turns captions off."
    ),
    "Quill Radio Video": (
        "The picture, when what is playing has one. The audio and every "
        "transport key keep working whether or not this window is open; F11 "
        "fills the screen and Escape leaves full screen."
    ),
    # -- the dialogs -------------------------------------------------------------
    "Add Custom Station": (
        "Add a station Quill Radio's directories do not know, by pasting its "
        "own stream address. Name it what you like; it lands in your "
        "favorites as a custom station and plays like any other."
    ),
    "Audio and Described Audio": (
        "Choose which audio track plays when what you are watching or "
        "listening to carries more than one -- the described-audio track, a "
        "different language, a commentary. For described video, this is where "
        "the description lives."
    ),
    "Audio Health": (
        "Can this installation play and record? Each row names one piece of "
        "the media machinery -- the playback engine, the recorder, the "
        "converters -- and says plainly whether it is present, with a button "
        "to fetch anything missing."
    ),
    "Browse Sources": (
        "Choose which sources appear in the Browse Stations tree. A source "
        "that is off is not merely hidden -- it is never contacted at all."
    ),
    "Caption Settings": (
        "How captions look when a video shows them: size, colors, and "
        "placement. Changes apply to the caption display, not to the video "
        "itself."
    ),
    "Chapters": (
        "The chapter list of what is playing. Enter jumps straight to the "
        "highlighted chapter; the player keeps playing from there."
    ),
    "Closing Quill Radio": (
        "A recording is being written right now, and exiting would stop it. "
        "Exit finishes the file and quits; Minimize to Tray keeps recording "
        "with the window tucked away; Cancel returns to the app. The "
        "checkbox makes your answer permanent -- changeable later in "
        "Preferences."
    ),
    "Download Preferences": (
        "Where downloads land, how they are filed, and whether the queue "
        "keeps going when the window closes. These settings govern every "
        "download, from any source."
    ),
    "Find Streams from a Website": (
        "Point Quill Radio at a web page you know carries a stream, and it "
        "scans the page for playable stream links. Useful for the station "
        "whose website plays fine in a browser but appears in no directory."
    ),
    "Go To": (
        "Every place in Quill Radio, one keystroke away: a numbered list of "
        "destinations that never renumbers itself. Press an entry's number "
        "to go there -- open or not, it opens or comes to the front. Go To "
        "Settings chooses what is listed and in what order."
    ),
    "Go To Settings": (
        "Arrange the Go To menu: which places are in it, in what order, ten "
        "at most -- numbered 1 to 9 then 0, which is why ten. What you use "
        "most belongs at 1, because you will press Ctrl+G then 1 without "
        "reading anything."
    ),
    "Import Stations": (
        "Bring stations in from a playlist file -- M3U, PLS -- or another "
        "player's export. What arrives lands in your favorites; nothing "
        "already there is touched."
    ),
    "Keyboard Shortcuts Sheet": (
        "Every key Quill Radio answers to, in one filterable list, built by "
        "reading the menus in front of you -- so it shows the keys you "
        "actually have, including anything you rebound. Type to filter; "
        "Copy All takes the list with you."
    ),
    "Listening Statistics": (
        "A report of your listening: which stations, how long, and when. It "
        "reads your own local history and nothing leaves this computer."
    ),
    "ACB Media Schedule": (
        "What is on the ten ACB Media channels this week, Sunday to Saturday, "
        "with a heading before each day. Enter tunes in to the highlighted "
        "programme's channel; the buttons and the context menu also offer "
        "Schedule a Recording, Set a Reminder, Add to the Play Queue and Copy "
        "Details. Search narrows the week in place, and the channel box "
        "narrows it to one. The schedule is kept on this computer, so it opens "
        "with no connection and says how old it is when it does."
    ),
    "Set a Reminder": (
        "Be told about this at a time you choose -- a programme in the "
        "schedule, a station, a recording. Pick how much warning you want, "
        "add a note if there is something to say with it, and choose High "
        "priority if it should come through quiet hours. A reminder only "
        "tells you: it never starts, records or queues anything by itself."
    ),
    "Upcoming": (
        "Everything Quill Radio has planned -- reminders and scheduled "
        "recordings together, soonest first, with the kind on every row. "
        "Snooze and Dismiss work on a reminder; a recording is cancelled in "
        "Schedule Recording, where it was made, because Dismiss on the wrong "
        "row would mean a very different morning."
    ),
    "Quiet Hours": (
        "The window in which this app stops speaking on its own: check ticks, "
        "new-episode notices, download notices. Feeds are still checked and "
        "downloads still run -- only the announcements wait -- and anything "
        "you press a key for still answers. The window is shared with the "
        "other Quill listening apps."
    ),
    "Recent Problems": (
        "Everything that has failed recently, in one list that outlives the "
        "announcement: feeds that could not be read, downloads that died, "
        "streams that dropped -- each with its reason and the time it "
        "happened. Retry tries the highlighted row again; nothing here is "
        "sent anywhere."
    ),
    "Record Station": (
        "Record the chosen station, starting now, for a length you set -- or "
        "open-ended with a safety cap. The capture runs in the background; "
        "the Recordings window and the status bar both show its progress."
    ),
    "Recording Settings": (
        "How recordings are made: where the files go, how they are named, "
        "the format they are kept in, and the safety limits that stop an "
        "open-ended capture from filling the disk."
    ),
    "Resume Recording": (
        "Quill Radio closed while this recording was still being written -- "
        "a crash, a shutdown, a log-off. Resume picks the capture back up on "
        "the same station; Dismiss keeps what was saved and lets it go."
    ),
    "Resume Recordings": (
        "Quill Radio closed while these recordings were still being written. "
        "Resume picks the captures back up; Dismiss keeps what was saved and "
        "lets them go."
    ),
    "Search Sources": (
        "Choose which directories Find Stations asks. Fewer sources answer "
        "faster; a source that is off is never contacted."
    ),
    "Sleep Timer": (
        "Stop playback by itself after a time you choose, so the radio does "
        "not play to an empty room all night. The status bar's Sleep timer "
        "cell counts it down; setting a new time replaces the old one."
    ),
    "Station Catalog Status": (
        "Where browsing's answers come from: which sources are stored in the "
        "local station catalog, how fresh each one is, and which are "
        "live-only and why. The catalog is derived data -- it can be rebuilt "
        "from here at any time without touching your favorites."
    ),
    "Wake-Up Timer": (
        "Start a station playing at a time you choose -- an alarm clock that "
        "wakes you to radio. Quill Radio must be running (or in the tray) at "
        "the set time; the status readout here says what is scheduled."
    ),
    "Add from YouTube Playlist": (
        "Bring the entries of a YouTube playlist in as playable items. Pick "
        "the ones you want; each arrives as its own row in your favorites."
    ),
    "Quill Radio Preferences": (
        "Every setting in one place: launch behaviour, closing behaviour, "
        "the playback engine and output device, favorites ordering, "
        "logging, the station catalog, and the shared data folder. Each "
        "setting applies the moment you save."
    ),
    # -- the first-run screens ---------------------------------------------------
    "Welcome to Quill Radio": (
        "A three-screen tour for a first launch. Nothing here is a setting "
        "you can get wrong: read, press Next, and Skip leaves at any point."
    ),
    "Find something to listen to": (
        "The second first-run screen: the two doors to stations -- Browse "
        "Stations for wandering by category, Find Stations for searching by "
        "name -- and the button that opens Browse right now."
    ),
    "Keep the ones you like": (
        "The last first-run screen: how a found station becomes a favorite, "
        "and where favorites live afterwards -- the tree on the main window."
    ),
    # -- small utility prompts ---------------------------------------------------
    "Jump to Time": (
        "Type a position -- 90, 1:30, or 1:02:03 -- and playback moves straight there."
    ),
    "Jump to File": ("Type any part of a recording's name and the list jumps to the first match."),
}

#: Purposes for windows whose titles carry live data, matched by prefix.
PREFIX_PURPOSES: tuple[tuple[str, str], ...] = (
    (
        "Now Playing",
        "Everything known about what is playing, as reviewable, copyable "
        "text: the station's own details, the current track, and the live "
        "playback status. It is a snapshot -- open it again for fresh facts.",
    ),
    (
        "Details:",
        "One station's details -- source, stream address, format, country -- "
        "as reviewable, copyable text, exactly as the search results show "
        "them.",
    ),
    (
        "Song History",
        "What each station has played while you listened: every title the "
        "stream reported, newest first, with the time it was heard.",
    ),
    (
        "Help:",
        "This is the help window itself: the purpose of the window you were "
        "in, then the control you were on. Escape returns you to it.",
    ),
    (
        "Chapters",
        "The chapter list of what is playing. Enter jumps straight to the highlighted chapter.",
    ),
)

#: The honest fallback for a surface the catalogue does not know. The gate
#: keeps this from being reachable from any surface in the tree; it exists so
#: a Quillin-contributed or brand-new window still answers F1 with something
#: true rather than nothing.
GENERIC_PURPOSE = (
    "A Quill Radio window. Tab moves between its controls, Escape closes it, "
    "and F1 on any control explains that control."
)


def purpose_for_title(title: str) -> str:
    """The purpose paragraph for a window titled *title* (never empty)."""
    exact = PURPOSES.get(title.strip())
    if exact:
        return exact
    stripped = title.strip()
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
