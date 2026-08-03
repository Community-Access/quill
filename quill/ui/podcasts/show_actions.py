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

TOP_LEVEL_CHOICE = "(Top level -- no folder)"
NEW_FOLDER_CHOICE = "(New folder...)"


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


def rename_folder_prompt(
    parent: object,
    library: PodcastLibrary,
    folder_id: str,
    *,
    announce: Callable[[str], None],
) -> bool:
    import wx

    folder = library.find_folder(folder_id)
    if folder is None:
        return False
    entry = wx.TextEntryDialog(parent, "Folder name:", "Rename Folder", value=folder.name)
    try:
        if entry.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
            return False
        name = entry.GetValue().strip()
    finally:
        entry.Destroy()
    if not name or name == folder.name:
        return False
    folder.name = name
    announce(f"Folder renamed to {name}")
    return True


def delete_folder_prompt(
    parent: object,
    library: PodcastLibrary,
    folder_id: str,
    *,
    announce: Callable[[str], None],
) -> bool:
    """Confirm, then dissolve the folder -- its shows are never unsubscribed."""
    import wx

    folder = library.find_folder(folder_id)
    if folder is None:
        return False
    answer = wx.MessageBox(  # MSGBOX-OK: parented confirmation for a shared action
        f"Delete the folder {folder.name}?\n\n"
        "Your shows are completely safe: they simply step out of the folder "
        "and land at the top level of your library. Nothing is unsubscribed.",
        "Delete Folder",
        wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT,
        parent,
    )
    if answer != wx.YES:
        return False
    moved = library.delete_folder(folder_id, contents="promote")
    announce(f"Folder {folder.name} deleted; shows moved to the top level.")
    return bool(moved) or True


def create_folder_prompt(
    parent: object,
    library: PodcastLibrary,
    *,
    announce: Callable[[str], None],
    initial_parent_id: str | None = None,
) -> bool:
    """New Folder...: pick where it lives, then name it.

    The folder exists immediately (before any show is filed into it) and
    shows up in every tree and picker.
    """
    import wx

    folders = sorted(library.folders, key=lambda f: f.name.casefold())
    choices = [TOP_LEVEL_CHOICE, *(f.name for f in folders)]
    picker = wx.SingleChoiceDialog(
        parent,
        "Where should the new folder live?",
        "New Folder -- Location",
        choices,
    )
    try:
        if initial_parent_id:
            names = [f.name for f in folders]
            match = next((f for f in folders if f.id == initial_parent_id), None)
            if match is not None:
                picker.SetSelection(names.index(match.name) + 1)
        if picker.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
            return False
        location = picker.GetStringSelection()
    finally:
        picker.Destroy()
    parent_id = None
    if location != TOP_LEVEL_CHOICE:
        match = next((f for f in folders if f.name == location), None)
        parent_id = match.id if match is not None else None
    entry = wx.TextEntryDialog(parent, "Folder name:", "New Folder")
    try:
        if entry.ShowModal() != wx.ID_OK:  # dialog_button_contract: exempt
            return False
        name = entry.GetValue().strip()
    finally:
        entry.Destroy()
    if not name:
        return False
    library.add_folder(name, parent_folder_id=parent_id)
    announce(f"Created folder {name}. File shows into it with Move to Folder.")
    return True


def start_episode_playback(
    controller: object,
    library: PodcastLibrary,
    show: PodcastShow,
    episode: PodcastEpisode,
    *,
    resume_ms: int | None = None,
) -> bool:
    """Start one episode on the shared player, with the show's effective
    settings and an authenticated source (private feeds embed same-host
    credentials for streaming). The one implementation behind every Play
    call site, so speed/EQ/skip settings and feed auth can never drift
    apart between surfaces. Returns False when there is nothing to play."""
    from quill.core.podcasts import feed_auth

    source = feed_auth.playback_source(show, episode)
    if not source:
        return False
    settings = library.effective_settings(show)
    controller.play_episode(
        show_id=show.id,
        episode_guid=episode.guid,
        title=episode.title,
        source=source,
        resume_ms=episode.position_ms if resume_ms is None else resume_ms,
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


def unsubscribe_show_prompt(
    parent: object,
    library: PodcastLibrary,
    show: PodcastShow,
    *,
    announce: Callable[[str], None],
) -> bool:
    """Confirm, then unsubscribe -- optionally deleting downloaded episodes
    per the show's (or library default's) delete-files-on-remove policy."""
    import wx

    downloaded = [e for e in show.episodes if e.downloaded_path]
    policy = library.effective_settings(show).delete_files_on_remove
    answer = wx.MessageBox(  # MSGBOX-OK: parented confirmation for a shared action
        f"Unsubscribe from {show.title}?",
        "Unsubscribe",
        wx.ICON_QUESTION | wx.YES_NO,
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
    if delete_files:
        for episode in downloaded:
            path = Path(episode.downloaded_path)
            if path.exists():
                path.unlink(missing_ok=True)
    # Unsubscribing removes the show's stored private-feed password too --
    # no orphaned secrets in the credential store (spec S-3).
    from quill.core.podcasts import feed_auth

    feed_auth.delete_feed_password(show.id)
    library.remove_show(show.id)
    if delete_files and downloaded:
        announce(f"Unsubscribed from {show.title} and deleted its downloaded episodes")
    else:
        announce(f"Unsubscribed from {show.title}")
    return True


def download_all_episodes(
    download_queue: PodcastDownloadQueue,
    download_root: Path,
    show: PodcastShow,
    *,
    announce: Callable[[str], None],
) -> int:
    """Queue every not-yet-downloaded, not-already-queued episode of *show*.

    Purely additive, like the existing single-episode Download action -- no
    confirmation prompt. Returns the number of episodes queued.
    """
    queued = 0
    for episode in show.episodes:
        if episode.downloaded_path or download_queue.get(episode.guid) is not None:
            continue
        enqueue_episode_download(download_queue, download_root, show, episode)
        queued += 1
    if queued:
        announce(f"Queued {queued} episode(s) of {show.title} for download")
    else:
        announce(f"Nothing to download for {show.title} -- already downloaded or in progress")
    return queued


def remove_all_episodes_prompt(
    parent: object,
    download_queue: PodcastDownloadQueue,
    show: PodcastShow,
    *,
    announce: Callable[[str], None],
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
    for episode in show.episodes:
        download_queue.cancel_item(episode.guid)
    if delete_files:
        for episode in downloaded:
            path = Path(episode.downloaded_path)
            if path.exists():
                path.unlink(missing_ok=True)
    count = len(show.episodes)
    show.episodes = []
    if delete_files and downloaded:
        announce(f"Removed {count} episode(s) of {show.title} and deleted their downloaded files")
    else:
        announce(f"Removed {count} episode(s) of {show.title}")
    return True
