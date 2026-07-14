"""Tests for ArtifactsDialog: list/refresh, download-selected/all gating,
overwrite confirmation, and cancellation -- mirroring the real-wx.App,
_SyncThread, faked-provider pattern already used for GitHubItemsDialog's
write actions in test_github_items_dialog_actions.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import wx

from quill.core.github.items_provider import GitHubArtifact, GitHubItemsError
from quill.ui.github_artifacts_dialog import ArtifactsDialog


class _FakeProvider:
    def __init__(self) -> None:
        self.artifacts: list[GitHubArtifact] = [
            GitHubArtifact(
                id=1,
                name="build-output",
                size_bytes=2048,
                expired=False,
                archive_download_url="https://api.github.com/artifacts/1/zip",
            ),
        ]
        self.raise_on_fetch: Exception | None = None
        self.downloaded: list[tuple[str, Path]] = []
        self.raise_on_download: dict[str, Exception] = {}

    def fetch_workflow_run_artifacts(self, repo: str, run_id: int) -> list[GitHubArtifact]:
        if self.raise_on_fetch is not None:
            raise self.raise_on_fetch
        return self.artifacts

    def download_artifact_to_file(
        self,
        artifact: GitHubArtifact,
        dest: Path,
        *,
        progress: Any = None,
        should_cancel: Any = None,
    ) -> Path:
        if artifact.name in self.raise_on_download:
            raise self.raise_on_download[artifact.name]
        if progress is not None:
            progress(artifact.size_bytes, artifact.size_bytes)
        dest.write_bytes(b"zip")
        self.downloaded.append((artifact.name, dest))
        return dest


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


class _SyncThread:
    """See test_github_items_dialog_actions.py's _SyncThread: runs the
    target immediately on .start() so worker/CallAfter round trips are
    deterministic without a real event loop."""

    def __init__(
        self, target=None, args: tuple = (), kwargs: dict | None = None, daemon=None, **_kw: Any
    ) -> None:
        self._target = target
        self._args = args
        self._kwargs = kwargs or {}

    def start(self) -> None:
        if self._target is not None:
            self._target(*self._args, **self._kwargs)


@pytest.fixture
def provider() -> _FakeProvider:
    return _FakeProvider()


@pytest.fixture
def dlg(wx_app, provider: _FakeProvider, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("quill.ui.github_artifacts_dialog.threading.Thread", _SyncThread)
    monkeypatch.setattr(wx, "CallAfter", lambda fn, *a, **k: fn(*a, **k))
    frame = wx.Frame(None)
    dialog = ArtifactsDialog(
        frame,
        provider,
        repo="owner/repo",
        run_id=42,
        run_label="#42 - build.yml",
        run_url="https://github.com/owner/repo/actions/runs/42",
    )
    announcements: list[str] = []
    dialog._announce = lambda message: announcements.append(message)
    dialog.announcements = announcements
    return dialog


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def test_reload_populates_the_list(dlg, provider: _FakeProvider) -> None:
    dlg._reload()
    assert dlg._artifacts == provider.artifacts
    assert dlg._list.GetItemCount() == 1
    assert dlg._list.GetItemText(0, 0) == "build-output"
    assert dlg._list.GetItemText(0, 1) == "2.0 KB"
    assert dlg._list.GetItemText(0, 2) == "Available"


def test_reload_with_no_artifacts_announces_empty(dlg, provider: _FakeProvider) -> None:
    provider.artifacts = []
    dlg._reload()
    assert dlg._list.GetItemCount() == 0
    assert "no artifacts" in dlg.announcements[-1].lower()


def test_reload_error_sets_status_and_reenables_buttons(dlg, provider: _FakeProvider) -> None:
    provider.raise_on_fetch = GitHubItemsError("boom")
    dlg._reload()
    assert "boom" in dlg._status.GetLabel()
    assert dlg._refresh_btn.IsEnabled()


# ---------------------------------------------------------------------------
# Download gating
# ---------------------------------------------------------------------------


def test_download_selected_with_no_selection_announces(dlg) -> None:
    dlg._on_download_selected(None)
    assert "Select an artifact" in dlg.announcements[-1]


def test_download_all_with_no_artifacts_announces(dlg) -> None:
    dlg._artifacts = []
    dlg._on_download_all(None)
    assert "No artifacts" in dlg.announcements[-1]


def test_download_refuses_when_every_artifact_is_expired(dlg, provider: _FakeProvider) -> None:
    expired = GitHubArtifact(
        id=2, name="expired-one", size_bytes=10, expired=True, archive_download_url="https://x"
    )
    dlg._download([expired])
    assert "expired" in dlg.announcements[-1].lower()
    assert provider.downloaded == []


# ---------------------------------------------------------------------------
# Download flow (folder-picker and overwrite-confirmation seams stubbed,
# matching GitHubItemsDialog's _show_modal precedent)
# ---------------------------------------------------------------------------


def test_download_selected_writes_the_file(dlg, provider: _FakeProvider, tmp_path: Path) -> None:
    dlg._reload()
    dlg._list.Select(0)
    dlg._choose_download_folder = lambda: tmp_path
    dlg._on_download_selected(None)

    assert provider.downloaded == [("build-output", tmp_path / "build-output.zip")]
    assert (tmp_path / "build-output.zip").read_bytes() == b"zip"
    assert "Downloaded 1 artifact" in dlg.announcements[-1]


def test_download_cancelled_folder_picker_does_nothing(
    dlg, provider: _FakeProvider, tmp_path: Path
) -> None:
    dlg._reload()
    dlg._list.Select(0)
    dlg._choose_download_folder = lambda: None
    dlg._on_download_selected(None)

    assert provider.downloaded == []


def test_download_existing_file_prompts_overwrite_and_honors_decline(
    dlg, provider: _FakeProvider, tmp_path: Path
) -> None:
    (tmp_path / "build-output.zip").write_bytes(b"stale")
    dlg._reload()
    dlg._list.Select(0)
    dlg._choose_download_folder = lambda: tmp_path
    confirms: list[str] = []

    def _decline(names: str) -> bool:
        confirms.append(names)
        return False

    dlg._confirm_overwrite = _decline
    dlg._on_download_selected(None)

    assert confirms == ["build-output"]
    assert provider.downloaded == []
    assert (tmp_path / "build-output.zip").read_bytes() == b"stale"


def test_download_existing_file_overwrite_confirmed_replaces_it(
    dlg, provider: _FakeProvider, tmp_path: Path
) -> None:
    (tmp_path / "build-output.zip").write_bytes(b"stale")
    dlg._reload()
    dlg._list.Select(0)
    dlg._choose_download_folder = lambda: tmp_path
    dlg._confirm_overwrite = lambda _names: True
    dlg._on_download_selected(None)

    assert provider.downloaded == [("build-output", tmp_path / "build-output.zip")]
    assert (tmp_path / "build-output.zip").read_bytes() == b"zip"


def test_download_partial_failure_is_reported(dlg, provider: _FakeProvider, tmp_path: Path) -> None:
    provider.artifacts = [
        GitHubArtifact(
            id=1, name="ok-one", size_bytes=4, expired=False, archive_download_url="https://x"
        ),
        GitHubArtifact(
            id=2, name="bad-one", size_bytes=4, expired=False, archive_download_url="https://x"
        ),
    ]
    provider.raise_on_download["bad-one"] = GitHubItemsError("network gone")
    dlg._reload()
    dlg._choose_download_folder = lambda: tmp_path
    dlg._on_download_all(None)

    message = dlg.announcements[-1]
    assert "Downloaded 1" in message
    assert "bad-one" in message
    assert "network gone" in message


# ---------------------------------------------------------------------------
# Open in browser
# ---------------------------------------------------------------------------


def test_open_browser_button_disabled_without_a_run_url(wx_app, provider: _FakeProvider) -> None:
    frame = wx.Frame(None)
    dialog = ArtifactsDialog(
        frame, provider, repo="owner/repo", run_id=1, run_label="#1", run_url=""
    )
    assert not dialog._browser_btn.IsEnabled()


def test_open_browser_opens_the_run_url(dlg, monkeypatch: pytest.MonkeyPatch) -> None:
    opened: list[str] = []
    monkeypatch.setattr(
        "quill.ui.github_artifacts_dialog.webbrowser.open", lambda url: opened.append(url)
    )
    dlg._on_open_browser(None)
    assert opened == ["https://github.com/owner/repo/actions/runs/42"]
