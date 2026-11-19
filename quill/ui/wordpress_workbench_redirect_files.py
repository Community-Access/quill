"""Redirects > Groups, Export Redirects... and Import Redirects... (complete.md 2.3).

The Workbench side of :mod:`quill.core.wordpress.workbench_redirect_files`. A
group is made, renamed or turned on and off after a preview, and deleted only
after its name is typed, because its redirects go with it. Export writes the
redirects read for the list to a file here; Import reads a file here,
previews every redirect it would add and every line it cannot use, and adds
them one at a time, then says how many went in.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.wordpress import workbench_redirect_files as files
from quill.core.wordpress.workbench_redirects import edit_body, read_groups, read_pages
from quill.core.wordpress.workbench_rows import WbRow
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_workbench_dialogs as wdlg

__all__ = ["WorkbenchRedirectFiles"]


def _rename_back(api: Any, route: str, old: str, module: int) -> str:
    api.post(route, files.group_body(old, module))
    return f"{old} is its name again."


def _group_back(api: Any, action: str, group_id: int, name: str, state: str) -> str:
    api.post(files.group_route(action=action), {"items": [group_id]})
    return f"The redirect group {name} is {state} again."


class WorkbenchRedirectFiles:
    """Mixed into the redirect commands; the provider supplies ctx, background and say."""

    parent: Any
    say: Callable[[str], None]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    step: Callable[..., None]
    refresh: Callable[[], None]
    show_modal: Callable[[Any, str], int]
    _file: Callable[..., Path | None]
    _redirect_site: Callable[[Any, WbRow | None], str]
    _in_group: Callable[[str, str, Callable[[int], None]], None]

    def redirect_group_rows(self, site: str, api: Any) -> list[WbRow]:
        """Off the UI thread: Redirects > Groups."""
        return [files.group_row(site, g) for g in read_groups(api)]

    # -- groups ---------------------------------------------------------------------

    def _redirect_group_send(
        self,
        site: str,
        title: str,
        lines: list[str],
        route: str,
        body: dict[str, Any],
        said: str,
        undo: Callable[[Any], str] | None = None,
        *,
        yes: str,
    ) -> None:
        if not wdlg.ask_preview(
            self.parent, self.show_modal, title=title, summary=lines[0], lines=lines, yes=yes
        ):
            return
        api = self.ctx(site).api

        def done(_answer: Any) -> None:
            self.say(said)
            self.step(site, said.rstrip("."), (lambda: undo(api)) if undo else None)
            self.refresh()

        self.background(title.lower(), lambda: api.post(route, body), done)

    def do_new_redirect_group(self, ref: Any, row: WbRow | None) -> None:
        site = self._redirect_site(ref, row)
        name = (
            dlg.ask_text(
                self.parent,
                self.show_modal,
                title="New Redirect Group",
                prompt="&Name:",
                value="",
                help_text="Such as Old Shop or Campaigns.",
            )
            if site
            else None
        )
        if not name:
            return
        try:
            body = files.group_body(name)
        except ValueError as exc:
            self.say(str(exc))
            return
        self._redirect_group_send(
            site,
            "New Redirect Group",
            [f"Make the redirect group {body['name']} on {site}, run by WordPress."],
            files.group_route(),
            body,
            f"Made the redirect group {body['name']} on {site}.",
            yes="Make Group",
        )

    def do_rename_redirect_group(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "redirect_group":
            return
        old = row.cell("name")
        name = dlg.ask_text(
            self.parent,
            self.show_modal,
            title="Rename Redirect Group",
            prompt="&Name:",
            value=old,
            help_text="Its redirects stay in it.",
        )
        if not name or name.strip() == old:
            return
        module = int(row.raw.get("module_id", 1) or 1)
        body = files.group_body(name, module)
        route = files.group_route(row.object_id)
        self._redirect_group_send(
            row.site,
            "Rename Redirect Group",
            [f"Rename the redirect group {old} on {row.site} to {body['name']}."],
            route,
            body,
            f"Renamed the redirect group {old} to {body['name']} on {row.site}.",
            lambda api: _rename_back(api, route, old, module),
            yes="Rename",
        )

    def do_toggle_redirect_group(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "redirect_group":
            return
        on = row.status != "disabled"
        action, back = ("disable", "enable") if on else ("enable", "disable")
        name = row.cell("name")
        effect = "its redirects stop working" if on else "its redirects work again"
        self._redirect_group_send(
            row.site,
            "Turn Off Group" if on else "Turn On Group",
            [f"Turn the redirect group {name} on {row.site} {'off' if on else 'on'}: {effect}."],
            files.group_route(action=action),
            {"items": [row.object_id]},
            f"The redirect group {name} on {row.site} is {'off' if on else 'on'}.",
            lambda api: _group_back(api, back, row.object_id, name, "on" if on else "off"),
            yes="Turn Off" if on else "Turn On",
        )

    def do_delete_redirect_group(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "redirect_group":
            return
        name, count = row.cell("name"), row.cell("redirects") or "0"
        typed = dlg.ask_text(
            self.parent,
            self.show_modal,
            title="Delete Redirect Group",
            prompt=f"Deleting {name} deletes its {count} redirects with it, for good. "
            "Type its name to delete it:",
            value="",
            help_text="The Redirection plugin keeps no Trash.",
        )
        if typed is None:
            return
        if typed.strip() != name:
            self.say("The name did not match. Nothing was deleted.")
            return
        api = self.ctx(row.site).api
        said = f"Deleted the redirect group {name} and its {count} redirects on {row.site}."

        def done(_answer: Any) -> None:
            self.say(said)
            self.step(row.site, said.rstrip("."))
            self.refresh()

        self.background(
            "deleting a redirect group",
            lambda: api.post(files.group_route(action="delete"), {"items": [row.object_id]}),
            done,
        )

    # -- export and import ----------------------------------------------------------

    def do_export_redirects(self, ref: Any, row: WbRow | None) -> None:
        site = self._redirect_site(ref, row)
        if not site:
            return
        path = self._file(
            "Export Redirects", "CSV (*.csv)|*.csv|Redirection JSON (*.json)|*.json", save=True
        )
        if path is None:
            return
        api = self.ctx(site).api
        as_json = path.suffix.casefold() == ".json"

        def work() -> int:
            redirects = read_pages(api, "redirect")
            text = (
                files.export_json(redirects, read_groups(api))
                if as_json
                else files.export_csv(redirects)
            )
            path.write_text(text, encoding="utf-8")
            return len(redirects)

        def done(count: int) -> None:
            self.say(f"Saved {count} redirects from {site} to {path.name}.")

        self.background("exporting redirects", work, done)

    def do_import_redirects(self, ref: Any, row: WbRow | None) -> None:
        site = self._redirect_site(ref, row)
        if not site:
            return
        path = self._file(
            "Import Redirects",
            "CSV or Redirection JSON (*.csv;*.json)|*.csv;*.json|All files|*.*",
            save=False,
        )
        if path is None:
            return
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError) as exc:
            self.say(f"QUILL could not read {path.name}: {exc}")
            return
        api = self.ctx(site).api
        self.background(
            "reading the redirects already there",
            lambda: [str(r.get("url", "")) for r in read_pages(api, "redirect")],
            lambda known: self._redirects_planned(
                site, path.name, files.parse_import(text, path.name, known)
            ),
        )

    def _redirects_planned(self, site: str, name: str, plan: files.ImportPlan) -> None:
        if not plan.adds:
            why = plan.problems[0] if plan.problems else ""
            self.say(f"{name} has nothing to add to {site}. {why}".strip())
            return
        count = len(plan.adds)
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title="Import Redirects",
            summary=f"Add {count} redirect{'s' if count != 1 else ''} from {name} to {site}.",
            lines=plan.lines(),
            yes="Import",
        ):
            return
        self._in_group(
            site, "Import Redirects", lambda group: self._redirects_into(site, plan, group)
        )

    def _redirects_into(self, site: str, plan: files.ImportPlan, group: int) -> None:
        api = self.ctx(site).api

        def work() -> list[str]:
            failed: list[str] = []
            for source, target, code, regex in plan.adds:
                try:
                    body = edit_body(source, target, code, group_id=group, regex=regex)
                    api.post("redirection/v1/redirect", body)
                except Exception as exc:  # noqa: BLE001 - a result per redirect
                    failed.append(f"{source}: {exc}")
            return failed

        def done(failed: list[str]) -> None:
            added = len(plan.adds) - len(failed)
            said = f"Added {added} of {len(plan.adds)} redirects to {site}." + (
                f" {len(failed)} {'was' if len(failed) == 1 else 'were'} refused." if failed else ""
            )
            self.say(said)
            self.step(site, said.rstrip("."))
            if failed:
                dlg.show_report(
                    self.parent,
                    self.show_modal,
                    title="Import Redirects",
                    text="\n".join(failed),
                    help_text="Each redirect the plugin refused.",
                )
            self.refresh()

        self.background("importing redirects", work, done)
