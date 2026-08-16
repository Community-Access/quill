"""Import the channels you already follow, from your own Google export.

A listener asked whether Quill Radio could sign in with a YouTube account and
sync their history. Researched against Google's own documentation, both halves
are no: YouTube Premium's benefits are tied to YouTube's own player, and watch
history was removed from third-party reach years ago (``playlistItems.list``
answers ``watchHistoryNotAccessible``). What sat underneath the question was
simpler and entirely answerable -- *I follow forty channels; do not make me
paste forty addresses.*

This does that, and does it **without a Google account ever touching the app**.
Google Takeout hands a listener their own subscriptions as a CSV; they pick the
file, and the channels land in the branch they already have. Compared with the
OAuth route it avoids every risk that made the OAuth route worth refusing:

* no account connected to a program that also extracts streams (our playback
  passes no cookies and no credentials, and this keeps it that way);
* no Google Cloud project for the listener to create -- seven steps of console
  work replaced by a file picker;
* no token to store, refresh, protect, or leak;
* no YouTube API Services call, so none of their terms bind us;
* it works offline, and in Safe Mode, because it reads a local file.

**The shape of the file** (``YouTube and YouTube Music/subscriptions/
subscriptions.csv``): three columns -- Channel ID, Channel URL, Channel title.
Only two matter here, because ``ChannelStore`` stores a URL and a name, and the
URL is already in the export. Deliberately tolerant: the header may be absent,
localized, or reordered, columns may be quoted or not, and an export from a
different tool may carry extra columns. A row that yields no usable channel URL
is skipped rather than failing the import -- one odd row in a hundred should
not cost a listener the other ninety-nine.

Pure and wx-free: it parses text and returns rows. Reading the file and adding
to the store belong to the caller.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass

from quill.core.radio.youtube_channels import normalize_channel_url

#: Column headers we recognise, lowercased. Takeout's own English headers plus
#: the shapes other exporters use, since a listener may arrive with either.
_URL_HEADERS = frozenset({"channel url", "channelurl", "url", "channel link"})
_TITLE_HEADERS = frozenset({"channel title", "channeltitle", "title", "name", "channel name"})
_ID_HEADERS = frozenset({"channel id", "channelid", "id"})


@dataclass(frozen=True, slots=True)
class TakeoutChannel:
    """One followed channel, as the export describes it."""

    url: str
    name: str = ""


def _channel_url_from_id(value: str) -> str:
    """A canonical URL from a bare ``UC...`` channel id, or ``""``.

    The export always carries a URL as well, so this is a fallback for a file
    that has been through a spreadsheet -- where a column can easily be lost.
    """
    ident = (value or "").strip()
    if not ident.startswith("UC") or len(ident) < 10 or "/" in ident:
        return ""
    return normalize_channel_url(f"https://www.youtube.com/channel/{ident}")


def _pick_columns(header: list[str]) -> tuple[int, int, int]:
    """``(url, title, id)`` column indexes from a header row; -1 when absent."""
    url_at = title_at = id_at = -1
    for index, cell in enumerate(header):
        name = cell.strip().strip("﻿").lower()
        if url_at < 0 and name in _URL_HEADERS:
            url_at = index
        elif title_at < 0 and name in _TITLE_HEADERS:
            title_at = index
        elif id_at < 0 and name in _ID_HEADERS:
            id_at = index
    return url_at, title_at, id_at


def _row_channel(row: list[str], url_at: int, title_at: int, id_at: int) -> TakeoutChannel | None:
    def cell(index: int) -> str:
        return row[index].strip() if 0 <= index < len(row) else ""

    url = normalize_channel_url(cell(url_at)) if url_at >= 0 else ""
    if not url and id_at >= 0:
        url = _channel_url_from_id(cell(id_at))
    if not url:
        # No header, or a header we did not recognise: take the first cell that
        # looks like a channel address, and the first that does not as the name.
        for value in row:
            url = normalize_channel_url(value.strip()) or _channel_url_from_id(value.strip())
            if url:
                break
    if not url:
        return None
    name = cell(title_at)
    if not name:
        name = next(
            (
                value.strip()
                for value in row
                if value.strip()
                and not value.strip().lower().startswith(("http://", "https://"))
                and not value.strip().startswith("UC")
            ),
            "",
        )
    return TakeoutChannel(url=url, name=name)


def parse_subscriptions(text: str) -> list[TakeoutChannel]:
    """Channels from a Takeout ``subscriptions.csv`` (pure; never raises).

    Duplicates within the file collapse to the first occurrence, so a listener
    who exported twice and concatenated the files still gets one of each.
    """
    if not text.strip():
        return []
    try:
        rows = list(csv.reader(io.StringIO(text)))
    except csv.Error:
        return []
    if not rows:
        return []

    url_at, title_at, id_at = _pick_columns(rows[0])
    body = rows[1:] if (url_at >= 0 or title_at >= 0 or id_at >= 0) else rows

    channels: list[TakeoutChannel] = []
    seen: set[str] = set()
    for row in body:
        if not row or not any(cell.strip() for cell in row):
            continue
        channel = _row_channel(row, url_at, title_at, id_at)
        if channel is None or channel.url in seen:
            continue
        seen.add(channel.url)
        channels.append(channel)
    return channels
