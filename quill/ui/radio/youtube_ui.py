"""Host-side wiring for YouTube stations (#1268): consent, and the resolver.

Two host concerns that do not belong in the playback controller or in a dialog:

* **Consent.** Playing or recording a YouTube link reaches YouTube through
  yt-dlp, which is bundled with the app. The listener is
  asked once -- when a YouTube link is first *added* as a station, not when it
  plays -- and the answer is remembered in ``RadioHistory.youtube_consented``.
  Asking at add time is deliberate: a scheduled recording can fire while nobody
  is at the computer, and that must never be the first time QUILL touches
  YouTube.
* **Resolving.** The controller calls this on a worker thread for every play,
  because YouTube's stream addresses expire within hours and a cached one would
  simply stop working mid-listen.

The frame keeps two thin delegating methods; the policy lives here, next to the
text the listener actually reads.
"""

from __future__ import annotations

from typing import Any

from quill.ui import modal_stack

#: The one-time consent + rights notice. Mirrors the converter's URL-import
#: notice (#1255 §4.6): same component, same rights reminder.
#:
#: It no longer promises a download. yt-dlp is bundled now, so the first
#: YouTube link installs nothing -- and a notice that says otherwise asks
#: someone to agree to something that will not happen, which is a worse kind of
#: wrong than saying too little. What is still worth consenting to is the part
#: that remains true: adding the station means contacting YouTube.
#: Rewritten when video shipped. The old text promised only that Quill Radio
#: found "the audio stream behind the page", which stopped being the whole truth
#: the moment a picture could be shown -- and a consent notice that understates
#: what happens is not consent. The **flag** deliberately does not reset:
#: somebody who consented to YouTube has consented to YouTube, and asking twice
#: for a superset of the same thing is friction rather than ethics. The change is
#: stated plainly in the release notes for everyone who already agreed.
YOUTUBE_CONSENT = (
    "Adding a YouTube link lets Quill Radio play and record it like any other "
    "station. To do that it contacts YouTube to find the audio -- or, if you ask "
    "to see the picture, the video -- behind the page, every time the station "
    "plays. YouTube's own stream addresses expire after a few hours.\n\n"
    "Quill Radio plays audio only unless you press Show Video. It never "
    "downloads a video, and it never embeds YouTube's own player.\n\n"
    "The component that does this, yt-dlp, is already included; nothing is "
    "downloaded or installed.\n\n"
    "Only play or record content you have the right to. Video raises more of "
    "those questions than audio does. QUILL sends no account or credential to "
    "YouTube, and this is unavailable in Safe Mode.\n\n"
    "Continue?"
)

YOUTUBE_TITLE = "YouTube station"


def ask_youtube_consent(host: Any) -> bool:
    """Ask once, remember the answer, and report whether YouTube may be used."""
    wx = host._wx
    if bool(getattr(host, "_safe_mode", False)):
        host._show_message_box(
            "YouTube stations are unavailable in Safe Mode.",
            YOUTUBE_TITLE,
            wx.ICON_INFORMATION | wx.OK,
        )
        return False
    history = host._radio_history
    if bool(getattr(history, "youtube_consented", False)):
        return True
    if (
        host._show_message_box(YOUTUBE_CONSENT, YOUTUBE_TITLE, wx.ICON_QUESTION | wx.YES_NO)
        != wx.YES
    ):
        host._announce("YouTube station cancelled.")
        return False
    history.youtube_consented = True
    try:
        from quill.core.paths import app_data_dir
        from quill.core.radio import history as radio_history

        radio_history.save_history(app_data_dir(), history)
    except Exception:  # noqa: BLE001 - a failed save must never block playback
        pass
    return True


#: Prompt for the playlist command. A playlist link is long and always pasted,
#: never typed, so the field starts with whatever is already on the clipboard.
PLAYLIST_PROMPT = (
    "Paste a YouTube playlist link (youtube.com/playlist?list=...).\n\n"
    "Quill Radio will list its videos so you can choose which to add as "
    "stations. Listing asks YouTube once for the whole playlist; no video's "
    "audio is fetched until you play it."
)

PLAYLIST_TITLE = "Add from YouTube Playlist"


def _clipboard_text(host: Any) -> str:
    """Whatever text is on the clipboard, or "". Never raises."""
    wx = host._wx
    try:
        if not wx.TheClipboard.Open():
            return ""
        try:
            data = wx.TextDataObject()
            if wx.TheClipboard.GetData(data):
                return str(data.GetText() or "").strip()
        finally:
            wx.TheClipboard.Close()
    except Exception:  # noqa: BLE001 - an unavailable clipboard is not an error
        return ""
    return ""


def add_youtube_playlist(host: Any) -> None:
    """Ask for a playlist link, list it off-thread, and offer its videos.

    The resolve is a network round trip, so it never runs on the UI thread: a
    frozen window is unusable with a screen reader, and the freeze would land
    exactly when the listener pressed OK.
    """
    from quill.core.radio.youtube import is_youtube_playlist_url

    wx = host._wx
    if not ask_youtube_consent(host):
        return

    prefill = _clipboard_text(host)
    if not is_youtube_playlist_url(prefill):
        prefill = ""
    entry = wx.TextEntryDialog(
        modal_stack.parent_window(host), PLAYLIST_PROMPT, PLAYLIST_TITLE, value=prefill
    )
    try:
        if host._show_modal_dialog(entry, PLAYLIST_TITLE) != wx.ID_OK:
            return
        url = entry.GetValue().strip()
    finally:
        entry.Destroy()
    if not url:
        return
    if not is_youtube_playlist_url(url):
        host._show_message_box(
            "That is not a YouTube playlist link.\n\n"
            "A playlist address looks like youtube.com/playlist?list=... . "
            "A link to a single video -- even one copied while a playlist was "
            "open -- adds just that video through Add Custom Station.",
            PLAYLIST_TITLE,
            wx.ICON_INFORMATION | wx.OK,
        )
        return

    host._announce("Listing that playlist...")

    def _work(**_kwargs: object) -> object:
        from quill.core.radio.youtube import (
            _default_installer,
            resolve_youtube_playlist_details,
            youtube_available,
        )

        # Same on-demand install ensure_and_resolve performs for a station:
        # consent was given above, so first use may install yt-dlp here.
        if not youtube_available():
            _default_installer(None)
        # Details, not just entries: the playlist's own name comes back in the
        # same request, and heading the picker with it beats the raw address.
        return resolve_youtube_playlist_details(url)

    def _done(_op: str, result: object) -> None:
        host._wx.CallAfter(_open_playlist_picker, host, result, url)

    def _failed(*args: object) -> None:
        detail = str(args[-1]) if args else ""
        host._wx.CallAfter(
            host._announce,
            detail or "That YouTube playlist could not be opened.",
        )

    host._task_manager.submit("youtube-playlist", _work, on_success=_done, on_failure=_failed)


UPDATE_TITLE = "Update YouTube Support"


def update_youtube_support(host: Any) -> None:
    """Fetch a newer yt-dlp than the one built into this build.

    yt-dlp ships inside the app, so YouTube works with no download -- but
    YouTube changes how it serves audio every so often, and when it does the
    bundled copy stops resolving links until upstream fixes it. Upstream ships
    those fixes far more often than Quill Radio ships releases, so this is the
    escape hatch: it installs the current yt-dlp into the engine-pack folder,
    which from then on takes precedence over the bundled copy.

    Off in Safe Mode, and it reaches the network, so it asks first.
    """
    wx = host._wx
    if bool(getattr(host, "_safe_mode", False)):
        host._announce("Updating YouTube support is disabled in Safe Mode.")
        return
    answer = host._show_message_box(
        "Quill Radio already includes YouTube support, so you only need this if "
        "YouTube links have stopped working.\n\n"
        "It downloads the current version of the yt-dlp helper (about 3 MB) from "
        "the Python package index and uses it in place of the built-in copy from "
        "now on.\n\nDownload it now?",
        UPDATE_TITLE,
        wx.ICON_QUESTION | wx.YES_NO,
    )
    if answer != wx.YES:
        return
    _install_youtube_support(host)


def offer_stale_component_update(host: Any, state: Any) -> bool:
    """A YouTube play that failed offers the one-click repair, once per run.

    "If a video doesn't play, can't we prompt the user to update the component
    automagically?" (2026-08-23) -- and it is the right question, because this
    particular failure has exactly one cause and exactly one fix. YouTube
    issues stream addresses per player client and stops honouring them for the
    others, so when the bundled yt-dlp falls behind, the resolve still succeeds
    (title, length, chapters all correct) and the address it hands back is
    refused. Nothing else about the app is wrong, and nothing the listener can
    do in the player will help.

    Asked once per session, and only for this failure: a dialog that appears
    every time a stream is unreachable would be an app arguing with somebody
    about their network. Answering Yes installs the current yt-dlp and offers
    to play the thing that failed.
    """
    from quill.ui.radio.youtube_playback import STALE_COMPONENT_MESSAGE

    if str(getattr(getattr(state, "state", None), "name", "")) != "ERROR":
        return False
    if STALE_COMPONENT_MESSAGE.split(".")[0] not in str(getattr(state, "message", "")):
        return False
    if getattr(host, "_youtube_update_offered", False):
        return False
    host._youtube_update_offered = True
    wx = host._wx
    if bool(getattr(host, "_safe_mode", False)):
        return False
    station = getattr(state, "station", None)
    answer = host._show_message_box(
        "That video did not play, and the reason is almost certainly the "
        "YouTube support component: YouTube changes how it serves audio far "
        "more often than Quill Radio ships releases, and when it does, the "
        "built-in helper stops working until it is updated.\n\n"
        "Download the current version now (about 3 MB) and try again?",
        UPDATE_TITLE,
        wx.ICON_QUESTION | wx.YES_NO,
    )
    if answer != wx.YES:
        host._announce("Left as it is. Station, Update YouTube Support does this at any time.")
        return False
    _install_youtube_support(host, retry=station)
    return True


def _install_youtube_support(host: Any, *, retry: Any = None) -> None:
    """Fetch the current yt-dlp off-thread, then say what happened.

    Shared by the menu command and the offer above, so the repair is one
    implementation with one set of words. *retry*, when given, is the station
    to play again once the new component is in place -- the failed play is the
    reason the listener said yes, so finishing it is the actual answer.
    """
    host._announce("Updating YouTube support...")

    def _work(**_kwargs: object) -> object:
        from quill.core.speech.engine_install import install_yt_dlp

        install_yt_dlp(None)
        from quill.core.radio.youtube import youtube_version

        return youtube_version()

    def _report(message: str, icon: int) -> None:
        host._show_message_box(message, UPDATE_TITLE, icon | host._wx.OK)

    def _done(_op: str, result: object) -> None:
        version = str(result or "")
        named = (
            f"YouTube support is now version {version}."
            if version
            else "YouTube support was updated."
        )
        if retry is not None:
            host._wx.CallAfter(_finish_update_and_retry, host, named, retry)
            return
        host._wx.CallAfter(
            _report,
            f"{named}\n\nIt is in use from now on, in place of the built-in copy. "
            "If a video was refusing to play, try it again.",
            host._wx.ICON_INFORMATION,
        )

    def _failed(*args: object) -> None:
        detail = str(args[-1]) if args else ""
        host._wx.CallAfter(
            _report,
            "YouTube support could not be updated, so the built-in version is still in use."
            + (f"\n\n{detail}" if detail else ""),
            host._wx.ICON_ERROR,
        )

    host._task_manager.submit("youtube-update", _work, on_success=_done, on_failure=_failed)


def _finish_update_and_retry(host: Any, named: str, station: Any) -> None:
    """Say the component is new, then play the thing that failed."""
    host._show_message_box(
        f"{named}\n\nQuill Radio will try that video again now.",
        UPDATE_TITLE,
        host._wx.ICON_INFORMATION | host._wx.OK,
    )
    controller = getattr(host, "_radio_controller", None)
    if controller is not None and station is not None:
        controller.play_station(station)


def _open_playlist_picker(host: Any, result: object, url: str) -> None:
    """Show the resolved playlist, or say why there is nothing to show."""
    title = ""
    if isinstance(result, tuple) and len(result) == 2 and isinstance(result[0], str):
        title, payload = result
    else:  # a bare entries sequence (older callers, tests)
        payload = result
    entries = list(payload) if isinstance(payload, (list, tuple)) else []
    if not entries:
        host._announce(
            "That playlist has no videos Quill Radio can add. It may be private, empty, or removed."
        )
        return

    from quill.ui.radio.youtube_playlist_dialog import YouTubePlaylistDialog

    host._announce(f"{len(entries)} videos in that playlist.")
    dialog = YouTubePlaylistDialog(
        host.frame,
        entries=entries,
        playlist_title=title or url,
        show_modal_dialog=host._show_modal_dialog,
        announce=host._announce,
        add_stations=lambda chosen: add_playlist_entries_as_stations(host, chosen),
    )
    dialog.show()


def add_playlist_entries_as_stations(host: Any, entries: list[Any]) -> tuple[int, int]:
    """Add chosen playlist videos to favorites. Returns ``(added, skipped)``.

    Each entry is saved exactly as a pasted YouTube link would be: the durable
    *page* URL, never a resolved stream address, because YouTube's expire within
    hours. Duplicates are skipped rather than added twice -- adding a playlist
    twice should be harmless.
    """
    from quill.core.radio.models import RadioStation

    store = host._radio_favorites
    added = 0
    skipped = 0
    for entry in entries:
        page_url = str(getattr(entry, "page_url", ""))
        if not page_url:
            skipped += 1
            continue
        if store.find(page_url) is not None:
            skipped += 1
            continue
        station = RadioStation(
            name=str(getattr(entry, "title", "")) or page_url,
            stream_url=page_url,
            source="YouTube",
        )
        # add() answers whether anything was actually added since 11.6, so the
        # count is now the truth rather than the number of rows we looked at.
        if store.add(station, custom=True):
            added += 1
        else:
            skipped += 1
    if added:
        # _save_radio_favorites, not _persist_radio_favorites: adding stations is
        # a structural change, and the standalone app's favorites tree has to be
        # rebuilt to show them. _persist_ deliberately skips the UI refresh, so
        # using it here would save the stations and leave the list looking empty.
        host._save_radio_favorites()
    return added, skipped


def resolve_youtube_for_host(host: Any, page_url: str) -> Any:
    """Turn a saved YouTube link into a playable stream (worker thread).

    Returns the whole :class:`~quill.core.radio.youtube.YouTubeStream`, not
    just its URL: the controller needs the video's duration to tell a finished
    video from a live broadcast, and its chapters to offer chapter navigation.
    Both already came back in the same yt-dlp answer, so returning the object
    costs nothing and discarding it cost the feature.

    Raises :class:`quill.core.radio.youtube.YouTubeError` with a speakable
    reason, which the controller announces as the play failure.
    """
    from quill.core.radio.youtube import YouTubeError, ensure_and_resolve

    if bool(getattr(host, "_safe_mode", False)):
        raise YouTubeError("YouTube stations are unavailable in Safe Mode.")
    if not bool(getattr(host._radio_history, "youtube_consented", False)):
        raise YouTubeError(
            "This YouTube station needs the one-time YouTube consent, which has "
            "not been given yet. Press Enter on it again to be asked."
        )
    stream = ensure_and_resolve(page_url)
    _backfill_saved_name(page_url, stream)
    return stream


def _backfill_saved_name(page_url: str, stream: object) -> None:
    """Name a saved video that was filed before its details were fetched.

    Rows added by an older build (or while YouTube was unreachable) carry the
    address as their label. Playing one answers the same question the add-time
    fetch asks, so the shelf heals itself rather than keeping an unreadable row
    forever. Best effort: a failure here must never break playback.
    """
    from quill.core.radio import youtube_saved

    try:
        store = youtube_saved.SavedStore()
        existing = next(
            (i for i in store.all(youtube_saved.VIDEO) if i.url == page_url and not i.name), None
        )
        if existing is not None:
            store.describe(youtube_saved.details_from_stream(page_url, stream))
    except Exception:  # noqa: BLE001 - naming a row is never worth a failed play
        return


#: Prompt for the one add-anything command (QA: a pasted YouTube link had no
#: obvious way in without searching). The link's shape decides where it lands.
LINK_PROMPT = (
    "Paste any YouTube link -- a video, a playlist, or a channel page.\n\n"
    "Quill Radio files it under Browse Stations, YouTube: a video becomes a "
    "playable row, a playlist becomes a folder of its videos, and a channel "
    "is followed with its uploads and playlists."
)

LINK_TITLE = "Add YouTube Link"


def add_youtube_link(host: Any) -> None:
    """Station > Add YouTube Link...: one prompt, filed by what the link is."""
    from quill.core.radio import youtube_saved
    from quill.core.radio.youtube_channels import ChannelStore

    wx = host._wx
    if not ask_youtube_consent(host):
        return
    prefill = _clipboard_text(host)
    if youtube_saved.classify_link(prefill)[0] == "":
        prefill = ""
    entry = wx.TextEntryDialog(host.frame, LINK_PROMPT, LINK_TITLE, value=prefill)
    try:
        if host._show_modal_dialog(entry, LINK_TITLE) != wx.ID_OK:
            return
        url = entry.GetValue().strip()
    finally:
        entry.Destroy()
    if not url:
        return
    kind, canonical = youtube_saved.classify_link(url)
    if not kind:
        host._show_message_box(
            "That does not look like a YouTube link.\n\n"
            "A video looks like youtube.com/watch?v=... or youtu.be/..., a "
            "playlist like youtube.com/playlist?list=..., and a channel like "
            "youtube.com/@name.",
            LINK_TITLE,
            wx.ICON_INFORMATION | wx.OK,
        )
        return
    if kind == "channel":
        ChannelStore().add(canonical)
        _refresh_browse(host)
        host._announce("Following that channel. Find it under Browse Stations, YouTube.")
        return
    youtube_saved.SavedStore().add(kind, canonical)
    _refresh_browse(host)
    what = "playlist" if kind == youtube_saved.PLAYLIST else "video"
    host._announce(f"Added the {what}. Find it under Browse Stations, YouTube.")
    _name_saved_link(host, kind, canonical, what)


def _refresh_browse(host: Any) -> None:
    """Show the new row in the Browse window, if one is open."""
    from quill.ui.radio import browse_refresh

    browse_refresh.reload_open_browse(host, "youtube")


def _name_saved_link(host: Any, kind: str, url: str, what: str) -> None:
    """Learn what the link *is*, off-thread, and say its name when it lands.

    Without this the shelf keeps the address as the row's label, and a saved
    video reads back as eleven characters of video id spelled out one at a
    time. The request is the same one playing it would make; consent was given
    above, so nothing new is being asked of the listener.
    """
    from quill.core.radio import youtube_saved

    def _work(**_kwargs: object) -> object:
        if kind == youtube_saved.PLAYLIST:
            return youtube_saved.fetch_playlist_details(url)
        return youtube_saved.fetch_video_details(url)

    def _ok(_op: str, result: object) -> None:
        if not isinstance(result, youtube_saved.SavedItem) or not result.name:
            return
        youtube_saved.SavedStore().describe(result)
        host._wx.CallAfter(_refresh_browse, host)
        note = f", {result.note}" if result.note else ""
        host._wx.CallAfter(host._announce, f"That {what} is {result.name}{note}.")

    def _failed(*_args: object) -> None:
        return  # the row is saved and plays; its name is the only thing missing

    host._task_manager.submit("youtube-link-details", _work, on_success=_ok, on_failure=_failed)
