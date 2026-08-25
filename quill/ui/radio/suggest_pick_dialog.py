"""Community > Suggest a Station or Podcast...: no account, no browser.

The whole point of this surface is that **it does not send anybody to GitHub**.
Quill Radio already carries a bundled, issues-only token so Report a Bug works
for people who have configured nothing; a suggestion rides the same path. You
type it here and it becomes a real issue, with an issue number read back to
you, without a login, an account, or a web form designed by somebody else.

The fallback still exists -- a pre-filled issue in the browser -- for a build
with no token (dev checkouts) or a post that fails. It is a fallback and
nothing more: it needs the GitHub account this flow exists to avoid.

Validation happens before anything is sent, because catching a duplicate here
costs one dialog and catching it after moderation costs a round trip through a
person.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from quill.core.pick_suggestion import (
    REPO,
    SUGGESTION_LABEL,
    Suggestion,
    browser_url,
    issue_body,
    issue_title,
    known_urls,
    validate,
)
from quill.ui.dialog_contract import apply_modal_ids

TITLE = "Suggest a Station or Podcast"

_KINDS = (("A radio station", "stream"), ("A podcast", "podcast"))
_API = f"https://api.github.com/repos/{REPO}/issues"
_TIMEOUT_SECONDS = 20


def open_suggest_dialog(host: Any) -> None:
    """Collect a suggestion and file it. Never raises into the menu."""
    if getattr(host, "_safe_mode", False):
        host._announce("Safe Mode is on, so nothing is sent anywhere.")
        return
    import wx

    _SuggestDialog(host, wx).show()


class _SuggestDialog:
    def __init__(self, host: Any, wx: Any) -> None:
        self._host = host
        self._wx = wx

    def show(self) -> None:
        wx = self._wx
        self.dialog = wx.Dialog(self._host.frame, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE)
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                self.dialog,
                label=(
                    "Tell us about a station or podcast worth adding to the "
                    "Community Picks list. You do not need a GitHub account -- "
                    "Quill Radio sends it for you."
                ),
            ),
            0,
            wx.ALL,
            8,
        )

        grid = wx.FlexGridSizer(0, 2, 6, 8)
        grid.AddGrowableCol(1, 1)
        self._kind = self._choice(
            grid,
            "&What is it:",
            [label for label, _ in _KINDS],
            "Whether this is a live radio station or a podcast feed.",
        )
        self._title_ctrl = self._field(grid, "&Name:", "What it should be called in the list.")
        self._url = self._field(
            grid,
            "&Address:",
            "The stream address for a station, or the feed address for a podcast. "
            "It must start with https.",
        )
        self._description = self._field(
            grid,
            "&Description:",
            "One or two sentences saying what it is, for somebody who has never heard it.",
            multiline=True,
        )
        self._language = self._field(grid, "&Language:", "Such as en, or en-US. Optional.")
        self._why = self._field(
            grid,
            "W&hy it belongs:",
            "Anything that would help decide. Optional, and not published.",
            multiline=True,
        )
        root.Add(grid, 1, wx.EXPAND | wx.ALL, 8)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._send = wx.Button(self.dialog, wx.ID_OK, "&Send Suggestion")
        self._send.SetHelpText("Checks what you typed, then files it. Nothing is sent until now.")
        cancel = wx.Button(self.dialog, wx.ID_CANCEL, "Cl&ose")
        cancel.SetHelpText("Closes without sending anything.")
        buttons.AddStretchSpacer()
        buttons.Add(self._send, 0, wx.RIGHT, 6)
        buttons.Add(cancel, 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)

        self.dialog.SetSizerAndFit(root)
        self._send.Bind(wx.EVT_BUTTON, lambda _e: self._submit())
        apply_modal_ids(self.dialog, affirmative_id=self._send.GetId(), escape_id=cancel.GetId())
        try:
            self._host._show_modal_dialog(self.dialog, TITLE)
        finally:
            self.dialog.Destroy()

    # -- fields -----------------------------------------------------------------

    def _field(self, grid: Any, label: str, help_text: str, *, multiline: bool = False) -> Any:
        wx = self._wx
        # Label before field, always: the dialog z-order gate reads tab order,
        # and a screen reader names a field from the static text before it.
        grid.Add(wx.StaticText(self.dialog, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
        style = wx.TE_MULTILINE if multiline else 0
        control = wx.TextCtrl(self.dialog, style=style, size=(340, 66 if multiline else -1))
        control.SetName(help_text)
        control.SetHelpText(help_text)
        grid.Add(control, 1, wx.EXPAND)
        return control

    def _choice(self, grid: Any, label: str, options: list[str], help_text: str) -> Any:
        wx = self._wx
        grid.Add(wx.StaticText(self.dialog, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
        control = wx.Choice(self.dialog, choices=options)
        control.SetSelection(0)
        control.SetName(help_text)
        control.SetHelpText(help_text)
        grid.Add(control, 1, wx.EXPAND)
        return control

    def _suggestion(self) -> Suggestion:
        index = max(0, self._kind.GetSelection())
        return Suggestion(
            type=_KINDS[index][1],
            title=self._title_ctrl.GetValue().strip(),
            url=self._url.GetValue().strip(),
            description=self._description.GetValue().strip(),
            language=self._language.GetValue().strip(),
            why=self._why.GetValue().strip(),
        )

    # -- sending ----------------------------------------------------------------

    def _submit(self) -> None:
        suggestion = self._suggestion()
        from quill.core.community_picks import load_bundled

        result = validate(suggestion, known_urls=known_urls(load_bundled()))
        if not result.ok:
            # Spoken and shown: the first problem is the one to fix, and a list
            # of six read out at once is a list nobody retains.
            self._host._announce(result.errors[0])
            self._host._show_message_box(
                "\n".join(result.errors), TITLE, self._wx.ICON_INFORMATION | self._wx.OK
            )
            return
        number = _post_issue(suggestion, self._app_label())
        if number:
            self._host._announce(
                f"Thank you. Your suggestion was sent as issue {number}. "
                "It appears in the list once it is approved."
            )
            self.dialog.EndModal(self._wx.ID_OK)
            return
        self._offer_browser(suggestion)

    def _app_label(self) -> str:
        version = getattr(self._host, "_app_version", "") or ""
        return f"Quill Radio {version}".strip()

    def _offer_browser(self, suggestion: Suggestion) -> None:
        answer = self._host._show_message_box(
            "The suggestion could not be sent from here. Open it in your browser "
            "instead? You will need a GitHub account for that route.",
            TITLE,
            self._wx.ICON_QUESTION | self._wx.YES_NO,
        )
        if answer == self._wx.YES:
            self._wx.LaunchDefaultBrowser(browser_url(suggestion))
            self.dialog.EndModal(self._wx.ID_OK)


def _post_issue(suggestion: Suggestion, submitted_from: str) -> str:
    """File the issue with the bundled token. "" when it could not be sent.

    Never raises: every failure ends at the browser fallback, so a suggestion
    is never simply lost with nothing said.
    """
    from quill.core.feedback_token import effective_github_token, github_token_present

    if not github_token_present():
        return ""
    payload = json.dumps({
        "title": issue_title(suggestion),
        "body": issue_body(suggestion, submitted_from=submitted_from),
        "labels": [SUGGESTION_LABEL],
    }).encode("utf-8")
    request = urllib.request.Request(
        _API,
        data=payload,
        headers={
            "Authorization": f"Bearer {effective_github_token()}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "QUILL (community picks; +https://github.com/Community-Access/quill)",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            created = json.loads(response.read(1024 * 64).decode("utf-8", "replace"))
        return f"#{created.get('number')}" if created.get("number") else ""
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return ""


__all__ = ["TITLE", "open_suggest_dialog"]
