"""Companion wiring: agent spec + UI-thread-marshalling editor host.

These exercise the wx-free parts of ``ui/agent_editor_host`` (the module imports
wx only lazily inside functions), with a fake wx whose ``IsMainThread`` is True so
``_run_on_ui`` calls inline.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from quill.core.ai.permissions import Decision, PermissionCategory
from quill.ui.agent_editor_host import _companion_agent, _CompanionEditorHost


class FakeWx:
    @staticmethod
    def IsMainThread() -> bool:
        return True


@dataclass
class FakeEditor:
    value: str = "hello world"
    selection: str = ""
    replaced: list[str] = field(default_factory=list)

    def GetValue(self) -> str:
        return self.value

    def GetStringSelection(self) -> str:
        return self.selection


@dataclass
class FakeController:
    editor: FakeEditor = field(default_factory=FakeEditor)
    statuses: list[str] = field(default_factory=list)
    undo_snapshots: list[str] = field(default_factory=list)
    diff_calls: list[tuple[str, str]] = field(default_factory=list)
    approve: bool = True

    def _set_status(self, message: str) -> None:
        self.statuses.append(message)

    def _record_persistent_undo_state(self, text: str) -> None:
        self.undo_snapshots.append(text)

    def _ai_replace_selection(self, text: str) -> None:
        self.editor.replaced.append(text)

    def open_ai_diff_review(self, original, revised, on_apply) -> None:
        self.diff_calls.append((original, revised))
        if self.approve:
            on_apply(revised)


def test_companion_agent_reads_allowed_edits_previewed() -> None:
    agent = _companion_agent()
    overrides = agent.overrides_map()
    assert overrides[PermissionCategory.READ_DOCUMENT] is Decision.ALLOW
    assert overrides[PermissionCategory.READ_SELECTION] is Decision.ALLOW
    assert overrides[PermissionCategory.MODIFY_SELECTION] is Decision.PREVIEW_REQUIRED
    assert overrides[PermissionCategory.MODIFY_DOCUMENT] is Decision.PREVIEW_REQUIRED
    assert agent.id == "quill-companion"


def test_host_reads_pass_through() -> None:
    controller = FakeController(editor=FakeEditor(value="doc text", selection="sel"))
    host = _CompanionEditorHost(controller, FakeWx())
    assert host.get_document() == "doc text"
    assert host.get_selection() == "sel"


def test_preview_diff_reviews_without_mutating() -> None:
    controller = FakeController(approve=True)
    host = _CompanionEditorHost(controller, FakeWx())

    class Review:
        original = "old"

        def accept_all(self) -> str:
            return "new"

    approved = host.preview_diff(Review())

    assert approved is True
    assert controller.diff_calls == [("old", "new")]
    # preview only reviews; the gateway applies on its next step
    assert controller.editor.replaced == []


def test_preview_diff_declined_returns_false() -> None:
    controller = FakeController(approve=False)
    host = _CompanionEditorHost(controller, FakeWx())

    class Review:
        original = "old"

        def accept_all(self) -> str:
            return "new"

    assert host.preview_diff(Review()) is False


def test_apply_replacement_uses_controller_primitive() -> None:
    controller = FakeController()
    host = _CompanionEditorHost(controller, FakeWx())
    host.create_undo_checkpoint("Edit")
    host.apply_replacement("fixed")
    assert controller.editor.replaced == ["fixed"]
    assert controller.undo_snapshots == ["hello world"]
