"""The GitHub Workbench's writes: comments, state, runs, notifications and local lists.

Split out of :mod:`quill.ui.github_workbench_actions` (GATE-11), which routes
every command and calls these when the Workbench does the job itself. Each
write uses a call GitHub Items or Explore GitHub already makes, so there is no
new network call; each runs off the UI thread through the frame's runner and
says one result (GATE-13), which F9 repeats and Shift+F9 explains. A write
that changes something on GitHub asks first when it cannot be undone from the
same row.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.explore_models import ExploreRow
from quill.core.github.items_provider import GitHubItem, GitHubWorkflowRun
from quill.core.workbench.filters import render
from quill.ui.dialog_contract import show_modal_dialog

__all__ = ["GitHubWorkbenchWritesMixin", "number_of"]


def number_of(url: str) -> int:
    """The issue or pull request number at the end of a GitHub address (0 when none)."""
    tail = url.rstrip("/").rsplit("/", 1)[-1]
    return int(tail) if tail.isdigit() else 0


class GitHubWorkbenchWritesMixin:
    """The writes; helpers (``_ask_text``, ``_confirm``, ``_background``) are the router's."""

    items: Any
    frame: Any
    _say: Callable[[str], None]
    _ask_text: Callable[..., str]
    _confirm: Callable[[str, str], bool]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _current_repository: Callable[[], str]
    _row_url: Callable[[object], str]
    _explore_client: Callable[[], Any]

    # -- writes ----------------------------------------------------------------

    def _item_target(self, ref: Any, row: object) -> tuple[str, int]:
        if isinstance(row, GitHubItem):
            return ref.instance, row.number
        if isinstance(row, ExploreRow):
            return row.repo, number_of(row.url)
        return "", 0

    def _do_comment(self, ref: Any, row: object) -> None:
        repository, number = self._item_target(ref, row)
        if not repository or not number:
            self._say("Select an issue or a pull request first.")
            return
        body = self._ask_text("Comment", f"Comment on #{number}:", multiline=True)
        if not body:
            return
        self._background(
            "post the comment",
            lambda: self.items.create_comment(repository, number, body),
            lambda _result: self._say(f"Comment posted on #{number}."),
        )

    def _do_close_reopen(self, ref: Any, row: object) -> None:
        assert isinstance(row, GitHubItem)
        closing = row.state == "open"
        verb = "Close" if closing else "Reopen"
        if not self._confirm(f"{verb} #{row.number}", f"{verb} #{row.number}, {row.title}?"):
            return
        state = "closed" if closing else "open"
        self._background(
            f"{verb.lower()} #{row.number}",
            lambda: self.items.update_items(ref.instance, [row.number], state=state),
            lambda _result: (self._say(f"{verb}d #{row.number}."), self.frame.reload()),
        )

    def _do_rerun(self, ref: Any, row: object) -> None:
        assert isinstance(row, GitHubWorkflowRun)
        if not self._confirm("Re-run Workflow", f"Run {row.name} again from the start?"):
            return
        self._background(
            "re-run the workflow",
            lambda: self.items.rerun_workflow_run(ref.instance, row.id),
            lambda _result: self._say(f"Re-running {row.name}."),
        )

    def _notification_call(self, row: object, call: str, said: str) -> None:
        assert isinstance(row, ExploreRow)
        client = self._explore_client()
        self._background(
            said.lower(),
            lambda: getattr(client, call)(row.key),
            lambda _result: (self._say(said + "."), self.frame.reload()),
        )

    def _do_mark_read(self, _ref: Any, row: object) -> None:
        self._notification_call(row, "mark_notification_seen", "Marked read")

    def _do_mark_done(self, _ref: Any, row: object) -> None:
        self._notification_call(row, "mark_notification_done", "Marked done")

    def _do_unsubscribe(self, _ref: Any, row: object) -> None:
        self._notification_call(row, "unsubscribe_notification", "Unsubscribed")

    def _do_mark_all_read(self, _ref: Any, _row: object) -> None:
        notes = [
            r for r in self.frame.rows if isinstance(r, ExploreRow) and r.kind == "notification"
        ]
        if not notes:
            self._say("No notifications in this view.")
            return
        if len(notes) > 20 and not self._confirm(
            "Mark All Read", f"Mark all {len(notes)} notifications in this view read?"
        ):
            return
        client = self._explore_client()

        def work() -> int:
            for note in notes:
                client.mark_notification_seen(note.key)
            return len(notes)

        self._background(
            "mark them read",
            work,
            lambda count: (self._say(f"Marked {count} read."), self.frame.reload()),
        )

    def _do_star(self, _ref: Any, row: object) -> None:
        repository = row.repo if isinstance(row, ExploreRow) and row.kind == "repo" else ""
        repository = repository or self._current_repository()
        wx = self.frame._wx
        with wx.MessageDialog(
            self.frame.frame,
            f"Star or unstar {repository}?",
            "Star or Unstar",
            wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION,
        ) as dialog:
            dialog.SetYesNoLabels("&Star", "&Unstar")
            answer = show_modal_dialog(dialog, "Star or Unstar")
        if answer not in (wx.ID_YES, wx.ID_NO):
            return
        starred = answer == wx.ID_YES
        client = self._explore_client()
        self._background(
            "change the star",
            lambda: client.set_starred(repository, starred),
            lambda _result: self._say(f"{'Starred' if starred else 'Unstarred'} {repository}."),
        )

    # -- local stores -----------------------------------------------------------

    def _saved(self) -> Any:
        from quill.ui.github_workbench_loaders import saved_items_for

        return saved_items_for(self.items)

    def _do_favorite(self, ref: Any, row: object) -> None:
        from quill.core.github.saved_items import FavoriteItem

        url = self._row_url(row)
        if not url:
            self._say("Nothing to keep here.")
            return
        saved = self._saved()
        existing = next((f for f in saved.favorites if f.url == url), None)
        if existing is not None:
            saved.remove_favorite(existing.key)
            saved.save()
            self._say("Removed from Favorites.")
            return
        repository = getattr(row, "repo", "") or ref.instance
        title = str(getattr(row, "title", "") or getattr(row, "label", "") or url)
        kind = "pr" if getattr(row, "is_pr", False) or "/pull/" in url else "issue"
        saved.add_favorite(FavoriteItem(repository, kind, url, title))
        saved.save()
        self._say("Added to Favorites.")

    def _do_pin_repository(self, _ref: Any, row: object) -> None:
        repository = row.repo if isinstance(row, ExploreRow) and row.kind == "repo" else ""
        repository = repository or self._current_repository()
        saved = self._saved()
        if saved.is_pinned(repository):
            saved.unpin_repo(repository)
            said = f"Unpinned {repository}."
        else:
            saved.pin_repo(repository)
            said = f"Pinned {repository}."
        saved.save()
        self._say(said)

    def _can_save_search(self) -> bool:
        current = self.frame.current if self.frame is not None else None
        return current is not None and current.key in ("saved_searches", "search_issues")

    def _do_save_search(self, _ref: Any, _row: object) -> None:
        text = render(self.frame.query) if not self.frame.query.is_empty else ""
        text = text or self._ask_text(
            "Save a Search", "Search to keep, such as is:open author:@me:"
        )
        if not text:
            return
        saved = self._saved()
        saved.save_search(text)
        saved.save()
        self._say(f"Saved the search {text}.")

    def _do_remove_search(self, _ref: Any, row: object) -> None:
        assert isinstance(row, ExploreRow)
        saved = self._saved()
        saved.remove_search(row.key)
        saved.save()
        self._say("Saved search removed.")
        self.frame.reload()
