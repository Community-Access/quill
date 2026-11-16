"""Repository > Templates in the GitHub Workbench, and New Discussion (GitHub PRD 21).

Each Templates row is a :class:`~quill.core.github.template_catalog.TemplateEntry`
written into an ``ExploreRow`` key as ``kind|source|path|missing``, so the
row carries what the command needs and every command reads the file again
before it opens (the sha it opens from is the one a save checks against).

- **Open Template...** (Enter) opens the builder for an issue or discussion
  form, the source for anything else, and a starter for a missing community
  file. Save asks first, says where the save goes (the default branch, or a
  new branch and pull request when it is protected or the box is checked),
  stops on a conflict, reads the file back and says one result. A save that
  fails reopens the window with the draft as it was, so nothing is lost.
- **Convert to Issue Form...** on a Markdown issue template builds the form
  from its headings and saves it beside the original.
- **Copy to Repositories...** previews each target (missing, the same, a
  different variant, unreadable) and says one result per repository.
- **New Template...** (Ctrl+N on Templates) starts from a starter.
- **New Discussion...** (Ctrl+N on Discussions) fills the category's form
  natively when it has one (``.github/DISCUSSION_TEMPLATE/<slug>.yml``), with
  the issue form window, and otherwise asks for a title and body.

Every read and write runs through the frame's background runner (GATE-13:
only outcomes are said).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.explore_models import ExploreRow
from quill.ui.github_workbench_template_data import (
    _CHOOSER,
    _NEW_KINDS,
    _PR_TEMPLATE,
    _SHEETS,
    COMMUNITY_STARTERS,
    _context,
)

__all__ = [
    "COMMUNITY_STARTERS",
    "TEMPLATE_REASONS",
    "TEMPLATE_VERBS",
    "GitHubWorkbenchTemplatesMixin",
    "template_row_key",
]

TEMPLATE_VERBS: dict[str, frozenset[str]] = {
    "open_template": frozenset({"template"}),
    "convert_template": frozenset({"template"}),
    "copy_template": frozenset({"template"}),
    "new_template": frozenset({"view"}),
    "new_discussion": frozenset({"view"}),
}

TEMPLATE_REASONS: dict[str, str] = {
    "convert_template": "Only an issue form or a Markdown issue template converts.",
    "copy_template": "A missing file has nothing to copy yet; open it to create it first.",
    "new_template": "Open a repository first. Ctrl+L opens one by name or link.",
    "new_discussion": "Open a repository first. Ctrl+L opens one by name or link.",
}


def template_row_key(kind: str, source: str, path: str, *, missing: bool = False) -> str:
    """What a Templates row keeps: ``kind|source|path|missing``."""
    return f"{kind}|{source}|{path}|{'1' if missing else ''}"


def _parse_key(row: object) -> tuple[str, str, str, bool]:
    key = row.key if isinstance(row, ExploreRow) else ""
    parts = (key.split("|") + ["", "", "", ""])[:4]
    return parts[0], parts[1], parts[2], parts[3] == "1"


def _error_text(exc: BaseException) -> str:
    return str(exc.args[0]) if exc.args else str(exc)


class GitHubWorkbenchTemplatesMixin:
    """Templates and New Discussion; the helpers are the action router's."""

    items: Any
    frame: Any
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _confirm: Callable[[str, str], bool]
    _choose: Callable[[str, str, list[str]], int]
    _ask_text: Callable[..., str]
    _current_repository: Callable[[], str]

    # -- can it run? ---------------------------------------------------------------

    def _fits_open_template(self, row: object) -> bool:
        return bool(_parse_key(row)[2])

    def _fits_convert_template(self, row: object) -> bool:
        kind, _source, path, missing = _parse_key(row)
        return kind in ("issue_template", "issue_form") and bool(path) and not missing

    def _fits_copy_template(self, row: object) -> bool:
        kind, _source, path, missing = _parse_key(row)
        return bool(path) and not missing and bool(kind)

    def _fits_new_template(self, _row: object) -> bool:
        return bool(self._current_repository())

    _fits_new_discussion = _fits_new_template

    def _template_parent(self) -> Any:
        return self.frame.frame if self.frame is not None else None

    def _template_repo(self, name: str) -> Any:
        return self.items.template_repository(name)

    # -- Open Template, and saving ---------------------------------------------------

    def _do_open_template(self, ref: Any, row: object) -> None:
        kind, source, path, missing = _parse_key(row)
        source = source or ref.instance

        def read() -> tuple[str, str, Any, dict[str, Any]]:
            from quill.core.github.template_catalog import read_entry_text
            from quill.core.github.template_save import plan_save

            repo = self._template_repo(source)
            if missing:
                text, sha = COMMUNITY_STARTERS.get(path.rsplit("/", 1)[-1], ""), ""
            else:
                text, sha = read_entry_text(repo, path)
            return text, sha, plan_save(repo, source, path), _context(repo, kind, path)

        self._background(
            f"read {path}",
            read,
            lambda found: self._open_template_builder(kind, source, path, *found),
        )

    def _open_template_builder(
        self,
        kind: str,
        source: str,
        path: str,
        text: str,
        sha: str,
        plan: Any,
        context: dict[str, Any] | None = None,
    ) -> None:
        """The builder, a sheet or the source, then the save; a failed save reopens it."""
        context = context or {}
        filename = path.rsplit("/", 1)[-1]
        if kind == "chooser":
            self._open_chooser(source, path, text, sha, plan, context)
            return
        if kind == "community_file" and filename in _SHEETS:
            from quill.ui import github_template_sheets_dialog as sheets

            extra: dict[str, Any] = {}
            if filename == "CODEOWNERS":
                # Check Owners asks GitHub in the background (PRD 21.8).
                extra["check"] = lambda rules, done: self._background(
                    "check the code owners",
                    lambda: self.items.check_codeowners(source, rules),
                    done,
                )
            sheet = getattr(sheets, _SHEETS[filename])(
                self._template_parent(), text, announce=self._say, **extra
            )
            saved = sheet.show()
            use_pull = bool(plan.needs_pull_request)
        else:
            from quill.ui.github_template_builder_dialog import TemplateBuilderDialog

            window = TemplateBuilderDialog(
                self._template_parent(),
                text=text,
                kind=kind,
                path=path,
                repository=source,
                announce=self._say,
                protected=bool(plan.needs_pull_request),
                known_labels=context.get("labels"),
                known_assignees=context.get("assignees"),
            )
            saved = window.show()
            use_pull = window.use_pull_request or bool(plan.needs_pull_request)
        if saved is None:
            return
        if not self._confirm("Save Template", plan.sentence(use_pull_request=use_pull)):
            return
        self._save_template_draft(kind, source, path, saved, sha, plan, use_pull, context)

    def _save_template_draft(
        self,
        kind: str,
        source: str,
        path: str,
        text: str,
        sha: str,
        plan: Any,
        use_pull: bool,
        context: dict[str, Any] | None = None,
    ) -> None:
        from quill.core.github.template_save import save_template

        def work() -> tuple[Any, str]:
            try:
                repo = self._template_repo(source)
                return save_template(
                    repo, plan, text, expected_sha=sha, use_pull_request=use_pull
                ), ""
            except Exception as exc:  # noqa: BLE001 - the draft is kept and offered again
                return None, _error_text(exc)

        def done(result: tuple[Any, str]) -> None:
            saved, problem = result
            if saved is not None:
                self._say(saved.sentence())
                self.frame.reload()
                return
            self._say(f"{problem} Your draft is kept; the window opens again with it.")
            self._open_template_builder(kind, source, path, text, sha, plan, context)

        self._background("save the template", work, done)

    # -- the chooser -----------------------------------------------------------------

    def _open_chooser(
        self, source: str, path: str, text: str, sha: str, plan: Any, context: dict[str, Any]
    ) -> None:
        """The Template Chooser sheet: config.yml, then the order as renames."""
        from quill.ui.github_template_sheets_dialog import ChooserDialog

        sheet = ChooserDialog(
            self._template_parent(), text, context.get("filenames", []), announce=self._say
        )
        saved = sheet.show()
        if saved is None:
            return
        renames = list(sheet.renames)
        changed = saved != text
        if not changed and not renames:
            self._say("Nothing changed.")
            return
        question = plan.sentence(use_pull_request=bool(plan.needs_pull_request))
        if renames:
            question += " The new order renames " + "; ".join(f"{a} to {b}" for a, b in renames)
        if not self._confirm("Save Template Chooser", question):
            return
        folder = path.rsplit("/", 1)[0]

        def work() -> list[str]:
            from quill.core.github.template_save import rename_templates, save_template

            repo = self._template_repo(source)
            said = []
            if changed:
                said.append(save_template(repo, plan, saved, expected_sha=sha).sentence())
            if renames:
                done = rename_templates(repo, plan, folder, renames)
                number = done.pull_request_number
                said.append(
                    f"Renamed {len(renames)} templates"
                    + (f" in pull request #{number}." if number else ".")
                )
            return said

        def finished(said: list[str]) -> None:
            self._say(" ".join(said))
            self.frame.reload()

        self._background("save the template chooser", work, finished)

    # -- Convert -------------------------------------------------------------------

    def _do_convert_template(self, ref: Any, row: object) -> None:
        kind, source, path, _missing = _parse_key(row)
        source = source or ref.instance
        if kind == "issue_form":
            self._form_to_markdown(source, path)
            return
        stem = path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        target = f".github/ISSUE_TEMPLATE/{stem}.yml"

        def read() -> tuple[str, Any]:
            from quill.core.github.template_builder import dump_draft, markdown_to_form
            from quill.core.github.template_catalog import read_entry_text
            from quill.core.github.template_save import plan_save

            repo = self._template_repo(source)
            text, _sha = read_entry_text(repo, path)
            draft = markdown_to_form(text, filename=path.rsplit("/", 1)[-1])
            return dump_draft(draft), plan_save(repo, source, target)

        def opened(found: tuple[str, Any]) -> None:
            text, plan = found
            if plan.current_sha:
                self._say(f"{target} already exists; open it from the list instead.")
                return
            self._say(
                f"Converted; each heading is now a long text field. {path} stays as it is "
                "until you remove it."
            )
            self._open_template_builder("issue_form", source, target, text, "", plan)

        self._background(f"convert {path}", read, opened)

    def _form_to_markdown(self, source: str, path: str) -> None:
        """An issue form as a Markdown template; says what it loses first."""
        stem = path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        target = f".github/ISSUE_TEMPLATE/{stem}.md"

        def read() -> tuple[str, list[str], Any]:
            from quill.core.github.template_builder import load_draft
            from quill.core.github.template_catalog import read_entry_text
            from quill.core.github.template_convert import form_to_markdown, markdown_losses
            from quill.core.github.template_save import plan_save

            repo = self._template_repo(source)
            text, _sha = read_entry_text(repo, path)
            draft = load_draft(text)
            return form_to_markdown(draft), markdown_losses(draft), plan_save(repo, source, target)

        def opened(found: tuple[str, list[str], Any]) -> None:
            text, losses, plan = found
            if plan.current_sha:
                self._say(f"{target} already exists; open it from the list instead.")
                return
            lost = " ".join(losses) or "Nothing beyond the form layout itself."
            if not self._confirm(
                "Convert to Markdown",
                f"A Markdown template loses the form's structure. {lost} Continue?",
            ):
                return
            self._open_template_builder("issue_template", source, target, text, "", plan)

        self._background(f"convert {path}", read, opened)

    # -- Copy to Repositories --------------------------------------------------------

    def _do_copy_template(self, ref: Any, row: object) -> None:
        kind, source, path, _missing = _parse_key(row)
        source = source or ref.instance
        whole_set = kind == "chooser"
        folder = path.rsplit("/", 1)[0]
        what = f"the whole template set in {folder}" if whole_set else path
        typed = self._ask_text(
            "Copy to Repositories",
            f"Copy {what} to which repositories? owner/name, separated by commas:",
        )
        targets = [name.strip() for name in typed.replace("\n", ",").split(",") if name.strip()]
        if not targets:
            return
        if whole_set:
            self._copy_set(source, folder, targets)
            return

        def preview() -> tuple[str, list[Any]]:
            from quill.core.github.template_catalog import read_entry_text
            from quill.core.github.template_save import plan_copy

            text, _sha = read_entry_text(self._template_repo(source), path)
            return text, plan_copy(self._template_repo, path, text, targets)

        self._background(
            "preview the copy", preview, lambda found: self._copy_confirmed(path, *found)
        )

    def _copy_confirmed(self, path: str, text: str, plan: list[Any]) -> None:
        from quill.core.github.template_save import copy_template

        lines = "\n".join(target.sentence() for target in plan)
        writes = [t for t in plan if t.state in ("missing", "variant")]
        if not writes:
            self._say(f"Nothing to copy. {lines}")
            return
        if not self._confirm("Copy to Repositories", f"Copy {path}?\n\n{lines}"):
            return

        def done(results: list[Any]) -> None:
            good = sum(1 for r in results if r.ok)
            self._say(
                f"Copied to {good} of {len(results)} repositories. "
                + " ".join(r.sentence for r in results)
            )

        self._background(
            "copy the template",
            lambda: copy_template(self._template_repo, path, text, plan),
            done,
        )

    # -- New Template ----------------------------------------------------------------

    def _do_new_template(self, _ref: Any, _row: object) -> None:
        from quill.core.github.template_builder import STARTERS, dump_draft, starter

        repository = self._current_repository()
        if not repository:
            self._say(TEMPLATE_REASONS["new_template"])
            return
        index = self._choose(
            "New Template", f"What to make in {repository}:", [k[0] for k in _NEW_KINDS]
        )
        if index < 0:
            return
        _label, kind, folder = _NEW_KINDS[index]
        if kind == "chooser":
            path, text = f"{folder}/config.yml", _CHOOSER
        elif kind == "pull_request_template":
            path, text = f"{folder}/pull_request_template.md", _PR_TEMPLATE
        else:
            names = list(STARTERS)
            labels = [STARTERS[n] for n in names]
            if kind == "issue_form":  # the SurveyJS and XLSForm door (PRD 21.4)
                from quill.ui.github_workbench_form_file import FROM_FILE_LABEL

                labels.append(FROM_FILE_LABEL)
            chosen = self._choose("New Template", "Start from:", labels)
            if chosen < 0:
                return
            if chosen == len(names):
                from quill.ui.github_workbench_form_file import start_from_form_file

                start_from_form_file(self, repository, folder)
                return
            prompt = (
                "The discussion category's slug (its form is named after it):"
                if kind == "discussion_form"
                else "File name for the form:"
            )
            default = "" if kind == "discussion_form" else names[chosen].replace("_", "-")
            name = self._ask_text("New Template", prompt, value=default)
            stem = name.strip().removesuffix(".yml").removesuffix(".yaml")
            if not stem:
                return
            path = f"{folder}/{stem}.yml"
            text = dump_draft(starter(names[chosen], kind=kind))

        def read() -> Any:
            from quill.core.github.template_save import plan_save

            return plan_save(self._template_repo(repository), repository, path)

        def opened(plan: Any) -> None:
            if plan.current_sha:
                self._say(f"{path} already exists; open it from the Templates list.")
                return
            self._open_template_builder(kind, repository, path, text, "", plan)

        self._background("read the default branch", read, opened)

    # -- New Discussion --------------------------------------------------------------

    def _do_new_discussion(self, _ref: Any, _row: object) -> None:
        repository = self._current_repository()
        if not repository:
            self._say(TEMPLATE_REASONS["new_discussion"])
            return
        self._background(
            "read the discussion categories",
            lambda: self.items.fetch_discussion_categories(repository),
            lambda found: self._discussion_category(repository, *found),
        )

    def _discussion_category(self, repository: str, repo_id: str, categories: list[Any]) -> None:
        index = self._choose(
            "New Discussion",
            f"Category for the discussion in {repository}:",
            [c.name + (", takes answers" if c.answerable else "") for c in categories],
        )
        if index < 0:
            return
        category = categories[index]

        def read_form() -> Any:
            from quill.core.github.issue_forms import parse_issue_form
            from quill.core.github.template_catalog import read_entry_text

            if not category.slug:
                return None
            path = f".github/DISCUSSION_TEMPLATE/{category.slug}.yml"
            try:
                text, _sha = read_entry_text(self._template_repo(repository), path)
            except Exception as exc:  # noqa: BLE001 - no form is the normal case
                if getattr(exc, "status", None) == 404:
                    return None
                raise
            return parse_issue_form(text, f"{category.slug}.yml")

        self._background(
            "read the category's form",
            read_form,
            lambda form: self._fill_discussion(repository, repo_id, category, form),
        )

    def _fill_discussion(self, repository: str, repo_id: str, category: Any, form: Any) -> None:
        values: tuple[str, str] | None = None
        if form is not None and not form.unsupported:
            from quill.ui.github_issue_form_dialog import IssueFormDialog

            window = IssueFormDialog(
                self._template_parent(),
                form,
                repository=repository,
                announce=self._say,
                noun="discussion",
                action_label="Start Discussion",
            )
            if not window.show() or window.result is None:
                return
            values = window.result
        else:
            if form is not None:
                self._say(f"{form.unsupported} The plain discussion form is used instead.")
            from quill.ui.github_discussion_dialog import NewDiscussionDialog

            chosen = NewDiscussionDialog(
                self._template_parent(), [category], announce_cb=self._say
            ).show()
            if chosen is None:
                return
            values = (chosen[1], chosen[2])
        title, body = values
        labels = tuple(getattr(form, "labels", ()) or ()) if form is not None else ()
        note = (
            f"\n\nThe form asks for the labels {', '.join(labels)}; starting a discussion "
            "this way does not add them, so add them on GitHub if they matter."
            if labels
            else ""
        )
        if not self._confirm(
            "Start Discussion",
            f"Start a discussion in {repository}, {category.name}?\n\nTitle: {title}\n\n"
            f"{body[:2000]}{note}",
        ):
            return
        self._background(
            "start the discussion",
            lambda: self.items.create_discussion(repo_id, category.id, title, body),
            lambda made: (
                self._say(f"Started discussion #{made[0]} in {category.name}."),
                self.frame.reload(),
            ),
        )

    # -- a whole set ---------------------------------------------------------------

    def _copy_set(self, source: str, folder: str, targets: list[str]) -> None:
        """Every file in the issue template folder, with its chooser, to each target."""

        def preview() -> tuple[dict[str, str], dict[str, list[Any]]]:
            from quill.core.github.template_catalog import read_entry_text
            from quill.core.github.template_save import plan_copy_set

            repo = self._template_repo(source)
            files: dict[str, str] = {}
            for entry in repo.get_contents(folder):
                if str(getattr(entry, "type", "")) == "file":
                    files[entry.path] = read_entry_text(repo, entry.path)[0]
            return files, plan_copy_set(self._template_repo, files, targets)

        def confirm(found: tuple[dict[str, str], dict[str, list[Any]]]) -> None:
            from quill.core.github.template_save import copy_set

            files, plan = found
            lines = []
            for repository, rows in plan.items():
                states = ", ".join(f"{p.rsplit('/', 1)[-1]} {t.state}" for p, t in rows)
                lines.append(f"{repository}: {states}.")
            if not self._confirm(
                "Copy Template Set",
                f"Copy {len(files)} files from {folder}?\n\n" + "\n".join(lines),
            ):
                return

            def done(results: list[Any]) -> None:
                good = sum(1 for r in results if r.ok)
                self._say(
                    f"Copied the set to {good} of {len(results)} repositories. "
                    + " ".join(r.sentence for r in results)
                )

            self._background(
                "copy the template set", lambda: copy_set(self._template_repo, files, plan), done
            )

        self._background("preview the set", preview, confirm)
