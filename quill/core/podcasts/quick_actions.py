"""Quick Actions in QUILL Cast: what each kind of row offers, in order.

The machinery -- the record, the ordering, the repair that keeps an order saved
by another build usable, and the store -- is shared with Quill Radio in
:mod:`quill.core.quick_actions`. This module is Cast's **catalogue**: three
kinds of row, and what each one can do.

The two apps deliberately keep separate stores and separate catalogues. Their
action ids have nothing in common, and one file would mean each app's repair
pass silently discarding the other's list every time it saved. What they share
is the behaviour, and ``DIRECT_KEY_COUNT`` -- so Ctrl+3 is the third action of
whatever list has focus, in Cast and in Radio alike.

wx-free, strict-typed.
"""

from __future__ import annotations

from pathlib import Path

from quill.core import quick_actions as _shared
from quill.core.quick_actions import DIRECT_KEY_COUNT, QuickAction

_FILE_NAME = "podcast_quick_actions.json"

#: Actions on one episode. Order here is the shipped default, chosen so the
#: existing Enter behavior (play it) survives the upgrade unchanged.
EPISODE_ACTIONS: tuple[QuickAction, ...] = (
    QuickAction("play", "Play", "Play this episode now, from where you left off."),
    QuickAction("play_next", "Play Next", "Put it at the front of the Play Queue."),
    QuickAction("add_to_queue", "Add to Queue", "Put it at the end of the Play Queue."),
    QuickAction("download", "Download Episode", "Fetch it for offline listening."),
    QuickAction("toggle_played", "Mark as Played or Unplayed", "Flip this episode's played mark."),
    QuickAction("show_notes", "View Show Notes...", "Read the episode's own notes."),
    QuickAction("episode_notes", "Episode Notes...", "Your timestamped notes on this episode."),
    QuickAction("chapters", "Chapters...", "Browse and jump to this episode's chapters."),
    QuickAction("add_to_playlist", "Add to Playlist...", "File it into a saved playlist."),
    QuickAction("copy_link", "Copy Episode Link", "Copy the audio URL to the clipboard."),
    QuickAction(
        "share_moment",
        "Share This Moment",
        "Copy a sentence and a link that reopen this episode at this second.",
    ),
    QuickAction(
        "save_audio_as",
        "Save Episode Audio As...",
        "Keep your own copy of the audio wherever you choose; downloads it first if need be.",
    ),
    QuickAction(
        "show_in_explorer",
        "Show in File Explorer",
        "Open the folder holding the downloaded file, with it selected.",
    ),
    QuickAction(
        "copy_path",
        "Copy File Path",
        "Copy where the downloaded file is, to paste somewhere else.",
    ),
    QuickAction("file_to_inbox", "File to Inbox Folder...", "Move it inside your Inbox tree."),
    QuickAction(
        "remove_download", "Remove Downloaded Copy", "Delete the local file, keep the episode."
    ),
    QuickAction("rename", "Rename...", "Give the episode your own title."),
)

#: Actions on one podcast.
SHOW_ACTIONS: tuple[QuickAction, ...] = (
    QuickAction(
        "play_next_episode", "Play Next Episode", "Play this show's next unplayed episode."
    ),
    QuickAction("refresh", "Refresh Feed", "Check this show for new episodes now."),
    QuickAction("toggle_favorite", "Add to or Remove from Favorites", "Flip the Favorites star."),
    QuickAction(
        "toggle_auto_queue", "Auto-Queue New Episodes", "New episodes go straight to the queue."
    ),
    QuickAction("toggle_inbox", "Route New Episodes to Inbox", "New episodes land in the Inbox."),
    QuickAction(
        "toggle_notify", "Announce New Episodes", "Say this show's name when it publishes."
    ),
    QuickAction("mark_all_played", "Mark All as Played...", "Dismiss every episode of this show."),
    QuickAction("download_all", "Download All Episodes", "Queue the whole catalog for download."),
    QuickAction(
        "show_settings",
        "Podcast Settings for This Show...",
        "Per-show playback and download settings.",
    ),
    QuickAction(
        "copy_show_link",
        "Copy Podcast Link",
        "Copy this show's feed address to the clipboard.",
    ),
    QuickAction("move_to_folder", "Move to Folder...", "File the show in your library tree."),
    QuickAction("feed_credentials", "Feed Credentials...", "Sign in to a private feed."),
    QuickAction("rename", "Rename...", "Give the show your own title."),
    QuickAction(
        "remove_all_episodes", "Remove All Episodes...", "Empty the episode list, stay subscribed."
    ),
    QuickAction("unsubscribe", "Unsubscribe...", "Remove the show from your library."),
)

#: Actions on one Play Queue slot.
QUEUE_ACTIONS: tuple[QuickAction, ...] = (
    QuickAction("play", "Play", "Play this queued episode now."),
    QuickAction("move_up", "Move Up", "Nudge it one slot earlier."),
    QuickAction("move_down", "Move Down", "Nudge it one slot later."),
    QuickAction("move_to_top", "Move to Top", "Send it to the front of the queue."),
    QuickAction("mark", "Mark for Move", "Mark it, then place it above or below another."),
    QuickAction("remove", "Remove from Queue", "Take it out; the episode itself stays."),
    QuickAction("download", "Download Episode", "Fetch it for offline listening."),
)

#: Actions on one library folder. New in the folder-as-a-lens work: a folder
#: had no actions at all, so there was nothing to order.
FOLDER_ACTIONS: tuple[QuickAction, ...] = (
    QuickAction(
        "play_all_unplayed",
        "Play All Unplayed",
        "Queue the newest unplayed episode of each podcast in this folder.",
    ),
    QuickAction(
        "add_all_to_queue", "Add All to Queue", "Queue every unplayed episode in this folder."
    ),
    QuickAction("move_up", "Move Up", "Move this folder one place earlier."),
    QuickAction("move_down", "Move Down", "Move this folder one place later."),
    QuickAction(
        "folder_settings", "Folder Settings...", "Apply a few settings to every podcast in it."
    ),
    QuickAction("export_opml", "Export This Folder as OPML...", "Write it out as a file."),
    QuickAction("rename", "Rename...", "Give the folder another name."),
    QuickAction("delete", "Delete...", "Remove the folder; its podcasts go up a level."),
)

#: context id -> the actions it offers.
CONTEXTS: dict[str, tuple[QuickAction, ...]] = {
    "episode": EPISODE_ACTIONS,
    "show": SHOW_ACTIONS,
    "queue": QUEUE_ACTIONS,
    "folder": FOLDER_ACTIONS,
}

#: context id -> the words for it, for the reorder dialog and announcements.
CONTEXT_LABELS: tuple[tuple[str, str], ...] = (
    ("episode", "Episode actions"),
    ("show", "Podcast actions"),
    ("queue", "Play Queue actions"),
    ("folder", "Folder actions"),
)


class QuickActionOrders(_shared.QuickActionOrders):
    """Cast's orders, already bound to Cast's catalogue.

    A two-line subclass rather than a factory function, so every existing
    caller -- ``QuickActionOrders()`` for the shipped default,
    ``QuickActionOrders.from_dict(saved)`` for a stored one -- keeps working
    unchanged through the move to the shared implementation. A migration that
    churns its callers is a migration that gets reviewed as a rewrite.
    """

    def __init__(self, orders: dict[str, list[str]] | None = None) -> None:
        super().__init__(
            catalogue=CONTEXTS,
            orders=orders if orders is not None else {},
        )
        if orders is None:
            for context in CONTEXTS:
                self.reset(context)

    @classmethod
    def from_dict(cls, data: object, _catalogue: object = None) -> QuickActionOrders:  # type: ignore[override]
        orders = cls()
        if isinstance(data, dict):
            for context in CONTEXTS:
                raw = data.get(context)
                if isinstance(raw, list):
                    orders.set_order(context, [str(entry) for entry in raw])
        return orders


def default_order(context: str) -> list[str]:
    """The shipped order for one context (also the Reset target)."""
    return _shared.default_order(CONTEXTS, context)


def repair_order(context: str, ids: list[str]) -> list[str]:
    """A saved order made safe for this build."""
    return _shared.repair_order(CONTEXTS, context, ids)


def load_quick_actions(data_dir: Path) -> QuickActionOrders:
    """Cast's saved order, or the shipped default.

    Read through Cast's own subclass rather than the shared loader's return
    value, so what callers get back is the same type they construct.
    """
    import json

    try:
        raw = json.loads((data_dir / _FILE_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return QuickActionOrders()
    return QuickActionOrders.from_dict(raw)


def save_quick_actions(data_dir: Path, orders: QuickActionOrders) -> None:
    """Persist Cast's order atomically."""
    _shared.save_quick_actions(data_dir, orders, file_name=_FILE_NAME)


__all__ = [
    "CONTEXTS",
    "CONTEXT_LABELS",
    "DIRECT_KEY_COUNT",
    "EPISODE_ACTIONS",
    "FOLDER_ACTIONS",
    "QUEUE_ACTIONS",
    "SHOW_ACTIONS",
    "QuickAction",
    "QuickActionOrders",
    "default_order",
    "load_quick_actions",
    "repair_order",
    "save_quick_actions",
]
