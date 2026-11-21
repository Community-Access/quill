"""Repositories > My Packages: deleting a package or one of its versions (GitHub PRD 14.2).

The list itself is an Explore view (``my_packages``, from
:mod:`quill.core.github.packages`). This mixin adds what a package's row can
do: **Delete Package Version...** lists the versions with their tags, newest
first, and deletes the one chosen after you type the package's name;
**Delete Package...** deletes the whole package the same way. Repository >
Packages lists a repository's own, with the same commands.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.explore_models import ExploreRow

__all__ = ["PACKAGE_REASONS", "PACKAGE_VERBS", "GitHubWorkbenchPackagesMixin"]

PACKAGE_VERBS: dict[str, frozenset[str]] = {
    "restore_package": frozenset({"view"}),
    "delete_package_version": frozenset({"package"}),
    "delete_package": frozenset({"package"}),
    "show_package_versions": frozenset({"package"}),
    "restore_package_version": frozenset({"package"}),
}

PACKAGE_REASONS: dict[str, str] = {
    "restore_package": "Restore Package is Ctrl+N in a list of packages, while you are signed in.",
    "delete_package_version": "Delete Package Version is for a package, while you are signed in.",
    "delete_package": "Delete Package is for a package, while you are signed in.",
    "show_package_versions": "Show Versions is for a package, while you are signed in.",
    "restore_package_version": (
        "Restore Package Version is for your own or your organization's package."
    ),
}


class GitHubWorkbenchPackagesMixin:
    frame: Any
    signed_in: bool
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _choose: Callable[[str, str, list[str]], int]
    _confirm: Callable[[str, str], bool]
    _ask_text: Callable[..., str]
    _show_text: Callable[[str, str], None]

    def github_api(self) -> Any:
        raise NotImplementedError

    @staticmethod
    def _package(row: object) -> tuple[str, str, str] | None:
        """(organization or "", type, name) for a package row."""
        from quill.core.github.packages import row_parts

        if isinstance(row, ExploreRow) and row.kind == "package" and "/" in row.key:
            if row.key.startswith("~"):  # another person's: only they may change it
                return None
            return row_parts(row.key)
        return None

    @staticmethod
    def _any_package(row: object) -> tuple[str, str, str, str] | None:
        """(organization, person, type, name) for any package row, another person's too."""
        from quill.core.github.packages import row_owner

        if isinstance(row, ExploreRow) and row.kind == "package" and "/" in row.key:
            return row_owner(row.key)
        return None

    def _fits_delete_package_version(self, row: object) -> bool:
        return self.signed_in and self._package(row) is not None

    def _fits_delete_package(self, row: object) -> bool:
        return self.signed_in and self._package(row) is not None

    def _fits_show_package_versions(self, row: object) -> bool:
        return self.signed_in and self._any_package(row) is not None

    def _fits_restore_package_version(self, row: object) -> bool:
        return self.signed_in and self._package(row) is not None

    def _do_show_package_versions(self, _ref: Any, row: object) -> None:
        from quill.core.github.packages import fetch_versions, versions_text

        found = self._any_package(row)
        if found is None:
            return
        org, person, kind, name = found
        api = self.github_api()
        self._background(
            f"list the versions of {name}",
            lambda: fetch_versions(api, kind, name, org, person=person),
            lambda versions: self._show_text(
                f"Versions: {name}", versions_text(name, list(versions))
            ),
        )

    def _do_restore_package_version(self, _ref: Any, row: object) -> None:
        from quill.core.github.packages import fetch_versions, restore_version

        found = self._package(row)
        if found is None:
            return
        org, kind, name = found
        api = self.github_api()

        def chosen(versions: Any) -> None:
            versions = list(versions)
            if not versions:
                self._say(f"{name} has no deleted versions to restore.")
                return
            picked = self._choose(
                "Restore Package Version",
                f"Which deleted version of {name} to bring back? Newest first.",
                [version.label for version in versions],
            )
            if picked < 0:
                return
            version = versions[picked]
            self._background(
                "restore the version",
                lambda: restore_version(api, kind, name, version, org),
                lambda said: (self._say(str(said)), self.frame.reload()),
            )

        self._background(
            f"list the deleted versions of {name}",
            lambda: fetch_versions(api, kind, name, org, state="deleted"),
            chosen,
        )

    def _do_delete_package_version(self, _ref: Any, row: object) -> None:
        from quill.core.github.packages import fetch_versions

        found = self._package(row)
        if found is None:
            return
        org, kind, name = found
        api = self.github_api()
        self._background(
            "list the versions",
            lambda: fetch_versions(api, kind, name, org),
            lambda versions: self._pick_version(kind, name, list(versions), org),
        )

    def _pick_version(self, kind: str, name: str, versions: list[Any], org: str = "") -> None:
        from quill.core.github.packages import delete_version
        from quill.ui.github_repo_admin_dialogs import TypedConfirmDialog

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
        # A version's own name is often a 71-character digest, so the package's name is typed.
        if not TypedConfirmDialog(
            self.frame.frame,
            title="Delete Package Version",
            message=(
                f"Delete version {version.label} of the {kind} package {name}. Anything that "
                "installs this exact version will fail. GitHub can restore it for 30 days. "
                "Type the package's name to confirm."
            ),
            expected=name,
            confirm_label="Delete",
        ).show():
            self._say("Cancelled; the version was not deleted.")
            return
        api = self.github_api()
        self._background(
            "delete the version",
            lambda: delete_version(api, kind, name, version, org),
            lambda said: (self._say(str(said)), self.frame.reload()),
        )

    def _do_delete_package(self, _ref: Any, row: object) -> None:
        from quill.core.github.packages import delete_package
        from quill.ui.github_repo_admin_dialogs import TypedConfirmDialog

        found = self._package(row)
        if found is None:
            return
        org, kind, name = found
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
            lambda: delete_package(api, kind, name, org),
            lambda said: (self._say(str(said)), self.frame.reload()),
        )

    # -- restoring ---------------------------------------------------------------------

    def _fits_restore_package(self, _row: object) -> bool:
        key = getattr(getattr(self.frame, "current", None), "key", "")
        return self.signed_in and key in ("packages", "organization_packages")

    def _do_restore_package(self, ref: Any, _row: object) -> None:
        from quill.core.github.packages import PACKAGE_TYPES, restore_package

        org = (
            ref.instance
            if getattr(self.frame.current, "key", "") == "organization_packages"
            else ""
        )
        picked = self._choose(
            "Restore Package", "Which type of package was deleted?", list(PACKAGE_TYPES)
        )
        if picked < 0:
            return
        kind = PACKAGE_TYPES[picked]
        name = self._ask_text("Restore Package", f"The deleted {kind} package's name:")
        if not name:
            return
        api = self.github_api()
        self._background(
            "restore the package",
            lambda: restore_package(api, kind, name, org),
            lambda said: (self._say(str(said)), self.frame.reload()),
        )
