"""Consent-gated AI summaries for GitHub issues and pull requests."""

from __future__ import annotations

import threading

from quill.core.github.items_provider import GitHubItem, GitHubItemsError


class GitHubItemsAiMixin:
    """Summarize a selected discussion using the user's configured AI route."""

    def _on_summarize(self) -> None:
        index = self._list.GetFirstSelected()
        model = self._rows[index] if 0 <= index < len(self._rows) else None
        if not isinstance(model, GitHubItem):
            self._announce("Select an issue or pull request to summarize.")
            return
        if self._ai_acquire is None:
            self._announce("AI summaries are unavailable here.")
            return
        summarize = self._ai_acquire()
        if summarize is None:
            self._announce("AI is not configured; summary cancelled.")
            return
        self._set_status(f"Summarizing #{model.number} with AI...")

        def worker() -> None:
            wx = self._wx
            from quill.core.github.thread_summary import compose_thread_text

            try:
                comments = self._provider.fetch_issue_comments(self._repo, model.number)
            except GitHubItemsError:
                comments = list(self._comments)
            thread_text = compose_thread_text(model.title, model.author, model.body, comments)
            truncated = "[... middle of the thread truncated ...]" in thread_text
            try:
                summary = summarize(thread_text)
            except Exception as exc:  # noqa: BLE001 - surface, never crash
                wx.CallAfter(self._set_status, f"Summary failed: {exc}")
                return
            wx.CallAfter(self._on_summary_ready, model.number, summary, model.url, truncated)

        threading.Thread(target=worker, daemon=True).start()  # GATE-40-OK: explicit AI request.

    def _on_summary_ready(
        self, number: int, summary: str, source_url: str = "", truncated: bool = False
    ) -> None:
        existing = self._details.GetValue()
        source = source_url or f"GitHub item #{number}"
        evidence = f"Source: {source}"
        if truncated:
            evidence += (
                "\nContext note: the middle of the discussion was omitted to fit "
                "the AI input limit."
            )
        self._details.SetValue(
            f"AI SUMMARY of #{number}:\n{summary}\n\n{evidence}\n\n{'-' * 40}\n{existing}"
        )
        self._details.SetFocus()
        self._details.SetInsertionPoint(0)
        self._announce(f"Summary ready for #{number}. {summary}")


__all__ = ["GitHubItemsAiMixin"]
