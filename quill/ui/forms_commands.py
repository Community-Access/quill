"""The Forms commands, once, for QUILL and QUILL Lite (wordpress.md 17a.4 to 17a.6).

Each ``cmd_*`` here is one row of :data:`quill.core.forms.menu.PLACES`, in
both editors. The editor is reached only through the host the WordPress
commands already use (:class:`~quill.ui.wordpress_host.WordPressHost`): the
document's path and text, a whole-text replace that is one undo step, the
caret, the modal runner and the announcer. Nothing here touches the network;
everything a form does before it is published runs on this computer.

A form document is a BFL file (:data:`~quill.core.forms.menu.FORM_EXTENSION`).
The commands about the form in front of you say why when there is none,
because the Command Palette can reach them from anywhere.
"""

from __future__ import annotations

from typing import Any

from quill.core.forms import model as M
from quill.core.forms.menu import FORM_EXTENSION, is_form_path
from quill.core.wordpress.block_catalog import Field as Ask
from quill.ui import forms_check as fc
from quill.ui import forms_dialogs as fdlg
from quill.ui import forms_doc as fd
from quill.ui import forms_field_types as ft
from quill.ui import forms_fill as ff
from quill.ui import forms_fill_window as ffw
from quill.ui import wordpress_block_dialogs as wbd
from quill.ui import wordpress_dialogs as dlg
from quill.ui.forms_outline_commands import FormsOutlineCommands
from quill.ui.forms_publish_commands import FormsPublishCommands
from quill.ui.forms_templates import TEMPLATES


def not_a_form(command: str) -> str:
    return (
        f"{command} works in a form document, a {FORM_EXTENSION} file. Start one with New Form "
        "in the File menu, or open one."
    )


class FormsCommands(FormsPublishCommands, FormsOutlineCommands):
    def __init__(self, host: Any) -> None:
        self.host = host

    # ------------------------------------------------------------------ #
    # plumbing

    def document(self, command: str) -> Any | None:
        """The form in front, read; or say why there is none and return None."""
        if not is_form_path(self.host.current_path()):
            self.host.announce(not_a_form(command))
            return None
        return fd.read(self.host.current_text())

    def apply(self, doc: Any, said: str, go_to: str | None = None) -> None:
        """Write the edited model back as one undo step, then say what changed."""
        text = fd.write(doc)
        if text != self.host.current_text():
            self.host.replace_text(text)
        if go_to:
            offset = fd.item_offset(fd.read(text), go_to)
            if offset is not None:
                self.host.go_to_offset(offset)
        if said:
            self.host.announce(said)

    # ------------------------------------------------------------------ #
    # File > New Form (17a.4.1)

    def cmd_new_form(self) -> None:
        answers = wbd.ask_fields(
            self.host.parent,
            self.host.show_modal,
            title="New Form",
            purpose=(
                "Start a form from a template. QUILL writes it as plain text in the QAF form "
                "language, saves it, and opens it; change anything afterwards."
            ),
            fields=[
                Ask("title", "&Title:", "text", "The form's name, as visitors will see it."),
                Ask(
                    "template",
                    "Te&mplate:",
                    "choice",
                    "What to start from. Each template is a few questions you can change.",
                    value=TEMPLATES[0].id,
                    choices=[f"{t.name}: {t.description}" for t in TEMPLATES],
                    values=[t.id for t in TEMPLATES],
                ),
            ],
            ok_label="Next",
        )
        if answers is None:
            return
        template = next((t for t in TEMPLATES if t.id == answers.get("template")), TEMPLATES[0])
        model = template.model(str(answers.get("title") or ""))
        path = fdlg.ask_save_path(
            self.host.parent,
            self.host.show_modal,
            title="Save the New Form",
            suggested=model["title"],
        )
        if path is None:
            return
        try:
            path.write_text(fd.canonical(model), encoding="utf-8", newline="\n")
        except OSError as exc:
            self.host.announce(f"QUILL could not save {path.name}: {exc.strerror or exc}.")
            return
        self.host.open_path(path)
        count = len(fd.fields(model))
        self.host.announce(
            f"Saved {path.name}, a {template.name.lower()} with {count} "
            + ("question." if count == 1 else "questions.")
        )

    # ------------------------------------------------------------------ #
    # Insert > Form Field (17a.4.2)

    def cmd_insert_field(self) -> None:
        doc = self.document("Insert Form Field")
        if doc is None:
            return
        kinds = ft.kinds()
        index = fdlg.pick_from_list(
            self.host.parent,
            self.host.show_modal,
            title="Insert Form Field",
            purpose=(
                "Every kind of question a form can ask, with Section and Page Break first. "
                "Type to narrow the list, then choose one; the next window asks only what it needs."
            ),
            list_label="&Kind of question:",
            list_help="Each kind and what a visitor meets. Press Enter to choose the selected one.",
            rows=[ft.row(k) for k in kinds],
            filter_label="&Search:",
            filter_help="Type words, such as date or choose, and press Enter to narrow the list.",
            matches=lambda query, i: ft.matches(query, kinds[i]),
            details=lambda i: ft.describe(kinds[i]),
        )
        if index is None:
            return
        kind = kinds[index]
        answers = wbd.ask_fields(
            self.host.parent,
            self.host.show_modal,
            title=f"Insert {ft.spoken(kind)}",
            purpose=f"{ft.describe(kind)} Fill in what it needs; anything can change later.",
            fields=self._field_questions(kind),
            ok_label="Insert",
        )
        if answers is None:
            return
        self._insert(doc, kind, answers)

    def _field_questions(self, kind: str) -> list[Ask]:
        if kind == ft.PAGE_BREAK:
            return [Ask("label", "Page &title (optional):", "text", "A title for the new page.")]
        asks = [Ask("label", "&Label:", "text", "The question, as visitors will hear it.")]
        if kind == ft.SECTION:
            return asks
        asks += [
            Ask("id", "&Id (optional):", "text", "The name rules use for it. Left empty, QUILL "
                "makes one from the label."),
            Ask("required", "&Required", "check", "Visitors must answer it to send the form."),
            Ask("help", "&Help text:", "multiline", "A sentence under the question saying what "
                "is expected. A screen reader reads it with the question."),
        ]  # fmt: skip
        if ft.takes_choices(kind):
            asks.append(
                Ask("choices", "&Choices, one per line:", "multiline", "Each line is one choice. "
                    "Leave it empty to use a choice library instead.")
            )  # fmt: skip
            asks.append(self._library_question())
        return asks

    def _library_question(self) -> Ask:
        try:
            from quill.core.forms import libraries

            found = sorted(libraries.all_info(), key=lambda i: i.label.lower())
        except Exception:  # noqa: BLE001 - no libraries is no library choice, not a failure
            found = []
        return Ask(
            "library",
            "Choice li&brary:",
            "choice",
            "A ready-made list, such as countries or time zones, used when there are no choices "
            "above. Type a letter to jump through the list.",
            value="",
            choices=["None"] + [f"{i.label}, {i.count} choices" for i in found],
            values=[""] + [i.id for i in found],
        )

    def _insert(self, doc: Any, kind: str, answers: dict[str, Any]) -> None:
        model = doc.model
        label = str(answers.get("label") or "").strip()
        after = self._item_at_caret(doc)
        if kind == ft.PAGE_BREAK:
            said = self._page_break(model, after, label)
            self.apply(doc, said)
            return
        item: dict[str, Any] = {
            "id": fd.new_id(model, str(answers.get("id") or "") or label or kind),
            "type": kind,
        }
        if label:
            item["label"] = label
        if kind == ft.SECTION:
            item["items"] = []
        else:
            if answers.get("required"):
                item["required"] = True
            if str(answers.get("help") or "").strip():
                item["help"] = str(answers["help"]).strip()
            lines = [ln.strip() for ln in str(answers.get("choices") or "").splitlines()]
            lines = [ln for ln in lines if ln]
            if lines:
                item["choices"] = [{"value": M.slug(ln) or f"choice-{n}", "label": ln}
                                   for n, ln in enumerate(lines, 1)]  # fmt: skip
            elif answers.get("library"):
                item["choice_library"] = str(answers["library"])
            elif kind in M.CHOICE_TYPES:
                item["choices"] = [{"value": "choice-1", "label": "Choice 1"}]
        self._place_new(model, item, after)
        self.apply(doc, f"Inserted {fd.name_of(item)}, {ft.spoken(kind).lower()}.", item["id"])

    def _item_at_caret(self, doc: Any) -> str | None:
        """The id of the last item that starts at or before the caret, if any."""
        caret = self.host.caret_offset()
        best: tuple[int, str] | None = None
        for item in M.iter_items(doc.model):
            offset = fd.item_offset(doc, str(item.get("id")))
            if offset is not None and offset <= caret and (best is None or offset >= best[0]):
                best = (offset, str(item.get("id")))
        return best[1] if best else None

    def _place_new(self, model: fd.Model, item: dict[str, Any], after: str | None) -> None:
        where = fd.place_of(model, after) if after else None
        if where is None:
            pages = model.setdefault("pages", [{"id": "page_1", "items": []}])
            pages[0].setdefault("items", []).insert(0, item)
            return
        current = where.siblings[where.index]
        if current.get("type") == "section" and item.get("type") != "section":
            current.setdefault("items", []).insert(0, item)
            return
        where.siblings.insert(where.index + 1, item)

    def _page_break(self, model: fd.Model, after: str | None, title: str) -> str:
        pages = model.setdefault("pages", [{"id": "page_1", "items": []}])
        where = fd.place_of(model, after) if after else None
        page_index = where.page if where else 0
        items = pages[page_index].setdefault("items", [])
        top = where
        while top is not None and top.parent is not None:
            top = fd.place_of(model, str(top.parent.get("id")))
        cut = top.index + 1 if top is not None else 0
        new_page: dict[str, Any] = {"id": fd.new_id(model, "page"), "items": items[cut:]}
        if title:
            new_page["title"] = title
        del items[cut:]
        pages.insert(page_index + 1, new_page)
        return f"Page break inserted. Page {page_index + 2} starts here."

    # ------------------------------------------------------------------ #
    # Tools > Forms (17a.4.5, 17a.5, 17a.6, 17a.8)

    def cmd_check(self) -> None:
        if self.document("Check This Form") is None:
            return
        findings = fc.check(self.host.current_text())
        if not findings:
            self.host.announce("Check This Form found nothing to fix.")
            return

        def go(row: int | None) -> object:
            if row is None or row >= len(findings):
                return None
            finding = findings[row]
            offset = finding.offset
            if offset is None and finding.item_id:
                offset = fd.item_offset(fd.read(self.host.current_text()), finding.item_id)
            if offset is None:
                self.host.announce("That finding is about the whole form, not one line.")
                return None
            self.host.go_to_offset(offset)
            return dlg.CLOSE

        def again(_row: int | None) -> object:
            findings[:] = fc.check(self.host.current_text())
            return [f.text for f in findings]

        count = len(findings)
        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title="Check This Form",
            purpose=(
                f"{count} thing{'' if count == 1 else 's'} to fix in this form, most serious "
                "first. "
                "Go to It takes you to the line; Check Again after you change it."
            ),
            list_label="&Findings:",
            list_help="Each finding says what to fix. Press Enter to go to it.",
            rows=[f.text for f in findings],
            actions=[
                dlg.Action("&Go to It", "Close this window and put the cursor on the line.", go),
                dlg.Action(
                    "Check &Again",
                    "Check the form again and refresh the list.",
                    again,
                    needs_row=False,
                ),
            ],  # fmt: skip
            on_enter=go,
        )
        window.Destroy()

    def cmd_fill_in(self) -> None:
        doc = self.document("Fill It In Yourself")
        if doc is None:
            return
        if not fd.fields(doc.model):
            self.host.announce("This form has no questions to fill in yet.")
            return
        if fd.reading_problems(doc):
            self.host.announce(
                "QUILL could not read all of this form, so some questions may be missing. "
                "Check This Form says where."
            )
        ffw.show_fill_window(
            self.host.parent,
            self.host.show_modal,
            session=ff.FillSession(doc.model),
            announce=self.host.announce,
        )

    def cmd_properties(self) -> None:
        doc = self.document("Form Properties")
        if doc is None:
            return
        model = doc.model
        settings = model.get("settings") or {}
        message = next(
            (c for c in model.get("confirmations") or [] if c.get("type") == "message"), {}
        )
        redirect = next(
            (c for c in model.get("confirmations") or [] if c.get("type") == "redirect"), {}
        )
        answers = fdlg.ask_properties(
            self.host.parent,
            self.host.show_modal,
            title="Form Properties",
            purpose="Everything about this form that is not a question.",
            fields=[
                Ask("title", "&Title:", "text", "The form's name.", value=model.get("title", "")),
                Ask(
                    "description",
                    "&Description:",
                    "multiline",
                    "A sentence or two shown above the questions.",
                    value=model.get("description", ""),
                ),
                Ask(
                    "language",
                    "&Language:",
                    "text",
                    "The language the form is written in, as a short code such as en, fr or pt-BR.",
                    value=model.get("language", "en"),
                ),
                Ask(
                    "submit_label",
                    "&Submit button:",
                    "text",
                    "What the send button says.",
                    value=settings.get("submit_label", ""),
                ),
                Ask(
                    "message",
                    "Success &message:",
                    "multiline",
                    "What visitors read after sending the form.",
                    value=message.get("message", ""),
                ),
                Ask(
                    "url",
                    "&Redirect to:",
                    "text",
                    "A web address to go to after sending, "
                    "instead of the message. Leave it empty to show the message.",
                    value=redirect.get("url", ""),
                ),
                Ask(
                    "save",
                    "Let visitors save and &continue later",
                    "check",
                    "Visitors can save a long form part way and come back to it.",
                    value=bool(settings.get("save_continue_enabled")),
                ),
            ],  # fmt: skip
            facts=self._facts(model),
        )
        if answers is None:
            return
        self._set_properties(model, answers)
        self.apply(doc, "Form properties saved in the document.")

    def _facts(self, model: fd.Model) -> str:
        settings = model.get("settings") or {}
        on = {True: "on", False: "off"}
        notices = model.get("notifications") or []
        return "\n".join([
            f"CAPTCHA: {on[bool(settings.get('enable_captcha'))]}.",
            f"Spam trap (honeypot): {on[bool(settings.get('enable_honeypot'))]}.",
            f"Email notifications: {len(notices)}.",
            f"Form id on the site: {model.get('id') or 'not published yet'}.",
        ])  # fmt: skip

    def _set_properties(self, model: fd.Model, answers: dict[str, Any]) -> None:
        for key in ("title", "description", "language"):
            value = str(answers.get(key) or "").strip()
            if value:
                model[key] = value
            elif key != "title":
                model.pop(key, None)
        settings = model.setdefault("settings", {})
        label = str(answers.get("submit_label") or "").strip()
        _set(settings, "submit_label", label or None)
        _set(settings, "save_continue_enabled", True if answers.get("save") else None)
        if not settings:
            model.pop("settings", None)
        kept = [
            c
            for c in model.get("confirmations") or []
            if c.get("type") not in ("message", "redirect")
        ]
        if str(answers.get("message") or "").strip():
            kept.append({
                "id": "message",
                "type": "message",
                "message": str(answers["message"]).strip(),
            })
        if str(answers.get("url") or "").strip():
            kept.append({"id": "redirect", "type": "redirect", "url": str(answers["url"]).strip()})
        if kept:
            model["confirmations"] = kept
        else:
            model.pop("confirmations", None)


def _set(table: dict[str, Any], key: str, value: Any) -> None:
    if value is None:
        table.pop(key, None)
    else:
        table[key] = value
