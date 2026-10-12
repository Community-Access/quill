"""Applying a planned OPML import: the step that changes the library.

Split from :mod:`quill.core.podcasts.opml_import` under GATE-11. Planning
decides; this module acts on the decision -- folders first in the file's own
order, then each new show, then the extra folder placements of shows already
followed. It is a generator so the import window can apply two thousand
entries a few at a time between paints and notice a library changed under it
(``revision``) rather than freezing until the last one lands.

wx-free, strict-typed. No network.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING

from quill.core.podcasts.models import PodcastSettings, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary, new_id

if TYPE_CHECKING:
    from quill.core.podcasts.opml_import import ImportPlan

__all__ = ["apply_plan", "apply_plan_steps"]


def apply_plan(
    library: PodcastLibrary,
    plan: ImportPlan,
    *,
    stream_only: bool = False,
    into_folder: str | None = None,
) -> list[PodcastShow]:
    return [
        show
        for show in apply_plan_steps(
            library, plan, stream_only=stream_only, into_folder=into_folder
        )
        if show is not None
    ]


def apply_plan_steps(
    library: PodcastLibrary,
    plan: ImportPlan,
    *,
    stream_only: bool = False,
    into_folder: str | None = None,
    revision: Callable[[], int] | None = None,
) -> Iterator[PodcastShow | None]:
    """Add every planned show to *library*; returns the shows added.

    Folder paths are memoized, so a file whose two thousand entries live in
    forty folders walks the folder tree forty times rather than two thousand.
    ``library.add_show`` is deliberately bypassed: the plan has already ruled
    out duplicates in constant time, and re-scanning every show per entry is
    exactly the quadratic behavior this module exists to remove.
    """
    # Imported here: opml_import re-exports this module, so a top-level import
    # would be circular.
    from quill.core.podcasts.opml_import import normalize_feed_url

    folder_cache: dict[tuple[str, ...], str | None] = {}
    known_feeds: dict[str, PodcastShow] = {}
    indexed_revision: int | None = None

    def rebuild_index() -> Iterator[None]:
        nonlocal indexed_revision
        while True:
            before = revision() if revision is not None else None
            known_feeds.clear()
            for index, show in enumerate(library.shows):
                if show.feed_url:
                    known_feeds[normalize_feed_url(show.feed_url)] = show
                if (index + 1) % 64 == 0:
                    yield None
            if revision is None or revision() == before:
                indexed_revision = before
                return

    yield from rebuild_index()

    def resolve_folder(path: list[str]) -> str | None:
        full = tuple([into_folder, *path] if into_folder else path)
        if not full:
            return None
        if full in folder_cache:
            return folder_cache[full]
        folder_id = library.find_or_create_folder_path(list(full))
        folder_cache[full] = folder_id
        return folder_id

    # The file's folders first, in its own order, so empty ones exist and the
    # tree reads in the order the file gave it.
    for path in plan.folders:
        resolve_folder(path)
        yield None
    candidates = plan.new
    plan.new = []
    for candidate in candidates:
        if revision is not None and revision() != indexed_revision:
            yield from rebuild_index()
        key = normalize_feed_url(candidate.feed_url)
        if key in known_feeds:
            plan.duplicates_in_library.append(f"{candidate.title} ({candidate.feed_url})")
            yield None
            continue
        show = PodcastShow(
            id=new_id(),
            title=candidate.title,
            feed_url=candidate.feed_url,
            homepage=candidate.homepage,
            folder_id=resolve_folder(candidate.folder_path),
            description=candidate.description,
            language=candidate.language,
            category=candidate.category,
        )
        if stream_only:
            show.settings = PodcastSettings(playback_mode="stream")
        library.shows.append(show)
        plan.new.append(candidate)
        known_feeds[key] = show
        yield show
    from quill.core.podcasts.folder_membership import copy_to

    for key, paths in plan.folder_placements.items():
        if revision is not None and revision() != indexed_revision:
            yield from rebuild_index()
        existing = known_feeds.get(key)
        if existing is None:
            continue
        for path in paths:
            if copy_to(library, existing, resolve_folder(path)):
                plan.copied_placements += 1
            yield None
