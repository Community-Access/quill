"""The Gravity Forms editor's Other Notifications and Confirmations window (complete.md 2.3).

A list of the form's other notifications and confirmations
(:mod:`quill.core.wordpress.gravity_messages`), with Add Notification, Add
Confirmation, Change, Turn On or Off and Remove. It changes the editor's copy
of the form, so nothing is sent until the editor's Review and Save shows each
change and you agree; Cancel on the editor throws them all away.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.wordpress import gravity_messages as gm
from quill.core.wordpress.block_catalog import Field
from quill.ui import wordpress_dialogs as dlg
from quill.ui.wordpress_block_dialogs import ask_fields

__all__ = ["edit_messages"]

_TO_HELP = (
    "Who gets this email: addresses with a comma between, {admin_email} for the site's "
    "admin, or a field's merge tag such as {Email:3}."
)
_BODY_HELP = "The email's text. {all_fields} lists every answer."


def edit_messages(
    parent: Any,
    show_modal: dlg.ShowModal,
    form: dict[str, Any],
    announce: Callable[[str], None],
) -> None:
    """Show the window over *form*, which it changes in place."""

    def rows() -> list[str]:
        return [gm.spoken(m) for m in gm.others(form)]

    def at(index: int | None) -> gm.Message | None:
        found = gm.others(form)
        return found[index] if index is not None and 0 <= index < len(found) else None

    def ask(title: str, fields: list[Field]) -> dict[str, Any] | None:
        return ask_fields(
            parent,
            show_modal,
            title=title,
            purpose="Nothing is sent until the form's Review and Save.",
            fields=fields,
        )

    def notification_fields(record: dict[str, Any]) -> list[Field]:
        return [
            Field("name", "Name", "text", "What this email is called in Gravity Forms.",
                  record.get("name", "")),
            Field("to", "Send to", "text", _TO_HELP, record.get("to", "")),
            Field("subject", "Subject", "text", "The email's subject line.",
                  record.get("subject", "")),
            Field("message", "Message", "multiline", _BODY_HELP,
                  record.get("message", "{all_fields}")),
        ]  # fmt: skip

    def confirmation_fields(record: dict[str, Any]) -> list[Field]:
        return [
            Field("name", "Name", "text", "What this confirmation is called in Gravity Forms.",
                  record.get("name", "")),
            Field("message", "Message", "multiline", "What people read after sending the form.",
                  record.get("message", "")),
        ]  # fmt: skip

    def add_notification(_index: int | None) -> object:
        answers = ask("Add Notification", notification_fields({}))
        if not answers or not str(answers.get("name", "")).strip():
            return None
        made = gm.add_notification(
            form,
            str(answers["name"]).strip(),
            str(answers.get("to", "")).strip() or "{admin_email}",
            str(answers.get("subject", "")).strip(),
            str(answers.get("message", "")),
        )
        announce(f"Added the notification {made.name}. Review and Save sends it.")
        return rows()

    def add_confirmation(_index: int | None) -> object:
        answers = ask("Add Confirmation", confirmation_fields({}))
        if not answers or not str(answers.get("name", "")).strip():
            return None
        made = gm.add_confirmation(
            form, str(answers["name"]).strip(), str(answers.get("message", ""))
        )
        announce(
            f"Added the confirmation {made.name}. Gravity Forms shows it when its logic, set "
            "in Gravity Forms, matches; Review and Save sends it."
        )
        return rows()

    def change(index: int | None) -> object:
        message = at(index)
        if message is None:
            return None
        if not message.simple:
            announce(
                f"{message.name} uses routing, logic or a page; change it in Gravity Forms. "
                "QUILL can turn it on or off, or remove it, and keeps the rest."
            )
            return None
        fields = (
            notification_fields(message.record)
            if message.kind == "notifications"
            else confirmation_fields(message.record)
        )
        answers = ask(f"Change {message.name}", fields)
        if not answers:
            return None
        changed = gm.change(message, {k: str(v) for k, v in answers.items()})
        announce(
            f"Changed {', '.join(changed)} on {message.name}." if changed else "Nothing changed."
        )
        return rows()

    def toggle(index: int | None) -> object:
        message = at(index)
        if message is None:
            return None
        on = gm.toggle(message)
        announce(f"{message.name} is {'on' if on else 'off'}. Review and Save sends it.")
        return rows()

    def remove(index: int | None) -> object:
        message = at(index)
        if message is None:
            return None
        if not dlg.confirm(
            parent,
            show_modal,
            title="Remove",
            message=f"Remove {message.name} from the form? Review and Save sends it.",
            yes_label="Remove",
        ):
            return None
        gm.remove(form, message)
        announce(f"Removed {message.name}.")
        return rows()

    window = dlg.show_list_window(
        parent,
        show_modal,
        title="Other Notifications and Confirmations",
        purpose=(
            "The form's notifications other than the Admin Notification, and its confirmations "
            "other than the default, which the editor itself changes."
        ),
        list_label="&Notifications and confirmations:",
        list_help="Each one's name, whether it is an email or a confirmation, and if it is on.",
        rows=rows(),
        actions=[
            dlg.Action(
                "Add Notifica&tion...",
                "A new email when the form is sent.",
                add_notification,
                needs_row=False,
            ),
            dlg.Action(
                "Add Con&firmation...",
                "A new message after sending.",
                add_confirmation,
                needs_row=False,
            ),
            dlg.Action(
                "&Change...", "Change the selected one's name, address, subject or text.", change
            ),
            dlg.Action(
                "Turn On or &Off",
                "Turn the selected one on or off.",
                toggle,
                label_for=lambda i: (
                    "Turn &Off"
                    if (m := at(i)) is not None
                    and m.record.get("isActive", True) not in (False, 0, "0")
                    else "Turn &On"
                ),
            ),
            dlg.Action("&Remove...", "Take the selected one out of the form.", remove),
        ],
    )
    window.Destroy()
