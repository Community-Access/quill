"""Scribe for Documents Options (PRD 7.7), one page for the whole family.

The values live in the shared QUILL data folder (:mod:`quill.core.scribe.
options`), so QUILL and QUILL Lite show and change the same choices. Account
and pages are read-only fields that Tab reaches; the links to Scribe's terms,
privacy policy and manual are buttons, as elsewhere in the family. Tokens
never go in options.

**Progress and results** (:mod:`quill.ui.scribe_feedback_settings`) replaced
"Speak each stage" on 2026-11-23: a sound, words, both or neither for a
conversion starting, each stage, finishing, and failing or needing you.

There is no batch setting: Pneuma approved the exception on 2026-11-21, so
several files chosen together always go one after another (7.4). The About
text carries the privacy notes of 10.1.2.
"""

from __future__ import annotations

import webbrowser
from typing import Any

import wx

from quill.core.scribe import LINKS, PRODUCT_NAME
from quill.core.scribe.consent import ABOUT_TEXT
from quill.core.scribe.library import default_download_root
from quill.core.scribe.model import FORMATS
from quill.core.scribe.options import OPEN_CHOICES, ScribeOptions
from quill.ui.accessible_group import GroupedRadioBox, describe_group
from quill.ui.dialog_contract import apply_modal_ids, bind_close_button
from quill.ui.scribe_feedback_settings import FeedbackSection


class ScribeOptionsDialog(wx.Dialog):
    def __init__(self, parent: Any, controller: Any) -> None:
        super().__init__(
            parent,
            title="Scribe for Documents Options",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.SetName("scribe_options_dialog")  # F1 finds its topic by this name (topics.json)
        self._controller = controller
        self._options = controller.options()
        app = controller.app_name
        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(wx.StaticText(self, label="Account:"), 0, wx.LEFT | wx.TOP, 6)
        self.account = wx.TextCtrl(self, style=wx.TE_READONLY, value="Checking...")
        self.account.SetName("Account")
        self.account.SetHelpText("Who is signed in to Scribe for Documents, and pages left.")
        sizer.Add(self.account, 0, wx.EXPAND | wx.ALL, 6)
        row = wx.BoxSizer(wx.HORIZONTAL)
        self.sign = wx.Button(self, label="Sign &In...")
        self.sign.SetHelpText(
            "Signs in to Scribe for Documents in your browser, or signs out, which forgets "
            f"the sign-in for every {app} app on this computer."
        )
        row.Add(self.sign, 0, wx.ALL, 6)
        self.account_button = wx.Button(self, label="Open My Scribe &Account in Browser")
        self.account_button.SetHelpText(
            "Opens your Scribe account, already signed in: settings, retention, purchases "
            "and account deletion."
        )
        row.Add(self.account_button, 0, wx.ALL, 6)
        sizer.Add(row)

        box = wx.StaticBoxSizer(wx.VERTICAL, self, "Default formats")
        self.formats: dict[str, Any] = {}
        for item in FORMATS:
            check = wx.CheckBox(box.GetStaticBox(), label=item.label)
            check.SetValue(item.id in self._options.default_formats)
            check.SetHelpText("Checked in the convert dialog unless you chose otherwise last time.")
            describe_group(box, check)
            box.Add(check, 0, wx.ALL, 2)
            self.formats[item.id] = check
        sizer.Add(box, 0, wx.EXPAND | wx.ALL, 6)

        sizer.Add(wx.StaticText(self, label="&Download folder:"), 0, wx.LEFT, 6)
        row = wx.BoxSizer(wx.HORIZONTAL)
        self.folder = wx.TextCtrl(
            self, value=self._options.download_folder or str(default_download_root())
        )
        self.folder.SetHelpText(
            "Where results are saved, in a folder per document. An existing file is never "
            "overwritten."
        )
        row.Add(self.folder, 1, wx.ALL, 6)
        browse = wx.Button(self, label="B&rowse...")
        browse.SetHelpText("Chooses the download folder.")
        row.Add(browse, 0, wx.ALL, 6)
        sizer.Add(row, 0, wx.EXPAND)

        self.open_results = GroupedRadioBox(
            self,
            label="Open each result &when it is ready",
            choices=[label for _key, label in OPEN_CHOICES],
            majorDimension=1,
        )
        open_keys = [key for key, _label in OPEN_CHOICES]
        current = self._options.open_results
        self.open_results.SetSelection(open_keys.index(current) if current in open_keys else 0)
        self.open_results.SetHelpText(
            "Open it: the result opens in the app that asked, if it is in front. Ask me "
            "first: Open Result is offered, never as a dialog. Don't open: it is only saved."
        )
        sizer.Add(self.open_results, 0, wx.EXPAND | wx.ALL, 6)

        self.offer_pdf = wx.CheckBox(self, label="O&ffer Scribe when a PDF has little or no text")
        self.offer_pdf.SetValue(self._options.offer_low_text_pdf)
        self.offer_pdf.SetHelpText("When a PDF looks scanned, the OCR question also offers Scribe.")
        sizer.Add(self.offer_pdf, 0, wx.ALL, 6)

        self.feedback = FeedbackSection(
            self, self._options.feedback, say=controller.host.scribe_announce
        )
        sizer.Add(self.feedback.sizer, 0, wx.EXPAND | wx.ALL, 6)

        box = wx.StaticBoxSizer(wx.VERTICAL, self, f"Powered by {PRODUCT_NAME}")
        parent_box = box.GetStaticBox()
        box.Add(wx.StaticText(parent_box, label="Abou&t:"), 0, wx.LEFT, 4)
        about = wx.TextCtrl(
            parent_box, style=wx.TE_MULTILINE | wx.TE_READONLY, value=ABOUT_TEXT.format(app=app)
        )
        about.SetMinSize(self.FromDIP(wx.Size(-1, 110)))
        about.SetHelpText("What Scribe for Documents is, and the privacy notes.")
        box.Add(about, 0, wx.EXPAND | wx.ALL, 4)
        links = wx.BoxSizer(wx.HORIZONTAL)
        for label, key in (
            ("Open Scribe Ter&ms in Browser", "terms"),
            ("Open Scribe Pri&vacy Policy in Browser", "privacy"),
            ("Open Scribe Ma&nual in Browser", "manual"),
        ):
            button = wx.Button(parent_box, label=label)
            button.SetHelpText(f"Opens {LINKS[key]} in your browser.")
            button.Bind(wx.EVT_BUTTON, lambda _e, k=key: webbrowser.open(LINKS[k]))
            links.Add(button, 0, wx.ALL, 4)
        box.Add(links)
        sizer.Add(box, 0, wx.EXPAND | wx.ALL, 6)

        buttons = wx.StdDialogButtonSizer()
        ok = wx.Button(self, wx.ID_OK, label="OK")
        ok.SetHelpText("Saves these options for every QUILL app.")
        ok.SetDefault()
        cancel = wx.Button(self, wx.ID_CANCEL, label="Cancel")
        cancel.SetHelpText("Closes without saving.")
        buttons.AddButton(ok)
        buttons.AddButton(cancel)
        buttons.Realize()
        sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 6)
        self.SetSizerAndFit(sizer)
        apply_modal_ids(self, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)

        bind_close_button(self, cancel, modeless=False)
        browse.Bind(wx.EVT_BUTTON, self._browse)
        self.sign.Bind(wx.EVT_BUTTON, self._sign)
        self.account_button.Bind(wx.EVT_BUTTON, lambda _e: controller.open_account_in_browser())
        self._refresh_account()
        self.account.SetFocus()

    def _refresh_account(self) -> None:
        controller = self._controller
        reason = controller.unavailable()
        if reason:
            self.account.SetValue(reason)
            self.sign.SetLabel("Sign &In...")
            return
        if not controller.session.is_signed_in():
            self.account.SetValue(f"Not signed in to {PRODUCT_NAME}.")
            self.sign.SetLabel("Sign &In...")
            return
        self.sign.SetLabel("Sign &Out")
        self.account.SetValue("Signed in. Checking pages...")

        def work() -> str:
            account = controller.client().account()
            return f"Signed in as {account.name}. {account.pages_phrase()}"

        controller._background(
            work,
            self._set_account,
            lambda _error: self._set_account("Signed in. Pages left could not be checked."),
        )

    def _set_account(self, text: str) -> None:
        try:
            if self and not self.IsBeingDeleted():
                self.account.SetValue(text)
        except RuntimeError:
            pass

    def _sign(self, _event: Any) -> None:
        if self._controller.session.is_signed_in() and not self._controller.unavailable():
            self._controller.sign_out(done=self._refresh_account)
        else:
            self._controller.sign_in()
            self._refresh_account()
        self.sign.SetFocus()

    def _browse(self, _event: Any) -> None:
        dialog = wx.DirDialog(self, "Download folder", self.folder.GetValue())
        try:
            from quill.ui.dialog_contract import show_modal_dialog

            if show_modal_dialog(dialog, "Download folder") == wx.ID_OK:
                self.folder.SetValue(dialog.GetPath())
        finally:
            dialog.Destroy()

    def result(self) -> ScribeOptions:
        options = self._options
        chosen = [key for key, check in self.formats.items() if check.GetValue()]
        options.default_formats = chosen or ["docx"]
        folder = self.folder.GetValue().strip()
        options.download_folder = "" if folder == str(default_download_root()) else folder
        options.open_results = OPEN_CHOICES[max(0, self.open_results.GetSelection())][0]
        options.offer_low_text_pdf = self.offer_pdf.GetValue()
        options.feedback = self.feedback.choices(options.feedback)
        return options


__all__ = ["ScribeOptionsDialog"]
