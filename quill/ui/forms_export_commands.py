"""Save a form as a web page, a Word document, large print or braille (wordpress.md 17a.7).

A mixin of :class:`~quill.ui.forms_publish_commands.FormsPublishCommands`.
Everything here is local: nothing reaches a site or an AI, so every export
works in Safe Mode (17a.11). One source, every format -- each export reads the
form in front through the same model, so a paper form and its web form can
never disagree.

- **Web page:** BAF's accessible markup patterns
  (:func:`quill.core.forms.interop_html.export_html`): a ``<label>`` for every
  control, a ``<fieldset>`` and ``<legend>`` for every group, help tied with
  ``aria-describedby``, required as an attribute and a word. It submits to an
  address you give, or nowhere when it is for printing.
- **Word and large print:** :mod:`quill.core.forms.export_word`, with lines
  to write on and boxes to check; large print is 18 point and up.
- **Braille-ready text:** :func:`quill.core.forms.print_layout.braille_text`,
  one question a block; with the braille pack installed it can also be
  translated through QUILL's own braille output (the liblouis worker, UEB
  contracted) and saved as a BRF file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.forms import model as M
from quill.core.forms import print_layout as pl
from quill.core.storage import write_text_atomic
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_route_dialogs as rdlg

WEB_WILDCARD = "Web pages (*.html)|*.html|All files (*.*)|*.*"
WORD_WILDCARD = "Word documents (*.docx)|*.docx|All files (*.*)|*.*"
TEXT_WILDCARD = "Text files (*.txt)|*.txt|All files (*.*)|*.*"
BRF_WILDCARD = "Braille files (*.brf)|*.brf|All files (*.*)|*.*"
#: QUILL's default braille code for a translated export.
BRAILLE_TABLE = "en-ueb-g2"


def _count(model: M.Model) -> str:
    count = sum(1 for b in pl.blocks(model) if b.kind == "question")
    return f"{count} {'question' if count == 1 else 'questions'}"


def _with_suffix(path: Path, suffix: str) -> Path:
    return path if path.suffix.lower() == suffix else path.with_name(path.name + suffix)


class FormsExportCommands:
    # Provided by FormsSiteBase and the commands class.
    host: Any

    def _export_target(self, title: str, stem: str, suffix: str, wildcard: str) -> Path | None:
        path = rdlg.save_as(
            self.host.parent,
            self.host.show_modal,
            title=title,
            name=stem + suffix,
            wildcard=wildcard,
        )
        return None if path is None else _with_suffix(path, suffix)

    def _export_form(self, command: str) -> tuple[Path, M.Model] | None:
        found = self.form_in_front(command)  # type: ignore[attr-defined]
        if found is None:
            return None
        path, doc = found
        if not self.readable(command, doc):  # type: ignore[attr-defined]
            return None
        return path, doc.model

    def _saved(self, target: Path, what: str) -> None:
        self.host.announce(f"Saved {target.name}, {what}.")

    def _failed(self, target: Path, exc: BaseException) -> None:
        reason = getattr(exc, "strerror", None) or str(exc)
        self.host.announce(f"QUILL could not save {target.name}: {reason}".rstrip(".") + ".")

    # ------------------------------------------------------------------ #
    # Save As Web Page

    def cmd_save_web_page(self) -> None:
        found = self._export_form("Save As Web Page")
        if found is None:
            return
        path, model = found
        action = dlg.ask_text(
            self.host.parent,
            self.host.show_modal,
            title="Save As Web Page",
            prompt="&Send answers to:",
            value="",
            help_text="The web address the form sends its answers to, starting https://. Leave "
            "it empty for a form to print or read, which sends nothing.",
        )
        if action is None:
            return
        action = action.strip()
        if action and not action.lower().startswith(("https://", "http://")):
            self.host.announce(
                "That is not a web address. Start it with https://, or leave it empty."
            )
            return
        target = self._export_target("Save As Web Page", path.stem, ".html", WEB_WILDCARD)
        if target is None:
            return
        from quill.core.forms.interop_html import export_html

        try:
            write_text_atomic(target, export_html(pl.resolve_choices(model), action=action))
        except OSError as exc:
            self._failed(target, exc)
            return
        where = f"sends its answers to {action}" if action else "sends its answers nowhere"
        self._saved(target, f"a web page with {_count(model)}. It {where}")

    # ------------------------------------------------------------------ #
    # Save As Word Document, and large print

    def cmd_save_word(self) -> None:
        self._save_word("Save As Word Document", large_print=False)

    def cmd_save_large_print(self) -> None:
        self._save_word("Save As Large Print", large_print=True)

    def _save_word(self, command: str, *, large_print: bool) -> None:
        found = self._export_form(command)
        if found is None:
            return
        path, model = found
        stem = path.stem + (" large print" if large_print else "")
        target = self._export_target(command, stem, ".docx", WORD_WILDCARD)
        if target is None:
            return
        from quill.core.forms import export_word as ew

        try:
            ew.write(model, target, large_print=large_print)
        except (OSError, ew.FormWordExportError) as exc:
            self._failed(target, exc)
            return
        kind = "a large-print Word document, 18 point and up," if large_print else "a Word form"
        self._saved(target, f"{kind} with {_count(model)}, lines to write on and boxes to check")

    # ------------------------------------------------------------------ #
    # Save As Braille-Ready Text

    def cmd_save_braille(self) -> None:
        command = "Save As Braille-Ready Text"
        found = self._export_form(command)
        if found is None:
            return
        path, model = found
        text = pl.braille_text(model)
        rows = ["Braille-ready text, 40 cells a line (.txt)"]
        if _braille_pack():
            rows.append("Braille file, translated to UEB contracted (.brf)")
        picked = (
            dlg.ask_choice(
                self.host.parent,
                self.host.show_modal,
                title=command,
                prompt="&Save as:",
                rows=rows,
                initial=0,
                help_text="Text you can emboss or read on a display as it is, or a braille "
                "file translated by QUILL's braille output.",
            )
            if len(rows) > 1
            else 0
        )
        if picked is None:
            return
        brf = picked == 1
        suffix, wildcard = (".brf", BRF_WILDCARD) if brf else (".txt", TEXT_WILDCARD)
        target = self._export_target(command, path.stem, suffix, wildcard)
        if target is None:
            return
        what = f"braille-ready text with {_count(model)}, one a block"
        if not brf:
            try:
                write_text_atomic(target, text, newline="\r\n")
            except OSError as exc:
                self._failed(target, exc)
                return
            self._saved(target, what)
            return

        def translate() -> str:
            from quill.core import braille_worker_client as worker

            return worker.forward_translate(text, table=BRAILLE_TABLE, timeout=30.0)

        def translated(result: str) -> None:
            if not result.strip():
                self.host.announce("The braille translation came back empty. Nothing was saved.")
                return
            try:
                write_text_atomic(target, result, encoding="ascii", newline="\r\n")
            except (OSError, UnicodeEncodeError) as exc:
                self._failed(target, exc)
                return
            self._saved(target, f"a braille file in UEB contracted, with {_count(model)}")

        self.host.run_task(
            "Forms: translating to braille",
            translate,
            translated,
            lambda exc: self.host.announce(
                f"The braille translation did not work: {exc}".rstrip(".") + ". Nothing was saved."
            ),
        )


def _braille_pack() -> bool:
    try:
        from quill.core.braille_pack import is_braille_pack_installed

        return bool(is_braille_pack_installed())
    except Exception:  # noqa: BLE001 - no pack means the text export alone
        return False


__all__ = ["FormsExportCommands"]
