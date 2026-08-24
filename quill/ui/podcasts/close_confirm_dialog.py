"""Closing QUILL Cast: Exit or Minimize to Tray, with a persisted default.

Cast had one answer to closing -- exit -- and one narrow escape from it, the
Alt+F4-to-tray checkbox. So the titlebar X ended playback with no way to say
otherwise, on a window whose whole job is to keep playing while you do
something else (list.md 5.4). Quill Radio has carried three answers for as
long as it has had a tray icon, and it is the same window model and the same
audience; one of them lost an hour of listening to a reflex.

**Why this is Cast's own dialog and not Radio's.** The structure is identical
and deliberately so, but the *words* are what the dialog is for, and none of
them survive the move: Radio's warns about a recording in progress, offers to
keep recording in the tray, and is titled after a different app. A shared
dialog with the nouns swapped out by parameter would read as neither app's,
and the sentence a listener hears at the moment they close the window is not
the place to save ninety lines.

**Exit is the default button**, as in Radio and for the same reason: the
titlebar X and Alt+F4 are the "close this window" gesture, so the answer Enter
gives must be the one the gesture asked for. Minimize is the interesting
alternative, not the expected reply.

Never shown from inside ``EVT_CLOSE`` -- ``AppShellFrame.handle_app_close``
vetoes and re-runs this deferred, because ShowModal from a close handler on
wxMSW can return without ever displaying (the "Alt+F4 does nothing while
playing" bug).
"""

from __future__ import annotations

from collections.abc import Callable

from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog

__all__ = ["CastCloseConfirmDialog", "stakes_line"]

TITLE = "Closing QUILL Cast"


def stakes_line(*, playing: bool, downloads: int) -> str:
    """What closing costs *right now*, or "" when it costs nothing.

    Named and pure so the sentence can be tested without a window. Both
    halves matter and they are different kinds of loss: playback stops and can
    be resumed, a download in flight is thrown away and has to start again.
    Said plainly rather than as a warning icon, because the point is to let
    somebody choose Minimize on purpose.
    """
    parts: list[str] = []
    if playing:
        parts.append("An episode is playing")
    if downloads == 1:
        parts.append("a download is in progress")
    elif downloads > 1:
        parts.append(f"{downloads} downloads are in progress")
    if not parts:
        return ""
    said = parts[0] if len(parts) == 1 else f"{parts[0]} and {parts[1]}"
    return f"{said} -- exiting now stops it."


class CastCloseConfirmDialog:
    """Returns ``(action, dont_ask_again)`` where *action* is ``"exit"`` or
    ``"minimize"``, or ``None`` when the listener cancelled (the window stays
    open and nothing happens)."""

    def __init__(
        self,
        parent: object,
        *,
        playing: bool = False,
        downloads: int = 0,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _m: None)
        self._result: tuple[str, bool] | None = None
        self._minimize_id = int(wx.NewIdRef())
        self._exit_id = int(wx.NewIdRef())

        self.dialog = wx.Dialog(parent, title=TITLE)
        root = wx.BoxSizer(wx.VERTICAL)

        stakes = stakes_line(playing=playing, downloads=downloads)
        message = (f"{stakes}\n\n" if stakes else "") + (
            "Exit QUILL Cast, or minimize it to the system tray and keep it running?"
        )
        intro = wx.StaticText(self.dialog, label=message)
        intro.Wrap(360)
        root.Add(intro, 0, wx.EXPAND | wx.ALL, 10)

        self._dont_ask_check = wx.CheckBox(self.dialog, label="&Don't ask me again")
        self._dont_ask_check.SetName(
            "Don't ask me again -- remembers this choice; change it later in Preferences"
        )
        self._dont_ask_check.SetHelpText(
            "Stops this question appearing and always does what you choose here. "
            "Preferences can set it back to Ask every time."
        )
        root.Add(self._dont_ask_check, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer()
        exit_btn = wx.Button(self.dialog, self._exit_id, "E&xit")
        exit_btn.SetHelpText(
            "Quits QUILL Cast. Your position in the episode is saved, so it "
            "resumes where you left it."
        )
        minimize_btn = wx.Button(self.dialog, self._minimize_id, "&Minimize to Tray")
        minimize_btn.SetHelpText(
            "Keeps playing and downloading with the window tucked into the "
            "system tray; the tray icon brings it back."
        )
        cancel_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        cancel_btn.SetHelpText("Returns to QUILL Cast with everything as it was.")
        buttons.Add(exit_btn, 0, wx.RIGHT, 6)
        buttons.Add(minimize_btn, 0, wx.RIGHT, 6)
        buttons.Add(cancel_btn)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
        self.dialog.SetSizerAndFit(root)

        minimize_btn.Bind(wx.EVT_BUTTON, lambda _e: self._choose("minimize"))
        exit_btn.Bind(wx.EVT_BUTTON, lambda _e: self._choose("exit"))

    def _choose(self, action: str) -> None:
        self._result = (action, self._dont_ask_check.GetValue())
        self.dialog.EndModal(self._minimize_id if action == "minimize" else self._exit_id)

    def show(self) -> tuple[str, bool] | None:
        wx = self._wx
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._exit_id,
            affirmative_label="Exit",
            cancel_id=wx.ID_CANCEL,
            escape_id=wx.ID_CANCEL,
        )
        try:
            answer = show_modal_dialog(self.dialog, TITLE, announce=self._announce)
            return self._result if answer in (self._minimize_id, self._exit_id) else None
        finally:
            self.dialog.Destroy()

    def close(self) -> None:
        self.dialog.EndModal(self._wx.ID_CANCEL)
