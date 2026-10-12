"""The app side of shared family choices (qc.md X-05): join, publish, adopt, say.

Each app calls :func:`at_launch` once it is up and :func:`after_preferences`
after its Preferences saved. Both speak when anything was taken from the other
apps, because a choice that changes under you without a word is exactly what
X-05 forbids.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core import family_preferences as family


def _save(
    app_id: str,
    history: Any,
    radio_save: Callable[[], None] | None = None,
) -> None:
    from quill.core.paths import app_data_dir

    try:
        if app_id == "cast":
            from quill.core.podcasts.history import save_history

            save_history(app_data_dir(), history)
        elif app_id == "radio":
            if radio_save is not None:
                radio_save()
                return
            from quill.core.radio.history_store import save_history as save_radio

            save_radio(app_data_dir(), history)
    except Exception:  # noqa: BLE001 - the choice still holds for this session
        return


def at_launch(host: Any, app_id: str, history: Any) -> None:
    """Take the shared values this app differs on, and say which."""
    from quill.core.paths import app_data_dir

    if not getattr(history, "share_family_prefs", False):
        return
    changed = family.adopt(app_data_dir(), app_id, history)
    if changed:
        _save(app_id, history)
        host._announce(f"Using your shared choice for {family.words_for(changed)}.")


def after_preferences(host: Any, app_id: str, history: Any, changes: dict[str, object]) -> None:
    """After Preferences saved: join or leave, or publish what changed."""
    adopted = apply_preferences(app_id, history, changes)
    if adopted:
        radio_save = getattr(host, "_save_radio_history", None) if app_id == "radio" else None
        _save(app_id, history, radio_save if callable(radio_save) else None)
        host._announce(f"Now using your shared choice for {family.words_for(adopted)}.")


def apply_preferences(
    app_id: str,
    history: Any,
    changes: dict[str, object],
    *,
    data_dir: Path | None = None,
) -> list[str]:
    """Apply sharing to a detached record without touching a window or speaking."""
    from quill.core.paths import app_data_dir

    if data_dir is None:
        data_dir = app_data_dir()
    on = bool(getattr(history, "share_family_prefs", False))
    if "share_family_prefs" in changes and on != family.is_sharing(data_dir, app_id):
        return family.set_sharing(data_dir, app_id, on, history)
    if on:
        family.publish(data_dir, app_id, history, changed=changes.keys())
    return []
