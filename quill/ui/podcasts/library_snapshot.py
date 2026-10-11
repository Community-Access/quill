"""Detached library copies, prepared in bounded turns of the wx event loop."""

from __future__ import annotations

import copy
import dataclasses
from collections.abc import Callable, Generator
from time import perf_counter
from typing import Any

EPISODES_PER_TURN = 256
ITEMS_PER_TURN = 128
TURN_BUDGET_SECONDS = 0.008


def copy_show_metadata(show: Any) -> Any:
    """Detach a show's metadata without copying its episode catalogue."""
    copied = copy.copy(show)
    names = (
        [field.name for field in dataclasses.fields(show)]
        if dataclasses.is_dataclass(show)
        else list(vars(show))
    )
    for name in names:
        if name != "episodes":
            setattr(copied, name, copy.deepcopy(getattr(show, name)))
    copied.episodes = []
    return copied


def snapshot_chunks(
    library: Any,
    *,
    show_ids: set[str] | None = None,
    metadata_only: bool = False,
    shows_only: bool = False,
) -> Generator[None, None, Any]:
    """Yield between small copies; return the completely detached generation."""
    snapshot = copy.copy(library)
    names = (
        [field.name for field in dataclasses.fields(library)]
        if dataclasses.is_dataclass(library)
        else list(vars(library))
    )
    for name in names:
        if shows_only and name != "shows":
            continue
        value = getattr(library, name)
        if name == "shows":
            if metadata_only:
                continue
            snapshot.shows = []
            for show in list(value):
                if show_ids is not None and show.id not in show_ids:
                    continue
                copied_show = copy_show_metadata(show)
                snapshot.shows.append(copied_show)
                episodes = list(show.episodes)
                for offset in range(0, len(episodes), EPISODES_PER_TURN):
                    copied_show.episodes.extend(
                        copy.deepcopy(episodes[offset : offset + EPISODES_PER_TURN])
                    )
                    yield
                if not episodes:
                    yield
        elif name == "playlists":
            snapshot.playlists = []
            for playlist in value:
                copied = copy.copy(playlist)
                copied.rules = copy.deepcopy(playlist.rules)
                copied.items = []
                items = list(playlist.items)
                for offset in range(0, len(items), ITEMS_PER_TURN):
                    copied.items.extend(copy.deepcopy(items[offset : offset + ITEMS_PER_TURN]))
                    yield
                snapshot.playlists.append(copied)
                yield
        elif isinstance(value, (list, dict)):
            items = list(value.items()) if isinstance(value, dict) else list(value)
            target: Any = {} if isinstance(value, dict) else []
            setattr(snapshot, name, target)
            for offset in range(0, len(items), ITEMS_PER_TURN):
                batch = copy.deepcopy(items[offset : offset + ITEMS_PER_TURN])
                if isinstance(target, dict):
                    target.update(batch)
                else:
                    target.extend(batch)
                yield
        else:
            setattr(snapshot, name, copy.deepcopy(value))
            yield
    return snapshot


class SnapshotJob:
    """A cancellable copy with no worker access to the UI-owned library."""

    def __init__(
        self,
        library: Any,
        wx: Any,
        *,
        completed: Callable[[Any], None],
        failed: Callable[[BaseException], None],
        show_ids: set[str] | None = None,
        alive: Callable[[], bool] | None = None,
    ) -> None:
        self._chunks = snapshot_chunks(library, show_ids=show_ids)
        self._wx = wx
        self._completed = completed
        self._failed = failed
        self._alive = alive
        self._later: Any = None
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True
        if self._later is not None:
            self._later.Stop()
            self._later = None
        self._chunks.close()

    def start(self) -> None:
        self._advance()

    def _advance(self) -> None:
        self._later = None
        if self.cancelled:
            return
        if self._alive is not None and not self._alive():
            self.cancel()
            return
        call_later = getattr(self._wx, "CallLater", None)
        deadline = perf_counter() + TURN_BUDGET_SECONDS
        while True:
            try:
                next(self._chunks)
            except StopIteration as result:
                self._completed(result.value)
                return
            except Exception as error:
                self._failed(error)
                return
            if callable(call_later) and perf_counter() >= deadline:
                self._later = call_later(1, self._advance)
                return
