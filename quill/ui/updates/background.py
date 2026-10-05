"""Background downloads on Beta and Dev, for every app's silent update check.

The automatic check in QUILL Lite, Quill Radio and QUILL Cast calls
:func:`silent_found` when it finds a newer build. On Stable it returns
``False`` and the app shows its update dialog exactly as before. On Beta and
Dev it fetches the file quietly first (resumable, checked against the signed
list), records it in Update History, says "Update 3.3.0 Beta 2 downloaded"
once, and only then shows the same dialog -- whose Update button now installs
straight away. Nothing is ever installed without that button.

When the download has to wait -- a metered connection, Quiet Hours, or a
Quill Radio recording -- Update History says why, and during Quiet Hours or a
recording no dialog appears at all (plan 6.7, "no surprise popups").
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import wx

from quill.core.updater import history
from quill.core.updater.background import background_gate, read_conditions
from quill.core.updater.channels import ChannelState
from quill.core.versioning import ReleaseVersion

__all__ = ["offer_downloaded", "shell_found", "silent_found"]

Submit = Callable[..., Any]


def _shown(version: str) -> str:
    parsed = ReleaseVersion.try_parse(version)
    return parsed.display() if parsed is not None else version


def silent_found(
    *,
    app_key: str,
    release: Any,
    state: ChannelState,
    target_dir: Path,
    submit: Submit,
    announce: Callable[[str], Any],
    on_ready: Callable[[Path], Any],
) -> bool:
    """Handle a silent check's find. ``True`` means the app should show nothing now.

    ``on_ready(path)`` runs on the UI thread once the file is downloaded and
    verified; the app then offers it (:func:`offer_downloaded`).
    """
    gate = background_gate(state, read_conditions())
    version = str(getattr(release, "version", "") or "")
    if not gate.download:
        if gate.reason:
            history.record(
                app_key, "held_back", to_version=version, channel=state.channel, detail=gate.reason
            )
        return not gate.may_show
    url = str(getattr(release, "download_url", "") or "")
    digest = str(getattr(release, "download_digest", "") or "")
    if "/releases/download/" not in url or not digest:
        return False  # nothing to verify against: the normal offer asks first
    size = int(getattr(release, "size", 0) or 0)
    dest = target_dir / url.rsplit("/", 1)[-1]

    def _download(**_kw: object) -> Path:
        from quill.core.updater.download import download_verified

        return download_verified(url, dest, sha256=digest, size=size)

    def _done(_name: str, path: object) -> None:
        history.record(app_key, "downloaded", to_version=version, channel=state.channel)
        wx.CallAfter(announce, f"Update {_shown(version)} downloaded")
        wx.CallAfter(on_ready, Path(str(path)))

    def _failed(_name: str, error: BaseException) -> None:
        # Quiet: the .partial is kept, and the next check picks up from there.
        history.record(
            app_key, "failed", to_version=version, channel=state.channel, detail=str(error)
        )

    submit("app-update-background-download", _download, on_success=_done, on_failure=_failed)
    return True


def offer_downloaded(
    parent: Any,
    *,
    app_name: str,
    current_version: str,
    release: Any,
    target: Path,
    portable: bool,
    announce: Callable[[str], Any],
    show_message_box: Callable[..., Any],
    show_modal_dialog: Callable[[Any, str], int],
    close_app: Callable[[], Any],
) -> None:
    """The usual update dialog; Update goes straight to the install choices."""
    from quill.ui.update_download import offer_install
    from quill.ui.update_notice import show_update_available

    choice = show_update_available(
        parent,
        app_name=app_name,
        current_version=current_version,
        release=release,
        show_modal_dialog=show_modal_dialog,
        announce=announce,
    )
    if choice != "update":
        return
    offer_install(
        parent,
        release=release,
        target=target,
        portable=portable,
        announce=announce,
        show_message_box=show_message_box,
        show_modal_dialog=show_modal_dialog,
        close_app=close_app,
    )


def shell_found(shell: Any, app_key: str, release: Any, state: Any, current_version: str) -> bool:
    """:func:`silent_found` for an app built on ``quill.ui.app_shell``.

    ``True`` when the silent check should show nothing now. Stable, and any
    app without release channels, answers ``False`` and is unchanged.
    """
    from quill.core.paths import app_data_dir
    from quill.core.updater.profiles import PROFILES

    if app_key not in PROFILES:
        return False
    return silent_found(
        app_key=app_key,
        release=release,
        state=state,
        target_dir=app_data_dir() / "updates",
        submit=shell._task_manager.submit,
        announce=shell._announce,
        on_ready=lambda path: offer_downloaded(
            shell.frame,
            app_name=shell._update_app_name(),
            current_version=current_version,
            release=release,
            target=path,
            portable=shell._running_portable_build(),
            announce=shell._announce,
            show_message_box=shell._show_message_box,
            show_modal_dialog=shell._show_modal_dialog,
            close_app=shell.frame.Close,
        ),
    )
