"""Copy episode JSON rather than allocating a second catalogue of model objects."""

from __future__ import annotations

import copy
from collections.abc import Generator
from typing import Any

from quill.ui.podcasts.library_snapshot import ITEMS_PER_TURN

PAYLOAD_TURN_BUDGET_SECONDS = 0.003


def show_payload_chunks(
    library: Any, *, show_ids: set[str] | None = None
) -> Generator[None, None, list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    for show in list(library.shows):
        if show_ids is not None and show.id not in show_ids:
            continue
        metadata = copy.copy(show)
        metadata.episodes = []
        record = metadata.to_dict()
        records.append(record)
        episodes = list(show.episodes)
        for offset in range(0, len(episodes), ITEMS_PER_TURN):
            record["episodes"].extend(
                episode.to_dict() for episode in episodes[offset : offset + ITEMS_PER_TURN]
            )
            yield
        if not episodes:
            yield
    return records
