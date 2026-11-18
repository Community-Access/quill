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
from typing import Any

from quill.core.github.diff_lines import (
    LINE_MARK_LABELS,
    LINE_MARK_STYLES,
    SYMBOLS_NOTE,
    DiffLine,
    LineCommentAnchor,
    anchor_for,
    change_runs,
    changed_only,
    describe_change,
    is_symbol_style,
    line_sound,
    lines_for_range,
    parse_diff_lines,
    parse_range,
    reading_order,
    render_line,
    unified_diff_text,
)
from quill.core.github.items_errors import GitHubItemsError
from quill.core.github.line_comment_drafts import LineCommentDraftStore
from quill.core.github.review_errors import GitHubReviewError
from quill.core.github.review_preferences import load_line_marks, save_line_marks
from quill.ui.dialog_contract import apply_listbox_activation, dialog_alive, show_modal_dialog
from quill.ui.github_items_view import pull_diff_file_label


class GitHubPullDiffCommentsMixin:
    """Build and drive the patch-line list and its comment and export buttons."""

    def _build_line_controls(self, panel: object, root: object) -> None:
        wx = self._wx
        self._line_style = load_line_marks()
        self._patch_lines: tuple[DiffLine, ...] = ()
        self._visible: tuple[int, ...] = ()
        self._posting = False
        self._pending_store = LineCommentDraftStore.load(getattr(self._provider, "token", None))

        marks_row = wx.BoxSizer(wx.HORIZONTAL)
        marks_label = wx.StaticText(panel, label="Line &marks:")
        self._marks_choice = wx.Choice(
            panel, choices=[LINE_MARK_LABELS[style] for style in LINE_MARK_STYLES]
        )
        self._marks_choice.SetName("Line marks")
        self._marks_choice.SetHelpText(
            "How patch lines are marked, in Kelly Ford's four styles: words (Added line), "
            "short words (Add), diff symbols (plus, minus, equals), or diff symbols with "
            "each changed line read old then new. Symbols need your screen reader to read "
            "punctuation. The same choice marks every difference in QUILL."
        )
        self._marks_choice.SetSelection(LINE_MARK_STYLES.index(self._line_style))
        marks_row.Add(marks_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        marks_row.Add(self._marks_choice, 0)
        self._changed_only = wx.CheckBox(panel, label="C&hanged Lines Only")
        self._changed_only.SetName("Changed lines only")
        self._changed_only.SetHelpText(
            "Leave out the unchanged lines around each change, so the arrows move from "
            "change to change. Hunk headings stay, so each change still says where it is."
        )
        marks_row.Add(self._changed_only, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 12)
        self._hide_ws = wx.CheckBox(panel, label="Hide &Whitespace Changes")
        self._hide_ws.SetName("Hide whitespace changes")
        self._hide_ws.SetHelpText(
            "Leave out changed lines that differ only in spaces, tabs or blank lines, such "
            "as a reindent, so what is left is what really changed."
        )
        marks_row.Add(self._hide_ws, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 12)
        self._commit_btn = wx.Button(panel, label="Choose Commi&t...")
        self._commit_btn.SetHelpText(
            "Review one commit of the pull request at a time, or go back to all of them."
        )
        marks_row.Add(self._commit_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 12)
        self._whole_diff = self._diff
        root.Add(marks_row, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self._marks_note = wx.StaticText(
            panel, label=SYMBOLS_NOTE if is_symbol_style(self._line_style) else ""
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
            "run of lines. Enter comments on the selected lines. Alt+N and Alt+P, or F8 and "
            "Shift+F8, move to the next and previous change and say which words changed."
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
        self._changed_only.Bind(wx.EVT_CHECKBOX, self._on_changed_only)
        self._hide_ws.Bind(wx.EVT_CHECKBOX, self._on_hide_whitespace)
        self._commit_btn.Bind(wx.EVT_BUTTON, lambda _event: self._choose_commit())
        self._patch_list.Bind(wx.EVT_LISTBOX, self._on_patch_line)
        self._patch_list.Bind(wx.EVT_KEY_DOWN, self._on_patch_key)
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
        before = {
            self._visible[position]
            for position in self._patch_list.GetSelections()
            if 0 <= position < len(self._visible)
        }
        if self._changed_only.GetValue():
            self._visible = changed_only(self._patch_lines)
        else:
            self._visible = tuple(range(len(self._patch_lines)))
        if self._hide_ws.GetValue():
            from quill.core.github.commit_review import whitespace_only

            gone = whitespace_only(self._patch_lines)
            self._visible = tuple(index for index in self._visible if index not in gone)
        shown = set(self._visible)
        kept = [line for index, line in enumerate(self._patch_lines) if index in shown]
        where = [index for index in range(len(self._patch_lines)) if index in shown]
        order = reading_order(kept, self._line_style)
        self._visible = tuple(where[position] for position, _paired in order)
        rows = [
            render_line(kept[position], self._line_style, paired=paired)
            for position, paired in order
        ]
        self._patch_list.Set(rows or ["GitHub sent no patch lines for this file."])
        for position, index in enumerate(self._visible):
            if index in before:
                self._patch_list.SetSelection(position)

    def _on_changed_only(self, _event: object) -> None:
        self._render_patch_lines()
        if self._changed_only.GetValue() and self._patch_lines:
            changes = sum(1 for line in self._patch_lines if line.kind in ("added", "removed"))
            self._announce(
                f"{changes} changed line{'s' if changes != 1 else ''}, without the "
                f"{len(self._patch_lines) - len(self._visible)} unchanged around them."
            )

    def _on_hide_whitespace(self, _event: object) -> None:
        from quill.core.github.commit_review import whitespace_only

        self._render_patch_lines()
        if self._hide_ws.GetValue():
            gone = len(whitespace_only(self._patch_lines))
            self._announce(
                f"{gone} changed line{'s' if gone != 1 else ''} that only change whitespace "
                "left out."
                if gone
                else "No change here is only whitespace."
            )

    # -- one commit at a time ------------------------------------------------

    def _api(self) -> object:
        from quill.core.github.workbench_api import TokenApi

        return TokenApi(getattr(self._provider, "token", None))

    def _off_thread(self, work: object, done: object) -> None:
        wx = self._wx

        def worker() -> None:
            try:
                result = work()  # type: ignore[operator]
            except Exception as exc:  # noqa: BLE001 - said, never raised into wx
                reason = str(exc.args[0]) if exc.args else str(exc)
                wx.CallAfter(self._announce, f"Could not read the commits: {reason}")
                return
            wx.CallAfter(done, result)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: commit reads.

    def _choose_commit(self) -> None:
        from quill.core.github.commit_review import pull_commits

        api, repo, number = self._api(), self._repo, self._whole_diff.number
        self._off_thread(lambda: pull_commits(api, repo, number), self._commits_listed)

    def _commits_listed(self, commits: list[object]) -> None:
        if not dialog_alive(self.dialog):
            return
        wx = self._wx
        whole = f"All {len(commits)} commits: the whole pull request"
        labels = [whole] + [str(getattr(c, "label", "")) for c in commits]
        with wx.SingleChoiceDialog(
            self.dialog, "Review which commit?", "Choose Commit", labels
        ) as box:
            box.SetName("Choose commit")
            if show_modal_dialog(box, "Choose Commit", announce=self._announce) != wx.ID_OK:
                return
            picked = box.GetSelection()
        if picked <= 0:
            self._switch_diff(self._whole_diff, "The whole pull request.")
            return
        from quill.core.github.commit_review import commit_diff

        sha = str(getattr(commits[picked - 1], "sha", ""))
        api, repo, whole_diff = self._api(), self._repo, self._whole_diff
        self._off_thread(
            lambda: commit_diff(api, repo, whole_diff.number, whole_diff.title, sha),
            lambda diff: self._switch_diff(diff, f"Commit {sha[:7]}."),
        )

    def _switch_diff(self, diff: object, said: str) -> None:
        if not dialog_alive(self.dialog):
            return
        self._diff = diff
        files = getattr(diff, "files", ())
        self._files.Set([pull_diff_file_label(f) for f in files])
        count = len(files)
        head = getattr(diff, "head_ref", "") or "head"
        base = getattr(diff, "base_ref", "") or "base"
        noun = "file" if count == 1 else "files"
        self._header.SetLabel(f"{count} changed {noun}, {head} into {base}")
        self._announce(f"{said} {count} changed file{'s' if count != 1 else ''}.")
        if files:
            self._files.SetSelection(0)
            self._on_select(None)

    def _on_patch_key(self, event: Any) -> None:
        """Next and previous change: Alt+N and Alt+P, as in Kelly Ford's
        GHManage, and F8 and Shift+F8, as in Compare Files."""
        import wx

        code = event.GetKeyCode()
        alt, shift, ctrl = event.AltDown(), event.ShiftDown(), event.ControlDown()
        step = 0
        if code == wx.WXK_F8 and not alt and not ctrl:
            step = -1 if shift else 1
        elif alt and not shift and not ctrl and code in (ord("N"), ord("P")):
            step = 1 if code == ord("N") else -1
        if not step:
            event.Skip()
            return
        self._step_change(step)

    def _step_change(self, step: int) -> None:
        """Select the first line of the next (or previous) change and say
        "Change 2 of 5", where it is, and which words changed."""
        shown = {index: position for position, index in enumerate(self._visible)}
        runs = [
            (run, min(shown[i] for i in range(run[0], run[1] + 1) if i in shown))
            for run in change_runs(self._patch_lines)
            if any(i in shown for i in range(run[0], run[1] + 1))
        ]
        if not runs:
            self._announce("No changes in this file.")
            return
        selected = self._patch_list.GetSelections()
        here = selected[0] if selected else -1
        if step > 0:
            ahead = [item for item in runs if item[1] > here]
            target = ahead[0] if ahead else None
        else:
            behind = [item for item in runs if item[1] < here]
            target = behind[-1] if behind else None
        if target is None:
            self._announce("No more changes." if step > 0 else "No earlier changes.")
            return
        run, position = target
        for chosen in selected:
            self._patch_list.Deselect(chosen)
        self._patch_list.SetSelection(position)
        self._patch_list.EnsureVisible(position)
        self._update_comment_buttons()
        number = [item[0] for item in runs].index(run) + 1
        self._announce(describe_change(self._patch_lines, run, number, len(runs)))

    def _on_patch_line(self, _event: object) -> None:
        """Arriving on an added or removed line plays its sound (Sound Scheme, optional)."""
        chosen = self._selected_patch_lines()
        if len(chosen) != 1:
            return
        if not line_sound(chosen[0]):
            return
        added = chosen[0].kind == "added"
        try:
            from quill.core.sound_events import SoundEvent
            from quill.ui import sound_manager

            sound_manager.post_sound(
                SoundEvent.DIFF_LINE_ADDED if added else SoundEvent.DIFF_LINE_REMOVED
            )
        except Exception:  # noqa: BLE001 - a sound never interrupts reading
            pass

    def _on_marks_changed(self, _event: object) -> None:
        index = self._marks_choice.GetSelection()
        if not 0 <= index < len(LINE_MARK_STYLES):
            return
        self._line_style = LINE_MARK_STYLES[index]
        saved = save_line_marks(self._line_style)
        symbols = is_symbol_style(self._line_style)
        self._marks_note.SetLabel(SYMBOLS_NOTE if symbols else "")
        self._render_patch_lines()
        if symbols:
            self._announce(SYMBOLS_NOTE)
        if not saved:
            self._announce("Could not save the line marks choice; it lasts until you close.")

    def _selected_patch_lines(self) -> list[DiffLine]:
        return [
            self._patch_lines[self._visible[position]]
            for position in self._patch_list.GetSelections()
            if 0 <= position < len(self._visible)
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
            provider=self._provider,
            repository=self._repo,
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
