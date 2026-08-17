"""Change where the Quill family stores its data -- from any app.

QUILL has had the data-location machinery since #615: the Setup Wizard's
data-location page, ``storage-mode.json``, and the restart-deferred move in
``core.data_location``. What it never had was a surface *outside* QUILL --
a Quill Radio or QUILL Cast user had no way to point the shared profile at
a synced folder at all. This dialog is that surface, shared by the
standalone apps' Preferences.

The point of a custom folder is cross-machine sync: pick a folder that
Dropbox, OneDrive, Google Drive or iCloud already keeps in sync and the
whole family's settings, favorites, and subscriptions travel between
machines with no account and no API -- the sync client does the moving.
The move itself is restart-deferred (a live move is not safe while
Settings objects hold the old path), exactly like QUILL's Preferences.

One dialog per family rule: modal via the host's ``_show_modal_dialog``,
every control named, no control reachable only by pointer.
"""

from __future__ import annotations

from typing import Any

import wx

from quill.core import storage_mode
from quill.ui.dialog_contract import apply_modal_ids


def surface_data_folder_startup(host: Any, *, announce: Any = None) -> None:
    """Launch-time surfacing, called deferred once *host* can announce.

    Two one-liners: the result of a Data Folder move applied earlier this
    launch (consumed once, so only the launch that moved says anything), and
    the two-machines warning when a synced custom folder was stamped by a
    different computer minutes ago. Never raises -- a courtesy must not
    break a launch. *announce* overrides ``host._announce`` for hosts whose
    announcer has a different name (QUILL's ``_announce_result``).
    """
    try:
        from quill.core.data_location import pop_pending_migration_notice
        from quill.core.paths import app_data_dir
        from quill.core.profile_heartbeat import startup_profile_guard

        say = announce if announce is not None else host._announce
        notice = pop_pending_migration_notice()
        if notice:
            say(notice)
        if storage_mode.load_storage_mode() == "custom":
            warning = startup_profile_guard(app_data_dir())
            if warning:
                say(warning)
    except Exception:  # noqa: BLE001
        return


def open_data_folder_dialog(host: Any, *, app_title: str) -> None:
    """Show the Data Folder dialog and apply (queue) whatever it decides.

    *host* is an app frame: ``.frame``, ``._announce``, ``._show_modal_dialog``.
    """
    from quill.core.data_location import (
        pending_data_location_target,
        request_data_location_change,
    )
    from quill.core.paths import app_data_dir

    current = app_data_dir().resolve()
    portable_root = storage_mode.portable_root_dir()
    mode = storage_mode.load_storage_mode() or "appdata"

    dialog = wx.Dialog(host.frame, title="Data Folder", style=wx.DEFAULT_DIALOG_STYLE)
    sizer = wx.BoxSizer(wx.VERTICAL)

    where = wx.StaticText(
        dialog, label=f"Your data is stored at:\n{current}", name="data_folder.current"
    )
    sizer.Add(where, flag=wx.ALL, border=12)

    tip = wx.StaticText(
        dialog,
        label=(
            "Settings, favorites, subscriptions, and playback positions for every "
            "Quill app live here. Choosing a folder that Dropbox, OneDrive, Google "
            "Drive, or iCloud already keeps in sync carries them between your "
            "computers -- the sync client does the rest. Do not run Quill apps on "
            "two computers against the same folder at the same time."
        ),
        name="data_folder.tip",
    )
    tip.Wrap(440)
    sizer.Add(tip, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM, border=12)

    appdata_radio = wx.RadioButton(
        dialog,
        label="In my &user profile (recommended)",
        name="data_folder.appdata",
        style=wx.RB_GROUP,
    )
    sizer.Add(appdata_radio, flag=wx.LEFT | wx.BOTTOM, border=12)

    portable_radio = wx.RadioButton(
        dialog,
        label="Next to the app, on this &portable drive",
        name="data_folder.portable",
    )
    portable_radio.Show(portable_root is not None)
    sizer.Add(portable_radio, flag=wx.LEFT | wx.BOTTOM, border=12)

    custom_radio = wx.RadioButton(
        dialog, label="A &folder I choose (synced folders welcome):", name="data_folder.custom"
    )
    sizer.Add(custom_radio, flag=wx.LEFT | wx.BOTTOM, border=4)

    # A StaticText display, not a TextCtrl, so a screen reader does not offer
    # an editable field the Choose dialog owns (same reasoning as the Setup
    # Wizard's data-location page, #610).
    chosen: dict[str, str] = {"path": ""}
    custom_row = wx.BoxSizer(wx.HORIZONTAL)
    custom_display = wx.StaticText(dialog, label="No folder chosen", name="data_folder.custom_path")
    choose_btn = wx.Button(dialog, label="C&hoose...", name="data_folder.choose")
    custom_row.Add(custom_display, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
    custom_row.Add(choose_btn, 0, wx.ALIGN_CENTER_VERTICAL)
    sizer.Add(custom_row, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=12)

    if mode == "custom":
        custom_radio.SetValue(True)
        chosen["path"] = str(current)
        custom_display.SetLabel(str(current))
    elif mode == "portable" and portable_root is not None:
        portable_radio.SetValue(True)
    else:
        appdata_radio.SetValue(True)

    def _on_choose(_event: object) -> None:
        with wx.DirDialog(
            dialog,
            "Choose a folder for Quill's data",
            defaultPath=chosen["path"],
            style=wx.DD_DEFAULT_STYLE,
        ) as picker:
            if picker.ShowModal() != wx.ID_OK:
                return
            chosen["path"] = picker.GetPath()
        custom_display.SetLabel(chosen["path"])
        dialog.Layout()
        custom_radio.SetValue(True)

    choose_btn.Bind(wx.EVT_BUTTON, _on_choose)

    buttons = dialog.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
    sizer.Add(buttons, flag=wx.EXPAND | wx.ALL, border=12)
    dialog.SetSizerAndFit(sizer)
    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)

    result = host._show_modal_dialog(dialog, "Data Folder")
    if result != wx.ID_OK:
        dialog.Destroy()
        return
    if custom_radio.GetValue() and chosen["path"]:
        new_mode: str = "custom"
        custom_path = chosen["path"]
    elif custom_radio.GetValue():
        dialog.Destroy()
        host._announce("No folder was chosen, so the data folder is unchanged.")
        return
    elif portable_radio.GetValue() and portable_root is not None:
        new_mode, custom_path = "portable", None
    else:
        new_mode, custom_path = "appdata", None
    dialog.Destroy()

    from pathlib import Path

    try:
        target = request_data_location_change(new_mode, Path(custom_path) if custom_path else None)
    except (ValueError, OSError) as error:
        host._announce(f"Could not change the data folder: {error}")
        return

    if pending_data_location_target() is None:
        host._announce(f"Data folder unchanged: already {target}.")
        return
    _offer_restart(host, app_title=app_title, target=target)


def _offer_restart(host: Any, *, app_title: str, target: object) -> None:
    """The move applies at next launch; offer that launch now (mirrors
    QUILL Preferences' restart offer for the same change)."""
    dialog = wx.MessageDialog(
        host.frame,
        f"{app_title}'s data will move to:\n{target}\n\nEvery Quill app applies "
        f"this the next time it starts. Restart {app_title} now?",
        "Data Folder Changed",
        wx.YES_NO | wx.ICON_INFORMATION,
    )
    dialog.SetYesNoLabels("Restart Now", "Later")
    apply_modal_ids(dialog, affirmative_id=wx.ID_YES, escape_id=wx.ID_NO)
    result = host._show_modal_dialog(dialog, "Data Folder Changed")
    dialog.Destroy()
    if result != wx.ID_YES:
        host._announce(f"The data folder change is saved and applies when {app_title} next starts.")
        return
    import subprocess
    import sys

    from quill.core.relaunch import build_relaunch_command

    try:
        subprocess.Popen(build_relaunch_command(sys.executable, sys.argv))
    except OSError as error:
        host._announce(f"Could not restart automatically: {error}. Please restart {app_title}.")
        return
    host.frame.Close()
