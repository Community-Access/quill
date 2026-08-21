"""Subscription-library verbs on the browse tree's podcast rows.

Extracted from ``browse_tree_menu`` under GATE-11 the day they were written:
folders, OPML import, and Mark All as Played are one concern -- the shared
podcast library, edited from Radio -- and the menu module stays what it was,
a map from action ids to handlers.

Every confirmation goes through :func:`quill.ui.dialog_contract.show_message_box`
so the question is announced and parented correctly (GATE-16), and every
outcome is spoken in the words the wx-free core helpers return -- the same
sentences the unit tests pin.
"""

from __future__ import annotations

from typing import Any


def new_podcast_folder(dialog: Any, kind: str, args: list[str]) -> None:
    """New Folder... on the Subscriptions root, or inside a library folder."""
    wx = dialog._wx
    parent_id = args[0] if kind == "mypodcastfolder" and args else None
    with wx.TextEntryDialog(  # dialog_button_contract: exempt
        dialog._win, "Folder name:", "New Folder"
    ) as entry:
        if entry.ShowModal() != wx.ID_OK:
            return
        name = entry.GetValue()
    from quill.core.paths import app_data_dir
    from quill.core.radio.podcast_follow import create_podcast_folder

    dialog._announce(create_podcast_folder(app_data_dir(), name, parent_folder_id=parent_id))
    dialog._refresh_selected()


def rename_podcast_folder(dialog: Any, args: list[str]) -> None:
    wx = dialog._wx
    if not args:
        return
    current = dialog._tree.GetItemText(dialog._tree.GetSelection()).split(" (")[0]
    with wx.TextEntryDialog(  # dialog_button_contract: exempt
        dialog._win, "New name:", "Rename Folder", value=current
    ) as entry:
        if entry.ShowModal() != wx.ID_OK:
            return
        name = entry.GetValue()
    from quill.core.paths import app_data_dir
    from quill.core.radio.podcast_follow import rename_podcast_folder as rename_op
    from quill.ui.radio import browse_reveal

    spoken = rename_op(app_data_dir(), args[0], name)
    if browse_reveal.refetch_and_reveal(dialog, folder_id=args[0]):
        dialog._announce(spoken)
    else:
        dialog._announce(spoken + " Refresh Podcasts to update.")


def delete_podcast_folder(dialog: Any, args: list[str]) -> None:
    wx = dialog._wx
    if not args:
        return
    from quill.ui.dialog_contract import show_message_box

    name = dialog._tree.GetItemText(dialog._tree.GetSelection()).split(" (")[0]
    answer = show_message_box(
        f"Delete the folder {name}? Its podcasts and subfolders move up a "
        "level; nothing is unsubscribed.",
        "Delete Folder",
        wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
        dialog._win,
        announce=dialog._announce,
    )
    if answer != wx.YES:
        return
    from quill.core.paths import app_data_dir
    from quill.core.radio.podcast_follow import delete_podcast_folder as delete_op
    from quill.ui.radio import browse_reveal

    spoken = delete_op(app_data_dir(), args[0])
    # The folder is gone; reloading the branch is the whole reveal.
    if browse_reveal.refetch_subscriptions(dialog):
        dialog._announce(spoken)
    else:
        dialog._announce(spoken + " Refresh Podcasts to update.")


def move_show_to_folder(dialog: Any, args: list[str]) -> None:
    """Move to Folder... -- Quill Cast's own picker over the same library."""
    if not args:
        return
    from quill.core.paths import app_data_dir
    from quill.core.podcasts.subscriptions import load_library
    from quill.core.radio.podcast_follow import move_show_to_folder as move_op
    from quill.ui.podcasts.folder_picker_dialog import FolderPickerDialog

    library = load_library(app_data_dir())
    show = library.find_show_by_feed_url(args[0])
    title = show.title if show is not None else "this show"
    picker = FolderPickerDialog(
        dialog._win,
        library=library,
        title=f"Move {title} to Folder",
        announce_cb=dialog._announce,
    )
    result = picker.show()
    if not result.confirmed:
        return
    spoken = move_op(app_data_dir(), args[0], result.folder_id)
    from quill.ui.radio import browse_reveal

    # Reload the branch and walk the cursor to the show in its new folder --
    # the tree showing the move IS the confirmation. The spoken fallback only
    # fires if the selection somehow left the Subscriptions subtree.
    if browse_reveal.refetch_and_reveal(dialog, feed_url=args[0]):
        dialog._announce(spoken)
    else:
        dialog._announce(spoken + " Refresh Podcasts to update.")


def mark_all_played(dialog: Any, args: list[str]) -> None:
    """Mark All as Played... -- the same verb and the same shared state as
    Quill Cast's Episode menu, so the badge clears in both apps.

    Confirmed by name and count, until the listener checks Don't ask me again
    (a shared preference: answered once, quiet in both apps). Afterwards the
    branch reloads with the cursor kept on the show, so the badges clear on
    screen the moment the verb speaks."""
    if not args:
        return
    from quill.core.paths import app_data_dir
    from quill.core.radio.podcast_follow import mark_show_played, unheard_for_feed
    from quill.ui.podcasts.mark_played_confirm_dialog import confirm_mark_all_played
    from quill.ui.radio import browse_reveal

    count = unheard_for_feed(app_data_dir(), args[0])
    name = dialog._tree.GetItemText(dialog._tree.GetSelection()).split(" (")[0]
    if not confirm_mark_all_played(
        dialog._win,
        message=f"Mark all {count} unplayed episode(s) of {name} as played?",
        announce=dialog._announce,
    ):
        return
    spoken = mark_show_played(app_data_dir(), args[0])
    if browse_reveal.refetch_and_reveal(dialog, feed_url=args[0]):
        dialog._announce(spoken)
    else:
        dialog._announce(spoken + " Refresh Podcasts to update.")


def mark_episode_played(dialog: Any, station: Any, *, played: bool) -> None:
    """Mark one episode played or unplayed, from the episode's own row."""
    from quill.core.paths import app_data_dir
    from quill.core.radio.podcast_follow import mark_episode_played as mark_op
    from quill.ui.radio import browse_reveal

    feed = str(getattr(station, "homepage", "") or "")
    audio = str(getattr(station, "stream_url", "") or "")
    spoken = mark_op(app_data_dir(), feed, audio, played=played)
    # Reload so the show's badge tells the new truth; the cursor comes back
    # to the show row (its episode rows reload under it). Best effort -- the
    # library edit itself already happened either way.
    browse_reveal.refetch_and_reveal(dialog, feed_url=feed)
    dialog._announce(spoken)


def hand_to_cast(dialog: Any, station: Any, *, action: str) -> None:
    """Note a QUILL Cast instruction for this episode, and say what will happen.

    A handoff, not a write into Cast's library: both apps load and save the
    library wholesale, so a Radio write while Cast is open would be a
    last-writer-wins clobber waiting to happen. Cast carries it out at its next
    launch, which is why the confirmation is in the future tense -- a message
    implying it had already happened would be a small lie the listener finds
    out about later.
    """
    from quill.core.paths import app_data_dir
    from quill.core.podcasts import radio_actions

    feed = str(getattr(station, "homepage", "") or "")
    audio = str(getattr(station, "stream_url", "") or "")
    title = str(getattr(station, "name", "") or "")
    if not radio_actions.record_action(
        app_data_dir(), feed_url=feed, audio_url=audio, action=action, title=title
    ):
        dialog._announce("That episode could not be handed to QUILL Cast.")
        return
    dialog._announce(radio_actions.ACTION_DONE.get(action, "Noted for QUILL Cast."))


def episode_played(station: Any) -> bool | None:
    """The played state of a subscribed podcast episode, or ``None``.

    ``None`` (no mark item) for anything that is not a subscribed episode --
    the library is only consulted for rows whose source says it could know.
    """
    if station is None:
        return None
    from quill.core.podcasts.radio_listens import PODCAST_EPISODE_SOURCES

    if str(getattr(station, "source", "")) not in PODCAST_EPISODE_SOURCES:
        return None
    try:
        from quill.core.paths import app_data_dir
        from quill.core.podcasts.subscriptions import load_library

        library = load_library(app_data_dir())
        show = library.find_show_by_feed_url(str(getattr(station, "homepage", "") or ""))
        if show is None:
            return None
        audio = str(getattr(station, "stream_url", "") or "")
        episode = next((e for e in show.episodes if e.audio_url == audio), None)
        return bool(episode.played) if episode is not None else None
    except Exception:  # noqa: BLE001 - a menu must never fail on a library read
        return None


def register_cast_handoffs(handlers: dict, dialog: Any, station: Any) -> None:
    """Wire the three Cast handoffs onto an episode row's handler table."""
    from quill.core.podcasts import radio_actions
    from quill.core.radio import cast_handoff

    for row_id, action in (
        (cast_handoff.CAST_PLAY_NEXT, radio_actions.ACTION_QUEUE_TOP),
        (cast_handoff.CAST_ADD_TO_QUEUE, radio_actions.ACTION_QUEUE_BOTTOM),
        (cast_handoff.CAST_SEND_TO_INBOX, radio_actions.ACTION_INBOX),
    ):
        handlers[row_id] = lambda a=action: hand_to_cast(dialog, station, action=a)


def download_all_episodes(dialog: Any, args: list[str]) -> None:
    """Queue every episode the library holds for this show, filed per show.

    The same queue single downloads use (one at a time, resumable, spoken
    progress) -- this only feeds it the whole list, with the show's title as
    the folder group so everything lands under Podcasts\\<Show>\\.
    """
    if not args:
        return
    from quill.core.paths import app_data_dir
    from quill.core.podcasts.subscriptions import load_library
    from quill.core.radio.models import RadioStation
    from quill.ui.radio import download_command

    show = load_library(app_data_dir()).find_show_by_feed_url(args[0])
    if show is None:
        dialog._announce("That show is not in your subscriptions.")
        return
    rows = [
        RadioStation(
            name=episode.title or "Episode",
            stream_url=episode.audio_url,
            homepage=show.feed_url,
            source="Subscribed Podcasts",
            is_recording=True,
        )
        for episode in show.episodes
        if episode.audio_url
    ]
    if not rows:
        dialog._announce("The library has no episodes for this show yet. Open the show first.")
        return
    host = getattr(dialog, "_download_host", dialog)
    download_command.download_book(host, rows, title=show.title or "Podcast")


def remove_all_downloads(dialog: Any, args: list[str]) -> None:
    """Delete this show's downloaded files, confirmed; the library is untouched."""
    wx = dialog._wx
    if not args:
        return
    from quill.core.paths import app_data_dir
    from quill.core.radio import download_cleanup
    from quill.core.radio.podcast_follow import show_facts_for_feed
    from quill.ui.dialog_contract import show_message_box

    _unheard, _episodes, title = show_facts_for_feed(app_data_dir(), args[0])
    count = download_cleanup.downloaded_file_count(app_data_dir(), title)
    if not count:
        dialog._announce("There is nothing downloaded for that show.")
        return
    answer = show_message_box(
        f"Remove {count} downloaded file(s) for {title or 'this show'}? "
        "Your subscription and played state are untouched.",
        "Remove All Downloads",
        wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
        dialog._win,
        announce=dialog._announce,
    )
    if answer != wx.YES:
        return
    dialog._announce(download_cleanup.remove_show_downloads(app_data_dir(), title))


def add_podcast_by_url_prompt(dialog: Any) -> None:
    """Add a Podcast by URL...: paste a feed address, get a subscription.

    The validation and every human-centered refusal live in the wx-free
    :mod:`quill.core.podcasts.add_by_url`; this is the prompt (clipboard
    pre-filled, like every address prompt in the tree), the off-thread
    fetch, and the spoken outcome -- plus the cursor walking to the new
    show when the Subscriptions branch is in view.
    """
    from quill.ui.radio import browse_actions

    url = browse_actions._ask(
        dialog,
        title="Add a Podcast by URL",
        prompt=(
            "Address of the podcast's RSS feed, for example\n"
            "https://example.com/feed.xml -- usually behind a link named\n"
            "RSS or Subscribe on the show's website."
        ),
    )
    if not url:
        return
    dialog._announce("Checking that feed...")

    def _work(**_kwargs: Any) -> Any:
        from quill.core.paths import app_data_dir
        from quill.core.podcasts.add_by_url import add_podcast_by_url

        return add_podcast_by_url(app_data_dir(), url, safe_mode=dialog._safe_mode)

    def _ok(_op: str, outcome: Any) -> None:
        if not dialog._tree:  # the window closed while the feed was checked
            return
        dialog._announce(str(getattr(outcome, "spoken", "") or ""))
        if getattr(outcome, "ok", False) and getattr(outcome, "feed_url", ""):
            from quill.ui.radio import browse_reveal

            browse_reveal.refetch_and_reveal(dialog, feed_url=outcome.feed_url)

    def _failed(_op: str, error: object) -> None:
        if dialog._tree:
            dialog._announce(f"That feed could not be checked. {error}.")

    dialog._task_manager.submit("radio-add-podcast-url", _work, on_success=_ok, on_failure=_failed)


def import_opml(dialog: Any) -> None:
    """Import Podcasts from OPML... on the Podcasts branch itself.

    The parse/plan/apply runs off the UI thread -- a two-thousand-line file
    must not freeze the tree -- and the outcome is spoken in full.
    """
    wx = dialog._wx
    if dialog._safe_mode:
        dialog._announce("Importing is disabled in Safe Mode. Restart Quill Radio normally.")
        return
    with wx.FileDialog(  # dialog_button_contract: exempt
        dialog._win,
        "Import Podcasts from OPML",
        wildcard="OPML files (*.opml;*.xml)|*.opml;*.xml|All files (*.*)|*.*",
        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
    ) as chooser:
        if chooser.ShowModal() != wx.ID_OK:
            return
        path = chooser.GetPath()
    dialog._announce("Importing podcasts...")

    def _work(**_kwargs: Any) -> str:
        from quill.core.paths import app_data_dir
        from quill.core.podcasts.opml_import import import_opml_file

        return import_opml_file(app_data_dir(), path).spoken

    def _ok(_op: str, spoken: object) -> None:
        # Reload the branch rather than telling somebody to do it: an import
        # that added forty shows and left the tree saying "you have none" is
        # the one moment the list is most obviously wrong.
        from quill.ui.radio import browse_reveal

        if browse_reveal.refetch_subscriptions(dialog):
            dialog._announce(str(spoken))
        else:
            dialog._announce(f"{spoken} Refresh Podcasts to see them.")

    def _failed(_op: str, error: object) -> None:
        dialog._announce(f"That file could not be imported. {error}.")

    dialog._task_manager.submit("radio-opml-import", _work, on_success=_ok, on_failure=_failed)
