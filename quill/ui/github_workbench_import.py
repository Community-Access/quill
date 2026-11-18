"""Issues in: Import Issues from a Spreadsheet and New Issues from Lines (GitHub PRD 22.7).

A mixin of :class:`~quill.ui.github_workbench_window.GitHubWorkbenchProvider`,
on the Workbench's File menu:

- **Import Issues from a Spreadsheet...** (Ctrl+Alt+I): choose a CSV file or an
  Excel workbook; the preview starts with which column fills which field and
  which columns are left out, then a line per row, skipped rows with their
  reason; Create Issues sends them, and the details pane ends with a sentence a
  row (:mod:`quill.core.github.issue_import`, the shared reader in
  :mod:`quill.core.workbench.spreadsheet`).
- **New Issues from Lines...** (Ctrl+Alt+L): the editor's selection, in a box
  you can change first, one issue per line, list markers and check boxes taken
  off; optionally each a sub-issue of an issue you name.

Every issue made goes into Change History. Nothing is sent before the preview,
and Cancel there sends nothing.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from quill.core.github.permissions import WriteTier
from quill.ui.dialog_contract import show_modal_dialog

__all__ = ["GitHubWorkbenchImportMixin"]


class GitHubWorkbenchImportMixin:
    """File > Import Issues from a Spreadsheet, File > New Issues from Lines."""

    frame: Any
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _current_repository: Callable[[], str]
    _ask_text: Callable[..., str]
    github_api: Callable[[], Any]

    # -- Import Issues from a Spreadsheet ----------------------------------------

    def _do_import_issues(self, _ref: Any, _row: object) -> None:
        repository = self._current_repository()
        if not repository:
            self._say("Open a repository first. Ctrl+L opens one by name or link.")
            return
        from quill.core.workbench.spreadsheet import SPREADSHEET_WILDCARD, numbered_rows

        wx = self.frame._wx
        title = "Import Issues from a Spreadsheet"
        style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        with wx.FileDialog(
            self.frame.frame, title, wildcard=SPREADSHEET_WILDCARD, style=style
        ) as box:
            if show_modal_dialog(box, title) != wx.ID_OK:
                return
            path = Path(box.GetPath())
        try:
            numbered = numbered_rows(path)
        except (OSError, ValueError) as exc:
            self._say(f"Could not read {path.name}: {exc}")
            return
        if not numbered:
            self._say(f"{path.name} has no rows under its header.")
            return
        rows = [row for _n, row in numbered]
        api = self.github_api()

        def milestones() -> dict[str, int]:
            answer = api.rest(
                "GET", f"/repos/{repository}/milestones", query={"state": "all", "per_page": "100"}
            )
            data = answer.data if isinstance(answer.data, list) else []
            return {str(m.get("title")): int(m.get("number")) for m in data if m.get("number")}

        def preview(numbers: dict[str, int]) -> None:
            from quill.core.github.issue_import import import_mapping, import_plan, mapping_lines

            mapping, ignored = import_mapping(rows[0].keys())
            plan = import_plan(rows, milestones=numbers, numbers=[n for n, _r in numbered])
            ready = [row for row in plan if not row.problem]
            summary = (
                f"{len(ready)} issues will be made in {repository}; "
                f"{len(plan) - len(ready)} rows are skipped."
            )
            lines = [*mapping_lines(mapping, ignored), *(row.sentence for row in plan)]
            if not ready:
                self.frame.details.ChangeValue("\n".join([summary, "", *lines]))
                self._say(f"Nothing to import. {summary} The details say why.")
                return
            if not self._ask_issue_preview(title, summary, lines):
                return
            self._create_imported(repository, ready, numbers)

        self._background("read the milestones", milestones, preview)

    def _create_imported(self, repository: str, ready: Sequence[Any], numbers: Any) -> None:
        from quill.core.github.issue_import import issue_payload

        api = self.github_api()

        def send() -> list[tuple[str, int, str]]:
            results: list[tuple[str, int, str]] = []
            for row in ready:
                try:
                    answer = api.rest(
                        "POST", f"/repos/{repository}/issues", body=issue_payload(row, numbers)
                    )
                    number = int((answer.data or {}).get("number") or 0)
                    results.append((
                        f"Row {row.number}: made #{number}, {row.title}.",
                        number,
                        row.title,
                    ))
                except Exception as exc:  # noqa: BLE001 - one refusal must not stop the rest
                    results.append((f"Row {row.number}: GitHub refused it: {exc}", 0, row.title))
            return results

        self._background(
            "import the issues", send, lambda done: self._report_made(repository, done)
        )

    # -- New Issues from Lines ----------------------------------------------------

    def _do_issues_from_lines(self, _ref: Any, _row: object) -> None:
        repository = self._current_repository()
        if not repository:
            self._say("Open a repository first. Ctrl+L opens one by name or link.")
            return
        from quill.core.github.issue_import import titles_from_lines

        source = getattr(self, "_gist_source", None)
        start = ""
        if callable(source):
            try:
                start = str(source()[1] or "")
            except Exception:  # noqa: BLE001 - the editor's text is a convenience only
                start = ""
        title = "New Issues from Lines"
        text = self._ask_text(
            title, "One issue per line. Change the lines if you like:", multiline=True, value=start
        )
        titles = titles_from_lines(text)
        if not titles:
            return
        parent_text = self._ask_text(
            title, "Make them sub-issues of issue number (leave empty for none):"
        )
        parent = int(parent_text.lstrip("#")) if parent_text.lstrip("#").isdigit() else 0
        summary = f"{len(titles)} issues will be made in {repository}" + (
            f", each a sub-issue of #{parent}." if parent else "."
        )
        if not self._ask_issue_preview(
            title, summary, [f"Line {n}: {t}" for n, t in enumerate(titles, 1)]
        ):
            return
        api = self.github_api()

        def send() -> list[tuple[str, int, str]]:
            results: list[tuple[str, int, str]] = []
            for n, name in enumerate(titles, start=1):
                try:
                    answer = api.rest("POST", f"/repos/{repository}/issues", body={"title": name})
                    data = answer.data or {}
                    number = int(data.get("number") or 0)
                    said = f"Line {n}: made #{number}, {name}."
                    if parent:
                        try:
                            api.rest(
                                "POST",
                                f"/repos/{repository}/issues/{parent}/sub_issues",
                                body={"sub_issue_id": int(data.get("id") or 0)},
                            )
                            said = f"Line {n}: made #{number}, a sub-issue of #{parent}, {name}."
                        except Exception as exc:  # noqa: BLE001
                            said = f"Line {n}: made #{number}, {name}, but not a sub-issue: {exc}"
                    results.append((said, number, name))
                except Exception as exc:  # noqa: BLE001 - one refusal must not stop the rest
                    results.append((f"Line {n}: GitHub refused it: {exc}", 0, name))
            return results

        self._background("make the issues", send, lambda done: self._report_made(repository, done))

    # -- shared -------------------------------------------------------------------

    def _ask_issue_preview(self, title: str, summary: str, lines: Sequence[str]) -> bool:
        from quill.ui.wordpress_workbench_dialogs import ask_preview

        return ask_preview(
            self.frame.frame,
            show_modal_dialog,
            title=title,
            summary=summary,
            lines=lines,
            yes="Create Issues",
            destructive=False,
        )

    def _report_made(self, repository: str, results: Sequence[tuple[str, int, str]]) -> None:
        from quill.ui import wordpress_dialogs as dlg

        made = [r for r in results if r[1]]
        said = f"Made {len(made)} of {len(results)} issues in {repository}."
        self._record_made(repository, made)
        self.frame.reload()
        self._say(said)
        dlg.show_report(
            self.frame.frame,
            show_modal_dialog,
            title="Issues Made",
            text="\n".join([said, "", *(r[0] for r in results)]),
            help_text="A sentence for each row or line: the issue made, or why GitHub "
            "refused it. Change History has each issue made.",
        )

    def _record_made(self, repository: str, made: Sequence[tuple[str, int, str]]) -> None:
        try:
            log = self.change_log()  # type: ignore[attr-defined]
            account = self.account_name()  # type: ignore[attr-defined]
            for _said, number, name in made:
                log.record(
                    account=account,
                    kind="issue",
                    ident={"repository": repository, "number": str(number)},
                    target=f"{repository}#{number}",
                    summary=f"Made issue #{number}: {name}",
                    changes=[],
                    tier=int(WriteTier.VISIBLE),
                    confirmed=True,
                    can_undo=False,
                )
        except OSError:
            pass  # a history that cannot be written must not hide the results
