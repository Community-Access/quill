"""Draft a Form, Plain Language, Suggest Autofill Hints, Summarise Responses (wordpress.md 17a.9).

A mixin of :class:`~quill.ui.forms_publish_commands.FormsPublishCommands`.
Optional, and through Choose Your AI exactly as the WordPress AI commands are:
the editor object carrying ``HostedAiMixin`` (``host.ai_editor()``) and its own
gates (the AI area is on, the agreement accepted, a connection that does text:
``requires=("text",)``, GATE-CAPS). Nothing new is invented.

Each command says what it sends before it sends it, and every answer is a
proposal: it is shown for reading, and applied only on a yes, as one undo
step. Summarise Responses sends people's answers, so it asks every time and
says how many. Off in Safe Mode (17a.11). The prompts and the checks on the
answers are in :mod:`quill.core.forms.ai_prompts`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.forms import ai_prompts as ap
from quill.core.forms import model as M
from quill.ui import wordpress_dialogs as dlg


def _editor(host: Any) -> Any:
    from quill.ui.wordpress_picture_ai import editor_of

    return editor_of(host)


class FormsAiCommands:
    # Provided by FormsSiteBase and the commands class.
    host: Any

    def _ask_ai(self, command: str, prompt: str, on_answer: Any) -> bool:
        """One text request to the chosen AI. False: nothing was sent (and it said why)."""
        editor = _editor(self.host)
        if editor is None:
            self.host.announce("AI help is not available in this window.")
            return False
        from quill.ui.wordpress_check_commands import ask_text_ai

        def failed(said: str) -> None:
            reason = (said or "no reason was given").rstrip(".")
            self.host.announce(f"{command}: the AI did not answer. {reason}.")

        return ask_text_ai(editor, prompt, on_answer, failed)

    def _same_form(self, path: Path, command: str) -> Any | None:
        """The form, read again when the answer arrives; None if it is no longer in front."""
        current = self.host.current_path()
        if current is None or Path(current) != path:
            self.host.announce(f"{command}: the form is no longer in front, so nothing changed.")
            return None
        from quill.ui import forms_doc as fd

        return fd.read(self.host.current_text())

    def _apply(self, doc: Any, said: str) -> None:
        from quill.ui import forms_doc as fd

        text = fd.write(doc)
        if text != self.host.current_text():
            self.host.replace_text(text)
        self.host.announce(said)

    # ------------------------------------------------------------------ #
    # Draft a Form

    def cmd_draft_form(self) -> None:
        command = "Draft a Form"
        if self.offline_only(command):  # type: ignore[attr-defined]
            return
        description = dlg.ask_text(
            self.host.parent,
            self.host.show_modal,
            title=command,
            prompt="&Describe the form:",
            value="",
            help_text="A sentence or two: who fills it in, and what you need to know. Only "
            "this description goes to your chosen AI. You read the draft before it is used.",
            multiline=True,
        )
        if description is None or not description.strip():
            return
        self.host.announce(
            f"{command} sends your description, and nothing else, to your chosen AI."
        )
        self._ask_ai(command, ap.draft_prompt(description), self._drafted)

    def _drafted(self, answer: str) -> None:
        from quill.core.forms.menu import is_form_path
        from quill.ui import forms_doc as fd

        bfl = ap.extract_bfl(answer)
        doc = fd.read(bfl)
        count = len(M.fields(doc.model))
        if not count:
            self.host.announce("The AI's draft could not be read as a form. Nothing was changed.")
            return
        problems = len(getattr(doc, "errors", []) or [])
        note = f" It has {problems} reading problems to fix." if problems else ""
        dlg.show_report(
            self.host.parent,
            self.host.show_modal,
            title="Draft a Form: the proposal",
            text=bfl,
            help_text=f"The AI's draft, {count} questions, in the form language. Read it; the "
            "next question asks whether to use it.",
        )
        in_form = is_form_path(self.host.current_path())
        where = "replace the form in front" if in_form else "save it as a new form"
        if not dlg.confirm(
            self.host.parent,
            self.host.show_modal,
            title="Draft a Form",
            message=f"Use this draft of {count} questions? It will {where}.{note}",
            yes_label="Use It",
        ):
            return
        if in_form:
            self.host.replace_text(bfl)
            self.host.announce(f"The draft is in, {count} questions. Undo takes it out.")
            return
        from quill.ui import forms_dialogs as fdlg

        path = fdlg.ask_save_path(
            self.host.parent,
            self.host.show_modal,
            title="Save the Drafted Form",
            suggested=str(doc.model.get("title") or "form"),
        )
        if path is None:
            return
        try:
            path.write_text(bfl, encoding="utf-8", newline="\n")
        except OSError as exc:
            self.host.announce(f"QUILL could not save {path.name}: {exc.strerror or exc}.")
            return
        self.host.open_path(path)
        self.host.announce(f"Saved {path.name}, a drafted form with {count} questions.")

    # ------------------------------------------------------------------ #
    # Plain Language

    def cmd_plain_language(self) -> None:
        command = "Plain Language"
        found = self.form_in_front(command)  # type: ignore[attr-defined]
        if found is None or self.offline_only(command):  # type: ignore[attr-defined]
            return
        path, doc = found
        count = len(ap.wording(doc.model))
        if not count:
            self.host.announce("This form has no questions to rewrite yet.")
            return
        self.host.announce(
            f"{command} sends the labels and help text of {count} questions to your chosen AI. "
            "No answers are sent."
        )
        prompt = ap.plain_language_prompt(doc.model)
        self._ask_ai(command, prompt, lambda answer: self._plain_answered(path, doc, answer))

    def _plain_answered(self, path: Path, asked: Any, answer: str) -> None:
        changes = ap.plain_changes(asked.model, answer)
        if not changes:
            self.host.announce("Your AI found nothing to make plainer. Nothing was changed.")
            return
        lines = [
            f"{item_id}, {'question' if part == 'label' else 'help'}:\n"
            f"  Now: {old}\n  Plainer: {new}"
            for item_id, part, old, new in changes
        ]
        if not self._review("Plain Language", lines, len(changes), "rewording"):
            return
        doc = self._same_form(path, "Plain Language")
        if doc is None:
            return
        applied = 0
        for item_id, part, old, new in changes:
            item = M.find(doc.model, item_id)
            if item is not None and str(item.get(part) or "") == old:
                item[part] = new
                applied += 1
        self._apply(doc, f"{applied} rewordings applied. Undo takes them all out.")

    def _review(self, command: str, lines: list[str], count: int, noun: str) -> bool:
        dlg.show_report(
            self.host.parent,
            self.host.show_modal,
            title=f"{command}: the proposal",
            text="\n\n".join(lines) + "\n",
            help_text=f"What your AI proposes, {count} in all, each with what is there now. "
            "Read it; the next question asks whether to apply it.",
        )
        plural = noun + ("" if count == 1 else "s")
        return dlg.confirm(
            self.host.parent,
            self.host.show_modal,
            title=command,
            message=f"Apply {count} {plural}? It is one step, and Undo takes it all out.",
            yes_label="Apply",
        )

    # ------------------------------------------------------------------ #
    # Suggest Autofill Hints and Help Text

    def cmd_suggest_autofill(self) -> None:
        command = "Suggest Autofill Hints"
        found = self.form_in_front(command)  # type: ignore[attr-defined]
        if found is None or self.offline_only(command):  # type: ignore[attr-defined]
            return
        path, doc = found
        flagged = ap.needs_help(doc.model)
        if not flagged:
            self.host.announce(
                "Every question that takes an autofill hint has one, and every format rule has "
                "help. Nothing to suggest."
            )
            return
        self.host.announce(
            f"{command} sends the labels and types of {len(flagged)} questions to your chosen "
            "AI. No answers are sent."
        )
        prompt = ap.autofill_prompt(doc.model)
        self._ask_ai(command, prompt, lambda answer: self._autofill_answered(path, doc, answer))

    def _autofill_answered(self, path: Path, asked: Any, answer: str) -> None:
        changes = ap.autofill_changes(asked.model, answer)
        if not changes:
            self.host.announce("Your AI suggested nothing usable. Nothing was changed.")
            return
        labels = M.labels(asked.model)
        lines = [
            f"{labels.get(i) or i}: "
            + (f"autofill hint {value}" if part == "autocomplete" else f"help: {value}")
            for i, part, value in changes
        ]
        if not self._review("Suggest Autofill Hints", lines, len(changes), "suggestion"):
            return
        doc = self._same_form(path, "Suggest Autofill Hints")
        if doc is None:
            return
        applied = 0
        for item_id, part, value in changes:
            item = M.find(doc.model, item_id)
            if item is None:
                continue
            if part == "autocomplete":
                item.setdefault("props", {})["autocomplete"] = value
            elif not item.get("help"):
                item["help"] = value
            applied += 1
        self._apply(doc, f"{applied} suggestions applied. Undo takes them all out.")

    # ------------------------------------------------------------------ #
    # Summarise Responses (from the Responses window)

    def summarise_responses(self, title: str, responses: list[Any], labels: dict[str, str]) -> None:
        command = "Summarise Responses"
        if self.offline_only(command):  # type: ignore[attr-defined]
            return
        if not responses:
            self.host.announce("There are no responses to summarise.")
            return
        from quill.core.forms import responses as rs

        prompt, sent = ap.summary_prompt(title, [rs.pairs(r, labels) for r in responses])
        left = len(responses) - sent
        more = f" The other {left} do not fit in one request and stay here." if left else ""
        noun = "response" if sent == 1 else "responses"
        if not dlg.confirm(
            self.host.parent,
            self.host.show_modal,
            title=command,
            message=f"Send the answers in {sent} {noun} to {title} to your chosen AI? They "
            "may include names, email addresses and anything else people wrote. QUILL asks "
            f"every time.{more}",
            yes_label=f"Send {sent}",
        ):
            return

        def answered(summary: str) -> None:
            dlg.show_report(
                self.host.parent,
                self.host.show_modal,
                title=f"Summary of responses to {title}",
                text=summary.strip() or "Your AI gave no summary.",
                help_text=f"Your AI's summary of {sent} {noun}. Check it against the responses "
                "before you rely on it.",
            )

        self._ask_ai(command, prompt, answered)


__all__ = ["FormsAiCommands"]
