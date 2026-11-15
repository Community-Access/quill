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
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.field_plugins import (
    acf_lookup,
    acf_schema,
    acf_values,
    meta_from_properties,
    route_properties,
    with_acf_page,
)
from quill.core.wordpress.site import kind_route
from quill.core.wordpress.workbench_edit import (
    EditConflict,
    EditRefused,
    body_for,
    run_batch,
    save,
)
from quill.core.wordpress.workbench_forms import form_plugins
from quill.core.wordpress.workbench_moderation import version_of
from quill.core.wordpress.workbench_people_bulk import user_post_count
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.wordpress.workbench_sheets import (
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
    SheetSpec,
    SheetState,
    merge_values,
)
from quill.ui import wordpress_dialogs as dlg
from quill.ui.wordpress_workbench_batch_sheets import _GRAVITY_SHEETS, _NO_EDIT, BATCH_SHEETS
from quill.ui.wordpress_workbench_sheet_guards import setting_cleared

__all__ = ["BATCH_SHEETS", "WorkbenchSheetCommands"]


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

    def _load_sheet(
        self, row: WbRow
    ) -> tuple[SheetSpec, dict[str, Any], dict[str, Any], Any, dict[str, Any]]:
        """Off the UI thread: the fresh object, its sheet, its values and term names."""
        if row.subkind == "gravity" and row.kind in _GRAVITY_SHEETS:
            return self.gravity_sheet(row)  # type: ignore[attr-defined]
        ctx = self.ensure(self.ctx(row.site))
        api = ctx.api
        fresh: dict[str, Any] = dict(row.raw)
        if row.route and row.kind not in ("setting", "fact", "help", "problem"):
            got = api.get(row.route, context="edit")
            fresh = dict(got) if isinstance(got, dict) else fresh
        if row.kind == "user":  # wp-admin's Posts column, on the sheet (9.18)
            fresh["post_count"] = user_post_count(api, row.object_id)
        names: dict[str, dict[str, int]] = {}
        term_names: dict[int, str] = {}
        author_names: dict[int, str] = {}
        taxonomies: dict[str, str] = {}
        meta: dict[str, Any] = {}
        schema: dict[str, Any] = {}
        acf: dict[str, Any] | None = None  # Advanced Custom Fields, where the site shows it
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
            props = route_properties(api, kind_route(row.subkind))
            meta, acf = meta_from_properties(props), acf_schema(props)
        elif row.kind in ("term", "user", "comment") and row.route:
            try:
                props = route_properties(api, row.route.rsplit("/", 1)[0])
                meta, acf = meta_from_properties(props), acf_schema(props)
            except WordPressApiError as exc:
                if exc.status not in (401, 403, 404):
                    raise
                meta = {}
        elif (
            row.kind not in ("media", "comment", "term", "user", "plugin", "setting") and row.route
        ):
            try:
                schema = route_properties(api, row.route.rsplit("/", 1)[0])
            except Exception:  # noqa: BLE001 - a route without OPTIONS keeps the raw sheet
                schema = {}
        sheet = sheet_for(replace(row, raw=fresh), taxonomies=taxonomies, meta=meta, schema=schema)
        values = values_for(row, fresh, term_names=term_names, author_names=author_names)
        if row.kind == "user" and hasattr(self, "with_access_page"):  # PMPro's Has Access
            sheet = self.with_access_page(ctx, sheet, values)
        if row.kind == "item":  # Author and Template as choices, as wp-admin offers (9.18)
            from quill.core.wordpress import workbench_parity as wpp

            kind = str(fresh.get("type", "") or row.subkind)
            sheet = wpp.with_choices(
                sheet,
                values,
                authors=wpp.author_choices(api),
                templates=wpp.template_choices(api, kind) if "template" in fresh else (),
            )
            if "featured_media" in fresh:  # the picture by title, chosen from the library
                sheet = wpp.with_featured(sheet)
                values["featured_media"] = wpp.featured_value(api, fresh.get("featured_media"))
        if acf:  # its own page; saved as {"acf": ...} and checked like meta
            sheet = with_acf_page(sheet, acf)
            values.update(acf_values(fresh))
            meta = {**meta, **acf_lookup(acf)}
        return sheet, values, fresh, names, meta

    def _one_sheet(self, row: WbRow) -> None:
        def shown(
            loaded: tuple[SheetSpec, dict[str, Any], dict[str, Any], Any, dict[str, Any]],
        ) -> None:
            sheet, values, fresh, names, meta = loaded
            locked, can_save = self._locked(sheet, row)
            loaded_modified = version_of(row.kind, fresh)  # comments and users: their fields

            def on_save(state: SheetState) -> bool:
                return self._save_one(sheet, row, state, fresh, names, meta, loaded_modified)

            self._editor(
                sheet,
                values,
                title=sheet_title(row),
                on_save=on_save if can_save else None,
                locked=locked,
                field_buttons=self._featured(row),
            ).show()

        self.background(f"reading {row.title}", lambda: self._load_sheet(row), shown)

    def _featured(self, row: WbRow) -> dict[str, Any]:
        """Choose from Library and Remove Featured Image, on an item's featured image (9.18)."""
        if row.kind == "user" and hasattr(self, "access_buttons"):
            return self.access_buttons(row)  # the Access page's Check a Post or Page
        if row.kind != "item" or not hasattr(self, "featured_buttons"):
            return {}
        return {"featured_media": self.featured_buttons(row.site)}

    def _save_one(
        self,
        sheet: SheetSpec,
        row: WbRow,
        state: SheetState,
        fresh: Mapping[str, Any],
        names: Mapping[str, Mapping[str, int]],
        meta_schema: Mapping[str, Any],
        loaded_modified: str,
    ) -> bool:
        if row.kind == "form_entry" and row.subkind == "gravity":
            return bool(self.gravity_entry_save(row, state))  # type: ignore[attr-defined]
        try:
            body = body_for(
                sheet,
                row,
                state.pending(),
                term_names=names,
                meta_schema=meta_schema,
            )
            if row.kind == "item":
                from quill.core.wordpress.workbench_parity import clean_body

                body = clean_body(body)
        except EditRefused as exc:
            self.say(str(exc.args[0]))
            return False
        if not body:
            self.say("Nothing changed on this row.")
            return True
        if row.kind == "setting" and not setting_cleared(self, row, body):
            return False
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
            if row.kind == "user" and "roles" in body:  # the same guard as Change Role
                from quill.core.wordpress.workbench_people import check_role_save

                account = self.ensure(self.ctx(row.site)).account
                check_role_save(api, account, row.object_id, body)
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
        return True

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
            field_buttons=self._featured(rows[0]),
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
            for number in ("author", "featured_media"):  # "Sky (9)" sends 9
                if number in body:
                    body[number] = int(str(body[number]).rsplit("(", 1)[-1].rstrip(")") or 0)
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
                # QAF's part of the Spam page, editable where the site allows it.
                **self.spam_page_values(ctx),  # type: ignore[attr-defined]
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
            lambda values: self._site_editor(site, values).show(),
        )

    def _site_editor(self, site: str, values: dict[str, Any]) -> Any:
        parts = self.site_sheet_with_spam(site, SITE_SHEET, values)  # type: ignore[attr-defined]
        return self._editor(
            parts["sheet"],
            parts["values"],
            title=f"{site} Properties",
            on_save=parts.get("on_save"),
            locked=parts.get("locked", {}),
        )

    # -- Change History and Undo --------------------------------------------------

    def do_undo(self, _ref: Any, _row: WbRow | None) -> None:
        change = self.history.next_undo()
        if change is None:
            self.say("Nothing to undo.")
            return
        if change.undo is None:  # said once, then passed over: Ctrl+Z reaches the one before
            self.history.undo()
            more = " Ctrl+Z again undoes the change before it." if self.history.next_undo() else ""
            self.say(f"{change.summary} This cannot be undone.{more}")
            return
        self.background("undoing", self.history.undo, lambda said: (self.say(said), self.refresh()))

    def do_history(self, _ref: Any, _row: WbRow | None) -> None:
        entries = list(self.history.entries)
        if not entries:
            self.say("No changes made in the Workbench yet.")
            return
        upcoming = self.history.next_undoable()
        lines = [
            f"{i}. {c.summary}"
            + ("" if c.undo else " (cannot be undone)")
            + (" (Ctrl+Z undoes this next)" if c is upcoming else "")
            for i, c in enumerate(reversed(entries), 1)
        ]
        dlg.show_report(
            self.parent,
            self.show_modal,
            title="Change History",
            text="\n".join(lines),
            help_text="Every change made in the Workbench this session, newest first. "
            "Ctrl+Z undoes the newest one that can be undone; a newer one that cannot is "
            "named once and passed over.",
        )
