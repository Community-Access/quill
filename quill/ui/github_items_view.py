"""View-model formatting for the GitHub items viewer (#924).

Wx-free, pure-Python helpers that turn :mod:`quill.core.github.items_provider`
models into ListCtrl cells and a screen-reader-friendly details string. Kept
separate from ``github_items_dialog.py`` (the wx surface) so the formatting --
including the GHManage-parity Quick/Full list mode -- is unit-testable without
a display, and so the dialog module stays under the 600-line size budget.

The reference viewer is GHManage (https://github.com/kellylford/GHManage); this
module mirrors its Item field set and the "Full" list-mode spelling
(``col: value`` per cell) so a screen reader reads a self-describing line.
"""

from __future__ import annotations

from quill.core.github.items_provider import (
    GitHubBranch,
    GitHubCommit,
    GitHubItem,
    GitHubRelease,
    GitHubTag,
    GitHubWorkflow,
    GitHubWorkflowRun,
)

# ---------------------------------------------------------------------------
# View definitions -- one entry per switchable view. Each view names its
# ListCtrl columns.
# ---------------------------------------------------------------------------

VIEW_ISSUES = "issues"
VIEW_BRANCHES = "branches"
VIEW_COMMITS = "commits"
VIEW_TAGS = "tags"
VIEW_RELEASES = "releases"
VIEW_WORKFLOWS = "workflows"
VIEW_RUNS = "runs"

VIEWS: tuple[tuple[str, str], ...] = (
    (VIEW_ISSUES, "Issues & PRs"),
    (VIEW_BRANCHES, "Branches"),
    (VIEW_COMMITS, "Commits"),
    (VIEW_TAGS, "Tags"),
    (VIEW_RELEASES, "Releases"),
    (VIEW_WORKFLOWS, "Workflows"),
    (VIEW_RUNS, "Workflow Runs"),
)

_ISSUE_COLUMNS = ("number", "type", "state", "title", "author", "updated", "labels", "comments")
_BRANCH_COLUMNS = ("name", "protected", "author", "date", "commit")
_COMMIT_COLUMNS = ("short_sha", "author", "date", "message")
_TAG_COLUMNS = ("name", "commit_sha")
_RELEASE_COLUMNS = ("tag", "name", "draft", "prerelease", "created")
_WORKFLOW_COLUMNS = ("name", "state", "path")
_RUN_COLUMNS = ("name", "status", "conclusion", "branch", "event", "run_number")

VIEW_COLUMNS: dict[str, tuple[str, ...]] = {
    VIEW_ISSUES: _ISSUE_COLUMNS,
    VIEW_BRANCHES: _BRANCH_COLUMNS,
    VIEW_COMMITS: _COMMIT_COLUMNS,
    VIEW_TAGS: _TAG_COLUMNS,
    VIEW_RELEASES: _RELEASE_COLUMNS,
    VIEW_WORKFLOWS: _WORKFLOW_COLUMNS,
    VIEW_RUNS: _RUN_COLUMNS,
}

SORT_ORDERS: tuple[tuple[str, str], ...] = (
    ("number_desc", "Number (newest first)"),
    ("number_asc", "Number (oldest first)"),
    ("title_asc", "Title (A-Z)"),
    ("title_desc", "Title (Z-A)"),
    ("updated_desc", "Updated (newest first)"),
    ("updated_asc", "Updated (oldest first)"),
    ("comments_desc", "Comments (most first)"),
)


def sort_items(items: list[GitHubItem], order: str) -> list[GitHubItem]:
    """Sort issue/PR rows by the given order key (GHManage parity).

    The combined issues+PRs inbox arrives from two PyGithub calls; this is the
    single place they get merged and ordered. Never raises -- a sort failure
    falls back to the incoming order so the render always succeeds.
    """
    key = {
        "number_desc": lambda i: i.number,
        "number_asc": lambda i: i.number,
        "title_asc": lambda i: i.title.lower(),
        "title_desc": lambda i: i.title.lower(),
        "updated_desc": lambda i: i.updated_at,
        "updated_asc": lambda i: i.updated_at,
        "comments_desc": lambda i: i.comments,
    }.get(order, lambda i: i.number)
    try:
        return sorted(items, key=key, reverse=order.endswith("_desc"))
    except Exception:  # noqa: BLE001 - never let a sort fail the render
        return items


def view_label(view: str) -> str:
    return next((label for key, label in VIEWS if key == view), view)


def parse_repo_reference(text: str) -> str | None:
    """Normalize a pasted GitHub URL or ``owner/repo`` string to ``owner/repo``.

    Accepts a plain ``owner/repo``, an ``https://github.com/owner/repo`` URL
    (with or without a trailing ``.git``, ``/tree/...``, ``/pull/...``, etc.),
    and an ssh ``git@github.com:owner/repo.git`` remote -- the shapes a user
    is most likely to paste from a browser address bar or ``git remote -v``
    (GHManage parity, Ctrl+Shift+O). Returns ``None`` when no owner/repo pair
    can be recovered.
    """
    value = text.strip()
    if not value:
        return None
    if value.startswith("git@github.com:"):
        value = value[len("git@github.com:") :]
    else:
        for prefix in ("https://github.com/", "http://github.com/", "github.com/"):
            if value.lower().startswith(prefix):
                value = value[len(prefix) :]
                break
    if value.endswith(".git"):
        value = value[: -len(".git")]
    parts = [p for p in value.split("/") if p]
    if len(parts) < 2:
        return None
    owner, repo = parts[0], parts[1]
    return f"{owner}/{repo}"


# ---------------------------------------------------------------------------
# Row + detail formatting (the list mode lives here -- GHManage parity).
# ---------------------------------------------------------------------------


def _cell(model: object, col: str) -> str:
    """Return the display string for one column of one model."""
    if isinstance(model, GitHubItem):
        if col == "number":
            return str(model.number)
        if col == "type":
            return model.kind
        if col == "state":
            return model.state_display
        if col == "title":
            return model.title
        if col == "author":
            return model.author
        if col == "updated":
            return model.updated_at[:10]
        if col == "labels":
            return ", ".join(model.labels)
        if col == "comments":
            return str(model.comments)
    if isinstance(model, GitHubBranch):
        if col == "name":
            return model.name
        if col == "protected":
            return "protected" if model.protected else ""
        if col == "author":
            return model.commit_author
        if col == "date":
            return model.commit_date[:10]
        if col == "commit":
            return model.commit_sha[:7]
    if isinstance(model, GitHubCommit):
        if col == "short_sha":
            return model.short_sha
        if col == "author":
            return model.author
        if col == "date":
            return model.date[:10]
        if col == "message":
            return model.message.splitlines()[0] if model.message else ""
    if isinstance(model, GitHubTag):
        if col == "name":
            return model.name
        if col == "commit_sha":
            return model.commit_sha[:7]
    if isinstance(model, GitHubRelease):
        if col == "tag":
            return model.tag
        if col == "name":
            return model.name
        if col == "draft":
            return "draft" if model.draft else ""
        if col == "prerelease":
            return "prerelease" if model.prerelease else ""
        if col == "created":
            return model.created_at[:10]
    if isinstance(model, GitHubWorkflow):
        if col == "name":
            return model.name
        if col == "state":
            return model.state
        if col == "path":
            return model.path
    if isinstance(model, GitHubWorkflowRun):
        if col == "name":
            return model.name
        if col == "status":
            return model.status
        if col == "conclusion":
            return model.conclusion
        if col == "branch":
            return model.branch
        if col == "event":
            return model.event
        if col == "run_number":
            return str(model.run_number)
    return ""


def row_cells(model: object, columns: tuple[str, ...], *, full: bool) -> list[str]:
    """Return the per-column cell strings. Full mode prefixes ``col: `` for a
    screen-reader self-describing line (GHManage parity)."""
    cells: list[str] = []
    for col in columns:
        value = _cell(model, col)
        if full and value:
            cells.append(f"{col}: {value}")
        else:
            cells.append(value)
    return cells


def item_detail(
    item: GitHubItem, comments: list[dict[str, str]]
) -> tuple[str, list[tuple[int, int]]]:
    """Return (detail_text, comment_positions) for an issue/PR.

    ``comment_positions`` is ``(start_line, line_count)`` per comment for the
    Alt+N/Alt+P navigator. Mirrors GHManage's details layout.
    """
    lines: list[str] = [
        f"#{item.number} [{item.kind}] {item.title}",
        f"State: {item.state_display}",
        f"Author: {item.author}",
        f"Created: {item.created_at}",
        f"Updated: {item.updated_at}",
        f"URL: {item.url}",
    ]
    if item.labels:
        lines.append(f"Labels: {', '.join(item.labels)}")
    if item.assignees:
        lines.append(f"Assignees: {', '.join(item.assignees)}")
    lines.append(f"Comments: {item.comments}")
    if item.is_pr:
        lines.append(f"Draft: {'Yes' if item.is_draft else 'No'}")
        lines.append(f"Merged: {'Yes' if item.is_merged else 'No'}")
        if item.review_status:
            lines.append(f"Review: {item.review_status}")
        lines.append(f"Branches: {item.head_branch} -> {item.base_branch}")
        lines.append(f"Changes: +{item.additions} -{item.deletions} ({item.changed_files} files)")
    lines += ["", "-" * 60, "", item.body or "(no description)", ""]
    positions: list[tuple[int, int]] = []
    if comments:
        lines += ["-" * 60, f"Comments ({len(comments)}):", "-" * 60]
        for i, c in enumerate(comments):
            lines.append("")
            start_line = len(lines)
            header = (
                f"  Comment {i + 1} of {len(comments)} - "
                f"{c.get('author', '')} ({c.get('created_at', '')[:10]}):"
            )
            lines.append(header)
            body_lines = [f"    {ln}" for ln in c.get("body", "").splitlines() or [""]]
            lines.extend(body_lines)
            positions.append((start_line, len(body_lines) + 1))
    return "\n".join(lines), positions


def model_detail(model: object) -> str:
    """Detail text for the non-issue views (no comment thread)."""
    if isinstance(model, GitHubBranch):
        return "\n".join([
            f"Branch: {model.name}",
            f"Protected: {'Yes' if model.protected else 'No'}",
            f"Commit: {model.commit_sha}",
            f"Author: {model.commit_author}",
            f"Date: {model.commit_date}",
            f"URL: {model.url}",
            "",
            model.commit_message,
        ])
    if isinstance(model, GitHubCommit):
        return "\n".join([
            f"Commit: {model.sha}",
            f"Author: {model.author}",
            f"Date: {model.date}",
            f"URL: {model.url}",
            f"Changes: +{model.additions} -{model.deletions} ({model.files_changed} files)",
            "",
            model.message,
        ])
    if isinstance(model, GitHubTag):
        return f"Tag: {model.name}\nCommit: {model.commit_sha}\nURL: {model.url}"
    if isinstance(model, GitHubRelease):
        return "\n".join([
            f"Release: {model.name} ({model.tag})",
            f"Draft: {'Yes' if model.draft else 'No'}",
            f"Prerelease: {'Yes' if model.prerelease else 'No'}",
            f"Created: {model.created_at}",
            f"URL: {model.url}",
            "",
            model.body or "(no release notes)",
        ])
    if isinstance(model, GitHubWorkflow):
        return "\n".join([
            f"Workflow: {model.name}",
            f"State: {model.state}",
            f"Path: {model.path}",
            f"URL: {model.url}",
            "",
            "Press Enter (or Actions... > Run on Branch...) to dispatch this "
            "workflow, if it accepts manual runs.",
        ])
    if isinstance(model, GitHubWorkflowRun):
        return "\n".join([
            f"Run: {model.name} #{model.run_number}",
            f"Status: {model.status}",
            f"Conclusion: {model.conclusion}",
            f"Branch: {model.branch}",
            f"Event: {model.event}",
            f"Created: {model.created_at}",
            f"URL: {model.url}",
        ])
    return ""


def model_url(model: object) -> str:
    return getattr(model, "url", "") or ""


def model_label(model: object) -> str:
    if isinstance(model, GitHubItem):
        return f"#{model.number}"
    if isinstance(model, GitHubBranch):
        return f"branch {model.name}"
    if isinstance(model, GitHubCommit):
        return f"commit {model.short_sha}"
    if isinstance(model, GitHubTag):
        return f"tag {model.name}"
    if isinstance(model, GitHubRelease):
        return f"release {model.tag}"
    if isinstance(model, GitHubWorkflow):
        return f"workflow {model.name}"
    if isinstance(model, GitHubWorkflowRun):
        return f"run {model.name}"
    return "item"


__all__ = [
    "SORT_ORDERS",
    "VIEWS",
    "VIEW_BRANCHES",
    "VIEW_COLUMNS",
    "VIEW_COMMITS",
    "VIEW_ISSUES",
    "VIEW_RELEASES",
    "VIEW_RUNS",
    "VIEW_TAGS",
    "VIEW_WORKFLOWS",
    "item_detail",
    "model_detail",
    "model_label",
    "model_url",
    "parse_repo_reference",
    "row_cells",
    "sort_items",
    "view_label",
]


# ---------------------------------------------------------------------------
# PR diff rendering (Unified GitHub Management: "PR Diff Viewer") -- the file
# content of both sides runs through QUILL's own compare engine
# (quill.core.compare_service), so a pull request's changes read as the same
# accessible difference walk Compare Documents already gives: "Difference N of
# M, text changed at line L, left ..., right ...", never a raw unified patch.
# ---------------------------------------------------------------------------


def pull_diff_file_label(pull_file: object) -> str:
    """One list row per changed file: status, +/- counts, name (rename-aware)."""
    status = str(getattr(pull_file, "status", "") or "changed")
    name = str(getattr(pull_file, "filename", ""))
    previous = str(getattr(pull_file, "previous_filename", "") or "")
    additions = int(getattr(pull_file, "additions", 0) or 0)
    deletions = int(getattr(pull_file, "deletions", 0) or 0)
    rename = f" (was {previous})" if previous and previous != name else ""
    return f"{status}: {name}{rename}  +{additions} -{deletions}"


def render_pull_file_diff(
    filename: str,
    base_text: str,
    head_text: str,
    *,
    base_label: str = "base",
    head_label: str = "this PR",
) -> str:
    """An accessible compare of one PR file, via QUILL's compare engine.

    Returns the full spoken-friendly walk: a header, then every
    DifferenceGroup's verbose summary (location, what changed, the changed
    words) followed by the actual lines, prefixed the screen-reader-friendly
    way (``base:`` / ``this PR:``). Whole-file adds/removes are stated plainly
    instead of dumping hundreds of "added" lines.
    """
    from quill.core.compare_service import CompareService

    if not base_text and head_text:
        line_count = len(head_text.splitlines())
        header = f"{filename}: new file with {line_count} lines.\n\n"
        return header + head_text
    if base_text and not head_text:
        line_count = len(base_text.splitlines())
        return f"{filename}: file deleted ({line_count} lines removed)."
    service = CompareService()
    groups = service.compare(base_text, head_text, left_label=base_label, right_label=head_label)
    if not groups:
        return f"{filename}: no text differences (content identical on both sides)."
    parts = [f"{filename}: {len(groups)} difference{'s' if len(groups) != 1 else ''}.", ""]
    for group in groups:
        parts.append(group.summary_verbose)
        for line in group.left_text:
            parts.append(f"  {base_label}: {line}")
        for line in group.right_text:
            parts.append(f"  {head_label}: {line}")
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"
