"""More GitHub Workbench nodes, kept apart so :mod:`workbench_tree` stays under its size budget.

``MORE_FIXED`` joins the account's own nodes and ``MORE_REPOSITORY`` each
repository's; :mod:`quill.core.github.workbench_tree` adds both to the tree.
wx-free and strict-typed.
"""

from __future__ import annotations

from quill.core.workbench.tree import Need, NodeSpec, Scope

__all__ = ["MORE_FIXED", "MORE_REPOSITORY"]

_SIGN_IN = frozenset({Need.SIGN_IN})

MORE_FIXED: tuple[NodeSpec, ...] = (
    NodeSpec(
        "my_codespaces",
        "My Codespaces",
        "repositories",
        needs=_SIGN_IN,
        loader="explore:my_codespaces",
        row_type="codespace",
    ),
)

MORE_REPOSITORY: tuple[NodeSpec, ...] = (
    NodeSpec(
        "environments",
        "Environments",
        "settings",
        scope=Scope.REPOSITORY,
        needs=frozenset({Need.SIGN_IN, Need.ADMIN}),
        loader="explore:repo_environments",
        row_type="environment",
    ),
    NodeSpec(
        "repo_codespaces",
        "Codespaces",
        "code",
        scope=Scope.REPOSITORY,
        needs=_SIGN_IN,
        loader="explore:repo_codespaces",
        row_type="codespace",
    ),
)
