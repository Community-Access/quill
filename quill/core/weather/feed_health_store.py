"""Saving and loading alert-feed health (``weather_feed_health.json``). Split
from ``feed_health`` (GATE-11); wx-free. A missing file reads as "never checked";
a damaged one is kept aside and reads the same."""

from __future__ import annotations

import logging
from datetime import tzinfo
from pathlib import Path

from quill.core.weather.feed_health import FeedHealthTracker

logger = logging.getLogger(__name__)

_STORE_NAME = "weather_feed_health.json"


def store_path(data_dir: Path) -> Path:
    return data_dir / _STORE_NAME


def load_tracker(
    data_dir: Path, *, safe_mode: bool = False, tz: tzinfo | None = None
) -> FeedHealthTracker:
    """Read the saved health. Missing reads as "never checked"; a damaged file
    is kept aside (migration-backups) and also reads as "never checked"."""
    import json

    path = store_path(data_dir)
    if not path.exists():
        return FeedHealthTracker(safe_mode=safe_mode, tz=tz)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return FeedHealthTracker.from_json(raw, safe_mode=safe_mode, tz=tz)
    except (OSError, ValueError, TypeError, OverflowError) as exc:
        logger.warning("weather feed health is unreadable (%s); starting fresh", exc)
        try:
            from quill.core.migration_backup import backup_corrupt_file

            backup_corrupt_file("weather_feed_health", path)
        except Exception:  # noqa: BLE001 - keeping a copy is best effort
            pass
        return FeedHealthTracker(safe_mode=safe_mode, tz=tz)


def save_tracker(data_dir: Path, tracker: FeedHealthTracker) -> None:
    """Persist atomically. Best effort: health bookkeeping never breaks a poll."""
    from quill.core.storage import write_json_atomic

    try:
        write_json_atomic(store_path(data_dir), tracker.to_json())
    except OSError as exc:
        logger.warning("could not save weather feed health: %s", exc)
