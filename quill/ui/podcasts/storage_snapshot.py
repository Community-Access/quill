"""Small, coherent storage generations copied only by the UI thread."""

from __future__ import annotations

import copy
from collections.abc import Callable, Generator
from dataclasses import dataclass, field, replace
from time import perf_counter
from typing import Any

from quill.core.podcasts import inbox
from quill.core.podcasts.models import ExpiredEntry, PodcastEpisode, PodcastShow, QueueItem
from quill.core.podcasts.storage_maintenance import EpisodeKey
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui.podcasts.library_snapshot import ITEMS_PER_TURN, TURN_BUDGET_SECONDS
from quill.ui.surface_lifetime import window_is_going


def owner_alive(host: Any, *, allow_closing: bool = False) -> bool:
    return (
        not getattr(host, "_cast_closed", False)
        and (allow_closing or not getattr(host, "_cast_closing", False))
        and not window_is_going(host.frame)
    )


def transfer_protected(host: Any, key: EpisodeKey) -> bool:
    for name in ("_podcast_download_queue", "_podcast_cache_queue"):
        queue = getattr(host, name, None)
        get = getattr(queue, "get", None)
        item = get(key[1]) if callable(get) else None
        if item is not None and (item.show_id, item.episode_guid) == key:
            if item.status in ("queued", "downloading", "paused"):
                return True
    state = getattr(getattr(host, "_podcast_controller", None), "state", None)
    return bool(state is not None and (state.show_id, state.episode_guid) == key)


class TurnJob:
    """Run bounded items within a time budget before yielding to wx."""

    def __init__(
        self,
        wx: Any,
        chunks: Generator[None, None, Any],
        *,
        completed: Callable[[Any], None],
        failed: Callable[[BaseException], None],
        alive: Callable[[], bool],
        valid: Callable[[], bool] | None = None,
        changed: Callable[[], None] | None = None,
        turn_budget_seconds: float = TURN_BUDGET_SECONDS,
        ready: Callable[[], bool] | None = None,
    ) -> None:
        self._wx = wx
        self._chunks = chunks
        self._completed = completed
        self._failed = failed
        self._alive = alive
        self._valid = valid
        self._changed = changed
        self._turn_budget_seconds = turn_budget_seconds
        self._ready = ready
        self._later: Any = None
        self.cancelled = False

    def start(self) -> None:
        later = getattr(self._wx, "CallLater", None)
        after = getattr(self._wx, "CallAfter", None)
        if callable(later):
            self._later = later(1, self._advance)
        elif callable(after):
            after(self._advance)
        else:
            self._failed(RuntimeError("Storage work needs a UI event-loop dispatcher"))

    def cancel(self) -> None:
        self.cancelled = True
        if self._later is not None:
            self._later.Stop()
            self._later = None
        self._chunks.close()

    def _advance(self) -> None:
        self._later = None
        if self.cancelled:
            return
        if not self._alive():
            self.cancel()
            return
        if self._ready is not None and not self._ready():
            self.start()
            return
        deadline = perf_counter() + self._turn_budget_seconds
        for index in range(ITEMS_PER_TURN):
            if self._valid is not None and not self._valid():
                self.cancel()
                if self._changed is not None:
                    self._changed()
                return
            if index and perf_counter() >= deadline:
                break
            try:
                next(self._chunks)
            except StopIteration as result:
                self._completed(result.value)
                return
            except Exception as error:
                self.cancel()
                self._failed(error)
                return
        self.start()


@dataclass(slots=True)
class StorageCapture:
    source: PodcastLibrary
    library: PodcastLibrary
    revision: object
    shows: dict[str, PodcastShow] = field(default_factory=dict)
    episodes: dict[EpisodeKey, tuple[PodcastShow, PodcastEpisode]] = field(default_factory=dict)
    queue: list[QueueItem] = field(default_factory=list)
    expired: list[ExpiredEntry] = field(default_factory=list)
    queued: set[EpisodeKey] = field(default_factory=set)
    protected: set[EpisodeKey] = field(default_factory=set)


def generation(host: Any) -> tuple[object, ...]:
    library = host._podcast_library
    return (
        id(library),
        getattr(host, "_podcast_library_revision", 0),
        id(library.shows),
        len(library.shows),
        id(library.queue),
        len(library.queue),
        id(library.recently_expired),
        len(library.recently_expired),
        id(library.inbox_assignments),
        len(library.inbox_assignments),
        id(library.folders),
        len(library.folders),
        id(library.show_folder_copies),
        len(library.show_folder_copies),
        id(library.extra_settings),
        len(library.extra_settings),
        id(library.scope_overrides),
        len(library.scope_overrides),
        id(library.settings),
    )


def capture_chunks(
    host: Any, captured: StorageCapture, *, include_inbox: bool = True
) -> Generator[None, None, StorageCapture]:
    library = captured.source
    snapshot = captured.library
    snapshot.settings = copy.deepcopy(library.settings)
    yield
    for folder in library.folders:
        snapshot.folders.append(replace(folder))
        yield
    for show_id, folder_ids in library.show_folder_copies.items():
        placements: list[str | None] = []
        snapshot.show_folder_copies[show_id] = placements
        yield
        for folder_id in folder_ids:
            placements.append(folder_id)
            yield
    for key, value in library.extra_settings.items():
        snapshot.extra_settings[key] = copy.deepcopy(value)
        yield
    for key, overrides in library.scope_overrides.items():
        snapshot.scope_overrides[key] = copy.deepcopy(overrides)
        yield
    for key, value in library.inbox_assignments.items():
        snapshot.inbox_assignments[key] = value
        yield
    for item in library.queue:
        captured.queue.append(item)
        captured.queued.add((item.show_id, item.episode_guid))
        snapshot.queue.append(replace(item))
        yield
    required = set(captured.queued)
    for entry in library.recently_expired:
        captured.expired.append(entry)
        required.add((entry.show_id, entry.episode_guid))
        snapshot.recently_expired.append(replace(entry))
        yield
    for show in library.shows:
        copied_show = PodcastShow(
            id=show.id,
            title=show.title,
            folder_id=show.folder_id,
            is_local=show.is_local,
            route_to_inbox=show.route_to_inbox,
            inbox_default_folder_id=show.inbox_default_folder_id,
            settings=copy.deepcopy(show.settings),
        )
        snapshot.shows.append(copied_show)
        captured.shows[show.id] = show
        yield
        trim_inbox = (
            include_inbox and inbox.in_inbox(library, show) and any(inbox.inbox_caps(library, show))
        )
        yield
        skipped = 0
        for episode in show.episodes:
            key = (show.id, episode.guid)
            inbox_candidate = (
                trim_inbox
                and not episode.played
                and episode.position_ms <= 0
                and key not in captured.queued
                and library.inbox_assignments.get(inbox.inbox_key(*key)) is None
            )
            # Storage policies need downloads, referenced slots and Inbox-cap
            # candidates, not a second copy of the entire feed catalogue.
            if episode.downloaded_path or key in required or inbox_candidate:
                captured.episodes[key] = (show, episode)
                copied_show.episodes.append(
                    PodcastEpisode(
                        guid=episode.guid,
                        title=episode.title,
                        audio_url=episode.audio_url,
                        published=episode.published,
                        downloaded_path=episode.downloaded_path,
                        played=episode.played,
                        position_ms=episode.position_ms,
                    )
                )
                if episode.downloaded_path and transfer_protected(host, key):
                    captured.protected.add(key)
                skipped = 0
                yield
            else:
                skipped += 1
                if skipped >= ITEMS_PER_TURN:
                    skipped = 0
                    yield
    return captured


class CoherentSnapshot:
    """Discard a hybrid generation and retry when a UI mutation intervenes."""

    def __init__(
        self,
        host: Any,
        *,
        completed: Callable[[StorageCapture], None],
        failed: Callable[[BaseException], None],
        allow_closing: bool = False,
        include_inbox: bool = True,
    ) -> None:
        self.host = host
        self.completed = completed
        self.failed = failed
        self.allow_closing = allow_closing
        self.include_inbox = include_inbox
        self.job: TurnJob | None = None
        self.cancelled = False

    def start(self) -> None:
        if self.cancelled:
            return
        revision = generation(self.host)
        captured = StorageCapture(self.host._podcast_library, PodcastLibrary(), revision)
        self.job = TurnJob(
            self.host._wx,
            capture_chunks(self.host, captured, include_inbox=self.include_inbox),
            completed=self.completed,
            failed=self.failed,
            alive=lambda: owner_alive(self.host, allow_closing=self.allow_closing),
            valid=lambda: generation(self.host) == revision,
            changed=self.start,
        )
        self.job.start()

    def cancel(self) -> None:
        self.cancelled = True
        if self.job is not None:
            self.job.cancel()
