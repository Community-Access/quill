"""The Lite command opens the shared GitHub Items viewer through its gates."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from quill.apps.lite_window_tools import DocumentToolsMixin


def test_lite_github_workbench_uses_shared_viewer_and_closes_provider(monkeypatch) -> None:
    calls: list[object] = []
    host = SimpleNamespace(
        app=SimpleNamespace(safe_mode=False),
        path=Path("notes.md"),
        _announce=lambda message: calls.append(("announce", message)),
        _open_github_file_reference=lambda _url: None,
    )

    class _Provider:
        def __init__(self, *, token=None) -> None:
            calls.append(("provider", token))

        def close(self) -> None:
            calls.append("closed")

    class _Dialog:
        def __init__(self, _parent, _provider, *, initial_repo="", **_kwargs) -> None:
            calls.append(("viewer", initial_repo))

        def show(self) -> None:
            calls.append("shown")

    monkeypatch.setattr("quill.core.github.github_provider.require_pygithub", lambda: None)
    monkeypatch.setattr("quill.core.github.consent.load_github_consent_complete", lambda: True)
    monkeypatch.setattr("quill.core.github.token_store.load_github_token", lambda: "secret")
    monkeypatch.setattr(
        "quill.core.github.local_repo.detect_github_repo", lambda _path: "owner/repo"
    )
    monkeypatch.setattr("quill.core.github.items_provider.GitHubItemsProvider", _Provider)
    monkeypatch.setattr("quill.ui.github_items_dialog.GitHubItemsDialog", _Dialog)

    DocumentToolsMixin.cmd_github_workbench(host)

    assert calls == [("provider", "secret"), ("viewer", "owner/repo"), "shown", "closed"]


def test_lite_github_workbench_refuses_safe_mode_before_network(monkeypatch) -> None:
    calls: list[str] = []
    host = SimpleNamespace(app=SimpleNamespace(safe_mode=True), path=None)
    monkeypatch.setattr(
        "quill.core.github.github_provider.require_pygithub",
        lambda: calls.append("dependency check"),
    )
    monkeypatch.setattr(
        "quill.apps.lite_window_tools.show_message_box",
        lambda *_args: calls.append("message"),
    )

    DocumentToolsMixin.cmd_github_workbench(host)

    assert calls == ["message"]
