"""QUILL Transcribe's menu bar and its tray menu.

Every enabled item shows its key (the family's menu rule); the tray menu, which
has no keys of its own, gives every row a distinct access letter instead, so a
screen-reader user can reach any row with one letter. The tray menu's commands
are bound on the menu itself, not on the frame: a tray popup routes its
commands through the menu it was handed (#1465).

The two status rows at the top of the tray menu -- what dictation is doing and
which model it uses -- are disabled read-outs, so arrowing past them says the
state without anything to press.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

__all__ = ["build_menu_bar", "build_tray_menu", "start_stop_label"]


def start_stop_label(host: Any) -> str:
    """The Start/Stop command as it should read now."""
    if host.dictation_armed():
        return "Cancel &Waiting to Start"
    return "&Stop Dictation" if host.dictation_active() else "&Start Dictation"


def _add(host: Any, menu: Any, label: str, handler: Callable[[], None]) -> Any:
    item_id = wx.NewIdRef()
    menu.Append(item_id, label)
    host.frame.Bind(wx.EVT_MENU, lambda _e: handler(), id=item_id)
    host._keep_menu_ids(item_id)
    return item_id


def _check(host: Any, menu: Any, label: str, checked: bool, handler: Callable[[bool], None]) -> Any:
    item_id = wx.NewIdRef()
    menu.AppendCheckItem(item_id, label)
    menu.Check(item_id, checked)
    host.frame.Bind(wx.EVT_MENU, lambda e: handler(e.IsChecked()), id=item_id)
    host._keep_menu_ids(item_id)
    return item_id


def build_menu_bar(host: Any, *, title: str, version: str) -> None:
    """File, Dictation, Model, Options, QuillVille, Help."""
    bar = wx.MenuBar()

    file_menu = wx.Menu()
    _add(host, file_menu, "Transcribe a &Recording...\tCtrl+O", host.transcribe_a_recording)
    _add(host, file_menu, "&Notifications...\tCtrl+Shift+N", host.open_dictation_notifications)
    file_menu.AppendSeparator()
    _add(host, file_menu, "Minimize to &Tray\tCtrl+W", host.toggle_window_to_tray)
    host._append_key_items(file_menu)  # Show and Hide Key..., Start and Stop Key...
    file_menu.AppendSeparator()
    _add(host, file_menu, "E&xit\tCtrl+Q", host._exit_application)
    bar.Append(file_menu, "&File")

    dictation = wx.Menu()
    host._start_item_id = _add(
        host, dictation, f"{start_stop_label(host)}\tCtrl+D", host.start_or_stop_from_here
    )
    host._resume_item_id = _add(host, dictation, "&Resume\tCtrl+R", host.resume_dictation)
    host._here_item_id = _add(
        host, dictation, "Resume in &This Field\tCtrl+Shift+R", host.resume_in_this_field
    )
    host._discard_item_id = _add(
        host, dictation, "&Discard Held Words\tCtrl+Shift+D", host.discard_held_words
    )
    dictation.AppendSeparator()
    _add(
        host,
        dictation,
        "Use the &Built-in Model This Time\tCtrl+B",
        host.use_built_in_model_once,
    )
    _add(host, dictation, "Dictation &Commands...\tCtrl+Shift+C", host.show_dictation_commands)
    bar.Append(dictation, "&Dictation")

    model = wx.Menu()
    _add(host, model, "Choose &Model...\tCtrl+M", host.choose_model)
    _add(host, model, "Choose Micro&phone...\tCtrl+Shift+M", host.choose_microphone)
    _add(host, model, "Model &Library...\tCtrl+L", host.open_model_library)
    _add(host, model, "Dictation &Settings...\tCtrl+,", host.edit_dictation_settings)
    bar.Append(model, "&Model")

    options = wx.Menu()
    host._startup_item_id = _check(
        host,
        options,
        f"Start {title} with &Windows\tCtrl+Alt+W",
        host.launch_at_startup_enabled(),
        host.set_launch_at_startup,
    )
    _check(
        host,
        options,
        "Start &minimized to the tray\tCtrl+Alt+M",
        host._settings.start_in_tray,
        lambda on: host.set_option("start_in_tray", on),
    )
    _check(
        host,
        options,
        f"&Close button keeps {title} running\tCtrl+Alt+C",
        host._settings.close_to_tray,
        lambda on: host.set_option("close_to_tray", on),
    )
    bar.Append(options, "&Options")

    from quill.ui.quillville_menu import build_quillville_menu

    bar.Append(
        build_quillville_menu(
            wx, host.frame, host._launch_sibling, exclude="transcribe", retain=host._keep_menu_ids
        ),
        "&QuillVille",
    )

    help_menu = wx.Menu()
    _add(host, help_menu, "User &Guide\tCtrl+F1", host.open_user_guide)
    setup = title.replace("Transcribe", "T&ranscribe")
    _add(host, help_menu, f"Set Up {setup}...\tCtrl+Alt+S", host.open_setup)
    _add(host, help_menu, "Check for &Updates...\tCtrl+Alt+U", host.check_for_updates)
    from quill.ui.menu_palette import append_palette_row
    from quill.ui.support_menu import append_get_help_item

    append_palette_row(host, help_menu)
    append_get_help_item(host, help_menu, wx, source_app=title, app_version=version)
    _add(host, help_menu, f"&About {title}\tCtrl+Alt+I", host._show_about)
    bar.Append(help_menu, "&Help")

    host._windows.install(host.frame, bar)
    host.frame.SetMenuBar(bar)


def build_tray_menu(host: Any, menu: Any) -> None:
    """The tray's own rows, between the shared Show and Exit."""
    from quill.core.transcribe.models import model_name

    def add(label: str, handler: Callable[[], None], *, enabled: bool = True) -> None:
        item_id = wx.NewIdRef()
        menu.Append(item_id, label)
        menu.Enable(item_id, enabled)
        menu.Bind(wx.EVT_MENU, lambda _e: wx.CallAfter(handler), id=item_id)
        host._keep_menu_ids(item_id)

    def readout(text: str) -> None:
        item_id = wx.NewIdRef()
        menu.Append(item_id, text)
        menu.Enable(item_id, False)
        host._keep_menu_ids(item_id)

    readout(f"State: {host.dictation_state_word()}")
    readout(f"Model: {model_name(host.engine_in_use())}")
    menu.AppendSeparator()
    if host.dictation_armed():
        label = "Cancel Wai&ting to Start"
    else:
        label = "Stop Dic&tation" if host.dictation_active() else "Start Dic&tation"
    add(label, host.start_or_stop_from_here)
    paused = host.dictation_paused()
    add("&Resume", host.resume_dictation, enabled=paused)
    add("Resume in This &Field", host.resume_in_this_field, enabled=paused)
    add("&Discard Held Words", host.discard_held_words, enabled=paused)
    menu.AppendSeparator()
    add("Choose &Model...", host.choose_model)
    add("Choose Micro&phone...", host.choose_microphone)
    add("Dictation Settin&gs...", host.edit_dictation_settings)
    add("Model &Library...", host.open_model_library)
    add("Transcribe a Re&cording...", host.transcribe_a_recording)
    menu.AppendSeparator()
    add("&User Guide", host.open_user_guide)
    add("Chec&k for Updates...", host.check_for_updates)
