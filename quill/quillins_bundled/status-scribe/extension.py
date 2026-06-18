"""Status Scribe — live document statistics in the status bar.

Pushes a word/character/sentence count into a status bar cell after every save
and on tab activation.  Demonstrates:
- ``status_bar`` contribution (get_count_cell handler)
- ``api.log()`` developer logging routed to the Developer Console
- ``quillin.enabled`` / ``quillin.disabled`` lifecycle events
- ``settings.changed`` event for live preference hot-reload
"""

from __future__ import annotations

_last_count: int = 0


def register(api) -> None:
    api.register_command("on_after_save", on_after_save)
    api.register_command("on_activated", on_activated)
    api.register_command("on_enabled", on_enabled)
    api.register_command("on_disabled", on_disabled)
    api.register_command("on_settings_changed", on_settings_changed)
    api.register_command("on_timer_refresh", on_timer_refresh)
    api.register_command("get_count_cell", _get_count_cell_handler)


# ---------------------------------------------------------------------------
# Status bar cell handler
# ---------------------------------------------------------------------------


def _count_text(api) -> str:
    """Return the current cell text given a live API handle."""
    mode = api.get_setting("count_mode", "words")
    show_label = api.get_setting("show_label", True)
    prefix = {"words": "Words", "chars": "Chars", "sentences": "Sents"}.get(mode, "Words")
    if show_label:
        return f"{prefix}: {_last_count}"
    return str(_last_count)


def _get_count_cell_handler(api) -> None:
    """Push the current count into the status bar when the host polls the cell."""
    api.set_status(_count_text(api))


# ---------------------------------------------------------------------------
# Document event handlers
# ---------------------------------------------------------------------------


def on_after_save(api, event: dict) -> None:
    global _last_count
    _refresh_count(api)
    api.set_status(_count_text(api))
    if api.get_setting("announce_on_save", False):
        api.announce(_count_text(api))


def on_activated(api, event: dict) -> None:
    _refresh_count(api)
    api.set_status(_count_text(api))


def on_enabled(api, event: dict) -> None:
    api.log("Status Scribe enabled — status bar cell is live.")


def on_disabled(api, event: dict) -> None:
    global _last_count
    _last_count = 0
    api.log("Status Scribe disabled — cell cleared.")


def on_settings_changed(api, event: dict) -> None:
    key: str = event.get("key", "")
    value = event.get("value")
    api.log(f"Status Scribe setting changed: {key} = {value!r}")
    _refresh_count(api)
    api.set_status(_count_text(api))


def on_timer_refresh(api, event: dict) -> None:
    """Timer tick: recount the active document so the cell never goes stale.

    ``event`` carries ``timer_id`` and ``interval_seconds``.
    """
    interval = event.get("interval_seconds")
    _refresh_count(api)
    api.set_status(_count_text(api))
    api.log(f"Status Scribe: timer refresh ({interval}s) -> {_last_count}")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _refresh_count(api) -> None:
    global _last_count
    try:
        text: str = api.get_text()
    except Exception:
        return
    mode = api.get_setting("count_mode", "words")
    if mode == "chars":
        _last_count = len(text)
    elif mode == "sentences":
        import re

        _last_count = len(re.split(r"[.!?]+", text.strip())) if text.strip() else 0
    else:
        _last_count = len(text.split())
    api.log(f"Status Scribe: count refreshed to {_last_count} ({mode})")
