"""Catalogue rows for GitHub > From This Line (GitHub PRD 22.3, 2026-11-17).

The eight commands that ask GitHub about the line in front of you. They arrive
with their rows (GATE-CATALOGUE), so "who changed this line" or "copy the
GitHub link to this line" reaches them from Say or Type a Command, in QUILL
and, through ``COMMAND_EQUIVALENTS``, in QUILL Lite.

None is offered to the agents: each reads the person's own working copy and
signed-in account. Commenting on a pull request asks first (CONFIRM): it ends
in a post other people read, even though the comment box comes before it.
"""

from __future__ import annotations

from quill.core.command_catalogue.spec import CommandSpec, Kind, Risk

__all__ = ["GITHUB_LINE_ROWS"]

_WHERE = "the GitHub menu, From This Line"

GITHUB_LINE_ROWS: tuple[CommandSpec, ...] = (
    CommandSpec(
        "github.copy_line_link",
        "Copy GitHub Link to This Line",
        "Copy a link to this line on GitHub that keeps pointing at the same text",
        aliases=("copy github link", "github permalink", "link to this line"),
        examples=(
            "copy the github link to this line",
            "give me a permalink for these lines",
            "copy a link to this line on github",
        ),
        risk=Risk.SAFE,
        group="GitHub",
        announces_itself=True,
        where=_WHERE,
    ),
    CommandSpec(
        "localgit.blame_at_cursor",
        "Who Changed This Line?",
        "Say who last changed this line, when, and why",
        aliases=("who changed this line", "who wrote this line", "git blame"),
        examples=(
            "who changed this line",
            "who last edited this line and when",
            "blame this line",
        ),
        risk=Risk.SAFE,
        kind=Kind.READOUT,
        group="GitHub",
        announces_itself=True,
        where=_WHERE,
    ),
    CommandSpec(
        "github.open_line_pull",
        "Open the Pull Request for This Line",
        "Open the pull request that brought this line's last change",
        aliases=("pull request for this line", "which pull request changed this"),
        examples=(
            "open the pull request that changed this line",
            "which pull request brought this line",
            "show the pr for this line",
        ),
        risk=Risk.SAFE,
        kind=Kind.OPENS_DIALOG,
        group="GitHub",
        where=_WHERE,
    ),
    CommandSpec(
        "github.open_line",
        "Open This Line on GitHub",
        "Open this line on GitHub in your browser",
        aliases=("open line on github", "show this line on github"),
        examples=(
            "open this line on github",
            "show me this line on github",
            "view these lines on the github website",
        ),
        risk=Risk.SAFE,
        group="GitHub",
        announces_itself=True,
        where=_WHERE,
    ),
    CommandSpec(
        "github.issue_from_selection",
        "New GitHub Issue from Selection",
        "Start a GitHub issue that quotes the selected text and links to it",
        aliases=("issue from selection", "file an issue about this"),
        examples=(
            "file an issue about the selected code",
            "make a github issue from this selection",
            "open an issue quoting these lines",
        ),
        risk=Risk.SAFE,
        kind=Kind.OPENS_DIALOG,
        group="GitHub",
        where=_WHERE,
    ),
    CommandSpec(
        "github.issues_mentioning_file",
        "GitHub Issues Mentioning This File",
        "List the GitHub issues that mention this file",
        aliases=("issues mentioning this file", "issues about this file"),
        examples=(
            "which issues mention this file",
            "show github issues about this file",
            "find issues that talk about this file",
        ),
        risk=Risk.SAFE,
        kind=Kind.OPENS_DIALOG,
        group="GitHub",
        where=_WHERE,
    ),
    CommandSpec(
        "github.comment_on_line",
        "Comment on This Line in the Open Pull Request",
        "Leave a review comment on this line in the pull request for this branch",
        aliases=("comment on this line", "review comment on this line"),
        examples=(
            "comment on this line in the pull request",
            "leave a review comment on these lines",
            "add a pr comment here",
        ),
        risk=Risk.CONFIRM,
        kind=Kind.OPENS_DIALOG,
        group="GitHub",
        where=_WHERE,
    ),
    CommandSpec(
        "github.open_reference_at_cursor",
        "Open the GitHub Reference at the Cursor",
        "Open the issue, pull request, person or commit written where the cursor is",
        aliases=("open github reference", "open this issue number"),
        examples=(
            "open the issue the cursor is on",
            "open this github reference",
            "go to the pull request mentioned here",
        ),
        risk=Risk.SAFE,
        kind=Kind.OPENS_DIALOG,
        group="GitHub",
        where=_WHERE,
    ),
)
