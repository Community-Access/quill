"""Edit actions for the GitHub Projects list/detail dialog."""

from __future__ import annotations

import re
import threading

from quill.core.github.projects import (
    GitHubProjectsError,
    resolve_issue_reference,
    update_issue_relationship,
    update_project_field,
)
from quill.ui.dialog_contract import dialog_alive, show_modal_dialog

_ISSUE_NUMBER = re.compile(
    r"^(?P<repository>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)#(?P<number>[1-9][0-9]*)$"
)


class GitHubProjectsActionsMixin:
    """Write actions shared by issue fields, blockers, and sub-issues."""

    def _edit_field(self) -> None:
        item, board = self._selected(), self._board
        if item is None or board is None:
            return
        fields = [
            field
            for field in board.fields
            if field.kind
            in {"single_select", "multi_select", "text", "number", "date", "iteration"}
        ]
        if not fields:
            self._announce("This Project has no editable fields supported by QUILL.")
            return
        selected = self._choose(
            "Project field:", "Edit Project Field", [field.name for field in fields]
        )
        if selected is None:
            return
        field = fields[selected]
        current = dict(item.values).get(field.name, "")
        if field.kind in {"single_select", "iteration"}:
            choices = field.options if field.kind == "single_select" else field.iterations
            choice = self._choose(
                field.name, "Edit Project Field", [label for _key, label in choices]
            )
            if choice is None:
                return
            value = choices[choice][0]
            shown_value = choices[choice][1]
        elif field.kind == "multi_select":
            wx = self._wx
            choices = field.options
            with wx.MultiChoiceDialog(
                self.dialog,
                f"Choose values for {field.name}:",
                "Edit Project Field",
                [label for _key, label in choices],
            ) as dialog:
                selected_ids = dict(item.selected_option_ids).get(field.name, ())
                dialog.SetSelections([
                    index
                    for index, (option_id, _label) in enumerate(choices)
                    if option_id in selected_ids
                ])
                if (
                    show_modal_dialog(dialog, "Edit Project Field", announce=self._announce)
                    != wx.ID_OK
                ):
                    return
                selected = dialog.GetSelections()
            value = tuple(choices[index][0] for index in selected)
            shown_value = ", ".join(choices[index][1] for index in selected) or "(none)"
        else:
            value = self._prompt(f"New value for {field.name}:", "Edit Project Field", current)
            if value is None:
                return
            shown_value = value
        if not self._confirm(
            f"Set {field.name} to {shown_value!r} for {item.title} in {board.project.title}?",
            "Confirm Project Field Update",
        ):
            return
        self._run_write(
            lambda: update_project_field(
                self._token, board.project.node_id, item.node_id, field, value
            ),
            f"Updated {field.name} for {item.title}.",
        )

    def _add_relation(self, relation: str) -> None:
        item = self._selected()
        if item is None:
            return
        reference = self._prompt(
            "Issue to add (GitHub URL or owner/repo#number):",
            "Add Issue Relationship",
        )
        parsed = _parse_issue_reference(reference or "")
        if parsed is None:
            if reference:
                self._show_error(
                    "Enter an issue URL or owner/repo#number.", "Add Issue Relationship"
                )
            return
        repository, number = parsed
        relation_text = "blocker" if relation == "blocked_by" else "sub-issue"
        if not self._confirm(
            f"Add {repository}#{number} as a {relation_text} for "
            f"{item.repository}#{item.number} {item.title}?",
            "Confirm Issue Relationship",
        ):
            return

        def action() -> None:
            related = resolve_issue_reference(self._token, repository, number)
            update_issue_relationship(
                self._token,
                relation=relation,
                add=True,
                issue_id=item.content_id,
                related_issue_id=related.node_id,
            )

        self._run_write(action, f"Added {relation_text} {repository}#{number}.")

    def _remove_relation(self, relation: str) -> None:
        item = self._selected()
        if item is None:
            return
        links = item.blocked_by if relation == "blocked_by" else item.sub_issues
        if not links:
            return
        selected = self._choose(
            "Issue relationship to remove:",
            "Remove Issue Relationship",
            [f"{link.repository}#{link.number}: {link.title}" for link in links],
        )
        if selected is None:
            return
        link = links[selected]
        label = "blocker" if relation == "blocked_by" else "sub-issue"
        if not self._confirm(
            f"Remove {link.repository}#{link.number} as a {label} for {item.title}?",
            "Confirm Issue Relationship",
        ):
            return
        self._run_write(
            lambda: update_issue_relationship(
                self._token,
                relation=relation,
                add=False,
                issue_id=item.content_id,
                related_issue_id=link.node_id,
            ),
            f"Removed {label} {link.repository}#{link.number}.",
        )

    def _run_write(self, action, success: str) -> None:
        if self._write_in_flight:
            self._announce("Wait for the current project action to finish.")
            return
        self._write_in_flight = True
        self._write_token += 1
        token = self._write_token
        self._actions_btn.Enable(False)
        self._next_btn.Enable(False)
        self._status.SetLabel("Updating GitHub Project...")

        def worker() -> None:
            try:
                action()
                self._wx.CallAfter(self._write_done, token, success)
            except GitHubProjectsError as exc:
                self._wx.CallAfter(self._write_done, token, f"Project action failed: {exc}")
            except Exception as exc:  # noqa: BLE001 - no write failure may disappear
                self._wx.CallAfter(self._write_done, token, f"Project action failed: {exc}")

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: confirmed project write.

    def _write_done(self, token: int, message: str) -> None:
        if token != self._write_token or not dialog_alive(self.dialog):
            return
        self._write_in_flight = False
        self._status.SetLabel(message)
        self._announce(message)
        self._load_board(None)

    def _choose(self, prompt: str, title: str, choices: list[str]) -> int | None:
        wx = self._wx
        if not choices:
            return None
        with wx.SingleChoiceDialog(self.dialog, prompt, title, choices) as dialog:
            if show_modal_dialog(dialog, title, announce=self._announce) != wx.ID_OK:
                return None
            return dialog.GetSelection()

    def _prompt(self, message: str, title: str, value: str = "") -> str | None:
        wx = self._wx
        with wx.TextEntryDialog(self.dialog, message, title, value) as dialog:
            if show_modal_dialog(dialog, title, announce=self._announce) != wx.ID_OK:
                return None
            return dialog.GetValue().strip()

    def _confirm(self, message: str, title: str) -> bool:
        wx = self._wx
        with wx.MessageDialog(self.dialog, message, title, wx.YES_NO | wx.NO_DEFAULT) as dialog:
            return show_modal_dialog(dialog, title, announce=self._announce) == wx.ID_YES

    def _show_error(self, message: str, title: str) -> None:
        wx = self._wx
        with wx.MessageDialog(self.dialog, message, title, wx.OK | wx.ICON_ERROR) as dialog:
            show_modal_dialog(dialog, title, announce=self._announce)


def _parse_issue_reference(value: str) -> tuple[str, int] | None:
    match = _ISSUE_NUMBER.fullmatch(value.strip())
    if match:
        return match.group("repository"), int(match.group("number"))
    from quill.core.github.references import GitHubReferenceError, parse_github_reference

    try:
        reference = parse_github_reference(value)
    except GitHubReferenceError:
        return None
    if (
        reference.host not in {"github.com", "www.github.com"}
        or reference.kind != "issue"
        or reference.number is None
    ):
        return None
    return reference.repository, reference.number


__all__ = ["GitHubProjectsActionsMixin"]
