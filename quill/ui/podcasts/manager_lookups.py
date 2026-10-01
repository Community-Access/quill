"""Where a download lands, and who is under which folder -- no wx involved.

Extracted from ``manager_dialog.py`` under GATE-11 rather than growing that
module again. The seam is the right one for a second reason: ``show_actions.py``
and ``main_frame_podcast_transfers.py`` both reached into the *dialog* module for
``episode_destination``, and ``manager_reveal.py`` for ``_item_key`` -- importing
a window in order to compute a filename, which is the shape that makes a UI
module impossible to test without wx.

Nothing here touches a widget except :func:`_item_key`, which only asks a
``wx.TreeItemId`` for its pointer value.
"""

from __future__ import annotations

import re
from pathlib import Path

from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary

__all__ = [
    "episode_destination",
    "item_key",
    "shows_episodes",
    "shows_in_folder_subtree",
]


def _slug(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return slug or "show"


def episode_destination(download_root: Path, show: PodcastShow, episode: PodcastEpisode) -> Path:
    """Where a downloaded episode's file lands: ``<root>/<show-slug>/<episode-slug><ext>``."""
    suffix = Path(episode.audio_url.split("?", 1)[0]).suffix or ".mp3"
    return download_root / _slug(show.title) / f"{_slug(episode.title)}{suffix}"


def shows_in_folder_subtree(library: PodcastLibrary, folder_id: str) -> list[PodcastShow]:
    """Every show in *folder_id* or any folder nested under it, tree order.

    Powers the per-folder bulk actions (set the whole folder's shows to
    stream/download) where "the folder" always means the whole subtree a
    user sees under that node, never just its direct children.
    """
    shows = [show for show in library.shows if show.folder_id == folder_id]
    for folder in library.folders:
        if folder.parent_folder_id == folder_id:
            shows.extend(shows_in_folder_subtree(library, folder.id))
    return shows


def item_key(item: object) -> int:
    """Stable, hashable identity for a wx.TreeItemId.

    ``GetID()`` returns a fresh ``sip.voidptr`` wrapper on every call; two
    wrappers for the SAME tree item never compare equal, so keying the
    item->show / item->folder dicts by the wrapper silently missed every lookup
    -- ``_selected_show_id`` always returned None, so selecting a podcast showed
    no episodes (#1189). ``int()`` of the voidptr is the raw pointer value:
    stable, equal, hashable.
    """
    get_id = getattr(item, "GetID", None)
    if callable(get_id):
        try:
            return int(get_id())
        except (TypeError, ValueError):
            pass
    return id(item)


def shows_episodes(library: PodcastLibrary, folder_id: str) -> list[PodcastEpisode]:
    """Every episode belonging to a show directly in *folder_id* (not
    subfolders -- the caller recurses those separately)."""
    episodes: list[PodcastEpisode] = []
    for show in library.shows:
        if show.folder_id == folder_id:
            episodes.extend(show.episodes)
    return episodes
