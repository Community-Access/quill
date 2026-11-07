"""Accessible local draft composer for a pull-request review."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from quill.core.github.local_drafts import GitHubIssueDraftStore, GitHubReviewDraftData
from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog
from quill.ui.dpi import dip_size


@dataclass(frozen=True, slots=True)
class GitHubReviewDraft:
    """A user-approved review payload, ready for the explicit Submit action."""

    event: str
    body: str
    saved_head_sha: str


class GitHubReviewDraftDialog:
    """Recover a local review draft and submit it only after explicit review."""

    _EVENTS = ("comment", "approve", "request changes")

    def __init__(
        self,
        parent: object,
        *,
        draft_store: GitHubIssueDraftStore,
        repository: str,
        number: int,
        current_head_sha: str,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _message: None)
        self._draft_store = draft_store
        self._repository = repository
        self._number = number
        self._current_head_sha = current_head_sha
        self._save_timer = None
        self._draft_suppressed = False
        self._result: GitHubReviewDraft | None = None
        saved = draft_store.get_review(repository, number)
        self._saved: GitHubReviewDraftData | None = saved
        self._draft_head_sha = saved.head_sha if saved and saved.head_sha else current_head_sha
        self._stale = bool(saved and saved.head_sha and saved.head_sha != current_head_sha)

        self.dialog = wx.Dialog(
            parent,
            title=f"Review Pull Request #{number}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(dip_size(self.dialog, 640, 460))
        self.dialog.SetSize(dip_size(self.dialog, 780, 600))
        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(
            panel,
            label=(
                "Choose the review action and edit its message. Changes save locally; "
                "Submit Review is the only action that sends this review to GitHub."
            ),
        )
        intro.Wrap(720)
        root.Add(intro, 0, wx.EXPAND | wx.ALL, 10)

        self._notice = wx.StaticText(panel, label=self._notice_text(saved))
        self._notice.SetName("Local pull-request review draft status")
        self._notice.SetHelpText(
            "This review is saved on this device and is not sent until Submit Review is activated."
        )
        root.Add(self._notice, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        event_label = wx.StaticText(panel, label="Review action:")
        event_label.SetName("Review action label")
        root.Add(event_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self._event = wx.Choice(panel, choices=["Comment", "Approve", "Request changes"])
        self._event.SetName("Review action; comment, approve, or request changes")
        saved_event = saved.event if saved and saved.event in self._EVENTS else "comment"
        self._event.SetSelection(self._EVENTS.index(saved_event))
        self._event.SetHelpText(
            "Select the review decision to submit after checking the current diff."
        )
        root.Add(self._event, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        root.Add(wx.StaticText(panel, label="Review &message:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self._body = wx.TextCtrl(
            panel,
            value=saved.body if saved else "",
            style=wx.TE_MULTILINE | wx.TE_WORDWRAP,
        )
        self._body.SetName("Pull-request review message")
        self._body.SetHelpText(
            "Required for Comment and Request Changes. Saved locally until submitted."
        )
        root.Add(self._body, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._stale_confirm = wx.CheckBox(
            panel,
            label=(
                "I reviewed the current changes and want to submit this draft on the current HEAD"
            ),
        )
        self._stale_confirm.SetName(
            "Confirm saved review is still appropriate for the current pull request head"
        )
        self._stale_confirm.SetHelpText(
            "The saved review was created for a different pull request head commit."
        )
        self._stale_confirm.Show(self._stale)
        root.Add(self._stale_confirm, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._status = wx.StaticText(panel, label="")
        self._status.SetName("Review draft validation status")
        root.Add(self._status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._discard_btn = wx.Button(panel, wx.ID_ANY, label="Discard Saved Draft")
        self._discard_btn.SetName("Discard this saved local review draft")
        self._discard_btn.SetHelpText(
            "Remove the review draft from this device without submitting it."
        )
        self._discard_btn.Enable(saved is not None)
        root.Add(self._discard_btn, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        buttons = wx.StdDialogButtonSizer()
        submit_btn = wx.Button(panel, wx.ID_OK, label="Submit Review")
        submit_btn.SetDefault()
        submit_btn.SetName("Submit this review to GitHub")
        submit_btn.SetHelpText("Send the selected review action to GitHub now.")
        cancel_btn = wx.Button(panel, wx.ID_CANCEL, label="Save Draft and Close")
        cancel_btn.SetName("Save the local review draft and close")
        buttons.AddButton(submit_btn)
        buttons.AddButton(cancel_btn)
        buttons.Realize()
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)
        self._body.Bind(wx.EVT_TEXT, self._schedule_save)
        self._event.Bind(wx.EVT_CHOICE, self._schedule_save)
        self._discard_btn.Bind(wx.EVT_BUTTON, self._discard)
        submit_btn.Bind(wx.EVT_BUTTON, self._submit)

    def _notice_text(self, saved: GitHubReviewDraftData | None) -> str:
        if self._stale and saved is not None:
            return (
                f"Recovered a local draft saved for HEAD {saved.head_sha[:12]}. "
                f"The current HEAD is {self._current_head_sha[:12]}. It is not submitted."
            )
        if saved is not None:
            return "Recovered a local review draft. It is not submitted to GitHub."
        return "Review changes save locally as you type. They are not submitted."

    def _schedule_save(self, _event: object | None = None) -> None:
        self._draft_suppressed = False
        if self._save_timer is not None:
            self._save_timer.Stop()
        self._save_timer = self._wx.CallLater(350, self._save_local)

    def _save_local(self) -> None:
        if self._save_timer is not None:
            self._save_timer.Stop()
            self._save_timer = None
        if self._draft_suppressed:
            return
        event_index = self._event.GetSelection()
        event = self._EVENTS[event_index] if 0 <= event_index < len(self._EVENTS) else "comment"
        body = self._body.GetValue().strip()
        if event == "comment" and not body and self._saved is None:
            return
        saved = self._draft_store.save_review(
            self._repository,
            self._number,
            event=event,
            body=body,
            head_sha=self._draft_head_sha,
        )
        if saved:
            # Silent on success: this runs while typing, and the reader would talk over it.
            self._notice.SetLabel("Saved locally. Not submitted to GitHub.")
        else:
            self._say(self._notice, "Could not save locally. This review has not been submitted.")

    def _say(self, label: object, message: str) -> None:
        """Show *message* in a status line and say it: focus is elsewhere (GATE-12)."""
        label.SetLabel(message)  # type: ignore[attr-defined]
        self._announce(message)

    def _discard(self, _event: object) -> None:
        if self._save_timer is not None:
            self._save_timer.Stop()
            self._save_timer = None
        if not self._draft_store.delete_review(self._repository, self._number):
            self._say(self._status, "Could not discard the local review draft.")
            return
        self._draft_suppressed = True
        self._body.ChangeValue("")
        self._event.SetSelection(self._EVENTS.index("comment"))
        self._stale_confirm.SetValue(False)
        self._stale = False
        self._saved = None
        self._draft_head_sha = self._current_head_sha
        self._discard_btn.Enable(False)
        self._say(self._notice, "Local review draft discarded. Nothing has been submitted.")

    def _submit(self, _event: object) -> None:
        event_index = self._event.GetSelection()
        if not 0 <= event_index < len(self._EVENTS):
            self._say(self._status, "Choose a review action.")
            return
        event = self._EVENTS[event_index]
        body = self._body.GetValue().strip()
        if event in {"comment", "request changes"} and not body:
            self._say(self._status, "Enter a message for this review action.")
            self._body.SetFocus()
            return
        if self._stale and not self._stale_confirm.GetValue():
            self._say(self._status, "Confirm that this draft still matches the current changes.")
            return
        if self._stale:
            self._draft_head_sha = self._current_head_sha
            self._stale = False
        self._save_local()
        self._result = GitHubReviewDraft(
            event=event, body=body, saved_head_sha=self._draft_head_sha
        )
        self.dialog.EndModal(self._wx.ID_OK)

    def show(self) -> GitHubReviewDraft | None:
        wx = self._wx
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        try:
            if show_modal_dialog(self.dialog, f"Review Pull Request #{self._number}") != wx.ID_OK:
                return None
            return self._result
        finally:
            self._save_local()
            self.dialog.Destroy()


__all__ = ["GitHubReviewDraft", "GitHubReviewDraftDialog"]
