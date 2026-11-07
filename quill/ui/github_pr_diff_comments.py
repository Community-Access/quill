"""Patch lines, line comments, Copy Diff and Open Diff for the PR diff viewer.

The selected file's patch is listed one line per row, marked with words or
symbols as the reader prefers (Line marks, saved for both editors). From a
row: Comment on This Line, or Comment on Lines for a selected run or a typed
start and end. A comment is added to the pending review (kept on this device
until Compose Review submits it) or posted now. Copy Diff and Open Diff in
Default App hand the whole pull request over as a unified ``.diff``.
"""

from __future__ import annotations

import os
import tempfile
import threading
import webbrowser
from pathlib import Path

from quill.core.github.diff_lines import (
    LINE_MARK_LABELS,
    LINE_MARK_STYLES,
    LINE_MARKS_SYMBOLS,
    SYMBOLS_NOTE,
    DiffLine,
    LineCommentAnchor,
    anchor_for,
    lines_for_range,
    parse_diff_lines,
    parse_range,
    render_line,
    unified_diff_text,
)
from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.line_comment_drafts import LineCommentDraftStore
from quill.core.github.review_errors import GitHubReviewError
from quill.core.github.review_preferences import load_line_marks, save_line_marks
from quill.ui.dialog_contract import apply_listbox_activation, dialog_alive, show_modal_dialog


class GitHubPullDiffCommentsMixin:
    """Build and drive the patch-line list and its comment and export buttons."""

    def _build_line_controls(self, panel: object, root: object) -> None:
        wx = self._wx
        self._line_style = load_line_marks()
        self._patch_lines: tuple[DiffLine, ...] = ()
        self._posting = False
        self._pending_store = LineCommentDraftStore.load(getattr(self._provider, "token", None))

        marks_row = wx.BoxSizer(wx.HORIZONTAL)
        marks_label = wx.StaticText(panel, label="Line &marks:")
        self._marks_choice = wx.Choice(
            panel, choices=[LINE_MARK_LABELS[style] for style in LINE_MARK_STYLES]
        )
        self._marks_choice.SetName("Line marks")
        self._marks_choice.SetHelpText(
            "How patch lines are marked: words (Added line, Removed line) or symbols "
            "(plus and minus). Symbols need your screen reader to read punctuation."
        )
        self._marks_choice.SetSelection(LINE_MARK_STYLES.index(self._line_style))
        marks_row.Add(marks_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        marks_row.Add(self._marks_choice, 0)
        root.Add(marks_row, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self._marks_note = wx.StaticText(
            panel, label=SYMBOLS_NOTE if self._line_style == LINE_MARKS_SYMBOLS else ""
        )
        self._marks_note.SetName("Line marks note")
        self._marks_note.SetHelpText("Reminds you that symbols are spoken only with punctuation.")
        root.Add(self._marks_note, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        patch_label = wx.StaticText(panel, label="&Patch lines:")
        root.Add(patch_label, 0, wx.LEFT | wx.TOP, 8)
        self._patch_list = wx.ListBox(panel, choices=[], style=wx.LB_EXTENDED)
        self._patch_list.SetName("Patch lines")
        self._patch_list.SetHelpText(
            "The selected file's changes, one line per row. Shift with the arrows selects a "
            "run of lines. Enter comments on the selected lines."
        )
        root.Add(self._patch_list, 2, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        row = wx.BoxSizer(wx.HORIZONTAL)
        self._comment_line_btn = wx.Button(panel, wx.ID_ANY, label="Comment on This &Line…")
        self._comment_line_btn.SetHelpText(
            "Write a comment on the selected patch line, for your review or to post now."
        )
        self._comment_lines_btn = wx.Button(panel, wx.ID_ANY, label="Comment on Line&s…")
        self._comment_lines_btn.SetHelpText(
            "Comment on the selected run of lines, or type a start and end line."
        )
        self._copy_diff_btn = wx.Button(panel, wx.ID_ANY, label="&Copy Diff")
        self._copy_diff_btn.SetHelpText("Copy the whole pull request as a unified diff.")
        self._open_diff_btn = wx.Button(panel, wx.ID_ANY, label="&Open Diff in Default App")
        self._open_diff_btn.SetHelpText(
            "Save the whole pull request as a .diff file and open it in the app your "
            "computer uses for .diff files."
        )
        for button in (
            self._comment_line_btn,
            self._comment_lines_btn,
            self._copy_diff_btn,
            self._open_diff_btn,
        ):
            row.Add(button, 0, wx.RIGHT, 6)
        root.Add(row, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self._pending_label = wx.StaticText(panel, label=self._pending_text())
        self._pending_label.SetName("Pending line comments")
        self._pending_label.SetHelpText(
            "How many line comments wait for your review. Submit them from Compose Review."
        )
        root.Add(self._pending_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

        self._marks_choice.Bind(wx.EVT_CHOICE, self._on_marks_changed)
        self._comment_line_btn.Bind(wx.EVT_BUTTON, self._comment_on_line)
        self._comment_lines_btn.Bind(wx.EVT_BUTTON, self._comment_on_lines)
        self._copy_diff_btn.Bind(wx.EVT_BUTTON, self._copy_diff)
        self._open_diff_btn.Bind(wx.EVT_BUTTON, self._open_diff_in_app)
        apply_listbox_activation(self._patch_list, self._on_patch_activate)
        self._update_comment_buttons()

    # -- state --------------------------------------------------------

    def _can_comment(self) -> bool:
        return (
            bool(getattr(self._provider, "is_authenticated", False))
            and self._diff.number > 0
            and bool(self._diff.head_sha)
            and self._current_file is not None
        )

    def _update_comment_buttons(self) -> None:
        enabled = self._can_comment() and any(line.commentable for line in self._patch_lines)
        self._comment_line_btn.Enable(enabled)
        self._comment_lines_btn.Enable(enabled)

    def _pending_text(self) -> str:
        count = len(self._pending_store.pending(self._repo, self._diff.number))
        if not count:
            return "No line comments are waiting for your review."
        return (
            f"{count} line comment{'s' if count != 1 else ''} waiting for your review. "
            "Submit from Compose Review."
        )

    def _fill_patch_lines(self, pull_file: object) -> None:
        self._patch_lines = parse_diff_lines(str(getattr(pull_file, "patch", "") or ""))
        self._render_patch_lines()
        self._update_comment_buttons()

    def _render_patch_lines(self) -> None:
        selected = set(self._patch_list.GetSelections())
        rows = [render_line(line, self._line_style) for line in self._patch_lines]
        self._patch_list.Set(rows or ["GitHub sent no patch lines for this file."])
        for index in selected:
            if index < len(rows):
                self._patch_list.SetSelection(index)

    def _on_marks_changed(self, _event: object) -> None:
        index = self._marks_choice.GetSelection()
        if not 0 <= index < len(LINE_MARK_STYLES):
            return
        self._line_style = LINE_MARK_STYLES[index]
        saved = save_line_marks(self._line_style)
        symbols = self._line_style == LINE_MARKS_SYMBOLS
        self._marks_note.SetLabel(SYMBOLS_NOTE if symbols else "")
        self._render_patch_lines()
        if symbols:
            self._announce(SYMBOLS_NOTE)
        if not saved:
            self._announce("Could not save the line marks choice; it lasts until you close.")

    def _selected_patch_lines(self) -> list[DiffLine]:
        return [
            self._patch_lines[index]
            for index in self._patch_list.GetSelections()
            if 0 <= index < len(self._patch_lines)
        ]

    # -- commenting ---------------------------------------------------

    def _on_patch_activate(self, event: object) -> None:
        if len(self._patch_list.GetSelections()) > 1:
            self._comment_on_lines(event)
        else:
            self._comment_on_line(event)

    def _comment_on_line(self, _event: object) -> None:
        if not self._can_comment():
            self._announce("Sign in to GitHub and choose a changed file to comment.")
            return
        lines = [line for line in self._selected_patch_lines() if line.commentable]
        try:
            anchor = anchor_for(self._current_file.filename, lines[:1])
        except GitHubReviewError as exc:
            self._announce(str(exc))
            return
        self._open_line_comment(anchor, lines[:1])

    def _comment_on_lines(self, _event: object) -> None:
        if not self._can_comment():
            self._announce("Sign in to GitHub and choose a changed file to comment.")
            return
        selected = [line for line in self._selected_patch_lines() if line.commentable]
        try:
            if len(selected) > 1:
                lines = selected
            else:
                side = selected[0].side if selected else "RIGHT"
                typed = self._ask_line_range(selected[0] if selected else None)
                if typed is None:
                    return
                start, end = parse_range(typed)
                lines = list(lines_for_range(self._patch_lines, start, end, side=side))
            anchor = anchor_for(self._current_file.filename, lines)
        except GitHubReviewError as exc:
            self._announce(str(exc))
            return
        self._open_line_comment(anchor, lines)

    def _ask_line_range(self, line: DiffLine | None) -> str | None:
        wx = self._wx
        side = "old-file" if line is not None and line.side == "LEFT" else "new-file"
        start = line.line if line is not None else ""
        dialog = wx.TextEntryDialog(
            self.dialog,
            f"Start and end {side} lines to comment on, for example 12-15:",
            "Comment on Lines",
            value=f"{start}-{start}" if start else "",
        )
        try:
            if show_modal_dialog(dialog, "Comment on Lines", announce=self._announce) != wx.ID_OK:
                return None
            return dialog.GetValue().strip() or None
        finally:
            dialog.Destroy()

    def _open_line_comment(
        self, anchor: LineCommentAnchor, lines: list[DiffLine], body: str = ""
    ) -> None:
        from quill.ui.github_line_comment_dialog import POST_NOW, GitHubLineCommentDialog

        choice = GitHubLineCommentDialog(
            self.dialog,
            anchor=anchor,
            lines=lines,
            style=self._line_style,
            body=body,
            can_post_now=not self._posting,
            announce_cb=self._announce,
        ).show()
        if choice is None:
            return
        if choice.action == POST_NOW:
            self._post_line_comment(anchor, choice.body)
            return
        added = self._pending_store.add(
            self._repo, self._diff.number, anchor, choice.body, self._diff.head_sha
        )
        if added is None:
            self._announce("Could not keep the comment on this device. Nothing was sent.")
            return
        self._pending_label.SetLabel(self._pending_text())
        self._announce(f"Added to your review: {anchor.describe()}. {self._pending_text()}")
        callback = getattr(self, "_on_pending_changed", None)
        if callback is not None:
            callback()

    def _post_line_comment(self, anchor: LineCommentAnchor, body: str) -> None:
        if self._posting:
            self._announce("Please wait for the comment being posted.")
            return
        self._posting = True
        repo, number, head = self._repo, self._diff.number, self._diff.head_sha

        def worker() -> None:
            try:
                self._provider.post_line_comment(repo, number, anchor, body, head)
            except GitHubItemsError as exc:
                self._wx.CallAfter(self._line_comment_posted, anchor, str(exc))
                return
            except Exception as exc:  # noqa: BLE001 - say it, never lose it
                self._wx.CallAfter(self._line_comment_posted, anchor, f"Unexpected error: {exc}")
                return
            self._wx.CallAfter(self._line_comment_posted, anchor, "")

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: line comment.

    def _line_comment_posted(self, anchor: LineCommentAnchor, error: str) -> None:
        if not dialog_alive(self.dialog):
            return
        self._posting = False
        self._announce(error or f"GitHub posted your comment on {anchor.describe()}.")

    # -- whole-diff export --------------------------------------------

    def _copy_diff(self, _event: object) -> None:
        wx = self._wx
        text = unified_diff_text(self._diff.files)
        if not wx.TheClipboard.Open():
            self._announce("Could not open the clipboard.")
            return
        try:
            copied = wx.TheClipboard.SetData(wx.TextDataObject(text))
        finally:
            wx.TheClipboard.Close()
        files = len(self._diff.files)
        self._announce(
            f"Copied the diff of {files} file{'s' if files != 1 else ''}."
            if copied
            else "Could not copy the diff."
        )

    def _open_diff_in_app(self, _event: object) -> None:
        text = unified_diff_text(self._diff.files)
        try:
            handle, name = tempfile.mkstemp(prefix=f"pr-{self._diff.number}-", suffix=".diff")
            with os.fdopen(handle, "wb") as stream:
                stream.write(text.encode("utf-8"))
        except OSError as exc:
            self._announce(f"Could not save the diff file: {exc}")
            return
        path = Path(name)
        try:
            if hasattr(os, "startfile"):
                os.startfile(str(path))  # noqa: S606 - our own temp file, opened by association
                opened = True
            else:
                opened = bool(webbrowser.open(path.as_uri()))
        except OSError:
            opened = False
        self._announce(
            f"Opened the diff in your default app. The file is {path}."
            if opened
            else f"No app opened the diff. It is saved at {path}."
        )


__all__ = ["GitHubPullDiffCommentsMixin"]
