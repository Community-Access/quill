"""Read-only peer places, prepared off the UI thread for natural Queue advance.

Only a completed snapshot can influence the next episode's initial position.
An unavailable or late shared folder leaves the local place in charge; there
is never a callback that seeks a loaded player.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Event, Thread
from typing import Any

from quill.core.sync.listening_places import PlaceRecord


@dataclass(slots=True)
class Snapshot:
    ready: Event = field(default_factory=Event)
    records: dict[str, PlaceRecord] = field(default_factory=dict)


def _read() -> dict[str, PlaceRecord]:
    from quill.core.paths import app_data_dir
    from quill.core.sync.listening_places import read_other_devices, remote_view
    from quill.core.sync.places_config import load

    config = load(app_data_dir())
    if (
        not config.interchange_ready
        or config.encrypted
        or config.share_subscriptions
        or not config.device_id
    ):
        return {}
    return remote_view(read_other_devices(config.remote_dir, config.device_id))


def prefetch(host: Any) -> None:
    """Start a fresh read without waiting for the shared folder or touching UI."""
    if getattr(host, "_startup_app_id", None) != "cast":
        return
    pending = getattr(host, "_cast_queue_places", None)
    if pending is not None and not pending.ready.is_set():
        return  # a sleeping share gets one reader, not a new thread per resume
    snapshot = Snapshot()
    host._cast_queue_places = snapshot

    def work() -> None:
        try:
            snapshot.records = _read()
        except Exception:  # noqa: BLE001 - an optional peer read cannot stop playback
            pass
        finally:
            snapshot.ready.set()

    try:
        Thread(target=work, name="cast-queue-place", daemon=True).start()
    except RuntimeError:
        snapshot.ready.set()  # no worker; local position remains the fallback


def newest_queue_place(host: Any, show: Any, episode: Any) -> int | None:
    """Use a completed peer event only when consent and last-write-wins allow it."""
    snapshot = getattr(host, "_cast_queue_places", None)
    if snapshot is None or not snapshot.ready.is_set():
        return None
    from quill.core.paths import app_data_dir
    from quill.core.sync.listening_places import episode_id
    from quill.core.sync.places_config import load
    from quill.core.sync.subscriptions_sync import is_private

    # Consent may have changed after the background read started.
    config = load(app_data_dir())
    if (
        not config.interchange_ready
        or config.encrypted
        or config.share_subscriptions
        or is_private(show)
        or config.subscription_policy().keeps_local(show)
    ):
        return None
    key = episode_id(
        str(getattr(episode, "guid", "") or ""),
        str(getattr(episode, "audio_url", "") or ""),
    )
    record = snapshot.records.get(key)
    if (
        record is None
        or record.deleted
        or record.played
        or record.position_ms <= 0
        or not record.updated_at
        or record.updated_at < str(getattr(episode, "position_updated_at", "") or "")
    ):
        return None
    return record.position_ms
