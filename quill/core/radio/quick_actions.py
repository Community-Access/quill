"""Quick Actions for Quill Radio rows: what each kind of row offers, in order.

QUILL Cast has had this since 1.1.0 and Radio has not, so the same idea -- "put
the actions I use at the top, and let Enter be the one I mean" -- worked in one
of the two apps a listener uses for the same job. Radio's rows built a fixed
menu (:mod:`quill.core.radio.row_actions`) and there was nothing to reorder.

The machinery is shared (:mod:`quill.core.quick_actions`); this module is only
the catalogue: three kinds of row, and what each one can do. **The ids are
``row_actions``' own ids, verbatim.** That is not tidiness -- it is the only
thing that stops the reorder dialog and the context menu drifting apart, and
``tests/unit/core/radio/test_radio_quick_actions.py`` fails the build if an id
here is one no row menu builds. An action a listener can put first and then
never reach is worse than one that was never offered.

**Three contexts, because a Radio row is three different things.** A station is
something you play, favorite and record. A recording is a file you play, rename,
export and delete. A browse node is a place in a tree you open, search inside and
hide. Offering one merged list would mean most of it being irrelevant on any
given row, which is exactly the problem ordering exists to solve.

wx-free, strict-typed, pure data.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from quill.core.quick_actions import (
    QuickAction,
    QuickActionOrders,
    load_quick_actions,
    save_quick_actions,
)

__all__ = [
    "BROWSE_NODE_ACTIONS",
    "CONTEXTS",
    "CONTEXT_LABELS",
    "FILE_NAME",
    "RECORDING_ACTIONS",
    "STATION_ACTIONS",
    "apply_order",
    "load_radio_quick_actions",
    "save_radio_quick_actions",
]

#: Radio's own store. A separate file from Cast's, because the two apps'
#: contexts and action ids have nothing in common and a shared file would mean
#: each app's repair pass silently discarding the other's list.
FILE_NAME = "radio_quick_actions.json"

#: A station row: something you play. The shipped order keeps Enter as Play,
#: which is what it has always been -- an upgrade must not move somebody's
#: default action out from under them.
STATION_ACTIONS: tuple[QuickAction, ...] = (
    QuickAction("play", "Play", "Play this station now."),
    QuickAction("favorite.add", "Add to Favorites", "Keep this station in your own list."),
    QuickAction("favorite.remove", "Remove from Favorites", "Take it out of your list."),
    QuickAction("details", "Station Details...", "Bitrate, country, tags and homepage."),
    QuickAction("copy.link", "Copy Stream Link", "Copy the stream address."),
    QuickAction("station.record", "Record This Station...", "Capture what is playing to a file."),
    QuickAction(
        "station.schedule_recording", "Schedule Recording...", "Record it at a time you choose."
    ),
    QuickAction("download", "Download...", "Fetch this item for offline listening."),
    QuickAction("download.remove", "Remove Download", "Delete the local copy."),
    QuickAction("favorite.rename", "Rename Favorite...", "Give it your own name."),
    QuickAction("open.site", "Open Station Website", "Open the homepage in your browser."),
    QuickAction("view.transcript", "Transcript...", "Read what was said, if there is one."),
    QuickAction("report.bad", "Report Bad Station...", "Tell the directory it is broken."),
    QuickAction("podcast.mark_episode_played", "Mark Episode as Played", "Dismiss this episode."),
    QuickAction(
        "podcast.cast_play_next", "Play Next in QUILL Cast", "Hand it to Cast's queue, first."
    ),
    QuickAction(
        "podcast.cast_add_to_queue", "Add to QUILL Cast Queue", "Hand it to Cast's queue, last."
    ),
    QuickAction(
        "podcast.cast_send_to_inbox", "Send to the QUILL Cast Inbox", "Hand it to Cast's Inbox."
    ),
)

#: A recording row: a file on this machine. Ids match the Recordings window's
#: own buttons rather than ``row_actions``, which does not build that surface.
RECORDING_ACTIONS: tuple[QuickAction, ...] = (
    QuickAction("recording.play", "Play", "Play this recording from where you left off."),
    QuickAction("recording.stop", "Stop Recording", "End a capture that is running."),
    QuickAction("recording.rename", "Rename...", "Give the file your own name."),
    QuickAction("recording.chapters", "Chapters...", "Jump between marks in this recording."),
    QuickAction("recording.transcript", "Transcript...", "Read what was said, if there is one."),
    QuickAction("recording.show_in_folder", "Show in File Explorer", "Open its folder."),
    QuickAction("recording.export", "Export...", "Save a copy somewhere else."),
    QuickAction("recording.delete", "Delete...", "Remove the file from this machine."),
)

#: A browse-tree node: a place, not a thing.
BROWSE_NODE_ACTIONS: tuple[QuickAction, ...] = (
    QuickAction("folder.open", "Open", "Show what is inside."),
    QuickAction("folder.close", "Close", "Collapse it again."),
    QuickAction("folder.refresh", "Refresh", "Fetch this branch again."),
    QuickAction("source.search", "Search Inside This...", "Find something within this branch."),
    QuickAction("favorite.place_add", "Add to Places", "Bookmark this spot in the tree."),
    QuickAction("favorite.place_remove", "Remove from Places", "Drop the bookmark."),
    QuickAction("podcast.download_all_episodes", "Download All Episodes", "Fetch the catalog."),
    QuickAction("podcast.mark_all_played", "Mark All as Played...", "Dismiss the whole show."),
    QuickAction("podcast.move_to_folder", "Move to Folder...", "File it in your library tree."),
    QuickAction("source.hide", "Hide This Source", "Stop showing it in the tree."),
    QuickAction("source.reset", "Reset Sources to Default", "Show every source again."),
)

#: context id -> the actions it offers.
CONTEXTS: dict[str, tuple[QuickAction, ...]] = {
    "station": STATION_ACTIONS,
    "recording": RECORDING_ACTIONS,
    "node": BROWSE_NODE_ACTIONS,
}

#: context id -> the words for it, for the reorder dialog and announcements.
CONTEXT_LABELS: tuple[tuple[str, str], ...] = (
    ("station", "Station actions"),
    ("recording", "Recording actions"),
    ("node", "Browse folder actions"),
)


def load_radio_quick_actions(data_dir: Path) -> QuickActionOrders:
    """Radio's saved order, or the shipped default."""
    return load_quick_actions(data_dir, file_name=FILE_NAME, catalogue=CONTEXTS)


def save_radio_quick_actions(data_dir: Path, orders: QuickActionOrders) -> None:
    """Persist Radio's order."""
    save_quick_actions(data_dir, orders, file_name=FILE_NAME)


def apply_order(
    actions: Sequence[Any], orders: QuickActionOrders | None, context: str
) -> list[Any]:
    """Reorder a row's built menu to match the listener's preference.

    Takes ``RowAction`` values rather than :class:`QuickAction` ones, because
    what a *particular* row offers is decided by that row -- a station that is
    already a favorite offers Remove and not Add, and a live stream offers no
    Download at all. The preference orders what is there; it never conjures an
    action onto a row that cannot do it, which is the failure a naive "just show
    the listener's list" would produce.

    Anything the preference does not mention keeps its relative position at the
    end, so a row action with no Quick Actions entry yet is still reachable.
    """
    rows = list(actions)
    if orders is None:
        return rows
    ranking = {action_id: index for index, action_id in enumerate(orders.order(context))}
    if not ranking:
        return rows
    tail = len(ranking)
    return sorted(
        rows,
        key=lambda row: (ranking.get(str(getattr(row, "id", "")), tail), rows.index(row)),
    )
