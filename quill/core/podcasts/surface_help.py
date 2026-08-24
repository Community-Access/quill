"""What every QUILL Cast window is *for* -- the F1 help's opening paragraph.

Quill Radio authored this first (:mod:`quill.core.radio.surface_help`,
2026-08-23) and the F1 engine went family-wide the same day, but only Radio
had a catalogue: every Cast window answered F1 with the generic sentence,
which is true and useless. This module is Cast's half -- the wx-free
catalogue of surface purposes keyed by window title, composed by
:mod:`quill.ui.app_context_help` exactly as Radio's is.

Keyed by **window title** for the same reasons Radio is: the title is the one
identity a window already announces, the raise-if-open guards key on it too,
and it is what a person quotes back in a bug report. Cast titles carry live
data far more often than Radio's ("My Notes -- Episode 412"), so most entries
here resolve by prefix.

The catalogue is **gated** (GATE-CAST-HELP,
``quill/tools/cast_help_audit.py``): every ``wx.Frame``/``wx.Dialog`` title
constructed in the podcast UI must resolve here, so a new surface cannot ship
without saying what it is for.

Wording rules, unchanged from Radio's, so the entries stay worth reading:

* One to three sentences. The first says what the window is for; the rest say
  what somebody actually does here or the one fact that saves a support email.
* Address the listener ("your shows"), never the developer.
* No key-by-key tours -- the control section below the purpose covers the
  control under focus, and the Keyboard Shortcuts Sheet covers the rest.
"""

from __future__ import annotations

# Re-exported so Cast's help code and tests need one import, matching Radio.
from quill.core.control_help import (
    compose_control_body as compose_control_body,
)
from quill.core.control_help import (
    role_usage as role_usage,
)

#: Surface purposes by exact window title.
PURPOSES: dict[str, str] = {
    # -- the windows -------------------------------------------------------------
    "Closing QUILL Cast": (
        "What closing the window should do: exit, or keep playing with QUILL "
        "Cast tucked into the system tray. Cancel leaves everything as it "
        "was. Don't ask me again remembers your answer, and Preferences can "
        "set it back to asking."
    ),
    "QUILL Cast": (
        "The main window: what is playing, and the transport for it. Your "
        "shows live in the Podcast Manager, the episodes waiting for you are "
        "in its Inbox, and everything else is one menu away. Nothing here "
        "needs an account, and nothing you listen to leaves this computer."
    ),
    "Podcasts": (
        "The Podcast Manager: every show you follow, the episodes in each, "
        "and every verb that acts on them -- play, download, mark played, "
        "file into a folder, unsubscribe. One list chooses the show, the "
        "other holds its episodes, and Shift+F10 on any row offers "
        "everything that can be done to it."
    ),
    "Downloads": (
        "The download queue, and everything you can do to it. Finished rows "
        'stay until you clear them so "did that actually download?" always '
        "has an answer, and Enter on a saved row opens the folder it landed "
        "in."
    ),
    "Play Queue": (
        "What plays next, in order. Move a row up or down to change the "
        "order, remove one you have changed your mind about, and Enter plays "
        "the highlighted episode now without losing the rest of the queue."
    ),
    "Listening Statistics": (
        "A report of your listening: which shows, how many episodes, how "
        "long, and when. It reads your own local history and nothing leaves "
        "this computer."
    ),
    "Search Everywhere": (
        "One search across everything Cast knows: your shows, their "
        "episodes, show notes and transcripts. Each result says which show "
        "and which episode it came from, and Enter opens the row it names."
    ),
    # -- the dialogs -------------------------------------------------------------
    "Add Podcast": (
        "Follow a new show. Search the directories by name, or paste a feed "
        "address you already have. What you add lands in your library, and "
        "its episodes appear the first time the feed is read."
    ),
    "Feed Credentials": (
        "The user name and password for a private feed -- a paid "
        "subscription, a members-only show. They are kept for this feed "
        "alone and sent to its own host, never to a directory."
    ),
    "Podcast Index Credentials": (
        "Your own Podcast Index API key and secret, if you have them. Cast "
        "ships with a working key; entering yours here means directory "
        "searches count against your quota rather than the shared one."
    ),
    "Import OPML": (
        "Bring shows in from another podcast app's OPML export. Choose the "
        "file, review what it found, and import; anything you already follow "
        "is left alone rather than added twice."
    ),
    "OPML Import Report": (
        "What the import actually did: how many shows were added, how many "
        "were already followed, and every feed that could not be read, with "
        "its reason. Copy All takes the report with you."
    ),
    "Smart Playlist Rules": (
        "The rules that build a smart playlist: which shows it draws from, "
        "how old an episode may be, whether played episodes count, and how "
        "many it holds. The playlist rebuilds itself from these rules -- you "
        "never add episodes to it by hand."
    ),
    "Podcast Settings": (
        "Every podcast setting in one place: how often feeds are checked, "
        "how many episodes are kept, where downloads land, what happens when "
        "an episode finishes, and how rows are spoken. Each setting applies "
        "the moment you save."
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
    "Skip Settings": (
        "How far each skip key moves, forward and back, and the intro and "
        "outro amounts an episode can skip by itself. A show can override "
        "any of this for itself in its own Settings."
    ),
    "Mark All as Played": (
        "Confirm marking every episode listed as played. It says how many "
        "rows this touches before it does anything, and it changes only the "
        "played mark -- no file is deleted."
    ),
    "Move Podcasts to Folder": (
        "File the chosen shows into a library folder. Folders are yours to "
        "invent; a show sits in one at a time, and moving one changes "
        "nothing about its episodes or its downloads."
    ),
    "Move to Folder": (
        "Choose the folder to file into, or make a new one. Folders are "
        "yours to invent, and filing changes nothing about what is "
        "downloaded or played."
    ),
    "Year in Review": (
        "Your listening year as a short report: the shows you gave the most "
        "time to, how many episodes you finished, and when you listened. It "
        "is built from your own local history."
    ),
    "About This Episode": (
        "Everything the feed says about one episode -- people, links, "
        "chapters, transcripts, funding -- as reviewable, copyable text. "
        "What is missing here is missing from the feed, not hidden by Cast."
    ),
    "Folder Settings": (
        "Settings that apply to every show in one folder: how it is checked, "
        "how much is kept, and what happens when an episode finishes. A show "
        "with its own answer keeps it; the folder answers for the rest."
    ),
    # -- the first-run screens ---------------------------------------------------
    "Welcome to QUILL Cast": (
        "A three-screen tour for a first launch. Nothing here is a setting "
        "you can get wrong: read, press Next, and Skip leaves at any point."
    ),
    "Add your first podcast": (
        "The second first-run screen: the two ways a show gets into your "
        "library -- searching the directories by name, or pasting a feed "
        "address -- and the button that opens Add Podcast right now."
    ),
    "You're set": (
        "The last first-run screen: where your shows live from here, and the "
        "handful of keys worth knowing on day one."
    ),
}

#: Purposes for windows whose titles carry live data, matched by prefix.
PREFIX_PURPOSES: tuple[tuple[str, str], ...] = (
    (
        # The three single-setting editors are titled "<Setting> -- <Show>",
        # so they are matched by prefix; each carries its own sentence on the
        # control itself (single_settings.SingleSetting.help).
        "Episodes to Keep",
        "How many downloaded episodes of this one podcast to keep before the "
        "oldest are deleted. Zero keeps all of them, and it is the downloaded "
        "audio only -- nothing leaves the episode list.",
    ),
    (
        "Queue Expiry",
        "How long this one podcast's episodes wait in the Play Queue before "
        "they drop out. Zero means they wait indefinitely. Dropping out of "
        "the queue does not delete an episode or mark it played.",
    ),
    (
        "Playback Speed",
        "How fast this one podcast plays, remembered between its episodes, so "
        "a host who talks slowly stays sped up without setting it each time.",
    ),
    (
        "Review Chapters",
        "The chapters Cast worked out for this episode, before they are "
        "kept: rename one, drop one that is wrong, and save. Chapters the "
        "feed supplied are never guessed at -- this window appears only for "
        "episodes that arrived without them.",
    ),
    (
        "Chapters",
        "The chapter list of this episode. Enter jumps straight to the "
        "highlighted chapter; the player keeps playing from there.",
    ),
    (
        "My Notes",
        "Your own notes on this episode, each anchored to the moment you "
        "wrote it. Enter jumps playback to a note's position, and a note can "
        "be shared as text with its timestamp.",
    ),
    (
        "Show Notes",
        "The notes the show published with this episode, as reviewable, "
        "copyable text -- links, guests, timestamps. A timestamp here is "
        "live: Enter on one moves playback to it.",
    ),
    (
        "Preview",
        "This show before you follow it: what it is about, and its most "
        "recent episodes. Nothing joins your library until you say so, and "
        "you can play an episode from here to try it first.",
    ),
    (
        "Settings for",
        "Settings for this show alone: how often it is checked, how many "
        "episodes are kept, whether new ones download by themselves, the "
        "speed it plays at, and what to skip at the start and end. Anything "
        "left alone follows your general Podcast Settings.",
    ),
    (
        "About This Episode",
        "Everything the feed says about one episode -- people, links, "
        "chapters, transcripts, funding -- as reviewable, copyable text.",
    ),
    (
        "Folder Settings",
        "Settings that apply to every show in this folder. A show with its "
        "own answer keeps it; the folder answers for the rest.",
    ),
    (
        "Move",
        "Choose the folder to file into, or make a new one. Folders are "
        "yours to invent, and filing changes nothing about what is "
        "downloaded or played.",
    ),
    (
        "File",
        "Choose the Inbox folder to file into, or make a new one. Filing "
        "moves the row out of the Inbox list; it deletes nothing.",
    ),
    (
        "Help:",
        "This is the help window itself: the purpose of the window you were "
        "in, then the control you were on. Escape returns you to it.",
    ),
)

#: The honest fallback for a surface the catalogue does not know. The gate
#: keeps this from being reachable from any surface in the podcast tree; it
#: exists so a Quillin-contributed or brand-new window still answers F1 with
#: something true rather than nothing.
GENERIC_PURPOSE = (
    "A QUILL Cast window. Tab moves between its controls, Escape closes it, "
    "and F1 on any control explains that control."
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
