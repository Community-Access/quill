"""Read as Document and the GitHub API Console in the GitHub Workbench (PRD 22.2, 22.3).

**Read as Document** (Ctrl+Shift+I, and the context menu of an issue, pull
request or discussion) reads the whole thread fresh and gives it as one
document (:mod:`quill.core.github.thread_document`): a heading for every post
with its author and date, bodies as GitHub wrote them, links kept. It opens
in the editor that opened the Workbench (a Markdown file in QUILL's GitHub
Documents folder) or is saved where you choose as Markdown or HTML.

**GitHub API Console** (Tools, Ctrl+Shift+J) is :mod:`quill.ui.github_api_console`.

Both read through the Workbench's one door (``github_api()``); only the
console can write, after Full access and a typed confirmation.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.github.explore_models import ExploreRow
from quill.core.github.items_provider import GitHubItem

__all__ = [
    "READING_REASONS",
    "READING_VERBS",
    "GitHubWorkbenchReadingMixin",
    "documents_folder",
    "thread_target",
]

READING_VERBS: dict[str, frozenset[str]] = {
    "read_as_document": frozenset({"item", "issue", "pr", "discussion"}),
    "api_console": frozenset({"view"}),
}

READING_REASONS: dict[str, str] = {
    "read_as_document": "Select an issue, pull request or discussion first.",
}

_NUMBER = re.compile(r"/(?:issues|pull|discussions)/(\d+)")


def documents_folder() -> Path:
    """Where Open in Editor keeps the documents it writes."""
    from quill.core.paths import app_data_dir

    return app_data_dir() / "github_documents"


def thread_target(row: object, repository: str) -> tuple[str, int, str] | None:
    """(repository, number, kind) for a row that is a thread, else None."""
    if isinstance(row, GitHubItem):
        return repository, row.number, "pull_request" if row.is_pr else "issue"
    if not isinstance(row, ExploreRow) or row.kind not in ("issue", "pr", "discussion"):
        return None
    kind = {"pr": "pull_request"}.get(row.kind, row.kind)
    number = int(row.key) if row.key.isdigit() else 0
    if not number:
        found = _NUMBER.search(row.url or "")
        number = int(found.group(1)) if found else 0
    repo = row.repo or repository
    if not number or "/" not in repo:
        return None
    return repo, number, kind


class GitHubWorkbenchReadingMixin:
    """The two commands, on the GitHub provider."""

    items: Any
    frame: Any
    _open_document: Callable[[Path], None] | None = None
    _say: Callable[[str], None]
    _choose: Callable[[str, str, list[str]], int]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    github_api: Callable[[], Any]
    _current_repository: Callable[[], str]
    current_repository_name: Callable[[], str]

    def _fits_read_as_document(self, row: object) -> bool:
        return thread_target(row, "owner/name") is not None

    def _do_read_as_document(self, ref: Any, row: object) -> None:
        repository = str(getattr(ref, "instance", "") or "") or self.current_repository_name()
        target = thread_target(row, repository)
        if target is None:
            self._say(READING_REASONS["read_as_document"])
            return
        choices = ["Save as Markdown...", "Save as HTML..."]
        if self._open_document is not None:
            choices.insert(0, "Open in Editor")
        index = self._choose("Read as Document", "The whole thread, as one document:", choices)
        if index < 0:
            return
        how = choices[index]
        api = self.github_api()
        repo, number, kind = target

        def work() -> Any:
            from quill.core.github.thread_document import fetch_thread

            return fetch_thread(api, repo, number, kind)

        self._background(f"read #{number} as a document", work, lambda doc: self._deliver(doc, how))

    def _deliver(self, doc: Any, how: str) -> None:
        from quill.core.github.thread_document import (
            suggested_name,
            thread_html,
            thread_markdown,
        )

        posts = f"{len(doc.entries)} posts"
        if how == "Open in Editor" and self._open_document is not None:
            folder = documents_folder()
            target = folder / suggested_name(doc)
            try:
                folder.mkdir(parents=True, exist_ok=True)
                target.write_text(thread_markdown(doc), encoding="utf-8", newline="\n")
            except OSError as exc:
                self._say(f"Could not write the document: {exc}")
                return
            self._open_document(target)
            self._say(f"Opened #{doc.number} in the editor, {posts}.")
            return
        html = how.startswith("Save as HTML")
        extension = ".html" if html else ".md"
        path = self._save_path(suggested_name(doc, extension), html)
        if path is None:
            return
        text = thread_html(doc) if html else thread_markdown(doc)
        try:
            path.write_text(text, encoding="utf-8", newline="\n")
        except OSError as exc:
            self._say(f"Could not save {path.name}: {exc}")
            return
        self._say(f"Saved {path.name}, {posts}.")

    def _save_path(self, name: str, html: bool) -> Path | None:
        from quill.ui.dialog_contract import show_modal_dialog

        wx = self.frame._wx
        wildcard = "HTML files (*.html)|*.html" if html else "Markdown files (*.md)|*.md"
        with wx.FileDialog(
            self.frame.frame,
            "Save Thread As",
            defaultFile=name,
            wildcard=wildcard,
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as chooser:
            if show_modal_dialog(chooser, "Save Thread As") != wx.ID_OK:
                return None
            return Path(chooser.GetPath())

    def _do_api_console(self, _ref: Any, _row: object) -> None:
        from quill.ui.github_api_console import GitHubApiConsole

        GitHubApiConsole(self, self._current_repository() or self.current_repository_name()).show()
