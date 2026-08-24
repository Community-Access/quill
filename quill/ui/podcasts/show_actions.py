"""Shared show/folder actions (favorite / move / unsubscribe / folder CRUD).

One implementation behind every surface that acts on a subscribed show --
today the standalone QUILL Cast main panel's tree; the Podcast Manager
dialog keeps its own long-established equivalents for now -- so wording and
announcements for a given action stay identical wherever it's added next.
Mirrors the shape of ``quill/ui/radio/favorite_actions.py``, adapted to
podcasts' id-based folder tree (``PodcastFolder.id``/``parent_folder_id``)
rather than radio favorites' string-path folders.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from quill.core.podcasts.download_queue import PodcastDownloadQueue
from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary

# Re-exported from folder_prompts, which owns the naming prompts since the
# GATE-11 split -- callers import either name from either module.
from quill.ui.podcasts.folder_prompts import (
    NEW_FOLDER_CHOICE as NEW_FOLDER_CHOICE,
)
from quill.ui.podcasts.folder_prompts import (
    TOP_LEVEL_CHOICE as TOP_LEVEL_CHOICE,
)
from quill.ui.podcasts.folder_prompts import (
    create_folder_prompt as create_folder_prompt,
)
from quill.ui.podcasts.folder_prompts import (
    delete_folder_prompt as delete_folder_prompt,
)
from quill.ui.podcasts.folder_prompts import (
    rename_folder_prompt as rename_folder_prompt,
)
from quill.ui.podcasts.folder_prompts import (
    rename_view_prompt as rename_view_prompt,
)
from quill.ui.podcasts.folder_prompts import (
    reset_view_name_action as reset_view_name_action,
)


def toggle_favorite(
    library: PodcastLibrary,
    show: PodcastShow,
    *,
    announce: Callable[[str], None],
) -> None:
    show.is_favorite = not show.is_favorite
    verb = "Added" if show.is_favorite else "Removed"
    preposition = "to" if show.is_favorite else "from"
    announce(f"{verb} {show.title} {preposition} Favorites")


def move_show_to_folder(
    parent: object,
    library: PodcastLibrary,
    show: PodcastShow,
    *,
    announce: Callable[[str], None],
) -> bool:
    """Pick (or create) the library folder this show lives in."""
    import wx

    folders = sorted(library.folders, key=lambda f: f.name.casefold())
    choices = [TOP_LEVEL_CHOICE, *(f.name for f in folders), NEW_FOLDER_CHOICE]
    picker = wx.SingleChoiceDialog(
        parent,
        "Where should this show live?",
        f"Move {show.title} to Folder",
        choices,
    )
    try:
        if picker.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
            return False
        choice = picker.GetStringSelection()
    finally:
        picker.Destroy()
    if choice == NEW_FOLDER_CHOICE:
        entry = wx.TextEntryDialog(parent, "New folder name:", "New Folder")
        try:
            if entry.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
                return False
            name = entry.GetValue().strip()
        finally:
            entry.Destroy()
        if not name:
            return False
        folder_id = library.add_folder(name).id
    elif choice == TOP_LEVEL_CHOICE:
        folder_id = None
    else:
        match = next((f for f in folders if f.name == choice), None)
        folder_id = match.id if match is not None else None
    show.folder_id = folder_id
    label = next((f.name for f in library.folders if f.id == folder_id), None)
    announce(f"Filed {show.title} under {label or 'the top level'}")
    return True


def start_episode_playback(
    controller: object,
    library: PodcastLibrary,
    show: PodcastShow,
    episode: PodcastEpisode,
    *,
    resume_ms: int | None = None,
    announce: Callable[[str], None] | None = None,
) -> bool:
    """Start one episode on the shared player, with the show's effective
    settings and an authenticated source (private feeds embed same-host
    credentials for streaming). The one implementation behind every Play
    call site, so speed/EQ/skip settings and feed auth can never drift
    apart between surfaces. Returns False when there is nothing to play.

    A streamed episode whose audio is already sitting in the playback cache is
    played from that file rather than fetched again -- the same bytes, minus
    the network. See ``core/podcasts/playback_cache.py``."""
    from quill.core.podcasts import feed_auth, playback_cache

    settings = library.effective_settings(show)
    source = ""
    if not episode.downloaded_path and settings.playback_cache:
        cached = playback_cache.cached_audio(show.id, episode.guid, episode.audio_url)
        if cached is not None:
            playback_cache.touch(cached)
            source = str(cached)
    if not source:
        source = feed_auth.playback_source(show, episode)
    if not source:
        return False
    start_ms = episode.position_ms if resume_ms is None else resume_ms
    if resume_ms is None:
        from quill.ui.podcasts.episode_start import cross_app_start

        start_ms, crossed = cross_app_start(show, episode, start_ms)
        if crossed and announce is not None:
            announce(crossed)
    controller.play_episode(
        show_id=show.id,
        episode_guid=episode.guid,
        title=episode.title,
        source=source,
        resume_ms=start_ms,
        rate=settings.speed,
        bass_db=settings.eq_bass_db,
        mid_db=settings.eq_mid_db,
        treble_db=settings.eq_treble_db,
        compressor_enabled=settings.compressor_enabled,
        smart_speed_enabled=settings.smart_speed_enabled,
        auto_skip_intro_ms=settings.auto_skip_intro_seconds * 1000,
        auto_skip_outro_ms=settings.auto_skip_outro_seconds * 1000,
    )
    return True


def enqueue_episode_download(
    download_queue: PodcastDownloadQueue,
    download_root: Path,
    show: PodcastShow,
    episode: PodcastEpisode,
    *,
    item_id: str | None = None,
) -> None:
    """One authenticated episode download -- destination, same-host auth
    header, enqueue. The shared path behind every Download action, so the
    private-feed Authorization header can never be forgotten at a call site."""
    from quill.core.podcasts import feed_auth
    from quill.ui.podcasts.manager_dialog import episode_destination

    destination = episode_destination(download_root, show, episode)
    destination.parent.mkdir(parents=True, exist_ok=True)
    download_queue.enqueue(
        item_id or episode.guid,
        show_id=show.id,
        episode_guid=episode.guid,
        url=episode.audio_url,
        destination=destination,
        auth_header=feed_auth.auth_header_for_url(show, episode.audio_url),
    )


def start_playback_cache(
    cache_queue: PodcastDownloadQueue,
    show: PodcastShow,
    episode: PodcastEpisode,
) -> str:
    """Begin filling the playback cache for a streamed episode.

    Returns the queue item id, or "" when there is nothing to do -- the episode
    is downloaded, already fully cached, or has no https enclosure to fetch.

    Runs on a queue of its own (see ``main_frame_podcasts``) rather than the
    download queue, for two reasons: a forty-episode download batch must never
    leave the episode you are *listening to* waiting behind it for its bytes,
    and a cache fill is not a download and has no business appearing in the
    Downloads list.
    """
    from quill.core.podcasts import feed_auth, playback_cache

    if episode.downloaded_path or not episode.audio_url:
        return ""
    if playback_cache.cached_audio(show.id, episode.guid, episode.audio_url) is not None:
        return ""
    if not episode.audio_url.startswith("https://"):
        return ""
    destination = playback_cache.partial_path(show.id, episode.guid, episode.audio_url)
    item_id = f"cache:{show.id}:{episode.guid}"
    cache_queue.enqueue(
        item_id,
        show_id=show.id,
        episode_guid=episode.guid,
        url=episode.audio_url,
        destination=destination,
        auth_header=feed_auth.auth_header_for_url(show, episode.audio_url),
    )
    return item_id


def announce_if_feed_auth_failure(
    exc: BaseException, show: PodcastShow, *, announce: Callable[[str], None]
) -> None:
    """Background-refresh failure hook: an auth failure gets an actionable
    announcement, never a modal prompt (spec D-2); any other failure stays
    quiet, exactly as refresh always behaved."""
    from quill.core.podcasts import feed_reader

    if isinstance(exc, feed_reader.FeedAuthError):
        announce(
            f"{show.title}: feed sign-in failed. Update credentials with "
            "Feed Credentials on the show's menu."
        )


def append_feed_credentials_item(
    menu: object,
    wx: object,
    *,
    parent: object,
    library: PodcastLibrary,
    show: PodcastShow,
    announce: Callable[[str], None],
    on_changed: Callable[[], None],
) -> None:
    """Add "Feed Credentials..." to a show's context menu (skipped for local
    shows -- there is no feed to sign in to)."""
    if not show.feed_url:
        return
    item = menu.Append(wx.ID_ANY, "Feed Cre&dentials...")
    item.SetHelp(
        "Username and password for a private feed (Patreon-style supporter "
        "feeds). Only ever sent to this feed's own host."
    )

    def _run(_event: object) -> None:
        if feed_credentials_prompt(parent, library, show, announce=announce):
            on_changed()

    menu.Bind(wx.EVT_MENU, _run, item)


def feed_credentials_prompt(
    parent: object,
    library: PodcastLibrary,
    show: PodcastShow,
    *,
    announce: Callable[[str], None],
) -> bool:
    """Set, change, or clear the show's private-feed credentials.

    Saves the username on the show record and the password in the platform
    secret store; returns True when anything changed so the caller persists
    the library. The *library* parameter keeps the signature consistent with
    every other shared action here (and future-proofs a per-library hook).
    """
    del library  # persisted by the caller, like every other shared action
    from quill.core.podcasts import feed_auth
    from quill.ui.podcasts.feed_credentials_dialog import FeedCredentialsDialog

    result = FeedCredentialsDialog(
        parent,
        username=show.feed_username,
        allow_clear=bool(show.feed_username),
        announce_cb=announce,
    ).show()
    if result is None:
        return False
    if result.action == "clear":
        show.feed_username = ""
        feed_auth.delete_feed_password(show.id)
        announce(f"Cleared feed credentials for {show.title}")
        return True
    show.feed_username = result.username
    if result.password:
        feed_auth.save_feed_password(show.id, result.password)
    announce(f"Saved feed credentials for {show.title}")
    return True


def _restores_phrase(episodes: int, files: int) -> str:
    """ "412 episodes and 3 downloaded files" -- what an undo would bring back."""
    parts: list[str] = []
    if episodes:
        parts.append(f"{episodes} episode{'' if episodes == 1 else 's'}")
    if files:
        parts.append(f"{files} downloaded file{'' if files == 1 else 's'}")
    if not parts:
        return ""
    return " and ".join(parts)


def unsubscribe_show_prompt(
    parent: object,
    library: PodcastLibrary,
    show: PodcastShow,
    *,
    announce: Callable[[str], None],
    on_change: Callable[[], None] | None = None,
) -> bool:
    """Confirm, then unsubscribe -- optionally deleting downloaded episodes
    per the show's (or library default's) delete-files-on-remove policy.

    Undoable once (11.3): the show object, its place in the library and any
    files this deleted are all held, so Ctrl+Z puts the whole subscription
    back where it was. *on_change* is what the caller does after either the
    removal or the undo -- save the library, refresh the list.
    """
    import wx

    from quill.ui import undo_last_ui

    downloaded = [e for e in show.episodes if e.downloaded_path]
    policy = library.effective_settings(show).delete_files_on_remove
    answer = wx.MessageBox(  # MSGBOX-OK: parented confirmation for a shared action
        f"Unsubscribe from {show.title}?",
        "Unsubscribe",
        wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT,
        parent,
    )
    if answer != wx.YES:
        return False
    delete_files = policy == "always"
    if downloaded and policy == "ask":
        delete_files = (
            wx.MessageBox(  # MSGBOX-OK: parented confirmation for a shared action
                f"Also delete the {len(downloaded)} downloaded episode file(s)?",
                "Delete Downloaded Files",
                wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT,
                parent,
            )
            == wx.YES
        )
    held: dict[Path, Path] = {}
    if delete_files:
        held = undo_last_ui.hold_or_delete([
            Path(e.downloaded_path) for e in downloaded if e.downloaded_path
        ])
    # Unsubscribing removes the show's stored private-feed password too --
    # no orphaned secrets in the credential store (spec S-3).
    from quill.core.podcasts import feed_auth

    had_password = bool(feed_auth.load_feed_password(show.id))
    feed_auth.delete_feed_password(show.id)
    position = library.shows.index(show) if show in library.shows else len(library.shows)
    library.remove_show(show.id)

    def _undo() -> None:
        library.shows.insert(min(position, len(library.shows)), show)
        undo_last_ui.restore(held)
        if on_change is not None:
            on_change()

    undo_last_ui.remember(
        "Unsubscribe",
        show.title,
        _restores_phrase(len(show.episodes), len(held)),
        _undo,
        # The password is gone by design (spec S-3, no orphaned secrets), and
        # an undo that quietly did not restore it would be the worse answer.
        caveat=(
            "The private-feed password is not restored -- enter it again in Feed Credentials"
            if had_password
            else ""
        ),
        dispose=lambda: undo_last_ui.discard(held),
    )
    if delete_files and downloaded:
        announce(
            undo_last_ui.offer(
                f"Unsubscribed from {show.title} and deleted its downloaded episodes"
            )
        )
    else:
        announce(undo_last_ui.offer(f"Unsubscribed from {show.title}"))
    if on_change is not None:
        on_change()
    return True


def download_all_episodes(
    download_queue: PodcastDownloadQueue,
    download_root: Path,
    show: PodcastShow,
    *,
    announce: Callable[[str], None],
) -> int:
    """Queue this show's not-yet-downloaded, not-already-queued episodes.

    Purely additive, like the existing single-episode Download action -- no
    confirmation prompt. Bounded to :data:`~quill.core.podcasts.download_batch.BATCH_CAP`
    per invocation, and the announcement carries every count (eligible,
    started, skipped, deferred) rather than one number that hides the rest.
    Returns the number of episodes actually started.
    """
    from quill.core.podcasts.download_batch import plan_download_all

    batch = plan_download_all(
        show.episodes,
        already_have=lambda e: bool(e.downloaded_path) or download_queue.get(e.guid) is not None,
    )
    for episode in batch.started:
        enqueue_episode_download(download_queue, download_root, show, episode)
    announce(batch.sentence(show.title))
    return len(batch.started)


def remove_all_episodes_prompt(
    parent: object,
    download_queue: PodcastDownloadQueue,
    show: PodcastShow,
    *,
    announce: Callable[[str], None],
    on_change: Callable[[], None] | None = None,
) -> bool:
    """Confirm, then clear every episode from *show*'s list -- optionally
    deleting downloaded media too, asked as its own follow-up question (same
    two-step shape as :func:`unsubscribe_show_prompt`).

    The show stays subscribed; a future feed refresh can repopulate its
    episode list from the feed itself, unlike Unsubscribe.
    """
    import wx

    if not show.episodes:
        announce(f"{show.title} has no episodes to remove")
        return False
    downloaded = [e for e in show.episodes if e.downloaded_path]
    answer = wx.MessageBox(  # MSGBOX-OK: parented confirmation for a shared action
        f"Remove all {len(show.episodes)} episode(s) of {show.title}? The show "
        "stays subscribed -- a future feed refresh can bring episodes back.",
        "Remove All Episodes",
        wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT,
        parent,
    )
    if answer != wx.YES:
        return False
    delete_files = False
    if downloaded:
        delete_files = (
            wx.MessageBox(  # MSGBOX-OK: parented confirmation for a shared action
                f"Also delete the {len(downloaded)} downloaded episode file(s)?",
                "Delete Downloaded Files",
                wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT,
                parent,
            )
            == wx.YES
        )
    from quill.ui import undo_last_ui

    for episode in show.episodes:
        download_queue.cancel_item(episode.guid)
    held: dict[Path, Path] = {}
    if delete_files:
        held = undo_last_ui.hold_or_delete([
            Path(e.downloaded_path) for e in downloaded if e.downloaded_path
        ])
    count = len(show.episodes)
    # The list itself is the undo: hold the removed episodes rather than the
    # ids of them, so Ctrl+Z restores play positions and played marks too.
    removed = list(show.episodes)
    show.episodes = []

    def _undo() -> None:
        show.episodes = removed
        undo_last_ui.restore(held)
        if on_change is not None:
            on_change()

    undo_last_ui.remember(
        "Remove All Episodes",
        show.title,
        _restores_phrase(count, len(held)),
        _undo,
        dispose=lambda: undo_last_ui.discard(held),
    )
    if delete_files and downloaded:
        announce(
            undo_last_ui.offer(
                f"Removed {count} episode(s) of {show.title} and deleted their downloaded files"
            )
        )
    else:
        announce(undo_last_ui.offer(f"Removed {count} episode(s) of {show.title}"))
    if on_change is not None:
        on_change()
    return True
