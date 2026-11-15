"""WooCommerce's reviews, webhooks, customers' details and variations in the Workbench window.

A mixin on :class:`quill.ui.wordpress_workbench_shop_commands.WorkbenchShopCommands`;
the words, checks and bodies are wx-free in
:mod:`quill.core.wordpress.workbench_shop_care`. Every write is previewed,
then checked against the site again before it is sent, verified after, and
recorded in the Change History with an undo where putting the old values
back truly restores them (:mod:`quill.core.wordpress.workbench_plugin_write`).
A change to several reviews says how each went. A customer's personal
details are read only when asked for, only for a role WooCommerce lets read
them, and never spoken in a list.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from quill.core.wordpress import workbench_shop_care as care
from quill.core.wordpress import workbench_shop_catalog as cat
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.plugin_shop_seo import ShopValueError
from quill.core.wordpress.workbench_edit import EditConflict
from quill.core.wordpress.workbench_plugin_write import (
    Outcome,
    Written,
    checked_write,
    outcomes_report,
)
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.history import Change
from quill.ui.wordpress_workbench_shop_commands import WorkbenchShopCommands

_STATUS_VERBS = {"approved": "Approved", "hold": "Held", "spam": "Marked as spam"}


class WorkbenchShopCareCommands(WorkbenchShopCommands):
    """Checked writes, and the review, webhook, customer and variation handlers."""

    # -- checked writes, shared by the plugin mixins ----------------------------------------

    def _pl_undo(
        self, api: Any, route: str, body: dict[str, Any], said: str
    ) -> Callable[[], str] | None:
        if not body:
            return None
        return lambda: (api.post(route, body), said)[1]

    def _pl_checked(
        self,
        site: str,
        name: str,
        write: Callable[[], Written],
        said: str,
        undo: Callable[[Written], Callable[[], str] | None] | None = None,
    ) -> None:
        """Run *write* (a :func:`checked_write`) off the UI thread; record, say, refresh."""

        def done(written: Written) -> None:
            text = said + written.tail()
            self.history.record(  # type: ignore[attr-defined]
                Change(f"{site}: {name}", text, undo=undo(written) if undo else None)
            )
            self.say(text)  # type: ignore[attr-defined]
            self.refresh()  # type: ignore[attr-defined]

        self.background(name, write, done)  # type: ignore[attr-defined]

    def _pl_many(
        self,
        rows: Sequence[WbRow],
        what: str,
        each: Callable[[WbRow], tuple[str, Callable[[], str] | None]],
    ) -> None:
        """Run *each* on every row off the UI thread: an outcome each, one undo for all."""
        site = rows[0].site

        def work() -> tuple[list[Outcome], list[Callable[[], str]]]:
            outcomes, undos = [], []
            for row in rows:
                try:
                    said, undo = each(row)
                except (WordPressApiError, EditConflict, ShopValueError) as exc:
                    plain = getattr(exc, "plain", "") or str(exc)
                    outcomes.append(Outcome(row.title, False, f"{row.title}: {plain}"))
                    continue
                outcomes.append(Outcome(row.title, True, f"{row.title}: {said}"))
                if undo is not None:
                    undos.append(undo)
            return outcomes, undos

        def done(result: tuple[list[Outcome], list[Callable[[], str]]]) -> None:
            outcomes, undos = result
            said, report = outcomes_report(outcomes, what)
            undo = None
            if undos:
                undo = lambda: (  # noqa: E731
                    [u() for u in undos],
                    f"Put {len(undos)} back as they were on {site}.",
                )[1]
            self.history.record(Change(f"{site}: {what}", said, undo=undo))  # type: ignore[attr-defined]
            self.say(said)  # type: ignore[attr-defined]
            if len(outcomes) > 1 or any(not o.ok for o in outcomes):
                self._pl_report(what, report, "How each one went, one a line.")
            self.refresh()  # type: ignore[attr-defined]

        self.background(what.lower(), work, done)  # type: ignore[attr-defined]

    # -- product reviews ------------------------------------------------------------------

    def _review_rows(self, row: WbRow | None) -> list[WbRow]:
        chosen = self.selected_rows() or ([row] if row is not None else [])  # type: ignore[attr-defined]
        rows = [r for r in chosen if r.kind == "shop_review"]
        if rows and any(r.site != rows[0].site for r in rows):
            self.say("Change reviews on one site at a time.")  # type: ignore[attr-defined]
            return []
        return rows

    def _review_status(self, row: WbRow | None, status: str) -> None:
        rows = self._review_rows(row)
        if not rows:
            return
        site = rows[0].site
        verb = _STATUS_VERBS[status]
        if not self._pl_preview(
            f"{verb} Reviews",
            f"{len(rows)} review{'s' if len(rows) != 1 else ''} on {site}.",
            care.review_status_preview(rows, status, site),
            verb.split()[0] if status != "spam" else "Mark as Spam",
        ):
            return
        api = self.ctx(site).api  # type: ignore[attr-defined]

        def each(r: WbRow) -> tuple[str, Callable[[], str] | None]:
            route = f"{care.REVIEWS}/{r.object_id}"
            body = {"status": status}
            written = checked_write(
                api, route, body, r.raw.get("_loaded", {}), name=r.title, site=site
            )
            back = dict(written.undo)
            undo = self._pl_undo(api, route, back, f"Put the review back as {back.get('status')}.")
            return care.REVIEW_STATUSES[status] + written.tail(), undo

        self._pl_many(rows, f"{verb} reviews", each)

    def do_approve_review(self, _ref: Any, row: WbRow | None) -> None:
        self._review_status(row, "approved")

    def do_hold_review(self, _ref: Any, row: WbRow | None) -> None:
        self._review_status(row, "hold")

    def do_spam_review(self, _ref: Any, row: WbRow | None) -> None:
        self._review_status(row, "spam")

    def do_trash_review(self, _ref: Any, row: WbRow | None) -> None:
        rows = self._review_rows(row)
        if not rows:
            return
        site = rows[0].site
        if not self._pl_preview(
            "Move Reviews to Trash",
            f"{len(rows)} review{'s' if len(rows) != 1 else ''} on {site} to the Trash.",
            [*(r.detail for r in rows), "Ctrl+Z takes them out of the Trash again."],
            "Move to Trash",
        ):
            return
        api = self.ctx(site).api  # type: ignore[attr-defined]

        def each(r: WbRow) -> tuple[str, Callable[[], str] | None]:
            route = f"{care.REVIEWS}/{r.object_id}"
            api.delete(route)
            return "moved to the Trash", self._pl_undo(
                api, route, {"status": "untrash"}, "Took the review out of the Trash."
            )

        self._pl_many(rows, "Moved reviews to the Trash", each)

    def do_edit_review(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "shop_review":
            return
        loaded = row.raw.get("_loaded", {})
        title = f"Edit Review - {row.title}"
        words = self._pl_ask(
            title, "&Review:", "The review's words.", str(loaded.get("review", ""))
        )
        if words is None:
            return
        rating = self._pl_ask(
            title, "&Rating (1 to 5):", "A whole number.", str(loaded.get("rating", "") or "")
        )
        if rating is None:
            return
        try:
            body = care.review_edit_body(loaded, words, rating)
        except ShopValueError as exc:
            self.say(f"{exc} Nothing was changed.")  # type: ignore[attr-defined]
            return
        if not body:
            self.say("Nothing about the review would change.")  # type: ignore[attr-defined]
            return
        lines = [
            f"{k.capitalize()}: {loaded.get(k) or 'none'} becomes {v}." for k, v in body.items()
        ]
        if not self._pl_preview(
            "Edit Review",
            f"Change a review on {row.site}.",
            [*lines, "The reviewer is not told."],
            "Change Review",
        ):
            return
        api = self.ctx(row.site).api  # type: ignore[attr-defined]
        route = f"{care.REVIEWS}/{row.object_id}"
        self._pl_checked(
            row.site,
            "changing a review",
            lambda: checked_write(api, route, body, loaded, name="The review", site=row.site),
            f"Changed the review on {row.site}.",
            lambda w: self._pl_undo(api, route, dict(w.undo), "Put the review back."),
        )

    def do_reply_review(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "shop_review":
            return
        text = self._pl_ask(
            f"Reply - {row.title}", "&Reply:", "Shown under the review, as you.", ""
        )
        if text is None:
            return
        try:
            body = care.reply_body(row, text)
        except ShopValueError as exc:
            self.say(f"{exc} Nothing was sent.")  # type: ignore[attr-defined]
            return
        if not self._pl_preview(
            "Reply to Review",
            f"Reply on {row.site}.",
            [
                f"Under {row.cells.get('reviewer', '')}'s review of "
                f"{row.cells.get('product', '')}:",
                body["content"],
                "It shows on the product's page as soon as it is sent.",
            ],
            "Send Reply",
        ):
            return
        api = self.ctx(row.site).api  # type: ignore[attr-defined]

        def done(answer: Any) -> None:
            said = f"Replied to the review on {row.site}."
            reply_id = answer.get("id") if isinstance(answer, dict) else None
            undo = None
            if reply_id:
                undo = lambda: (  # noqa: E731
                    api.delete(f"wp/v2/comments/{reply_id}"),
                    "Moved the reply to the Trash.",
                )[1]
            self.history.record(Change(f"{row.site}: a reply", said, undo=undo))  # type: ignore[attr-defined]
            self.say(said)  # type: ignore[attr-defined]

        self.background("sending the reply", lambda: api.post("wp/v2/comments", body), done)  # type: ignore[attr-defined]

    # -- webhooks ---------------------------------------------------------------------------

    def do_new_webhook(self, ref: Any, row: WbRow | None) -> None:
        site = self._shop_site(ref, row)
        if not site or not self._may_change(site):
            return
        name = self._pl_ask("New Webhook", "&Name:", "What it is for, such as Orders to Sheets.")
        if name is None:
            return
        topics = list(care.WEBHOOK_TOPICS)
        picked = self._pl_choose(
            "New Webhook",
            "&Send when:",
            [care.WEBHOOK_TOPICS[t] for t in topics],
            "What makes WooCommerce send it.",
        )
        if picked is None:
            return
        url = self._pl_ask(
            "New Webhook", "&Delivery address:", "Where it is sent; it must start with https://."
        )
        if url is None:
            return
        try:
            body = care.webhook_body(name, topics[picked], url)
        except ShopValueError as exc:
            self.say(f"{exc} Nothing was made.")  # type: ignore[attr-defined]
            return
        if not self._pl_preview(
            "New Webhook",
            f"Make a webhook on {site}.",
            care.webhook_preview(body, site),
            "Make Webhook",
        ):
            return
        api = self.ctx(site).api  # type: ignore[attr-defined]

        def done(answer: Any) -> None:
            said = f"Made the webhook {body['name']} on {site}."
            made = answer.get("id") if isinstance(answer, dict) else None
            undo = None
            if made:
                undo = lambda: (  # noqa: E731
                    api.delete(f"{care.WEBHOOKS}/{made}", force=True),
                    f"Deleted the webhook {body['name']}.",
                )[1]
            self.history.record(Change(f"{site}: {body['name']}", said, undo=undo))  # type: ignore[attr-defined]
            self.say(said)  # type: ignore[attr-defined]
            self.refresh()  # type: ignore[attr-defined]

        self.background("making the webhook", lambda: api.post(care.WEBHOOKS, body), done)  # type: ignore[attr-defined]

    def do_toggle_webhook(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "shop_webhook":
            return
        new = "paused" if row.status == "active" else "active"
        if not self._pl_preview(
            "Pause or Activate Webhook",
            f"{row.title} on {row.site} becomes {new}.",
            [
                f"{row.title}: {row.status or 'unknown'} becomes {new}.",
                "Paused, WooCommerce sends nothing to its address; activated, it sends again.",
            ],
            "Pause" if new == "paused" else "Activate",
        ):
            return
        api = self.ctx(row.site).api  # type: ignore[attr-defined]
        route = f"{care.WEBHOOKS}/{row.object_id}"
        body = {"status": new}
        self._pl_checked(
            row.site,
            f"changing {row.title}",
            lambda: checked_write(
                api, route, body, row.raw.get("_loaded", {}), name=row.title, site=row.site
            ),
            f"{row.title} on {row.site} is {new}.",
            lambda w: self._pl_undo(api, route, dict(w.undo), f"{row.title} is as it was."),
        )

    def do_delete_webhook(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "shop_webhook":
            return
        if not self._pl_preview(
            "Delete Webhook",
            f"Delete {row.title} on {row.site} for good.",
            [
                row.detail,
                "Webhooks have no Trash, so this cannot be undone; Pause stops it "
                "without deleting it.",
            ],
            "Delete Webhook",
        ):
            return
        api = self.ctx(row.site).api  # type: ignore[attr-defined]
        self._pl_send(
            row.site,
            f"deleting {row.title}",
            lambda: api.delete(f"{care.WEBHOOKS}/{row.object_id}", force=True),
            f"Deleted the webhook {row.title} on {row.site}.",
        )

    # -- customers --------------------------------------------------------------------------

    def _may_read_people(self, site: str) -> bool:
        account = self.account_for(site)  # type: ignore[attr-defined]
        if account is not None and not account.can("list_users"):
            self.say(  # type: ignore[attr-defined]
                f"WooCommerce lets only roles that can list people read a customer's details, "
                f"and yours on {site} cannot."
            )
            return False
        return True

    def _read_customer(self, row: WbRow, then: Callable[[dict[str, Any]], None]) -> None:
        api = self.ctx(row.site).api  # type: ignore[attr-defined]

        def read() -> dict[str, Any]:
            found = api.get(f"{care.CUSTOMERS}/{row.object_id}", context="edit")
            return found if isinstance(found, dict) else {}

        self.background(f"reading {row.title}", read, then)  # type: ignore[attr-defined]

    def do_customer_details(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "shop_customer" or not self._may_read_people(row.site):
            return
        self._read_customer(
            row,
            lambda raw: self._pl_report(
                f"Customer Details - {row.title}",
                "\n".join(care.customer_lines(raw)),
                "Personal details, read from WooCommerce now and kept only while this is open.",
            ),
        )

    def do_edit_customer(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "shop_customer" or not self._may_read_people(row.site):
            return
        parts = ["account", "billing", "shipping"]
        picked = self._pl_choose(
            f"Edit Customer - {row.title}",
            "&Change:",
            ["Name and email", "Billing address", "Shipping address"],
            "Which of the customer's details to change.",
        )
        if picked is None:
            return
        part = parts[picked]

        def chosen(raw: dict[str, Any]) -> None:
            fields = (
                [("first_name", "First name"), ("last_name", "Last name"), ("email", "Email")]
                if part == "account"
                else list(care.ADDRESS_FIELDS)
            )
            source = raw if part == "account" else (raw.get(part) or {})
            values: dict[str, str] = {}
            for key, label in fields:
                text = self._pl_ask(
                    f"Edit Customer - {row.title}",
                    f"&{label}:",
                    f"The customer's {label.lower()}.",
                    str(source.get(key, "") or ""),
                )
                if text is None:
                    return
                values[key] = text
            try:
                body = care.customer_body(raw, care.CustomerEdit(part, values))
            except ShopValueError as exc:
                self.say(f"{exc} Nothing was changed.")  # type: ignore[attr-defined]
                return
            if not body:
                self.say(f"Nothing about {row.title} would change.")  # type: ignore[attr-defined]
                return
            if not self._pl_preview(
                "Edit Customer",
                f"Change {row.title}'s details on {row.site}.",
                care.customer_preview(row.title, raw, body),
                "Change Customer",
            ):
                return
            api = self.ctx(row.site).api  # type: ignore[attr-defined]
            route = f"{care.CUSTOMERS}/{row.object_id}"
            self._pl_checked(
                row.site,
                f"changing {row.title}",
                lambda: checked_write(api, route, body, raw, name=row.title, site=row.site),
                f"Changed {row.title}'s details on {row.site}.",
                lambda w: self._pl_undo(api, route, dict(w.undo), f"Put {row.title}'s back."),
            )

        self._read_customer(row, chosen)

    # -- variations -------------------------------------------------------------------------

    def do_edit_variation(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "shop_product":
            return
        api = self.ctx(row.site).api  # type: ignore[attr-defined]
        base = f"{cat.product_route(row.object_id)}/variations"

        def read() -> list[dict[str, Any]]:
            found = api.iter_collection(base, {}, per_page=100, max_pages=3)
            return [v for v in found if isinstance(v, dict)]

        def chosen(variations: list[dict[str, Any]]) -> None:
            if not variations:
                self.say(f"{row.title} has no variations; it is not a variable product.")  # type: ignore[attr-defined]
                return
            picked = self._pl_choose(
                f"Edit Variation - {row.title}",
                "&Variation:",
                cat.variation_lines(variations),
                "The variation to change.",
            )
            if picked is None:
                return
            raw = variations[picked]
            title = f"Edit Variation - {care.variation_name(raw)}"
            answers = []
            for key, prompt, help_text in (
                ("regular_price", "&Regular price:", "Such as 12.50, with no currency sign."),
                ("sale_price", "&Sale price (blank for none):", "Blank ends a sale."),
                ("stock_quantity", "S&tock count (blank to leave):", "A whole number."),
            ):
                text = self._pl_ask(title, prompt, help_text, str(raw.get(key, "") or ""))
                if text is None:
                    return
                answers.append(text)
            statuses = list(care.VARIATION_STATUSES)
            status = self._pl_choose(
                title,
                "St&atus:",
                [care.VARIATION_STATUSES[s] for s in statuses],
                "Whether shoppers can choose this variation.",
            )
            if status is None:
                return
            try:
                body = care.variation_body(raw, *answers, statuses[status])
            except ShopValueError as exc:
                self.say(f"{exc} Nothing was changed.")  # type: ignore[attr-defined]
                return
            if not body:
                self.say("Nothing about the variation would change.")  # type: ignore[attr-defined]
                return
            if not self._pl_preview(
                "Edit Variation",
                f"Change a variation of {row.title} on {row.site}.",
                care.variation_preview(row.title, raw, body),
                "Change Variation",
            ):
                return
            route = f"{base}/{raw.get('id')}"
            name = f"{row.title}, {care.variation_name(raw)}"
            self._pl_checked(
                row.site,
                f"changing {name}",
                lambda: checked_write(api, route, body, raw, name=name, site=row.site),
                f"Changed {name} on {row.site}.",
                lambda w: self._pl_undo(api, route, dict(w.undo), f"Put {name} back."),
            )

        self.background(f"reading {row.title}'s variations", read, chosen)  # type: ignore[attr-defined]
