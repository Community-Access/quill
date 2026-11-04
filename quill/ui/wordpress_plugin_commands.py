"""Plugins QUILL recognises: events, products and SEO (wordpress.md 9.15).

A mixin of :class:`~quill.ui.wordpress_commands.WordPressCommands`. When a
recognised plugin's namespace is in the site's index, QUILL adds a small,
plain extra for it; without the plugin nothing shows, and a command reached
anyway says why in one sentence.

* **The Events Calendar:** Coming Up, New Event, and an event's start, end
  and venue in Properties and Plugin Fields.
* **WooCommerce:** a product's price and stock in Properties, the prices and
  stock changeable in Plugin Fields (Shop Orders is in
  :mod:`quill.ui.wordpress_shop_commands`).
* **SEO plugins** (Yoast SEO, Rank Math) that register their meta: the SEO
  title and description with their lengths.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from quill.core.wordpress import plugin_events as ev
from quill.core.wordpress import plugin_shop_seo as shop
from quill.core.wordpress import site as wp
from quill.core.wordpress import site_features as sf
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.block_catalog import Field
from quill.ui import wordpress_block_dialogs as bdlg
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_plugin_dialogs as pdlg
from quill.ui.wordpress_api_site_base import WordPressApiSiteBase, plain_error, role_cannot

if TYPE_CHECKING:
    from quill.core.wordpress import local as lc
    from quill.core.wordpress import sites as st


def no_events(site_name: str) -> str:
    return f"{site_name} does not have The Events Calendar, so there are no events for QUILL."


@dataclass
class Extras:
    """What the site's plugins add to one page, post, event or product."""

    event: ev.Event | None = None
    venues: list[ev.Venue] = field(default_factory=list)
    product: shop.Product | None = None
    seo: list[tuple[str, str, int, str]] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        return self.event is None and self.product is None and not self.seo

    def facts(self) -> str:
        text = ""
        if self.event is not None:
            text += self.event.facts()
        if self.product is not None:
            text += self.product.facts()
        text += "".join(
            f"{label}: {value or '(empty)'}\n{shop.length_note(label, value, limit)}\n"
            for _k, label, limit, value in self.seo
        )
        return text


def load_extras(api: Any, index: sf.SiteIndex, copy: lc.WorkingCopy, *, venues: bool) -> Extras:
    """Everything the recognised plugins add to *copy*; a part that fails is left out."""
    found = Extras()

    def attempt(work: Callable[[], Any]) -> Any:
        try:
            return work()
        except WordPressApiError:
            return None

    if copy.kind in ev.EVENT_KINDS and index.supports(ev.NAMESPACE):
        found.event = attempt(lambda: ev.load_event(api, copy.remote_id))
        if found.event is not None and venues:
            found.venues = attempt(lambda: ev.list_venues(api)) or []
    if copy.kind in shop.PRODUCT_KINDS and index.supports(shop.SHOP_NAMESPACE):
        found.product = attempt(lambda: shop.load_product(api, copy.remote_id))
    if any(index.supports(ns) for ns in shop.SEO_NAMESPACES):
        meta = attempt(lambda: shop.load_meta(api, copy.kind, copy.remote_id)) or {}
        found.seo = shop.seo_fields(meta)
    return found


class WordPressPluginCommands(WordPressApiSiteBase):
    # ------------------------------------------------------------------ #
    # Properties: the plugins' facts, read once when Properties opens

    def plugin_facts(
        self, copy: lc.WorkingCopy, profile: st.SiteProfile, then: Callable[[str], None]
    ) -> None:
        """Hand *then* the plugins' lines for Properties ("" when there are none).

        A copy not yet on the site has none, and nothing is read. Any failure
        is quiet: Properties still opens with what it always showed.
        """
        if not copy.remote_id:
            then("")
            return
        api = self.api(profile)  # type: ignore[attr-defined]

        def job() -> str:
            try:
                index = self.site_facts(profile, api)[0]
            except WordPressApiError:
                return ""
            extras = load_extras(api, index, copy, venues=False)
            if extras.empty:
                return ""
            return extras.facts() + "Change these with File, WordPress, Plugin Fields.\n"

        self.host.run_task(
            "WordPress: reading what the site's plugins add",
            job,
            then,
            lambda _exc: then(""),
        )

    # ------------------------------------------------------------------ #
    # Plugin Fields

    def cmd_plugin_fields(self) -> None:
        found = self.current("Plugin Fields")  # type: ignore[attr-defined]
        if found is None:
            return
        copy, profile = found
        if not copy.remote_id:
            self.host.announce(
                f"This is not on {profile.name} yet. Save Draft to Site first; then its plugin "
                "fields can be filled in."
            )
            return
        self.when_offered(
            profile,
            f"reading what {profile.name}'s plugins add",
            lambda _index, _account: "",
            lambda api, index, _account: load_extras(api, index, copy, venues=True),
            lambda extras: self._edit_extras(copy, profile, extras),
        )

    def _edit_extras(self, copy: lc.WorkingCopy, profile: st.SiteProfile, extras: Extras) -> None:
        if extras.empty:
            self.host.announce(f"{profile.name}'s plugins add no fields to this {copy.kind}.")
            return
        fields: list[Field] = []
        limits: dict[str, int] = {}
        if extras.event is not None:
            e = extras.event
            fields += [
                Field(
                    "start",
                    "&Starts:",
                    "text",
                    "When it starts, such as 2026-11-21 10:00.",
                    e.start[:16],
                ),
                Field(
                    "end", "&Ends:", "text", "When it ends, such as 2026-11-21 16:00.", e.end[:16]
                ),
                Field(
                    "venue",
                    "&Venue:",
                    "choice",
                    "Where it is, from the site's venues.",
                    e.venue_id,
                    ["No venue", *(v.name for v in extras.venues)],
                    [0, *(v.id for v in extras.venues)],
                ),
            ]
        if extras.product is not None:
            p = extras.product
            fields += [
                Field(
                    "regular_price",
                    "&Regular price:",
                    "text",
                    "The usual price, such as 12.50.",
                    p.regular_price,
                ),
                Field(
                    "sale_price",
                    "S&ale price:",
                    "text",
                    "A sale price, or empty for no sale.",
                    p.sale_price,
                ),
            ]
            if p.manage_stock:
                fields.append(
                    Field(
                        "stock", "Stoc&k:", "text", "How many are left.", str(p.stock_quantity or 0)
                    )
                )
        for key, label, limit, value in extras.seo:
            title = label.endswith("title")
            fields.append(
                Field(
                    key,
                    "SEO &title:" if title else "SEO &description:",
                    "text" if title else "multiline",
                    f"The {label} search engines show. About {limit} characters fit.",
                    value,
                )
            )
            limits[key] = limit
        answers = pdlg.ask_plugin_fields(
            self.host.parent,
            self.host.show_modal,
            title=f"Plugin Fields, {copy.title or 'untitled'}",
            purpose=f"The fields {profile.name}'s plugins add. Save to Site sends them at once.",
            fields=fields,
            limits=limits,
            announce=self.host.announce,
        )
        if answers is None:
            return
        self._save_extras(copy, profile, extras, answers)

    def _save_extras(
        self, copy: lc.WorkingCopy, profile: st.SiteProfile, extras: Extras, answers: dict[str, Any]
    ) -> None:
        jobs: list[Callable[[Any], None]] = []
        said: list[str] = []
        try:
            if extras.event is not None:
                start = ev.parse_when(str(answers["start"]), label="The start")
                end = ev.parse_when(str(answers["end"]), label="The end")
                if end < start:
                    self.host.announce("The event ends before it starts. Nothing was saved.")
                    return
                venue = int(answers.get("venue") or 0)
                event_id = extras.event.id or copy.remote_id
                jobs.append(lambda api: ev.update_event(api, event_id, start, end, venue))
                said.append("the event's dates and venue")
            if extras.product is not None:
                product = extras.product
                regular = shop.check_price(str(answers["regular_price"]), label="The regular price")
                sale = shop.check_price(str(answers["sale_price"]), label="The sale price")
                stock = shop.check_quantity(str(answers["stock"])) if "stock" in answers else None
                if regular != product.regular_price or sale != product.sale_price:
                    if not dlg.confirm(
                        self.host.parent,
                        self.host.show_modal,
                        title="Change Price",
                        message=(
                            f"Change the price of {product.name} on {profile.name}? Customers "
                            f"see it at once. Regular price {regular or 'none'}, sale price "
                            f"{sale or 'none'}."
                        ),
                        yes_label="Change Price",
                    ):
                        return
                jobs.append(
                    lambda api: shop.update_product(
                        api,
                        product.id,
                        regular_price=regular,
                        sale_price=sale,
                        stock_quantity=stock,
                    )
                )
                said.append("the price and stock")
        except ValueError as exc:
            self.host.announce(plain_error(exc) + " Nothing was saved.")
            return
        changed = {
            key: str(answers.get(key, ""))
            for key, _l, _m, value in extras.seo
            if str(answers.get(key, "")) != value
        }
        if changed:
            jobs.append(lambda api: shop.save_meta(api, copy.kind, copy.remote_id, changed))
            said.append("the SEO fields")
        api = self.api(profile)  # type: ignore[attr-defined]

        def work() -> None:
            for job in jobs:
                job(api)

        self.background(  # type: ignore[attr-defined]
            f"saving plugin fields to {profile.name}",
            work,
            lambda _r: self.host.announce(f"Saved to {profile.name}: {', '.join(said)}."),
        )

    # ------------------------------------------------------------------ #
    # Coming Up and New Event

    def cmd_events_coming_up(self) -> None:
        profile = self.chosen_site("Coming Up")
        if profile is None:
            return
        self.when_offered(
            profile,
            f"reading what is coming up on {profile.name}",
            lambda index, _account: "" if index.supports(ev.NAMESPACE) else no_events(profile.name),
            lambda api, _index, _account: ev.coming_up(api),
            lambda events: self._show_coming_up(profile, events),
        )

    def _show_coming_up(self, profile: st.SiteProfile, events: list[ev.Event]) -> None:
        if not events:
            self.host.announce(f"Nothing is coming up on {profile.name}.")
            return

        def open_one(index: int | None) -> object:
            if index is None or index >= len(events):
                return None
            self.open_item(profile, "tribe_events", events[index].id)  # type: ignore[attr-defined]
            return dlg.CLOSE

        def on_site(index: int | None) -> object:
            if index is not None and index < len(events) and events[index].url:
                self.host.open_in_browser(events[index].url)
            return None

        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title=f"Coming Up, {profile.name}",
            purpose=f"Every event from today on {profile.name}, soonest first.",
            list_label="&Events:",
            list_help="Each event's name, when it is, and where.",
            rows=[e.spoken() for e in events],
            on_enter=open_one,
            actions=[
                dlg.Action("&Open", "Open the selected event in the editor.", open_one),
                dlg.Action("Open on &Site", "Open the event's page in your browser.", on_site),
            ],
        )
        window.Destroy()

    def cmd_new_event(self) -> None:
        profile = self.chosen_site("New Event")
        if profile is None:
            return

        def why_not(index: sf.SiteIndex, account: wp.Account) -> str:
            if not index.supports(ev.NAMESPACE):
                return no_events(profile.name)
            return role_cannot(profile.name, account, "edit_posts", "add events")

        self.when_offered(
            profile,
            f"reading {profile.name}'s venues",
            why_not,
            lambda api, _index, _account: _venues_or_none(api),
            lambda venues: self._ask_new_event(profile, venues),
        )

    def _ask_new_event(self, profile: st.SiteProfile, venues: list[ev.Venue]) -> None:
        answers = bdlg.ask_fields(
            self.host.parent,
            self.host.show_modal,
            title="New Event",
            purpose=f"A new event on {profile.name}, made as a draft. Nothing is public yet.",
            fields=[
                Field("title", "&Name:", "text", "What the event is called."),
                Field("start", "&Starts:", "text", "When it starts, such as 2026-11-21 10:00."),
                Field("end", "&Ends:", "text", "When it ends, such as 2026-11-21 16:00."),
                Field(
                    "venue",
                    "&Venue:",
                    "choice",
                    "Where it is, from the site's venues.",
                    0,
                    ["No venue", *(v.name for v in venues)],
                    [0, *(v.id for v in venues)],
                ),
            ],
            ok_label="Make Draft",
        )
        if answers is None:
            return
        title = str(answers.get("title", "")).strip()
        if not title:
            self.host.announce("An event needs a name. Nothing was made.")
            return
        try:
            start = ev.parse_when(str(answers.get("start", "")), label="The start")
            end = ev.parse_when(str(answers.get("end", "")) or start, label="The end")
        except ValueError as exc:
            self.host.announce(plain_error(exc) + " Nothing was made.")
            return
        if end < start:
            self.host.announce("The event ends before it starts. Nothing was made.")
            return
        api = self.api(profile)  # type: ignore[attr-defined]
        venue = int(answers.get("venue") or 0)

        def done(event: ev.Event) -> None:
            self.host.announce(f"Event {event.title} made as a draft on {profile.name}.")
            if event.id:
                self.open_item(profile, "tribe_events", event.id)  # type: ignore[attr-defined]

        self.background(  # type: ignore[attr-defined]
            f"making an event on {profile.name}",
            lambda: ev.create_event(api, title, start, end, venue),
            done,
        )


def _venues_or_none(api: Any) -> list[ev.Venue]:
    try:
        return ev.list_venues(api)
    except WordPressApiError:
        return []
