"""Find Streams actions on several rows: Favorites, playlists, links, servers (wx).

* **Add to Favorites:** one stream goes in with no question; two or more ask
  for a folder, prefilled with the page's title (Cancel adds nothing).
  Duplicates are counted, and one sentence follows, with the favourite sound.
* **Save as Playlist:** M3U, PLS, XSPF or ASX through the existing exporters
  (:mod:`quill.core.radio.playlist_export`).
* **Copy Stream Link(s):** the addresses, one per line.
* **Scan This Stream's Server:** handled by the dialog, which owns the address
  field; :func:`quill.core.radio.find_streams_view.server_to_scan` decides when
  it is offered.

Every result names its count (:mod:`quill.core.radio.find_streams_view`).
Prompts go through ``show_modal_dialog`` and ``apply_modal_ids`` like every
QUILL dialog.

Acting on several found streams at once and saving them as a playlist are
ideas from Andre Louis's StreamSift (https://github.com/OnjLouis/StreamSift),
written in QUILL's own code.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from quill.core.radio import find_streams_view as view
from quill.core.radio.favorites import FavoriteStation
from quill.core.radio.models import RadioStation
from quill.core.radio.page_links import PageStreamCandidate
from quill.core.radio.playlist_export import EXPORT_FORMATS
from quill.core.sound_events import SoundEvent

__all__ = [
    "Outcome",
    "add_to_favorites",
    "copy_links",
    "playlist_file_name",
    "save_as_playlist",
    "station_for",
]

Announce = Callable[..., None]


@dataclass(frozen=True, slots=True)
class Outcome:
    """What an action did, for the dialog to say once: the sentence ("" when
    the listener cancelled) and the sound to lead with ("" for none)."""

    sentence: str
    sound: str = ""


def station_for(candidate: PageStreamCandidate, page_title: str, favicon: str = "") -> RadioStation:
    """The station a found stream becomes: its own name first, then a guess."""
    name = (
        candidate.stream_name
        or (candidate.label if candidate.label_is_name else "")
        or page_title
        or candidate.label
        or candidate.url
    )
    return RadioStation(
        name=name,
        stream_url=candidate.url,
        favicon=favicon,
        codec=candidate.codec if candidate.codec != "HLS" else "",
        bitrate_kbps=candidate.bitrate_kbps,
    )


def prompt_text(
    wx: Any,
    parent: Any,
    title: str,
    message: str,
    value: str,
    announce: Announce,
    use: Callable[[str], str] = lambda text: text,
) -> str | None:
    """One line from the platform's own prompt, through the dialog contract.

    *use* runs on the answer **before** the prompt is destroyed, so Find can
    land on its match first and the row is read once. ``None`` on Cancel.
    """
    from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog

    entry = wx.TextEntryDialog(parent, message, title, value=value)
    try:
        # The platform's own prompt carries its OK and Cancel buttons.
        apply_modal_ids(  # dialog_button_contract: exempt
            entry, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL
        )
        if show_modal_dialog(entry, title, announce=announce) != wx.ID_OK:
            return None
        return use(str(entry.GetValue()).strip())
    finally:
        entry.Destroy()


def _ask_folder(wx: Any, parent: Any, count: int, value: str, announce: Announce) -> str | None:
    message = f"Add {count} streams to which Favorites folder? Leave it empty for no folder."
    return prompt_text(wx, parent, "Add to Favorites", message, value, announce)


def add_to_favorites(
    host: Any,
    wx: Any,
    parent: Any,
    candidates: Sequence[PageStreamCandidate],
    *,
    page_title: str,
    favicon: str = "",
) -> Outcome:
    """Add *candidates* to Favorites; the outcome is for the dialog to say."""
    if not candidates:
        return Outcome("")
    folder = ""
    if len(candidates) > 1:
        chosen = _ask_folder(wx, parent, len(candidates), page_title.strip(), host._announce)
        if chosen is None:
            return Outcome("")
        folder = chosen
    store = host._radio_favorites
    stations = [station_for(c, page_title, favicon) for c in candidates]
    if folder:
        store.add_folder(folder)
    added = sum(1 for s in stations if store.add(s, folder=folder, custom=True))
    if added:
        host._save_radio_favorites()
        for refresh in ("_reload_favorites_tree", "_refresh_favorite_toggle"):
            hook = getattr(host, refresh, None)
            if callable(hook):
                hook()
    sentence = view.added_sentence([s.name for s in stations], added, len(stations) - added, folder)
    return Outcome(sentence, SoundEvent.RADIO_FAVORITE_ADDED if added else "")


def playlist_file_name(page_title: str) -> str:
    """A file name from the page title: letters, digits, spaces and dashes."""
    cleaned = "".join(ch if ch.isalnum() or ch in " -_" else " " for ch in page_title)
    stem = " ".join(cleaned.split())[:60].strip()
    return stem or "streams"


def save_as_playlist(
    host: Any,
    wx: Any,
    parent: Any,
    candidates: Sequence[PageStreamCandidate],
    *,
    page_title: str,
) -> Outcome:
    """Save *candidates* as a playlist the listener names."""
    if not candidates:
        return Outcome("")
    from quill.ui.dialog_contract import show_modal_dialog

    wildcard = "|".join(f"{label} (*.{ext})|*.{ext}" for label, ext, _writer in EXPORT_FORMATS)
    title = "Save as Playlist"
    chooser = wx.FileDialog(
        parent,
        title,
        defaultFile=f"{playlist_file_name(page_title)}.m3u",
        wildcard=wildcard,
        style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
    )
    try:
        if show_modal_dialog(chooser, title, announce=host._announce) != wx.ID_OK:
            return Outcome("")
        index = max(0, min(int(chooser.GetFilterIndex()), len(EXPORT_FORMATS) - 1))
        destination = Path(chooser.GetPath())
    finally:
        chooser.Destroy()
    _label, extension, writer = EXPORT_FORMATS[index]
    if destination.suffix.lower() != f".{extension}":
        destination = destination.with_name(f"{destination.name}.{extension}")
    favorites = [FavoriteStation(station=station_for(c, page_title)) for c in candidates]
    try:
        destination.write_text(writer(favorites), encoding="utf-8")
    except OSError:
        return Outcome(f"Could not save {destination.name}: that folder could not be written to.")
    said = view.saved_sentence(len(candidates), destination)
    from quill.ui.outcome_report import keep_outcome

    keep_outcome("Save as Playlist", said, object_name=destination.name, path=destination)
    return Outcome(said)


def copy_links(candidates: Sequence[PageStreamCandidate], copy: Callable[[str], bool]) -> Outcome:
    """Put the stream links on the clipboard, one per line."""
    if not candidates:
        return Outcome("")
    if not copy("\n".join(c.url for c in candidates)):
        return Outcome("Could not copy: another program is using the clipboard.")
    return Outcome(view.copied_sentence(len(candidates)))
