"""GitHub from the editor, in both editors (GitHub PRD 22.3, GH-R-084).

The commands of :mod:`quill.core.github.editor_line`, wired to a window. QUILL
reaches them through ``quill/ui/main_frame_github_line.py`` and QUILL Lite
through ``quill/apps/lite_github_line.py``; each builds a :class:`LineHost`
from its own vocabulary, the way Clone Repository's ``CloneHost`` works, so
the commands, their sentences and their refusals exist once.

They open no window unless they must: Copy GitHub Link to This Line, Who
Changed This Line? and Open This Line on GitHub only speak (or open the
browser); Open the Pull Request for This Line and the reference at the cursor
open the Workbench's own view; New Issue from Selection... opens the
Workbench's issue window with the draft filled in and its preview before
anything is sent; Issues Mentioning This File opens the Workbench's search;
Comment on This Line in the Open Pull Request... asks for the comment.

Reading the working copy runs git in the background through
``safe_subprocess``; asking GitHub uses the editor's signed-in account. Both
are refused in Safe Mode, like every other git and GitHub command.
"""

from __future__ import annotations

import json
import time
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from quill.core.github import editor_line as el

__all__ = [
    "SECOND_PRESS_SECONDS",
    "LineHost",
    "comment_on_line",
    "copy_line_link",
    "issue_from_selection",
    "issues_mentioning_file",
    "open_line",
    "open_line_pull",
    "open_reference_at_cursor",
    "who_changed_line",
]

#: How soon a second Who Changed This Line? on the same line opens its pull request.
SECOND_PRESS_SECONDS = 10.0
SAFE_MODE = "GitHub and git commands are off in Safe Mode."
NO_GIT = (
    "This needs git. Install it from Help > Download Optional Components, "
    "or install git yourself and make sure it is on your PATH."
)


@dataclass
class LineHost:
    """What the commands need from the editor window, in its own terms.

    *span* gives the first and last line of the selection (1-based; the
    caret's line when nothing is selected) and the selected text.
    *text_and_offset* gives the document's text and the caret's offset in it.
    *provider* runs the editor's GitHub gates (Safe Mode, consent, sign-in)
    and returns the items provider, or ``None`` after saying why not; it is
    given the command to run again once the person has signed in.
    *open_workbench* opens the Workbench at a repository and then runs a
    request (``search:<query>`` or ``issue:<json>``); *open_reference* opens a
    parsed GitHub reference in the Workbench and then runs a request
    (``filter:#42`` narrows the list to that item).
    """

    parent: Any
    announce: Callable[[str], None]
    run_background: Callable[
        [str, Callable[[], Any], Callable[[Any], None], Callable[[BaseException], None]],
        None,
    ]
    copy_text: Callable[[str], bool]
    file_path: Callable[[], str]
    span: Callable[[], tuple[int, int, str]]
    text_and_offset: Callable[[], tuple[str, int]]
    provider: Callable[[Callable[[], None]], Any]
    open_workbench: Callable[[str, str], None]
    open_reference: Callable[[Any, str], None]
    show_modal: Callable[[Any, str], int]
    safe_mode: bool = False


#: The last Who Changed This Line? answer: (file, line, commit, when).
_LAST_BLAME: dict[str, tuple[str, int, str, float]] = {}


def _runner() -> Any:
    from quill.stability.safe_subprocess import run_subprocess_safely

    return run_subprocess_safely


def _git_ready(host: LineHost) -> bool:
    if host.safe_mode:
        host.announce(SAFE_MODE)
        return False
    from quill.core.git_binaries import git_available

    if not git_available():
        host.announce(NO_GIT)
        return False
    return True


def _failed(host: LineHost, action: str) -> Callable[[BaseException], None]:
    def say(error: BaseException) -> None:
        if isinstance(error, el.EditorLineError):
            host.announce(str(error))
        else:
            host.announce(f"Could not {action}: {error}")

    return say


def _with_site(
    host: LineHost,
    action: str,
    then: Callable[[el.LineSite], None],
    *,
    extra: Callable[[el.LineSite], Any] | None = None,
    then_extra: Callable[[el.LineSite, Any], None] | None = None,
) -> None:
    """Find the lines on GitHub in the background, then run *then* on the UI thread."""
    if not _git_ready(host):
        return
    path = host.file_path()
    first, last, _selection = host.span()
    runner = _runner()

    def work() -> Any:
        site = el.locate(path, first, last, runner=runner)
        return site, (extra(site) if extra is not None else None)

    def done(result: Any) -> None:
        site, more = result
        if then_extra is not None:
            then_extra(site, more)
        else:
            then(site)

    host.run_background(action, work, done, _failed(host, action))


def _say_with_caveat(host: LineHost, sentence: str, site: el.LineSite) -> None:
    note = el.caveat(site)
    host.announce(f"{sentence} {note}" if note else sentence)


# ---------------------------------------------------------------------------
# Copy GitHub Link to This Line, Open This Line on GitHub
# ---------------------------------------------------------------------------


def copy_line_link(host: LineHost) -> None:
    def done(site: el.LineSite) -> None:
        if host.copy_text(el.permalink(site)):
            _say_with_caveat(host, f"Copied the link to {site.lines}.", site)
        else:
            host.announce("Could not put the link on the clipboard. Try again.")

    _with_site(host, "find this line on GitHub", done)


def open_line(host: LineHost) -> None:
    def done(site: el.LineSite) -> None:
        if webbrowser.open(el.permalink(site), new=2):
            _say_with_caveat(host, f"Opened {site.lines} on GitHub in your browser.", site)
        else:
            host.announce("Could not open your browser.")

    _with_site(host, "find this line on GitHub", done)


# ---------------------------------------------------------------------------
# Who Changed This Line?, Open the Pull Request for This Line
# ---------------------------------------------------------------------------


def who_changed_line(host: LineHost) -> None:
    """Say who last changed the line; a second press soon after opens its pull request."""
    path = host.file_path()
    first, _last, _selection = host.span()
    previous = _LAST_BLAME.get("last")
    if (
        previous is not None
        and previous[:2] == (path, first)
        and time.monotonic() - previous[3] <= SECOND_PRESS_SECONDS
    ):
        _LAST_BLAME.pop("last", None)
        open_line_pull(host)
        return
    from quill.core.local_git import blame_line

    def blame(site: el.LineSite) -> Any:
        return blame_line(site.root, site.path, site.first, runner=_runner())

    def done(site: el.LineSite, info: Any) -> None:
        _LAST_BLAME["last"] = (path, first, info.commit_sha, time.monotonic())
        host.announce(el.blame_sentence(info))

    _with_site(host, "read who changed this line", lambda _s: None, extra=blame, then_extra=done)


def open_line_pull(host: LineHost) -> None:
    """Open the pull request that brought the line's last change."""
    provider = host.provider(lambda: open_line_pull(host))
    if provider is None:
        return
    from quill.core.github.references import parse_github_reference
    from quill.core.github.rest_transport import request_json
    from quill.core.local_git import blame_line

    token = getattr(provider, "token", None)

    def find(site: el.LineSite) -> Any:
        info = blame_line(site.root, site.path, site.first, runner=_runner())
        if set(info.commit_sha) == {"0"}:
            return None, info
        answer = request_json(token, "GET", el.commit_pulls_path(site.repository, info.commit_sha))
        return el.first_pull(answer.data), info

    def done(site: el.LineSite, found: Any) -> None:
        pull, info = found
        if pull is None:
            if set(info.commit_sha) == {"0"}:
                host.announce(el.blame_sentence(info))
            else:
                host.announce(
                    f"No pull request brought this line: commit {info.commit_sha[:7]} "
                    "went straight to its branch."
                )
            return
        number, url = pull
        host.open_reference(parse_github_reference(url), f"filter:#{number}")

    _with_site(
        host,
        "find the pull request for this line",
        lambda _s: None,
        extra=find,
        then_extra=done,
    )


# ---------------------------------------------------------------------------
# New Issue from Selection..., Issues Mentioning This File
# ---------------------------------------------------------------------------


def issue_from_selection(host: LineHost) -> None:
    _first, _last, selection = host.span()
    if not selection.strip():
        host.announce("Select the text the issue is about first.")
        return

    def done(site: el.LineSite) -> None:
        title, body = el.issue_draft(site, selection)
        note = el.caveat(site)
        if note:
            body = f"{body}\n_{note}_\n"
        host.open_workbench(site.repository, "issue:" + json.dumps([title, body]))

    _with_site(host, "find this file on GitHub", done)


def issues_mentioning_file(host: LineHost) -> None:
    def done(site: el.LineSite) -> None:
        host.open_workbench(site.repository, "search:" + el.issues_mentioning_query(site))

    _with_site(host, "find this file on GitHub", done)


# ---------------------------------------------------------------------------
# Comment on This Line in the Open Pull Request...
# ---------------------------------------------------------------------------


def comment_on_line(host: LineHost) -> None:
    provider = host.provider(lambda: comment_on_line(host))
    if provider is None:
        return
    from quill.core.github.rest_transport import request_json

    token = getattr(provider, "token", None)

    def find(site: el.LineSite) -> Any:
        query = el.open_pulls_query(site)
        if query is None:
            return None
        path, params = query
        answer = request_json(token, "GET", path, query=params)
        pulls = answer.data if isinstance(answer.data, list) else []
        return pulls[0] if pulls and isinstance(pulls[0], dict) else None

    def done(site: el.LineSite, pull: Any) -> None:
        if not site.branch:
            host.announce("No branch is checked out here, so there is no pull request to use.")
            return
        if pull is None:
            host.announce(f"No open pull request comes from the branch {site.branch}.")
            return
        number = int(pull.get("number") or 0)
        head = str((pull.get("head") or {}).get("sha") or "")
        if head and head != site.commit:
            host.announce(
                f"Pull request {number} is at commit {head[:7]} and this checkout is at "
                f"{site.commit[:7]}. Push or pull first, so the line numbers match."
            )
            return
        if site.changed:
            host.announce(
                "This file has changes that are not committed. Commit and push them first, "
                "so the line numbers match the pull request."
            )
            return
        anchor = el.line_anchor(site)
        text = _ask_comment(host, f"Comment on {anchor.describe()} in pull request {number}")
        if not text:
            return

        def post() -> Any:
            return provider.post_line_comment(site.repository, number, anchor, text, site.commit)

        def posted(_result: Any) -> None:
            host.announce(f"Commented on {anchor.describe()} in pull request {number}.")

        host.run_background("post the comment", post, posted, _failed(host, "post the comment"))

    _with_site(
        host, "find the pull request for this branch", lambda _s: None, extra=find, then_extra=done
    )


def _ask_comment(host: LineHost, title: str) -> str:
    import wx

    dialog = wx.TextEntryDialog(
        host.parent, "Your comment (Markdown):", title, style=wx.OK | wx.CANCEL | wx.TE_MULTILINE
    )
    dialog.SetName("Comment")
    try:
        if host.show_modal(dialog, title) != wx.ID_OK:
            return ""
        return str(dialog.GetValue()).strip()
    finally:
        dialog.Destroy()


# ---------------------------------------------------------------------------
# The GitHub reference at the cursor
# ---------------------------------------------------------------------------


def open_reference_at_cursor(host: LineHost) -> None:
    """Open ``#42``, ``owner/name#42``, ``@person`` or a commit under the caret."""
    if host.safe_mode:
        host.announce(SAFE_MODE)
        return
    from quill.core.github.local_repo import detect_github_repo
    from quill.core.github.references import GitHubReferenceError, parse_github_reference

    text, offset = host.text_and_offset()
    repository = detect_github_repo(host.file_path() or None)
    found = el.reference_at(text, offset, repository)
    if found is None:
        host.announce("No GitHub reference at the cursor.")
        return
    url = el.reference_url(found)
    if not url:
        host.announce(
            f"{found.describe()} needs a repository: save this document in a GitHub "
            "repository, or write it as owner/name#number."
        )
        return
    if found.kind == "person":
        if webbrowser.open(url, new=2):
            host.announce(f"Opened {found.describe()} on GitHub in your browser.")
        else:
            host.announce("Could not open your browser.")
        return
    then = f"filter:#{found.number}" if found.kind == "item" else f"filter:{found.sha[:7]}"
    try:
        host.open_reference(parse_github_reference(url), then)
    except GitHubReferenceError as exc:
        host.announce(str(exc))
