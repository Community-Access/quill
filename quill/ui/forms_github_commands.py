"""GitHub issue forms from the Forms commands, in both editors (GitHub PRD 21.4).

A mixin of :class:`~quill.ui.forms_commands.FormsCommands`, so QUILL and QUILL
Lite reach the same two commands from Tools > Forms:

- **Save As GitHub Issue Form:** the form in front as a GitHub issue form
  (``.yml``), through :func:`quill.core.forms.interop_github.export_github_issue_form`.
  What GitHub's forms cannot hold is listed before you choose where to save,
  one line each; nothing is left out without being said.
- **Open GitHub Issue Form:** an issue form (or a discussion form) read into
  the form language, saved as a form document and opened, so it can be
  written as plain text and saved back. GitHub's own settings (labels, the
  title prefix, ids, ``render``) ride along in the form's ``@extensions``.

Both are local file work: nothing reaches GitHub, so both work in Safe Mode.
Putting the file in a repository is the GitHub Workbench's job (Repository >
Templates), or a commit.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.storage import write_text_atomic
from quill.ui import forms_dialogs as fdlg
from quill.ui import forms_doc as fd
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_route_dialogs as rdlg

YAML_WILDCARD = "GitHub issue forms (*.yml;*.yaml)|*.yml;*.yaml|All files (*.*)|*.*"
#: What starts a sentence that says GitHub will not accept the saved form.
REFUSED = "GitHub will refuse this: "


def _questions(count: int) -> str:
    return f"{count} {'question' if count == 1 else 'questions'}"


def form_kind(path: Path) -> str:
    """``discussion_form`` for a file under ``DISCUSSION_TEMPLATE``, else ``issue_form``."""
    return "discussion_form" if "DISCUSSION_TEMPLATE" in path.parts else "issue_form"


class FormsGitHubCommands:
    # Provided by the commands class and its other mixins.
    host: Any

    # ------------------------------------------------------------------ #
    # Tools > Forms > Save As GitHub Issue Form

    def cmd_save_github_issue_form(self) -> None:
        command = "Save As GitHub Issue Form"
        found = self._export_form(command)  # type: ignore[attr-defined]
        if found is None:
            return
        path, model = found
        from quill.core.forms.interop_github import export_github_issue_form

        text, report = export_github_issue_form(model)
        if report:
            dlg.show_report(
                self.host.parent,
                self.host.show_modal,
                title=f"{command}: what changes",
                text="\n".join(report),
                help_text="What a GitHub issue form cannot hold from this form, one line each, "
                "and anything GitHub would refuse. Close this to choose where to save.",
            )
        target = self._export_target(command, path.stem, ".yml", YAML_WILDCARD)  # type: ignore[attr-defined]
        if target is None:
            return
        try:
            write_text_atomic(target, text, newline="\n")
        except OSError as exc:
            self._failed(target, exc)  # type: ignore[attr-defined]
            return
        from quill.core.github.template_builder import load_draft

        asked = sum(1 for raw in load_draft(text).fields if raw.get("type") != "markdown")
        what = f"a GitHub issue form with {_questions(asked)}"
        refused = sum(1 for line in report if line.startswith(REFUSED))
        if refused:
            what += (
                f". GitHub will refuse it until {refused} "
                + ("problem is" if refused == 1 else "problems are")
                + " fixed, as listed before saving"
            )
        elif report:
            what += (
                f"; {len(report)} "
                + ("change was" if len(report) == 1 else "changes were")
                + " listed before saving"
            )
        self._saved(target, what)  # type: ignore[attr-defined]

    # ------------------------------------------------------------------ #
    # Tools > Forms > Open GitHub Issue Form

    def cmd_open_github_issue_form(self) -> None:
        command = "Open GitHub Issue Form"
        source = rdlg.pick_file(
            self.host.parent, self.host.show_modal, title=command, wildcard=YAML_WILDCARD
        )
        if source is None:
            return
        from quill.core.forms.errors import FormImportError
        from quill.core.forms.interop_github import import_github_issue_form

        try:
            imported = import_github_issue_form(
                source.read_text(encoding="utf-8"), kind=form_kind(source)
            )
        except OSError as exc:
            self.host.announce(f"QUILL could not read {source.name}: {exc.strerror or exc}.")
            return
        except (FormImportError, UnicodeDecodeError) as exc:
            reason = str(exc).rstrip(".")
            self.host.announce(f"{source.name} is not a GitHub form QUILL can read: {reason}.")
            return
        model = imported.model
        target = fdlg.ask_save_path(
            self.host.parent,
            self.host.show_modal,
            title="Save the Form",
            suggested=str(model.get("title") or source.stem),
        )
        if target is None:
            return
        try:
            target.write_text(fd.canonical(model), encoding="utf-8", newline="\n")
        except OSError as exc:
            self.host.announce(f"QUILL could not save {target.name}: {exc.strerror or exc}.")
            return
        self.host.open_path(target)
        asked = sum(1 for item in fd.fields(model) if item.get("type") != "html")
        said = f"Saved {target.name}, {source.name} as a form with {_questions(asked)}."
        if imported.report:
            said += " " + " ".join(imported.report)
        self.host.announce(said)


__all__ = ["FormsGitHubCommands", "form_kind"]
