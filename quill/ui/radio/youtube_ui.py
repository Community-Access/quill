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

#: The one-time consent + rights notice. Mirrors the converter's URL-import
#: notice (#1255 §4.6): same component, same rights reminder.
#:
#: It no longer promises a download. yt-dlp is bundled now, so the first
#: YouTube link installs nothing -- and a notice that says otherwise asks
#: someone to agree to something that will not happen, which is a worse kind of
#: wrong than saying too little. What is still worth consenting to is the part
#: that remains true: adding the station means contacting YouTube.
YOUTUBE_CONSENT = (
    "Adding a YouTube link lets Quill Radio play and record it like any other "
    "station. To do that it contacts YouTube to find the audio stream behind "
    "the page, every time the station plays -- YouTube's own stream addresses "
    "expire after a few hours.\n\n"
    "The component that does this, yt-dlp, is already included; nothing is "
    "downloaded or installed.\n\n"
    "Only record content you have the right to record. QUILL sends no account "
    "or credential to YouTube, and this is unavailable in Safe Mode.\n\n"
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
    entry = wx.TextEntryDialog(host.frame, PLAYLIST_PROMPT, PLAYLIST_TITLE, value=prefill)
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

    host._announce("Updating YouTube support...")

    def _work(**_kwargs: object) -> object:
        from quill.core.speech.engine_install import install_yt_dlp

        install_yt_dlp(None)
        from quill.core.radio.youtube import youtube_version

        return youtube_version()

    def _done(_op: str, result: object) -> None:
        version = str(result or "")
        host._wx.CallAfter(
            host._announce,
            f"YouTube support updated to {version}." if version else "YouTube support updated.",
        )

    def _failed(*args: object) -> None:
        detail = str(args[-1]) if args else ""
        host._wx.CallAfter(
            host._announce,
            detail or "YouTube support could not be updated. The built-in version is still in use.",
        )

    host._task_manager.submit("youtube-update", _work, on_success=_done, on_failure=_failed)


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
        # RadioFavoritesStore.add returns None, not a bool -- counting its
        # return value would report "added 0" for every successful add.
        store.add(station, custom=True)
        added += 1
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
            "This YouTube station needs the one-time yt-dlp consent. "
            "Add it again from Add Custom Station to accept it."
        )
    return ensure_and_resolve(page_url)
