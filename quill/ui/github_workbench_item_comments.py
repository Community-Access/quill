"""An issue's or pull request's comments, under its description in the Workbench's details pane.

The list row carries only the comment count, so the thread is read off the UI
thread the first time a row with comments is selected, and kept for as long
as the row is unchanged (its address, last update and count). The pane shows
the description at once with a line saying the comments are being read, then
the whole thread when it arrives, if that row is still the selected one, with
the caret and any selection left where they were. Nothing is spoken unless
the pane has focus; then one line says the comments arrived, because a
changed read-only field is something the screen reader does not say.
Alt+N and Alt+P are not here; Read as Document (Ctrl+Shift+I) gives the
thread a heading per post for that.
"""

from __future__ import annotations

import re
from typing import Any

from quill.core.github.emoji_names import name_shortcodes
from quill.core.github.items_provider import GitHubItem
from quill.ui.github_items_view import item_detail

__all__ = ["READING", "detail_with_comments"]

READING = "Reading the comments..."

_REPO = re.compile(r"github\.com/([^/]+/[^/]+)/(?:issues|pull)/\d+")

_Key = tuple[str, str, int]


def _key(item: GitHubItem) -> _Key:
    return (item.url, item.updated_at, item.comments)


def _repo(item: GitHubItem) -> str:
    found = _REPO.search(item.url or "")
    return found.group(1) if found else ""


def detail_with_comments(provider: Any, item: GitHubItem) -> str:
    """The details text for *item*: its thread once read, and the read started if it is not."""
    threads: dict[_Key, list[dict[str, str]] | None] = provider.__dict__.setdefault(
        "_item_threads", {}
    )
    key, repo = _key(item), _repo(item)
    text = item_detail(item, [])[0]
    if item.comments <= 0 or not repo:
        return text
    if key in threads:
        thread = threads[key]
        return text + "\n" + READING if thread is None else item_detail(item, thread)[0]
    frame = getattr(provider, "frame", None)
    if frame is None:
        return text
    threads[key] = None  # reading: a second look starts no second read

    def still_selected() -> bool:
        row = frame.selected_row()
        return isinstance(row, GitHubItem) and _key(row) == key

    def show(words: str, said: str) -> None:
        details = frame.details
        wx = getattr(frame, "_wx", None)
        focused = wx is not None and wx.Window.FindFocus() is details
        start, end = details.GetSelection()
        details.ChangeValue(words)
        details.SetSelection(min(start, len(words)), min(end, len(words)))
        if focused:
            frame._say(said)

    def done(thread: Any) -> None:
        threads[key] = list(thread or [])
        if still_selected():
            count = len(threads[key])
            said = (
                "1 comment read; it follows the description."
                if count == 1
                else f"{count} comments read; they follow the description."
            )
            show(provider.detail(frame.selected_row()), said)

    def failed(error: BaseException) -> None:
        threads.pop(key, None)  # the next look tries again
        if still_selected():
            words = name_shortcodes(f"{text}\nCould not read the comments: {error}")
            show(words, "Could not read the comments.")

    frame._run_background(
        "Workbench read the comments",
        lambda: provider.items.fetch_issue_comments(repo, item.number),
        done,
        failed,
    )
    return text + "\n" + READING
