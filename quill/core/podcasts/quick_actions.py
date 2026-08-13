"""Quick Actions (1.1.0): the actions you use, where you expect them.

Earshot's headline idea is a user-ordered action list per content type, whose
first entry is the default and whose remainder fills the VoiceOver rotor. The
rotor has no desktop equivalent, so translating it literally would be
pointless -- but the *idea* translates to three things a Windows app can do
better than a phone:

1. a chosen **default action for Enter** on an episode row and a show row;
2. **context-menu ordering**, so the four items a given listener actually
   uses are the first four, in the same place, every time;
3. **direct keys** -- Ctrl+1 through Ctrl+9 run the first nine actions of
   whichever list has focus, so the common ones need no menu at all.

This module is the pure half: the known action sets, the default order, and a
record that repairs itself against them. Repair matters more than it sounds.
An order saved by a later version can name actions this build has never heard
of, and an order saved by an earlier one will be missing everything added
since; dropping unknown ids and appending missing ones means an upgrade (or a
downgrade, or a synced settings file) can never stand a listener in front of
an empty context menu.

wx-free, strict-typed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

_FILE_NAME = "podcast_quick_actions.json"

#: How many actions the direct Ctrl+N keys reach.
DIRECT_KEY_COUNT = 9


@dataclass(frozen=True, slots=True)
class QuickAction:
    """One orderable action: a stable id and the words the listener sees."""

    id: str
    label: str
    #: Shown in the reorder dialog's description field, so the list is
    #: self-explanatory without a manual.
    description: str = ""


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
        "save_audio_as",
        "Save Episode Audio As...",
        "Keep your own copy of the audio wherever you choose.",
    ),
    QuickAction(
        "show_in_explorer",
        "Show in File Explorer",
        "Open the folder holding the downloaded file, with it selected.",
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

#: context id -> the actions it offers.
CONTEXTS: dict[str, tuple[QuickAction, ...]] = {
    "episode": EPISODE_ACTIONS,
    "show": SHOW_ACTIONS,
    "queue": QUEUE_ACTIONS,
}

#: context id -> the words for it, for the reorder dialog and announcements.
CONTEXT_LABELS: tuple[tuple[str, str], ...] = (
    ("episode", "Episode actions"),
    ("show", "Podcast actions"),
    ("queue", "Play Queue actions"),
)


def default_order(context: str) -> list[str]:
    """The shipped order for one context (also the Reset target)."""
    return [action.id for action in CONTEXTS.get(context, ())]


def repair_order(context: str, ids: list[str]) -> list[str]:
    """A saved order made safe for this build.

    Unknown ids are dropped (an action this build does not have), duplicates
    collapse to their first appearance, and every known action missing from
    the list is appended in its default position order -- so a new action
    added in a later release shows up at the end of an existing listener's
    menu instead of not at all.
    """
    known = {action.id for action in CONTEXTS.get(context, ())}
    seen: set[str] = set()
    ordered: list[str] = []
    for action_id in ids:
        if action_id in known and action_id not in seen:
            seen.add(action_id)
            ordered.append(action_id)
    ordered.extend(action_id for action_id in default_order(context) if action_id not in seen)
    return ordered


@dataclass(slots=True)
class QuickActionOrders:
    """The three ordered lists, one per context."""

    episode: list[str] = field(default_factory=lambda: default_order("episode"))
    show: list[str] = field(default_factory=lambda: default_order("show"))
    queue: list[str] = field(default_factory=lambda: default_order("queue"))

    def order(self, context: str) -> list[str]:
        """The repaired order for *context* (empty for an unknown context)."""
        raw = {"episode": self.episode, "show": self.show, "queue": self.queue}.get(context)
        if raw is None:
            return []
        return repair_order(context, raw)

    def actions(self, context: str) -> list[QuickAction]:
        """The repaired order as real :class:`QuickAction` records."""
        by_id = {action.id: action for action in CONTEXTS.get(context, ())}
        return [by_id[action_id] for action_id in self.order(context) if action_id in by_id]

    def default_action(self, context: str) -> str:
        """The id Enter runs in *context* -- the first in the list."""
        order = self.order(context)
        return order[0] if order else ""

    def set_order(self, context: str, ids: list[str]) -> None:
        repaired = repair_order(context, ids)
        if context == "episode":
            self.episode = repaired
        elif context == "show":
            self.show = repaired
        elif context == "queue":
            self.queue = repaired

    def reset(self, context: str) -> None:
        self.set_order(context, default_order(context))

    def to_dict(self) -> dict[str, list[str]]:
        return {
            "episode": list(self.episode),
            "show": list(self.show),
            "queue": list(self.queue),
        }

    @classmethod
    def from_dict(cls, data: object) -> QuickActionOrders:
        orders = cls()
        if not isinstance(data, dict):
            return orders
        for context in ("episode", "show", "queue"):
            raw = data.get(context)
            if isinstance(raw, list):
                orders.set_order(context, [str(entry) for entry in raw])
        return orders


def _store_path(data_dir: Path) -> Path:
    return data_dir / _FILE_NAME


def load_quick_actions(data_dir: Path) -> QuickActionOrders:
    """Read the saved order (an absent or broken file reads as the default).

    A separate store rather than three list fields on ``PodcastSettings``:
    no per-show override ever wants its own action order, and putting them in
    the settings record would push three lists through every per-show clone.
    """
    try:
        raw = json.loads(_store_path(data_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return QuickActionOrders()
    return QuickActionOrders.from_dict(raw)


def save_quick_actions(data_dir: Path, orders: QuickActionOrders) -> None:
    """Persist the order atomically."""
    from quill.core.storage import write_json_atomic

    write_json_atomic(_store_path(data_dir), orders.to_dict())


__all__ = [
    "CONTEXTS",
    "CONTEXT_LABELS",
    "DIRECT_KEY_COUNT",
    "EPISODE_ACTIONS",
    "QUEUE_ACTIONS",
    "SHOW_ACTIONS",
    "QuickAction",
    "QuickActionOrders",
    "default_order",
    "load_quick_actions",
    "repair_order",
    "save_quick_actions",
]
