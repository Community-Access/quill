"""Optional grounded drafts with AI, from evidence you select (GX15).

* A pull request: **Draft Description with AI...** and **Draft Reviewer Brief
  with AI...**, from its changed files and their patches at the head commit.
* An issue: **Draft Task Breakdown with AI...**, from its title and text.
* Selected issues and pull requests: **Draft Release Notes with AI...**,
  from those rows only.

Each prompt is built by :mod:`quill.core.github.ai_context`: the evidence is
bounded, its sources (links, the head SHA) are named, and the model is told
the evidence is untrusted text and not to invent checks, tests or readiness.
The draft opens in the editor as a file of its own, headed as a draft with
its sources and any part that was left out; QUILL posts nothing. The AI is
the editor's own connection (Choose Your AI), asked for only when a draft is
run, through the same consent as Summarize Discussion. Without one, the rows
are greyed and say why, and every non-AI path (Draft Release Notes...,
Comment..., the pull request window) is unchanged.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.github.items_provider import GitHubItem

__all__ = ["DRAFT_REASONS", "DRAFT_VERBS", "GitHubWorkbenchDraftsMixin", "draft_header"]

_ITEM = frozenset({"item"})
DRAFT_VERBS: dict[str, frozenset[str]] = {
    "ai_pr_description": _ITEM,
    "ai_reviewer_brief": _ITEM,
    "ai_task_breakdown": _ITEM,
    "ai_release_notes": _ITEM,
}
_NO_AI = (
    "needs AI set up in the editor that opened this window (AI, Choose Your AI); "
    "without it the Workbench's own commands still do the job by hand."
)
DRAFT_REASONS: dict[str, str] = {
    "ai_pr_description": f"Draft Description with AI is for a pull request, and {_NO_AI}",
    "ai_reviewer_brief": f"Draft Reviewer Brief with AI is for a pull request, and {_NO_AI}",
    "ai_task_breakdown": f"Draft Task Breakdown with AI is for an issue, and {_NO_AI}",
    "ai_release_notes": (
        f"Draft Release Notes with AI is for selected issues and pull requests, and {_NO_AI}"
    ),
}
_TASK_WORDS = {
    "pr_description": "description",
    "reviewer_brief": "reviewer brief",
    "issue_decomposition": "task breakdown",
    "release_notes": "release notes",
}


def draft_header(what: str) -> str:
    """The first lines of every draft: what it is, and that nothing was posted."""
    return (
        f"Draft {what}, written by AI from the evidence you selected. QUILL has posted "
        "nothing. Check every claim against its source before you use it.\n\n"
    )


class GitHubWorkbenchDraftsMixin:
    items: Any
    frame: Any
    signed_in: bool
    #: Set by the editor that opened the window; returns ``draft(prompt) -> str`` or None.
    ai_drafter: Callable[[], Callable[[str], str] | None] | None = None
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _show_text: Callable[[str, str], None]
    _open_document: Callable[[Path], None] | None

    def _drafts_ready(self) -> bool:
        return self.ai_drafter is not None

    def _fits_ai_pr_description(self, row: object) -> bool:
        return self._drafts_ready() and isinstance(row, GitHubItem) and row.is_pr

    _fits_ai_reviewer_brief = _fits_ai_pr_description

    def _fits_ai_task_breakdown(self, row: object) -> bool:
        return self._drafts_ready() and isinstance(row, GitHubItem) and not row.is_pr

    def _selected_items(self) -> list[GitHubItem]:
        frame = self.frame
        rows = list(getattr(frame, "rows", ()) or ())
        pick = getattr(frame, "selected_indices", None)
        indices = list(pick()) if callable(pick) else []
        return [rows[i] for i in indices if 0 <= i < len(rows) and isinstance(rows[i], GitHubItem)]

    def _fits_ai_release_notes(self, row: object) -> bool:
        return self._drafts_ready() and isinstance(row, GitHubItem)

    def _do_ai_pr_description(self, ref: Any, row: object) -> None:
        self._pull_draft(str(ref.instance), row, "pr_description")

    def _do_ai_reviewer_brief(self, ref: Any, row: object) -> None:
        self._pull_draft(str(ref.instance), row, "reviewer_brief")

    def _pull_draft(self, repository: str, row: object, task: Any) -> None:
        from quill.core.github.ai_context import build_pull_request_draft_request

        assert isinstance(row, GitHubItem)
        number, items = row.number, self.items

        def request() -> Any:
            diff = items.fetch_pull_diff(repository, number)
            return build_pull_request_draft_request(repository, diff, diff.files, task=task)

        self._draft(f"{repository}-{number}", request)

    def _do_ai_task_breakdown(self, ref: Any, row: object) -> None:
        from quill.core.github.ai_context import build_issue_decomposition_request

        assert isinstance(row, GitHubItem)
        repository = str(ref.instance)
        self._draft(
            f"{repository}-{row.number}",
            lambda: build_issue_decomposition_request(repository, row),
        )

    def _do_ai_release_notes(self, ref: Any, row: object) -> None:
        from quill.core.github.ai_context import GitHubAIEvidenceItem, build_release_notes_request

        chosen = self._selected_items() or ([row] if isinstance(row, GitHubItem) else [])
        repository = str(ref.instance)
        evidence = [
            GitHubAIEvidenceItem(
                "Pull request" if item.is_pr else "Issue",
                f"#{item.number} {item.title}",
                item.body or "No text was reported.",
                item.url,
            )
            for item in chosen
        ]
        self._draft(repository, lambda: build_release_notes_request(repository, evidence))

    def _draft(self, name: str, build: Callable[[], Any]) -> None:
        """Ask for the AI on the UI thread, then build, send and open the draft off it."""
        acquire = self.ai_drafter
        draft = acquire() if acquire is not None else None
        if draft is None:
            self._say("AI is not set up, so there is no draft.")
            return

        def work() -> tuple[Any, str]:
            from quill.core.github.ai_context import format_grounded_draft

            request = build()
            return request, format_grounded_draft(draft(request.prompt), request)

        self._background("write the draft", work, lambda done: self._open_draft(name, *done))

    def _open_draft(self, name: str, request: Any, text: str) -> None:
        what = _TASK_WORDS.get(str(request.task), "draft")
        body = draft_header(what) + text + "\n"
        omitted = " Some evidence was left out; the draft says so." if request.omitted else ""
        path = _draft_path(name, str(request.task))
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
        except OSError:
            self._show_text(f"Draft {what}", body)
            self._say(f"The {what} draft is ready.{omitted}")
            return
        self._say(f"The {what} draft is ready, in {path.name}.{omitted}")
        if self._open_document is not None:
            self._open_document(path)
        else:
            self._show_text(f"Draft {what}", body)


def _draft_path(name: str, task: str) -> Path:
    from quill.core.paths import app_data_dir

    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", f"{name}-{task}").strip("-")
    return app_data_dir() / "GitHub Drafts" / f"{safe}.md"
