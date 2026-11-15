"""WooCommerce's shipping zones, taxes, attributes and brands in the Workbench window.

A mixin on :class:`quill.ui.wordpress_workbench_shop_care.WorkbenchShopCareCommands`
(its checked writes); the words, checks and bodies are wx-free in
:mod:`quill.core.wordpress.workbench_shop_setup`. None of these has a
Trash, so Delete is for good, after a preview that says what goes with it;
only a deleted tax rate can be put back by Ctrl+Z (it is made again with the
same fields), because nothing else here returns as it was.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.wordpress import workbench_shop_setup as setup
from quill.core.wordpress.plugin_shop_seo import ShopValueError
from quill.core.wordpress.workbench_plugin_write import checked_write
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.history import Change
from quill.ui.wordpress_workbench_shop_care import WorkbenchShopCareCommands

_NEW = {
    "shop_zone": ("New Shipping Zone", "A name such as United States or Local delivery."),
    "shop_attribute": ("New Attribute", "A name such as Size or Colour."),
    "shop_brand": ("New Brand", "The brand's name as shoppers see it."),
}
_RATE_FIELDS = (
    ("name", "&Name:", "What the checkout calls it, such as State tax."),
    ("rate", "&Rate (percent):", "Such as 8.25, with no percent sign."),
    ("country", "C&ountry code (blank for everywhere):", "Two letters, such as US."),
    ("state", "&State code (blank for all):", "Such as AZ."),
    ("postcode", "&Postal codes (blank for all):", "One, or several with a semicolon between."),
    ("city", "C&ity (blank for all):", "A city name."),
)


class WorkbenchShopSetupCommands(WorkbenchShopCareCommands):
    """Shipping zones, tax rates and classes, attributes and their terms, brands."""

    def _pl_made(self, site: str, name: str, route: str, body: dict[str, Any], said: str) -> None:
        """POST *body* to *route*; Ctrl+Z deletes what was made (it is new, so nothing is lost)."""
        api = self.ctx(site).api  # type: ignore[attr-defined]

        def done(answer: Any) -> None:
            made = answer.get("id") if isinstance(answer, dict) else None
            undo = None
            if made:
                undo = lambda: (api.delete(f"{route}/{made}", force=True), f"Deleted {name}.")[1]  # noqa: E731
            self.history.record(Change(f"{site}: {name}", said, undo=undo))  # type: ignore[attr-defined]
            self.say(said)  # type: ignore[attr-defined]
            self.refresh()  # type: ignore[attr-defined]

        self.background(f"making {name}", lambda: api.post(route, body), done)  # type: ignore[attr-defined]

    def _pl_new_named(self, ref: Any, row: WbRow | None, kind: str) -> None:
        site = self._shop_site(ref, row)
        if not site or not self._may_change(site):
            return
        title, help_text = _NEW[kind]
        name = self._pl_ask(title, "&Name:", help_text)
        if name is None or not name.strip():
            return
        noun, route = setup.SIMPLE[kind]
        if not self._pl_preview(
            title,
            f"Make the {noun} {name.strip()} on {site}.",
            [f"A new {noun} on {site}: {name.strip()}.", "Ctrl+Z deletes it again."],
            f"Make {noun.title()}",
        ):
            return
        self._pl_made(
            site,
            name.strip(),
            route,
            {"name": name.strip()},
            f"Made the {noun} {name.strip()} on {site}.",
        )

    def do_new_zone(self, ref: Any, row: WbRow | None) -> None:
        self._pl_new_named(ref, row, "shop_zone")

    def do_new_attribute(self, ref: Any, row: WbRow | None) -> None:
        self._pl_new_named(ref, row, "shop_attribute")

    def do_new_brand(self, ref: Any, row: WbRow | None) -> None:
        self._pl_new_named(ref, row, "shop_brand")

    def do_rename_shop_item(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind not in ("shop_zone", "shop_attribute", "shop_brand"):
            return
        if row.kind == "shop_zone" and row.key == "0":
            self.say("The zone for everywhere else has no name of its own to change.")  # type: ignore[attr-defined]
            return
        noun, base = setup.SIMPLE[row.kind]
        name = self._pl_ask(f"Rename - {row.title}", "&New name:", f"The {noun}'s name.", row.title)
        if name is None or name.strip() in ("", row.title):
            return
        if not self._pl_preview(
            "Rename",
            f"Rename the {noun} {row.title} on {row.site}.",
            [f"{row.title} becomes {name.strip()}.", "Products and orders keep using it."],
            "Rename",
        ):
            return
        api = self.ctx(row.site).api  # type: ignore[attr-defined]
        route, body = f"{base}/{row.object_id}", {"name": name.strip()}
        self._pl_checked(
            row.site,
            f"renaming {row.title}",
            lambda: checked_write(
                api, route, body, row.raw.get("_loaded", {}), name=row.title, site=row.site
            ),
            f"Renamed the {noun} {row.title} to {name.strip()} on {row.site}.",
            lambda w: self._pl_undo(api, route, dict(w.undo), f"Named it {row.title} again."),
        )

    def do_delete_shop_item(self, _ref: Any, row: WbRow | None) -> None:
        kinds = ("shop_zone", "shop_attribute", "shop_brand", "shop_tax_rate", "shop_tax_class")
        if row is None or row.kind not in kinds:
            return
        if row.kind == "shop_zone" and row.key == "0":
            self.say("The zone for everywhere else cannot be deleted; remove its methods instead.")  # type: ignore[attr-defined]
            return
        noun, base = setup.SIMPLE.get(row.kind, ("tax class", setup.TAX_CLASSES))
        goes = {
            "shop_zone": "Its locations and methods go with it.",
            "shop_attribute": "Its terms go with it, and products lose it.",
            "shop_brand": "Products lose this brand.",
            "shop_tax_rate": "Ctrl+Z makes the rate again with the same fields.",
            "shop_tax_class": "Every rate in it goes with it, and products in it are taxed as "
            "standard.",
        }[row.kind]
        if not self._pl_preview(
            f"Delete {noun.title()}",
            f"Delete the {noun} {row.title} on {row.site} for good.",
            [row.detail, f"There is no Trash. {goes}"],
            "Delete",
        ):
            return
        api = self.ctx(row.site).api  # type: ignore[attr-defined]
        route = f"{base}/{row.key}"
        said = f"Deleted the {noun} {row.title} on {row.site}."

        def done(_answer: Any) -> None:
            undo: Callable[[], str] | None = None
            if row.kind == "shop_tax_rate":
                fields = dict(row.raw.get("_loaded", {}))
                undo = lambda: (api.post(setup.TAXES, fields), f"Made {row.title} again.")[1]  # noqa: E731
            self.history.record(Change(f"{row.site}: {row.title}", said, undo=undo))  # type: ignore[attr-defined]
            self.say(said)  # type: ignore[attr-defined]
            self.refresh()  # type: ignore[attr-defined]

        self.background(f"deleting {row.title}", lambda: api.delete(route, force=True), done)  # type: ignore[attr-defined]

    # -- shipping zones ---------------------------------------------------------------------

    def do_zone_locations(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "shop_zone":
            return
        if row.key == "0":
            self.say(
                "The zone for everywhere else covers what no other zone does; it has no locations."
            )  # type: ignore[attr-defined]
            return
        old = list(row.raw.get("_locations") or [])
        text = self._pl_ask(
            f"Locations - {row.title}",
            "&Locations (a comma between):",
            "Each a kind and a code: country US, state US:AZ, postcode 85001, continent EU. "
            "Blank leaves the zone with none.",
            ", ".join(f"{loc.get('type')} {loc.get('code')}" for loc in old),
        )
        if text is None:
            return
        try:
            new = setup.location_body(text)
        except ShopValueError as exc:
            self.say(f"{exc} Nothing was changed.")  # type: ignore[attr-defined]
            return
        if setup.location_words(new) == setup.location_words(old):
            self.say("The locations would not change.")  # type: ignore[attr-defined]
            return
        if not self._pl_preview(
            "Zone Locations",
            f"Change where {row.title} on {row.site} applies.",
            [
                f"Locations: {setup.location_words(old)} become {setup.location_words(new)}.",
                "Shoppers in these places get this zone's methods at checkout.",
            ],
            "Change Locations",
        ):
            return
        api = self.ctx(row.site).api  # type: ignore[attr-defined]
        route = f"{setup.ZONES}/{row.object_id}/locations"

        def work() -> list[Any]:
            now = api.get(route)
            if setup.location_words(now if isinstance(now, list) else []) != setup.location_words(
                old
            ):
                from quill.core.wordpress.workbench_edit import EditConflict

                raise EditConflict(
                    f"{row.title}'s locations changed on {row.site} after QUILL read them. "
                    "Nothing was sent. F5 reads them again."
                )
            answer = api.post(route, new)
            return answer if isinstance(answer, list) else []

        def done(answer: list[Any]) -> None:
            kept = setup.location_words(answer) == setup.location_words(new)
            said = f"Changed {row.title}'s locations on {row.site}." + (
                "" if kept or not answer else " The site did not keep them all."
            )
            back = [{"code": loc.get("code"), "type": loc.get("type")} for loc in old]
            undo = lambda: (api.post(route, back), f"Put {row.title}'s locations back.")[1]  # noqa: E731
            self.history.record(Change(f"{row.site}: {row.title}", said, undo=undo))  # type: ignore[attr-defined]
            self.say(said)  # type: ignore[attr-defined]
            self.refresh()  # type: ignore[attr-defined]

        self.background(f"changing {row.title}'s locations", work, done)  # type: ignore[attr-defined]

    def do_zone_methods(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "shop_zone":
            return
        methods = list(row.raw.get("_methods") or [])
        lines = setup.method_lines(methods)
        picked = self._pl_choose(
            f"Methods - {row.title}",
            "&Methods:",
            [*lines, "Add a method..."],
            "Choose a method to turn it on or off, change its cost or remove it; the last row "
            "adds one.",
        )
        if picked is None:
            return
        api = self.ctx(row.site).api  # type: ignore[attr-defined]
        base = f"{setup.ZONES}/{row.object_id}/methods"
        if picked == len(methods):
            kinds = list(setup.METHOD_KINDS)
            kind = self._pl_choose(
                "Add a Method",
                "Method &kind:",
                [setup.METHOD_KINDS[k] for k in kinds],
                "WooCommerce's own shipping methods.",
            )
            if kind is None or not self._pl_preview(
                "Add a Method",
                f"Add {setup.METHOD_KINDS[kinds[kind]]} to {row.title}.",
                [
                    f"{setup.METHOD_KINDS[kinds[kind]]} is added to {row.title}, turned on, with "
                    "WooCommerce's default settings. Change Its Cost sets a flat rate's cost."
                ],
                "Add Method",
            ):
                return
            self._pl_made(
                row.site,
                setup.METHOD_KINDS[kinds[kind]],
                base,
                {"method_id": kinds[kind], "enabled": True},
                f"Added {setup.METHOD_KINDS[kinds[kind]]} to {row.title}.",
            )
            return
        method = methods[picked]
        route = f"{base}/{method.get('instance_id', method.get('id'))}"
        on = bool(method.get("enabled"))
        what = self._pl_choose(
            lines[picked],
            "&Do:",
            ["Turn it off" if on else "Turn it on", "Change its cost", "Remove it"],
            "What to do with this method.",
        )
        if what is None:
            return
        if what == 2:
            if self._pl_preview(
                "Remove Method",
                f"Remove {lines[picked]} from {row.title}.",
                ["Shoppers in this zone can no longer choose it. There is no Trash."],
                "Remove",
            ):
                self._pl_send(
                    row.site,
                    "removing a method",
                    lambda: api.delete(route, force=True),
                    f"Removed the method from {row.title}.",
                )
            return
        loaded = {"enabled": on}
        if what == 0:
            body: dict[str, Any] = {"enabled": not on}
            lines_said = [f"{lines[picked]} is turned {'off' if on else 'on'}."]
        else:
            settings = method.get("settings") if isinstance(method.get("settings"), dict) else {}
            cost = (settings or {}).get("cost")
            if not isinstance(cost, dict):
                self.say("This method has no cost to change; its settings are in wp-admin.")  # type: ignore[attr-defined]
                return
            text = self._pl_ask(
                "Change Its Cost", "&Cost:", "Such as 5.00.", str(cost.get("value", ""))
            )
            if text is None:
                return
            body = {"settings": {"cost": text.strip()}}
            loaded = {"settings": {"cost": cost.get("value", "")}}
            lines_said = [f"Cost: {cost.get('value') or 'none'} becomes {text.strip()}."]
        if not self._pl_preview(
            "Change Method", f"Change a method in {row.title}.", lines_said, "Change Method"
        ):
            return
        self._pl_checked(
            row.site,
            "changing a shipping method",
            lambda: checked_write(
                api, route, body, _method_view(loaded), name=lines[picked], site=row.site
            ),
            f"Changed the method in {row.title}.",
            lambda w: self._pl_undo(api, route, _plain_undo(w.undo), "Put the method back."),
        )

    # -- taxes -------------------------------------------------------------------------------

    def _rate_answers(self, title: str, old: dict[str, Any]) -> dict[str, str] | None:
        answers: dict[str, str] = {}
        for key, prompt, help_text in _RATE_FIELDS:
            text = self._pl_ask(title, prompt, help_text, str(old.get(key, "") or ""))
            if text is None:
                return None
            answers[key] = text
        return answers

    def do_new_tax_rate(self, ref: Any, row: WbRow | None) -> None:
        site = self._shop_site(ref, row)
        if not site or not self._may_change(site):
            return
        answers = self._rate_answers("New Tax Rate", {})
        if answers is None:
            return
        try:
            body = setup.rate_body({}, answers)
        except ShopValueError as exc:
            self.say(f"{exc} Nothing was made.")  # type: ignore[attr-defined]
            return
        if self._pl_preview(
            "New Tax Rate",
            f"Make a tax rate on {site}.",
            setup.rate_preview("", {}, body, site),
            "Make Rate",
        ):
            self._pl_made(
                site,
                body["name"] or "the tax rate",
                setup.TAXES,
                body,
                f"Made the tax rate on {site}.",
            )

    def do_edit_tax_rate(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "shop_tax_rate":
            return
        old = dict(row.raw.get("_loaded", {}))
        answers = self._rate_answers(f"Edit Tax Rate - {row.title}", old)
        if answers is None:
            return
        try:
            body = setup.rate_body(old, answers)
        except ShopValueError as exc:
            self.say(f"{exc} Nothing was changed.")  # type: ignore[attr-defined]
            return
        if not body:
            self.say(f"Nothing about {row.title} would change.")  # type: ignore[attr-defined]
            return
        if not self._pl_preview(
            "Edit Tax Rate",
            f"Change {row.title} on {row.site}.",
            setup.rate_preview(row.title, old, body, row.site),
            "Change Rate",
        ):
            return
        api = self.ctx(row.site).api  # type: ignore[attr-defined]
        route = f"{setup.TAXES}/{row.object_id}"
        self._pl_checked(
            row.site,
            f"changing {row.title}",
            lambda: checked_write(api, route, body, old, name=row.title, site=row.site),
            f"Changed the tax rate {row.title} on {row.site}.",
            lambda w: self._pl_undo(api, route, dict(w.undo), f"Put {row.title} back."),
        )

    def do_new_tax_class(self, ref: Any, row: WbRow | None) -> None:
        site = self._shop_site(ref, row)
        if not site or not self._may_change(site):
            return
        name = self._pl_ask("New Tax Class", "&Name:", "Such as Food or Books.")
        if name is None or not name.strip():
            return
        if not self._pl_preview(
            "New Tax Class",
            f"Make the tax class {name.strip()} on {site}.",
            [f"A new tax class on {site}: {name.strip()}. Add its rates with Ctrl+N on Tax Rates."],
            "Make Class",
        ):
            return
        api = self.ctx(site).api  # type: ignore[attr-defined]

        def done(answer: Any) -> None:
            slug = answer.get("slug") if isinstance(answer, dict) else ""
            said = f"Made the tax class {name.strip()} on {site}."
            undo = None
            if slug:
                undo = lambda: (  # noqa: E731
                    api.delete(f"{setup.TAX_CLASSES}/{slug}", force=True),
                    f"Deleted the tax class {name.strip()}.",
                )[1]
            self.history.record(Change(f"{site}: {name.strip()}", said, undo=undo))  # type: ignore[attr-defined]
            self.say(said)  # type: ignore[attr-defined]
            self.refresh()  # type: ignore[attr-defined]

        self.background(
            "making the tax class",
            lambda: api.post(setup.TAX_CLASSES, {"name": name.strip()}),
            done,
        )  # type: ignore[attr-defined]

    # -- attribute terms ---------------------------------------------------------------------

    def do_attribute_terms(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "shop_attribute":
            return
        api = self.ctx(row.site).api  # type: ignore[attr-defined]
        base = f"{setup.ATTRIBUTES}/{row.object_id}/terms"

        def read() -> list[dict[str, Any]]:
            found = api.iter_collection(base, {}, per_page=100, max_pages=5)
            return [t for t in found if isinstance(t, dict)]

        def chosen(terms: list[dict[str, Any]]) -> None:
            names = [str(t.get("name", "") or "") for t in terms]
            picked = self._pl_choose(
                f"Terms - {row.title}",
                "&Terms:",
                [*names, "Add a term..."],
                "Each of the attribute's values, such as Small or Large; the last row adds one.",
            )
            if picked is None:
                return
            if picked == len(terms):
                name = self._pl_ask("Add a Term", "&Name:", f"A value of {row.title}.")
                if (
                    name
                    and name.strip()
                    and self._pl_preview(
                        "Add a Term",
                        f"Add {name.strip()} to {row.title}.",
                        [f"{row.title} gets the value {name.strip()}."],
                        "Add Term",
                    )
                ):
                    self._pl_made(
                        row.site,
                        name.strip(),
                        base,
                        {"name": name.strip()},
                        f"Added {name.strip()} to {row.title}.",
                    )
                return
            term = terms[picked]
            route = f"{base}/{term.get('id')}"
            do = self._pl_choose(
                names[picked], "&Do:", ["Rename it", "Delete it"], "What to do with this term."
            )
            if do == 1:
                if self._pl_preview(
                    "Delete Term",
                    f"Delete {names[picked]} from {row.title}.",
                    ["Products lose this value. There is no Trash."],
                    "Delete",
                ):
                    self._pl_send(
                        row.site,
                        "deleting a term",
                        lambda: api.delete(route, force=True),
                        f"Deleted {names[picked]} from {row.title}.",
                    )
                return
            if do != 0:
                return
            new = self._pl_ask("Rename Term", "Ne&w name:", "The value's name.", names[picked])
            if (
                not new
                or new.strip() == names[picked]
                or not self._pl_preview(
                    "Rename Term",
                    f"Rename {names[picked]}.",
                    [f"{names[picked]} becomes {new.strip()}."],
                    "Rename",
                )
            ):
                return
            body = {"name": new.strip()}
            self._pl_checked(
                row.site,
                "renaming a term",
                lambda: checked_write(api, route, body, term, name=names[picked], site=row.site),
                f"Renamed {names[picked]} to {new.strip()}.",
                lambda w: self._pl_undo(
                    api, route, dict(w.undo), f"Named it {names[picked]} again."
                ),
            )

        self.background(f"reading {row.title}'s terms", read, chosen)  # type: ignore[attr-defined]


def _method_view(loaded: dict[str, Any]) -> dict[str, Any]:
    """A method as loaded, in the shape its route answers (a setting is ``{"value": ...}``)."""
    settings = loaded.get("settings")
    if isinstance(settings, dict):
        return {"settings": {k: {"value": v} for k, v in settings.items()}}
    return loaded


def _plain_undo(undo: dict[str, Any]) -> dict[str, Any]:
    """A method's undo: a setting read back as ``{"value": x}`` is sent as ``x``."""
    settings = undo.get("settings")
    if isinstance(settings, dict):
        return {
            "settings": {
                k: v.get("value", "") if isinstance(v, dict) else v for k, v in settings.items()
            }
        }
    return undo
