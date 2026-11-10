"""The GitHub provider for the Workbench window, and the one way to open it.

Phase 1 spike (GitHub PRD section 11): the window's tree is the whole of
:data:`quill.core.github.workbench_tree.GITHUB_TREE`, and the seven GitHub
Items views load in it through the same provider calls GitHub Items makes
(no new network call). Every other node is shown, says what it will hold,
and points at the window that still has it, so nothing seems to vanish.

Reached only behind the developer flag
(:mod:`quill.core.github.workbench_flag`), through
:func:`quill.ui.github_workbench_commands.open_in_workbench_window`, which
both editors call: QUILL Lite is never ahead.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from quill.core.github.item_actions import GITHUB_ACTIONS
from quill.core.github.items_provider import (
    GitHubBranch,
    GitHubCommit,
    GitHubItem,
    GitHubRelease,
    GitHubReleaseAsset,
    GitHubTag,
    GitHubWorkflow,
    GitHubWorkflowRun,
)
from quill.core.github.items_provider_constants import DEFAULT_PAGE_LIMIT
from quill.core.github.workbench_sheets import sheet_for, sheet_title, values_for
from quill.core.github.workbench_tree import GITHUB_TREE, START_NODE, node_for_items_view
from quill.core.github.workbench_window_menu import GO_NODES, WINDOW_MENU
from quill.core.workbench.filters import Query, describe, render
from quill.core.workbench.properties import SheetSpec
from quill.core.workbench.tree import Need, NodeSpec
from quill.ui.github_items_view import (
    VIEW_COLUMNS,
    item_detail,
    model_detail,
    model_url,
    parse_repo_reference,
    row_cells,
    sort_items,
)
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame
from quill.ui.workbench_status_bar import StatusCell

__all__ = ["START_HERE", "GitHubWorkbenchProvider", "open_github_workbench"]

START_HERE = (
    "The GitHub Workbench is one window for GitHub. It has three panes. The tree, "
    "where you are now, says where you are. The list says what is there. The details "
    "say what the selected one is. F6 moves from pane to pane and then to the status "
    "bar. Enter does the obvious thing; the Applications key lists everything else; "
    "Alt+Enter opens Properties. Backspace or Alt+Left goes back. F1 says what any "
    "control does.\n\nThis is an early preview: GitHub Items' seven views live under "
    "each repository here. Everything else in the tree is shown so you can see where "
    "it will go, and GitHub Items and Explore GitHub still have it."
)

_ROW_TYPES: tuple[tuple[type, str], ...] = (
    (GitHubBranch, "branch"),
    (GitHubCommit, "commit"),
    (GitHubTag, "tag"),
    (GitHubRelease, "release"),
    (GitHubReleaseAsset, "release_asset"),
    (GitHubWorkflow, "workflow"),
    (GitHubWorkflowRun, "run"),
)

_NEEDS_WORDS = {
    Need.SIGN_IN: "a signed-in GitHub account",
    Need.PUSH: "push access to the repository",
    Need.ADMIN: "admin access to the repository",
    Need.OPT_IN: "your opt-in, because it loads extra data",
    Need.FORK: "a repository that is a fork",
}


class GitHubWorkbenchProvider:
    """GitHub, for :class:`~quill.ui.workbench_frame.WorkbenchFrame`."""

    name = "GitHub Workbench"
    tree = GITHUB_TREE
    actions = GITHUB_ACTIONS
    menu = WINDOW_MENU
    go_nodes = GO_NODES

    def __init__(
        self, items: Any, repository: str = "", *, announce: Callable[[str], None]
    ) -> None:
        self.items = items
        self._repositories: list[str] = [repository] if repository else []
        self._announce = announce
        self.frame: WorkbenchFrame | None = None

    # -- the tree -----------------------------------------------------------------

    def window_title(self, instance: str) -> str:
        return f"{self.name} - {instance}" if instance else self.name

    def instances(self, template: str) -> Sequence[str]:
        return tuple(self._repositories) if template == "repository" else ()

    def add_instance(self, template: str, address: str) -> NodeRef | None:
        name = parse_repo_reference(address)
        if template != "repository" or name is None:
            return None
        if name in self._repositories:
            self._repositories.remove(name)
        self._repositories.insert(0, name)
        return NodeRef("repository", "repository", name)

    def node_help(self, ref: NodeRef, node: NodeSpec) -> str:
        if ref == NodeRef("", START_NODE):
            signed_in = "You are signed in." if self.signed_in else "You are not signed in."
            return f"{START_HERE}\n\n{signed_in}"
        what = node.label if not ref.instance else f"{node.label}, {ref.instance}"
        needs = ", ".join(_NEEDS_WORDS[need] for need in sorted(node.needs))
        lines = [what + "."]
        if needs:
            lines.append(f"Needs {needs}.")
        if not node.loader:
            lines.append("Open it with Right Arrow to see what it holds.")
        return " ".join(lines)

    def unavailable(self, ref: NodeRef, node: NodeSpec) -> str:
        if not node.loader:
            return ""
        if node.loader.startswith("items:"):
            if not ref.instance:
                return "Open a repository first: Ctrl+L, or File > Open GitHub Address."
            return ""
        if Need.SIGN_IN in node.needs and not self.signed_in:
            return "Sign in to GitHub to see this: GitHub menu > Manage GitHub Accounts."
        return (
            "This view is not in this preview yet. Explore GitHub still has it, "
            "from the editor's GitHub menu."
        )

    @property
    def signed_in(self) -> bool:
        return bool(getattr(self.items, "is_authenticated", False))

    # -- rows ---------------------------------------------------------------------

    def load(self, ref: NodeRef, node: NodeSpec, query: Query) -> list[object]:
        """Fetch a node's rows. Runs off the UI thread; the calls are GitHub Items' own."""
        view, repo, items = node.loader.removeprefix("items:"), ref.instance, self.items
        limit = DEFAULT_PAGE_LIMIT
        preset = dict(node.preset)
        if view == "issues":
            show = preset.get("show", "both")
            if query.conditions:
                kind = {"issues": " is:issue", "prs": " is:pr"}.get(show, "")
                found = items.search_items(
                    repo, render(Query(query.conditions)) + kind, limit=limit
                )
                return list(sort_items(found, "number_desc"))
            rows: list[GitHubItem] = []
            if show in ("issues", "both"):
                rows += items.fetch_issues(repo, state="open", limit=limit)
            if show in ("prs", "both"):
                rows += items.fetch_pulls(repo, state="open", limit=limit)
            return list(sort_items([r for r in rows if isinstance(r, GitHubItem)], "number_desc"))
        fetch = {
            "branches": lambda: items.fetch_branches(repo, limit=limit),
            "commits": lambda: items.fetch_commits(repo, branch=None, limit=limit),
            "tags": lambda: items.fetch_tags(repo, limit=limit),
            "releases": lambda: items.fetch_releases(repo, limit=limit),
            "workflows": lambda: items.fetch_workflows(repo, limit=limit),
            "runs": lambda: items.fetch_workflow_runs(repo, limit=limit),
        }.get(view)
        return list(fetch()) if fetch is not None else []

    def columns(self, node: NodeSpec) -> tuple[str, ...]:
        return VIEW_COLUMNS.get(node.loader.removeprefix("items:"), ())

    def cells(self, row: object, columns: tuple[str, ...]) -> list[str]:
        return row_cells(row, columns, full=False)

    def detail(self, row: object) -> str:
        if isinstance(row, GitHubItem):
            return item_detail(row, [])[0]
        return model_detail(row)

    def row_type(self, node: NodeSpec, row: object) -> str:
        if isinstance(row, GitHubItem):
            return "pull_request" if row.is_pr else "issue"
        return next((kind for cls, kind in _ROW_TYPES if isinstance(row, cls)), "node")

    def url(self, ref: NodeRef, row: object | None) -> str:
        if row is not None:
            return model_url(row)
        return f"https://github.com/{ref.instance}" if ref.instance else "https://github.com"

    def properties(self, ref: NodeRef, row: object) -> tuple[SheetSpec, dict[str, Any], str] | None:
        if not isinstance(row, GitHubItem):
            return None
        return sheet_for(row), dict(values_for(row)), sheet_title(row, ref.instance)

    # -- commands -----------------------------------------------------------------

    def supports(self, command_id: str) -> bool:
        return command_id in {"github.workbench.open", "github.workbench.review"}

    def run(self, command_id: str, ref: NodeRef, row: object) -> bool:
        frame = self.frame
        if frame is None or not self.supports(command_id):
            return False
        if command_id == "github.workbench.open":
            frame.details.SetFocus()
            return True
        if isinstance(row, GitHubItem) and row.is_pr:
            from quill.ui.github_pr_review_dialog import GitHubPullReviewDialog

            GitHubPullReviewDialog(
                frame.frame, self.items, ref.instance, row.number, announce_cb=self._announce
            ).show()
            return True
        return False

    # -- the status bar -----------------------------------------------------------

    def status_cells(self, frame: WorkbenchFrame) -> Sequence[StatusCell]:
        self.frame = frame

        def repository() -> str:
            current = frame.current
            return current.instance if current is not None and current.instance else ""

        def items_text() -> str:
            if frame.current is None or not frame.node(frame.current).loader:
                return ""
            chosen = len(frame.selected_indices())
            shown = f"{len(frame.rows)} shown"
            return f"{shown}, {chosen} selected" if chosen > 1 else shown

        def loading() -> str:
            if frame.loading:
                return "Loading"
            return f"Up to date, {frame.loaded_at}" if frame.loaded_at else ""

        return (
            StatusCell(
                "account",
                "Account",
                lambda: "Signed in" if self.signed_in else "Not signed in",
                "Whether GitHub knows who you are. The editor's GitHub menu manages accounts.",
            ),
            StatusCell(
                "repository",
                "Repository",
                repository,
                "The repository the selected node belongs to. Enter selects its node.",
                activate=lambda: frame.go("github.workbench.go_repository"),
                menu=lambda: (("Open on GitHub", frame.open_in_browser),),
            ),
            StatusCell(
                "items",
                "Items",
                items_text,
                "How many rows the list shows and how many are selected.",
                activate=frame.list.SetFocus,
            ),
            StatusCell(
                "filter",
                "Filter",
                lambda: describe(frame.query) if frame.current is not None else "",
                "The filter in effect. Enter moves to the filter box.",
                activate=frame.filter.SetFocus,
                menu=lambda: (("Clear Filter", frame.clear_filter),),
            ),
            StatusCell(
                "loading",
                "Loading",
                loading,
                "Whether the list is still loading, or when it last loaded. Enter refreshes.",
                activate=frame.reload,
                menu=lambda: (("Refresh", frame.reload),),
            ),
        )

    def close(self) -> None:
        try:
            self.items.close()
        except Exception:  # noqa: BLE001 - closing is best-effort cleanup
            pass


_OPEN: dict[str, WorkbenchFrame] = {}


def _start_ref(repository: str, view: str) -> NodeRef:
    if not repository:
        return NodeRef("", START_NODE)
    key = node_for_items_view(view) if view else node_for_items_view("issues")
    return NodeRef("repository", key, repository)


def open_github_workbench(
    editor: Any,
    items: Any,
    *,
    repository: str = "",
    view: str = "",
    announce: Callable[[str], None] | None = None,
) -> WorkbenchFrame:
    """Open the one GitHub Workbench (or bring it forward), at *view* of *repository*.

    The window owns *items* from here on and closes it with itself. A second
    open while one is showing closes the new *items* and reuses the window.
    """
    say = announce or (lambda _text: None)
    existing = _OPEN.get("github")
    if existing is not None:
        try:
            items.close()
        except Exception:  # noqa: BLE001
            pass
        provider = existing.provider
        if repository and isinstance(provider, GitHubWorkbenchProvider):
            provider.add_instance("repository", repository)
            existing._build_tree()
        existing.show(_start_ref(repository, view))
        return existing
    provider = GitHubWorkbenchProvider(items, repository, announce=say)
    frame = WorkbenchFrame(
        provider, editor=editor, announce=say, on_closed=lambda: _OPEN.pop("github", None)
    )
    _OPEN["github"] = frame
    frame.show(_start_ref(repository, view))
    return frame
