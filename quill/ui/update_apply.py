"""Shared one-click "apply the downloaded update and restart" action.

Every Quill app's post-download dialog (Radio/Cast via ``app_shell``, QUILL via
``main_frame_updates``, Quill Social via its own frame) offers "Install and
restart now". They all do the same thing: hand the already-downloaded asset to
:func:`quill.core.self_update.begin_self_update` and, on success, close the
window so the detached helper can swap the files and relaunch. This is that one
shared bridge, kept thin and wx-free at the boundary -- callers pass their own
``announce``/``show_error`` hooks -- so the behavior lives (and is tested) in
exactly one place instead of being copy-pasted into each app's frame.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path


def apply_update_and_restart(
    *,
    target: Path,
    portable: bool,
    version: str,
    app_data_dir: Path,
    announce: Callable[[str], None],
    show_error: Callable[[str], None],
) -> bool:
    """Stage + launch the update helper for the downloaded ``target``.

    ``app_data_dir`` is the calling app's own data directory (where the update
    staging folder and apply log live) -- passed in so each app (which may have
    its own data root) stages under the right place. Returns ``True`` when the
    caller should now close its window (the helper is running and will relaunch
    the app), or ``False`` on failure -- in which case ``show_error`` has already
    been called and the app should stay open so the user can update manually via
    Open folder.
    """
    from quill.core import self_update

    announce(f"Installing update {version} and restarting")
    try:
        self_update.begin_self_update(
            download_path=target,
            portable=portable,
            app_data_dir=app_data_dir,
        )
    except self_update.SelfUpdateError as exc:
        show_error(
            f"Could not install the update automatically: {exc}\n\n"
            "You can still choose Open folder to update manually."
        )
        return False
    return True
