"""Wiring + Safe Mode guard tests for the GitHub items viewer (#924).

Two layers, both display-free so they run in CI without a wx App:

1. Source-assertion that the command, menu item, binding, and feature map are
   wired (mirrors the pattern in ``test_main_frame_close_resilience.py`` --
   reading source keeps it deterministic and avoids constructing a MainFrame).
2. Behavioural test that Safe Mode refuses before any network/consent work, and
   that the current document's GitHub origin pre-fills the repository field.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.github.items_provider import GitHubItemsError
from quill.core.github.models import RemoteOrigin
from quill.ui.main_frame_github_items import GitHubItemsMixin

_UI = Path(__file__).resolve().parents[3] / "quill" / "ui"
_CORE = Path(__file__).resolve().parents[3] / "quill" / "core"


def _src(rel: str) -> str:
    return (Path(__file__).resolve().parents[3] / rel).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Source-assertion wiring
# ---------------------------------------------------------------------------


def test_command_registered_in_build_commands() -> None:
    src = _src("quill/ui/main_frame.py")
    assert '"file.open_github_items"' in src
    assert "self.open_github_items_viewer" in src


def test_mixin_in_base_classes() -> None:
    assert "GitHubItemsMixin" in _src("quill/ui/main_frame.py")


def test_menu_id_and_item_present() -> None:
    src = _src("quill/ui/main_frame_menu.py")
    assert "self._id_github_items = wx.NewIdRef()" in src
    assert '"file.open_github_items"' in src
    assert "GitHub &Items..." in src


def test_menu_bound_in_bind_github_menu() -> None:
    src = _src("quill/ui/main_frame_github.py")
    assert "self._id_github_items" in src
    assert "self.open_github_items_viewer()" in src


def test_feature_command_map_gates_on_github_remote() -> None:
    # The OFF-by-default core.github_remote feature gates the command, so a
    # release build keeps the viewer hidden until the feature is enabled.
    src = _src("quill/core/feature_command_map.py")
    assert '"file.open_github_items": "core.github_remote"' in src


# ---------------------------------------------------------------------------
# Safe Mode guard (no wx, no consent, no network)
# ---------------------------------------------------------------------------


class _StubMixin(GitHubItemsMixin):
    """A bare instance with stubbed collaborators for behavioural tests."""

    def __init__(self, *, safe_mode: bool) -> None:
        self._safe_mode = safe_mode
        self.shown_messages: list[tuple[str, str]] = []
        self.ensured_ready = False
        self.token_loaded = False
        self.announcements: list[str] = []

    # --- stubs for MainFrame collaborators ------------------------------
    class _wx:  # noqa: N801 - mimics the wx namespace surface used
        ICON_INFORMATION = 1
        OK = 4

    def _show_message_box(self, message: str, caption: str, _style: int) -> None:
        self.shown_messages.append((caption, message))

    def _ensure_github_ready(self) -> bool:
        self.ensured_ready = True
        return True

    def _announce(self, message: str) -> None:
        self.announcements.append(message)


def test_safe_mode_refuses_before_consent_or_network() -> None:
    stub = _StubMixin(safe_mode=True)
    stub.open_github_items_viewer()

    # The refuse path shows an info box and returns; it never reaches consent,
    # the token store, or any provider construction.
    assert stub.ensured_ready is False
    assert len(stub.shown_messages) == 1
    assert stub.shown_messages[0][0] == "GitHub Items"
    # The coded error surfaces a greppable QUILL-* code.
    assert "QUILL-GITHUB-ITEMS-ERROR" in stub.shown_messages[0][1]


def test_refuse_in_safe_mode_message_is_user_facing() -> None:
    # The same guard lives in the core provider; assert it raises with a code.
    with pytest.raises(GitHubItemsError, match="Safe Mode"):
        from quill.core.github.items_provider import refuse_in_safe_mode

        refuse_in_safe_mode(True)


# ---------------------------------------------------------------------------
# Initial-repo prefill from the current document's GitHub origin
# ---------------------------------------------------------------------------


class _OriginStub(_StubMixin):
    def __init__(self, *, safe_mode: bool, origins: dict, doc_path) -> None:
        super().__init__(safe_mode=safe_mode)
        self._origins = origins
        self.document = type("_Doc", (), {"path": doc_path})()

    def _gh_state(self):
        class _S:
            origins = self._origins

        return _S()


def test_initial_repo_prefilled_from_github_origin() -> None:
    origins = {
        "/local/docs/x.md": RemoteOrigin(
            "github", "github:alice", "owner/repo", "main", "docs/x.md", "sha", "url", "2026"
        )
    }
    stub = _OriginStub(safe_mode=False, origins=origins, doc_path="/local/docs/x.md")
    assert stub._github_items_initial_repo() == "owner/repo"


def test_initial_repo_empty_for_non_github_origin() -> None:
    origins = {
        "/local/docs/y.md": RemoteOrigin(
            "git", "git:bob", "owner/repo", "main", "y.md", "sha", "url", "2026"
        )
    }
    stub = _OriginStub(safe_mode=False, origins=origins, doc_path="/local/docs/y.md")
    assert stub._github_items_initial_repo() == ""


def test_initial_repo_empty_when_no_document_path() -> None:
    stub = _OriginStub(safe_mode=False, origins={}, doc_path=None)
    assert stub._github_items_initial_repo() == ""


def test_initial_repo_survives_missing_gh_state() -> None:
    # _gh_state must never crash the command; a broken state yields empty, not raise.
    class _Broken(_StubMixin):
        def __init__(self) -> None:
            super().__init__(safe_mode=False)

        def _gh_state(self):
            raise RuntimeError("boom")

    assert _Broken()._github_items_initial_repo() == ""
