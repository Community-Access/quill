"""The app side of shared family choices (qc.md X-05): join, publish, adopt, say.

Each app calls :func:`at_launch` once it is up and :func:`after_preferences`
after its Preferences saved. Both speak when anything was taken from the other
apps, because a choice that changes under you without a word is exactly what
X-05 forbids.
"""

from __future__ import annotations

from typing import Any

from quill.core import family_preferences as family


def _save(app_id: str, history: Any) -> None:
    from quill.core.paths import app_data_dir

    try:
        if app_id == "cast":
            from quill.core.podcasts.history import save_history

            save_history(app_data_dir(), history)
        elif app_id == "radio":
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
    from quill.core.paths import app_data_dir

    data_dir = app_data_dir()
    on = bool(getattr(history, "share_family_prefs", False))
    if "share_family_prefs" in changes and on != family.is_sharing(data_dir, app_id):
        adopted = family.set_sharing(data_dir, app_id, on, history)
        if adopted:
            _save(app_id, history)
            host._announce(f"Now using your shared choice for {family.words_for(adopted)}.")
        return
    if on:
        family.publish(data_dir, app_id, history)
