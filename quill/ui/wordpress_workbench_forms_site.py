"""QUILL Accessible Forms on the site, from the WordPress Workbench window (Package 13).

A mixin built on :class:`quill.ui.wordpress_workbench_event_commands.WorkbenchEventCommands`
(and through it the shop commands' asking and preview helpers), which the
provider takes in one place. The routes and words are wx-free in
:mod:`quill.core.wordpress.workbench_forms_site`. Deleting a form deletes its
responses with it, so the preview gives their count and the person types the
form's name before anything is sent.
"""

from __future__ import annotations

from typing import Any

from quill.core.wordpress import workbench_forms_site as qaf
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.workbench_rows import WbRow
from quill.ui.wordpress_workbench_event_commands import WorkbenchEventCommands
from quill.ui.wordpress_workbench_qaf_spam import WorkbenchQafSpamCommands


# QAF's spam settings, question bank and weeks ride with its form commands (complete.md WP-C).
class WorkbenchPluginCommands(WorkbenchQafSpamCommands, WorkbenchEventCommands):
    """Shop, events, SEO and the QAF form commands, as one mixin for the provider."""

    def _qaf_form(self, row: WbRow | None) -> bool:
        if row is None or row.kind != "form":
            return False
        if row.subkind != "qaf":
            self.say("That is a QUILL Accessible Forms command; choose one of its forms.")  # type: ignore[attr-defined]
            return False
        return True

    def do_change_form_status(self, _ref: Any, row: WbRow | None) -> None:
        if not self._qaf_form(row):
            return
        assert row is not None
        choices = [s for s in qaf.FORM_STATUSES if s != row.status]
        picked = self._pl_choose(
            f"Change Form Status - {row.title}",
            "&New status:",
            [qaf.FORM_STATUSES[s] for s in choices],
            "Whether the form takes responses.",
        )
        if picked is None:
            return
        new = choices[picked]
        if not self._pl_preview(
            "Change Form Status",
            f"{row.title} on {row.site} becomes {new}.",
            qaf.status_preview(row.title, row.status, new, row.site),
            "Change Status",
        ):
            return
        api = self.ctx(row.site).api  # type: ignore[attr-defined]
        self._pl_send(
            row.site,
            f"changing {row.title}",
            lambda: api.post(row.route, {"status": new}),
            f"{row.title} on {row.site} is {qaf.FORM_STATUSES[new]}.",
        )

    def do_delete_form(self, _ref: Any, row: WbRow | None) -> None:
        if not self._qaf_form(row):
            return
        assert row is not None
        responses = int(row.cell("entries") or 0) if row.cell("entries").isdigit() else 0
        if not self._pl_preview(
            "Delete Form",
            f"Delete {row.title} and its responses from {row.site}.",
            qaf.delete_preview(row.title, responses, row.site),
            "Go On to Confirm",
        ):
            return
        typed = self._pl_ask(
            "Delete Form",
            f"&Type the form's name, {row.title}, to delete it:",
            "The form is deleted only when this is its name exactly. Cancel deletes nothing.",
        )
        if typed is None or typed.strip() != row.title.strip():
            self.say("The name typed did not match, so nothing was deleted.")  # type: ignore[attr-defined]
            return
        api = self.ctx(row.site).api  # type: ignore[attr-defined]
        self._pl_send(
            row.site,
            f"deleting {row.title}",
            lambda: api.delete(row.route),
            f"Deleted {row.title} and its responses from {row.site}.",
        )

    def do_form_settings(self, _ref: Any, row: WbRow | None) -> None:
        if not self._qaf_form(row):
            return
        assert row is not None
        api = self.ctx(row.site).api  # type: ignore[attr-defined]

        def read() -> dict[str, Any]:
            found = api.get(row.route)
            settings = found.get("settings") if isinstance(found, dict) else None
            if not isinstance(settings, dict):
                raise WordPressApiError(f"{row.title} returned no settings QUILL can read.")
            return settings

        def chosen(settings: dict[str, Any]) -> None:
            lines = qaf.setting_lines(settings)
            picked = self._pl_choose(
                f"Form Settings - {row.title}",
                "&Settings (Enter changes one):",
                [f"{key.replace('_', ' ')}: {value}" for key, value in lines],
                "Each setting and its value. Lists such as conditional logic are changed in "
                "the form builder.",
            )
            if picked is None:
                return
            key = lines[picked][0]
            typed = self._pl_ask(
                f"Form Settings - {row.title}",
                f"&{key.replace('_', ' ')}:",
                "Its new value: on or off for a switch, a number for a count.",
                lines[picked][1],
            )
            if typed is None:
                return
            try:
                value = qaf.setting_value(settings[key], typed)
                body = qaf.settings_body(settings, key, value)
            except WordPressApiError as exc:
                self.say(f"{exc.plain} Nothing was changed.")  # type: ignore[attr-defined]
                return
            if value == settings[key]:
                self.say("That is its value already. Nothing was changed.")  # type: ignore[attr-defined]
                return
            if not self._pl_preview(
                "Form Settings",
                f"Change a setting of {row.title}.",
                qaf.settings_preview(row.title, key, settings[key], value, row.site),
                "Change Setting",
            ):
                return
            self._pl_send(
                row.site,
                f"changing {row.title}'s settings",
                lambda: api.post(row.route, body),
                f"Changed {key.replace('_', ' ')} on {row.title}.",
            )

        self.background(f"reading {row.title}'s settings", read, chosen)  # type: ignore[attr-defined]

    def do_show_views(self, _ref: Any, row: WbRow | None) -> None:
        if not self._qaf_form(row):
            return
        assert row is not None
        api = self.ctx(row.site).api  # type: ignore[attr-defined]
        namespace = qaf.namespace_of(row)

        def done(views: Any) -> None:
            self._pl_report(
                f"Saved Views - {row.site}",
                "\n".join(qaf.view_lines(views, {row.key: row.title})),
                "The site's saved views of its form responses, made in the plugin.",
            )

        self.background("reading saved views", lambda: api.get(f"{namespace}/views"), done)  # type: ignore[attr-defined]

    def do_search_responses(self, _ref: Any, row: WbRow | None) -> None:
        if not self._qaf_form(row):
            return
        assert row is not None
        words = self._pl_ask(
            f"Search Responses - {row.title}", "&Words:", "Found in any answer, on the site."
        )
        if not words or not words.strip():
            return
        api = self.ctx(row.site).api  # type: ignore[attr-defined]
        namespace = qaf.namespace_of(row)
        params = {"form_id": row.object_id, "search": words.strip(), "status": "active"}

        def read() -> list[str]:
            from quill.core.wordpress.workbench_forms import _answers_sentence

            found = api.iter_collection(f"{namespace}/entries", params, max_pages=3)
            return [
                f"Response {e.get('id')}, {e.get('created_at', '')}: "
                + _answers_sentence(e.get("fields") or {})
                for e in found
                if isinstance(e, dict)
            ]

        def done(lines: list[str]) -> None:
            self._pl_report(
                f"Responses with {words.strip()} - {row.title}",
                "\n".join(lines) or "No response has those words.",
                "Responses whose answers have the words, newest first.",
            )

        self.background("searching responses", read, done)  # type: ignore[attr-defined]
