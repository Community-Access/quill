"""By Name operations in the WordPress Workbench (PRD 15.12).

A mixin of :class:`quill.ui.wordpress_workbench_across.WorkbenchAcrossCommands`:
on a row of Sites > site > By Name, **Rename Everywhere**, **Split**,
**Merge Into**, **Reassign**, **Replace Everywhere** and **Find Items Missing
This Field**. Which operation a kind allows is
:mod:`quill.core.wordpress.workbench_scope_matrix`'s decision, and a kind
that does not allow it says why. Every change is planned in the core
(:mod:`quill.core.wordpress.workbench_by_name`), previewed item by item,
checked for conflicts as it is sent, reported item by item, and put in the
Change History with an undo wherever it can truly restore.

Every request runs through ``self.background``.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from quill.core.wordpress import workbench_by_name as bn
from quill.core.wordpress.workbench_across import kind_rows
from quill.core.wordpress.workbench_permissions import refusal
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.wordpress.workbench_scope_matrix import by_name_support
from quill.core.workbench.actions import Tier
from quill.core.workbench.history import Change
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_workbench_dialogs as wdlg

__all__ = ["WorkbenchByNameCommands"]

_NEEDS = {
    "terms": "manage_categories",
    "authors": "edit_others_posts",
    "template_parts": "edit_theme_options",
}
_PREVIEW_LINES = 200


class WorkbenchByNameCommands:
    """Rename, split, merge, reassign and replace a value everywhere it is used."""

    parent: Any
    history: Any
    say: Callable[[str], None]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    show_modal: Callable[[Any, str], int]
    refresh: Callable[[], None]
    write_refusal: Callable[[WbRow, Tier], str]
    account_for: Callable[[str], Any]
    site_scan: Callable[[str], Any]

    # -- shared --------------------------------------------------------------------

    def _bn_row(self, row: WbRow | None, op: str) -> WbRow | None:
        """The value row, when *op* is allowed on its kind here; else say why and None."""
        if row is None or row.kind != "value":
            self.say("Choose a row under By Name first.")
            return None
        support = by_name_support(row.subkind, op)
        if not support.supported:
            self.say(support.reason)
            return None
        reason = self.write_refusal(WbRow("item", row.site, "0", {}, ""), Tier.WRITE)
        account = self.account_for(row.site)
        need = _NEEDS.get(row.subkind, "edit_others_posts")
        if not reason and account is not None:
            reason = refusal(need, account, row.site)
        if reason:
            self.say(reason)
            return None
        return row

    def _bn_ask(self, title: str, prompt: str, value: str, help_text: str) -> str:
        said = dlg.ask_text(
            self.parent,
            self.show_modal,
            title=title,
            prompt=prompt,
            value=value,
            help_text=help_text,
        )
        return (said or "").strip()

    def _bn_pick(self, title: str, prompt: str, rows: Sequence[str], help_text: str) -> int | None:
        if not rows:
            self.say("There is nothing else to choose.")
            return None
        return dlg.ask_choice(
            self.parent,
            self.show_modal,
            title=title,
            prompt=prompt,
            rows=list(rows),
            help_text=help_text,
        )

    def _bn_pick_items(self, title: str, items: Sequence[Any]) -> list[int] | None:
        titles = [bn._title(raw) for raw in items]
        picked = wdlg.ask_checks(
            self.parent,
            self.show_modal,
            title=title,
            prompt="&Items that move:",
            rows=titles,
            help_text="Check each item that moves. The ones left unchecked stay as they are.",
        )
        if not picked:
            return None
        return [int(items[i].get("id", 0)) for i in picked]

    def _bn_send(
        self,
        row: WbRow,
        title: str,
        summary: str,
        edits: Sequence[bn.Edit],
        *,
        undoable: bool = True,
        prepare: Callable[[Any], Sequence[bn.Edit]] | None = None,
        after: Callable[[Any, list[bn.Edit]], str] | None = None,
        undo_extra: Callable[[], str] | None = None,
    ) -> None:
        """Preview *edits*, send them with the conflict check, report, and record undo."""
        kept = self.__dict__.get("_scans", {}).get(row.site)
        note, not_read = bn.unread_preview(kept[1], row.subkind) if kept else ("", [])
        if not edits:
            said = f"Nothing the scan read uses {row.cell('value') or row.key}."
            self.say(f"{said} {note}".strip())
            return
        lines = [e.line for e in edits[:_PREVIEW_LINES]]
        if len(edits) > _PREVIEW_LINES:
            lines.append(f"and {len(edits) - _PREVIEW_LINES} more")
        lines += not_read
        final = "" if undoable else " This cannot be undone."
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title=title,
            summary=f"{summary} {len(edits)} changes on {row.site}.{final}"
            + (f" {note}" if note else ""),
            lines=lines,
            yes=title.removesuffix("..."),
        ):
            return
        site = row.site

        def work() -> tuple[list[bn.Outcome], list[bn.Edit], str]:
            api = self.ctx(site).api
            planned = list(prepare(api)) if prepare is not None else list(edits)
            outcomes, sent = bn.apply_edits(api, planned)
            more = after(api, sent) if after is not None else ""
            return outcomes, sent, more

        def done(result: tuple[list[bn.Outcome], list[bn.Edit], str]) -> None:
            outcomes, sent, more = result
            said, report = bn.outcome_report(outcomes)
            said = f"{title.removesuffix('...')}: {said}{(' ' + more) if more else ''}"
            if note:
                said += f" {note}"
            self.say(said)
            if any(not o.ok for o in outcomes):
                dlg.show_report(
                    self.parent,
                    self.show_modal,
                    title=f"{title.removesuffix('...')}: Each Item",
                    text=report,
                    help_text="What happened to each item, one a line; Not done says why.",
                )
            undo = None
            if undoable and sent:

                def undo() -> str:
                    put = bn.undo_edits(lambda s: self.ctx(s).api, sent)
                    return f"{put} {undo_extra()}".strip() if undo_extra is not None else put

            self.history.record(Change(row.cell("value") or row.key, said, undo=undo))
            self.__dict__.setdefault("_scans", {}).pop(site, None)
            self.refresh()

        self.background(title.removesuffix("...").lower(), work, done)

    def _bn_terms_like(self, row: WbRow) -> list[tuple[str, str]]:
        """(key, name) of the other terms in the row's taxonomy."""
        taxonomy = row.key.rpartition(":")[0]
        scan = self.site_scan(row.site)
        return [
            (f"{tax}:{raw.get('id')}", str(raw.get("name", "")))
            for tax, raw in scan.terms
            if tax == taxonomy and f"{tax}:{raw.get('id')}" != row.key
        ]

    def _bn_people_but(self, row: WbRow) -> list[tuple[int, str]]:
        scan = self.site_scan(row.site)
        return [(i, n) for i, n in sorted(scan.users.items()) if str(i) != row.key]

    # -- the commands -------------------------------------------------------------------

    def do_rename_value(self, _ref: Any, row: WbRow | None) -> None:
        row = self._bn_row(row, "rename")
        if row is None:
            return
        scan = self.site_scan(row.site)
        if row.subkind == "terms":
            term = next((raw for tax, raw in scan.terms if f"{tax}:{raw.get('id')}" == row.key), {})
            name = self._bn_ask(
                "Rename Everywhere",
                "&New name:",
                str(term.get("name", "")),
                "The term's new name, on every post and page that has it.",
            )
            if not name:
                return
            slug = self._bn_ask(
                "Rename Everywhere",
                "New &slug (empty keeps it):",
                "",
                "The address part of the term's archive. Empty keeps the slug it has.",
            )
            edits = bn.plan_term_rename(scan, row.key, name, slug)
        elif row.subkind == "template_parts":
            title = self._bn_ask(
                "Rename Everywhere",
                "&New title:",
                row.cell("value"),
                "The part's new title. Its slug stays, so every template still places it.",
            )
            if not title or title == row.cell("value"):
                return
            edits = bn.plan_part_rename(scan, row.key, title)
        else:
            key, _sep, value = row.key.partition(": ")
            new = self._bn_ask(
                "Rename Everywhere",
                f"&New value for {key}:",
                value,
                "The value every item with this one gets instead.",
            )
            if not new or new == value:
                return
            edits = bn.plan_field(scan, row.key, new)
        self._bn_send(row, "Rename Everywhere...", f"{row.cell('value')} is renamed.", edits)

    def do_split_value(self, _ref: Any, row: WbRow | None) -> None:
        row = self._bn_row(row, "split")
        if row is None:
            return
        scan = self.site_scan(row.site)
        if row.subkind == "terms":
            ids = self._bn_pick_items("Split", bn.term_uses(scan, row.key))
            if not ids:
                return
            name = self._bn_ask(
                "Split", "&New term:", "", "The new term the checked items move to."
            )
            if not name:
                return
            preview = bn.plan_term_move(scan, row.key, 0, name, ids)
            made: dict[str, int] = {}

            def prepare(api: Any) -> list[bn.Edit]:
                made["id"], edits = bn.split_term(api, scan, row.key, name, ids)
                return edits

            taxonomy = row.key.rpartition(":")[0]

            def remove_new() -> str:
                if made.get("id"):
                    route = f"wp/v2/{bn.term_base(scan, taxonomy)}/{made['id']}"
                    self.ctx(row.site).api.delete(route, force=True)
                return f"{name} was deleted again."

            self._bn_send(
                row,
                "Split...",
                f"{len(ids)} items move to the new term {name}.",
                preview,
                prepare=prepare,
                undo_extra=remove_new,
            )
            return
        if row.subkind == "fields":
            ids = self._bn_pick_items("Split", bn.field_items(scan, row.key))
            if not ids:
                return
            key, _sep, value = row.key.partition(": ")
            new = self._bn_ask(
                "Split", f"&New value for {key}:", value, "The checked items' value."
            )
            if not new or new == value:
                return
            self._bn_send(
                row, "Split...", f"{len(ids)} items change.", bn.plan_field(scan, row.key, new, ids)
            )
            return
        items = [raw for raw in scan.items if str(raw.get("author", "")) == row.key]
        ids = self._bn_pick_items("Split", items)
        if not ids:
            return
        people = self._bn_people_but(row)
        index = self._bn_pick("Split", "&Give them to:", [n for _i, n in people], "The new author.")
        if index is None:
            return
        edits = bn.plan_author(scan, int(row.key), people[index][0], ids)
        self._bn_send(row, "Split...", f"{len(ids)} items go to {people[index][1]}.", edits)

    def do_merge_value(self, _ref: Any, row: WbRow | None) -> None:
        row = self._bn_row(row, "merge")
        if row is None:
            return
        scan = self.site_scan(row.site)
        if row.subkind == "terms":
            others = self._bn_terms_like(row)
            index = self._bn_pick(
                "Merge Into",
                "&Merge into:",
                [n for _k, n in others],
                "The term every item moves to. This term is then deleted.",
            )
            if index is None:
                return
            target_key, target_name = others[index]
            target_id = int(target_key.rpartition(":")[2])
            edits = bn.plan_term_move(scan, row.key, target_id, target_name)
            taxonomy, _sep, ident = row.key.rpartition(":")

            def delete_old(api: Any, sent: list[bn.Edit]) -> str:
                if len(sent) != len(edits):
                    return "The old term was kept, because not every item moved."
                api.delete(f"wp/v2/{bn.term_base(scan, taxonomy)}/{ident}", force=True)
                return "The old term was deleted."

            self._bn_send(
                row,
                "Merge Into...",
                f"Every item moves to {target_name}; this term is deleted.",
                edits,
                undoable=False,
                after=delete_old,
            )
            return
        key = row.key.partition(": ")[0]
        others = [
            r.key
            for r in kind_rows(scan, "fields")
            if r.key.startswith(f"{key}: ") and r.key != row.key
        ]
        index = self._bn_pick(
            "Merge Into", "&Merge into:", others, "The value every item with this one takes."
        )
        if index is None:
            return
        new = others[index].partition(": ")[2]
        self._bn_send(
            row,
            "Merge Into...",
            f"Every item takes {others[index]}.",
            bn.plan_field(scan, row.key, new),
        )

    def do_reassign_value(self, _ref: Any, row: WbRow | None) -> None:
        row = self._bn_row(row, "reassign")
        if row is None:
            return
        scan = self.site_scan(row.site)
        if row.subkind == "terms":
            others = self._bn_terms_like(row)
            index = self._bn_pick(
                "Reassign",
                "&Move items to:",
                [n for _k, n in others],
                "The term every item moves to. This term stays, with no items.",
            )
            if index is None:
                return
            target_key, target_name = others[index]
            edits = bn.plan_term_move(
                scan, row.key, int(target_key.rpartition(":")[2]), target_name
            )
            self._bn_send(row, "Reassign...", f"Every item moves to {target_name}.", edits)
            return
        people = self._bn_people_but(row)
        index = self._bn_pick(
            "Reassign", "&Give everything to:", [n for _i, n in people], "The new author."
        )
        if index is None:
            return
        edits = bn.plan_author(scan, int(row.key), people[index][0])
        self._bn_send(row, "Reassign...", f"Everything goes to {people[index][1]}.", edits)

    def do_replace_value(self, _ref: Any, row: WbRow | None) -> None:
        row = self._bn_row(row, "replace")
        if row is None:
            return
        scan = self.site_scan(row.site)
        kind = row.subkind
        if kind in ("media_usage", "patterns"):
            names = (
                [str(m.get("source_url", "")).rsplit("/", 1)[-1] for m in scan.media]
                if kind == "media_usage"
                else list(scan.patterns.values())
            )
            names = [n for n in names if n and n != row.key]
            index = self._bn_pick(
                "Replace Everywhere", "&Use instead:", names, "What every page uses instead."
            )
            if index is None:
                return
            new = names[index]
        else:
            prompts = {
                "links": ("&New address:", "The address every link to this one gets instead."),
                "blocks": ("&New shortcode name:", "Another shortcode's name, such as gallery."),
                "forms": ("&Other form, such as Form 7:", "The form every page places instead."),
            }
            prompt, help_text = prompts[kind]
            new = self._bn_ask("Replace Everywhere", prompt, "", help_text)
            if not new:
                return
        edits, reason = bn.plan_replace(scan, kind, row.key, new)
        if not edits:
            self.say(reason)
            return
        self._bn_send(
            row, "Replace Everywhere...", f"Every page using {row.key} uses {new}.", edits
        )

    def do_find_missing(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "value" or row.subkind != "fields":
            self.say("Find Items Missing This Field works on a row of By Name > Field Values.")
            return
        key = row.key.partition(": ")[0]
        scan = self.site_scan(row.site)
        missing = bn.items_missing_field(scan, key)
        note, _lines = bn.unread_preview(scan, "fields")
        text = "\n".join(missing) or f"Every post and page read has a value for {key}."
        dlg.show_report(
            self.parent,
            self.show_modal,
            title=f"Items Missing {key}",
            text=f"{text}\n\n{note}" if note else text,
            help_text="Each post or page with no value for the field, one a line.",
        )
