"""QUILL Accessible Forms' spam settings, changed from the WordPress Workbench (complete.md WP-C).

A mixin taken in through :class:`quill.ui.wordpress_workbench_forms_site.WorkbenchPluginCommands`,
which supplies the asking, preview and report helpers (``_pl_*``). The routes
and words are wx-free in :mod:`quill.core.wordpress.workbench_qaf_spam_edit`.

- **The site's Properties, Spam page** (Alt+Shift+Enter): QAF's checks,
  limits, questions and Send Anyway as fields, and a write-only OOPSpam key
  field. OK or Apply previews the change; the save reads the settings again
  and sends nothing if they changed on the site since (the conflict check),
  then reads them back and says what the site now holds (the verify). A site
  on ``baf/v1``, an older QAF, or a person without Manage Options sees the
  same fields read only, with the reason as their F1 help.
- **Form Spam Questions...** (the site's context menu): the site's own
  questions; add one, or change or remove one, each after a preview and
  checked by reading the bank back.
- **Form Spam by Week** (the site's context menu): the weeks QAF keeps.

The OOPSpam key is never spoken, previewed, put in Change History or left in
the sheet's values after a save.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.wordpress import workbench_qaf_spam_edit as edit
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.workbench_qaf_spam import read_spam_state, spam_namespace, spam_state_text
from quill.core.workbench.properties import FieldKind, FieldSpec, SheetState

__all__ = ["WorkbenchQafSpamCommands"]

_WEEKS = FieldSpec(
    "spam_weeks",
    "Form spam questions by week (QUILL Accessible Forms)",
    FieldKind.MULTILINE,
    readonly=True,
    help="Week by week, newest first: questions asked, answered, answered wrongly and sent "
    "anyway, as the site keeps them.",
)


class WorkbenchQafSpamCommands:
    """The QAF spam commands and the Spam page's save, for the Workbench provider."""

    say: Callable[[str], None]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    ensure: Callable[[Any], Any]
    site_of: Callable[[Any], str]
    current_site: Callable[[], str]
    refresh: Callable[[], None]

    # -- the Spam page -------------------------------------------------------------------

    def spam_page_values(self, ctx: Any) -> dict[str, Any]:
        """Off the UI thread: the Spam page's QAF part, read now."""
        namespace = spam_namespace(ctx)
        state = read_spam_state(ctx, namespace) if namespace else None
        if not namespace:
            text = "This site has no QUILL Accessible Forms, so there are no form spam checks."
        else:
            text = edit.namespace_note(namespace) + "\n" + spam_state_text(state)
        values: dict[str, Any] = {"form_spam": text}
        if state:
            values.update(edit.spam_values(state))
            values["spam_weeks"] = edit.weeks_text(edit.read_weeks(ctx.api, namespace))
        values["_qaf"] = {"namespace": namespace, "state": state}
        return values

    def site_sheet_with_spam(self, site: str, sheet: Any, values: dict[str, Any]) -> dict[str, Any]:
        """The site sheet, its values, and what makes its Spam page editable, for the editor."""
        from dataclasses import replace

        qaf = values.pop("_qaf", None) or {}
        namespace, state = str(qaf.get("namespace", "")), qaf.get("state")
        if not state:
            return {"sheet": sheet, "values": values}
        sheet = edit.with_spam_fields(sheet)
        sheet = replace(
            sheet,
            pages=tuple(
                replace(p, fields=(*p.fields, _WEEKS)) if p.key == "spam" else p
                for p in sheet.pages
            ),
        )
        reason = edit.write_refusal(namespace, state)
        if reason:
            locked = {f.key: reason for f in edit.spam_fields()}
            return {"sheet": sheet, "values": values, "locked": locked}
        revision = str(state.get("revision", ""))

        def on_save(sheet_state: SheetState) -> bool:
            return self.save_spam_page(site, namespace, revision, sheet_state)

        return {"sheet": sheet, "values": values, "on_save": on_save}

    def save_spam_page(
        self, site: str, namespace: str, revision: str, sheet_state: SheetState
    ) -> bool:
        """The Spam page's OK or Apply: preview, then read again, send, read back."""
        try:
            body = edit.spam_body(sheet_state.pending())
        except WordPressApiError as exc:
            self.say(f"{exc.plain} Nothing was changed.")
            return False
        # The key leaves the sheet's values now, whatever happens next.
        if sheet_state.edited.get("qaf_oopspam_key"):
            sheet_state.edited["qaf_oopspam_key"] = ""
        if not body:
            return True  # only the page's read-only lines, or nothing, changed
        if not self._pl_preview(  # type: ignore[attr-defined]
            "Change Form Spam Settings",
            f"Change QUILL Accessible Forms' spam settings on {site}.",
            edit.spam_preview(body, site),
            "Save Settings",
        ):
            return False
        api = self.ctx(site).api

        def done(result: tuple[str, dict[str, Any]]) -> None:
            self.say(result[0])

        # A refusal or a conflict is said by the window's own failure handler, in the
        # site's words or the conflict's; neither ever carries the key.
        self.background(
            f"saving {site}'s spam settings",
            lambda: edit.save_spam_settings(api, namespace, revision, body),
            done,
        )
        return True

    # -- the question bank ---------------------------------------------------------------

    def _spam_site(self, ref: Any) -> str:
        site = self.site_of(ref) or self.current_site()
        if not site:
            self.say("Connect a site first.")
        return site

    def do_spam_questions(self, ref: Any, _row: Any) -> None:
        site = self._spam_site(ref)
        if not site:
            return
        api = self.ctx(site).api
        where: dict[str, str] = {}

        def read() -> list[dict[str, Any]] | None:
            namespace = spam_namespace(self.ensure(self.ctx(site)))
            where["namespace"] = namespace
            if namespace != edit.WRITE_NAMESPACE:
                return None
            return edit.read_questions(api, namespace)

        def chosen(questions: list[dict[str, Any]] | None) -> None:
            namespace = where.get("namespace", "")
            if questions is None:
                self.say(edit.namespace_note(namespace))
                return
            rows = ["Add a question..."] + [edit.question_line(q) for q in questions]
            picked = self._pl_choose(  # type: ignore[attr-defined]
                f"Form Spam Questions - {site}",
                "&Questions (Enter on one changes or removes it):",
                rows,
                "The questions of the site's own that QUILL Accessible Forms asks a visitor "
                "when its checks are unsure, each with its right answers. Add a question is "
                "first.",
            )
            if picked is None:
                return
            if picked == 0:
                self._add_spam_question(site, api, namespace)
            else:
                self._change_spam_question(site, api, namespace, questions[picked - 1])

        self.background(f"reading {site}'s spam questions", read, chosen)

    def _ask_question(self, site: str, question: str = "") -> str | None:
        typed = self._pl_ask(  # type: ignore[attr-defined]
            f"Form Spam Questions - {site}",
            "&Question:",
            "Something anyone using the form would know, not a fact about your site. No bar "
            "character (|).",
            question,
        )
        return " ".join(typed.split()) if typed and typed.strip() else None

    def _ask_answers(self, site: str, answers: list[str] | None = None) -> list[str] | None:
        typed = self._pl_ask(  # type: ignore[attr-defined]
            f"Form Spam Questions - {site}",
            "&Right answers (a semicolon between):",
            "Every answer to accept, a semicolon between them, up to ten. Capitals and small "
            "slips are forgiven when a visitor answers.",
            "; ".join(answers or []),
        )
        found = edit.parse_answers(typed or "")
        return found or None

    def _send_bank(self, name: str, work: Callable[[], str]) -> None:
        # A refusal (a stale id answers 404) is said by the window's failure handler.
        self.background(name, work, self.say)

    def _add_spam_question(self, site: str, api: Any, namespace: str) -> None:
        question = self._ask_question(site)
        answers = self._ask_answers(site) if question else None
        if not question or not answers:
            self.say("A question needs its words and at least one right answer. Nothing was added.")
            return
        if not self._pl_preview(  # type: ignore[attr-defined]
            "Add a Spam Question",
            f"Add a question to {site}'s own.",
            [f"Question: {question}", f"Right answers: {'; '.join(answers)}."],
            "Add Question",
        ):
            return
        self._send_bank(
            f"adding a question to {site}",
            lambda: edit.add_question(api, namespace, question, answers),
        )

    def _change_spam_question(self, site: str, api: Any, namespace: str, q: dict[str, Any]) -> None:
        picked = self._pl_choose(  # type: ignore[attr-defined]
            f"Form Spam Questions - {site}",
            "&What to do:",
            ["Change its words...", "Change its answers...", "Remove it..."],
            edit.question_line(q),
        )
        if picked is None:
            return
        qid = str(q["id"])
        if picked == 2:
            if not self._pl_preview(  # type: ignore[attr-defined]
                "Remove a Spam Question",
                f"Remove a question from {site}'s own.",
                [edit.question_line(q), "Visitors are no longer asked it."],
                "Remove Question",
            ):
                return
            self._send_bank(
                f"removing a question from {site}",
                lambda: edit.delete_question(api, namespace, qid),
            )
            return
        question = self._ask_question(site, str(q["question"])) if picked == 0 else None
        answers = self._ask_answers(site, list(q["answers"])) if picked == 1 else None
        if question is None and answers is None:
            self.say("Nothing was changed.")
            return
        if question == q["question"] or answers == list(q["answers"]):
            self.say("That is how it is already. Nothing was changed.")
            return
        line = (
            f"Question: {question}" if question else f"Right answers: {'; '.join(answers or [])}."
        )
        if not self._pl_preview(  # type: ignore[attr-defined]
            "Change a Spam Question",
            f"Change a question of {site}'s own.",
            [f"Was: {edit.question_line(q)}", f"Becomes: {line}"],
            "Change Question",
        ):
            return
        self._send_bank(
            f"changing a question on {site}",
            lambda: edit.edit_question(api, namespace, qid, question=question, answers=answers),
        )

    # -- past weeks ------------------------------------------------------------------------

    def do_spam_weeks(self, ref: Any, _row: Any) -> None:
        site = self._spam_site(ref)
        if not site:
            return
        where: dict[str, str] = {}

        def read() -> list[dict[str, Any]] | None:
            ctx = self.ensure(self.ctx(site))
            where["namespace"] = namespace = spam_namespace(ctx)
            return edit.read_weeks(ctx.api, namespace) if namespace else None

        def done(weeks: Any) -> None:
            namespace = where.get("namespace", "")
            if not namespace:
                self.say(edit.namespace_note(namespace))
                return
            self._pl_report(  # type: ignore[attr-defined]
                f"Form Spam by Week - {site}",
                edit.namespace_note(namespace) + "\n" + edit.weeks_text(weeks),
                "Week by week, newest first: the questions QUILL Accessible Forms asked, "
                "answered, answered wrongly and let through with Send Anyway. Each week is "
                "kept about a hundred days.",
            )

        self.background(f"reading {site}'s spam weeks", read, done)
