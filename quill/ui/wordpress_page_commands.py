"""Scheduling, autosaves on Open, restoring from the Trash, and the add-to-menu offer.

Plan: wordpress.md 5.2, 5.8, 5.9, 9.3. The autosave timer and the offline
queue are in :mod:`quill.ui.wordpress_offline_commands`, the half this class
inherits.

A mixin of :class:`~quill.ui.wordpress_commands.WordPressCommands`, shared by
QUILL and QUILL Lite; it reaches the editor only through ``self.host``.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from typing import Any

from quill.core.wordpress import local as lc
from quill.core.wordpress import schedule as sch
from quill.core.wordpress import site as wp
from quill.core.wordpress.api import WordPressApiError
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_schedule_dialog as sdlg
from quill.ui.wordpress_offline_commands import WordPressOfflineCommands


class WordPressPageCommands(WordPressOfflineCommands):
    # Provided by WordPressCommands.
    host: Any
    local: lc.LocalStore

    # ------------------------------------------------------------------ #
    # Schedule Publish, Change Schedule, Publish Now (5.8)

    def cmd_schedule(self) -> None:
        found = self.current()  # type: ignore[attr-defined]
        if found is None:
            return
        if not self.host.save_current():
            return
        copy, profile = found
        copy = self.local.copy_for_path(self.host.current_path()) or copy
        if copy.status == "future" and copy.remote_id:
            stamp = str(copy.properties.get("date_gmt", ""))
            when = f" for {sch.when_spoken(stamp)}" if stamp else ""
            choice = dlg.ask_choice(
                self.host.parent,
                self.host.show_modal,
                title=f"Scheduled on {profile.name}",
                prompt="&What now:",
                rows=["Change the schedule", "Publish now"],
                help_text=(
                    f"'{copy.title or 'untitled'}' is scheduled to publish on {profile.name}"
                    f"{when}. Change the schedule picks a new time; Publish now makes it public "
                    "straight away."
                ),
            )
            if choice is None:
                return
            if choice == 1:
                self._publish_now(copy, profile)
                return
        api = self.api(profile)  # type: ignore[attr-defined]

        def zone() -> str:
            try:
                return sch.site_time_zone(api)
            except WordPressApiError:
                return ""  # the send will say why, if the site is away

        self.background(  # type: ignore[attr-defined]
            f"reading the time zone of {profile.name}",
            zone,
            lambda site_zone: self._ask_when(copy, profile, site_zone),
        )

    def _ask_when(self, copy: lc.WorkingCopy, profile: Any, site_zone: str) -> None:
        keys = sch.zone_keys(site_zone)
        labels = [sch.zone_label(k, site_zone) for k in keys]
        date_text = (date.today() + timedelta(days=1)).isoformat()
        time_text, zone_index, error = "09:00", 0, ""
        while True:
            answer = sdlg.ask_schedule(
                self.host.parent,
                self.host.show_modal,
                title="Schedule Publish",
                purpose=(
                    f"Choose when '{copy.title or 'untitled'}' publishes on {profile.name}. "
                    "Nothing is sent until you confirm."
                ),
                date_text=date_text,
                time_text=time_text,
                zones=labels,
                zone_index=zone_index,
                error=error,
            )
            if answer is None:
                return
            date_text, time_text = answer.date_text, answer.time_text
            zone_index = answer.zone_index if 0 <= answer.zone_index < len(keys) else 0
            try:
                when = sch.parse_schedule(date_text, time_text, keys[zone_index])
            except sch.ScheduleError as exc:
                error = exc.plain
                continue
            break
        spoken = f"{sch.spoken_moment(when)}, {labels[zone_index]}"
        if not dlg.confirm(
            self.host.parent,
            self.host.show_modal,
            title=f"Schedule on {profile.name}",
            message=(
                f"Schedule '{copy.title or 'untitled'}' to publish on {profile.name} on {spoken}?"
            ),
            yes_label="Schedule",
        ):
            return
        self._send_dated(copy, profile, "future", sch.date_gmt(when), spoken)

    def _publish_now(self, copy: lc.WorkingCopy, profile: Any) -> None:
        if not dlg.confirm(
            self.host.parent,
            self.host.show_modal,
            title=f"Publish Now on {profile.name}",
            message=(
                f"Publish '{copy.title or 'untitled'}' on {profile.name} now, instead of at its "
                "scheduled time?"
            ),
            yes_label="Publish Now",
        ):
            return
        now = datetime.now(UTC)
        self._send_dated(copy, profile, "publish", sch.date_gmt(now), "now")

    def _send_dated(
        self, copy: lc.WorkingCopy, profile: Any, status: str, when_gmt: str, spoken: str
    ) -> None:
        from quill.ui.wordpress_more_commands import item_from_copy

        api = self.api(profile)  # type: ignore[attr-defined]

        def work() -> tuple[str, Any]:
            account = wp.load_account(api)
            allowed = (
                account.can_publish_pages if copy.kind == "page" else account.can_publish_posts
            )
            if not allowed:
                return "refused", account.role_name
            if copy.remote_id:
                stamp = wp.modified_gmt(api, copy.kind, copy.remote_id)
                conflict = lc.conflict_between(copy.base_modified_gmt, stamp)
                if conflict is not None:
                    return "conflict", conflict
                before = wp.load_item(api, copy.kind, copy.remote_id)
                self.local.add_version(
                    copy, lc.REASON_SITE_BEFORE_UPDATE, text=before.content, title=before.title
                )
            self._upload_pending(api, copy)  # type: ignore[attr-defined]
            html = self.to_html(copy)[0]  # type: ignore[attr-defined]
            return "saved", sch.send_scheduled(
                api, item_from_copy(copy, html, status=status), when_gmt
            )

        def done(result: tuple[str, Any]) -> None:
            kind, value = result
            if kind == "refused":
                self.host.announce(
                    f"Your role on {profile.name}, {value}, cannot publish, so it cannot schedule "
                    "either. Choose Publish or Update to submit it for review instead."
                )
            elif kind == "conflict":
                self.host.announce(
                    value.spoken(profile.name) + " Use Compare with Site, then schedule again."
                )
            elif value.status == "future":
                copy.properties["date_gmt"] = value.date_gmt or when_gmt
                self.record_sent(copy, value)
                self.host.announce(f"Scheduled on {profile.name} for {spoken}.")
            else:
                copy.properties["date_gmt"] = value.date_gmt or when_gmt
                self._sent(copy, profile, value)  # type: ignore[attr-defined]

        self.background(f"scheduling on {profile.name}", work, done)  # type: ignore[attr-defined]

    # ------------------------------------------------------------------ #
    # an autosave newer than the site's copy, on Open (9.3)

    def offer_newer_autosave(
        self, profile: Any, item: wp.Item, then: Callable[[wp.Item], None]
    ) -> None:
        """Offer the newest autosave when it is newer than *item*; then open one of them."""
        api = self.api(profile)  # type: ignore[attr-defined]

        def check() -> sch.Autosave | None:
            try:
                return sch.newer_autosave(api, item)
            except WordPressApiError:
                return None  # no autosave to offer is never a reason not to open

        def done(autosave: sch.Autosave | None) -> None:
            if autosave is None:
                then(item)
                return
            when = sch.when_spoken(autosave.modified_gmt)
            choice = dlg.ask_choice(
                self.host.parent,
                self.host.show_modal,
                title="Unsaved Version",
                prompt=f"There is an unsaved version from {when}. Open that &instead?",
                rows=[
                    f"Yes, open the unsaved version from {when}",
                    "No, open the copy on the site",
                ],
                help_text=(
                    "An autosave newer than the copy on the site was found, from a browser or "
                    "from QUILL. Whichever you open, the other stays on the site."
                ),
            )
            if choice is None:
                return
            if choice == 0:
                item_now = replace(
                    item,
                    title=autosave.title or item.title,
                    content=autosave.content,
                    excerpt=autosave.excerpt or item.excerpt,
                )
                then(item_now)
                return
            then(item)

        self.background("checking for an unsaved version", check, done)  # type: ignore[attr-defined]

    # ------------------------------------------------------------------ #
    # Restore from the Trash, from the Open list (5.6)

    def restore_listed(self, profile: Any, kind: str, summary: wp.ItemSummary) -> None:
        title = summary.title or "untitled"
        if summary.status != "trash":
            self.host.announce(f"'{title}' is not in the Trash.")
            return
        api = self.api(profile)  # type: ignore[attr-defined]

        def done(item: wp.Item) -> None:
            copy = self.local.find(profile.id, kind, summary.id)
            if copy is not None:
                copy.status = item.status
                copy.base_modified_gmt = item.modified_gmt
                self.local.save(copy)
            self.host.announce(
                f"'{title}' is back on {profile.name} as a draft. Open it to publish it again."
            )

        self.background(  # type: ignore[attr-defined]
            f"restoring from the Trash on {profile.name}",
            lambda: wp.restore_from_trash(api, kind, summary.id),
            done,
        )

    # ------------------------------------------------------------------ #
    # after sending: the queue, and "Add it to a menu?" (5.9)

    def after_sent(
        self, copy: lc.WorkingCopy, profile: Any, saved: wp.Item, *, was_public: bool
    ) -> None:
        self.offline_queue().drop(copy.key)
        self.watch_documents()
        if saved.kind == "page" and saved.status == "publish" and not was_public:
            self.offer_menu(profile, saved)

    def offer_menu(self, profile: Any, saved: wp.Item) -> None:
        store = self.sites()  # type: ignore[attr-defined]
        fresh = store.get(profile.id) or profile
        if not fresh.ask_add_to_menu:
            return
        choice = dlg.ask_choice(
            self.host.parent,
            self.host.show_modal,
            title="Add to a Menu",
            prompt="&Add it to a menu?",
            rows=["Yes, open Menus", "Not this time", f"No, and stop asking for {fresh.name}"],
            help_text=(
                "Publishing a new page does not put it in the site's menus, so visitors may not "
                "find it. Menus is also in File, WordPress, Running the Site."
            ),
        )
        if choice == 0:
            menus = getattr(self, "cmd_menus", None)
            if not callable(menus):
                self.host.announce(
                    f"Menus is not available yet. Add the page on {fresh.name}, under Appearance, "
                    "Menus."
                )
                return
            if "page_id" in inspect.signature(menus).parameters:
                menus(page_id=saved.id)
            else:
                menus()
        elif choice == 2:
            store.upsert(replace(fresh, ask_add_to_menu=False))
            self.save_sites(store)  # type: ignore[attr-defined]
            self.host.announce(
                f"QUILL will not ask again for {fresh.name}. Menus is in File, WordPress, "
                "Running the Site."
            )
