"""View > Form Outline and Format > Form Rules (wordpress.md 17a.4.3, 17a.4.4).

Split from :mod:`quill.ui.forms_commands` under GATE-11. Both are the
WordPress list window -- a list, a details box and buttons -- so a person who
knows the Blocks window knows these. Every change is one undo step in the
editor: the window reads the document fresh, edits the form, and writes it
back, so nothing here can disagree with what is on the page.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.forms import model as M
from quill.core.wordpress.block_catalog import Field as Ask
from quill.ui import forms_dialogs as fdlg
from quill.ui import forms_doc as fd
from quill.ui import forms_field_types as ft
from quill.ui import forms_rules as fr
from quill.ui import wordpress_block_dialogs as wbd
from quill.ui import wordpress_dialogs as dlg


class FormsOutlineCommands:
    host: Any

    def document(self, command: str) -> Any | None:  # pragma: no cover - FormsCommands'
        raise NotImplementedError

    def apply(self, doc: Any, said: str, go_to: str | None = None) -> None:  # pragma: no cover
        raise NotImplementedError

    # ------------------------------------------------------------------ #
    # View > Form Outline (17a.4.3)

    def cmd_outline(self) -> None:
        doc = self.document("Form Outline")
        if doc is None:
            return

        def rows() -> list[tuple[str, str | None]]:
            return fd.outline_rows(fd.read(self.host.current_text()).model)

        def edit(change: Callable[[fd.Model, str], str]) -> Callable[[int | None], object]:
            def run(row: int | None) -> object:
                now = fd.read(self.host.current_text())
                listed = fd.outline_rows(now.model)
                if row is None or row >= len(listed):
                    return None
                item_id = listed[row][1]
                if item_id is None:
                    self.host.announce("That is a page. Move or change its questions instead.")
                    return None
                try:
                    said = change(now.model, item_id)
                except fd.Refused as why:
                    self.host.announce(str(why))
                    return None
                self.apply(now, said)
                return [
                    text for text, _id in fd.outline_rows(fd.read(self.host.current_text()).model)
                ]

            return run

        def go(row: int | None) -> object:
            listed = rows()
            if row is None or row >= len(listed):
                return None
            now = fd.read(self.host.current_text())
            item_id = listed[row][1]
            offset = (
                fd.item_offset(now, item_id) if item_id else self._page_offset(now, row, listed)
            )
            if offset is not None:
                self.host.go_to_offset(offset)
            return dlg.CLOSE

        window = fdlg.show_outline_window(
            self.host.parent,
            self.host.show_modal,
            title="Form Outline",
            purpose=(
                "Every page, section and question in this form, in order. Each change here is one "
                "step that Undo in the editor takes back. Alt+Shift and the arrows move the "
                "selected question: up and down, or into and out of a section."
            ),
            list_label="&Questions:",
            list_help=(
                "Each page, section and question, with what it needs. Press Enter to go to it; "
                "Alt+Shift and the arrow keys move it."
            ),
            rows=[text for text, _id in rows()],
            actions=[
                dlg.Action("&Go to It", "Close this window and put the cursor on it.", go),
                dlg.Action(
                    "Move &Up",
                    "Move it before the one above. Alt+Shift+Up.",
                    edit(lambda m, i: fd.move(m, i, -1)),
                ),
                dlg.Action(
                    "Move &Down",
                    "Move it after the one below. Alt+Shift+Down.",
                    edit(lambda m, i: fd.move(m, i, 1)),
                ),
                dlg.Action(
                    "Move &In",
                    "Move it into the section just above. Alt+Shift+Right.",
                    edit(fd.move_in),
                ),
                dlg.Action(
                    "Move Ou&t", "Move it out of its section. Alt+Shift+Left.", edit(fd.move_out)
                ),
                dlg.Action("&Rename...", "Change what the question says.", edit(self._rename)),
                dlg.Action(
                    "&Change Id...",
                    "Change the name rules use for it; every rule that names it changes too.",
                    edit(self._change_id),
                ),
                dlg.Action(
                    "Change T&ype...",
                    "Make it a different kind of question.",
                    edit(self._change_type),
                ),
                dlg.Action("Du&plicate", "Put a copy straight after it.", edit(fd.duplicate)),
                dlg.Action("Re&move...", "Take it out of the form.", edit(self._remove)),
            ],  # fmt: skip
            on_enter=go,
        )
        window.Destroy()

    def _page_offset(self, doc: Any, row: int, listed: list[tuple[str, str | None]]) -> int | None:
        page_number = sum(1 for text, item_id in listed[: row + 1] if item_id is None)
        if page_number <= 1:
            return 0
        pages = [s for s in getattr(doc, "statements", []) if getattr(s, "kind", "") == "page"]
        index = page_number - 2  # the first page has no page line of its own
        return int(pages[index].start) if 0 <= index < len(pages) else None

    def _rename(self, model: fd.Model, item_id: str) -> str:
        item = M.find(model, item_id) or {}
        label = dlg.ask_text(
            self.host.parent,
            self.host.show_modal,
            title="Rename",
            prompt="&Label:",
            value=str(item.get("label", "")),
            help_text="What the question says, as visitors will hear it.",
        )
        if label is None or not label.strip():
            raise fd.Refused("Nothing changed.")
        return fd.rename(model, item_id, label)

    def _change_id(self, model: fd.Model, item_id: str) -> str:
        wanted = dlg.ask_text(
            self.host.parent,
            self.host.show_modal,
            title="Change Id",
            prompt="&Id:",
            value=item_id,
            help_text="Letters, digits and underscores. Rules use it to name this question.",
        )
        if wanted is None or wanted.strip() == item_id:
            raise fd.Refused("Nothing changed.")
        return fd.change_id(model, item_id, wanted.strip())

    def _change_type(self, model: fd.Model, item_id: str) -> str:
        kinds = [k for k in ft.kinds() if k not in (ft.SECTION, ft.PAGE_BREAK)]
        item = M.find(model, item_id) or {}
        if item.get("type") in ("section", "columns"):
            raise fd.Refused("A section cannot become a question.")
        picked = dlg.ask_choice(
            self.host.parent,
            self.host.show_modal,
            title="Change Type",
            prompt="&Kind of question:",
            rows=[ft.row(k) for k in kinds],
            initial=kinds.index(item["type"]) if item.get("type") in kinds else 0,
            help_text="What it becomes. Its label, help and rules are kept.",
        )
        if picked is None:
            raise fd.Refused("Nothing changed.")
        return fd.change_type(model, item_id, kinds[picked])

    def _remove(self, model: fd.Model, item_id: str) -> str:
        item = M.find(model, item_id) or {"id": item_id}
        if not dlg.confirm(
            self.host.parent,
            self.host.show_modal,
            title="Remove",
            message=f"Remove {fd.name_of(item)} from this form? Undo in the editor brings it back.",
            yes_label="Remove",
        ):
            raise fd.Refused("Nothing changed.")
        return fd.remove(model, item_id)

    # ------------------------------------------------------------------ #
    # Format > Form Rules (17a.4.4)

    def cmd_rules(self) -> None:
        doc = self.document("Form Rules")
        if doc is None:
            return

        def rows() -> list[str]:
            return [r.text for r in fr.rule_rows(fd.read(self.host.current_text()).model)]

        def add(_row: int | None) -> object:
            now = fd.read(self.host.current_text())
            said = self._add_rule(now.model)
            if said:
                self.apply(now, said)
            return rows()

        def change(row: int | None) -> object:
            now = fd.read(self.host.current_text())
            listed = fr.rule_rows(now.model)
            if row is None or row >= len(listed):
                return None
            text = dlg.ask_text(
                self.host.parent,
                self.host.show_modal,
                title="Edit Rule",
                prompt="&Condition:",
                value=fr.current_text(now.model, listed[row]),
                help_text=(
                    'The rule in the form language, such as #type is "business". Leave it '
                    "empty to remove the rule."
                ),
            )
            if text is None:
                return None
            problem = fr.problem(text) if text.strip() else None
            if problem:
                self.host.announce(f"That rule cannot be read: {problem}")
                return None
            self.apply(now, fr.edit_rule(now.model, listed[row], text))
            return rows()

        def remove(row: int | None) -> object:
            now = fd.read(self.host.current_text())
            listed = fr.rule_rows(now.model)
            if row is None or row >= len(listed):
                return None
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title="Remove Rule",
                message=f"Remove this rule? {listed[row].text} Undo in the editor brings it back.",
                yes_label="Remove Rule",
            ):
                return None
            fr.remove_rule(now.model, listed[row])
            self.apply(now, "Rule removed.")
            return rows()

        def go(row: int | None) -> object:
            now = fd.read(self.host.current_text())
            listed = fr.rule_rows(now.model)
            if row is None or row >= len(listed) or listed[row].kind == "rule":
                return None
            offset = fd.item_offset(now, str(listed[row].key))
            if offset is not None:
                self.host.go_to_offset(offset)
            return dlg.CLOSE

        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title="Form Rules",
            purpose=(
                "Every rule in this form as a sentence: what shows or hides a question, what is "
                "worked out, and what is required when. Add Rule builds one from three choices."
            ),
            list_label="&Rules:",
            list_help="Each rule as a sentence. Press Enter to go to the question it is on.",
            rows=rows(),
            actions=[
                dlg.Action(
                    "&Add Rule...",
                    "Build a rule: when what, is what, then what.",
                    add,
                    needs_row=False,
                ),
                dlg.Action("&Edit...", "Change the selected rule's condition.", change),
                dlg.Action("Re&move...", "Take the selected rule out of the form.", remove),
                dlg.Action("&Go to It", "Close this window and go to the question.", go),
            ],  # fmt: skip
            on_enter=go,
        )
        window.Destroy()

    def _add_rule(self, model: fd.Model) -> str:
        questions = fd.fields(model)
        if not questions:
            self.host.announce("This form has no questions for a rule to use yet.")
            return ""
        names = [fd.name_of(q) for q in questions]
        ids = [str(q["id"]) for q in questions]
        pages = [str(p["id"]) for p in model.get("pages") or []]
        answers = wbd.ask_fields(
            self.host.parent,
            self.host.show_modal,
            title="Add Rule",
            purpose="When one question has an answer, do something to another. QUILL writes it "
            "into the form and reads it back as a sentence.",
            fields=[
                Ask(
                    "when",
                    "&When this question:",
                    "choice",
                    "The question the rule listens to.",
                    value=ids[0],
                    choices=names,
                    values=ids,
                ),
                Ask(
                    "test",
                    "&Is:",
                    "choice",
                    "How its answer is compared.",
                    value=0,
                    choices=[s for s, _p in fr.TESTS],
                    values=list(range(len(fr.TESTS))),
                ),
                Ask(
                    "value",
                    "This &answer:",
                    "text",
                    "The answer to compare with: one of the question's choices, "
                    "in any capitals, or a number. Not needed for filled in or empty.",
                ),
                Ask(
                    "own",
                    "Or write the condition &yourself:",
                    "text",
                    "Optional. A condition "
                    "in the form language, such as #age > 17 and #consent is filled. Used "
                    "instead of the three above.",
                ),
                Ask(
                    "action",
                    "&Then:",
                    "choice",
                    "What the rule does.",
                    value="show",
                    choices=list(fr.ACTIONS.values()),
                    values=list(fr.ACTIONS),
                ),
                Ask(
                    "target",
                    "To this &question or page:",
                    "choice",
                    "What the rule acts on. Skip to needs a page.",
                    value=ids[-1],
                    choices=names + [f"Page {n}" for n in range(1, len(pages) + 1)],
                    values=ids + pages,
                ),
            ],  # fmt: skip
            ok_label="Add Rule",
        )
        if answers is None:
            return ""
        own = str(answers.get("own") or "").strip()
        asked = next((q for q in questions if str(q["id"]) == str(answers["when"])), None)
        typed = choice_value(asked, model, str(answers.get("value") or ""))
        when = own or fr.condition(str(answers["when"]), int(answers["test"]), typed)
        problem = fr.problem(when)
        if problem:
            self.host.announce(f"That rule cannot be read: {problem}")
            return ""
        return fr.add_rule(model, str(answers["action"]), str(answers["target"]), when)


def choice_value(question: Any, model: Any, typed: str) -> str:
    """The stored value of the choice *typed* names, in any capitals.

    A choice is kept as a value ("phone") and shown as a label ("Phone").
    Typing either, in any case, gives the value, so the rule really matches
    when the form is filled in. Anything else (a number, free text) stays
    as typed.
    """
    if not question or not typed.strip():
        return typed
    from quill.core.forms import libraries

    wanted = typed.strip().casefold()
    for value, label in libraries.choices_for(question, model):
        if wanted in (str(value).casefold(), str(label).casefold()):
            return str(value)
    return typed
