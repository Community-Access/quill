"""Detached scalar input for Cast's read-only view policies."""

from __future__ import annotations

from collections.abc import Callable, Generator, Iterator, Sequence
from dataclasses import dataclass, field
from time import perf_counter, sleep
from typing import Any, NamedTuple, overload

from quill.core.podcasts.models import PodcastEpisode, PodcastSettings, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.stability.task_manager import CancellationToken
from quill.ui.podcasts.library_snapshot import copy_show_metadata, snapshot_chunks
from quill.ui.podcasts.storage_snapshot import TurnJob

RECORDS_PER_CHUNK = 128
VIEW_TURN_BUDGET_SECONDS = 0.003
WORKER_PAUSE_SECONDS = 0.001

type EpisodeData = tuple[
    int, str, str, str, str, int, str, str, bool, int, int, int, str, bool, str
]


class PersonView(NamedTuple):
    name: str


class EpisodePeople(NamedTuple):
    people: tuple[PersonView, ...]


_NO_PEOPLE = EpisodePeople(())


class _WorkerTurns:
    def __init__(self) -> None:
        self.deadline = perf_counter() + VIEW_TURN_BUDGET_SECONDS

    def __call__(self) -> None:
        if perf_counter() >= self.deadline:
            # A zero-length Windows sleep can immediately reacquire the GIL.
            sleep(WORKER_PAUSE_SECONDS)
            self.deadline = perf_counter() + VIEW_TURN_BUDGET_SECONDS


class EpisodeView(NamedTuple):
    source_index: int
    guid: str
    title: str
    audio_url: str
    published: str
    duration_seconds: int
    description: str
    downloaded_path: str
    played: bool
    position_ms: int
    season: int
    episode_number: int
    episode_type: str
    is_numbered: bool
    people_text: str

    @property
    def tags(self) -> EpisodePeople:
        return (
            EpisodePeople(tuple(PersonView(name) for name in self.people_text.split("\n")))
            if self.people_text
            else _NO_PEOPLE
        )


class ViewEpisodes(Sequence[EpisodeView]):
    """Build transient policy records on the worker, not a second model graph."""

    def __init__(self, rows: list[EpisodeData]) -> None:
        self.rows = rows
        self.checkpoint: Callable[[], None] | None = None

    def __len__(self) -> int:
        return len(self.rows)

    def __iter__(self) -> Iterator[EpisodeView]:
        for index, row in enumerate(self.rows):
            yield EpisodeView(*row)
            if (index + 1) % RECORDS_PER_CHUNK == 0 and self.checkpoint is not None:
                self.checkpoint()
        if self.checkpoint is not None:
            self.checkpoint()

    @overload
    def __getitem__(self, index: int) -> EpisodeView: ...

    @overload
    def __getitem__(self, index: slice) -> list[EpisodeView]: ...

    def __getitem__(self, index: int | slice) -> EpisodeView | list[EpisodeView]:
        if isinstance(index, slice):
            return [EpisodeView(*row) for row in self.rows[index]]
        return EpisodeView(*self.rows[index])


@dataclass(slots=True)
class ViewShow:
    metadata: PodcastShow
    episodes: ViewEpisodes

    @property
    def id(self) -> str:
        return self.metadata.id

    @property
    def title(self) -> str:
        return self.metadata.title

    def find_episode(self, guid: str) -> EpisodeView | None:
        for index, row in enumerate(self.episodes.rows):
            if row[1] == guid:
                return EpisodeView(*row)
            if (index + 1) % RECORDS_PER_CHUNK == 0 and self.episodes.checkpoint is not None:
                self.episodes.checkpoint()
        return None

    def __getattr__(self, name: str) -> Any:
        return getattr(self.metadata, name)


@dataclass(slots=True)
class ViewLibrary:
    """The existing domain helpers over detached metadata and scalar episodes."""

    metadata: PodcastLibrary
    shows: list[ViewShow] = field(default_factory=list)
    _shows: dict[str, ViewShow] = field(default_factory=dict)

    def find_show(self, show_id: str) -> ViewShow | None:
        return self._shows.get(show_id)

    def effective_settings(self, show: ViewShow) -> PodcastSettings:
        return self.metadata.effective_settings(show.metadata)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.metadata, name)


def view_snapshot_chunks(
    library: PodcastLibrary, *, retained: Callable[[ViewLibrary], None] | None = None
) -> Generator[None, None, ViewLibrary]:
    metadata = yield from snapshot_chunks(library, metadata_only=True)
    metadata.shows = []
    captured = ViewLibrary(metadata)
    if retained is not None:
        retained(captured)
    for show in library.shows:
        rows: list[EpisodeData] = []
        view = ViewShow(copy_show_metadata(show), ViewEpisodes(rows))
        captured.shows.append(view)
        captured._shows[view.id] = view
        yield
        for index, episode in enumerate(show.episodes):
            # Exact scalar tuples can be untracked by Python's GC. Named tuples
            # and model objects cannot, even when all their fields are scalar.
            rows.append((
                index,
                episode.guid,
                episode.title,
                episode.audio_url,
                episode.published,
                episode.duration_seconds,
                episode.description,
                episode.downloaded_path,
                episode.played,
                episode.position_ms,
                episode.season,
                episode.episode_number,
                episode.episode_type,
                episode.is_numbered,
                "\n".join(person.name for person in episode.tags.people),
            ))
            if (index + 1) % RECORDS_PER_CHUNK == 0:
                yield
        yield
    return captured


class ViewCaptureJob(TurnJob):
    """Keep partial detached input alive until its retirement worker owns it."""

    def __init__(
        self,
        library: PodcastLibrary,
        wx: Any,
        *,
        completed: Callable[[ViewLibrary], None],
        retire: Callable[[ViewLibrary], None],
        initialize: Callable[[], Generator[None]] | None = None,
        **callbacks: Any,
    ) -> None:
        self._retained: ViewLibrary | None = None
        self._consume_capture = completed
        self._retire = retire
        super().__init__(
            wx,
            (
                view_snapshot_chunks(library, retained=self._retain)
                if initialize is None
                else self._initialized_capture(library, initialize)
            ),
            completed=self._captured,
            **callbacks,
        )

    def _initialized_capture(
        self, library: PodcastLibrary, initialize: Callable[[], Generator[None]]
    ) -> Generator[None, None, ViewLibrary]:
        yield from initialize()
        return (yield from view_snapshot_chunks(library, retained=self._retain))

    def _retain(self, captured: ViewLibrary) -> None:
        self._retained = captured

    def _captured(self, captured: ViewLibrary) -> None:
        self._retained = None
        self._consume_capture(captured)

    def cancel(self) -> None:
        captured = self._retained
        self._retained = None
        try:
            super().cancel()
        finally:
            if captured is not None:
                self._retire(captured)


def prepare_worker_snapshot(
    captured: ViewLibrary, cancellation_token: CancellationToken | None = None
) -> None:
    turns = _WorkerTurns()

    def checkpoint() -> None:
        if cancellation_token is not None:
            cancellation_token.raise_if_cancelled()
        turns()

    for show in captured.shows:
        show.episodes.checkpoint = checkpoint


def discard_view_snapshot(captured: ViewLibrary) -> None:
    """Release episode records and show metadata without a catalogue-sized decref."""
    turns = _WorkerTurns()
    while captured.shows:
        show = captured.shows.pop()
        rows = show.episodes.rows
        while rows:
            del rows[-RECORDS_PER_CHUNK:]
            turns()
        captured._shows.pop(show.id, None)
        del show
        turns()


def resolve_view_pairs(
    library: PodcastLibrary,
    pairs: list[tuple[str, str]],
    offsets: list[int],
) -> Generator[None, None, list[tuple[PodcastShow, PodcastEpisode]] | None]:
    """Resolve displayed rows only; a moved or removed row invalidates the plan."""
    shows = {show.id: show for show in library.shows}
    resolved: list[tuple[PodcastShow, PodcastEpisode]] = []
    for index, ((show_id, guid), offset) in enumerate(zip(pairs, offsets, strict=True)):
        show = shows.get(show_id)
        if show is None or not 0 <= offset < len(show.episodes):
            return None
        episode = show.episodes[offset]
        if episode.guid != guid:
            return None
        resolved.append((show, episode))
        if (index + 1) % RECORDS_PER_CHUNK == 0:
            yield
    return resolved
