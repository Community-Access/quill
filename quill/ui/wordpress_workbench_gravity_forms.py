"""Gravity Forms forms and feeds in the WordPress Workbench: feeds, results, tests (10B.3).

A mixin on :class:`quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`
(through :class:`quill.ui.wordpress_workbench_commands.WorkbenchRowCommands`):

- **Feeds** (Sites > site > Forms > Feeds): Activate or Deactivate and Rename
  preview the one field that changes and send the whole feed back; Delete
  Permanently previews the feed and Ctrl+Z makes it again, with a new number.
- **Show Its Feeds** and **Show Its Results** on a form open those lists
  filtered to it; Results is a row per answer and a sentence per question.
- **Test This Form**: test values QUILL fills in and the person edits,
  checked by Gravity Forms' validation route first (nothing saved), then sent
  as a real submission after a preview that says a practice site is better.
- **Filter Builder** on a site's Responses: the form's own field filters, so
  a filter is built from the form's questions and the answers it allows. The
  conditions are sent to the site as ``gf/v2/entries``' ``search``
  (:mod:`quill.core.wordpress.workbench_gravity_search`), with All or Any
  asked when there is more than one, read page by page, and the site's own
  count is what the status bar says.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import replace
from typing import Any

from quill.core.wordpress import workbench_gravity as gravity
from quill.core.wordpress import workbench_gravity_search as gravity_search
from quill.core.wordpress import workbench_gravity_submit as submitting
from quill.core.wordpress.workbench_forms import form_plugins
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.filters import Condition, Operator
from quill.core.workbench.history import Change
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_workbench_dialogs as wdlg

__all__ = ["WorkbenchGravityFormCommands"]

_OPERATORS = {"is": ("is", Operator.IS), "isnot": ("is not", Operator.IS_NOT)}


class WorkbenchGravityFormCommands:
    """Feeds, results, Test This Form and the Gravity Forms Filter Builder."""

    frame: Any
    say: Callable[[str], None]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    ensure: Callable[[Any], Any]
    profile: Callable[[str], Any]
    show_modal: Callable[[Any, str], int]
    refresh: Callable[[], None]
    site_of: Callable[[Any], str]
    history: Any
    parent: Any
    _show_filtered: Callable[[str, str, str], None]
    _add_condition: Callable[..., None]

    def _gravity_form(self, row: WbRow | None) -> WbRow | None:
        """The form row, its title under ``title`` (a form row's own title is its plugin)."""
        if row is None or row.kind != "gravity_form" or row.subkind != "gravity":
            self.say("Choose a Gravity Forms form first.")
            return None
        return replace(row, cells={**row.cells, "title": row.cell("form") or row.title})

    def do_show_feeds(self, _ref: Any, row: WbRow | None) -> None:
        form = self._gravity_form(row)
        if form is not None:
            self._show_filtered("form_feeds", form.site, f'form:"{form.title}"')

    def do_show_results(self, _ref: Any, row: WbRow | None) -> None:
        form = self._gravity_form(row)
        if form is not None:
            self._show_filtered("form_results", form.site, f'form:"{form.title}"')

    # -- feeds ----------------------------------------------------------------------

    def _feed(self, row: WbRow | None) -> WbRow | None:
        if row is None or row.kind != "gravity_feed":
            self.say("Choose a Gravity Forms feed first, in Forms > Feeds.")
            return None
        return row

    def _change_feed(
        self, feed: WbRow, *, active: bool | None = None, name: str | None = None
    ) -> None:
        api = self.ctx(feed.site).api

        def previewed(current: Any) -> None:
            if not isinstance(current, dict) or not current.get("id"):
                self.say(f"Gravity Forms did not return {feed.title} on {feed.site}.")
                return
            body, lines = gravity.feed_body(current, active=active, name=name)
            if active is not None:
                verb = "Activate" if active else "Deactivate"
                summary = f"{verb} {gravity.feed_name(current)} on {feed.site}?"
                lines.insert(
                    0,
                    f"A {feed.cell('addon')} feed on {feed.cell('form')}. "
                    + (
                        "Submissions will reach it again."
                        if active
                        else "Submissions will stop reaching it."
                    ),
                )
            else:
                verb = "Rename"
                summary = f"Rename {gravity.feed_name(current)} on {feed.site}?"
            if not wdlg.ask_preview(
                self.parent,
                self.show_modal,
                title=f"{verb} Feed",
                summary=summary,
                lines=lines,
                yes=verb,
            ):
                return

            def saved(_answer: Any) -> None:
                if active is not None:
                    state = "active" if active else "inactive"
                    said = f"{gravity.feed_name(current)} is now {state} on {feed.site}."
                else:
                    said = f"Renamed the feed to {name} on {feed.site}."
                self.history.record(
                    Change(
                        f"{feed.site}: {feed.title}",
                        said,
                        undo=lambda: (
                            api.request("PUT", feed.route, json_body=dict(current)),
                            f"Put {gravity.feed_name(current)} back as it was.",
                        )[1],
                    )
                )
                self.say(said)
                self.refresh()

            self.background(
                "changing a feed",
                lambda: api.request("PUT", feed.route, json_body=body).payload,
                saved,
            )

        self.background(f"reading {feed.title}", lambda: api.get(feed.route), previewed)

    def do_toggle_feed(self, _ref: Any, row: WbRow | None) -> None:
        feed = self._feed(row)
        if feed is not None:
            self._change_feed(feed, active=feed.status != "active")

    def do_rename_feed(self, _ref: Any, row: WbRow | None) -> None:
        feed = self._feed(row)
        if feed is None:
            return
        name = dlg.ask_text(
            self.parent,
            self.show_modal,
            title=f"Rename Feed - {feed.title}",
            prompt="&Feed name:",
            value=feed.title,
            help_text="The name Gravity Forms shows for this feed. Nothing else about it changes.",
        )
        if name is None or not name.strip() or name.strip() == feed.title:
            return
        self._change_feed(feed, name=name.strip())

    def delete_feeds(self, rows: list[WbRow]) -> None:
        """Delete Permanently on feeds: a preview of each, and Ctrl+Z makes them again."""
        site = rows[0].site
        lines = [
            f"{r.title}: a {r.cell('addon')} feed on {r.cell('form')}, {r.status}." for r in rows
        ]
        lines.append(
            "Gravity Forms keeps no Trash for feeds. Ctrl+Z here makes each again with the "
            "same settings and a new number."
        )
        count = len(rows)
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title="Delete Feeds",
            summary=f"Delete {count} feed{'s' if count != 1 else ''} from {site} permanently?",
            lines=lines,
            yes="Delete Permanently",
        ):
            return
        api = self.ctx(site).api

        def work() -> list[dict[str, Any]]:
            kept = []
            for r in rows:
                current = api.get(r.route)
                kept.append(dict(current) if isinstance(current, dict) else dict(r.raw))
                api.delete(r.route)
            return kept

        def remake(kept: list[dict[str, Any]]) -> str:
            for feed in kept:
                body = {
                    k: feed[k] for k in ("form_id", "addon_slug", "meta", "is_active") if k in feed
                }
                api.post(f"{gravity.NS}/feeds", body)
            return f"Made {len(kept)} feed{'s' if len(kept) != 1 else ''} again on {site}."

        def done(kept: list[dict[str, Any]]) -> None:
            said = f"Deleted {count} feed{'s' if count != 1 else ''} from {site}."
            self.history.record(Change(f"{site}: feeds", said, undo=lambda: remake(kept)))
            self.say(said)
            self.refresh()

        self.background("deleting feeds", work, done)

    # -- Test This Form -------------------------------------------------------------

    def do_test_form(self, _ref: Any, row: WbRow | None) -> None:
        form_row = self._gravity_form(row)
        if form_row is None:
            return
        api = self.ctx(form_row.site).api
        form_id = form_row.key

        def filled(form: Any) -> None:
            if not isinstance(form, dict):
                self.say(f"Gravity Forms did not return {form_row.title} on {form_row.site}.")
                return
            inputs, skipped = submitting.sample_inputs(form)
            labels = {i.name: i.label for i in inputs}
            field_labels = {
                str(f.get("id", "")): str(f.get("label", "") or "")
                for f in form.get("fields") or []
                if isinstance(f, dict)
            }
            skipped_words = f" QUILL leaves these empty: {', '.join(skipped)}." if skipped else ""
            text = dlg.ask_text(
                self.parent,
                self.show_modal,
                title=f"Test This Form - {form_row.title}",
                prompt="&Test values, one input a line:",
                value="\n".join(f"{i.name}: {i.value}" for i in inputs),
                help_text=(
                    "Each line is a Gravity Forms input and the value QUILL will send. Change "
                    "any value after the colon; delete a line to leave that input empty."
                    f"{skipped_words}"
                ),
                multiline=True,
            )
            if text is None:
                return
            values = submitting.parse_inputs(text)

            def checked(answer: submitting.SubmitAnswer) -> None:
                if not answer.valid:
                    dlg.show_report(
                        self.parent,
                        self.show_modal,
                        title=f"Not Accepted - {form_row.title}",
                        text="\n".join(answer.lines(field_labels)),
                        help_text=(
                            "What Gravity Forms refused in the test values. Nothing was saved."
                        ),
                    )
                    return
                self._submit_test(form_row, values, labels)

            self.background(
                "checking the test values",
                lambda: submitting.submit(api, form_id, values, validate_only=True),
                checked,
            )

        self.background(f"reading {form_row.title}", lambda: api.get(form_row.route), filled)

    def _submit_test(self, form_row: WbRow, values: dict[str, str], labels: dict[str, str]) -> None:
        profile = self.profile(form_row.site)
        url = profile.site_url if profile is not None else ""
        practice = submitting.is_practice_site(url, form_row.site)
        where = (
            f"{form_row.site} is a practice site, so the test entry costs nothing."
            if practice
            else (
                f"{form_row.site} is a live site. A practice site is better for tests: this "
                "entry is real, and its emails and feeds reach real people and services."
            )
        )
        lines = [
            where,
            "Gravity Forms already checked these values; nothing has been saved yet.",
            *(f"{labels.get(k, k)} ({k}): {v}" for k, v in values.items()),
            "Ctrl+Z afterwards moves the test entry to Gravity Forms' Trash.",
        ]
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title="Submit a Test Entry",
            summary=f"Send a test entry to {form_row.title} on {form_row.site}?",
            lines=lines,
            yes="Submit Test Entry",
        ):
            return
        api = self.ctx(form_row.site).api

        def sent(answer: submitting.SubmitAnswer) -> None:
            if not answer.valid:
                self.say(
                    f"Gravity Forms did not accept the test entry: {'; '.join(answer.lines({}))}"
                )
                return
            said = f"Gravity Forms accepted the test entry to {form_row.title} on {form_row.site}"
            said += f", entry {answer.entry_id}." if answer.entry_id else "."
            if answer.confirmation:
                said += f" It said: {answer.confirmation}"
            undo = None
            if answer.entry_id:
                undo = lambda: (  # noqa: E731
                    api.delete(f"{gravity.NS}/entries/{answer.entry_id}"),
                    f"Moved test entry {answer.entry_id} to the Trash.",
                )[1]
            self.history.record(Change(f"{form_row.site}: {form_row.title}", said, undo=undo))
            self.say(said)

        self.background(
            "sending the test entry",
            lambda: submitting.submit(api, form_row.key, values, validate_only=False),
            sent,
        )

    # -- the Filter Builder on Responses ---------------------------------------------

    def gravity_filter_builder(self) -> bool:
        """The Filter Builder from a Gravity Forms form's field filters; False when not here."""
        frame = self.frame
        ref = frame.current if frame is not None else None
        if ref is None or frame.node(ref).loader not in ("forms:entries", "forms:spam"):
            return False
        site = self.site_of(ref)
        if not site or "gravity" not in form_plugins(self.ctx(site)):
            return False
        api = self.ctx(site).api

        def forms_read(titles: dict[str, str]) -> None:
            if not titles:
                self.say(f"{site} has no Gravity Forms forms to filter by.")
                return
            ids = list(titles)
            index = dlg.ask_choice(
                self.parent,
                self.show_modal,
                title="Filter Builder",
                prompt="&Form:",
                rows=[titles[i] for i in ids],
                help_text="Whose questions to filter the responses by. Only its responses stay.",
            )
            if index is None:
                return
            form_id, title = ids[index], titles[ids[index]]
            self.background(
                f"reading the filters of {title}",
                lambda: gravity.field_filters(api, form_id),
                lambda found: self._pick_field_filter(title, found),
            )

        self.background("reading the forms", lambda: gravity.gravity_forms(api), forms_read)
        return True

    def _pick_field_filter(self, title: str, found: list[gravity.FieldFilter]) -> None:
        if not found:
            self.say(f"Gravity Forms offers no field filters for {title}.")
            return
        index = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title="Filter Builder",
            prompt="&Filter on:",
            rows=[f.text for f in found],
            help_text=f"The questions and entry details Gravity Forms filters {title} by.",
        )
        if index is None:
            return
        chosen = found[index]
        ops = [_OPERATORS[o] for o in chosen.operators if o in _OPERATORS] or [_OPERATORS["is"]]
        op_index = 0
        if len(ops) > 1:
            op_index = dlg.ask_choice(
                self.parent,
                self.show_modal,
                title="Filter Builder",
                prompt="&How:",
                rows=[words for words, _op in ops],
                help_text="Keep the responses whose answer is, or is not, the value.",
            )
            if op_index is None:
                return
        if chosen.values:
            value_index = dlg.ask_choice(
                self.parent,
                self.show_modal,
                title="Filter Builder",
                prompt="&Value:",
                rows=[text for text, _value in chosen.values],
                help_text=f"The answers {chosen.text} allows.",
            )
            if value_index is None:
                return
            value = chosen.values[value_index][1]
        else:
            typed = dlg.ask_text(
                self.parent,
                self.show_modal,
                title="Filter Builder",
                prompt="&Value:",
                help_text=f"The answer to {chosen.text} to look for. Part of it is enough.",
            )
            if not typed or not typed.strip():
                return
            value = typed.strip()
        if not self._ask_gravity_mode(chosen.key):
            return
        self._add_condition(Condition("form", Operator.IS, title), replace=True)
        self._add_condition(Condition(chosen.key, ops[op_index][1], value), replace=True)

    def _gravity_modes(self) -> dict[str, str]:
        modes = getattr(self, "_gravity_mode", None)
        if modes is None:
            modes = self._gravity_mode = {}
        return modes

    def _ask_gravity_mode(self, key: str) -> bool:
        """With another site-side condition already there: All of them, or Any? False on Cancel."""
        frame = self.frame
        site = self.site_of(frame.current) if frame.current is not None else ""
        others = [
            c
            for c in frame.query.conditions
            if gravity_search.is_site_condition(c) and c.attribute != key
        ]
        if not others:
            self._gravity_modes()[site] = "all"
            return True
        index = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title="Filter Builder",
            prompt="&Keep the responses that match:",
            rows=["All of the conditions", "Any of the conditions"],
            help_text="All keeps a response only when every condition is true of it; Any "
            "keeps it when one is. Gravity Forms does the matching on the site.",
        )
        if index is None:
            return False
        self._gravity_modes()[site] = gravity_search.MODES[index]
        return True

    @contextmanager
    def gravity_load_scope(self, ref: Any, loader: str, query: Any) -> Iterator[tuple[Any, ...]]:
        """Around a list load: what stays on this computer; Responses send the rest to the site."""
        if loader not in ("forms:entries", "forms:spam"):
            yield tuple(query.conditions)
            return
        mode = self._gravity_modes().get(self.site_of(ref), "all")
        with gravity_search.gravity_scope(query.conditions, mode) as scope:
            yield scope.local
        words = gravity_search.count_words(scope)
        if words:
            self.cut[self.page_key(ref)] = words  # type: ignore[attr-defined]
