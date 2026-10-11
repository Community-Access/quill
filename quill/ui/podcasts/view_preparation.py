"""Prepare large Cast views off-thread; commit only the currently requested view."""

from __future__ import annotations

import logging
from collections.abc import Callable, Generator, Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quill.core.podcasts import places
from quill.stability.task_manager import TaskManager
from quill.ui.podcasts.storage_snapshot import TurnJob
from quill.ui.podcasts.view_snapshot import (
    VIEW_TURN_BUDGET_SECONDS,
    EpisodeView,
    ViewCaptureJob,
    ViewLibrary,
    discard_view_snapshot,
    prepare_worker_snapshot,
    resolve_view_pairs,
)
from quill.ui.surface_lifetime import window_is_going

logger = logging.getLogger(__name__)


@dataclass
class PreparedView:
    counts: dict[str, int] = field(default_factory=dict)
    unheard: dict[str, int] = field(default_factory=dict)
    playlist_counts: dict[str, int] = field(default_factory=dict)
    pairs: list[tuple[str, str]] = field(default_factory=list)
    offsets: list[int] = field(default_factory=list)
    lead_rows: list[tuple[str, str, str]] = field(default_factory=list)
    show_ids: list[str] = field(default_factory=list)
    notices: list[Any] = field(default_factory=list)


def _record_pairs(result: PreparedView, pairs: Iterable[tuple[Any, Any]]) -> None:
    for show, episode in pairs:
        result.pairs.append((show.id, episode.guid))
        result.offsets.append(
            episode.source_index
            if isinstance(episode, EpisodeView)
            else show.episodes.index(episode)
        )


def _filtered_pairs(pairs: Iterable[tuple[Any, Any]], mode: str) -> Iterator[tuple[Any, Any]]:
    from quill.core.podcasts.filtering import filter_episodes

    for show, episode in pairs:
        if mode == "all" or filter_episodes([episode], mode):
            yield show, episode


def prepare_view(
    library: Any,
    place_id: str,
    *,
    episode_filter: str,
    notifications_path: Path,
    show_id: str = "",
    playlist_id: str = "",
    inbox_folder: str = "",
    limit: int = 1000,
) -> PreparedView:
    from quill.core.notifications import load_notifications, newest_first, unread_count
    from quill.core.podcasts import library_view
    from quill.core.podcasts.episode_filter_maintenance import visible
    from quill.core.podcasts.filtering import filter_episodes
    from quill.core.podcasts.models_filters import SCOPE_LIBRARY
    from quill.core.podcasts.playlists import resolve_playlist
    from quill.core.podcasts.queue import resolve
    from quill.core.podcasts.show_policy import visible_episodes
    from quill.core.podcasts.sorting import sort_episodes, sort_pairs, unheard_count
    from quill.core.podcasts.virtual_views import favorite_shows, iter_virtual_view_pairs

    notices = load_notifications(path=notifications_path)
    result = PreparedView(
        counts={
            place.id: places.count(library, place.id, unread_notices=unread_count(notices))
            for place in places.PLACES
        },
        unheard={show.id: unheard_count(show) for show in library.shows},
    )
    if show_id:
        show = library.find_show(show_id)
        if show is not None:
            episodes = filter_episodes(
                visible(
                    library, show, visible_episodes(library, show, show.episodes), SCOPE_LIBRARY
                ),
                episode_filter,
            )
            _record_pairs(
                result,
                (
                    (show, episode)
                    for episode in sort_episodes(
                        episodes, library.effective_settings(show).episode_sort_mode
                    )
                ),
            )
        return result
    pairs: Iterable[tuple[Any, Any]]
    if playlist_id:
        playlist = next((p for p in library.playlists if p.id == playlist_id), None)
        pairs = list(resolve_playlist(library, playlist)) if playlist is not None else []
    elif place_id == "favorites":
        result.show_ids = [show.id for show in favorite_shows(library)]
        return result
    elif place_id == "playlists":
        result.playlist_counts = {
            playlist.id: len(resolve_playlist(library, playlist)) for playlist in library.playlists
        }
        return result
    elif place_id == "notifications":
        result.notices = newest_first(notices)
        return result
    elif place_id == "podcasts":
        return result
    elif place_id == "queue":
        pairs = (pair for item in library.queue if (pair := resolve(library, item)) is not None)
    elif place_id == "downloads":
        pairs = ((show, ep) for show in library.shows for ep in show.episodes if ep.downloaded_path)
    elif place_id == "personal_audio":
        pairs = ((show, ep) for show in library.shows if show.is_local for ep in show.episodes)
    else:
        pairs = iter_virtual_view_pairs(library, place_id)
        if inbox_folder:
            pairs = library_view.iter_inbox_folder_pairs(library, pairs, inbox_folder)
        elif place_id == "inbox":

            def inbox_episodes() -> Iterator[tuple[Any, Any]]:
                for row in library_view.iter_inbox_rows(
                    library, lambda: iter_virtual_view_pairs(library, place_id)
                ):
                    if row.kind == "inbox_folder":
                        result.lead_rows.append((row.kind, row.folder_id, row.label))
                    elif row.pair is not None:
                        yield row.pair

            pairs = inbox_episodes()
            if limit == 0:
                for _pair in pairs:
                    pass
                return result
    _record_pairs(
        result,
        sort_pairs(
            library,
            _filtered_pairs(pairs, episode_filter),
            view_mode=library.settings.episode_list_view_mode,
            limit=limit,
        ),
    )
    return result


class CastViewPreparationMixin:
    """One supersedable preparation, with detached worker input and live rows."""

    def _apply_cast_prepared_view(
        self,
        result: PreparedView,
        context: tuple[str, str, str, str],
        keep: Any,
    ) -> None:
        """Publish the view already prepared by the startup worker in bounded turns."""
        self._cancel_cast_view_preparation()
        generation = self._cast_view_generation
        source = self._podcast_library  # type: ignore[attr-defined]
        revision = int(getattr(self, "_podcast_library_revision", 0))

        def current() -> bool:
            return (
                generation == self._cast_view_generation
                and not getattr(self, "_cast_closed", False)
                and not getattr(self, "_cast_closing", False)
                and not window_is_going(self.frame)  # type: ignore[attr-defined]
            )

        def valid() -> bool:
            return source is self._podcast_library and revision == int(  # type: ignore[attr-defined]
                getattr(self, "_podcast_library_revision", 0)
            )

        def retry() -> None:
            if current():
                self._request_cast_view_preparation(self._current_place, keep=keep)  # type: ignore[attr-defined]

        def failed(error: BaseException) -> None:
            if current():
                self._cast_view_snapshot = None
                logger.error(
                    "Could not show the Cast startup view",
                    exc_info=(type(error), error, error.__traceback__),
                )
                self._set_status("Could not show this view. Try opening it again.")  # type: ignore[attr-defined]
                self._announce(f"Could not show this view. {error}")  # type: ignore[attr-defined]

        def published(_unused: None) -> None:
            if current():
                self._cast_view_snapshot = None

        def resolved(pairs: list[tuple[Any, Any]] | None) -> None:
            if not current():
                return
            if pairs is None or not valid():
                retry()
                return

            def chunks() -> Generator[None]:
                yield from self._cast_prepared_view_chunks(result, context, keep, pairs=pairs)
                yield from self._place_count_chunks()  # type: ignore[attr-defined]

            job = TurnJob(
                self._wx,  # type: ignore[attr-defined]
                chunks(),
                completed=published,
                failed=failed,
                alive=current,
                valid=valid,
                changed=retry,
                turn_budget_seconds=VIEW_TURN_BUDGET_SECONDS,
            )
            self._cast_view_snapshot = job
            job.start()

        job = TurnJob(
            self._wx,  # type: ignore[attr-defined]
            resolve_view_pairs(source, result.pairs, result.offsets),
            completed=resolved,
            failed=failed,
            alive=current,
            valid=valid,
            changed=retry,
            turn_budget_seconds=VIEW_TURN_BUDGET_SECONDS,
        )
        self._cast_view_snapshot = job
        job.start()

    def _cast_place_count(self, place_id: str) -> int | None:
        if self._podcast_library_is_large():  # type: ignore[attr-defined]
            return getattr(self, "_cast_place_counts", {}).get(place_id)
        return places.count(
            self._podcast_library,  # type: ignore[attr-defined]
            place_id,
            unread_notices=self._unread_notice_count() if place_id == "notifications" else 0,  # type: ignore[attr-defined]
        )

    def _cancel_cast_view_preparation(self) -> None:
        self._cast_view_generation = int(getattr(self, "_cast_view_generation", 0)) + 1
        job = getattr(self, "_cast_view_snapshot", None)
        if job is not None:
            job.cancel()
        self._cast_view_snapshot = None
        task = getattr(self, "_cast_view_task", None)
        if task is not None:
            self._task_manager.cancel(task.operation_id)  # type: ignore[attr-defined]
        self._cast_view_task = None

    def _retire_cast_view_snapshot(self, snapshot: ViewLibrary) -> None:
        pool = getattr(self, "_cast_view_retirement_pool", None)
        if pool is None:
            pool = TaskManager(max_workers=1)
            self._cast_view_retirement_pool = pool

        def work(**_kwargs: Any) -> None:
            discard_view_snapshot(snapshot)

        pool.submit("cast-view-retire", work, safe_to_cancel=False)

    def _request_cast_view_preparation(
        self,
        place_id: str,
        *,
        keep: Any = None,
        counts_only: bool = False,
        initialize: Callable[[], Generator[None]] | None = None,
    ) -> None:
        from quill.core.notifications import notifications_path

        self._cancel_cast_view_preparation()
        generation = self._cast_view_generation
        revision = int(getattr(self, "_podcast_library_revision", 0))
        source = self._podcast_library  # type: ignore[attr-defined]
        context = (
            place_id,
            getattr(self, "_place_opened_show_id", ""),
            getattr(self, "_place_opened_playlist_id", ""),
            getattr(self, "_place_opened_inbox_folder", ""),
        )
        path = notifications_path()
        mode = self._episode_show_filter()  # type: ignore[attr-defined]
        publication_keep = keep
        publication_cursor_revision: int | None = None

        def current() -> bool:
            return (
                generation == self._cast_view_generation
                and not getattr(self, "_cast_closed", False)
                and not getattr(self, "_cast_closing", False)
                and not window_is_going(self.frame)  # type: ignore[attr-defined]
            )

        def valid() -> bool:
            return (
                source is self._podcast_library  # type: ignore[attr-defined]
                and revision == int(getattr(self, "_podcast_library_revision", 0))
            )

        def ready() -> bool:
            return not getattr(self, "_podcast_commit_depth", 0)

        def retry() -> None:
            if current():
                selected = self._selected_tree_data()  # type: ignore[attr-defined]
                if (
                    selected is None
                    and publication_cursor_revision is not None
                    and publication_cursor_revision
                    == int(getattr(self, "_cast_cursor_revision", 0))
                ):
                    selected = publication_keep
                self._request_cast_view_preparation(
                    self._current_place,  # type: ignore[attr-defined]
                    keep=selected,
                    counts_only=counts_only,
                    initialize=(
                        initialize if self._current_place == place_id else None  # type: ignore[attr-defined]
                    ),
                )

        def failed(error: BaseException) -> None:
            if not current():
                return
            self._cast_view_snapshot = None
            self._cast_view_task = None
            logger.error(
                "Could not prepare the Cast view",
                exc_info=(type(error), error, error.__traceback__),
            )
            self._set_status("Could not prepare this view. Try opening it again.")  # type: ignore[attr-defined]
            self._announce(f"Could not prepare this view. {error}")  # type: ignore[attr-defined]

        def publication_chunks(
            result: PreparedView, pairs: list[tuple[Any, Any]]
        ) -> Generator[None]:
            nonlocal publication_keep, publication_cursor_revision
            self._cast_place_counts = result.counts
            self._cast_unheard_counts = result.unheard
            self._cast_playlist_counts = result.playlist_counts
            self._cast_counts_revision = revision
            self._refresh_window_title()  # type: ignore[attr-defined]
            yield
            if counts_only:
                if self._current_place == "podcasts":  # type: ignore[attr-defined]
                    if getattr(self, "_check_run", None) is not None:
                        self._tree_reload_pending = True
                    else:
                        self._reload_library_tree()  # type: ignore[attr-defined]
                    yield
                yield from self._place_count_chunks()  # type: ignore[attr-defined]
                return
            if context != (
                self._current_place,  # type: ignore[attr-defined]
                getattr(self, "_place_opened_show_id", ""),
                getattr(self, "_place_opened_playlist_id", ""),
                getattr(self, "_place_opened_inbox_folder", ""),
            ):
                return
            selected = self._selected_tree_data() or keep  # type: ignore[attr-defined]
            publication_keep = selected
            publication_cursor_revision = int(getattr(self, "_cast_cursor_revision", 0))
            yield from self._cast_prepared_view_chunks(result, context, selected, pairs=pairs)
            self._say_empty_place_once(place_id)  # type: ignore[attr-defined]
            yield
            yield from self._place_count_chunks()  # type: ignore[attr-defined]

        def published(_result: None) -> None:
            if current():
                self._cast_view_snapshot = None

        def publish(result: PreparedView, pairs: list[tuple[Any, Any]] | None) -> None:
            if not current():
                return
            if pairs is None or not valid():
                retry()
                return
            job = TurnJob(
                self._wx,  # type: ignore[attr-defined]
                publication_chunks(result, pairs),
                completed=published,
                failed=failed,
                alive=current,
                valid=valid,
                changed=retry,
                turn_budget_seconds=VIEW_TURN_BUDGET_SECONDS,
                ready=ready,
            )
            self._cast_view_snapshot = job
            job.start()

        def prepared(_operation: str, result: PreparedView) -> None:
            if not current():
                return
            self._cast_view_task = None
            if not valid():
                retry()
                return
            job = TurnJob(
                self._wx,  # type: ignore[attr-defined]
                resolve_view_pairs(source, result.pairs, result.offsets),
                completed=lambda pairs: publish(result, pairs),
                failed=failed,
                alive=current,
                valid=valid,
                changed=retry,
                turn_budget_seconds=VIEW_TURN_BUDGET_SECONDS,
                ready=ready,
            )
            self._cast_view_snapshot = job
            job.start()

        def submit(snapshot: ViewLibrary) -> None:
            if not current():
                self._retire_cast_view_snapshot(snapshot)
                return
            self._cast_view_snapshot = None

            def work(**_kwargs: Any) -> PreparedView:
                try:
                    prepare_worker_snapshot(snapshot, _kwargs.get("cancellation_token"))
                    return prepare_view(
                        snapshot,
                        "podcasts" if counts_only else place_id,
                        episode_filter=mode,
                        notifications_path=path,
                        show_id="" if counts_only else context[1],
                        playlist_id="" if counts_only else context[2],
                        inbox_folder="" if counts_only else context[3],
                    )
                finally:
                    discard_view_snapshot(snapshot)

            self._cast_view_task = self._task_manager.submit(  # type: ignore[attr-defined]
                "cast-view-prepare",
                work,
                on_success=prepared,
                on_failure=lambda _operation, error: failed(error),
            )

        job = ViewCaptureJob(
            source,
            self._wx,  # type: ignore[attr-defined]
            completed=submit,
            retire=self._retire_cast_view_snapshot,
            initialize=initialize,
            failed=failed,
            alive=current,
            valid=valid,
            changed=retry,
            turn_budget_seconds=VIEW_TURN_BUDGET_SECONDS,
            ready=ready,
        )
        self._cast_view_snapshot = job
        job.start()

    def _cast_prepared_view_chunks(
        self,
        result: PreparedView,
        context: tuple[str, str, str, str],
        keep: Any,
        *,
        pairs: list[tuple[Any, Any]],
    ) -> Generator[None]:
        place_id, show_id, playlist_id, inbox_folder = context
        library = self._podcast_library  # type: ignore[attr-defined]
        cursor_revision = int(getattr(self, "_cast_cursor_revision", 0))
        mutating = getattr(self, "_cast_list_mutating", False)
        rows: Generator[None] | None = None
        self._cast_list_mutating = True
        try:
            if place_id == "podcasts" and not (show_id or playlist_id or inbox_folder):
                self._reload_library_tree(keep_key=keep)  # type: ignore[attr-defined]
            elif place_id == "favorites" and not show_id:
                self._fill_podcast_rows(  # type: ignore[attr-defined]
                    [
                        show
                        for sid in result.show_ids
                        if (show := library.find_show(sid)) is not None
                    ]
                )
            elif place_id == "playlists" and not playlist_id:
                self._fill_playlist_rows()  # type: ignore[attr-defined]
            elif place_id == "notifications":
                self._fill_notice_rows(result.notices)  # type: ignore[attr-defined]
            else:
                if show_id:
                    self._fill_episodes(  # type: ignore[attr-defined]
                        library.find_show(show_id),
                        prepared_episodes=[episode for _show, episode in pairs],
                    )
                else:
                    rows = self._episode_pair_row_chunks(  # type: ignore[attr-defined]
                        pairs, lead_rows=result.lead_rows, prepared=True
                    )
        finally:
            self._cast_list_mutating = mutating
        if rows is None:
            yield
        else:
            yield from self._cast_list_update_chunks(rows)
        if (
            self._content_is_list()  # type: ignore[attr-defined]
            and cursor_revision == int(getattr(self, "_cast_cursor_revision", 0))
        ):
            self._cast_list_mutating = True
            try:
                self._select_list_key(keep) or self._select_list_row(0)  # type: ignore[attr-defined]
            finally:
                self._cast_list_mutating = mutating
        yield
        self._content.set_heading(self._place_heading(place_id))  # type: ignore[attr-defined]
        yield
        yield from self._selection_button_chunks()  # type: ignore[attr-defined]
        self._refresh_notes_pane()  # type: ignore[attr-defined]
        yield

    def _cast_list_update_chunks(self, chunks: Generator[None]) -> Generator[None]:
        mutating = getattr(self, "_cast_list_mutating", False)
        try:
            while True:
                self._cast_list_mutating = True
                try:
                    next(chunks)
                except StopIteration:
                    return
                finally:
                    self._cast_list_mutating = mutating
                yield
        finally:
            chunks.close()
