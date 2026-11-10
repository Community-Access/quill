"""Paid Memberships Pro member details in the WordPress Workbench."""

from __future__ import annotations

from typing import Any

from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.workbench_rows import WbRow
from quill.ui import wordpress_dialogs as dlg


class WorkbenchMembershipCommands:
    def do_pmpro_memberships(self, _ref: Any, row: WbRow | None) -> None:
        """Read the selected user's current and past Paid Memberships Pro levels."""
        if row is None or row.kind != "user":
            return
        api = self.ctx(row.site).api

        def read_memberships() -> list[dict[str, Any]]:
            from quill.core.wordpress.abilities import list_abilities, run_ability

            ability = next(
                (a for a in list_abilities(api) if a.name == "pmpro/member-memberships-get"), None
            )
            if ability is None or not ability.readonly:
                raise WordPressApiError(
                    f"{row.site} does not expose the Paid Memberships Pro "
                    "member-memberships ability."
                )
            answer = run_ability(
                api,
                ability,
                {"user_id": row.object_id, "include_inactive": True},
            )
            memberships = answer.get("memberships", []) if isinstance(answer, dict) else []
            return [item for item in memberships if isinstance(item, dict)]

        def done(memberships: list[dict[str, Any]]) -> None:
            lines = []
            for membership in memberships:
                name = str(
                    membership.get("name")
                    or membership.get("membership_name")
                    or f"Level {membership.get('id', '')}"
                )
                status = str(membership.get("status") or "unknown").replace("_", " ")
                start = str(membership.get("startdate") or "")
                end = str(membership.get("enddate") or "")
                dates = ", ".join(
                    value
                    for value in (f"started {start}" if start else "", f"ends {end}" if end else "")
                    if value
                )
                lines.append(f"{name}: {status}" + (f", {dates}" if dates else ""))
            text = "\n".join(lines) or "No current or past memberships were returned."
            dlg.show_report(
                self.parent,
                self.show_modal,
                title=f"Paid Memberships Pro - {row.title}",
                text=text,
                help_text=(
                    "Current and past membership levels returned by the site. Payment card "
                    "details are not included."
                ),
            )

        self.background(f"reading memberships for {row.title}", read_memberships, done)
