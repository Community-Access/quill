"""Speech output player popup for the chat companion (voice conversation mode).

When the agent answers in voice mode, its reply is spoken aloud and this popup
gives accessible transport controls: Pause/Resume, Stop, Play (replay from the
start), and Save as media (export the spoken reply to an MP3). Escape dismisses
the dialog (stopping playback). Shown through ``MainFrame._show_modal_dialog``
(GATE-16), so the keyboard/focus/announcement contract applies.

Playback runs on a worker thread; Pause/Stop are coarse (they take effect at the
next audio chunk boundary), driven by the ``pause_event`` / ``stop_event`` the
:class:`~quill.ui.voice_services.VoiceServices` honors.
"""

from __future__ import annotations

import threading
from typing import Any

__all__ = ["show_speech_player"]


def show_speech_player(controller: Any, voice: Any, text: str, *, title: str = "Speaking") -> None:
    """Open the speech player for *text* and block until the user dismisses it."""
    import wx

    stop_event = threading.Event()
    pause_event = threading.Event()
    state: dict[str, Any] = {"thread": None}

    dialog = wx.Dialog(controller.frame, title=title, style=wx.DEFAULT_DIALOG_STYLE)
    outer = wx.BoxSizer(wx.VERTICAL)

    preview = " ".join(text.split())
    if len(preview) > 200:
        preview = preview[:197] + "..."
    label = wx.StaticText(dialog, label=f"Speaking the reply.\n\n{preview}")
    label.SetName("Now speaking")
    label.Wrap(420)
    outer.Add(label, 0, wx.ALL, 12)

    buttons = wx.BoxSizer(wx.HORIZONTAL)
    pause_btn = wx.Button(dialog, label="&Pause")
    stop_btn = wx.Button(dialog, label="&Stop")
    play_btn = wx.Button(dialog, label="P&lay")
    save_btn = wx.Button(dialog, label="Save as &media")
    for btn in (pause_btn, stop_btn, play_btn, save_btn):
        buttons.Add(btn, 0, wx.RIGHT, 8)
    outer.Add(buttons, 0, wx.ALL, 12)
    close_row = wx.BoxSizer(wx.HORIZONTAL)
    close_row.AddStretchSpacer()
    close_row.Add(wx.Button(dialog, wx.ID_CANCEL, label="Close"), 0)
    outer.Add(close_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
    dialog.SetSizer(outer)
    dialog.Fit()

    def announce(message: str) -> None:
        try:
            controller._set_status(message)
        except Exception:  # noqa: BLE001
            pass

    def start_playback() -> None:
        thread = state.get("thread")
        if thread is not None and thread.is_alive():
            return
        stop_event.clear()
        pause_event.clear()
        pause_btn.SetLabel("&Pause")

        def worker() -> None:
            try:
                voice.play(text, stop_event=stop_event, pause_event=pause_event)
            except Exception:  # noqa: BLE001 - playback errors must not crash the UI
                pass

        new_thread = threading.Thread(target=worker, daemon=True)
        state["thread"] = new_thread
        new_thread.start()

    def on_pause(_event: object) -> None:
        if pause_event.is_set():
            pause_event.clear()
            pause_btn.SetLabel("&Pause")
            announce("Resumed")
        else:
            pause_event.set()
            pause_btn.SetLabel("Resume")
            announce("Paused")

    def on_stop(_event: object) -> None:
        stop_event.set()
        pause_event.clear()
        announce("Stopped")

    def on_play(_event: object) -> None:
        start_playback()
        announce("Playing")

    def on_save(_event: object) -> None:
        with wx.FileDialog(
            dialog,
            "Save spoken reply as media",
            wildcard="MP3 audio (*.mp3)|*.mp3",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as file_dialog:
            if file_dialog.ShowModal() != wx.ID_OK:
                return
            path = file_dialog.GetPath()

        def worker() -> None:
            try:
                voice.save(text, path)
                wx.CallAfter(announce, "Saved the spoken reply.")
            except Exception as exc:  # noqa: BLE001
                wx.CallAfter(announce, f"Could not save: {exc}")

        threading.Thread(target=worker, daemon=True).start()
        announce("Saving...")

    pause_btn.Bind(wx.EVT_BUTTON, on_pause)
    stop_btn.Bind(wx.EVT_BUTTON, on_stop)
    play_btn.Bind(wx.EVT_BUTTON, on_play)
    save_btn.Bind(wx.EVT_BUTTON, on_save)

    from quill.ui.dialog_contract import apply_modal_ids

    apply_modal_ids(dialog, affirmative_id=wx.ID_CANCEL, escape_id=wx.ID_CANCEL)

    start_playback()
    try:
        controller._show_modal_dialog(dialog, title)
    finally:
        stop_event.set()
        pause_event.clear()
        dialog.Destroy()
