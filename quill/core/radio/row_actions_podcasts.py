"""The subscription library's own verbs on the browse tree.

What the Subscriptions root, the Podcasts branch and a library folder offer
beyond play: organising (folders), growing (a pasted feed, an OPML file),
checking every feed, and -- since 3.0.4 -- handing the library to another
app as OPML. Extracted from :mod:`quill.core.radio.row_actions` on
2026-09-28, when the export verb would have taken that module over its
GATE-11 ceiling; the ids stay there, because every caller reads them there.

Export lives on the two rows a listener would look at: the Subscriptions root
and the Podcasts branch itself. Import lives on the Podcasts branch only (the
Subscriptions root offers it while empty, as a row), which the existing test
pins.
"""

from __future__ import annotations

from quill.core.podcasts import alert_toggle
from quill.core.radio.row_actions import (
    ADD_PODCAST_URL,
    DELETE_PODCAST_FOLDER,
    EXPORT_OPML,
    IMPORT_OPML,
    NEW_PODCAST_FOLDER,
    REFRESH_ALL_PODCASTS,
    RENAME_PODCAST_FOLDER,
    TOGGLE_ALERT,
    FolderState,
    RowAction,
)


def library_actions(kind: str, state: FolderState) -> list[RowAction]:
    """The library verbs for a folder row, in menu order; empty for other rows."""
    actions: list[RowAction] = []
    if kind == "mypodcasts":
        # The Subscriptions root organizes the library in place -- and grows
        # it: pasting a feed address is how a show that no directory lists
        # gets in. On this branch and the Podcasts branch only, never on a
        # show or an episode (they already ARE subscriptions).
        actions.append(RowAction(NEW_PODCAST_FOLDER, "New Fo&lder..."))
        actions.append(RowAction(ADD_PODCAST_URL, "Add a Podcast by &URL..."))
        # Refresh on a *show* re-reads that show. This is the other question --
        # "is there anything new anywhere?" -- which otherwise could only be
        # answered by opening every show in turn, and which the automatic check
        # answers on a cadence somebody may not have turned on.
        actions.append(RowAction(REFRESH_ALL_PODCASTS, "Chec&k All Feeds Now"))
        # The way out: the whole library, folders included, as the file every
        # podcast app reads. Beside the way in, so nobody has to know that
        # Quill Cast has the other half of the pair.
        actions.append(RowAction(EXPORT_OPML, "E&xport Podcasts to OPML..."))

    if kind == "apple" and state.root_source:
        # On the Podcasts branch itself: a whole OPML file's worth of shows
        # becomes subscriptions, folders included, shared with Quill Cast --
        # and the paste-a-feed door, same rule as the Subscriptions root.
        actions.append(RowAction(IMPORT_OPML, "I&mport Podcasts from OPML..."))
        actions.append(RowAction(EXPORT_OPML, "E&xport Podcasts to OPML..."))
        actions.append(RowAction(ADD_PODCAST_URL, "Add a Podcast by &URL..."))

    if kind == "mypodcastshow" and state.subscribed:
        # The one alert decision somebody makes without opening settings: tell
        # me about this show, or stop. Settings keeps the three-way choice (and
        # the folder and shared levels behind it); this toggles between the two
        # modes that cannot lose an episode either way, so it is safe to be one
        # keystroke from the row. The label says what pressing it will do.
        actions.append(RowAction(TOGGLE_ALERT, alert_toggle.menu_label(state.alerts_on)))

    if kind == "mypodcastfolder":
        # The same verbs Cast's manager offers on a folder, on the folder.
        # Delete promotes contents -- it can never silently unsubscribe.
        actions.append(RowAction(NEW_PODCAST_FOLDER, "New Fo&lder Inside..."))
        actions.append(RowAction(RENAME_PODCAST_FOLDER, "R&ename Folder..."))
        actions.append(RowAction(DELETE_PODCAST_FOLDER, "Dele&te Folder..."))
        actions.append(RowAction(REFRESH_ALL_PODCASTS, "Chec&k All Feeds Now"))
    return actions
