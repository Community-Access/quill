"""Release and deployment evidence on a row (GX10): reads only, nothing changes.

* **Release Evidence...** on a release: whether it is immutable, the commit its
  tag points at, which checks passed on that commit, which deployments of it
  went to which environments, and each file's attestations.
* **Attestations...** on a release's file: its digest and GitHub's
  attestations for it.
* **Check Download...** on a release's file: the downloaded copy, chosen in an
  Open box that starts in Downloads, hashed with SHA-256 and compared with
  GitHub's digest for the file (:mod:`quill.core.github.asset_digest`).
* **Deployments...** on an environment: its newest deployments, each with its
  latest state. Approving or rejecting one that waits is Review Pending
  Deployments... on the run that is waiting.

Each is read off the UI thread, said in one sentence, and shown as a list a
screen reader moves through line by line (Copy Results copies it). The rules
are :mod:`quill.core.github.release_evidence`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.explore_models import ExploreRow

__all__ = ["EVIDENCE_REASONS", "EVIDENCE_VERBS", "GitHubWorkbenchEvidenceMixin"]

EVIDENCE_VERBS: dict[str, frozenset[str]] = {
    "release_evidence": frozenset({"release"}),
    "asset_attestations": frozenset({"release_asset"}),
    "check_download": frozenset({"release_asset"}),
    "environment_deployments": frozenset({"environment"}),
}

EVIDENCE_REASONS: dict[str, str] = {
    "release_evidence": "Release Evidence... is for a release in a repository.",
    "asset_attestations": "Attestations... is for a file of a release in a repository.",
    "check_download": "Check Download... is for a file of a release in a repository.",
    "environment_deployments": "Deployments... is for an environment, while you are signed in.",
}


class GitHubWorkbenchEvidenceMixin:
    frame: Any
    signed_in: bool
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    #: From the Tools mixin: a read-only list, line by line, with Copy Results.
    _show_text: Callable[[str, str], None]

    def github_api(self) -> Any:
        raise NotImplementedError

    @staticmethod
    def _release_ident(row: object, ref: Any, kind: str) -> dict[str, str]:
        from quill.core.github.sheet_catalog import target_for

        found = target_for(row, str(getattr(ref, "instance", "") or ""))
        if found is None or found.kind != kind or not found.ident.get("repo"):
            return {}
        return dict(found.ident)

    def _fits_release_evidence(self, row: object) -> bool:
        return bool(self._release_ident(row, getattr(self.frame, "current", None), "release"))

    def _fits_asset_attestations(self, row: object) -> bool:
        ident = self._release_ident(row, getattr(self.frame, "current", None), "release_asset")
        return bool(ident.get("tag"))

    _fits_check_download = _fits_asset_attestations

    def _pick_download(self, name: str) -> Any:
        """The downloaded file to check, chosen in an Open box that starts in Downloads."""
        from pathlib import Path

        from quill.ui.dialog_contract import show_modal_dialog

        wx, title = self.frame._wx, "Check Download"
        folder = Path.home() / "Downloads"
        with wx.FileDialog(
            self.frame.frame,
            title,
            defaultDir=str(folder if folder.is_dir() else Path.home()),
            defaultFile=name,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as box:
            if show_modal_dialog(box, title) != wx.ID_OK:
                return None
            return Path(box.GetPath())

    def _do_check_download(self, ref: Any, row: object) -> None:
        from quill.core.github.asset_digest import asset_digest, check_file

        ident, api = self._release_ident(row, ref, "release_asset"), self.github_api()
        repo, tag, name = ident.get("repo", ""), ident.get("tag", ""), ident.get("name", "")
        path = self._pick_download(name)
        if path is None:
            return

        def show(found: Any) -> None:
            self._say(found.sentence)
            if found.matched is not None:
                self._show_text(f"Check Download: {name}", "\n".join(found.lines()))

        self._background(
            f"check {path.name} against {name}",
            lambda: check_file(path, name, asset_digest(api, repo, tag, name)),
            show,
        )

    def _fits_environment_deployments(self, row: object) -> bool:
        return self.signed_in and isinstance(row, ExploreRow) and row.kind == "environment"

    def _do_release_evidence(self, ref: Any, row: object) -> None:
        from quill.core.github.release_evidence import load_release_evidence

        ident, api = self._release_ident(row, ref, "release"), self.github_api()
        repo, tag = ident.get("repo", ""), ident.get("tag", "")

        def show(evidence: Any) -> None:
            self._say(evidence.sentence)
            self._show_text(f"Release Evidence: {tag}", "\n".join(evidence.lines()))

        self._background(
            f"read the evidence for {tag}", lambda: load_release_evidence(api, repo, tag), show
        )

    def _do_asset_attestations(self, ref: Any, row: object) -> None:
        from quill.core.github.release_evidence import attestations_for_asset

        ident, api = self._release_ident(row, ref, "release_asset"), self.github_api()
        repo, tag, name = ident.get("repo", ""), ident.get("tag", ""), ident.get("name", "")

        def show(found: Any) -> None:
            line = found.line()
            self._say(line)
            if found.attestations:
                self._show_text(
                    f"Attestations: {name}",
                    "\n".join([line, f"Digest: {found.digest}.", *_verify_note()]),
                )

        self._background(
            f"read the attestations for {name}",
            lambda: attestations_for_asset(api, repo, tag, name),
            show,
        )

    def _do_environment_deployments(self, _ref: Any, row: object) -> None:
        from quill.core.github.release_evidence import environment_deployments

        assert isinstance(row, ExploreRow)
        repo, name, api = row.repo, row.key, self.github_api()

        def show(found: Any) -> None:
            found = list(found)
            if not found:
                self._say(f"Nothing has deployed to {name} yet.")
                return
            self._say(f"{len(found)} deployments to {name}; the newest is {found[0].state}.")
            self._show_text(f"Deployments: {name}", "\n".join(d.line() for d in found))

        self._background(
            f"list the deployments to {name}",
            lambda: environment_deployments(api, repo, name),
            show,
        )


def _verify_note() -> list[str]:
    from quill.core.github.release_evidence import VERIFY_NOTE

    return [VERIFY_NOTE]
