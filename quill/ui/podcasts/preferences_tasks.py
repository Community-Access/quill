"""Ordered preference writes and guarded adoption, with no UI-thread file I/O."""

from __future__ import annotations

import copy
from typing import Any

from quill.core import family_preferences as family
from quill.core.paths import app_data_dir
from quill.core.podcasts import history as podcast_history
from quill.ui.family_sharing import apply_preferences
from quill.ui.podcasts import record_tasks

_FAILURE = "Preferences could not be saved. Recent Problems has the details."


def save_preferences(host: Any, changes: dict[str, object]) -> Any:
    history = host._podcast_history
    snapshot = copy.deepcopy(history)
    requested = copy.deepcopy(changes)
    before = {
        name: copy.deepcopy(getattr(history, name))
        for name in family.SHARED
        if hasattr(history, name)
    }
    generation = int(getattr(host, "_cast_preferences_generation", 0)) + 1
    host._cast_preferences_generation = generation
    data_dir = app_data_dir()

    def work() -> list[str]:
        adopted = apply_preferences("cast", snapshot, requested, data_dir=data_dir)
        podcast_history.save_history(data_dir, snapshot)
        return adopted

    def saved(adopted: list[str]) -> None:
        applied = []
        for name in adopted:
            if (
                host._podcast_history is history
                and name in before
                and getattr(history, name) == before[name]
            ):
                setattr(history, name, copy.deepcopy(getattr(snapshot, name)))
                applied.append(name)
        if applied:
            host._announce(f"Now using your shared choice for {family.words_for(applied)}.")
        finish(snapshot)

    def finish(written: Any) -> None:
        if written != host._podcast_history:
            latest = copy.deepcopy(host._podcast_history)
            record_tasks.submit(
                host,
                "preferences",
                lambda: podcast_history.save_history(data_dir, latest),
                on_success=lambda _result: finish(latest),
                failure_message=_FAILURE,
            )
        elif generation == getattr(host, "_cast_preferences_generation", None):
            host._announce("Application preferences saved.")

    return record_tasks.submit(
        host,
        "preferences",
        work,
        on_success=saved,
        failure_message=_FAILURE,
    )
