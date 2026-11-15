"""The GitHub Workbench's New Pull Request (Ctrl+N on Pull Requests).

Before it, Ctrl+N on Pull Requests ran ``github.workbench.new_pull`` and
nothing answered. Ported from GHManage (v1.0.0, "pull request from a
comparison"): the title and description start from the commits being
proposed, a branch that already has an open pull request into the same base
goes to that one instead, Draft is one check box, and Cancel keeps what was
typed (:mod:`quill.core.github.pull_compose`).

Every read and the one write run through the frame's background runner and
say one outcome (GATE-13).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.items_provider import GitHubBranch

__all__ = ["GitHubWorkbenchPullsMixin"]


class GitHubWorkbenchPullsMixin:
    """New Pull Request; the helpers are the action router's."""

    items: Any
    frame: Any
    _announce: Callable[[str], None]
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _current_repository: Callable[[], str]
    _go_filtered: Callable[[str, str, str, str], None]

    def _do_new_pull(self, _ref: Any, row: object) -> None:
        repository = self._current_repository()
        if not repository:
            self._say("Open a repository first. Ctrl+L opens one by name or link.")
            return
        chosen = row.name if isinstance(row, GitHubBranch) else ""
        items = self.items

        def read() -> dict[str, Any]:
            branches = items.fetch_branches(repository, limit=100)
            default = next((b.default_branch for b in branches if b.default_branch), "")
            names = [b.name for b in branches]
            head = chosen or next((n for n in names if n != default), "")
            messages: list[str] = []
            ahead: int | None = None
            if head and default and head != default:
                comparison = items.compare_branches(repository, default, head)
                ahead = comparison.ahead_by
                messages = [c.message for c in comparison.commits]
            return {
                "names": names,
                "default": default,
                "head": head,
                "messages": messages,
                "ahead": ahead,
                "templates": _pull_templates(items, repository),
            }

        self._background(
            "read the branches", read, lambda found: self._new_pull_form(repository, found)
        )

    def _new_pull_form(self, repository: str, found: dict[str, Any]) -> None:
        from quill.core.github.pull_compose import describe_refusal, prefill
        from quill.ui.github_new_pull_dialog import NewPullRequestDialog

        default, head = found["default"], found["head"]
        refusal = describe_refusal(default, head, ahead_by=found["ahead"]) if head else ""
        if refusal and head != default:
            self._say(refusal)
            return
        start = prefill(repository, default, head, found["messages"])
        start = self._with_pull_template(start, found.get("templates") or [])
        if start is None:
            return
        form = NewPullRequestDialog(
            self.frame.frame, start, found["names"], default_branch=default, announce=self._say
        )
        if not form.show() or form.draft is None:
            return
        self._send_pull(form.draft)

    def _with_pull_template(self, start: Any, templates: list[tuple[str, str]]) -> Any:
        """The repository's pull request template in the description (PRD 21.7):
        the one there is, or the one chosen when there are several. None cancels."""
        from dataclasses import replace

        if not templates:
            return start
        if len(templates) == 1:
            name, text = templates[0]
        else:
            labels = ["No template", *[name for name, _text in templates]]
            index = self._choose(  # type: ignore[attr-defined]
                "New Pull Request", "This repository has several pull request templates:", labels
            )
            if index < 0:
                return None
            if index == 0:
                return start
            name, text = templates[index - 1]
        body = text.rstrip() + ("\n\n" + start.body if start.body else "\n")
        return replace(start, body=body)

    def _send_pull(self, draft: Any) -> None:
        from quill.core.github.pull_compose import drop_draft, keep_draft, open_pull_item

        items = self.items

        def send() -> tuple[str, Any]:
            existing = open_pull_item(items, draft.repository, draft.base, draft.head)
            if existing is not None:
                return "existing", existing
            created = items.create_pull_request(
                draft.repository, draft.title, draft.body, draft.head, draft.base, draft=draft.draft
            )
            return "created", created

        def done(result: tuple[str, Any]) -> None:
            what, item = result
            if what == "existing":
                keep_draft(draft)
                self._say(
                    f"{draft.head} already has an open pull request into {draft.base}, "
                    f"#{item.number}. Showing it; your text is kept."
                )
            else:
                drop_draft(draft.repository, draft.base, draft.head)
                kind = "draft pull request" if draft.draft else "pull request"
                self._say(f"Opened {kind} #{item.number}, {item.title}.")
            self._go_filtered("repository", "pulls", draft.repository, f"number:{item.number}")

        def failed(error: BaseException) -> None:
            keep_draft(draft)
            self._say(f"Could not open the pull request; your text is kept. {error}")

        frame = self.frame
        frame._run_background("Workbench open the pull request", send, done, failed)


def _pull_templates(items: Any, repository: str) -> list[tuple[str, str]]:
    """The repository's pull request templates; none when they cannot be read."""
    from quill.core.github.template_catalog import pull_request_templates

    get = getattr(items, "template_repository", None)
    if not callable(get):
        return []
    try:
        return pull_request_templates(get(repository), repository)
    except Exception:  # noqa: BLE001 - a template is a convenience; the form still opens
        return []
