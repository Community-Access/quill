"""Yielding feed commits that retain the live episode objects used by playback and Undo."""

from __future__ import annotations

import copy
import html
from collections.abc import Callable, Generator
from time import perf_counter
from typing import Any

from quill.core.podcasts.subscriptions import merge_episode_metadata

ITEMS_PER_TURN = 128
TURN_BUDGET_SECONDS = 0.008


def _reference_keys(
    host: Any, items: Callable[[], list[Any]]
) -> Generator[None, None, set[tuple[str, str]]]:
    while True:
        revision = int(host.__dict__.get("_podcast_unscoped_revision", 0))
        original = items()
        count = len(original)
        keys = set()
        for index, item in enumerate(original):
            keys.add((item.show_id, item.episode_guid))
            if (index + 1) % ITEMS_PER_TURN == 0:
                yield
        if (
            items() is original
            and len(original) == count
            and revision == int(host.__dict__.get("_podcast_unscoped_revision", 0))
        ):
            return keys


def commit_steps(
    host: Any, prepared: Any, *, progress: dict[str, bool] | None = None
) -> Generator[None, None, Any]:
    progress = {} if progress is None else progress
    library = host._podcast_library
    show = library.find_show(prepared.show_id)
    source = prepared.library.find_show(prepared.show_id)
    if show is None or source is None:
        return None
    original = show.episodes
    original_count = len(original)
    signature: list[tuple[str, int]] = []
    existing: dict[str, Any] = {}
    for index, episode in enumerate(original):
        existing[episode.guid] = episode
        signature.append((episode.guid, id(episode)))
        if (index + 1) % ITEMS_PER_TURN == 0:
            yield
    merged: list[Any] = []
    included: set[str] = set()
    for index, incoming in enumerate(source.episodes):
        if (
            prepared.episode_before is not None
            and incoming.guid in prepared.episode_before
            and incoming.guid not in existing
        ):
            continue
        episode = existing.get(incoming.guid)
        if episode is None:
            episode = incoming
        else:
            publisher = incoming
            if incoming.feed_title:
                publisher = copy.copy(incoming)
                publisher.title = incoming.feed_title
            merge_episode_metadata(episode, publisher)
            progress["changed"] = True
        merged.append(episode)
        included.add(episode.guid)
        existing[episode.guid] = episode
        if (index + 1) % ITEMS_PER_TURN == 0:
            yield
    if show.episodes is not original:
        return None
    for index, episode in enumerate(original):
        if episode.guid not in included:
            merged.append(episode)
            included.add(episode.guid)
        if (index + 1) % ITEMS_PER_TURN == 0:
            yield
    for attribute in ("fresh", "returned", "auto_download"):
        references: list[Any] = []
        for index, episode in enumerate(getattr(prepared, attribute)):
            if episode.guid in existing:
                references.append(existing[episode.guid])
            if (index + 1) % ITEMS_PER_TURN == 0:
                yield
        setattr(prepared, attribute, references)
    revision = int(host.__dict__.get("_podcast_unscoped_revision", 0))
    if len(original) != original_count:
        return None
    for index, episode in enumerate(original):
        if index >= len(signature) or signature[index] != (episode.guid, id(episode)):
            return None
        if (index + 1) % ITEMS_PER_TURN == 0:
            yield
    if (
        show.episodes is not original
        or len(original) != original_count
        or revision != int(host.__dict__.get("_podcast_unscoped_revision", 0))
    ):
        return None
    show.title = html.unescape(show.title)
    show.tags = source.tags
    show.episodes = merged
    progress["changed"] = True
    state = prepared.library.show_check_state.get(prepared.show_id)
    if state:
        library.show_check_state[prepared.show_id] = state
    else:
        library.show_check_state.pop(prepared.show_id, None)
    review = prepared.library.episode_filter_reviews.get(prepared.show_id)
    if review is None:
        library.episode_filter_reviews.pop(prepared.show_id, None)
    else:
        library.episode_filter_reviews[prepared.show_id] = review
    queued = yield from _reference_keys(host, lambda: library.queue)
    queue = library.queue
    queue_count = len(queue)
    queue_revision = int(host.__dict__.get("_podcast_unscoped_revision", 0))
    prepared.queued = 0
    for index, item in enumerate(prepared.queue_additions):
        episode = existing.get(item.episode_guid)
        if episode is None or episode.played:
            continue
        if (
            library.queue is not queue
            or len(queue) != queue_count
            or queue_revision != int(host.__dict__.get("_podcast_unscoped_revision", 0))
        ):
            queued = yield from _reference_keys(host, lambda: library.queue)
            queue = library.queue
            queue_count = len(queue)
            queue_revision = int(host.__dict__.get("_podcast_unscoped_revision", 0))
        key = (item.show_id, item.episode_guid)
        if key not in queued:
            library.queue.append(item)
            queued.add(key)
            queue_count += 1
            prepared.queued += 1
        if (index + 1) % ITEMS_PER_TURN == 0:
            yield
    for index, (key, changed) in enumerate(prepared.assignment_changes.items()):
        if library.inbox_assignments.get(key) == prepared.assignment_before.get(key):
            if changed is None:
                library.inbox_assignments.pop(key, None)
            else:
                library.inbox_assignments[key] = changed
        if (index + 1) % ITEMS_PER_TURN == 0:
            yield
    for playlist_id, additions in prepared.playlist_additions.items():
        target = library.find_playlist(playlist_id)
        if target is None:
            continue
        known = yield from _reference_keys(host, lambda target=target: target.items)
        items = target.items
        count = len(items)
        revision = int(host.__dict__.get("_podcast_unscoped_revision", 0))
        for index, item in enumerate(additions):
            if item.episode_guid not in existing:
                continue
            if library.find_playlist(playlist_id) is not target:
                break
            if (
                target.items is not items
                or len(items) != count
                or revision != int(host.__dict__.get("_podcast_unscoped_revision", 0))
            ):
                known = yield from _reference_keys(host, lambda target=target: target.items)
                items = target.items
                count = len(items)
                revision = int(host.__dict__.get("_podcast_unscoped_revision", 0))
            key = (item.show_id, item.episode_guid)
            if key not in known:
                target.items.append(item)
                known.add(key)
                count += 1
            if (index + 1) % ITEMS_PER_TURN == 0:
                yield
    return show


def commit(
    host: Any,
    prepared: Any,
    *,
    active: Callable[[], bool],
    completed: Callable[[Any], None],
    failed: Callable[[BaseException], None],
) -> None:
    progress: dict[str, bool] = {}
    steps = commit_steps(host, prepared, progress=progress)
    timers = host.__dict__.setdefault("_podcast_feed_snapshot_timers", [])
    wx = host.__dict__.get("_wx")
    call_later = getattr(wx, "CallLater", None)
    registered = False
    finished = False
    cancellations = host.__dict__.setdefault("_podcast_feed_commit_cancellations", [])

    def schedule() -> None:
        timer: Any = None

        def resume() -> None:
            timers[:] = [item for item in timers if item is not timer]
            advance()

        timer = call_later(1, resume)
        timers.append(timer)

    def finish(result: Any, *, interrupted: bool = False, notify: bool = True) -> None:
        nonlocal finished
        if finished:
            return
        finished = True
        if registered:
            host._podcast_commit_depth -= 1
        cancellations[:] = [callback for callback in cancellations if callback is not cancel]
        if interrupted and progress.get("changed"):
            from quill.ui.podcasts.save_snapshot import save_show

            if host._podcast_library.find_show(prepared.show_id) is not None:
                save_show(host, prepared.show_id)
        if notify:
            completed(result)

    def cancel() -> None:
        steps.close()
        finish(None, interrupted=True)

    cancellations.append(cancel)

    def advance() -> None:
        nonlocal registered
        if finished:
            return
        if not active():
            cancel()
            return
        if not registered:
            if callable(call_later) and host.__dict__.get("_podcast_snapshot_state") is not None:
                schedule()
                return
            host._podcast_commit_depth = int(host.__dict__.get("_podcast_commit_depth", 0)) + 1
            registered = True
        deadline = perf_counter() + TURN_BUDGET_SECONDS
        try:
            while True:
                next(steps)
                if callable(call_later) and perf_counter() >= deadline:
                    schedule()
                    return
        except StopIteration as result:
            finish(result.value, interrupted=result.value is None)
        except Exception as error:
            finish(None, interrupted=True, notify=False)
            failed(error)

    advance()
