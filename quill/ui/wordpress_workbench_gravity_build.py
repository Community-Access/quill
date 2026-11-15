"""Build Gravity Forms forms in QUILL: New, Edit and Copy between plugins (WP-C).

A mixin on :class:`quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`:

- **New Gravity Form...** (New Here, Ctrl+N, on a site's Forms node; and Item >
  Gravity Forms) asks for a title, opens the editor on Gravity Forms' own
  defaults, and makes the form with ``POST gf/v2/forms``.
- **Edit Form...** on a Gravity Forms form row reads the form, opens the editor
  on a copy, and saves with ``PUT`` only if the form on the site is still the
  one that was opened.
- **Copy as a QUILL Accessible Form...** and **Copy as a Gravity Form...** make
  a new form in the other plugin, after a preview naming anything that cannot
  carry over.

Every save runs the accessibility checks first (Cancel goes back to the editor
on the first finding), then shows a preview of each change, then sends, reads
the form back and says any difference. Ctrl+Z puts the previous form back (a
new form goes to Gravity Forms' Trash). Entries are never read or sent: every
preview says so. Network work runs through ``self.background``.
"""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import replace
from typing import Any

from quill.core.forms import model as M
from quill.core.forms import qaf_site
from quill.core.wordpress import gravity_build as gb
from quill.core.wordpress import gravity_build_save as gs
from quill.core.wordpress.gravity_build_checks import Finding, check_form
from quill.core.wordpress.gravity_qaf import to_gravity, to_qaf
from quill.core.wordpress.workbench_forms import GRAVITY_NAMESPACE, form_plugins
from quill.core.wordpress.workbench_gravity import gravity_can
from quill.core.wordpress.workbench_permissions import tier_allowed
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.actions import Tier
from quill.core.workbench.history import Change
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_gravity_editor as gedit
from quill.ui import wordpress_workbench_dialogs as wdlg

__all__ = ["WorkbenchGravityBuildCommands", "shared_findings"]

#: QAF findings the Gravity Forms checks already make, in their own words.
_ALREADY = (
    "has no label",
    "only a placeholder",
    "asterisk",
    "has no questions",
    "autofill hint",
    "is used",
    "names #",
    "points at #",
    "question for its choices",
    "can never show",
)


def shared_findings(form: dict[str, Any]) -> list[Finding]:
    """QUILL's own QAF form checks (Check This Form, 17a.5) over the converted form."""
    try:
        from quill.ui import forms_check

        found = forms_check.accessibility(to_qaf(form).form)
    except Exception:  # noqa: BLE001 - the shared checks are advice; ours still run
        return []
    out = []
    for finding in found:
        if any(words in finding.text for words in _ALREADY):
            continue
        item = str(finding.item_id or "")
        out.append(Finding(finding.text, item.removeprefix("field_") or None))
    return out


class WorkbenchGravityBuildCommands:
    """New Gravity Form, Edit Form, and Copy between QAF and Gravity Forms."""

    say: Callable[[str], None]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    ensure: Callable[[Any], Any]
    show_modal: Callable[[Any, str], int]
    refresh: Callable[[], None]
    site_of: Callable[[Any], str]
    history: Any
    parent: Any
    access_for: Callable[[str], Any]
    account_for: Callable[[str], Any]
    _access_sentence: Callable[[str], str]

    # -- may it run --------------------------------------------------------------

    def gravity_build_refusal(self, site: str, capability: str, plugin: str = "gravity") -> str:
        """Why a form may not be built on *site* now ("" when it may)."""
        if not site:
            return "Choose a site's Forms first."
        if not tier_allowed(Tier.WRITE, self.access_for(site)):
            return self._access_sentence(site)
        ctx = self.ctx(site)
        if ctx.info is not None and plugin not in form_plugins(ctx):
            if plugin == "qaf":
                return f"QUILL Accessible Forms is not on {site}."
            return (
                f"Gravity Forms is not on {site}: the site's REST index has no {GRAVITY_NAMESPACE} "
                "routes. Its REST API must be turned on in Forms > Settings > REST API."
            )
        if not capability:
            return ""
        account = self.account_for(site)
        if gravity_can(account, capability):
            return ""
        return (
            f"That needs the Gravity Forms permission {capability.replace('_', ' ')}. "
            f"You are {account.role_name} on {site}."
        )

    def gravity_form_findings(self, form: dict[str, Any]) -> list[Finding]:
        return check_form(form) + shared_findings(form)

    # -- the commands ----------------------------------------------------------------

    def do_new_gravity_form(self, ref: Any, row: WbRow | None) -> None:
        site = row.site if row is not None and row.site else self.site_of(ref)
        if not site:
            self.say("Choose a site's Forms first.")
            return
        # Who you are and whether the site has Gravity Forms, read before asking anything.
        self.background(
            f"reading {site}", lambda: self.ensure(self.ctx(site)), lambda _c: self._new(site)
        )

    def _new(self, site: str) -> None:
        refusal = self.gravity_build_refusal(site, "gravityforms_create_form")
        if refusal:
            self.say(refusal)
            return
        title = dlg.ask_text(
            self.parent,
            self.show_modal,
            title="New Gravity Form",
            prompt="&Title:",
            help_text="The new form's name. The editor opens next; nothing is sent until you "
            "review and save.",
        )
        if not title or not title.strip():
            return
        self._edit_and_save(site, gb.new_form(title.strip()), None, "")

    def do_edit_gravity_form(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "gravity_form" or row.subkind != "gravity":
            self.say("Choose a Gravity Forms form first.")
            return
        refusal = self.gravity_build_refusal(row.site, "gravityforms_edit_forms")
        if refusal:
            self.say(refusal)
            return
        api = self.ctx(row.site).api

        def opened(form: Any) -> None:
            if not isinstance(form, dict) or not isinstance(form.get("fields"), list):
                self.say(f"Gravity Forms did not send the form {row.cell('form')} on {row.site}.")
                return
            self._edit_and_save(row.site, deepcopy(form), form, row.route)

        self.background(
            f"reading {row.cell('form') or 'the form'}", lambda: api.get(row.route), opened
        )

    # -- edit, check, preview, save ------------------------------------------------------

    def _edit_and_save(
        self,
        site: str,
        form: dict[str, Any],
        opened: dict[str, Any] | None,
        route: str,
        focus: str | None = None,
    ) -> None:
        ever = [int(f["id"]) for f in gb.fields_of(opened or {}) if str(f.get("id")).isdigit()]
        name = str(form.get("title") or "the form")
        edited = gedit.ask_form(
            self.parent,
            self.show_modal,
            title=f"{'Edit' if opened else 'New'} Gravity Form - {name}",
            form=form,
            ever=ever,
            announce=self.say,
            focus_field=focus,
        )
        if edited is None:
            return
        name = str(edited.get("title") or "Untitled form")
        findings = self.gravity_form_findings(edited)
        if findings and not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title="Check Before Saving",
            summary=f"{len(findings)} things to look at in {name} before it is saved. Cancel goes "
            "back to the editor, on the first of them.",
            lines=[f.text for f in findings],
            yes="Save Anyway",
        ):
            first = next((f.field_id for f in findings if f.field_id), None)
            self._edit_and_save(site, edited, opened, route, focus=first)
            return
        if opened is not None and edited == opened:
            self.say(f"Nothing changed in {name}; nothing was sent.")
            return
        lines = [f"Site: {site}", *gs.change_lines(opened, edited)]
        if not wdlg.ask_preview(
            self.parent,
            self.show_modal,
            title="Save Gravity Form",
            summary=f"{'Save' if opened else 'Make'} {name} on {site}.",
            lines=lines,
            yes="Save Form" if opened else "Make Form",
        ):
            return
        api = self.ctx(site).api
        if opened is None:
            self.background(
                f"making {name}",
                lambda: gs.create(api, edited),
                lambda s: self._made(site, name, s),
            )
            return

        def saved(answer: gs.Saved) -> None:
            self._record_edit(site, name, api, route, opened, edited, answer)

        self.background(f"saving {name}", lambda: gs.update(api, route, opened, edited), saved)

    def _said(self, site: str, name: str, verb: str, answer: gs.Saved) -> str:
        if answer.problems:
            return (
                f"{name} on {site} was {verb}, but it reads back differently: "
                + " ".join(answer.problems)
                + " Ctrl+Z puts it back as it was."
            )
        return f"{verb.capitalize()} {name} on {site}. Entries were not touched."

    def _made(self, site: str, name: str, answer: gs.Saved) -> None:
        api = self.ctx(site).api
        said = self._said(site, name, "made", answer)

        def undo() -> str:
            gs.trash(api, answer.route)
            return f"Moved {name} to Gravity Forms' Trash on {site}, where it can be restored."

        self.history.record(Change(f"{site}: {name}", said, undo=undo))
        self.say(said)
        self.refresh()

    def _record_edit(
        self,
        site: str,
        name: str,
        api: Any,
        route: str,
        opened: dict[str, Any],
        edited: dict[str, Any],
        answer: gs.Saved,
    ) -> None:
        expected = {"form": answer.stored or edited}

        def put(body: dict[str, Any], message: str) -> str:
            stored = gs.put_back(api, route, expected["form"], body)
            expected["form"] = stored if isinstance(stored, dict) else body
            return message

        said = self._said(site, name, "saved", answer)
        self.history.record(
            Change(
                f"{site}: {name}",
                said,
                undo=lambda: put(opened, f"Put {name} back as it was on {site}."),
                redo=lambda: put(edited, f"Saved {name} again on {site}."),
            )
        )
        self.say(said)
        self.refresh()

    # -- between the two plugins --------------------------------------------------------

    def do_copy_as_gravity_form(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "form" or row.subkind != "qaf":
            self.say("Choose a QUILL Accessible Forms form first.")
            return
        refusal = self.gravity_build_refusal(row.site, "gravityforms_create_form")
        if refusal:
            self.say(refusal)
            return
        api = self.ctx(row.site).api
        title = row.cell("form") or row.title

        def read(raw: Any) -> None:
            model = qaf_site.form_from_payload(raw).model()
            if model is None:
                self.say(f"QUILL Accessible Forms did not send the model of {title}.")
                return
            converted = to_gravity(model)
            fields = gb.fields_of(converted.form)
            lines = [
                f"Site: {row.site}",
                f"New Gravity Forms form: {converted.form.get('title')}, {len(fields)} fields.",
                *(f"Cannot carry over: {line}" for line in converted.lost),
                "Responses stay with the QUILL Accessible Forms form; none are copied.",
            ]
            if not wdlg.ask_preview(
                self.parent,
                self.show_modal,
                title="Copy as a Gravity Form",
                summary=f"Make a Gravity Forms form from {title} on {row.site}.",
                lines=lines,
                yes="Make Gravity Form",
            ):
                return
            name = str(converted.form.get("title") or title)
            self.background(
                f"making {name}",
                lambda: gs.create(api, converted.form),
                lambda saved: self._made(row.site, name, saved),
            )

        self.background(f"reading {title}", lambda: api.get(row.route), read)

    def do_copy_as_qaf_form(self, _ref: Any, row: WbRow | None) -> None:
        if row is None or row.kind != "gravity_form" or row.subkind != "gravity":
            self.say("Choose a Gravity Forms form first.")
            return
        refusal = self.gravity_build_refusal(row.site, "", plugin="qaf")
        if refusal:
            self.say(refusal)
            return
        ctx = self.ctx(row.site)
        info = ctx.info
        namespace = next(
            (n for n in qaf_site.NAMESPACES if info is not None and info.supports(n)),
            qaf_site.NAMESPACE,
        )
        row = replace(row, cells={**row.cells, "title": row.cell("form") or row.title})

        def read(form: Any) -> None:
            if not isinstance(form, dict):
                self.say(f"Gravity Forms did not send {row.title} on {row.site}.")
                return
            converted = to_qaf(form)
            problems = M.validate(converted.form)
            if problems:
                first = problems[0]
                said = first.get("message", first) if isinstance(first, dict) else first
                self.say(f"QUILL could not make a valid QUILL Accessible Forms form: {said}")
                return
            lines = [
                f"Site: {row.site}",
                f"New QUILL Accessible Forms draft: {converted.form.get('title')}.",
                *(f"Cannot carry over: {line}" for line in converted.lost),
                "Entries stay with the Gravity Forms form; none are copied.",
            ]
            if not wdlg.ask_preview(
                self.parent,
                self.show_modal,
                title="Copy as a QUILL Accessible Form",
                summary=f"Make a QUILL Accessible Forms draft from {row.title} on {row.site}.",
                lines=lines,
                yes="Make Draft",
            ):
                return
            from quill.ui import forms_doc

            body = qaf_site.publish_body(
                converted.form, forms_doc.canonical(converted.form), status="draft"
            )

            def made(_answer: Any) -> None:
                said = (
                    f"Made a QUILL Accessible Forms draft of {row.title} on {row.site}. "
                    "Delete it in Forms if you do not want it."
                )
                self.history.record(Change(f"{row.site}: {row.title}", said))
                self.say(said)
                self.refresh()

            self.background(
                "making a QUILL Accessible Forms draft",
                lambda: api.request("POST", f"{namespace}/forms", json_body=body).payload,
                made,
            )

        api = ctx.api
        self.background(f"reading {row.title}", lambda: api.get(row.route), read)
