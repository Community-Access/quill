"""Repositories > My Packages: deleting a package or one of its versions (GitHub PRD 14.2).

The list itself is an Explore view (``my_packages``, from
:mod:`quill.core.github.packages`). This mixin adds what a package's row can
do: **Delete Package Version...** lists the versions with their tags, newest
first, and deletes the one chosen after asking; **Delete Package...** deletes
the whole package after you type its name.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.explore_models import ExploreRow

__all__ = ["PACKAGE_REASONS", "PACKAGE_VERBS", "GitHubWorkbenchPackagesMixin"]

PACKAGE_VERBS: dict[str, frozenset[str]] = {
    "delete_package_version": frozenset({"package"}),
    "delete_package": frozenset({"package"}),
}

PACKAGE_REASONS: dict[str, str] = {
    "delete_package_version": "Delete Package Version is for a package, while you are signed in.",
    "delete_package": "Delete Package is for a package, while you are signed in.",
}


class GitHubWorkbenchPackagesMixin:
    frame: Any
    signed_in: bool
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _choose: Callable[[str, str, list[str]], int]
    _confirm: Callable[[str, str], bool]

    def github_api(self) -> Any:
        raise NotImplementedError

    @staticmethod
    def _package(row: object) -> tuple[str, str] | None:
        if isinstance(row, ExploreRow) and row.kind == "package" and "/" in row.key:
            kind, _, name = row.key.partition("/")
            return kind, name
        return None

    def _fits_delete_package_version(self, row: object) -> bool:
        return self.signed_in and self._package(row) is not None

    def _fits_delete_package(self, row: object) -> bool:
        return self.signed_in and self._package(row) is not None

    def _do_delete_package_version(self, _ref: Any, row: object) -> None:
        from quill.core.github.packages import fetch_versions

        found = self._package(row)
        if found is None:
            return
        kind, name = found
        api = self.github_api()
        self._background(
            "list the versions",
            lambda: fetch_versions(api, kind, name),
            lambda versions: self._pick_version(kind, name, list(versions)),
        )

    def _pick_version(self, kind: str, name: str, versions: list[Any]) -> None:
        from quill.core.github.packages import delete_version

        if not versions:
            self._say(f"{name} has no versions to delete.")
            return
        picked = self._choose(
            "Delete Package Version",
            f"Which version of {name} to delete? Newest first.",
            [version.label for version in versions],
        )
        if picked < 0:
            return
        version = versions[picked]
        if not self._confirm(
            "Delete Package Version",
            f"Delete version {version.label} of the {kind} package {name}? Anything that "
            "installs this exact version will fail. GitHub can restore it for 30 days.",
        ):
            return
        api = self.github_api()
        self._background(
            "delete the version",
            lambda: delete_version(api, kind, name, version),
            lambda said: (self._say(str(said)), self.frame.reload()),
        )

    def _do_delete_package(self, _ref: Any, row: object) -> None:
        from quill.core.github.packages import delete_package
        from quill.ui.github_repo_admin_dialogs import TypedConfirmDialog

        found = self._package(row)
        if found is None:
            return
        kind, name = found
        if not TypedConfirmDialog(
            self.frame.frame,
            title="Delete Package",
            message=(
                f"Delete the {kind} package {name} and every version of it. Anything that "
                "installs it will fail. GitHub can restore it for 30 days. Type the "
                "package's name to confirm."
            ),
            expected=name,
            confirm_label="Delete",
        ).show():
            self._say("Cancelled; the package was not deleted.")
            return
        api = self.github_api()
        self._background(
            "delete the package",
            lambda: delete_package(api, kind, name),
            lambda said: (self._say(str(said)), self.frame.reload()),
        )
