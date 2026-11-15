"""Help where the stakes are: problems, plugin dependencies and explained settings (PRD D2, D3).

A mixin on :class:`quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`;
the words and the rules are wx-free:

- **Site Health and Broken Links rows** (kind ``problem``,
  :mod:`quill.core.wordpress.workbench_problem_help`): Explain opens what the
  problem means for visitors, what usually causes it and the steps, with
  WordPress's own words, in a window the reader reads. Fix... changes a broken
  link in the post that holds it, or sets a city time zone, each after a
  preview and with Ctrl+Z to put it back; where only wp-admin can fix it, it
  says why and opens that screen. Take Me There selects the place in the tree;
  Open in Editor opens the post that holds a broken link.
- **What Depends on It** on a plugin
  (:mod:`quill.core.wordpress.workbench_plugin_depends`), which turning a
  plugin off also asks before its confirmation.
- **Explained settings** (kind ``setting_help``,
  :mod:`quill.core.wordpress.workbench_settings_more`): Open Its Documentation
  and Open in Dashboard.

Every request runs through ``self.background``; every outcome is one sentence.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from quill.core.wordpress.site import kind_route
from quill.core.wordpress.workbench_help_actions import command
from quill.core.wordpress.workbench_plugin_depends import Dependents, dependents
from quill.core.wordpress.workbench_problem_help import explanation, problem_help
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.history import Change
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_workbench_dialogs as wdlg
from quill.ui.workbench_help_dialogs import HelpTextDialog

__all__ = ["WorkbenchProblemCommands"]

_CITY = re.compile(r"^[A-Za-z]+(?:/[A-Za-z0-9_+\-]+){1,2}$")


def _broken(row: WbRow) -> bool:
    return row.key.startswith("broken:") and bool(row.raw.get("source_id"))


class WorkbenchProblemCommands:
    """Explain, Fix..., Take Me There and Open in Editor on problems; What Depends on It."""

    frame: Any
    commands: Any
    history: Any
    parent: Any
    say: Callable[[str], None]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    ensure: Callable[[Any], Any]
    profile: Callable[[str], Any]
    show_modal: Callable[[Any, str], int]
    refresh: Callable[[], None]
    _open_screen: Callable[..., None]
    _browser: Callable[[str], None]

    # -- greyed, with why -------------------------------------------------------------

    def problem_refusal(self, command_id: str, row: WbRow | None) -> str:
        """Why a problem row's command cannot run on *row* ("" when it can)."""
        if row is None or row.kind != "problem":
            return ""
        found = problem_help(row)
        if command_id == command("problem_in_editor") and not _broken(row):
            return "This is about the whole site, not one post. Take Me There goes to its place."
        if command_id == command("fix_problem"):
            if row.status == "good":
                return "This check passed, so there is nothing to fix."
            if not found.fix or (found.fix == "link" and not _broken(row)):
                return f"QUILL cannot fix this from here. {found.steps}"
        if command_id == command("problem_there") and not (found.there or found.screen):
            return "This problem has no one place to go to."
        return ""

    # -- the problem rows -------------------------------------------------------------

    def do_explain_problem(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "problem":
            self.say("Choose a Site Health or broken link row to explain.")
            return
        HelpTextDialog(self.parent, "Explain", explanation(row)).show()

    def do_problem_there(self, _ref: Any, row: WbRow | None) -> None:
        from quill.ui.workbench_frame import NodeRef

        if row is None or row.kind != "problem":
            return
        found = problem_help(row)
        if found.there and self.frame is not None:
            if self.frame.select(NodeRef("site", found.there, row.site)):
                self.frame.tree.SetFocus()
                return
        if found.screen:
            self._open_screen(row.site, found.screen)
            return
        self.say("This problem has no one place to go to.")

    def do_problem_in_editor(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or not _broken(row):
            self.say("Open in Editor works on a broken link, opening the post that holds it.")
            return
        profile = self.profile(row.site)
        if profile is None:
            self.say(f"{row.site} is no longer in your list of sites.")
            return
        self.commands.open_item(
            profile, str(row.raw.get("source_type") or "post"), int(row.raw["source_id"])
        )

    def do_fix_problem(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "problem":
            self.say("Choose a Site Health or broken link row to fix.")
            return
        refused = self.problem_refusal(command("fix_problem"), row)
        if refused:
            self.say(refused)
            return
        found = problem_help(row)
        if found.fix == "link":
            self._fix_link(row)
        elif found.fix == "timezone":
            self._fix_timezone(row)
        else:
            self._open_screen(row.site, found.screen)

    def _fix_link(self, row: WbRow) -> None:
        old = str(row.raw.get("target_url") or row.cell("target"))
        holder = row.cell("test") or "the post"
        new = dlg.ask_text(
            self.parent,
            self.show_modal,
            title="Fix a Broken Link",
            prompt="&New address:",
            value=old,
            help_text=f"The address that should replace {old} in {holder}, on {row.site}.",
        )
        new = (new or "").strip()
        if not new or new == old:
            return
        api = self.ctx(row.site).api
        route = f"{kind_route(str(row.raw.get('source_type') or 'post'))}/{row.raw['source_id']}"

        def read() -> str:
            raw = api.get(route, context="edit", _fields="content")
            content = raw.get("content") if isinstance(raw, dict) else None
            return str(content.get("raw", "") if isinstance(content, dict) else content or "")

        def done(text: str) -> None:
            count = text.count(old)
            if not count:
                self.say(f"{holder} no longer holds {old}, so nothing was changed.")
                return
            if not wdlg.ask_preview(
                self.parent,
                self.show_modal,
                title="Fix a Broken Link",
                summary=f"Change the link in {holder} on {row.site}?",
                lines=[f"{old} becomes {new}, {count} time{'s' if count != 1 else ''}."],
                yes="Change",
            ):
                return
            changed = text.replace(old, new)

            def saved(_raw: object) -> None:
                said = f"Changed the link in {holder} on {row.site}."
                self.say(said)

                def undo() -> str:
                    api.post(route, {"content": text})
                    return f"The link in {holder} is back as it was."

                self.history.record(Change(holder, said, undo=undo))
                self.refresh()

            self.background("changing a link", lambda: api.post(route, {"content": changed}), saved)

        self.background("reading the post that holds the link", read, done)

    def _fix_timezone(self, row: WbRow) -> None:
        city = dlg.ask_text(
            self.parent,
            self.show_modal,
            title="Set the Time Zone",
            prompt="&City time zone:",
            value="",
            help_text="A city time zone, such as Europe/London or America/Chicago, so "
            "scheduled posts follow daylight saving.",
        )
        city = (city or "").strip()
        if not city:
            return
        if not _CITY.match(city):
            self.say(f"{city} is not a city time zone. Write it like Europe/London.")
            return
        api = self.ctx(row.site).api

        def read() -> str:
            raw = api.get("wp/v2/settings")
            return str(raw.get("timezone", "") if isinstance(raw, dict) else "")

        def done(before: str) -> None:
            if not wdlg.ask_preview(
                self.parent,
                self.show_modal,
                title="Set the Time Zone",
                summary=f"Set {row.site}'s time zone?",
                lines=[f"Time zone: {before or 'a fixed offset'} becomes {city}."],
                yes="Set",
            ):
                return

            def saved(_raw: object) -> None:
                said = f"{row.site}'s time zone is now {city}."
                self.say(said)

                def undo() -> str:
                    api.post("wp/v2/settings", {"timezone": before})
                    return f"{row.site}'s time zone is back to {before or 'its offset'}."

                self.history.record(Change(row.site, said, undo=undo))
                self.refresh()

            self.background(
                "setting the time zone",
                lambda: api.post("wp/v2/settings", {"timezone": city}),
                saved,
            )

        self.background("reading the time zone", read, done)

    # -- plugins: what depends on one -------------------------------------------------

    def plugin_dependents(self, row: WbRow) -> Dependents:
        """What depends on *row*'s plugin, asked of its site (off the UI thread)."""
        ctx = self.ensure(self.ctx(row.site))
        namespaces = ctx.info.namespaces if getattr(ctx, "info", None) is not None else ()
        return dependents(ctx.api, row.key, name=row.title, namespaces=namespaces)

    def do_what_depends(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "plugin":
            self.say("Choose a plugin to ask what depends on it.")
            return
        self.background(
            f"asking {row.site} what depends on {row.title}",
            lambda: self.plugin_dependents(row),
            lambda found: self.say(found.sentence()),
        )

    # -- explained settings -----------------------------------------------------------

    def do_open_docs(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or not row.link:
            self.say("This setting has no documentation of its own; Read in Full explains it.")
            return
        self._browser(row.link)

    def do_setting_screen(self, _ref: Any, row: WbRow | None) -> None:
        screen = str(row.raw.get("screen", "")) if row is not None else ""
        if row is None or not screen:
            self.say("This setting is changed in the plugin's own screens in wp-admin.")
            return
        self._open_screen(row.site, screen)
