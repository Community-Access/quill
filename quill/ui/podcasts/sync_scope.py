"""Whether one podcast is kept on this device only (``ear.md`` 6.10).

The choice is device-local by design: it lives in this device's Sync Places
settings (``PlacesConfig.local_only``), never in the podcast library and never in
the shared Listening Places file, so it cannot travel to another device. A feed
that needs a sign-in, or carries a key in its address, is always kept on this
device, and the choice is shown locked with the reason.

Keeping a podcast on this device is never an unfollow: other devices simply stop
hearing about it, exactly as they do for a private feed.
"""

from __future__ import annotations

from typing import Any

#: Said beside a locked choice, and as its help.
PRIVATE_REASON = "This podcast needs a sign-in, so it always stays on this device."
HELP = (
    "With this on, nothing about this podcast goes to your sync folder -- not "
    "that you follow it, not its folder, not your place in its episodes -- and "
    "nothing about it is taken from there. It is not an unfollow: your other "
    "devices keep it as they have it. This is a choice for this device only; "
    "set it on each device where you want it."
)


def _key(show: Any) -> str:
    from quill.core.sync.subscriptions_sync import subscription_id

    url = str(getattr(show, "feed_url", "") or "")
    return subscription_id(url) if url else ""


def state(show: Any) -> tuple[bool, bool]:
    """``(kept_local, locked)`` for *show* on this device."""
    from quill.core.sync.subscriptions_sync import is_private

    if is_private(show):
        return True, True
    if getattr(show, "is_local", False) or not _key(show):
        return True, True  # a local show has no feed to share
    try:
        from quill.core.paths import app_data_dir
        from quill.core.sync import places_config

        chosen = set(places_config.load(app_data_dir()).local_only)
    except Exception:  # noqa: BLE001 - an unreadable config means "not chosen"
        chosen = set()
    return _key(show) in chosen, False


def set_kept_local(show: Any, kept: bool) -> bool:
    """Save the choice for *show*. Returns whether it was saved."""
    key = _key(show)
    if not key:
        return False
    try:
        from quill.core.paths import app_data_dir
        from quill.core.sync import places_config

        data_dir = app_data_dir()
        config = places_config.load(data_dir)
        chosen = set(config.local_only)
        if kept:
            chosen.add(key)
        else:
            chosen.discard(key)
        config.local_only = sorted(chosen)
        places_config.save(data_dir, config)
    except Exception:  # noqa: BLE001 - said by the caller, never a traceback
        return False
    return True
