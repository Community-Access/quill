"""The release-notes preview remains editable and never publishes."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
import wx

from quill.core.github.release_notes import GitHubReleaseNotesDraft
from quill.ui.github_release_notes_dialog import GitHubReleaseNotesDialog
from tests.wx_session import patch_call_after, shared_wx_app


@pytest.fixture(scope="module")
def wx_app():
    app = shared_wx_app()
    yield app
    app.Destroy()


def test_release_notes_preview_uses_explicit_range_and_stays_local(wx_app, monkeypatch) -> None:
    calls: list[dict[str, str]] = []

    def generate(_repo: str, **kwargs: str) -> GitHubReleaseNotesDraft:
        calls.append(kwargs)
        return GitHubReleaseNotesDraft(
            target_tag=kwargs["target_tag"],
            previous_tag=kwargs["previous_tag"],
            target_commitish=kwargs.get("target_commitish", ""),
            name="Version 2",
            body="## Changes\n- Fixed a bug",
        )

    provider = SimpleNamespace(generate_release_notes=generate)
    frame = wx.Frame(None)
    dialog = GitHubReleaseNotesDialog(frame, provider, "owner/repo", previous_tag="v1.9")

    class _SyncThread:
        def __init__(self, *, target, daemon) -> None:
            self._target = target

        def start(self) -> None:
            self._target()

    monkeypatch.setattr("quill.ui.github_release_notes_dialog.threading.Thread", _SyncThread)
    patch_call_after(monkeypatch)
    try:
        dialog._target.SetValue("v2.0")
        dialog._target_commitish.SetValue("main")
        dialog._on_generate(None)

        assert calls == [
            {
                "target_tag": "v2.0",
                "previous_tag": "v1.9",
                "target_commitish": "main",
            }
        ]
        assert dialog._name.GetValue() == "Version 2"
        assert "Fixed a bug" in dialog._body.GetValue()
        assert "nothing was published" in dialog._status.GetLabel()
        assert dialog._copy_btn.IsEnabled()
    finally:
        dialog.dialog.Destroy()
        frame.Destroy()


def test_release_notes_preview_rejects_missing_range_before_network(wx_app) -> None:
    frame = wx.Frame(None)
    calls: list[object] = []
    provider = SimpleNamespace(
        generate_release_notes=lambda *_args, **_kwargs: calls.append("called")
    )
    dialog = GitHubReleaseNotesDialog(frame, provider, "owner/repo")
    try:
        dialog._on_generate(None)
        assert calls == []
        assert "both tags" in dialog._status.GetLabel()
    finally:
        dialog.dialog.Destroy()
        frame.Destroy()
