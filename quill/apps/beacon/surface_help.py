"""What every QuillBeacon window is *for* -- the F1 help's opening paragraph.

Quill Radio authored the first surface catalogue (2026-08-23) and QUILL Cast
the second (2026-08-24); this is Beacon's, in the same shape: a wx-free
catalogue of surface purposes keyed by window title, composed by
:mod:`quill.ui.app_context_help` into every F1 answer. Beacon keeps its whole
app in one package (``quill/apps/beacon``), so the catalogue lives here
rather than under ``quill/core`` -- but it imports no wx and is typed to the
same standard.

Keyed by **window title** for the same reasons the others are: the title is
the one identity a window already announces, and it is what a person quotes
back in a bug report. Beacon's two live-data titles ("Trail -- ...",
"Attachments -- ...") resolve by prefix.

The catalogue is **gated** (GATE-BEACON-HELP,
``quill/tools/beacon_help_audit.py``). Beacon's windows subclass
``wx.Frame``/``wx.Dialog`` and pass their titles through
``super().__init__``, which the shared title scanner cannot see, so title
coverage is pinned window-by-window in
``tests/unit/tools/test_beacon_help_audit.py`` instead: a renamed or new
window must be re-pinned there against this catalogue.

Wording rules, unchanged from Radio's and Cast's:

* One to three sentences. The first says what the window is for; the rest say
  what somebody actually does here or the one fact that saves a support email.
* Address the person ("your bookmarks"), never the developer.
* No key-by-key tours -- the control section below the purpose covers the
  control under focus.
"""

from __future__ import annotations

#: Surface purposes by exact window title.
PURPOSES: dict[str, str] = {
    # -- the windows -------------------------------------------------------------
    "QuillBeacon": (
        "The main window: your whole library of bookmarks -- web pages, "
        "files, podcasts, radio streams -- in three panes. The sidebar "
        "chooses where you are looking, the list shows what is there, and "
        "the details pane reads out everything saved about the selected row. "
        "Everything is local-first: nothing needs an account."
    ),
    "QuillBeacon Player": (
        "The built-in player for one episode or stream, with its chapters "
        "and transcript. Selecting a chapter jumps playback there, and Add "
        "Time Point saves a bookmark at the exact moment you are hearing so "
        "you can come back to it."
    ),
    "Command Palette": (
        "Every command in the app as one searchable list. Type part of a "
        "name to filter, Enter runs the highlighted command, Escape closes "
        "without running anything."
    ),
    # -- the dialogs -------------------------------------------------------------
    "Add Bookmark to QuillBeacon": (
        "Save something new: a web address or a file path, with an optional "
        "title, note, collection, and tags. Only the address is required. "
        "New bookmarks land in the Inbox unless a routing rule files them "
        "into a folder."
    ),
    "Build Search": (
        "A form that writes the search query for you: words, an exact "
        "phrase, exclusions, type, collection, tag, link health, and domain. "
        "Search runs the built query in the main window's search box, where "
        "it can also be saved as a Smart Collection."
    ),
    "Collection Editor": (
        "Create a collection, or edit the one selected in the sidebar: its "
        "name, description, optional parent, sharing mark, and color. "
        "Collections are folders you invent; a bookmark can sit in several."
    ),
    "Publish Collection": (
        "Turn one collection into a read-only web page and manage it: "
        "publish, unpublish, and copy the local preview address. The preview "
        "is served by the capture bridge on this machine; publishing again "
        "refreshes the page with the collection's current contents."
    ),
    "Trail Editor": (
        "Build or edit a learning trail: a titled, ordered list of "
        "bookmarks, each step with its own note. Steps are added from "
        "whatever is selected in the main window's list, and reordered with "
        "Up and Down -- no dragging anywhere."
    ),
    "Review Location Repair": (
        "A saved location resolved poorly, and this is the decision: read "
        "what was saved against what the repair engine proposes, then accept "
        "the repair, keep the old location, or mark the bookmark broken for "
        "later. Nothing is rewritten without your choice."
    ),
    "Add Radio Program": (
        "Save a radio program with its schedule: station, program name, "
        "host, start and end times in 24-hour HH:MM, and an optional stream "
        "address. A station or a program name is enough to save."
    ),
    "Status Center": (
        "How the app is doing, in one readable report: the capture bridge, "
        "sync transport and vault state, library and trash counts, and how "
        "many bookmarks need attention. Refresh re-reads it; nothing here "
        "changes anything."
    ),
    "Preferences": (
        "Every setting in one place. The list on the left picks a section -- "
        "Accessibility, Sync, Capture Bridge, Published Pages, Routing Rules "
        "-- and Apply saves the inline fields; buttons inside the panels act "
        "immediately."
    ),
    "Routing Rule": (
        "One filing rule: when a new web bookmark's address contains the "
        "keyword, it is filed into the folder. The first matching rule in "
        "the Preferences list wins, and each keyword may be used only once."
    ),
    "Accessibility Settings": (
        "How the app speaks and looks: announcement verbosity, high "
        "contrast, text scale, and reduced motion. Apply puts the settings "
        "into effect across the whole window and announces the result."
    ),
    "Smart Collections": (
        "Your saved searches, managed: edit one's name, query, sort, or "
        "scope, or delete it. Deleting a smart collection never touches the "
        "bookmarks it matched -- it is only the saved search that goes."
    ),
    "Smart Collection Editor": (
        "One saved search, editable: its name, the live query it evaluates, "
        "the sort order, and an optional collection scope. The collection "
        "re-runs the query every time it is opened, so it stays current by "
        "itself."
    ),
    "Add Attachment": (
        "Attach one thing to the selected bookmark: a file on disk, a URL, "
        "or an inline note. Pick the kind first; the form shows the field "
        "that kind needs. Attachments stay on this machine and are never "
        "synced."
    ),
    "Sync Settings": (
        "Everything sync in one dialog: the transport (off, a shared folder, "
        "or a hosted server), magic-link sign-in, and the end-to-end "
        "encryption vault. Off is the default -- nothing touches the network "
        "until you configure it here."
    ),
    "Sync History": (
        "What sync has done and what it needs from you: the commit log, the "
        "conflicts waiting for a Local/Remote/Merged decision, and the "
        "pre-sync snapshots you can roll the library back to."
    ),
    "External Player": (
        "Which media player handles handoffs: the default player, optional "
        "paths to VLC and mpv for installs not on PATH, and a per-type "
        "override so radio and podcasts can open in different players."
    ),
}

#: Purposes for windows whose titles carry live data, matched by prefix.
PREFIX_PURPOSES: tuple[tuple[str, str], ...] = (
    (
        "Trail -- ",
        "Step through this trail one bookmark at a time. The list shows "
        "every step with its completion mark, Mark Complete toggles the "
        "current one, and Open Current opens its bookmark. Your place and "
        "progress are saved as you go.",
    ),
    (
        "Attachments -- ",
        "The files, URLs, and notes attached to this one bookmark. View "
        "opens the selected attachment, Add attaches something new, and "
        "Remove takes one off the bookmark without deleting any file on "
        "disk.",
    ),
    (
        "Help:",
        "This is the help window itself: the purpose of the window you were "
        "in, then the control you were on. Escape returns you to it.",
    ),
)

#: The honest fallback for a surface the catalogue does not know. The gate
#: test pins every shipped title above; this exists so a brand-new window
#: still answers F1 with something true rather than nothing.
GENERIC_PURPOSE = (
    "A QuillBeacon window. Tab moves between its controls, Escape closes it, "
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
