"""Station > Connect YouTube Account...: sign in, then import subscriptions live.

The command behind :mod:`quill.core.radio.youtube_oauth`, in the shape of
:mod:`quill.ui.radio.youtube_takeout_ui` beside it. Both end at the same place
-- channels added to :class:`~quill.core.radio.youtube_channels.ChannelStore`
-- so a listener sees one YouTube branch no matter which import path they used.
The difference is entirely upstream: this one signs in for a live answer
instead of reading a file exported by hand.

Gated behind the ``future.youtube_oauth`` feature (locked off in a public
build until the OAuth consent screen is verified -- see the core module's
docstring), Safe Mode, and this build actually carrying a bundled OAuth client.
The sign-in itself is a blocking browser round trip, so it always runs off the
UI thread via the task manager, exactly like Add from YouTube Playlist beside
it.
"""

from __future__ import annotations

from typing import Any

CONNECT_TITLE = "Connect YouTube Account"

#: Said before the browser opens. Names exactly what leaves the machine and
#: what does not, mirroring the existing YouTube playback consent notice.
CONNECT_EXPLAINER = (
    "This signs you in with your own Google account to list the YouTube "
    "channels you already subscribe to, then adds them to your YouTube "
    "channels here -- the same list the subscriptions.csv import fills in, "
    "kept live instead of exported by hand.\n\n"
    "QUILL can only READ your subscriptions and playlists. It cannot see your "
    "watch history, cannot post or change anything on your account, and never "
    "sends your Google sign-in to anyone but Google.\n\n"
    "A browser window opens for you to sign in and approve access. Continue?"
)

DISCONNECT_TITLE = "Disconnect YouTube Account"

#: The two outcomes of Disconnect, exactly one of which is spoken. The local
#: sign-in is forgotten in both; only the second needs the listener to act.
DISCONNECTED = "YouTube account disconnected."
DISCONNECTED_LOCALLY = (
    "YouTube account disconnected from QUILL. Google could not be reached, so to "
    "finish, remove QUILL at myaccount.google.com/permissions."
)


def connect_youtube_account(host: Any) -> None:
    """Ask for consent, sign in in the browser, then import subscriptions."""
    from quill.core.radio import youtube_oauth

    wx = host._wx
    if bool(getattr(host, "_safe_mode", False)):
        host._show_message_box(
            "Connecting a YouTube account is unavailable in Safe Mode.",
            CONNECT_TITLE,
            wx.ICON_INFORMATION | wx.OK,
        )
        return
    if not youtube_oauth.available():
        host._show_message_box(
            "This build has no YouTube sign-in configured yet. Use Station, "
            "Import YouTube Subscriptions instead.",
            CONNECT_TITLE,
            wx.ICON_INFORMATION | wx.OK,
        )
        return

    confirm = wx.MessageDialog(
        host.frame, CONNECT_EXPLAINER, CONNECT_TITLE, wx.OK | wx.CANCEL | wx.ICON_INFORMATION
    )
    try:
        if host._show_modal_dialog(confirm, CONNECT_TITLE) != wx.ID_OK:
            host._announce("Connect YouTube Account cancelled.")
            return
    finally:
        confirm.Destroy()

    host._announce("Opening your browser to sign in to Google...")

    def _work(**_kwargs: object) -> object:
        from quill.core.radio import youtube_oauth_api

        youtube_oauth.sign_in(safe_mode=bool(getattr(host, "_safe_mode", False)))
        return youtube_oauth_api.fetch_and_import_subscriptions()

    def _done(_op: str, result: object) -> None:
        added, already = result if isinstance(result, tuple) else (0, 0)
        host._wx.CallAfter(_report_import, host, int(added), int(already))

    def _failed(*args: object) -> None:
        detail = str(args[-1]) if args else ""
        host._wx.CallAfter(
            host._announce, detail or "Connecting your YouTube account did not succeed."
        )

    host._task_manager.submit("youtube-oauth-connect", _work, on_success=_done, on_failure=_failed)


def _report_import(host: Any, added: int, already: int) -> None:
    if added and already:
        message = (
            f"Signed in. Imported {added} channel{'s' if added != 1 else ''}; "
            f"{already} you already followed."
        )
    elif added:
        message = f"Signed in. Imported {added} channel{'s' if added != 1 else ''}."
    else:
        message = "Signed in. No new channels to import -- you already follow all of them."
    host._announce(f"{message} Find them under YouTube in Browse Stations.")
    refresh = getattr(host, "_refresh_youtube_channels", None)
    if callable(refresh):
        refresh()


def disconnect_youtube_account(host: Any) -> None:
    """Revoke QUILL's access at Google and forget the session (channels stay).

    The revoke is a network round trip, so it runs on the task manager; the
    local session is wiped whether or not Google answers, and exactly one
    outcome is spoken.
    """
    from quill.core.radio import youtube_oauth

    wx = host._wx
    if not youtube_oauth.is_signed_in():
        host._announce("No YouTube account is connected.")
        return
    answer = host._show_message_box(
        "Disconnect the YouTube account signed in to QUILL?\n\n"
        "This removes QUILL's access at Google and forgets the sign-in here. "
        "Channels already imported stay in your YouTube list; future "
        "subscription changes stop syncing until you connect again.",
        DISCONNECT_TITLE,
        # No is the default: pressing Enter reflexively must not sign out.
        wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT,
    )
    if answer != wx.YES:
        return

    def _work(**_kwargs: object) -> object:
        return youtube_oauth.sign_out()

    def _done(_op: str, result: object) -> None:
        host._wx.CallAfter(host._announce, DISCONNECTED if result is True else DISCONNECTED_LOCALLY)

    def _failed(*_args: object) -> None:
        host._wx.CallAfter(_forget_after_failure, host)

    host._task_manager.submit(
        "youtube-oauth-disconnect", _work, on_success=_done, on_failure=_failed
    )


def _forget_after_failure(host: Any) -> None:
    """``sign_out`` raised: make sure the local session is gone, then say so."""
    from quill.core.radio import youtube_oauth

    try:
        youtube_oauth.clear_tokens()
    except Exception as error:  # noqa: BLE001 - spoken, never swallowed
        host._announce(f"Could not forget the YouTube sign-in: {error}")
        return
    host._announce(DISCONNECTED_LOCALLY)
