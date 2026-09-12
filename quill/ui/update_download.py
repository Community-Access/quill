"""Fetching an update and offering to install it -- once, for every app.

:mod:`quill.ui.update_notice` is the dialog that *offers* an update. This is
what happens after the user says yes: the asset downloads off the UI thread
with coarse spoken milestones, and then one dialog offers **Install and restart
now**, **Open folder** or **Close**.

It lives here rather than on ``AppShellFrame`` because QuillLite is not an
AppShell app -- it is an MDI editor with no command registry, no tray icon and
no task manager -- and "QuillLite cannot update itself" is not an acceptable
consequence of that. The host supplies four small things (a parent window, a
way to speak, a way to run a modal, and a way to run work in the background)
and gets the same update experience as everything else in the family.

The background runner is passed in rather than imported so each host keeps its
own: the companion apps hand over ``QuillTaskManager.submit``, which drains and
cancels on shutdown; QuillLite hands over a one-shot thread, because it has no
task manager and a single download does not justify one.
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

import wx

from quill.core.file_manager import reveal_command
from quill.ui.accessible_names import set_accessible_name
from quill.ui.dialog_contract import apply_modal_ids

__all__ = [
    "Submit",
    "apply_and_restart",
    "download_and_offer_install",
    "offer_install",
    "thread_submit",
]


class Submit(Protocol):
    """The background runner, shaped like ``QuillTaskManager.submit``.

    ``func`` is called with the task manager's injected keyword arguments
    (``cancellation_token``, ``operation_id``, ``progress_callback``), so every
    closure passed here absorbs ``**kwargs``. The callbacks take
    ``(name, result)`` and ``(name, error)``.
    """

    def __call__(
        self,
        name: str,
        func: Callable[..., Any],
        *,
        on_success: Callable[[str, Any], None] | None = ...,
        on_failure: Callable[[str, BaseException], None] | None = ...,
    ) -> Any: ...


def thread_submit(
    name: str,
    func: Callable[..., Any],
    *,
    on_success: Callable[[str, Any], None] | None = None,
    on_failure: Callable[[str, BaseException], None] | None = None,
) -> None:
    """A ``Submit`` for a host with no task manager (QuillLite).

    One daemon thread, one result, no cancellation -- which is honest for this
    job: an update download the user explicitly asked for, whose only failure
    mode is a network error the callback reports. The callbacks are invoked on
    the worker thread exactly as the task manager does it; every caller here
    marshals back with ``wx.CallAfter``.
    """
    import threading

    def _run() -> None:
        try:
            result = func(
                cancellation_token=None,
                operation_id=name,
                progress_callback=lambda *_a, **_k: None,
            )
        except BaseException as error:  # noqa: BLE001 - mirrors QuillTaskManager
            if on_failure is not None:
                on_failure(name, error)
            return
        if on_success is not None:
            on_success(name, result)

    threading.Thread(  # GATE-40-OK: one-shot update download for a host with no
        # task manager (QuillLite); nothing to cancel, result reported to the caller.
        target=_run,
        name=f"quill-{name}",
        daemon=True,
    ).start()


def download_and_offer_install(
    parent: wx.Window,
    *,
    release: Any,
    target_dir: Path,
    portable: bool,
    announce: Callable[[str], Any],
    show_message_box: Callable[..., Any],
    show_modal_dialog: Callable[[Any, str], int],
    submit: Submit,
    close_app: Callable[[], Any],
) -> None:
    """Download the release asset to *target_dir*, then offer install actions.

    Progress is announced at 25/50/75 percent rather than continuously: a
    percentage read out on every socket read is noise, and three milestones are
    enough to know the thing is moving. A release with no downloadable asset
    falls back to opening its web page, which is the only remaining honest
    answer.
    """
    from quill.core.updates import download_release_asset

    url = str(getattr(release, "download_url", "") or "")
    version = str(getattr(release, "version", "") or "")
    if "/releases/download/" not in url:
        import webbrowser

        if url and webbrowser.open(url):
            announce(f"Opened download page for {version}")
        else:
            announce("No downloadable update asset found.")
        return

    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / (url.rsplit("/", 1)[-1] or f"update-{version}")
    announce(f"Downloading update {version}")
    last_milestone = {"value": -1}

    def _progress(done: int, total: int) -> None:
        if total <= 0:
            return
        percent = int(done * 100 / total)
        milestone = percent - (percent % 25)
        if milestone > last_milestone["value"] and milestone in (25, 50, 75):
            last_milestone["value"] = milestone
            wx.CallAfter(announce, f"Update download {milestone} percent")

    def _download(**_kw: object) -> None:
        # Absorb the task manager's injected kwargs (cancellation_token, ...).
        download_release_asset(
            url,
            target,
            progress=_progress,
            expected_sha256=str(getattr(release, "download_digest", "") or ""),
        )

    def _downloaded(_name: str, _result: object) -> None:
        wx.CallAfter(
            offer_install,
            parent,
            release=release,
            target=target,
            portable=portable,
            announce=announce,
            show_message_box=show_message_box,
            show_modal_dialog=show_modal_dialog,
            close_app=close_app,
        )

    def _failed(_name: str, error: BaseException) -> None:
        wx.CallAfter(
            show_message_box,
            f"Update download failed: {error}",
            "Check for Updates",
            wx.ICON_ERROR | wx.OK,
        )

    submit("app-update-download", _download, on_success=_downloaded, on_failure=_failed)


def offer_install(
    parent: wx.Window,
    *,
    release: Any,
    target: Path,
    portable: bool,
    announce: Callable[[str], Any],
    show_message_box: Callable[..., Any],
    show_modal_dialog: Callable[[Any, str], int],
    close_app: Callable[[], Any],
) -> None:
    """Post-download: Install and restart now, Open folder, or Close.

    Close is the escape and carries no access key (GATE-14); Install is the
    default when the asset is something this platform can actually apply.
    """
    version = str(getattr(release, "version", "") or "")
    announce(f"Update {version} downloaded")
    applyable = str(target).lower().endswith((".exe", ".msi", ".zip")) and sys.platform.startswith(
        "win"
    )
    action_line = (
        "Select 'Install and restart now' to update and relaunch automatically "
        "-- your settings and data are kept -- or "
        if applyable
        else ""
    )
    dialog = wx.Dialog(
        parent, title="Update downloaded", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
    )
    dialog.SetSize((500, 240))
    sizer = wx.BoxSizer(wx.VERTICAL)
    body = wx.TextCtrl(
        dialog,
        value=(
            f"Update {version} downloaded.\n\n"
            f"Saved to: {target}\n\n"
            f"{action_line}Select 'Open folder' to find it."
        ),
        style=wx.TE_MULTILINE | wx.TE_READONLY,
        name="update_body",
    )
    set_accessible_name(body, "Update details, read-only")
    sizer.Add(body, 1, wx.EXPAND | wx.ALL, 12)
    buttons = wx.BoxSizer(wx.HORIZONTAL)
    buttons.AddStretchSpacer()
    close_btn = wx.Button(dialog, wx.ID_CANCEL, label="Close")
    folder_btn = wx.Button(dialog, wx.ID_OPEN, label="Open folder")
    close_btn.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_CANCEL))
    folder_btn.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_OPEN))
    buttons.Add(close_btn, 0, wx.RIGHT, 6)
    buttons.Add(folder_btn, 0, wx.RIGHT, 6)
    if applyable:
        apply_btn = wx.Button(dialog, wx.ID_OK, label="Install and restart now")
        apply_btn.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_OK))
        apply_btn.SetDefault()
        buttons.Add(apply_btn, 0)
    else:
        close_btn.SetDefault()
    sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 12)
    dialog.SetSizer(sizer)
    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
    dialog.CentreOnParent()
    result = show_modal_dialog(dialog, "Update downloaded")
    dialog.Destroy()
    if result == wx.ID_OPEN:
        subprocess.Popen(reveal_command(target))  # noqa: S603 - shared, tested argv
        return
    if result == wx.ID_OK and applyable:
        apply_and_restart(
            release=release,
            target=Path(str(target)),
            portable=portable,
            announce=announce,
            show_message_box=show_message_box,
            close_app=close_app,
        )


def apply_and_restart(
    *,
    release: Any,
    target: Path,
    portable: bool,
    announce: Callable[[str], Any],
    show_message_box: Callable[..., Any],
    close_app: Callable[[], Any],
) -> None:
    """Apply the downloaded update and relaunch (one click).

    *close_app* is called only on success -- on any failure the app stays open
    and the user can still open the folder and update by hand, because an
    update that cannot be applied must never leave somebody with no editor.
    Passed in rather than derived from a window: for QuillLite the thing to
    close is the MDI shell, not the document the dialog is parented to.
    """
    from quill.core.paths import app_data_dir
    from quill.ui.update_apply import apply_update_and_restart

    if apply_update_and_restart(
        target=target,
        portable=portable,
        version=str(getattr(release, "version", "")),
        app_data_dir=app_data_dir(),
        announce=announce,
        show_error=lambda msg: show_message_box(msg, "Update", wx.ICON_ERROR | wx.OK),
    ):
        close_app()
