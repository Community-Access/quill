"""Quick-Action-ordered context menus for the Podcast Manager (1.1.0).

Before this, an episode's right-click menu was a run of ``menu.Append`` calls
in ``manager_dialog.py`` and another run in ``manager_phase4.py``, and the
order was whatever the source order happened to be. Quick Actions makes that
order the listener's, which means the menu can no longer be a sequence of
statements -- it has to be a *table* the order can be applied to.

So this module holds one specification per action: how it is labelled right
now (several are state-dependent -- Mark as Played flips to Mark as Unplayed),
whether it is available right now, and what it does. Building a menu is then
walking the listener's order through that table, and the same table answers
the other two halves of Quick Actions: what Enter does (the first entry) and
what Ctrl+1..Ctrl+9 do (the first nine).

Extracting it also does what GATE-11 asks for rather than what it merely
permits: both dialogs get smaller, and the menus gain a place to grow that is
not a 1,200-line file.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.quick_actions import DIRECT_KEY_COUNT


@dataclass(slots=True)
class ResolvedAction:
    """One action, resolved against the thing it would act on right now."""

    id: str
    label: str
    enabled: bool
    run: Callable[[], None]


def episode_actions(
    dialog: object, show: PodcastShow, episode: PodcastEpisode
) -> dict[str, ResolvedAction]:
    """Every episode action, keyed by id, resolved for this episode."""
    queue_ops = _queue_ops()
    downloaded = bool(episode.downloaded_path)
    queued_item = dialog._download_queue.get(dialog._download_item_id(episode))
    in_flight = queued_item is not None and queued_item.status in (
        "queued",
        "downloading",
        "paused",
    )

    def action(
        action_id: str, label: str, run: Callable[[], None], *, enabled: bool = True
    ) -> tuple[str, ResolvedAction]:
        return action_id, ResolvedAction(action_id, label, enabled, run)

    from quill.core.podcasts.chapter_sources import episode_has_possible_chapters

    return dict([
        action("play", "&Play", lambda: dialog._winamp_play_pair(show, episode)),
        action(
            "play_next",
            "Play Ne&xt",
            lambda: dialog._queue_and_announce(
                lambda: queue_ops.play_next(dialog._library, show.id, episode.guid),
                f"{episode.title} will play next",
            ),
        ),
        action(
            "add_to_queue",
            "Add to &Queue",
            lambda: dialog._queue_and_announce(
                lambda: queue_ops.add_to_queue(dialog._library, show.id, episode.guid),
                f"Added {episode.title} to the Play Queue",
            ),
        ),
        action(
            "download",
            "&Download Episode",
            lambda: dialog._on_download(None),
            enabled=not downloaded and not in_flight,
        ),
        action(
            "toggle_played",
            "Mark as &Unplayed" if episode.played else "Mark as &Played",
            lambda: dialog._on_toggle_played(episode),
        ),
        action(
            "show_notes",
            "&View Show Notes...",
            lambda: dialog._on_view_show_notes(episode),
            enabled=bool(episode.description),
        ),
        action(
            "episode_notes",
            "Episode &Notes...",
            lambda: dialog._on_episode_notes(show, episode),
        ),
        action(
            "chapters",
            "C&hapters...",
            lambda: dialog._on_chapters_click(None),
            enabled=episode_has_possible_chapters(episode),
        ),
        action(
            "add_to_playlist",
            "Add to Play&list...",
            lambda: dialog._on_add_to_playlist(show, episode),
        ),
        action("copy_link", "&Copy Episode Link", lambda: dialog._on_copy_episode_link(episode)),
        action(
            "save_audio_as",
            "&Save Episode Audio As...",
            lambda: dialog._on_save_episode_audio_as(show, episode),
        ),
        action(
            "show_in_explorer",
            "Sho&w in File Explorer",
            lambda: dialog._on_show_episode_in_explorer(episode),
            enabled=downloaded,
        ),
        action(
            "file_to_inbox",
            "F&ile to Inbox Folder...",
            lambda: dialog._on_file_to_inbox_folder(show, episode),
            enabled=show.route_to_inbox,
        ),
        action(
            "remove_download",
            "&Remove Downloaded Copy",
            lambda: dialog._on_remove_download(None),
            enabled=downloaded,
        ),
        action("rename", "Rena&me...\tF2", lambda: dialog._on_rename_episode(episode)),
    ])


def show_actions(dialog: object, show: PodcastShow) -> dict[str, ResolvedAction]:
    """Every podcast action, keyed by id, resolved for this show."""

    def action(
        action_id: str, label: str, run: Callable[[], None], *, enabled: bool = True
    ) -> tuple[str, ResolvedAction]:
        return action_id, ResolvedAction(action_id, label, enabled, run)

    return dict([
        action(
            "play_next_episode",
            "&Play Next Episode",
            lambda: dialog._play_next_unplayed(show),
        ),
        action(
            "refresh",
            "&Refresh Feed",
            lambda: dialog._on_refresh_feed(show),
            enabled=bool(show.feed_url) and not dialog._safe_mode,
        ),
        action(
            "toggle_favorite",
            "Remove from Fa&vorites" if show.is_favorite else "Add to Fa&vorites",
            lambda: dialog._on_toggle_favorite(show),
        ),
        action(
            "toggle_auto_queue",
            "Stop A&uto-Queueing New Episodes" if show.auto_queue else "A&uto-Queue New Episodes",
            lambda: dialog._on_toggle_auto_queue(show),
        ),
        action(
            "toggle_inbox",
            "Stop Routing to &Inbox" if show.route_to_inbox else "Route New Episodes to &Inbox",
            lambda: dialog._on_toggle_route_to_inbox(show),
        ),
        action(
            "toggle_notify",
            "Stop Announcing &New Episodes"
            if show.notify_new_episodes
            else "Announce &New Episodes",
            lambda: dialog._on_toggle_notify(show),
        ),
        action(
            "mark_all_played",
            "Mark All as Pla&yed...",
            lambda: dialog._on_mark_all_played(show),
        ),
        action(
            "download_all", "Download &All Episodes", lambda: dialog._on_download_all_episodes(show)
        ),
        action(
            "show_settings",
            "&Settings for This Podcast...",
            lambda: dialog._on_show_settings(show),
        ),
        action(
            "copy_show_link",
            "Copy Podcast &Link",
            lambda: dialog._on_copy_show_link(show),
            enabled=bool(show.feed_url),
        ),
        action(
            "move_to_folder", "&Move to Folder...", lambda: dialog._on_move_show_to_folder(show)
        ),
        action(
            "feed_credentials",
            "Feed Cre&dentials...",
            lambda: dialog._on_feed_credentials(show),
            enabled=bool(show.feed_url),
        ),
        action("rename", "Rena&me...\tF2", lambda: dialog._on_rename_show(show)),
        action(
            "remove_all_episodes",
            "Remove All &Episodes...",
            lambda: dialog._on_remove_all_episodes(show),
        ),
        action("unsubscribe", "&Unsubscribe", lambda: dialog._on_unsubscribe(None)),
    ])


def ordered_actions(
    dialog: object, context: str, resolved: dict[str, ResolvedAction]
) -> list[ResolvedAction]:
    """*resolved* in the listener's Quick Actions order.

    Actions the order does not mention (a build newer than the saved file)
    still appear, because ``QuickActionOrders.order`` appends anything
    missing -- a menu is never shorter than the build's own action set.
    """
    order = dialog._quick_actions.order(context)
    return [resolved[action_id] for action_id in order if action_id in resolved]


def build_menu(dialog: object, menu: object, actions: list[ResolvedAction]) -> None:
    """Append *actions* to *menu* in order, with their Ctrl+N hints.

    The accelerator text is a hint only -- the keys are dispatched by the
    list's own key handler, since a context menu that is not open cannot
    own an accelerator.
    """
    wx = dialog._wx
    for index, resolved in enumerate(actions):
        label = resolved.label
        if index < DIRECT_KEY_COUNT and "\t" not in label:
            label = f"{label}\tCtrl+{index + 1}"
        item = menu.Append(wx.ID_ANY, label)
        item.Enable(resolved.enabled)
        menu.Bind(wx.EVT_MENU, lambda _e, r=resolved: r.run(), item)


def run_direct_key(actions: list[ResolvedAction], number: int) -> bool:
    """Run the *number*-th action (1-based); False when there is none there
    or it is currently unavailable."""
    index = number - 1
    if not (0 <= index < len(actions)):
        return False
    resolved = actions[index]
    if not resolved.enabled:
        return False
    resolved.run()
    return True


def _queue_ops():
    from quill.core.podcasts import queue as queue_ops

    return queue_ops
