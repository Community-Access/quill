"""Reply, Add a Comment and Delete My Comment, in the YouTube Comments window.

The Comments window (:mod:`quill.ui.radio.youtube_comments_window`) reads
comments through yt-dlp, with no account. These three buttons act through the
official YouTube Data API instead, as the listener's own connected account:

* **Reply...** (Alt+R) answers the selected comment. YouTube threads one level
  deep, so a reply to a reply joins that thread, and says whom it answers.
* **Add a Comment...** (Alt+A) posts a new comment on the video.
* **Delete My Comment** (Alt+D) removes the selected comment once YouTube
  confirms it is yours; anybody else's is refused with a sentence.

They appear only when ``future.youtube_oauth`` is enabled (locked off in a
public build until Google approves the sign-in) and this copy has a client;
the first use asks for the extra permission in plain words
(:mod:`quill.ui.radio.youtube_account_ui`). Each says its outcome once, and a
posted comment or reply is added to the list where it belongs.
"""

from __future__ import annotations

from typing import Any


class _Host:
    """What :func:`run_write` needs, from the window and the app behind it."""

    def __init__(self, window: Any) -> None:
        self._window = window
        self._announce = window._announce
        self._task_manager = window._task_manager

    @property
    def _app(self) -> Any:
        return getattr(self._window, "account_app", None)

    @property
    def _wx(self) -> Any:
        return self._window._wx


def offered(window: Any) -> bool:
    """Whether this copy of Quill Radio can sign in to YouTube at all.

    The ``future.youtube_oauth`` feature must be enabled for the app behind
    *window*, not merely a client baked into the build: a release build with
    a client but without Google's approval keeps these buttons out of sight.
    """
    import os

    from quill.ui.radio.youtube_account_ui import can_sign_in

    return os.environ.get("QUILL_SAFE_MODE") != "1" and can_sign_in(_Host(window))


def attach(window: Any, panel: Any, buttons: Any) -> None:
    """Add the three buttons to *buttons* when :func:`offered`."""
    if not offered(window):
        window._account_buttons = ()
        return
    wx = window._wx
    reply_button = wx.Button(panel, label="&Reply...")
    reply_button.SetHelpText(
        "Writes a reply to the selected comment and posts it as your YouTube "
        "account. Needs Connect YouTube Account; the first time, Quill Radio "
        "asks for Google's permission to post for you."
    )
    add_button = wx.Button(panel, label="&Add a Comment...")
    add_button.SetHelpText(
        "Writes a new comment on this video and posts it as your YouTube account."
    )
    delete_button = wx.Button(panel, label="&Delete My Comment")
    delete_button.SetHelpText(
        "Deletes the selected comment if it is yours. Quill Radio checks with "
        "YouTube first and asks before deleting; nobody else's comment can be "
        "deleted."
    )
    for button in (reply_button, add_button, delete_button):
        buttons.Add(button, 0, wx.RIGHT, 6)
    reply_button.Bind(wx.EVT_BUTTON, lambda _e: reply_to_selected(window))
    add_button.Bind(wx.EVT_BUTTON, lambda _e: add_comment(window))
    delete_button.Bind(wx.EVT_BUTTON, lambda _e: delete_selected(window))
    window._account_buttons = (reply_button, add_button, delete_button)


def _video_id(window: Any) -> str:
    from quill.core.radio.youtube_urls import youtube_video_id

    return youtube_video_id(window._page_url) or ""


def _insert(window: Any, comment: Any, after: Any = None) -> None:
    """Put a posted comment into the window's list without a refetch."""
    comments = list(window._comments)
    if after is None:
        comments.insert(0, comment)
    else:
        index = next((i for i, c in enumerate(comments) if c.comment_id == after.comment_id), -1)
        # After the parent's existing replies, so the thread stays in order.
        index += 1
        while 0 < index < len(comments) and comments[index].parent_id == comment.parent_id:
            index += 1
        comments.insert(max(0, index), comment)
    window._comments = comments
    window.apply_filter(speak=False)


def reply_to_selected(window: Any) -> None:
    from quill.core.radio import youtube_account_api as api
    from quill.core.radio import youtube_comments as yc
    from quill.ui.radio.youtube_account_ui import ask_text, run_write

    chosen = window._selected()
    if chosen is None:
        window._announce("Select a comment first.")
        return
    host = _Host(window)
    text = ask_text(host, "Reply on YouTube", f"Your reply to {chosen.author}:", multiline=True)
    if not text:
        return
    thread = api.thread_of(chosen.comment_id)
    parent = next((c for c in window._comments if c.comment_id == thread), chosen)

    def _done(result: object) -> None:
        new_id = getattr(result, "comment_id", "") or f"{thread}.posted"
        _insert(
            window,
            yc.Comment(new_id, "You", text, parent_id=thread, reply_to=parent.author),
            after=parent,
        )
        window._announce("Reply posted.")

    run_write(
        host, "Reply on YouTube", lambda token: api.reply(token, chosen.comment_id, text), _done
    )


def add_comment(window: Any) -> None:
    from quill.core.radio import youtube_account_api as api
    from quill.core.radio import youtube_comments as yc
    from quill.ui.radio.youtube_account_ui import ask_text, run_write

    video_id = _video_id(window)
    if not video_id:
        window._announce("This is not a YouTube video, so it cannot be commented on.")
        return
    host = _Host(window)
    text = ask_text(host, "Add a Comment on YouTube", "Your comment:", multiline=True)
    if not text:
        return

    def _done(result: object) -> None:
        new_id = getattr(result, "comment_id", "") or "posted"
        _insert(window, yc.Comment(new_id, "You", text))
        window._announce("Comment posted.")

    run_write(
        host,
        "Comment on YouTube",
        lambda token: api.add_comment(token, video_id, text),
        _done,
    )


def delete_selected(window: Any) -> None:
    from quill.core.radio import youtube_account_api as api
    from quill.core.radio.youtube_oauth import YouTubeOAuthError
    from quill.ui.radio.youtube_account_ui import confirm, run_write

    chosen = window._selected()
    if chosen is None:
        window._announce("Select a comment first.")
        return
    host = _Host(window)
    if not confirm(
        host, "Delete My Comment", f'Delete your comment "{chosen.text[:80]}" from YouTube?'
    ):
        return

    def _work(token: str) -> object:
        if not api.is_mine(token, chosen.comment_id):
            raise YouTubeOAuthError("That comment is not yours, so it cannot be deleted.")
        api.delete_comment(token, chosen.comment_id)
        return chosen.comment_id

    def _done(_result: object) -> None:
        gone = {chosen.comment_id}
        window._comments = [
            c
            for c in window._comments
            if c.comment_id not in gone and not (c.parent_id in gone and not chosen.parent_id)
        ]
        window.apply_filter(speak=False)
        window._announce("Comment deleted.")

    run_write(host, "Delete a comment on YouTube", _work, _done)


__all__ = ["add_comment", "attach", "delete_selected", "offered", "reply_to_selected"]
