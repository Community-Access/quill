"""Persistent native screenshot conversation with editable prompts and async replies."""

from __future__ import annotations

import hashlib
import io
from pathlib import Path

import wx
from wx.lib.scrolledpanel import ScrolledPanel

from quill.core.settings import load_settings
from quill.core.studio_capture import save_capture_description, save_capture_report, verify_capture
from quill.core.studio_capture_ai import (
    capture_prompt,
    connection_identity,
    load_capture_ai_preferences,
    prompt_choices,
    save_capture_ai_preferences,
)
from quill.stability.task_manager import UiLifetimeToken
from quill.ui.dialog_contract import apply_modal_ids, bind_close_button, set_accessible_name


class ScreenshotChatDialog(wx.Dialog):
    def __init__(self, host, evidence, observations="", question=""):
        super().__init__(
            host.frame,
            title="Screenshot Inspector",
            size=(850, 720),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.host = host
        self.evidence = evidence
        self.observations = observations
        self.lifetime = UiLifetimeToken()
        self.task = None
        self.busy = False
        self.settings = load_settings()
        self.preferences = load_capture_ai_preferences()
        panel = ScrolledPanel(self)
        self._content = panel
        outer = wx.BoxSizer(wx.VERTICAL)
        self._field_label(outer, "&Verification and conversation")
        self.transcript = wx.TextCtrl(
            panel,
            value="Screenshot saved. Read its text locally, ask a question, or edit a copy.\n"
            "File checks passed; review the content before sharing."
            + ("\n\nUNVERIFIED OBSERVATIONS\n" + observations if observations else ""),
            style=wx.TE_MULTILINE | wx.TE_READONLY,
        )
        set_accessible_name(self.transcript, "Verification and conversation")
        self.transcript.SetHelpText(
            "Read the source, hash, proven file checks and conversation. "
            "AI and OCR observations are uncertain. This text can be selected and copied."
        )
        outer.Add(self.transcript, 2, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        details = wx.CollapsiblePane(panel, label="Advanced: file checks and source details")
        details.SetHelpText(
            "Optional dimensions, file hash, source metadata and verification limits."
        )
        details_label = wx.StaticText(details.GetPane(), label="File checks and source details")
        details_text = wx.TextCtrl(
            details.GetPane(),
            value=evidence.summary(),
            style=wx.TE_MULTILINE | wx.TE_READONLY,
            size=(-1, 130),
        )
        set_accessible_name(details_text, "File checks and source details")
        details_text.SetHelpText(
            "Objective file evidence. These checks do not prove privacy or completeness."
        )
        details_layout = wx.BoxSizer(wx.VERTICAL)
        details_layout.Add(details_label, 0, wx.BOTTOM, 4)
        details_layout.Add(details_text, 1, wx.EXPAND)
        details.GetPane().SetSizer(details_layout)
        outer.Add(details, 0, wx.EXPAND | wx.ALL, 8)
        details.Bind(wx.EVT_COLLAPSIBLEPANE_CHANGED, lambda event: self._layout_content())
        self._field_label(outer, "Prompt st&yle")
        self.style = wx.Choice(panel)
        set_accessible_name(self.style, "Prompt style")
        self.style.SetHelpText(
            "Choose a screenshot prompt or a shared image prompt. "
            "It fills the editable instructions; your question is kept separately."
        )
        outer.Add(self.style, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self._field_label(outer, "Editable &prompt instructions")
        self.prompt = wx.TextCtrl(panel, style=wx.TE_MULTILINE, size=(-1, 90))
        set_accessible_name(self.prompt, "Editable prompt instructions")
        self.prompt.SetHelpText(
            "Edit or extend the selected prompt before asking AI. "
            "Use Manage prompts to save reusable custom prompts in the shared library."
        )
        outer.Add(self.prompt, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self._reload_prompts(self.preferences.get("prompt_id", "screen-overview"))
        self.style.Bind(wx.EVT_CHOICE, self._choose_prompt)
        self._field_label(outer, "Your &question or additional instructions")
        self.question = wx.TextCtrl(panel, value=question, style=wx.TE_MULTILINE, size=(-1, 55))
        set_accessible_name(self.question, "Your question or additional instructions")
        self.question.SetHelpText(
            "Ask about this exact screenshot. Follow-ups include the prior "
            "conversation and the same image; they do not capture a new screen."
        )
        outer.Add(self.question, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self.automatic = wx.CheckBox(panel, label="Automatically inspect &future captures with AI")
        self.automatic.SetValue(self.preferences.get("auto_ai_enabled") is True)
        self.automatic.Bind(wx.EVT_CHECKBOX, self._set_automatic)
        self.automatic.SetHelpText(
            "Off by default. Enabling requires explicit approval to send future "
            "user-triggered screenshots to the approved AI connection. "
            "AI Off and Safe Mode override it."
        )
        outer.Add(self.automatic, 0, wx.ALL, 8)
        self.status = wx.StaticText(
            panel, label="Ready. AI requires permission; local OCR stays offline."
        )
        outer.Add(self.status, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        buttons = wx.WrapSizer(wx.HORIZONTAL)
        for label, handler in (
            ("Read &text locally", lambda _e: self.send(local=True)),
            ("&Ask AI", lambda _e: self.send(local=False)),
            ("&Save report", lambda _e: self._save(False)),
            ("&Export description", lambda _e: self._save(True)),
            ("Copy &image", self._copy_image),
            ("&Edit a copy...", self._edit_copy),
            ("Manage p&rompts...", self._manage_prompts),
            ("Use for a&utomatic AI...", self._use_automatic_prompt),
        ):
            button = wx.Button(panel, label=label)
            button.Bind(wx.EVT_BUTTON, handler)
            button.SetHelpText(label.replace("&", "") + " for the screenshot identified above.")
            buttons.Add(button, 0, wx.RIGHT | wx.BOTTOM, 6)
        close = wx.Button(self, wx.ID_CANCEL, "&Close")
        bind_close_button(self, close, modeless=False)
        close.SetHelpText(
            "Close the inspector and cancel unsent chat work. "
            "A request already sent to an AI provider may still finish."
        )
        outer.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        apply_modal_ids(self, cancel_id=wx.ID_CANCEL, cancel_label="&Close")
        panel.SetSizer(outer)
        panel.SetupScrolling(scroll_x=False)
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(panel, 1, wx.EXPAND)
        root.Add(close, 0, wx.ALL, 8)
        self.SetSizer(root)
        area = wx.GetClientDisplayRect()
        self.SetSize((min(850, area.width), min(720, area.height)))
        self.transcript.SetFocus()
        # a11y: needs manual verification — JAWS/NVDA/Narrator, high contrast,
        # scaling, multiline braille review, tab order and focus return.

    def _layout_content(self):
        self._content.Layout()
        self._content.FitInside()
        self.Layout()

    def _field_label(self, sizer, label):
        sizer.Add(wx.StaticText(self._content, label=label), 0, wx.ALL, 8)

    def _edit_copy(self, event):
        from quill.ui.studio_capture_editor import ScreenshotEditorDialog

        dialog = ScreenshotEditorDialog(self.host, self.evidence)
        try:
            self.host._show_modal_dialog(dialog, "Screenshot editing and evidence")
        finally:
            dialog.stop()
            dialog.Destroy()

    def _say(self, text):
        self.status.SetLabel(text)
        self.host._announce(text)

    def _reload_prompts(self, selected):
        self.choices = prompt_choices(self.settings)
        self.style.SetItems([choice["title"] for choice in self.choices])
        index = next((i for i, c in enumerate(self.choices) if c["id"] == selected), 0)
        self.style.SetSelection(index)
        self._choose_prompt()

    def _choose_prompt(self, _event=None):
        self.prompt.ChangeValue(
            capture_prompt(self.choices[self.style.GetSelection()]["id"], self.settings)
        )

    def _manage_prompts(self, _event):
        from quill.ui.vision_prompt_manager_dialog import VisionPromptManagerDialog

        selected = self.choices[self.style.GetSelection()]["id"]
        VisionPromptManagerDialog(self, load_settings()).show_modal()
        self.settings = load_settings()
        self._reload_prompts(selected)
        self._say("Image prompt library refreshed. You can edit these instructions before sending.")

    def _set_automatic(self, _event):
        from quill.core.ai.model_manager import load_ai_enabled
        from quill.core.assistant_ai import load_assistant_connection_settings

        preferences = load_capture_ai_preferences()
        if not self.automatic.GetValue():
            preferences["auto_ai_enabled"] = False
            save_capture_ai_preferences(preferences)
            self._say("Automatic screenshot AI disabled. Already sent requests may finish.")
            return
        connection = load_assistant_connection_settings()
        if self.host._safe_mode or not load_ai_enabled() or connection.provider == "off":
            self.automatic.SetValue(False)
            self._say(
                "Enable AI and connect a provider outside Safe Mode "
                "before enabling automatic analysis."
            )
            return
        identity = connection_identity(connection)
        approved = self.host._show_message_box(
            "Automatically send EVERY future user-triggered Studio screenshot, "
            "including full desktop "
            "captures, to this AI connection until disabled?\n\n"
            f"Provider: {identity['provider']}\nModel: {identity['model']}\n"
            f"Endpoint: {identity['host']}\n\n"
            "Images may contain private information. There is no automatic redaction. "
            "A changed connection pauses automatic analysis. Safe Mode and AI Off block it.",
            "Enable automatic screenshot AI",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
        )
        if approved != wx.YES:
            self.automatic.SetValue(False)
            return
        preferences.update({
            "auto_ai_enabled": True,
            "approved_connection": identity,
            "prompt_id": self.choices[self.style.GetSelection()]["id"],
            "instructions": self.prompt.GetValue().strip(),
        })
        save_capture_ai_preferences(preferences)
        self._say("Automatic screenshot AI enabled for future user-triggered captures.")

    def _use_automatic_prompt(self, _event):
        self.automatic.SetValue(True)
        self._set_automatic(None)

    def send(self, *, local):
        if self.busy:
            self._say(
                "An inspection is running. Your question remains editable; "
                "wait before sending again."
            )
            return
        connection = None
        if not local:
            # The per-image consent dialog remains available even when auto is enabled.
            connection = self.host._approve_capture_ai()
            if connection is None:
                return
        question = self.question.GetValue().strip()
        instructions = self.prompt.GetValue().strip()
        self.busy = True
        self.transcript.AppendText(
            "\n\nYou: " + (question or ("Read text locally" if local else "Inspect screenshot"))
        )
        self._say("Reading text locally..." if local else "Asking AI about this screenshot...")

        def ready(_task, text):
            self.busy = False
            self.observations += ("\n\n" if self.observations else "") + text
            self.host._remember_capture_notes(self.evidence, self.observations)
            selection = self.transcript.GetSelection()
            self.transcript.AppendText("\n\n" + text)
            if self.transcript.HasFocus():
                self.transcript.SetSelection(*selection)
            self._say(
                "Response ready. Review Verification and conversation, or ask a follow-up question."
            )

        def failed(_task, error):
            self.busy = False
            self.transcript.AppendText(f"\n\nInspection failed: {error}")
            self._say(f"Inspection failed: {error}. Your screenshot and conversation are retained.")

        self.task = self.host._submit_capture_inspection(
            self.evidence,
            instructions,
            question,
            self.observations,
            connection,
            ready,
            failed,
            self.lifetime,
        )

    def _save(self, description):
        try:
            method = save_capture_description if description else save_capture_report
            path = (
                method(self.evidence, observations=self.observations)
                if not description
                else method(self.evidence, self.observations)
            )
            self._say(f"Saved: {path}")
        except Exception as error:
            self._say(f"Could not save: {error}")

    def accept_external_observation(self, text):
        self.observations += ("\n\n" if self.observations else "") + text
        self.transcript.AppendText("\n\nAutomatic inspection:\n" + text)
        self.host._remember_capture_notes(self.evidence, self.observations)
        self._say("Automatic analysis arrived for this screenshot. Review the conversation.")

    def _copy_image(self, _event):
        try:
            raw = Path(self.evidence.path).read_bytes()
            if hashlib.sha256(raw).hexdigest() != self.evidence.sha256:
                raise ValueError("Screenshot changed since verification.")
            image = wx.Image(io.BytesIO(raw), wx.BITMAP_TYPE_PNG)
            if not image.IsOk() or not wx.TheClipboard.Open():
                raise RuntimeError("Could not open the image or clipboard. Try again.")
            try:
                if not wx.TheClipboard.SetData(wx.BitmapDataObject(wx.Bitmap(image))):
                    raise RuntimeError("Clipboard rejected the image.")
            finally:
                wx.TheClipboard.Close()
            self._say("Screenshot copied to the clipboard.")
        except Exception as error:
            self._say(f"Could not copy screenshot: {error}")

    def stop_delivery(self):
        self.lifetime.invalidate()
        if self.task is not None:
            self.task.cancellation_token.cancel()


def show_capture_chat(host, evidence, observations="", question=""):
    try:
        verify_capture(Path(evidence.path), evidence.target, expected_sha256=evidence.sha256)
    except Exception as error:
        host._show_message_box(
            str(error), "Screenshot changed or unavailable", wx.OK | wx.ICON_ERROR
        )
        return
    dialog = ScreenshotChatDialog(host, evidence, observations, question)
    if not hasattr(host, "_capture_chat_views"):
        host._capture_chat_views = {}
    host._capture_chat_views[evidence.path] = dialog
    try:
        host._show_modal_dialog(dialog, "Screenshot Inspector")
    finally:
        dialog.stop_delivery()
        host._capture_chat_views.pop(evidence.path, None)
        dialog.Destroy()
