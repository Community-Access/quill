"""Accessible local preview for a user-selected GitHub release range."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from quill.core.github.items_provider import GitHubItemsError
from quill.core.github.release_notes import GitHubReleaseNotesDraft
from quill.ui.dialog_contract import apply_modal_ids, dialog_alive, show_modal_dialog
from quill.ui.dpi import dip_size

if TYPE_CHECKING:
    from quill.core.github.items_provider import GitHubItemsProvider


class GitHubReleaseNotesDialog:
    """Generate, edit, and copy release notes without creating a GitHub release."""

    def __init__(
        self,
        parent: object,
        provider: GitHubItemsProvider,
        repository: str,
        *,
        previous_tag: str = "",
        announce_cb: object | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._provider = provider
        self._repository = repository
        self._announce = announce_cb if callable(announce_cb) else lambda _message: None
        self._draft: GitHubReleaseNotesDraft | None = None
        self.dialog = wx.Dialog(
            parent,
            title="Draft Release Notes",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(dip_size(self.dialog, 680, 580))
        self.dialog.SetSize(dip_size(self.dialog, 840, 740))
        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(
            panel,
            label=(
                "Choose an explicit previous and target tag. GitHub will generate "
                "a Markdown preview for that range. QUILL keeps the preview here; "
                "nothing is saved or published to GitHub."
            ),
        )
        intro.Wrap(780)
        root.Add(intro, 0, wx.EXPAND | wx.ALL, 10)

        self._target = self._text_field(
            panel,
            root,
            "Target release tag:",
            "Target release tag",
            "Required. Enter the tag for the release notes you are preparing.",
        )
        self._previous = self._text_field(
            panel,
            root,
            "Previous tag (start of range):",
            "Previous release tag",
            "Required. This tag defines the start of the generated change range.",
            previous_tag,
        )
        self._target_commitish = self._text_field(
            panel,
            root,
            "Target branch or commit (if the target tag is new):",
            "Release target branch or commit",
            "Optional for an existing tag; required by GitHub when the target tag does not exist.",
        )

        generate_row = wx.BoxSizer(wx.HORIZONTAL)
        self._generate_btn = wx.Button(panel, label="Generate Draft")
        self._generate_btn.SetName("Generate a local release-notes draft for the selected range")
        self._generate_btn.SetHelpText(
            "Ask GitHub to generate Markdown for the entered previous and target tags. "
            "This does not create a release."
        )
        generate_row.Add(self._generate_btn, 0, wx.RIGHT, 8)
        self._status = wx.StaticText(panel, label="")
        self._status.SetName("Release-notes generation status")
        generate_row.Add(self._status, 1, wx.ALIGN_CENTER_VERTICAL)
        root.Add(generate_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        name_label = wx.StaticText(panel, label="Draft name:")
        name_label.SetName("Release draft name label")
        root.Add(name_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self._name = wx.TextCtrl(panel, value="")
        self._name.SetName("Editable release draft name")
        self._name.SetHelpText("Edit the generated release name before copying it.")
        root.Add(self._name, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        body_label = wx.StaticText(panel, label="Draft body (Markdown):")
        body_label.SetName("Release draft body label")
        root.Add(body_label, 0, wx.LEFT | wx.RIGHT, 10)
        self._body = wx.TextCtrl(
            panel,
            value="",
            style=wx.TE_MULTILINE | wx.TE_WORDWRAP,
        )
        self._body.SetName("Editable release draft Markdown")
        self._body.SetHelpText("Review and edit the generated Markdown before copying it.")
        root.Add(self._body, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        buttons = wx.StdDialogButtonSizer()
        self._copy_btn = wx.Button(panel, wx.ID_ANY, label="Copy Draft")
        self._copy_btn.SetName("Copy editable release notes to the clipboard")
        self._copy_btn.SetHelpText(
            "Copy the draft name and Markdown body. This does not publish them."
        )
        close_btn = wx.Button(panel, wx.ID_CANCEL, label="Close")
        close_btn.SetName("Close release notes draft")
        buttons.AddButton(self._copy_btn)
        buttons.AddButton(close_btn)
        buttons.Realize()
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)
        self._generate_btn.Bind(wx.EVT_BUTTON, self._on_generate)
        self._copy_btn.Bind(wx.EVT_BUTTON, self._on_copy)
        self._copy_btn.Enable(False)

    @staticmethod
    def _text_field(
        panel: object,
        root: object,
        label: str,
        name: str,
        help_text: str,
        value: str = "",
    ) -> object:
        import wx

        label_control = wx.StaticText(panel, label=label)
        label_control.SetName(f"{name} label")
        root.Add(label_control, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        control = wx.TextCtrl(panel, value=value)
        control.SetName(name)
        control.SetHelpText(help_text)
        root.Add(control, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        return control

    def _on_generate(self, _event: object) -> None:
        target_tag = self._target.GetValue().strip()
        previous_tag = self._previous.GetValue().strip()
        target_commitish = self._target_commitish.GetValue().strip()
        if not target_tag or not previous_tag:
            self._status.SetLabel("Enter both tags to define the release range.")
            return
        if target_tag == previous_tag:
            self._status.SetLabel("The target tag and previous tag must be different.")
            return
        self._generate_btn.Enable(False)
        self._copy_btn.Enable(False)
        self._status.SetLabel(f"Generating a preview for {previous_tag} to {target_tag}…")

        def worker() -> None:
            try:
                draft = self._provider.generate_release_notes(
                    self._repository,
                    target_tag=target_tag,
                    previous_tag=previous_tag,
                    target_commitish=target_commitish,
                )
            except GitHubItemsError as exc:
                self._wx.CallAfter(self._generation_failed, str(exc))
                return
            self._wx.CallAfter(self._generation_ready, draft)

        threading.Thread(
            target=worker, daemon=True
        ).start()  # GATE-40-OK: explicit draft generation.

    def _generation_failed(self, message: str) -> None:
        if not dialog_alive(self.dialog):
            return
        self._generate_btn.Enable(True)
        self._status.SetLabel(f"Could not generate draft: {message}")
        self._announce(f"Could not generate release notes: {message}")

    def _generation_ready(self, draft: GitHubReleaseNotesDraft) -> None:
        if not dialog_alive(self.dialog):
            return
        self._draft = draft
        self._name.ChangeValue(draft.name)
        self._body.ChangeValue(draft.body)
        self._generate_btn.Enable(True)
        self._copy_btn.Enable(True)
        self._status.SetLabel(
            f"Preview generated for {draft.range_text}. Review it; nothing was published."
        )
        self._announce(f"Release-notes preview generated for {draft.range_text}.")

    def _on_copy(self, _event: object) -> None:
        text = self._name.GetValue().strip()
        body = self._body.GetValue().strip()
        value = f"{text}\n\n{body}".strip()
        if not value:
            self._status.SetLabel("There is no release-note draft to copy.")
            return
        wx = self._wx
        if not wx.TheClipboard.Open():
            self._status.SetLabel("Could not open the clipboard.")
            return
        try:
            copied = wx.TheClipboard.SetData(wx.TextDataObject(value))
        finally:
            wx.TheClipboard.Close()
        message = (
            "Copied the release-notes draft; it is still local."
            if copied
            else "Could not copy the draft."
        )
        self._status.SetLabel(message)
        self._announce(message)

    def show(self) -> None:
        wx = self._wx
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_CANCEL,
            affirmative_label="Close",
            cancel_id=wx.ID_CANCEL,
            cancel_label="Close",
            escape_id=wx.ID_CANCEL,
        )
        try:
            show_modal_dialog(self.dialog, "Draft Release Notes")
        finally:
            self.dialog.Destroy()


__all__ = ["GitHubReleaseNotesDialog"]
