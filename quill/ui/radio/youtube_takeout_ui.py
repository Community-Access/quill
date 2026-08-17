"""Station > Import YouTube Subscriptions...: a file picker, and you are done.

The command behind :mod:`quill.core.radio.youtube_takeout`. A listener asked
whether Quill Radio could sign in to YouTube and sync their history; both are
impossible (Premium is tied to YouTube's own player, and watch history was
removed from third-party reach years ago). What they actually wanted was not
to paste forty channel addresses -- and that needs no account at all.

Three things this deliberately does *not* do, each of which the OAuth route
would have required: no Google sign-in, no Cloud project for the listener to
create, no credential to store. It reads a file they exported themselves, once,
and adds the channels to the branch they already have. It therefore works
offline and in Safe Mode, because nothing here touches the network.

Host-taking functions, like ``youtube_ui`` beside it.
"""

from __future__ import annotations

from typing import Any

TITLE = "Import YouTube Subscriptions"

#: Said before the file picker opens. It names where the file comes from,
#: because "subscriptions.csv" is only obvious to somebody who already knows.
EXPLAINER = (
    "This adds the YouTube channels you already follow, from a file you export "
    "from Google -- no sign-in, no account, and nothing sent anywhere.\n\n"
    "At takeout.google.com, choose YouTube and YouTube Music, limit it to "
    "'subscriptions', and download the archive. Inside it, the file is:\n\n"
    "    YouTube and YouTube Music\\subscriptions\\subscriptions.csv\n\n"
    "This is a one-time import: nothing keeps syncing afterwards, and nothing "
    "runs in the background. Continue to pick the file?"
)


def import_subscriptions(host: Any) -> None:
    """Ask for a Takeout subscriptions.csv and follow every channel in it."""
    wx = host._wx

    confirm = wx.MessageDialog(
        host.frame, EXPLAINER, TITLE, wx.OK | wx.CANCEL | wx.ICON_INFORMATION
    )
    try:
        if host._show_modal_dialog(confirm, TITLE) != wx.ID_OK:
            host._announce("Import cancelled.")
            return
    finally:
        confirm.Destroy()

    picker = wx.FileDialog(
        host.frame,
        "Choose your subscriptions.csv",
        wildcard="Subscriptions export (*.csv)|*.csv|All files (*.*)|*.*",
        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
    )
    try:
        if host._show_modal_dialog(picker, TITLE) != wx.ID_OK:
            host._announce("Import cancelled.")
            return
        path = picker.GetPath()
    finally:
        picker.Destroy()

    _import_file(host, path)


def _import_file(host: Any, path: str) -> None:
    from pathlib import Path

    from quill.core.radio.youtube_channels import ChannelStore
    from quill.core.radio.youtube_takeout import parse_subscriptions

    try:
        # utf-8-sig eats the byte-order mark Excel leaves behind; errors are
        # replaced rather than fatal, because one bad character in a channel
        # name must not cost the listener the whole import.
        text = Path(path).read_text(encoding="utf-8-sig", errors="replace")
    except OSError as error:
        host._announce(f"That file could not be read: {error}")
        return

    channels = parse_subscriptions(text)
    if not channels:
        host._announce(
            "No channels were found in that file. Check it is the subscriptions.csv "
            "from your Google export."
        )
        return

    store = ChannelStore()
    already = {channel.url for channel in store.all()}
    added = 0
    for channel in channels:
        saved = store.add(channel.url, channel.name)
        if saved is not None and saved.url not in already:
            already.add(saved.url)
            added += 1

    skipped = len(channels) - added
    host._announce(_summary(added, skipped))
    refresh = getattr(host, "_refresh_youtube_channels", None)
    if callable(refresh):
        refresh()


def _summary(added: int, already_there: int) -> str:
    """What happened, in one sentence (pure).

    Counts first, and the "already following" number stated rather than
    silently folded in: importing forty channels and hearing "added 3" with no
    explanation reads as a failure.
    """
    if added and already_there:
        return (
            f"Imported {added} channel{'s' if added != 1 else ''}; "
            f"{already_there} you already followed. Find them under YouTube in Browse Stations."
        )
    if added:
        return (
            f"Imported {added} channel{'s' if added != 1 else ''}. "
            "Find them under YouTube in Browse Stations."
        )
    return (
        f"Nothing new to import: you already follow all "
        f"{already_there} channel{'s' if already_there != 1 else ''} in that file."
    )
