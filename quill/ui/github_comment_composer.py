"""The GitHub Workbench's comment composer (GH-C, GitHub PRD section 22).

A comment used to be a plain text box. The composer keeps that box, and adds
what GitHub's own comment box has, said rather than shown:

* **Insert Mention...** (Alt+M) lists the conversation's people, then who
  may be assigned, and inserts ``@login``;
* **Insert Reference...** (Alt+R) finds an issue or pull request by words in
  its title, or by number, and inserts ``#42``;
* **Insert Emoji...** (Alt+E) searches QUILL's emoji list by name;
* **Insert Saved Reply...** (Alt+S) inserts one of the account's saved
  replies from GitHub;
* **Preview** (Alt+P) reads the comment as GitHub will show it, line by line,
  into a read-only box, and moves there;
* **Check before posting** (Alt+H, on to begin with) runs the accessibility
  check when you post and asks before sending a comment it has something to
  say about;
* **Attach Files...** (Alt+F) says why it cannot: GitHub has no API for it.

Post is the default button; in the comment box Enter is a new line and
Ctrl+Enter posts, as on github.com. Lookups run through the caller's
*background*, never on the UI thread. The words are
:mod:`quill.core.github.comment_compose`.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import wx

from quill.core.github import comment_compose as cc
from quill.ui.dialog_contract import apply_modal_ids
from quill.ui.dpi import dip_size
from quill.ui.spoken_name import set_spoken_name

__all__ = ["CommentComposer", "compose_comment"]

ShowModal = Callable[[Any, str], int]
Background = Callable[[str, Callable[[], Any], Callable[[Any], None]], None]


class CommentComposer(wx.Dialog):
    def __init__(
        self,
        parent: wx.Window,
        *,
        title: str,
        api: Any,
        repository: str,
        people: Sequence[str] = (),
        text: str = "",
        background: Background,
        show_modal: ShowModal,
        say: Callable[[str], None],
    ) -> None:
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.api, self.repository, self.people = api, repository, list(people)
        self._background, self._show_modal, self._say = background, show_modal, say
        self.SetHelpText(
            "Write a comment for GitHub. The buttons insert a mention, a reference, an "
            "emoji or a saved reply at the cursor; Preview reads it as GitHub will show it. "
            "Ctrl+Enter or Post sends it; Escape leaves without sending."
        )
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label="&Comment:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.box = wx.TextCtrl(self, value=text, style=wx.TE_MULTILINE | wx.TE_RICH2)
        self.box.SetMinSize(dip_size(self, 520, 200))
        self.box.SetHelpText(
            "The comment, in Markdown. Enter starts a new line; Ctrl+Enter posts it."
        )
        set_spoken_name(self.box, "Comment")
        sizer.Add(self.box, 1, wx.EXPAND | wx.ALL, 8)

        row = wx.WrapSizer(wx.HORIZONTAL)
        self.buttons: dict[str, wx.Button] = {}
        for key, label, help_text, handler in (
            (
                "mention",
                "Insert &Mention...",
                "Choose a person to mention: the conversation's people first.",
                self.insert_mention,
            ),
            (
                "reference",
                "Insert &Reference...",
                "Find an issue or pull request by words in its title, or its number.",
                self.insert_reference,
            ),
            ("emoji", "Insert &Emoji...", "Find an emoji by its name.", self.insert_emoji),
            (
                "saved",
                "Insert &Saved Reply...",
                "Insert one of your saved replies from GitHub.",
                self.insert_saved_reply,
            ),
            (
                "attach",
                "Attach &Files...",
                "Says how to share a file, because GitHub lets no program attach one.",
                self.attach_files,
            ),
            ("preview", "&Preview", "Read the comment as GitHub will show it.", self.preview),
        ):
            button = wx.Button(self, label=label)
            button.SetHelpText(help_text)
            button.Bind(wx.EVT_BUTTON, lambda _e, h=handler: h())
            self.buttons[key] = button
            row.Add(button, 0, wx.ALL, 4)
        sizer.Add(row, 0, wx.LEFT | wx.RIGHT, 4)

        self.check = wx.CheckBox(self, label="C&heck before posting")
        self.check.SetValue(True)
        self.check.SetHelpText(
            "When on, Post first checks for images without a description, vague links, "
            "skipped heading levels, long capitals and emoji-only comments, and asks."
        )
        sizer.Add(self.check, 0, wx.ALL, 8)

        sizer.Add(wx.StaticText(self, label="Pre&view:"), 0, wx.LEFT | wx.RIGHT, 8)
        self.preview_box = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.preview_box.SetMinSize(dip_size(self, 520, 120))
        self.preview_box.SetHelpText(
            "The comment as GitHub will show it, one line each, saying what every line "
            "is. Press Preview again after a change."
        )
        set_spoken_name(self.preview_box, "Preview")
        sizer.Add(self.preview_box, 1, wx.EXPAND | wx.ALL, 8)

        buttons = wx.StdDialogButtonSizer()
        post = wx.Button(self, wx.ID_OK, "Post")
        post.SetHelpText("Send the comment to GitHub. Ctrl+Enter in the comment does the same.")
        post.SetDefault()
        cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")
        cancel.SetHelpText("Leave without sending anything. Escape does the same.")
        buttons.AddButton(post)
        buttons.AddButton(cancel)
        buttons.Realize()
        sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        apply_modal_ids(self)
        post.Bind(wx.EVT_BUTTON, lambda _e: self.post())
        self.box.Bind(wx.EVT_KEY_DOWN, self._on_key)
        self.box.SetFocus()

    # -- the box -----------------------------------------------------------------

    def text(self) -> str:
        return str(self.box.GetValue())

    def insert(self, words: str, said: str) -> None:
        """Put *words* at the cursor, with a space before when it would touch a word."""
        at = self.box.GetInsertionPoint()
        before = self.text()[at - 1 : at] if at else ""
        lead = " " if before and not before.isspace() and not words.startswith("\n") else ""
        self.box.WriteText(lead + words)
        self.box.SetFocus()
        self._say(said)

    def _on_key(self, event: wx.KeyEvent) -> None:
        if event.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER) and event.ControlDown():
            self.post()
            return
        event.Skip()

    def _pick(self, title: str, prompt: str, labels: list[str]) -> int:
        with wx.SingleChoiceDialog(self, prompt, title, labels) as dialog:
            dialog.SetName(title)
            if self._show_modal(dialog, title) != wx.ID_OK:
                return -1
            return int(dialog.GetSelection())

    def _ask(self, title: str, prompt: str) -> str:
        with wx.TextEntryDialog(self, prompt, title) as dialog:
            dialog.SetName(prompt.rstrip(":"))
            if self._show_modal(dialog, title) != wx.ID_OK:
                return ""
            return str(dialog.GetValue()).strip()

    # -- the inserts ---------------------------------------------------------------

    def insert_mention(self) -> None:
        api, repository, people = self.api, self.repository, self.people

        def chosen(logins: list[str]) -> None:
            if not logins:
                self._say("Nobody to mention was found in this repository.")
                return
            picked = self._pick("Insert Mention", "Mention who? GitHub will notify them.", logins)
            if picked >= 0:
                self.insert(f"@{logins[picked]}", f"Inserted @{logins[picked]}.")

        self._background(
            "find people to mention",
            lambda: cc.mention_candidates(api, repository, already=people),
            chosen,
        )

    def insert_reference(self) -> None:
        words = self._ask("Insert Reference", "Words in its title, or its number:")
        if not words:
            return
        api, repository = self.api, self.repository

        def chosen(found: list[cc.Reference]) -> None:
            if not found:
                self._say(f"No issue or pull request matches {words}.")
                return
            picked = self._pick(
                "Insert Reference", f"{len(found)} found:", [ref.label for ref in found]
            )
            if picked >= 0:
                self.insert(f"#{found[picked].number}", f"Inserted #{found[picked].number}.")

        self._background(
            "find issues and pull requests",
            lambda: cc.reference_candidates(api, repository, words),
            chosen,
        )

    def insert_emoji(self) -> None:
        from quill.core import emoji_data

        words = self._ask("Insert Emoji", "Emoji name, such as thumbs up or party:")
        if not words:
            return
        found = emoji_data.search(words)[:40] if emoji_data.is_available() else []
        if not found:
            self._say(f"No emoji is called {words}.")
            return
        labels = [f"{entry.name} {entry.char}" for entry in found]
        picked = self._pick("Insert Emoji", f"{len(found)} found:", labels)
        if picked >= 0:
            self.insert(found[picked].char, f"Inserted {found[picked].name}.")

    def insert_saved_reply(self) -> None:
        api = self.api

        def chosen(replies: list[cc.SavedReply]) -> None:
            if not replies:
                self._say(
                    "You have no saved replies on GitHub. Make them in GitHub's Settings, "
                    "Saved replies."
                )
                return
            picked = self._pick(
                "Insert Saved Reply", "Insert which?", [reply.title for reply in replies]
            )
            if picked >= 0:
                self.insert(replies[picked].body, f"Inserted {replies[picked].title}.")

        self._background("read your saved replies", lambda: cc.saved_replies(api), chosen)

    def attach_files(self) -> None:
        self._say(cc.ATTACHMENTS_SENTENCE)

    def preview(self) -> None:
        lines = cc.spoken_preview(self.text())
        self.preview_box.ChangeValue(cc.joined(lines) if lines else "The comment is empty.")
        self.preview_box.SetInsertionPoint(0)
        self.preview_box.SetFocus()

    # -- posting ---------------------------------------------------------------------

    def post(self) -> None:
        if not self.text().strip():
            self._say("Write a comment first.")
            self.box.SetFocus()
            return
        findings = cc.accessibility_findings(self.text()) if self.check.GetValue() else []
        if findings:
            question = (
                f"{len(findings)} things may trip a reader:\n\n"
                + "\n".join(f"- {finding}" for finding in findings)
                + "\n\nPost it anyway?"
            )
            with wx.MessageDialog(
                self, question, "Check Before Posting", wx.YES_NO | wx.NO_DEFAULT
            ) as dialog:
                if self._show_modal(dialog, "Check Before Posting") != wx.ID_YES:
                    self.box.SetFocus()
                    return
        self.EndModal(wx.ID_OK)


def compose_comment(
    parent: wx.Window,
    show_modal: ShowModal,
    *,
    title: str,
    api: Any,
    repository: str,
    background: Background,
    say: Callable[[str], None],
    people: Sequence[str] = (),
    text: str = "",
) -> str:
    """The comment to post, or "" when the person leaves without posting."""
    dialog = CommentComposer(
        parent,
        title=title,
        api=api,
        repository=repository,
        people=people,
        text=text,
        background=background,
        show_modal=show_modal,
        say=say,
    )
    try:
        if show_modal(dialog, title) != wx.ID_OK:
            return ""
        return dialog.text().strip()
    finally:
        dialog.Destroy()
