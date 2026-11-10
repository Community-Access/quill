"""GATE-GITHUB-HELP: F1 help on every GitHub window, control, node, row and option.

GitHub PRD section 7 and Part D10. Two halves, both content rather than wiring:

**Controls and titles** (the shared engine, :mod:`quill.tools.help_audit`):
every helpable control constructed in the GitHub Workbench and in every
``quill/ui/github_*`` window gets one status in the committed inventory
(``tests/unit/ui/fixtures/github_help_inventory.json``); ``missing`` fails the
build, so a new control cannot land without inline ``SetHelpText`` or a
reviewed classification. Every window title the scan can read must have a
purpose in :data:`quill.core.github.workbench_help.SURFACE_PURPOSES`.

**The catalogue** (:mod:`quill.core.github.workbench_help`): every tree node,
every action and menu row, every Workbench Options field and every GitHub
word a node or row names has authored help. :func:`catalogue_gaps` lists what
has none, and any gap fails the build.

Regenerate the inventory with::

    python -m quill.tools.github_help_audit --write

and review the diff: every ``missing`` you commit is a failing build.
"""

from __future__ import annotations

from pathlib import Path

from quill.tools.help_audit import (
    REPO_ROOT,
    ControlSite,
    TitleViolation,
    build_snapshot,
    resolve_paths,
    run_cli,
    scan_paths,
)
from quill.tools.help_audit import (
    STATUSES as STATUSES,
)
from quill.tools.help_audit import (
    write_snapshot as _write_snapshot,
)

SNAPSHOT_PATH = REPO_ROOT / "tests" / "unit" / "ui" / "fixtures" / "github_help_inventory.json"

_SCAN_DIRS: tuple[str, ...] = ()
#: The Workbench (the shared engine's window and GitHub's provider) and every
#: GitHub window, the twenty-seven the nine app gates never covered.
_SCAN_GLOBS: tuple[str, ...] = ("quill/ui/github_*.py", "quill/ui/workbench_*.py")

#: Surface constructions whose titles the scan cannot resolve, with the reason.
TITLE_EXEMPT: dict[str, str] = {
    "quill/ui/github_workbench_list_dialog.py::WorkbenchListDialog.__init__": (
        "One window for GitHub Permissions, Change History and the access tools, titled "
        "by its caller; each title has its purpose in workbench_help's SURFACE_PURPOSES."
    ),
    "quill/ui/workbench_properties_sheet.py::PropertiesSheet.__init__": (
        "The Workbench's Properties sheet, titled after the object it shows at run "
        'time ("Issue #42 Properties - owner/name"); its purpose is the Properties '
        "entry in workbench_help, and every field's help is authored in the sheet model."
    ),
    "quill/ui/github_workbench_results.py::show_results": (
        'A batch\'s results, titled after what was changed ("Changed 14 issues") at '
        "run time; the list's own help says what each line means."
    ),
    "quill/ui/workbench_sheet_editor.py::WorkbenchSheetEditor.__init__": (
        "The shared Workbench's editable Properties sheet, titled after the object "
        "it edits at run time; WordPress's gate owns its words."
    ),
    "quill/ui/github_commit_comments_dialog.py::GitHubCommitCommentsDialog.__init__": (
        "The title names the item it shows, built at run time; every such title "
        "names a GitHub thing the classic-word rule in workbench_help recognises."
    ),
    "quill/ui/github_compare_branches_dialog.py::GitHubCompareBranchesDialog.__init__": (
        "The title names the item it shows, built at run time; every such title "
        "names a GitHub thing the classic-word rule in workbench_help recognises."
    ),
    "quill/ui/github_file_runs_dialog.py::GitHubFileRunsDialog.__init__": (
        "The title names the item it shows, built at run time; every such title "
        "names a GitHub thing the classic-word rule in workbench_help recognises."
    ),
    "quill/ui/github_gist_editor_dialog.py::GitHubGistEditorDialog.__init__": (
        "The title names the item it shows, built at run time; every such title "
        "names a GitHub thing the classic-word rule in workbench_help recognises."
    ),
    "quill/ui/github_line_comment_dialog.py::GitHubLineCommentDialog.__init__": (
        "The title names the item it shows, built at run time; every such title "
        "names a GitHub thing the classic-word rule in workbench_help recognises."
    ),
    "quill/ui/github_milestones_dialog.py::MilestoneFormDialog.__init__": (
        "The title names the item it shows, built at run time; every such title "
        "names a GitHub thing the classic-word rule in workbench_help recognises."
    ),
    "quill/ui/github_pr_diff_dialog.py::GitHubPullDiffDialog.__init__": (
        "The title names the item it shows, built at run time; every such title "
        "names a GitHub thing the classic-word rule in workbench_help recognises."
    ),
    "quill/ui/github_repo_admin_dialogs.py::TypedConfirmDialog.__init__": (
        "The title names the item it shows, built at run time; every such title "
        "names a GitHub thing the classic-word rule in workbench_help recognises."
    ),
    "quill/ui/github_timeline_dialog.py::GitHubTimelineDialog.__init__": (
        "The title names the item it shows, built at run time; every such title "
        "names a GitHub thing the classic-word rule in workbench_help recognises."
    ),
    "quill/ui/workbench_frame.py::WorkbenchFrame.__init__": (
        "The title names the item it shows, built at run time; every such title "
        "names a GitHub thing the classic-word rule in workbench_help recognises."
    ),
    "quill/ui/workbench_properties_dialog.py::WorkbenchPropertiesDialog.__init__": (
        "The title names the item it shows, built at run time; every such title "
        "names a GitHub thing the classic-word rule in workbench_help recognises."
    ),
}


def scan() -> tuple[list[ControlSite], list[TitleViolation]]:
    """Every helpable-control site in the GitHub windows, and every unknown title."""
    from quill.core.github import workbench_help

    return scan_paths(
        resolve_paths(_SCAN_DIRS, _SCAN_GLOBS),
        is_known_title=workbench_help.is_known_title,
        title_exempt=TITLE_EXEMPT,
        catalogue="quill/core/github/workbench_help.py",
    )


def catalogue_gaps() -> list[str]:
    """Every node, row, option or word with no authored help, as sentences."""
    from quill.core.github import workbench_help

    return workbench_help.gaps()


def load_snapshot(path: Path = SNAPSHOT_PATH) -> dict[str, str]:
    from quill.tools.help_audit import load_snapshot as _load

    return _load(path)


def write_snapshot(snapshot: dict[str, str], path: Path = SNAPSHOT_PATH) -> None:
    _write_snapshot(snapshot, path)


def main(argv: list[str] | None = None) -> int:
    status = run_cli(
        argv,
        description=__doc__.splitlines()[0],
        module_name="quill.tools.github_help_audit",
        snapshot_path=SNAPSHOT_PATH,
        scan=scan,
    )
    gaps = catalogue_gaps()
    for gap in gaps:
        print(f"CATALOGUE {gap}")
    if not gaps:
        print("catalogue: every node, row, option and word has help")
    return 1 if status or gaps else 0


__all__ = [
    "SNAPSHOT_PATH",
    "STATUSES",
    "TITLE_EXEMPT",
    "ControlSite",
    "TitleViolation",
    "build_snapshot",
    "catalogue_gaps",
    "load_snapshot",
    "main",
    "scan",
    "write_snapshot",
]


if __name__ == "__main__":
    raise SystemExit(main())
