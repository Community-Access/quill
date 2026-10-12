"""Detached storage totals and saved report columns, read on a worker."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from quill.core.media.list_columns import ColumnDef, ColumnLayouts
from quill.core.podcasts.list_columns import DOWNLOADS, FILE_NAME, SURFACES
from quill.core.podcasts.storage_maintenance import EpisodeKey, StorageUsage, storage_usage
from quill.core.podcasts.subscriptions import PodcastLibrary


@dataclass(frozen=True, slots=True)
class UsageReport:
    usage: StorageUsage
    columns: tuple[ColumnDef, ...]

    @property
    def unreadable(self) -> int:
        return self.usage.unreadable


def usage_report(
    library: PodcastLibrary, _protected: frozenset[EpisodeKey], data_dir: Path
) -> UsageReport:
    usage = storage_usage(library)
    try:
        raw = json.loads((data_dir / FILE_NAME).read_text(encoding="utf-8"))
    except FileNotFoundError:
        layouts = ColumnLayouts.defaults(SURFACES)
    else:
        layouts = ColumnLayouts.from_dict(SURFACES, raw)
    return UsageReport(usage, tuple(layouts.columns(DOWNLOADS.id)))
