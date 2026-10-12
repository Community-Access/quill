"""Additional folder placements share one subscription and all its listening state."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from quill.core.podcasts.models import PodcastShow
    from quill.core.podcasts.subscriptions import PodcastLibrary

logger = logging.getLogger(__name__)


def placements(library: PodcastLibrary, show: PodcastShow) -> tuple[str | None, ...]:
    extra: dict[str, list[str | None]] = getattr(library, "show_folder_copies", {})
    return tuple(dict.fromkeys([show.folder_id, *extra.get(show.id, [])]))


def copy_to(library: PodcastLibrary, show: PodcastShow, target: str | None) -> bool:
    if target is not None and library.find_folder(target) is None:
        raise ValueError("The destination folder no longer exists.")
    if target in placements(library, show):
        return False
    library.show_folder_copies.setdefault(show.id, []).append(target)
    return True


def move_to(
    library: PodcastLibrary,
    show: PodcastShow,
    target: str | None,
    *,
    source: str | None,
) -> bool:
    if target is not None and library.find_folder(target) is None:
        raise ValueError("The destination folder no longer exists.")
    if source not in placements(library, show):
        raise ValueError("The podcast is no longer in the selected folder.")
    if source == target:
        return False
    extra = library.show_folder_copies.get(show.id, [])
    if source == show.folder_id:
        show.folder_id = target
        extra = [folder for folder in extra if folder not in (source, target)]
    else:
        extra = [folder for folder in extra if folder != source]
        if target != show.folder_id and target not in extra:
            extra.append(target)
    if extra:
        library.show_folder_copies[show.id] = extra
    else:
        library.show_folder_copies.pop(show.id, None)
    return True


def reorder(
    library: PodcastLibrary, show: PodcastShow, offset: int, *, folder_id: str | None
) -> bool:
    if offset not in (-1, 1):
        return False
    siblings = [item for item in library.shows if folder_id in placements(library, item)]
    if show not in siblings:
        raise ValueError("The podcast is no longer in the selected folder.")
    position = siblings.index(show) + offset
    if not 0 <= position < len(siblings):
        return False
    other = siblings[position]
    first, second = library.shows.index(show), library.shows.index(other)
    library.shows[first], library.shows[second] = library.shows[second], library.shows[first]
    return True


def parse(raw: object) -> dict[str, list[str | None]]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        logger.warning("Invalid podcast folder placement map was ignored")
        return {}
    result: dict[str, list[str | None]] = {}
    for show_id, folders in raw.items():
        if not isinstance(show_id, str) or not isinstance(folders, list):
            logger.warning("Invalid podcast folder placement entry was ignored")
            continue
        cleaned: list[str | None] = []
        for folder in folders:
            if folder is not None and not isinstance(folder, str):
                logger.warning("Invalid podcast folder placement was ignored")
                continue
            if folder not in cleaned:
                cleaned.append(folder)
        if cleaned:
            result[show_id] = cleaned
    return result
