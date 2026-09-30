"""Ask About an Image: choose a picture, ask about it, hear the answer.

The one AI help command whose input is a file rather than a passage. It is
modal, unlike the rest of the family, for the same reason the agreement is:
nothing is happening yet. The picture and the question are gathered here and
the request itself runs in the background once this window has closed, with
the answer arriving in the ordinary result window (Insert Below, Copy).

The picture is checked twice. Here, only that the path names a file with an
image extension -- so a typo is caught before OK. On the worker, for real
(:func:`quill.core.ai.chatgpt_client.image_part`), so a file that is not what
its name says is a sentence rather than a failed request.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import wx

from quill.core.ai.chatgpt_client import IMAGE_SUFFIXES
from quill.ui.accessible_names import set_accessible_name
from quill.ui.dialog_contract import apply_modal_ids

__all__ = ["TITLE", "AskImageDialog", "image_wildcard"]

TITLE = "Ask About an Image"
_PAD = 8


def image_wildcard() -> str:
    patterns = ";".join(f"*{suffix}" for suffix in IMAGE_SUFFIXES)
    return f"Images ({patterns})|{patterns}|All files (*.*)|*.*"


class AskImageDialog(wx.Dialog):
    """A picture and, if you like, a question about it."""

    def __init__(
        self,
        parent: Any,
        *,
        announce: Callable[[str], None] | None = None,
        initial_path: str = "",
        choose_file: Callable[[], str] | None = None,
    ) -> None:
        super().__init__(parent, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._announce = announce or (lambda _message: None)
        self._choose_file = choose_file or self._browse
        root = wx.BoxSizer(wx.VERTICAL)

        about = wx.StaticText(self, label="&What this does:")
        about_text = wx.TextCtrl(
            self,
            value=(
                "The picture is sent to OpenAI on your ChatGPT subscription, with your "
                "question if you type one, and the description comes back in a window "
                "you can read, copy, or insert into your document. Nothing else is sent."
            ),
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
            size=(-1, 70),
        )
        set_accessible_name(about_text, "What this does")
        about_text.SetHelpText("Where the picture goes and what comes back. Read with the arrows.")
        root.Add(about, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(about_text, 0, wx.EXPAND | wx.ALL, _PAD)

        path_label = wx.StaticText(self, label="&Image file:")
        row = wx.BoxSizer(wx.HORIZONTAL)
        self.path = wx.TextCtrl(self, value=initial_path)
        set_accessible_name(self.path, "Image file")
        self.path.SetHelpText(
            "The full path of a JPEG, PNG, WebP or GIF file. Type it, paste it, or "
            "choose Browse to pick it."
        )
        browse = wx.Button(self, label="&Browse...")
        browse.SetHelpText("Opens the file picker on your Pictures folder.")
        browse.Bind(wx.EVT_BUTTON, lambda _e: self._on_browse())
        row.Add(self.path, 1, wx.RIGHT, _PAD)
        row.Add(browse, 0)
        root.Add(path_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(row, 0, wx.EXPAND | wx.ALL, _PAD)

        question_label = wx.StaticText(self, label="Your &question (optional):")
        self.question = wx.TextCtrl(self, style=wx.TE_MULTILINE, size=(-1, 70))
        set_accessible_name(self.question, "Your question")
        self.question.SetHelpText(
            "What you want to know about the picture. Leave it empty for a plain "
            "description written for a blind reader."
        )
        root.Add(question_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.question, 0, wx.EXPAND | wx.ALL, _PAD)

        self.status = wx.StaticText(self, label="")
        root.Add(self.status, 0, wx.LEFT | wx.RIGHT, _PAD)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer(1)
        ask = wx.Button(self, wx.ID_OK, "Ask")
        ask.SetHelpText("Sends the picture and your question. The answer opens in its own window.")
        ask.SetDefault()
        cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")
        cancel.SetHelpText("Closes this window. Nothing is sent.")
        buttons.Add(ask, 0, wx.RIGHT, _PAD)
        buttons.Add(cancel, 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, _PAD)

        self.SetSizer(root)
        self.SetInitialSize((560, 360))
        self.Centre()
        apply_modal_ids(self, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)
        (self.question if initial_path else self.path).SetFocus()

    # -- choosing ---------------------------------------------------------- #

    def _browse(self) -> str:
        start = str(Path.home() / "Pictures") if (Path.home() / "Pictures").is_dir() else ""
        with wx.FileDialog(
            self,
            "Choose an image",
            defaultDir=start,
            wildcard=image_wildcard(),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return ""
            return str(dialog.GetPath())

    def _on_browse(self) -> None:
        chosen = self._choose_file()
        if chosen:
            self.path.SetValue(chosen)
            self.question.SetFocus()

    # -- leaving ------------------------------------------------------------ #

    def problem(self) -> str:
        """Why OK cannot proceed, or "" when it can."""
        raw = self.path.GetValue().strip().strip('"')
        if not raw:
            return "Choose an image file first."
        path = Path(raw)
        if not path.is_file():
            return f"There is no file at {raw}."
        if path.suffix.lower() not in IMAGE_SUFFIXES:
            return "Choose a JPEG, PNG, WebP or GIF file."
        return ""

    def _on_ok(self, event: wx.CommandEvent) -> None:
        said = self.problem()
        if said:
            # The message goes where focus is going, and the field is what
            # needs typing into, so both happen: label, then focus.
            self.status.SetLabel(said)
            self.path.SetFocus()
            self._announce(said)
            return
        event.Skip()

    def chosen(self) -> tuple[Path, str]:
        """The picture and the question, once OK was allowed through."""
        return Path(self.path.GetValue().strip().strip('"')), self.question.GetValue().strip()
