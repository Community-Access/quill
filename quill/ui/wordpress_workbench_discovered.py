"""More from This Site, the Content Model and Abilities in the WordPress Workbench (W5).

A mixin on :class:`quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`:

- a namespace row opens its node, which lists the namespace's routes with
  their methods and where the Workbench reaches each
  (:mod:`quill.core.wordpress.workbench_coverage`);
- a route row reads the route (a GET, shown as text; the REST Console reads
  routes that need values) or shows what it accepts (its ``OPTIONS`` schema);
- an ability row runs the ability: its input schema is its sheet, the
  preview names the site, what it will do and each input, and nothing is sent
  before Run. A read-only ability is a read; any other needs Full access.

Every request runs through ``self.background``; results are shown in a
read-only report, never spoken whole (GATE-13 says only the outcome).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from quill.core.wordpress.abilities import ability_from, result_text, run_ability
from quill.core.wordpress.workbench_discovered import (
    ability_input,
    ability_preview,
    ability_sheet,
    ability_values,
)
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.wordpress.workbench_tree import DYNAMIC_NAMESPACE
from quill.core.workbench.actions import Tier
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_workbench_dialogs as wdlg

__all__ = ["WorkbenchDiscoveredCommands"]


def _pretty(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


class WorkbenchDiscoveredCommands:
    """Namespaces, routes, the content model and abilities."""

    frame: Any
    parent: Any
    say: Callable[[str], None]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    show_modal: Callable[[Any, str], int]
    write_refusal: Callable[[WbRow, Tier], str]

    def namespace_children(self, site: str) -> list[tuple[str, str]]:
        from quill.ui.wordpress_workbench_window import SEP

        ctx = getattr(self, "_contexts", {}).get(site)
        info = ctx.info if ctx is not None else None
        return [(f"{site}{SEP}{n}", n) for n in (info.namespaces if info else ())]

    def do_open_namespace(self, _ref: Any, row: WbRow | None) -> None:
        from quill.ui.wordpress_workbench_window import SEP
        from quill.ui.workbench_frame import NodeRef

        if row is None:
            return
        if self.frame.select(NodeRef("site", DYNAMIC_NAMESPACE, f"{row.site}{SEP}{row.key}")):
            self.frame.tree.SetFocus()
        else:
            self.say("Its node is still being added. Press F5 in a moment.")

    def _report(self, title: str, text: str, help_text: str) -> None:
        dlg.show_report(self.parent, self.show_modal, title=title, text=text, help_text=help_text)

    def do_read_route(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "route":
            return
        if "(?P<" in row.key:
            self.say(
                "This route needs a value in its address, such as a number. Tools > REST "
                "Console reads it with the value filled in."
            )
            return
        methods = row.raw.get("methods") or []
        if methods and "GET" not in methods:
            self.say(f"{row.key} only takes {', '.join(methods)}, so there is nothing to read.")
            return
        api = self.ctx(row.site).api
        self.background(
            f"reading {row.key}",
            lambda: api.get(row.route),
            lambda answer: self._report(
                f"{row.key} - {row.site}",
                _pretty(answer),
                "What the site answered, as text. Tools > REST Console shows it as a tree.",
            ),
        )

    def do_route_schema(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "route":
            return
        api = self.ctx(row.site).api

        def work() -> str:
            payload = api.request("OPTIONS", row.route).payload
            if not isinstance(payload, dict):
                return "The site did not describe this route."
            lines: list[str] = []
            for endpoint in payload.get("endpoints") or []:
                if not isinstance(endpoint, dict):
                    continue
                methods = ", ".join(endpoint.get("methods") or [])
                lines.append(f"{methods}:")
                for name, spec in (endpoint.get("args") or {}).items():
                    spec = spec if isinstance(spec, dict) else {}
                    kind = spec.get("type", "any")
                    need = ", required" if spec.get("required") else ""
                    said = str(spec.get("description") or "").strip()
                    lines.append(f"  {name} ({kind}{need}){': ' + said if said else ''}")
            schema = payload.get("schema")
            if isinstance(schema, dict) and isinstance(schema.get("properties"), dict):
                lines.append("Fields:")
                lines += [f"  {name}" for name in sorted(schema["properties"])]
            return "\n".join(lines) or "The route takes nothing."

        self.background(
            f"asking about {row.key}",
            work,
            lambda text: self._report(
                f"What {row.key} Accepts",
                text,
                "Each method's arguments and the route's fields, as the site describes them.",
            ),
        )

    def do_run_ability(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "ability":
            return
        api = self.ctx(row.site).api

        def got(raw: Any) -> None:
            ability = ability_from(raw)
            if ability is None:
                self.say("The site did not describe this ability.")
                return
            if not ability.readonly:
                reason = self.write_refusal(row, Tier.WRITE)
                if reason:
                    self.say(reason)
                    return
            self._ability_sheet(row, api, ability)

        self.background(
            f"reading {row.title}",
            lambda: api.get(f"wp-abilities/v1/abilities/{row.key}"),
            got,
        )

    def _ability_sheet(self, row: WbRow, api: Any, ability: Any) -> None:
        from quill.ui.workbench_sheet_editor import WorkbenchSheetEditor

        sheet = ability_sheet(ability)
        pending: dict[str, Any] = {}

        def keep(state: Any) -> None:
            pending.update({change.key: change.after for change in state.pending()})

        editor = WorkbenchSheetEditor(
            self.parent,
            sheet,
            ability_values(ability),
            title=f"Run {ability.label} - {row.site}",
            copy_text=self.frame.copy_text,
            on_save=keep,
        )
        if editor.show() != self.frame._wx.ID_OK and not pending:
            return
        given = ability_input(ability, pending)
        summary, lines = ability_preview(row.site, ability, given)
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title=f"Run {ability.label}",
            summary=summary,
            lines=lines,
            yes="Run",
        ):
            return
        self.background(
            f"running {ability.label}",
            lambda: run_ability(api, ability, given),
            lambda result: self._report(
                f"{ability.label} - {row.site}",
                result_text(result),
                "What the ability answered.",
            ),
        )
