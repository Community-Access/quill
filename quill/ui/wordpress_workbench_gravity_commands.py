"""Gravity Forms field conversion commands for the WordPress Workbench."""

from __future__ import annotations

from typing import Any

from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.workbench_forms import (
    GRAVITY_FIELD_TYPES,
    plan_gravity_field_type_change,
)
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.history import Change
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_workbench_dialogs as wdlg


class WorkbenchGravityCommands:
    def do_change_gravity_field_type(self, _ref: Any, row: WbRow | None) -> None:
        """Read, preview and update one supported Gravity Forms field."""
        if row is None or row.kind != "gravity_form" or row.subkind != "gravity":
            return
        refusal = self.refusal_for("wordpress.workbench.change_gravity_field_type", row)
        if refusal:
            self.say(refusal)
            return
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
                answer = api.request("PUT", row.route, json_body=updated).payload
                return answer if isinstance(answer, dict) else updated

            def saved(stored: Any) -> None:
                said = f"Changed {plan.field_label} in {row.title} on {row.site}."
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
