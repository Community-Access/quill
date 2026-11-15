"""Gravity Forms field conversion commands for the WordPress Workbench."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.workbench_forms import (
    GRAVITY_FIELD_TYPES,
    gravity_replacement_problems,
    plan_gravity_field_type_change,
)
from quill.core.wordpress.workbench_gravity import gravity_can
from quill.core.wordpress.workbench_permissions import tier_allowed
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.actions import Tier
from quill.core.workbench.history import Change
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_workbench_dialogs as wdlg


class WorkbenchGravityCommands:
    def gravity_conversion_refusal(self, row: WbRow) -> str:
        """Why Change a Field Type may not run on *row* ("" when it may).

        Full Workbench access, and Gravity Forms' own gravityforms_create_form, which
        it grants to anyone with gform_full_access; the site still checks again.
        """
        if row.kind != "gravity_form" or row.subkind != "gravity":
            return "This is not a Gravity Forms form. QAF fields are changed in Form Outline."
        if not tier_allowed(Tier.WRITE, self.access_for(row.site)):
            return self._access_sentence(row.site)
        account = self.account_for(row.site)
        if gravity_can(account, "gravityforms_create_form"):
            return ""
        return (
            "Changing a form's fields needs the Gravity Forms permission gravityforms create "
            f"form. You are {account.role_name} on {row.site}."
        )

    def do_change_gravity_field_type(self, _ref: Any, row: WbRow | None) -> None:
        """Read, preview and update one supported Gravity Forms field."""
        if row is None or row.kind != "gravity_form" or row.subkind != "gravity":
            return
        refusal = self.refusal_for("wordpress.workbench.change_gravity_field_type", row)
        if refusal:
            self.say(refusal)
            return
        # A form row's own title is its plugin's name; the form's is in its "form" cell.
        row = replace(row, cells={**row.cells, "title": row.cell("form") or row.title})
        api = self.ctx(row.site).api

        def choose_field(form: Any) -> None:
            if not isinstance(form, dict) or not isinstance(form.get("fields"), list):
                self.say(f"Gravity Forms did not return the fields for {row.title} on {row.site}.")
                return
            fields = [
                field
                for field in form["fields"]
                if isinstance(field, dict) and str(field.get("type", "")) in GRAVITY_FIELD_TYPES
            ]
            if not fields:
                self.say(f"{row.title} has no fields QUILL can convert.")
                return
            field_rows = [
                f"{field.get('id', '?')}: {field.get('label') or 'Untitled'} "
                f"({GRAVITY_FIELD_TYPES[str(field['type'])]})"
                for field in fields
            ]
            picked_field = dlg.ask_choice(
                self.parent,
                self.show_modal,
                title=f"Change a Field Type - {row.title}",
                prompt="&Field:",
                rows=field_rows,
                help_text=(
                    "Choose a text, email, number or choice field in this Gravity Forms form."
                ),
            )
            if picked_field is None:
                return
            field = fields[picked_field]
            target_types = list(GRAVITY_FIELD_TYPES)
            target_rows = [f"{label} ({kind})" for kind, label in GRAVITY_FIELD_TYPES.items()]
            picked_type = dlg.ask_choice(
                self.parent,
                self.show_modal,
                title="Change Field Type",
                prompt="&New control:",
                rows=target_rows,
                initial=target_types.index(str(field["type"])),
                help_text=(
                    "The field keeps its shared settings. Choice controls keep or create their "
                    "choices."
                ),
            )
            if picked_type is None:
                return
            try:
                plan = plan_gravity_field_type_change(
                    form, str(field.get("id", "")), target_types[picked_type]
                )
            except ValueError as exc:
                self.say(str(exc))
                return
            if plan.old_type == plan.new_type:
                self.say("The field already uses that control.")
                return
            lines = [f"Site: {row.site}", f"Form: {row.title}", *plan.review_lines()]
            if not wdlg.ask_preview(
                self.parent,
                self.show_modal,
                title="Update Gravity Forms Field",
                summary=plan.summary,
                lines=lines,
                yes="Update Form",
            ):
                return

            original = dict(form)
            updated = plan.form

            def save() -> Any:
                current = api.get(row.route)
                if not isinstance(current, dict) or current != original:
                    raise WordPressApiError(
                        f"{row.title} on {row.site} changed while you reviewed the conversion. "
                        "Reopen the form and review the current fields."
                    )
                api.request("PUT", row.route, json_body=updated)
                # Gravity Forms replaces the whole form: read it back and check it.
                stored = api.get(row.route)
                return stored, gravity_replacement_problems(plan, stored)

            def saved(answer: tuple[Any, list[str]]) -> None:
                stored, problems = answer
                if not isinstance(stored, dict):
                    stored = updated
                said = f"Changed {plan.field_label} in {row.title} on {row.site}."
                if problems:
                    said = (
                        f"{row.title} on {row.site} was saved, but it reads back differently: "
                        + " ".join(problems)
                        + " Ctrl+Z puts the form back as it was."
                    )
                expected = {"form": stored}

                def put_back(body: Any, message: str) -> str:
                    current = api.get(row.route)
                    if not isinstance(current, dict) or current != expected["form"]:
                        raise WordPressApiError(
                            f"{row.title} on {row.site} changed since this conversion. "
                            "QUILL did not replace the newer form."
                        )
                    answer = api.request("PUT", row.route, json_body=body).payload
                    expected["form"] = answer if isinstance(answer, dict) else body
                    return message

                self.history.record(
                    Change(
                        f"{row.site}: {row.title}, field {plan.field_id}",
                        said,
                        undo=lambda: put_back(
                            original, f"Restored {plan.field_label} in {row.title}."
                        ),
                        redo=lambda: put_back(
                            updated, f"Changed {plan.field_label} in {row.title}."
                        ),
                    )
                )
                self.say(said)
                self.refresh()

            self.background("updating a Gravity Forms field", save, saved)

        self.background(
            f"reading {row.title}",
            lambda: api.get(row.route),
            choose_field,
        )
