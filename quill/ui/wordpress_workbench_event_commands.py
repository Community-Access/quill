"""The Events Calendar and Yoast SEO in the WordPress Workbench window (Packages 11 and 12).

A mixin built on :class:`quill.ui.wordpress_workbench_terms_seo.WorkbenchTermsSeoCommands`
(and through it the shop mixins' asking, preview, background and checked-write
helpers; Search Appearance and Edit SEO moved there with the Bulk SEO Editor);
the words and checks are wx-free in :mod:`quill.core.wordpress.workbench_events` and
:mod:`quill.core.wordpress.workbench_seo`. A recurring occurrence is refused
for Edit and Move to Trash with where its series is changed.
"""

from __future__ import annotations

from typing import Any

from quill.core.wordpress import workbench_events as ev
from quill.core.wordpress.plugin_events import EventDateError
from quill.core.wordpress.workbench_rows import WbRow
from quill.ui.wordpress_workbench_terms_seo import WorkbenchTermsSeoCommands

_PLACES = {
    "venue": ("venues", ev.VENUE_FIELDS, ev.venue_body),
    "organizer": ("organizers", ev.ORGANIZER_FIELDS, ev.organizer_body),
}


class WorkbenchEventCommands(WorkbenchTermsSeoCommands):
    """Events, venues and organizers (event terms and SEO are in the base mixins)."""

    # -- events -------------------------------------------------------------------------

    def _recurring_refused(self, row: WbRow) -> bool:
        if row.subkind == "recurring":
            self.say(ev.recurring_words({"recurring": True}))  # type: ignore[attr-defined]
            return True
        return False

    def _event_spec(self, title: str, old: dict[str, Any]) -> ev.EventSpec | None:
        answers: list[str] = []
        for key, prompt, help_text in (
            ("title", "&Title:", "The event's name."),
            ("start_date", "&Starts (YYYY-MM-DD HH:MM):", "In the event's own time zone."),
            ("end_date", "&Ends (YYYY-MM-DD HH:MM):", "In the event's own time zone."),
            (
                "time_zone",
                "Time &zone (blank for the site's):",
                "Such as America/New_York. Blank keeps the site's own time zone.",
            ),
            ("cost", "&Cost (blank for none):", "Such as Free, or 10."),
        ):
            value = str(old.get(key, "") or "")
            if key == "time_zone" and value == "the site's time zone":
                value = ""
            text = self._pl_ask(
                title, prompt, help_text, value[:16] if key.endswith("_date") else value
            )
            if text is None:
                return None
            answers.append(text)
        all_day = self._pl_choose(
            title, "&All day:", ["No, it has times", "Yes, all day"], "Whether times matter."
        )
        if all_day is None:
            return None
        name, start, end, zone, cost = answers
        return ev.EventSpec(
            name, start, end, all_day == 1, zone, int(old.get("venue_id") or 0), (), cost
        )

    def do_new_event(self, ref: Any, row: WbRow | None) -> None:
        site = self._shop_site(ref, row)
        if not site or not self._may_change(site):
            return
        spec = self._event_spec("New Event", {})
        if spec is None:
            return
        api = self.ctx(site).api  # type: ignore[attr-defined]

        def read_venues() -> list[dict[str, Any]]:
            return ev.collect(api, "venues", {})

        def chosen(venues: list[dict[str, Any]]) -> None:
            names = [ev.venue_row(v, site).title for v in venues]
            picked = self._pl_choose(
                "New Event", "&Venue:", ["No venue", *names], "Where it happens, if anywhere."
            )
            if picked is None:
                return
            venue_id = int(venues[picked - 1].get("id", 0) or 0) if picked else 0
            final = ev.EventSpec(
                spec.title,
                spec.start,
                spec.end,
                spec.all_day,
                spec.timezone,
                venue_id,
                (),
                spec.cost,
            )
            try:
                body = ev.event_body(final)
            except EventDateError as exc:
                self.say(f"{exc} Nothing was made.")  # type: ignore[attr-defined]
                return
            venue = names[picked - 1] if picked else ""
            if not self._pl_preview(
                "New Event",
                f"Make {final.title} on {site}.",
                ev.event_preview(final, body, site, venue=venue, new=True),
                "Make Event",
            ):
                return
            self._pl_send(
                site,
                f"making {final.title}",
                lambda: api.post(f"{ev.NAMESPACE}/events", body),
                f"Made {final.title} on {site}, as a draft.",
            )

        self.background("reading the venues", read_venues, chosen)  # type: ignore[attr-defined]

    def do_edit_event(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "tribe_event" or self._recurring_refused(row):
            return
        spec = self._event_spec(f"Edit Event - {row.title}", dict(row.raw))
        if spec is None:
            return
        try:
            body = ev.event_body(spec, row.raw)
        except EventDateError as exc:
            self.say(f"{exc} Nothing was changed.")  # type: ignore[attr-defined]
            return
        if not body:
            self.say(f"Nothing about {row.title} would change.")  # type: ignore[attr-defined]
            return
        if not self._pl_preview(
            "Edit Event",
            f"Change {row.title} on {row.site}.",
            ev.event_preview(spec, body, row.site, venue=str(row.raw.get("venue", "")), new=False),
            "Change Event",
        ):
            return
        api = self.ctx(row.site).api  # type: ignore[attr-defined]
        self._pl_send(
            row.site,
            f"changing {row.title}",
            lambda: api.post(f"{ev.NAMESPACE}/events/{row.object_id}", body),
            f"Changed {spec.title} on {row.site}.",
        )

    def do_trash_event(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "tribe_event" or self._recurring_refused(row):
            return
        self._pl_trash_place(row, "event", "events")

    def do_events_between(self, ref: Any, row: WbRow | None) -> None:
        site = self._shop_site(ref, row)
        if not site:
            return
        first = self._pl_ask("Events Between Dates", "&From (YYYY-MM-DD):", "The first day.")
        if first is None:
            return
        last = self._pl_ask("Events Between Dates", "&To (YYYY-MM-DD):", "The last day, included.")
        if last is None:
            return
        try:
            params = ev.between_params(first, last)
        except EventDateError as exc:
            self.say(str(exc))  # type: ignore[attr-defined]
            return
        ctx = self.ctx(site)  # type: ignore[attr-defined]

        def read() -> list[WbRow]:
            return ev.load_events(self.ensure(ctx), "upcoming", params)  # type: ignore[attr-defined]

        def done(rows: list[WbRow]) -> None:
            lines = [r.detail for r in rows] or ["No events in those dates."]
            self._pl_report(
                f"Events from {first.strip()} to {last.strip()} - {site}",
                "\n".join(lines),
                "Every event in those dates, one a line, in each event's own time zone.",
            )

        self.background("reading events between dates", read, done)  # type: ignore[attr-defined]

    # -- venues and organizers ------------------------------------------------------------

    def _pl_place(self, noun: str, title: str, old: dict[str, Any]) -> ev.VenueSpec | None:
        name = self._pl_ask(title, "&Name:", f"The {noun}'s name.", str(old.get("name", "") or ""))
        if name is None:
            return None
        values: dict[str, str] = {}
        for key in _PLACES[noun][1]:
            label = {"stateprovince": "State or province", "zip": "Postal code"}.get(
                key, key.capitalize()
            )
            text = self._pl_ask(
                title,
                f"&{label}:",
                f"The {noun}'s {label.lower()}, or blank.",
                str(old.get(key, "") or ""),
            )
            if text is None:
                return None
            values[key] = text
        return ev.VenueSpec(name, values)

    def _pl_new_place(self, ref: Any, row: WbRow | None, noun: str) -> None:
        site = self._shop_site(ref, row)
        if not site or not self._may_change(site):
            return
        spec = self._pl_place(noun, f"New {noun.title()}", {})
        if spec is None:
            return
        route, _fields, make = _PLACES[noun]
        try:
            body = make(spec)
        except EventDateError as exc:
            self.say(f"{exc} Nothing was made.")  # type: ignore[attr-defined]
            return
        if not self._pl_preview(
            f"New {noun.title()}",
            f"Make {spec.name} on {site}.",
            ev.place_preview(noun, body, site, new=True),
            f"Make {noun.title()}",
        ):
            return
        api = self.ctx(site).api  # type: ignore[attr-defined]
        self._pl_send(
            site,
            f"making {spec.name}",
            lambda: api.post(f"{ev.NAMESPACE}/{route}", body),
            f"Made the {noun} {spec.name} on {site}.",
        )

    def _pl_edit_place(self, row: WbRow | None, noun: str) -> None:
        if row is None or row.kind != f"tribe_{noun}":
            return
        spec = self._pl_place(noun, f"Edit {noun.title()} - {row.title}", dict(row.raw))
        if spec is None:
            return
        route, fields, make = _PLACES[noun]
        try:
            body = make(spec)
        except EventDateError as exc:
            self.say(f"{exc} Nothing was changed.")  # type: ignore[attr-defined]
            return
        body = {
            k: v
            for k, v in body.items()
            if k == noun and v != row.raw.get("name") or k in fields and v != row.raw.get(k)
        }
        cleared = [k for k in fields if row.raw.get(k) and not spec.values.get(k, "").strip()]
        body.update({k: "" for k in cleared})
        if not body:
            self.say(f"Nothing about {row.title} would change.")  # type: ignore[attr-defined]
            return
        if not self._pl_preview(
            f"Edit {noun.title()}",
            f"Change {row.title} on {row.site}.",
            ev.place_preview(noun, {noun: spec.name, **body}, row.site, new=False),
            f"Change {noun.title()}",
        ):
            return
        api = self.ctx(row.site).api  # type: ignore[attr-defined]
        self._pl_send(
            row.site,
            f"changing {row.title}",
            lambda: api.post(f"{ev.NAMESPACE}/{route}/{row.object_id}", body),
            f"Changed the {noun} {spec.name} on {row.site}.",
        )

    def _pl_trash_place(self, row: WbRow, noun: str, route: str) -> None:
        if not self._pl_preview(
            f"Move {noun.title()} to Trash",
            f"Move {row.title} on {row.site} to the Trash.",
            ev.trash_preview(noun, row.title, row.site),
            "Move to Trash",
        ):
            return
        api = self.ctx(row.site).api  # type: ignore[attr-defined]
        self._pl_send(
            row.site,
            f"trashing {row.title}",
            lambda: api.delete(f"{ev.NAMESPACE}/{route}/{row.object_id}"),
            f"Moved {row.title} to the Trash on {row.site}.",
        )

    def do_new_venue(self, ref: Any, row: WbRow | None) -> None:
        self._pl_new_place(ref, row, "venue")

    def do_new_organizer(self, ref: Any, row: WbRow | None) -> None:
        self._pl_new_place(ref, row, "organizer")

    def do_edit_venue(self, _ref: Any, row: WbRow | None) -> None:
        self._pl_edit_place(row, "venue")

    def do_edit_organizer(self, _ref: Any, row: WbRow | None) -> None:
        self._pl_edit_place(row, "organizer")

    def do_trash_venue(self, _ref: Any, row: WbRow | None) -> None:
        if row is not None and row.kind == "tribe_venue":
            self._pl_trash_place(row, "venue", "venues")

    def do_trash_organizer(self, _ref: Any, row: WbRow | None) -> None:
        if row is not None and row.kind == "tribe_organizer":
            self._pl_trash_place(row, "organizer", "organizers")
