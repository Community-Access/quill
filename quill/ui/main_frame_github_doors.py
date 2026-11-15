"""Repository Admin and Codespaces open the GitHub Workbench and run there (GitHub PRD 6).

Phase 4 took these rows out of the GitHub menu but kept their command ids,
registrations and any key a person bound. With the Workbench in use, each one
now opens the Workbench on the current repository and runs there
(:data:`quill.ui.github_workbench_commands.ADMIN_DOORS`): Rename, Change
Visibility, Change Default Branch and Configure Branch Protection open the
repository's Properties sheet at the page that changes it; Delete Branch,
Create Release, Dispatch Workflow and Security Alerts go to their node; the
rest (Create and Fork Repository, Commit Multiple Files, Browse Organization
and the Codespaces pair) open the Workbench on the repository and run the
editor's own dialog from it, so there is still one implementation.

The Workbench can call an editor-owned command from its own context. The
``_FROM_WORKBENCH`` guard lets that command reach its existing implementation
without opening a second management window. This mixin sits ahead of the
admin, extras and gh-bridge mixins in ``MainFrame``'s order, so the command
registry and menu bindings, which both call ``self.github_*()``, reach it.
"""

from __future__ import annotations

from typing import Any

from quill.ui.github_workbench_commands import ADMIN_DOORS, workbench_takes

__all__ = ["GitHubAdminDoorsMixin"]


def _door(command_id: str) -> Any:
    method = "github_" + command_id.removeprefix("github.")

    def run(self: Any) -> None:
        if workbench_takes(command_id):
            node, then = ADMIN_DOORS[command_id]
            self.open_github_items_viewer(node=node, then=then)
            return
        getattr(super(GitHubAdminDoorsMixin, self), method)()

    run.__name__ = method
    run.__doc__ = f"{command_id}: open the Workbench and continue there."
    return run


class GitHubAdminDoorsMixin:
    """One override per admin and Codespaces command (see the module docstring)."""


for _command_id in ADMIN_DOORS:
    setattr(
        GitHubAdminDoorsMixin, "github_" + _command_id.removeprefix("github."), _door(_command_id)
    )
