"""Shipping Classes and Generate Variations in the Workbench window (complete.md 2.3, Shop).

The Workbench side of :mod:`quill.core.wordpress.workbench_shop_classes` and
:mod:`quill.core.wordpress.workbench_shop_variations`. New, Change and Delete
of a shipping class are each a preview, then one request, then a step in
Change History: a new class is deleted by Ctrl+Z and a change is sent back;
a deleted class cannot return as it was, and the preview says so. Properties
on a product offers its shipping class by name (:meth:`with_shipping_classes`,
called by the sheet loader). Generate Variations refuses a product that is not
variable, with the reason, before anything is sent, and says how many it made
in one sentence.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.counted import plural
from quill.core.wordpress import workbench_shop_classes as classes
from quill.core.wordpress import workbench_shop_variations as variations
from quill.core.wordpress.plugin_shop_seo import ShopValueError
from quill.core.wordpress.workbench_plugin_write import checked_write
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.wordpress.workbench_shop_catalog import product_route
from quill.core.workbench.properties import SheetSpec
from quill.ui.wordpress_workbench_shop_order_edit import WorkbenchShopOrderEditCommands

__all__ = ["WorkbenchShopClassCommands"]

_FIELDS = (
    ("name", "&Name:", "What the shop calls it, such as Heavy items."),
    ("slug", "&Slug (blank to let WooCommerce make one):", "Such as heavy-items."),
    ("description", "&Description (blank for none):", "A note for the shop's managers."),
)


class WorkbenchShopClassCommands(WorkbenchShopOrderEditCommands):
    """Mixed into the provider beside the other shop commands, whose helpers it uses."""

    say: Callable[[str], None]
    ctx: Callable[[str], Any]
    background: Callable[..., None]
    refresh: Callable[[], None]
    step: Callable[..., None]
    history: Any
    _pl_ask: Callable[..., str | None]
    _pl_preview: Callable[[str, str, list[str], str], bool]
    _pl_send: Callable[..., None]
    _pl_made: Callable[..., None]
    _pl_checked: Callable[..., None]
    _pl_undo: Callable[..., Any]
    _shop_site: Callable[[Any, WbRow | None], str]
    _may_change: Callable[[str], bool]

    # -- Properties ----------------------------------------------------------------------

    def with_shipping_classes(self, api: Any, sheet: SheetSpec, values: dict[str, Any]) -> Any:
        """A product's sheet with its shipping class a choice by name. Off the UI thread."""
        try:
            found = api.get(classes.ROUTE, per_page=100)
        except Exception:  # noqa: BLE001 - a role that cannot read them keeps the typed slug
            return sheet
        return classes.with_class_choice(sheet, values, found if isinstance(found, list) else [])

    # -- shipping classes ------------------------------------------------------------------

    def _class_answers(self, title: str, old: dict[str, Any]) -> dict[str, str] | None:
        """Name, slug and description, asked in turn; None when one is cancelled.

        A blank name on a new class stops there, as every New here does.
        """
        answers: dict[str, str] = {}
        for key, prompt, help_text in _FIELDS:
            text = self._pl_ask(title, prompt, help_text, str(old.get(key, "") or ""))
            if text is None or (key == "name" and not old and not text.strip()):
                return None
            answers[key] = text
        return answers

    def do_new_shipping_class(self, ref: Any, row: WbRow | None) -> None:
        site = self._shop_site(ref, row)
        if not site or not self._may_change(site):
            return
        answers = self._class_answers("New Shipping Class", {})
        if answers is None:
            return
        try:
            body = classes.class_body({}, answers)
        except ShopValueError as exc:
            self.say(f"{exc} Nothing was made.")
            return
        if not self._pl_preview(
            "New Shipping Class",
            f"Make the shipping class {body['name']} on {site}.",
            classes.class_preview(site, {}, body),
            "Make Class",
        ):
            return
        self._pl_made(
            site,
            body["name"],
            classes.ROUTE,
            body,
            f"Made the shipping class {body['name']} on {site}.",
        )

    def do_change_shipping_class(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "shop_shipping_class":
            return
        old = dict(row.raw.get("_loaded", {}))
        answers = self._class_answers(f"Change Shipping Class - {row.title}", old)
        if answers is None:
            return
        try:
            body = classes.class_body(old, answers)
        except ShopValueError as exc:
            self.say(f"{exc} Nothing was changed.")
            return
        if not body:
            self.say(f"Nothing about {row.title} would change.")
            return
        if not self._pl_preview(
            "Change Shipping Class",
            f"Change the shipping class {row.title} on {row.site}.",
            classes.class_preview(row.site, old, body),
            "Change Class",
        ):
            return
        api = self.ctx(row.site).api
        route = f"{classes.ROUTE}/{row.object_id}"
        self._pl_checked(
            row.site,
            f"changing {row.title}",
            lambda: checked_write(api, route, body, old, name=row.title, site=row.site),
            f"Changed the shipping class {row.title} on {row.site}.",
            lambda w: self._pl_undo(
                api, route, dict(w.undo), f"Put the shipping class {row.title} back."
            ),
        )

    def do_delete_shipping_class(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "shop_shipping_class":
            return
        if not self._pl_preview(
            "Delete Shipping Class",
            f"Delete the shipping class {row.title} on {row.site} for good?",
            classes.delete_lines(row),
            "Delete",
        ):
            return
        api = self.ctx(row.site).api
        self._pl_send(
            row.site,
            f"deleting {row.title}",
            lambda: api.delete(f"{classes.ROUTE}/{row.object_id}", force=True),
            f"Deleted the shipping class {row.title} on {row.site}.",
        )

    # -- Generate Variations -------------------------------------------------------------

    def do_generate_variations(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "shop_product":
            return
        name, site = row.title, row.site
        listed = str(row.raw.get("product_type", "") or "")
        if listed and listed != "variable":  # said at once: no request for what cannot run
            self.say(variations.refusal(name, site, {"type": listed}))
            return
        api = self.ctx(site).api
        route = product_route(row.object_id)

        def read() -> dict[str, Any]:
            found = api.get(route)
            return dict(found) if isinstance(found, dict) else {}

        def previewed(product: dict[str, Any]) -> None:
            why = variations.refusal(name, site, product)
            if why:
                self.say(why)
                return
            if not self._pl_preview(
                "Generate Variations",
                f"Make every missing variation of {name} on {site}?",
                variations.preview_lines(name, site, product),
                "Generate",
            ):
                return
            before = variations.variation_ids(product)
            self.background(
                f"generating {name}'s variations",
                lambda: variations.generate(api, row.object_id, before),
                made,
            )

        def made(result: tuple[int, list[int]]) -> None:
            count, new_ids = result
            said = variations.made_sentence(name, site, count)

            def undo() -> str:
                for ident in new_ids:
                    api.delete(f"{route}/variations/{ident}", force=True)
                return f"Deleted {plural(len(new_ids), 'new variation')} of {name} on {site}."

            self.say(said)
            self.step(site, said, undo if new_ids else None)
            self.refresh()

        self.background(f"reading {name}", read, previewed)
