"""The editorial queue and the calendar's moves (PRD 15.3, 15.4; W7).

A mixin on :class:`quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`:

- **Approve and Schedule** (Ctrl+Shift+D): publish now, or at a time read on
  the site's own clock -- a daylight-saving gap or repeat is named, not
  guessed -- after a preview in the site's time and yours.
- **Send Back with a Note** (Ctrl+Shift+B): a note on the draft, and back to
  its writer as a draft.
- **Assign a Reviewer** (Ctrl+Shift+J): a reviewer chosen from the people who
  may edit others' posts (or typed, when the site will not list them), a note
  on the draft naming them, and a record the Review Watch follows.
  WordPress sends no email for any of this, and the outcome says so.
- **Move to Another Day** (Ctrl+Alt+Shift+D): the calendar's way to move a
  post, as an editable date with the same preview.

Every request runs through ``self.background``; every change is previewed
and goes to Change History; outcomes are one sentence.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Any

from quill.core.wordpress import block_notes as notes
from quill.core.wordpress.schedule import ScheduleError, date_gmt, site_time_zone
from quill.core.wordpress.workbench_editorial import (
    NOTICE_WORDS,
    Review,
    assign_reviewer,
    moment_words,
    site_moment,
)
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.history import Change
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_workbench_dialogs as wdlg

__all__ = ["WorkbenchQueueCommands"]


def _split(text: str) -> tuple[str, str]:
    day, _sep, clock = text.strip().partition(" ")
    return day, clock


class WorkbenchQueueCommands:
    """Approve and Schedule, Send Back, Assign a Reviewer, Move to Another Day."""

    parent: Any
    history: Any
    _data_dir: Any
    say: Callable[[str], None]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    show_modal: Callable[[Any, str], int]
    refresh: Callable[[], None]
    selected_rows: Callable[[], list[WbRow]]

    def _queue_rows(self, row: WbRow | None) -> list[WbRow]:
        rows = [r for r in (self.selected_rows() or ([row] if row else [])) if r.kind == "item"]
        if not rows:
            self.say("Select a post or page first.")
            return []
        site = rows[0].site
        if any(r.site != site for r in rows):
            self.say(f"Select items from one site at a time; these are on several. {site}'s first.")
            rows = [r for r in rows if r.site == site]
        return rows

    def _at_site_time(
        self,
        rows: Sequence[WbRow],
        text: str,
        *,
        future_only: bool,
        then: Callable[[datetime, str], None],
    ) -> None:
        """Read *text* on the site's clock off the UI thread, then call *then* (when, words)."""
        api = self.ctx(rows[0].site).api
        day, clock = _split(text)

        def work() -> tuple[datetime, str] | str:
            zone = site_time_zone(api) or "UTC"
            try:
                when = site_moment(day, clock, zone, future_only=future_only)
            except ScheduleError as exc:
                return exc.plain
            return when, moment_words(when, zone)

        def done(answer: tuple[datetime, str] | str) -> None:
            if isinstance(answer, str):
                self.say(answer)
            else:
                then(*answer)

        self.background("reading the site's time zone", work, done)

    def _send(self, rows: Sequence[WbRow], body: dict[str, Any], said: str, what: str) -> None:
        api = self.ctx(rows[0].site).api

        def work() -> None:
            for r in rows:
                api.post(r.route, body)

        def done(_none: object) -> None:
            self.history.record(Change(rows[0].route, f"{what} on {rows[0].site}."))
            self.say(said)
            self.refresh()

        self.background(what.lower(), work, done)

    # -- approve and schedule -------------------------------------------------------

    def do_approve_schedule(self, _ref: Any, row: WbRow | None) -> None:
        rows = self._queue_rows(row)
        if not rows:
            return
        site = rows[0].site
        text = dlg.ask_text(
            self.parent,
            self.show_modal,
            title="Approve and Schedule",
            prompt="&Publish on (2026-11-20 9:00 AM), or empty for now:",
            help_text="A day and time on the site's own clock. A time that happens twice when "
            "the clocks go back takes first or second after it. Empty publishes now.",
        )
        if text is None:
            return
        titles = [r.title for r in rows]
        if not text.strip():
            if wdlg.ask_preview(
                self.parent,
                self.show_modal,
                title="Approve and Publish",
                summary=f"Publish {len(rows)} on {site} now.",
                lines=titles,
                yes="Publish",
            ):
                self._send(rows, {"status": "publish"}, f"{len(rows)} published.", "Published")
            return

        def previewed(when: datetime, words: str) -> None:
            if wdlg.ask_preview(
                self.parent,
                self.show_modal,
                title="Approve and Schedule",
                summary=f"Approve {len(rows)} on {site} and schedule them for {words}.",
                lines=titles,
                yes="Schedule",
            ):
                body = {"status": "future", "date_gmt": date_gmt(when)}
                self._send(rows, body, f"{len(rows)} scheduled for {words}.", "Scheduled")

        self._at_site_time(rows, text, future_only=True, then=previewed)

    # -- move to another day ----------------------------------------------------------

    def do_move_day(self, _ref: Any, row: WbRow | None) -> None:
        rows = self._queue_rows(row)
        if not rows:
            return
        site = rows[0].site
        was = str(rows[0].raw.get("date", "") or "")
        start = was[:16].replace("T", " ") if was else ""
        text = dlg.ask_text(
            self.parent,
            self.show_modal,
            title="Move to Another Day",
            prompt="&New day and time (2026-11-20 9:00 AM):",
            value=start,
            help_text="On the site's own clock. A time that happens twice when the clocks go "
            "back takes first or second after it. The preview says it in your time too.",
        )
        if not text or not text.strip():
            return
        scheduled = all(r.status == "future" for r in rows)

        def previewed(when: datetime, words: str) -> None:
            lines = [r.title for r in rows]
            if any(r.status == "publish" for r in rows) and when.timestamp() > _now():
                lines.append(
                    "Published items moved to a future time are scheduled again, and are off "
                    "the site until then."
                )
            if wdlg.ask_preview(
                self.parent,
                self.show_modal,
                title="Move to Another Day",
                summary=f"Move {len(rows)} on {site} to {words}.",
                lines=lines,
                yes="Move",
            ):
                body = {"date_gmt": date_gmt(when)}
                self._send(rows, body, f"Moved {len(rows)} to {words}.", "Moved to another day")

        self._at_site_time(rows, text, future_only=scheduled, then=previewed)

    # -- notes: send back and reviewers -------------------------------------------------

    def _ask_note(self, title: str, prompt: str, *, required: bool) -> str | None:
        text = dlg.ask_text(
            self.parent,
            self.show_modal,
            title=title,
            prompt=prompt,
            help_text="A note on the draft, which its writer and reviewer read in the editor.",
            multiline=True,
        )
        if text is None or (required and not text.strip()):
            return None
        return text.strip()

    def do_send_back(self, _ref: Any, row: WbRow | None) -> None:
        rows = self._queue_rows(row)
        if not rows:
            return
        text = self._ask_note("Send Back with a Note", "&What needs changing:", required=True)
        if text is None:
            return
        api = self.ctx(rows[0].site).api

        def work() -> None:
            for r in rows:
                notes.add_note(api, int(r.object_id), text)
                api.post(r.route, {"status": "draft"})

        def done(_none: object) -> None:
            self.history.record(Change(rows[0].route, f"Sent back {len(rows)} on {rows[0].site}."))
            self.say(f"Sent back {len(rows)} as drafts, with your note. WordPress sends no email.")
            self.refresh()

        self.background("sending back", work, done)

    def do_assign_reviewer(self, _ref: Any, row: WbRow | None) -> None:
        rows = self._queue_rows(row)
        if not rows:
            return
        api = self.ctx(rows[0].site).api

        def people() -> list[str]:
            for params in (
                {"capabilities": "edit_others_posts", "context": "edit", "_fields": "id,name"},
                {"who": "authors", "_fields": "id,name"},
            ):
                try:
                    found = list(api.iter_collection("wp/v2/users", params, per_page=100))
                except Exception:  # noqa: BLE001 - the site will not list them: type a name
                    continue
                names = [str(p.get("name", "")) for p in found if p.get("name")]
                if names:
                    return names
            return []

        self.background("listing reviewers", people, lambda names: self._reviewer_then(rows, names))

    def _reviewer_then(self, rows: Sequence[WbRow], names: list[str]) -> None:
        if names:
            index = dlg.ask_choice(
                self.parent,
                self.show_modal,
                title="Assign a Reviewer",
                prompt="&Reviewer:",
                rows=names,
                help_text="The people on the site who may edit and publish others' posts.",
            )
            reviewer = None if index is None else names[index]
        else:
            reviewer = dlg.ask_text(
                self.parent,
                self.show_modal,
                title="Assign a Reviewer",
                prompt="&Reviewer's name:",
                help_text="The site would not list its editors, so type the reviewer's name.",
            )
        if not reviewer or not reviewer.strip():
            return
        reviewer = reviewer.strip()
        note = self._ask_note("Assign a Reviewer", f"&A note for {reviewer}:", required=False)
        if note is None:
            return
        site = rows[0].site
        api = self.ctx(site).api
        base = self._data_dir

        def work() -> None:
            said = f"Review requested from {reviewer}." + (f" {note}" if note else "")
            for r in rows:
                notes.add_note(api, int(r.object_id), said)
                assign_reviewer(
                    base, Review(site, int(r.object_id), r.route, r.title, reviewer, note)
                )

        def done(_none: object) -> None:
            self.history.record(Change(rows[0].route, f"{reviewer} asked to review on {site}."))
            self.say(f"{reviewer} reviews {len(rows)}. {NOTICE_WORDS}")

        self.background("assigning a reviewer", work, done)


def _now() -> float:
    import time

    return time.time()
