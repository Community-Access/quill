"""Properties, batch edits and undo in the WordPress Workbench (PRD 8, 9, W2 and W3).

A mixin on :class:`quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`.

- **Alt+Enter on one row** reads the object again (``context=edit``), with its
  term and author names, its registered meta and, for anything without a
  written sheet, its route's schema, then opens the shared editable sheet
  (:class:`quill.ui.workbench_sheet_editor.WorkbenchSheetEditor`). A field the
  person's role or Workbench access cannot change is read only, with the
  reason as its F1 help.
- **Saving** is :func:`quill.core.wordpress.workbench_edit.save`: the conflict
  check on ``modified_gmt``, the write, and the verify after it. A conflict
  sends nothing and asks Use Mine or Keep Theirs.
- **Alt+Enter on several rows** is the batch sheet (section 9): only the
  fields they share, Mixed where they differ, categories and tags added or
  removed; a preview names every item, and the change goes through
  ``batch/v1`` with a result per item and Try Again for any that failed.
- **Alt+Enter on a site** (or Alt+Shift+Enter anywhere in it) is the Site sheet,
  with its Spam page read only (13a.5).
- **Ctrl+Z** undoes the newest change from Change History, off the UI thread.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from typing import Any

from quill.core.wordpress import site_taxonomies as tx
from quill.core.wordpress.custom_fields import meta_schema_for
from quill.core.wordpress.field_plugins import route_properties
from quill.core.wordpress.site import kind_route
from quill.core.wordpress.workbench_edit import (
    EditConflict,
    EditRefused,
    body_for,
    run_batch,
    save,
)
from quill.core.wordpress.workbench_forms import form_plugins
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.wordpress.workbench_sheets import (
    ITEM_STATUSES,
    SITE_SHEET,
    sheet_for,
    sheet_title,
    term_ids,
    values_for,
)
from quill.core.workbench.actions import Tier
from quill.core.workbench.history import Change
from quill.core.workbench.properties import (
    MIXED,
    FieldKind,
    FieldSpec,
    PageSpec,
    SheetSpec,
    SheetState,
    merge_values,
)
from quill.ui import wordpress_dialogs as dlg

__all__ = ["BATCH_SHEETS", "WorkbenchSheetCommands"]

_OPEN = ("open", "closed")

BATCH_SHEETS: dict[str, SheetSpec] = {
    "item": SheetSpec(
        "item",
        "Items",
        (
            PageSpec(
                "general",
                "General",
                (
                    FieldSpec("status", "Status", FieldKind.CHOICE, choices=ITEM_STATUSES),
                    FieldSpec("author", "Author number", FieldKind.TEXT),
                    FieldSpec("comment_status", "Comments", FieldKind.CHOICE, choices=_OPEN),
                    FieldSpec("ping_status", "Pingbacks", FieldKind.CHOICE, choices=_OPEN),
                    FieldSpec("sticky", "Sticky", FieldKind.CHECK),
                    FieldSpec("template", "Template", FieldKind.TEXT),
                    FieldSpec("parent", "Parent number", FieldKind.NUMBER),
                ),
            ),
            PageSpec(
                "organize",
                "Categories and Tags",
                (
                    FieldSpec("add_categories", "Add categories", FieldKind.LIST),
                    FieldSpec("remove_categories", "Remove categories", FieldKind.LIST),
                    FieldSpec("add_tags", "Add tags", FieldKind.LIST),
                    FieldSpec("remove_tags", "Remove tags", FieldKind.LIST),
                ),
            ),
        ),
    ),
    "media": SheetSpec(
        "media",
        "Media",
        (
            PageSpec(
                "general",
                "General",
                (
                    FieldSpec("title", "Title"),
                    FieldSpec("alt_text", "Alt text"),
                    FieldSpec("caption", "Caption", FieldKind.MULTILINE),
                    FieldSpec("description", "Description", FieldKind.MULTILINE),
                ),
            ),
        ),
    ),
}
"""The batch sheets: fields many objects share (section 9)."""

_NO_EDIT = {
    "fact",
    "help",
    "namespace",
    "ability",
    "problem",
    "site",
    "writing_type",
    "taxonomy",
    "app_password",
    "theme",
}


class WorkbenchSheetCommands:
    """Properties for one row, several rows, a site; Change History and Undo."""

    frame: Any
    history: Any
    parent: Any
    say: Callable[[str], None]
    selected_rows: Callable[[], list[WbRow]]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    ensure: Callable[[Any], Any]
    show_modal: Callable[[Any, str], int]
    refresh: Callable[[], None]
    site_of: Callable[[Any], str]
    current_site: Callable[[], str]
    access_for: Callable[[str], Any]
    write_refusal: Callable[[WbRow, Tier], str]

    def _editor(self, sheet: SheetSpec, values: Mapping[str, object], **kw: Any) -> Any:
        from quill.ui.workbench_sheet_editor import WorkbenchSheetEditor

        return WorkbenchSheetEditor(
            self.parent, sheet, values, copy_text=self.frame.copy_text, **kw
        )

    def _locked(self, sheet: SheetSpec, row: WbRow) -> tuple[dict[str, str], bool]:
        """Fields the person cannot change, with why; and whether anything can be saved."""
        reason = "" if row.kind not in _NO_EDIT else "This is read only here."
        reason = reason or self.write_refusal(row, Tier.WRITE)
        locked: dict[str, str] = {}
        account = self.ctx(row.site).account if row.site else None
        for spec in sheet.fields():
            if spec.readonly:
                continue
            if reason:
                locked[spec.key] = reason
            elif spec.requirement and account is not None and not account.can(spec.requirement):
                from quill.core.wordpress.workbench_permissions import refusal

                locked[spec.key] = refusal(spec.requirement, account, row.site)
        return locked, not reason

    # -- one row ------------------------------------------------------------------

    def do_sheet(self, ref: Any, row: WbRow | None) -> None:
        frame = self.frame
        rows = self.selected_rows()
        on_tree = frame._wx.Window.FindFocus() is frame.tree
        if on_tree or not rows:
            if self.site_of(ref):
                self.do_site_sheet(ref, None)
            else:
                self.say("Alt+Enter on a row shows its Properties; Alt+Shift+Enter, the site's.")
            return
        if len(rows) > 1:
            self._batch_sheet(rows)
            return
        self._one_sheet(rows[0])

    def _load_sheet(self, row: WbRow) -> tuple[SheetSpec, dict[str, Any], dict[str, Any], Any]:
        """Off the UI thread: the fresh object, its sheet, its values and term names."""
        ctx = self.ensure(self.ctx(row.site))
        api = ctx.api
        fresh: dict[str, Any] = dict(row.raw)
        if row.route and row.kind not in ("setting", "fact", "help", "problem"):
            got = api.get(row.route, context="edit")
            fresh = dict(got) if isinstance(got, dict) else fresh
        names: dict[str, dict[str, int]] = {}
        term_names: dict[int, str] = {}
        author_names: dict[int, str] = {}
        taxonomies: dict[str, str] = {}
        meta: dict[str, Any] = {}
        schema: dict[str, Any] = {}
        if row.kind == "item":
            post_type = str(fresh.get("type", "") or row.subkind)
            for info in tx.taxonomies_for_type(api, post_type):
                if info.rest_base in fresh:
                    taxonomies[info.rest_base] = info.name
                    ids = [int(i) for i in fresh.get(info.rest_base) or []]
                    found = api.get(info.route, include=ids, _fields="id,name") if ids else []
                    for term in found if isinstance(found, list) else []:
                        term_names[int(term.get("id", 0))] = str(term.get("name", ""))
                        names.setdefault(info.rest_base, {})[str(term.get("name", ""))] = int(
                            term.get("id", 0)
                        )
            author = int(fresh.get("author", 0) or 0)
            if author:
                person = api.get(f"wp/v2/users/{author}", _fields="id,name")
                if isinstance(person, dict):
                    author_names[author] = str(person.get("name", ""))
            meta = meta_schema_for(api, kind_route(row.subkind))
        elif (
            row.kind not in ("media", "comment", "term", "user", "plugin", "setting") and row.route
        ):
            try:
                schema = route_properties(api, row.route.rsplit("/", 1)[0])
            except Exception:  # noqa: BLE001 - a route without OPTIONS keeps the raw sheet
                schema = {}
        sheet = sheet_for(replace(row, raw=fresh), taxonomies=taxonomies, meta=meta, schema=schema)
        values = values_for(row, fresh, term_names=term_names, author_names=author_names)
        return sheet, values, fresh, names

    def _one_sheet(self, row: WbRow) -> None:
        def shown(loaded: tuple[SheetSpec, dict[str, Any], dict[str, Any], Any]) -> None:
            sheet, values, fresh, names = loaded
            locked, can_save = self._locked(sheet, row)
            loaded_modified = str(fresh.get("modified_gmt", "") or "")

            def on_save(state: SheetState) -> None:
                self._save_one(sheet, row, state, fresh, names, loaded_modified)

            self._editor(
                sheet,
                values,
                title=sheet_title(row),
                on_save=on_save if can_save else None,
                locked=locked,
            ).show()

        self.background(f"reading {row.title}", lambda: self._load_sheet(row), shown)

    def _save_one(
        self,
        sheet: SheetSpec,
        row: WbRow,
        state: SheetState,
        fresh: Mapping[str, Any],
        names: Mapping[str, Mapping[str, int]],
        loaded_modified: str,
    ) -> None:
        try:
            body = body_for(sheet, row, state.pending(), term_names=names)
        except EditRefused as exc:
            self.say(str(exc.args[0]))
            return
        api = self.ctx(row.site).api

        def done(result: Any) -> None:
            self.say(result.sentence)
            if "slug" in body and hasattr(self, "offer_redirect"):
                self.offer_redirect(row, str(fresh.get("link", "") or ""))
            undo = dict(result.undo)
            if undo:
                self.history.record(
                    Change(
                        row.title,
                        result.sentence,
                        undo=lambda: (
                            save(api, row, undo),
                            f"Put {row.title} back as it was.",
                        )[1],
                    )
                )
            self.refresh()

        def work(check: str) -> Any:
            return save(api, row, body, loaded_modified=check, before=fresh)

        def failed(error: BaseException) -> None:
            if isinstance(error, EditConflict) and dlg.confirm(
                self.parent,
                self.show_modal,
                title="Changed on the Site",
                message=f"{error.args[0]} Send your changes anyway, replacing theirs?",
                yes_label="Use Mine",
            ):
                self.background("saving anyway", lambda: work(""), done)
                return
            if not isinstance(error, EditConflict):
                self.say(getattr(error, "plain", "") or str(error))

        self.frame._run_background(
            f"WordPress Workbench: saving {row.title}", lambda: work(loaded_modified), done, failed
        )

    # -- several rows (section 9) -------------------------------------------------

    def _batch_sheet(self, rows: Sequence[WbRow]) -> None:
        kinds = {r.kind for r in rows}
        sites = {r.site for r in rows}
        if len(kinds) > 1 or len(sites) > 1:
            self.say("Several rows at once need to be the same kind, from one site.")
            return
        kind = rows[0].kind
        if kind == "comment":
            self.say("For several comments, use Approve, Unapprove, Spam or Delete.")
            return
        sheet = BATCH_SHEETS.get(kind)
        if sheet is None:
            self.say("Several at once can be changed for posts, pages, custom items and media.")
            return
        reason = self.write_refusal(rows[0], Tier.WRITE)
        values = merge_values([values_for(r) for r in rows])
        for key in ("add_categories", "remove_categories", "add_tags", "remove_tags"):
            values[key] = ()
        title = f"{len(rows)} items Properties - {rows[0].site}"

        def on_save(state: SheetState) -> None:
            self._send_batch(sheet, rows, state)

        self._editor(
            sheet,
            values,
            title=title,
            on_save=None if reason else on_save,
            locked={spec.key: reason for spec in sheet.fields()} if reason else {},
        ).show()

    def _bodies(self, rows: Sequence[WbRow], edits: Mapping[str, Any]) -> list[dict[str, Any]]:
        bodies = []
        for row in rows:
            body = {k: v for k, v in edits.items() if not k.startswith(("add_", "remove_"))}
            for field_name in ("categories", "tags"):
                add, _ = term_ids(edits.get(f"add_{field_name}", ()), {})
                remove, _ = term_ids(edits.get(f"remove_{field_name}", ()), {})
                if add or remove:
                    have = [int(i) for i in row.raw.get(field_name) or []]
                    body[field_name] = sorted((set(have) | set(add)) - set(remove))
            if "parent" in body:
                body["parent"] = int(body["parent"] or 0)
            if "author" in body:
                body["author"] = int(str(body["author"]).rsplit("(", 1)[-1].rstrip(")") or 0)
            bodies.append(body)
        return bodies

    def _send_batch(self, sheet: SheetSpec, rows: Sequence[WbRow], state: SheetState) -> None:
        edits = {c.key: c.after for c in state.pending() if c.after is not MIXED}
        if not edits:
            self.say("Nothing changed, so nothing was sent.")
            return
        bodies = self._bodies(rows, edits)
        site = rows[0].site
        said = ", ".join(f"{sheet.field(k).label} to {v}" for k, v in edits.items())
        listing = "\n".join(f"- {r.title}" for r in rows[:25])
        more = f"\nand {len(rows) - 25} more" if len(rows) > 25 else ""
        if not dlg.confirm(
            self.parent,
            self.show_modal,
            title="Change Several",
            message=f"Change {len(rows)} items on {site}: {said}?\n{listing}{more}",
            yes_label="Change Them",
        ):
            return
        api = self.ctx(site).api
        before = [{k: r.raw.get(k) for k in body} for r, body in zip(rows, bodies, strict=True)]
        self._run_batch(api, list(rows), bodies, before)

    def _run_batch(
        self,
        api: Any,
        rows: list[WbRow],
        bodies: list[dict[str, Any]],
        before: list[dict[str, Any]],
    ) -> None:
        def done(results: Sequence[Any]) -> None:
            good = [r for r in results if r.ok]
            bad = [i for i, r in enumerate(results) if not r.ok]
            said = f"Changed {len(good)} of {len(results)} on {rows[0].site}."
            self.say(said)
            undo_rows = [r.row for r in good]
            undo_bodies = [before[i] for i, r in enumerate(results) if r.ok]
            self.history.record(
                Change(
                    said,
                    said,
                    undo=lambda: (
                        run_batch(api, undo_rows, undo_bodies),
                        f"Put {len(undo_rows)} back as they were.",
                    )[1],
                )
            )
            self.refresh()
            if bad:
                failures = "\n".join(results[i].sentence for i in bad)
                if dlg.confirm(
                    self.parent,
                    self.show_modal,
                    title="Some Were Not Changed",
                    message=f"{len(bad)} were not changed:\n{failures}\n\nTry them again?",
                    yes_label="Try Again",
                ):
                    self._run_batch(
                        api,
                        [rows[i] for i in bad],
                        [bodies[i] for i in bad],
                        [before[i] for i in bad],
                    )

        self.background("changing several", lambda: run_batch(api, rows, bodies), done)

    # -- the site -----------------------------------------------------------------

    def do_site_sheet(self, ref: Any, _row: WbRow | None) -> None:
        site = self.site_of(ref) or self.current_site()
        if not site:
            self.say("Connect a site first.")
            return

        def work() -> dict[str, Any]:
            ctx = self.ensure(self.ctx(site))
            info, account = ctx.info, ctx.account
            namespaces = info.namespaces if info else ()
            spam = [
                n
                for n, ns in (("Akismet", "akismet/v1"), ("Jetpack", "jetpack/v4"))
                if ns in namespaces
            ]
            forms = [p for p in form_plugins(ctx)]
            try:
                settings = ctx.api.get("wp/v2/settings")
            except Exception:  # noqa: BLE001 - settings need manage_options
                settings = {}
            settings = settings if isinstance(settings, dict) else {}
            return {
                "name": info.name if info else site,
                "description": info.description if info else "",
                "url": ctx.url,
                "wp_version": info.wp_version if info else "",
                "role": account.role_name if account else "",
                "capabilities": "\n".join(sorted(account.capabilities)) if account else "",
                "username": account.username if account else "",
                "kind": "WordPress.com" if ctx.api.address.is_wpcom else "Self-hosted",
                "access": self.access_for(site).words,
                "namespaces": "\n".join(namespaces),
                "comment_moderation": str(settings.get("default_comment_status", "not shown")),
                "spam_plugins": ", ".join(spam) or "none found",
                "form_plugins": ", ".join(forms) or "none found",
                "spam_note": (
                    "Held as Spam under Needs My Attention gathers the comments and form "
                    "entries this site doubted. WordPress's REST API does not show the "
                    "moderation rules or the blocklist, so they are changed in wp-admin, "
                    "under Settings, Discussion."
                ),
            }

        self.background(
            f"reading {site}",
            work,
            lambda values: self._editor(SITE_SHEET, values, title=f"{site} Properties").show(),
        )

    # -- Change History and Undo --------------------------------------------------

    def do_undo(self, _ref: Any, _row: WbRow | None) -> None:
        change = self.history.next_undo()
        if change is None:
            self.say("Nothing to undo.")
            return
        if change.undo is None:
            self.say(f"{change.summary} This cannot be undone.")
            return
        self.background("undoing", self.history.undo, lambda said: (self.say(said), self.refresh()))

    def do_history(self, _ref: Any, _row: WbRow | None) -> None:
        entries = list(self.history.entries)
        if not entries:
            self.say("No changes made in the Workbench yet.")
            return
        lines = [
            f"{i}. {c.summary}" + ("" if c.undo else " (cannot be undone)")
            for i, c in enumerate(reversed(entries), 1)
        ]
        dlg.show_report(
            self.parent,
            self.show_modal,
            title="Change History",
            text="\n".join(lines),
            help_text="Every change made in the Workbench this session, newest first. "
            "Ctrl+Z undoes the newest.",
        )
