"""One accessible form for drafting an issue from a blank start or template."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from quill.core.github.issue_templates import GitHubIssueTemplate
from quill.core.github.local_drafts import GitHubIssueDraftStore
from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog
from quill.ui.dpi import dip_size


@dataclass(frozen=True, slots=True)
class GitHubIssueDraft:
    """User-reviewed issue fields, ready for the explicit Create Issue action."""

    title: str
    body: str
    labels: tuple[str, ...]
    assignees: tuple[str, ...]


def _split_values(value: str, *, usernames: bool = False) -> tuple[str, ...]:
    cleaned = (
        part.strip().removeprefix("@") if usernames else part.strip() for part in value.split(",")
    )
    return tuple(dict.fromkeys(part for part in cleaned if part))


class GitHubIssueDraftDialog:
    """Edit a title, body, labels, and assignees in one native dialog."""

    def __init__(
        self,
        parent: object,
        template: GitHubIssueTemplate | None = None,
        *,
        draft_store: GitHubIssueDraftStore | None = None,
        repository: str = "",
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _message: None)
        self._result: GitHubIssueDraft | None = None
        self._template = template
        self._draft_store = draft_store
        self._repository = repository
        self._save_timer = None
        self._draft_suppressed = False
        saved_draft = draft_store.get_issue(repository) if draft_store and repository else None
        self._recovered = saved_draft is not None
        self.dialog = wx.Dialog(
            parent,
            title="New Issue",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(dip_size(self.dialog, 620, 560))
        self.dialog.SetSize(dip_size(self.dialog, 760, 700))
        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)
        intro = wx.StaticText(
            panel,
            label=(
                "Review the title and body. Labels and assignees are optional; "
                "they must already exist in this repository. Create Issue is the "
                "only action here that submits anything to GitHub."
            ),
        )
        intro.Wrap(700)
        root.Add(intro, 0, wx.EXPAND | wx.ALL, 10)

        self._draft_notice = wx.StaticText(
            panel,
            label=(
                f"Recovered a local draft for {repository}. It has not been submitted."
                if self._recovered
                else "Draft changes save locally as you type. They are not submitted."
            ),
        )
        self._draft_notice.SetName("Local issue draft status")
        self._draft_notice.SetHelpText(
            "A saved issue draft is private to this account and repository. "
            "It is never submitted automatically."
        )
        root.Add(self._draft_notice, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        def initial(field: str, fallback: str) -> str:
            return getattr(saved_draft, field) if saved_draft is not None else fallback

        title_label = wx.StaticText(panel, label="&Title:")
        title_label.SetName("Issue title label")
        root.Add(title_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self._title = wx.TextCtrl(panel, value=initial("title", template.title if template else ""))
        self._title.SetName("Issue title")
        self._title.SetHelpText("Required. Up to 256 characters.")
        root.Add(self._title, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        body_label = wx.StaticText(panel, label="&Body:")
        body_label.SetName("Issue body label")
        root.Add(body_label, 0, wx.LEFT | wx.RIGHT, 10)
        self._body = wx.TextCtrl(
            panel,
            value=initial("body", template.body if template else ""),
            style=wx.TE_MULTILINE | wx.TE_WORDWRAP,
        )
        self._body.SetName("Issue body")
        self._body.SetHelpText("Optional. Markdown is submitted as plain issue text.")
        root.Add(self._body, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        labels_label = wx.StaticText(panel, label="&Labels (comma-separated):")
        labels_label.SetName("Issue labels label")
        root.Add(labels_label, 0, wx.LEFT | wx.RIGHT, 10)
        self._labels = wx.TextCtrl(
            panel,
            value=(
                ", ".join(saved_draft.labels)
                if saved_draft is not None
                else ", ".join(template.labels)
                if template
                else ""
            ),
        )
        self._labels.SetName("Issue labels")
        self._labels.SetHelpText("Optional repository labels. Leave blank for none.")
        root.Add(self._labels, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        assignees_label = wx.StaticText(panel, label="&Assignees (GitHub usernames):")
        assignees_label.SetName("Issue assignees label")
        root.Add(assignees_label, 0, wx.LEFT | wx.RIGHT, 10)
        self._assignees = wx.TextCtrl(
            panel,
            value=(
                ", ".join(saved_draft.assignees)
                if saved_draft is not None
                else ", ".join(template.assignees)
                if template
                else ""
            ),
        )
        self._assignees.SetName("Issue assignees")
        self._assignees.SetHelpText("Optional usernames separated by commas; @ is optional.")
        root.Add(self._assignees, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._status = wx.StaticText(panel, label="")
        self._status.SetName("Issue draft validation status")
        root.Add(self._status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._discard_btn = wx.Button(panel, wx.ID_ANY, label="Discard Saved Draft")
        self._discard_btn.SetName("Discard the recovered local issue draft")
        self._discard_btn.SetHelpText("Remove this draft from this device without submitting it.")
        self._discard_btn.Enable(self._recovered)
        root.Add(self._discard_btn, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        buttons = wx.StdDialogButtonSizer()
        create_btn = wx.Button(panel, wx.ID_OK, label="Create Issue")
        create_btn.SetDefault()
        create_btn.SetName("Create issue on GitHub")
        cancel_btn = wx.Button(panel, wx.ID_CANCEL, label="Cancel")
        cancel_btn.SetName("Cancel issue creation")
        buttons.AddButton(create_btn)
        buttons.AddButton(cancel_btn)
        buttons.Realize()
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)
        for control in (self._title, self._body, self._labels, self._assignees):
            control.Bind(wx.EVT_TEXT, self._schedule_local_draft_save)
        create_btn.Bind(wx.EVT_BUTTON, self._on_create)
        self._discard_btn.Bind(wx.EVT_BUTTON, self._discard_local_draft)
        if not self._recovered:
            self._save_local_draft()

    def _schedule_local_draft_save(self, _event: object | None = None) -> None:
        self._draft_suppressed = False
        if self._save_timer is not None:
            self._save_timer.Stop()
        self._save_timer = self._wx.CallLater(350, self._save_local_draft)

    def _save_local_draft(self) -> None:
        if self._save_timer is not None:
            self._save_timer.Stop()
            self._save_timer = None
        if self._draft_suppressed or self._draft_store is None or not self._repository:
            return
        title = self._title.GetValue().strip()
        body = self._body.GetValue().strip()
        labels = _split_values(self._labels.GetValue())
        assignees = _split_values(self._assignees.GetValue(), usernames=True)
        if not (title or body or labels or assignees):
            saved = self._draft_store.delete_issue(self._repository)
            if saved:
                self._draft_notice.SetLabel("Local draft cleared. Nothing has been submitted.")
            else:
                self._say(
                    self._draft_notice,
                    "Could not clear the local draft. Nothing has been submitted.",
                )
            return
        saved = self._draft_store.save_issue(
            self._repository,
            title=title,
            body=body,
            labels=labels,
            assignees=assignees,
        )
        if saved:
            # Silent on success: this runs while typing, and the reader would talk over it.
            self._draft_notice.SetLabel("Saved locally. Not submitted to GitHub.")
        else:
            self._say(
                self._draft_notice, "Could not save locally. This draft has not been submitted."
            )

    def _say(self, label: object, message: str) -> None:
        """Show *message* in a status line and say it: focus is elsewhere (GATE-12)."""
        label.SetLabel(message)  # type: ignore[attr-defined]
        self._announce(message)

    def _discard_local_draft(self, _event: object) -> None:
        if self._save_timer is not None:
            self._save_timer.Stop()
            self._save_timer = None
        if self._draft_store is None or not self._repository:
            return
        if not self._draft_store.delete_issue(self._repository):
            self._say(self._draft_notice, "Could not discard the saved local draft.")
            return
        self._recovered = False
        self._draft_suppressed = True
        self._title.ChangeValue(self._template.title if self._template else "")
        self._body.ChangeValue(self._template.body if self._template else "")
        self._labels.ChangeValue(", ".join(self._template.labels) if self._template else "")
        self._assignees.ChangeValue(", ".join(self._template.assignees) if self._template else "")
        self._discard_btn.Enable(False)
        self._say(self._draft_notice, "Saved local draft discarded. Nothing has been submitted.")

    def _on_create(self, _event: object) -> None:
        title = self._title.GetValue().strip()
        if not title:
            self._say(self._status, "Enter an issue title before creating the issue.")
            self._title.SetFocus()
            return
        if len(title) > 256:
            self._say(self._status, "Issue titles must be 256 characters or fewer.")
            self._title.SetFocus()
            return
        self._result = GitHubIssueDraft(
            title=title,
            body=self._body.GetValue().strip(),
            labels=_split_values(self._labels.GetValue()),
            assignees=_split_values(self._assignees.GetValue(), usernames=True),
        )
        self._save_local_draft()
        self.dialog.EndModal(self._wx.ID_OK)

    def show(self) -> GitHubIssueDraft | None:
        wx = self._wx
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_OK,
            escape_id=wx.ID_CANCEL,
        )
        try:
            if show_modal_dialog(self.dialog, "New Issue") != wx.ID_OK:
                return None
            return self._result
        finally:
            self._save_local_draft()
            self.dialog.Destroy()


__all__ = ["GitHubIssueDraft", "GitHubIssueDraftDialog"]
