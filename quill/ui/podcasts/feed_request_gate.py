"""Guards that must run before one podcast feed request enters a worker."""

from __future__ import annotations

from typing import Any


def feed_request_active(host: Any, generation: int) -> bool:
    enabled = getattr(host, "_feature_enabled", None)
    return (
        generation == host.__dict__.get("_podcast_feed_generation", 0)
        and not host.__dict__.get("_cast_closing", False)
        and not host.__dict__.get("_cast_closed", False)
        and (not callable(enabled) or bool(enabled("core.podcasts")))
    )


def prepare_feed_request(host: Any, show_id: str) -> bool:
    try:
        from quill.ui.startup_launch import ensure_ssl_trust

        ensure_ssl_trust()
    except Exception as error:  # noqa: BLE001 - no feed may queue without trust
        host._announce(f"The podcast feed could not be checked. {error}")
        from quill.ui.podcasts import check_run

        check_run.step(host, show_id, failed_title="Security setup failed")
        return False
    return True
