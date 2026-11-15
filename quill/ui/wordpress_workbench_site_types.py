"""QUILL Site Types on the Content Model: define, stop defining, export (PRD 12b, WP-R-037).

A mixin of :class:`~quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`.
The site must have the QUILL Site Types plugin (``quill-site-types/v1`` in its
index) and you the Administrator role; each change is previewed first and
recorded in Change History:

- **Define with QUILL Site Types...** (Ctrl+N on Content Model): a post type,
  a taxonomy, or a field group with its fields as ``name: kind``;
- **Stop Defining...**: the definition goes, its content stays, Ctrl+Z defines
  it again;
- **Export as Code**: the ``register_*`` calls, opened in the editor;
- **Fields...**: a field group's fields, one sheet each (kind, label, help,
  required, default, choices), or a new field;
- **Add a Field Kind...**: a kind of the site's own (``POST /kinds``).

The requests are in :mod:`quill.core.wordpress.site_types_plugin`.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.wordpress import site_types_plugin as qst
from quill.core.wordpress.sites import sites_path
from quill.core.wordpress.workbench_discovered import SITE_TYPES_NAMESPACE
from quill.core.wordpress.workbench_edit import EditRefused
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.history import Change
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_workbench_dialogs as wdlg

__all__ = ["WorkbenchSiteTypesCommands"]

_CHOICES = (("type", "A post type"), ("taxonomy", "A taxonomy"), ("field_group", "A field group"))


class WorkbenchSiteTypesCommands:
    """Content Model commands for definitions kept by QUILL Site Types."""

    parent: Any
    commands: Any
    history: Any
    _data_dir: Any
    say: Callable[[str], None]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    ensure: Callable[[Any], Any]
    show_modal: Callable[[Any, str], int]
    refresh: Callable[[], None]
    site_of: Callable[[Any], str]
    current_site: Callable[[], str]

    def _site_types_missing(self, site: str) -> str:
        """Why *site* cannot take definitions ("" when it has the plugin)."""
        info = self.ctx(site).info
        if info is None:
            return f"Open {site}'s Content Model first, so QUILL knows what the site offers."
        if info.supports(SITE_TYPES_NAMESPACE):
            return ""
        return (
            f"{site} does not have the QUILL Site Types plugin, so a post type or field can "
            "only be made in code or another plugin there. Content Model still lists them all."
        )

    def _ask(self, title: str, prompt: str, help_text: str, value: str = "") -> str | None:
        return dlg.ask_text(
            self.parent, self.show_modal, title=title, prompt=prompt, value=value,
            help_text=help_text,
        )  # fmt: skip

    def do_define_site_type(self, ref: Any, row: WbRow | None) -> None:
        site = (row.site if row is not None else "") or self.site_of(ref) or self.current_site()
        missing = self._site_types_missing(site) if site else "Choose a site first."
        if missing:
            self.say(missing)
            return
        index = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title="Define with QUILL Site Types",
            prompt="&Define:",
            rows=[words for _what, words in _CHOICES],
            help_text="A post type holds items; a taxonomy sorts them; a field group adds "
            "fields to a type's Properties.",
        )
        if index is None:
            return
        what = _CHOICES[index][0]
        noun = qst.WHAT[what][2]
        key = self._ask(
            f"New {noun.title()}", "&Key:", "1 to 20 small letters, digits, hyphens or "
            "underscores, such as book. It never changes after this.",
        )  # fmt: skip
        if not key:
            return
        name = self._ask(f"New {noun.title()}", "&Name:", "What people see, such as Books.") or ""
        attach = ""
        if what != "type":
            attach = (
                self._ask(
                    f"New {noun.title()}",
                    "&For post types:",
                    "Post type keys separated by commas, such as post, book. Empty means Posts.",
                )  # fmt: skip
                or ""
            )
        self._define(site, what, key, name, attach)

    def _define(self, site: str, what: str, key: str, name: str, attach: str) -> None:
        ctx = self.ctx(site)
        fields_text = ""
        if what == "field_group":
            fields_text = (
                self._ask(
                    "New Field Group",
                    "&Fields:",
                    "Each as name: kind, separated by commas, "
                    "such as isbn: text, cover: picture. A picture needs alt text when filled.",
                )  # fmt: skip
                or ""
            )

        def prepared() -> dict[str, Any]:
            kinds = qst.read_kinds(ctx.api) if what == "field_group" else ()
            fields = qst.parse_fields(fields_text, kinds) if fields_text else []
            return qst.define_body(what, key, name, attach=attach, fields=fields)

        def previewed(body: dict[str, Any]) -> None:
            summary, lines = qst.define_preview(site, what, body)
            if not wdlg.ask_preview(
                self.parent, self.show_modal, title="Define", summary=summary, lines=lines,
                yes="Define",
            ):  # fmt: skip
                return

            def done(saved: dict[str, Any]) -> None:
                said = f"Defined {saved.get('name') or saved.get('title') or key} on {site}."
                self.say(said)
                undo = lambda: (  # noqa: E731
                    qst.stop_defining(ctx.api, what, str(body[qst.WHAT[what][1]])),
                    f"Stopped defining {key} again.",
                )[1]
                self.history.record(Change(key, said, undo=undo))
                self.refresh()

            self.background("defining", lambda: qst.define(ctx.api, what, body), done)

        # A bad key or field is refused in the work, and said as the failure.
        self.background("checking the definition", prepared, previewed)

    def do_stop_defining(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "model":
            self.say("Choose a row in Content Model.")
            return
        if not row.raw.get("editable_definition"):
            self.say(
                f"{row.title} is not defined through QUILL Site Types, so it is changed where it "
                "is registered. Its detail says where."
            )
            return
        what = row.subkind if row.subkind in qst.WHAT else "type"
        summary, lines = qst.stop_preview(row.site, what, row.key, row.title)
        if not wdlg.ask_preview(
            self.parent, self.show_modal, title="Stop Defining", summary=summary, lines=lines,
            yes="Stop Defining",
        ):  # fmt: skip
            return
        api = self.ctx(row.site).api

        def done(previous: dict[str, Any]) -> None:
            said = f"Stopped defining {row.title} on {row.site}; its content is kept."
            self.say(said)
            self.history.record(
                Change(row.title, said, undo=lambda: qst.put_back(api, what, previous))
            )
            self.refresh()

        self.background(
            "stopping a definition", lambda: qst.stop_defining(api, what, row.key), done
        )

    def do_export_as_code(self, ref: Any, row: WbRow | None) -> None:
        site = (row.site if row is not None else "") or self.site_of(ref) or self.current_site()
        missing = self._site_types_missing(site) if site else "Choose a site first."
        if missing:
            self.say(missing)
            return
        api = self.ctx(site).api

        def done(exported: tuple[str, str]) -> None:
            name, content = exported
            folder = sites_path(self._data_dir).parent / "site-types-exports"
            folder.mkdir(parents=True, exist_ok=True)
            path: Path = folder / name
            path.write_bytes(content.encode("utf-8"))  # exactly as sent, LF kept
            self.commands.host.open_path(path)
            self.say(f"Exported {site}'s definitions as code, open in the editor.")

        self.background("exporting definitions", lambda: qst.export_code(api, "php"), done)

    # -- one field at a time, and the site's own kinds ---------------------------------

    def do_edit_site_type_fields(self, _ref: Any, row: WbRow | None) -> None:
        """Fields...: a field group's fields, each on its own sheet, or a new one."""
        if row is None or row.kind != "model" or row.subkind != "field_group":
            self.say("Fields... works on a field group in Content Model.")
            return
        group = dict(row.raw.get("definition") or {})
        if not row.raw.get("editable_definition") or not group:
            self.say(f"{row.title} is not defined through QUILL Site Types.")
            return
        fields = [f for f in group.get("fields") or [] if isinstance(f, dict)]
        index = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title=f"Fields of {row.title}",
            prompt="&Field:",
            rows=[f"{f.get('label') or f.get('name')} ({f.get('kind')})" for f in fields]
            + ["Add a field"],
            help_text="Choose a field to open its sheet, or Add a field for a new one.",
        )
        if index is None:
            return
        name = str(fields[index].get("name", "")) if index < len(fields) else ""
        api = self.ctx(row.site).api

        def shown(kinds: tuple[str, ...]) -> None:
            current = fields[index] if name else {"kind": "text"}

            def on_save(state: Any) -> bool:
                changed = {c.key: c.after for c in state.pending()}
                try:
                    after = qst.apply_field(group, name, changed, kinds)
                except EditRefused as exc:
                    self.say(str(exc.args[0]))
                    return False
                summary, lines = qst.field_preview(row.site, group, name, after)
                if not wdlg.ask_preview(
                    self.parent, self.show_modal, title="Field", summary=summary,
                    lines=lines, yes="Save",
                ):  # fmt: skip
                    return False

                def done(_saved: object) -> None:
                    said = f"Saved {row.title} on {row.site}."
                    self.say(said)
                    undo = lambda: (  # noqa: E731
                        qst.save_group(api, group),
                        f"{row.title} is as it was.",
                    )[1]
                    self.history.record(Change(row.title, said, undo=undo))
                    self.refresh()

                self.background("saving a field group", lambda: qst.save_group(api, after), done)
                return True

            self._editor(  # type: ignore[attr-defined]
                qst.field_sheet(kinds, new=not name),
                qst.field_values(current),
                title=f"{name or 'New Field'} - {row.title}",
                on_save=on_save,
            ).show()

        self.background("reading field kinds", lambda: qst.read_kinds(api), shown)

    def do_add_field_kind(self, ref: Any, row: WbRow | None) -> None:
        """Add a Field Kind...: a kind of the site's own, for its field groups."""
        site = (row.site if row is not None else "") or self.site_of(ref) or self.current_site()
        missing = self._site_types_missing(site) if site else "Choose a site first."
        if missing:
            self.say(missing)
            return
        key = self._ask(
            "Add a Field Kind", "&Key:", "Small letters, such as isbn or stars.",
        )  # fmt: skip
        if not key:
            return
        label = self._ask("Add a Field Kind", "&Label:", "What people see, such as ISBN.") or ""
        base = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title="Add a Field Kind",
            prompt="&Stored as:",
            rows=list(qst.KIND_TYPES),
            help_text="What WordPress stores: text is string; a whole number is integer.",
        )
        if base is None:
            return
        pattern = ""
        if qst.KIND_TYPES[base] == "string":
            pattern = (
                self._ask(
                    "Add a Field Kind",
                    "&Pattern:",
                    "A regular expression every value must "
                    "match, such as ^[0-9]{13}$; empty for none.",
                )  # fmt: skip
                or ""
            )
        try:
            body = qst.kind_body(key, label, qst.KIND_TYPES[base], pattern)
        except EditRefused as exc:
            self.say(str(exc.args[0]))
            return
        summary, lines = qst.kind_preview(site, body)
        if not wdlg.ask_preview(
            self.parent, self.show_modal, title="Add a Field Kind", summary=summary, lines=lines,
            yes="Add",
        ):  # fmt: skip
            return
        api = self.ctx(site).api

        def done(_saved: object) -> None:
            said = f"Added the field kind {body['label']} to {site}."
            self.say(said)
            self.history.record(Change(body["kind"], said))

        self.background("adding a field kind", lambda: qst.add_kind(api, body), done)
