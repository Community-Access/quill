"""Podcast Index credentials: where a key and a secret go, and where they do not.

Podcast Index is the second directory Add Podcast can search, and it is the one
that knows the Podcasting 2.0 tags. It needs a key and a secret, which anybody
can register for free at podcastindex.org -- and which most people never will,
which is exactly why iTunes stays the default and why this window is somewhere
you go rather than something you meet.

**The secrets never touch a settings file.** They go into the platform
credential store (DPAPI on Windows), like every other secret QUILL holds, and
``podcasts.json`` records nothing about them at all -- not even that they exist.

**The secret field is masked, and there is a way to hear it.** Masking is right
for a shoulder-surfing risk and wrong for a screen reader: a field that reads as
"dot dot dot dot" cannot be proof-read. So the box is masked by default and
"Read It Back" says the value once, a character group at a time, which is what
somebody typing a long random string from another window actually needs.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.ui.dialog_contract import apply_modal_ids

__all__ = ["DirectoryCredentialsDialog", "open_directory_credentials"]

TITLE = "Podcast Index Credentials"

_INTRO = (
    "Podcast Index is a second podcast directory. It is free, and it carries "
    "the extra information some podcasts publish -- chapters, transcripts, and "
    "the moments a show marked as worth hearing. It needs a key and a secret, "
    "which you can get for nothing at podcastindex.org. Leave these empty and "
    "QUILL Cast simply searches iTunes, as it always has."
)


class DirectoryCredentialsDialog:
    """Returns ``(key, secret)`` on OK, or ``None`` on Cancel."""

    def __init__(
        self,
        parent: object,
        *,
        key: str = "",
        secret: str = "",
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _m: None)
        self._result: tuple[str, str] | None = None

        self.dialog = wx.Dialog(parent, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE)
        root = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(self.dialog, label=_INTRO)
        intro.Wrap(520)
        root.Add(intro, 0, wx.ALL | wx.EXPAND, 10)

        grid = wx.FlexGridSizer(cols=2, gap=(6, 8))
        grid.AddGrowableCol(1, 1)
        grid.Add(wx.StaticText(self.dialog, label="&Key:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._key = wx.TextCtrl(self.dialog, value=key)
        self._key.SetName("Your Podcast Index API key")
        grid.Add(self._key, 1, wx.EXPAND)
        grid.Add(wx.StaticText(self.dialog, label="S&ecret:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._secret = wx.TextCtrl(self.dialog, value=secret, style=wx.TE_PASSWORD)
        self._secret.SetName("Your Podcast Index API secret. Press Read It Back to hear it.")
        grid.Add(self._secret, 1, wx.EXPAND)
        root.Add(grid, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        speak_btn = wx.Button(self.dialog, label="&Read It Back")
        speak_btn.SetName("Say the secret out loud once, so you can check what you typed")
        clear_btn = wx.Button(self.dialog, label="&Forget These")
        buttons.Add(speak_btn, 0, wx.RIGHT, 6)
        buttons.Add(clear_btn, 0)
        buttons.AddStretchSpacer()
        buttons.Add(wx.Button(self.dialog, wx.ID_OK, "&Save"), 0, wx.RIGHT, 6)
        buttons.Add(wx.Button(self.dialog, wx.ID_CANCEL, "Cancel"), 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)
        self.dialog.Fit()

        speak_btn.Bind(wx.EVT_BUTTON, lambda _e: self._read_back())
        clear_btn.Bind(wx.EVT_BUTTON, lambda _e: self._forget())
        self.dialog.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)

    def _read_back(self) -> None:
        value = self._secret.GetValue().strip()
        if not value:
            self._announce("There is no secret to read.")
            return
        # In groups of four, with spaces: a screen reader reading thirty-two
        # characters as one run is unfollowable, and this is exactly what
        # somebody copying from another window needs to check.
        grouped = " ".join(value[index : index + 4] for index in range(0, len(value), 4))
        self._announce(grouped)

    def _forget(self) -> None:
        self._key.SetValue("")
        self._secret.SetValue("")
        self._announce("Cleared. Saving now removes them from this computer.")

    def _on_ok(self, event: Any) -> None:
        self._result = (self._key.GetValue().strip(), self._secret.GetValue().strip())
        event.Skip()

    def show(self) -> tuple[str, str] | None:
        from quill.ui.dialog_contract import show_modal_dialog

        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._wx.ID_OK,
            affirmative_label="Save",
            cancel_id=self._wx.ID_CANCEL,
            escape_id=self._wx.ID_CANCEL,
        )
        try:
            answer = show_modal_dialog(self.dialog, TITLE, announce=self._announce)
            return self._result if answer == self._wx.ID_OK else None
        finally:
            self.dialog.Destroy()


def open_directory_credentials(host: Any) -> None:
    """The command: edit the credentials, and store them where secrets go."""
    from quill.core.podcasts.podcast_index import CREDENTIAL_KEY, CREDENTIAL_KEY_SECRET
    from quill.ui.podcasts.preview_command import podcast_index_credentials

    announce = getattr(host, "_announce", None) or (lambda _m: None)
    key, secret = podcast_index_credentials()
    edited = DirectoryCredentialsDialog(
        getattr(host, "frame", None) or host,
        key=key,
        secret=secret,
        announce_cb=announce,
    ).show()
    if edited is None:
        return
    new_key, new_secret = edited
    try:
        from quill.platform.windows.credential_manager import (
            delete_generic_credential,
            save_generic_credential,
        )
    except ImportError:
        announce("This computer has no secure place to keep those credentials.")
        return
    try:
        for name, value in (
            (CREDENTIAL_KEY, new_key),
            (CREDENTIAL_KEY_SECRET, new_secret),
        ):
            if value:
                save_generic_credential(name, value)
            else:
                delete_generic_credential(name)
    except OSError as error:  # pragma: no cover - platform dependent
        announce(f"Those credentials could not be saved: {error}")
        return
    announce(
        "Podcast Index credentials saved."
        if new_key and new_secret
        else "Podcast Index credentials removed. Searches use iTunes."
    )
