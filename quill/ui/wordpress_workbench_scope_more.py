"""The rest of By Name and Across Sites: convert, patterns, a plugin's blocks, merge, remove.

A mixin on :class:`quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`,
ahead of :class:`~quill.ui.wordpress_workbench_across.WorkbenchAcrossCommands`
whose By Name helpers (``_bn_row``, ``_bn_send``, ``_bn_pick_items``) and
Across Sites helpers (``_across_refusal``, ``_across_report``, ``scope_sites``)
it uses (WP-R-043, WP-R-044):

- **Convert to Block** on a shortcode row of By Name > Blocks and Shortcodes;
- **Update Pattern Everywhere** and **Detach Copies** on a row of Patterns Used;
- **Pages Using Its Blocks** on a block row, and on a plugin's row before it is
  removed;
- **Merge Everywhere** (terms) and **Remove Everywhere** (terms, redirects,
  blocked senders) on an Across Sites row.

Which kind allows what is :mod:`quill.core.wordpress.workbench_scope_matrix`'s
decision; the planning is :mod:`quill.core.wordpress.workbench_by_name_blocks`
and :mod:`quill.core.wordpress.workbench_across_more`. Everything is previewed
before it is sent, every request runs through ``self.background``, and every
outcome is said per item or per site.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.wordpress import workbench_by_name as bn
from quill.core.wordpress import workbench_by_name_blocks as bb
from quill.core.wordpress.workbench_across_more import (
    removal_plan,
    run_removals,
    term_merge_plan,
)
from quill.core.wordpress.workbench_across_ops import run_edits_by_site
from quill.core.wordpress.workbench_by_name import Edit, Outcome
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.wordpress.workbench_scope_matrix import by_name_support, classify
from quill.core.workbench.actions import Tier
from quill.core.workbench.history import Change
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_workbench_dialogs as wdlg

__all__ = ["WorkbenchScopeMoreCommands"]

_PREVIEW_LINES = 200


class WorkbenchScopeMoreCommands:
    """Convert to Block, Update Pattern, Detach Copies, a plugin's blocks, Merge and Remove."""

    parent: Any
    history: Any
    say: Callable[[str], None]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    show_modal: Callable[[Any, str], int]
    refresh: Callable[[], None]
    write_refusal: Callable[[WbRow, Tier], str]
    site_scan: Callable[[str], Any]
    _bn_row: Callable[[WbRow | None, str], WbRow | None]
    _bn_send: Callable[..., None]
    _bn_pick_items: Callable[[str, Any], list[int] | None]
    _across_refusal: Callable[[str, str], str]
    _across_report: Callable[[str, str, list[Outcome]], None]

    # -- shortcodes to blocks -----------------------------------------------------------

    def do_convert_shortcode(self, _ref: Any, row: WbRow | None) -> None:
        row = self._bn_row(row, "convert")
        if row is None:
            return
        value = row.cell("value") or row.key
        code = bb.shortcode_of(value)
        if code not in bb.CONVERTIBLE:
            self.say(bb.NO_BLOCK.get(code, f"{value} has no core block to become") + ".")
            return
        scan = self.site_scan(row.site)
        uses = [raw for raw in scan.items if f"[{code}" in bn._content(raw)]
        if not uses:
            self.say(f"Nothing the scan read uses [{code}].")
            return
        chosen = self._bn_pick_items(f"Convert [{code}] to Block", uses)
        if chosen is None:
            return
        edits, left = bb.plan_convert(scan, value, chosen)
        if not edits:
            self.say(f"Nothing to convert: {left[0]}." if left else "Nothing to convert.")
            return
        self._bn_send(
            row,
            "Convert to Block...",
            f"Each checked item's [{code}] becomes the {code} block."
            + (f" {len(left)} uses stay shortcodes, such as {left[0]}." if left else ""),
            edits,
        )

    # -- synced patterns ----------------------------------------------------------------

    def _pattern_ref(self, row: WbRow | None, op: str) -> tuple[WbRow, int] | None:
        row = self._bn_row(row, op)
        if row is None:
            return None
        scan = self.site_scan(row.site)
        ident = bn._pattern_id(scan, row.key)
        if not ident:
            self.say(f"{row.key} is not one of {row.site}'s synced patterns as read.")
            return None
        return row, ident

    def do_update_pattern(self, _ref: Any, row: WbRow | None) -> None:
        found = self._pattern_ref(row, "update_all")
        if found is None:
            return
        row, ident = found
        api = self.ctx(row.site).api
        uses = int(row.cell("count") or 0)

        def read() -> Any:
            return api.get(f"wp/v2/blocks/{ident}", context="edit")

        def got(pattern: Any) -> None:
            if not isinstance(pattern, dict):
                self.say(f"{row.site} did not send the pattern {row.key}.")
                return
            text = dlg.ask_text(
                self.parent,
                self.show_modal,
                title=f"Update {row.key} Everywhere",
                prompt="&Content (block markup):",
                value=bn._content(pattern),
                multiline=True,
                help_text=(
                    "The synced pattern's blocks. Saving changes it once, and every page "
                    "placing it shows the change."
                ),
            )
            if text is None:
                return
            edit = bb.pattern_update_edit(row.site, pattern, text, uses)
            if edit is None:
                self.say("The content is unchanged, so nothing was sent.")
                return
            self._bn_send(
                row,
                "Update Pattern Everywhere...",
                f"{row.key} changes once, on {row.site}.",
                [edit],
            )

        self.background(f"reading {row.key}", read, got)

    def do_detach_pattern(self, _ref: Any, row: WbRow | None) -> None:
        found = self._pattern_ref(row, "detach")
        if found is None:
            return
        row, ident = found
        scan = self.site_scan(row.site)
        uses = bb.pattern_items(scan, ident)
        if not uses:
            self.say(f"No page the scan read places {row.key}.")
            return
        chosen = self._bn_pick_items(f"Detach {row.key}", uses)
        if chosen is None:
            return
        api = self.ctx(row.site).api

        def got(pattern: Any) -> None:
            content = bn._content(pattern) if isinstance(pattern, dict) else ""
            if not content:
                self.say(f"{row.site} did not send the blocks of {row.key}, so nothing changed.")
                return
            self._bn_send(
                row,
                "Detach Copies...",
                f"Each checked page gets {row.key}'s own blocks; editing the pattern no longer "
                "changes them.",
                bb.plan_detach(scan, ident, content, chosen),
            )

        self.background(
            f"reading {row.key}", lambda: api.get(f"wp/v2/blocks/{ident}", context="edit"), got
        )

    # -- a plugin's blocks --------------------------------------------------------------

    def do_plugin_block_uses(self, _ref: Any, row: WbRow | None) -> None:
        if row is not None and row.kind == "value":
            support = by_name_support(row.subkind, "plugin_uses")
            if not support.supported:
                self.say(support.reason)
                return
            namespace = bb.block_namespace(row.cell("value") or row.key)
            if not namespace or namespace == "core":
                self.say("That is a core block, which no plugin removes.")
                return
            namespaces = [namespace]
            name = f"the {namespace} blocks"
        elif row is not None and row.kind == "plugin":
            namespaces = bb.plugin_namespaces(row.raw)
            name = row.cell("plugin") or row.title or row.key
            if not namespaces:
                self.say(f"{name} does not say its name space, so its blocks cannot be found.")
                return
        else:
            self.say("Choose a block under By Name, or a plugin, first.")
            return
        site = row.site

        def work() -> list[tuple[str, list[str]]]:
            return bb.namespace_uses(self.site_scan(site), namespaces)

        def done(found: list[tuple[str, list[str]]]) -> None:
            spaces = ", ".join(namespaces)
            if not found:
                self.say(f"No page the scan read on {site} uses a block from {spaces}.")
                return
            said = f"{len(found)} pages on {site} use blocks from {spaces}."
            self.say(said)
            dlg.show_report(
                self.parent,
                self.show_modal,
                title=f"Pages Using {name}",
                text="\n".join([
                    said,
                    "",
                    *(f"{title}: {', '.join(names)}" for title, names in found),
                ]),
                help_text=(
                    "Each page using a block from the plugin, with the blocks it uses. Removing "
                    "the plugin leaves those blocks unable to show."
                ),
            )

        self.background(f"finding the blocks of {name}", work, done)

    # -- merge and remove everywhere ----------------------------------------------------

    def _across_row(self, row: WbRow | None, op: str) -> WbRow | None:
        if row is None or row.kind != "across":
            self.say("Choose a row under Across Sites first.")
            return None
        support = classify("across", row.subkind, "all_sites", op)
        if not support.supported:
            self.say(support.reason)
            return None
        return row

    def do_merge_everywhere(self, _ref: Any, row: WbRow | None) -> None:
        row = self._across_row(row, "merge")
        if row is None:
            return
        objects: dict[str, Any] = row.raw.get("objects") or {}
        target = dlg.ask_text(
            self.parent,
            self.show_modal,
            title=f"Merge {row.key} Everywhere",
            prompt="&Merge into the term named:",
            help_text=(
                "The term each site's posts move to, in the same taxonomy. A site without a "
                "term of that name is left alone and said."
            ),
        )
        if not target or not target.strip():
            return
        target = target.strip()
        refused = [
            Outcome(s, row.key, False, why)
            for s in objects
            if (why := self._across_refusal(s, "terms"))
        ]
        sites = [s for s in objects if s not in {o.site for o in refused}]

        def plan() -> tuple[list[Edit], dict[str, int], list[Outcome]]:
            edits: list[Edit] = []
            sources: dict[str, int] = {}
            cannot: list[Outcome] = []
            for site in sites:
                try:
                    got, source, why = term_merge_plan(
                        self.ctx(site).api, site, row.key, objects[site], target
                    )
                except Exception as exc:  # noqa: BLE001 - one site's failure is said for it
                    got, source, why = [], 0, getattr(exc, "plain", "") or str(exc)
                if why:
                    cannot.append(Outcome(site, row.key, False, why))
                    continue
                edits += got
                sources[site] = source
            return edits, sources, cannot

        def planned(answer: tuple[list[Edit], dict[str, int], list[Outcome]]) -> None:
            edits, sources, cannot = answer
            blocked = refused + cannot
            if not sources:
                self.say(f"Nothing to merge: {blocked[0].line}." if blocked else "No site has it.")
                return
            if not self.practice_crossing_ok(  # type: ignore[attr-defined]
                f"Merge {row.key} Everywhere", list(sources), list(sources), together=True
            ):
                return
            lines = [e.line for e in edits[:_PREVIEW_LINES]]
            lines += [f"{s}: {row.key}: deleted once its posts have moved" for s in sources]
            lines += [f"Not changed. {o.line}" for o in blocked]
            if not wdlg.ask_preview(
                self.parent,
                self.show_modal,
                title=f"Merge {row.key} Everywhere",
                summary=(
                    f"On {len(sources)} sites, {len(edits)} posts move to {target} and {row.key} "
                    "is deleted. A site where any post does not move keeps the old term. This "
                    "cannot be undone."
                ),
                lines=lines,
                yes="Merge",
            ):
                return
            self._send_merge(row, target, edits, sources, blocked)

        self.background(f"planning to merge {row.key}", plan, planned)

    def _send_merge(
        self,
        row: WbRow,
        target: str,
        edits: list[Edit],
        sources: dict[str, int],
        blocked: list[Outcome],
    ) -> None:
        route = "wp/v2/categories" if row.key.endswith("(category)") else "wp/v2/tags"

        def work() -> list[Outcome]:
            outcomes, sent = run_edits_by_site(lambda s: self.ctx(s).api, edits)
            for site, source in sources.items():
                wanted = [e for e in edits if e.site == site]
                if len([e for e in sent if e.site == site]) != len(wanted):
                    outcomes.append(
                        Outcome(site, row.key, False, "kept, because not every post moved")
                    )
                    continue
                try:
                    self.ctx(site).api.delete(f"{route}/{source}", force=True)
                    outcomes.append(Outcome(site, row.key, True, f"merged into {target}"))
                except Exception as exc:  # noqa: BLE001 - said per site
                    said = getattr(exc, "plain", "") or str(exc)
                    outcomes.append(Outcome(site, row.key, False, said))
            return outcomes

        def done(outcomes: list[Outcome]) -> None:
            outcomes = outcomes + blocked
            merged = sum(1 for o in outcomes if o.ok and o.title == row.key)
            said = f"{row.key}: merged into {target} on {merged} of {len(sources)} sites."
            self._across_report(f"Merge {row.key} Everywhere", said, outcomes)
            self.history.record(Change(row.key, said, undo=None))
            self.refresh()

        self.background("merging everywhere", work, done)

    def do_remove_everywhere(self, _ref: Any, row: WbRow | None) -> None:
        row = self._across_row(row, "remove")
        if row is None:
            return
        if row.subkind == "app_passwords":
            self.do_revoke_everywhere(_ref, row)  # type: ignore[attr-defined]
            return
        objects: dict[str, Any] = row.raw.get("objects") or {}
        plan, refused = removal_plan(row.subkind, row.key, objects)
        for step in list(plan):
            why = self._across_refusal(step.site, row.subkind)
            if why:
                plan.remove(step)
                refused.append(Outcome(step.site, row.key, False, why))
        if not plan:
            self.say(f"Nothing to remove: {refused[0].line}." if refused else "No site has it.")
            return
        changed = [step.site for step in plan]
        if not self.practice_crossing_ok(  # type: ignore[attr-defined]
            f"Remove {row.key} Everywhere", changed, changed, together=True
        ):
            return
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title=f"Remove {row.key} Everywhere",
            summary=f"{row.key} is removed on {len(plan)} sites. This cannot be undone.",
            lines=[step.line for step in plan] + [f"Not changed. {o.line}" for o in refused],
            yes="Remove",
            destructive=True,
        ):
            return

        def done(outcomes: list[Outcome]) -> None:
            outcomes = outcomes + refused
            good = sum(1 for o in outcomes if o.ok)
            said = f"{row.key}: removed on {good} of {len(outcomes)} sites. It cannot be undone."
            self._across_report(f"Remove {row.key} Everywhere", said, outcomes)
            self.history.record(Change(row.key, said, undo=None))
            self.refresh()

        self.background(
            "removing everywhere", lambda: run_removals(lambda s: self.ctx(s).api, plan), done
        )
