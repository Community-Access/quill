"""MainFrameEditorHost adapter: delegates to MainFrame primitives correctly."""

from __future__ import annotations

from dataclasses import dataclass, field

from quill.core.ai.context_builder import ContextScope
from quill.core.ai.diff_review import build_diff_review
from quill.core.ai.harness import AgentSpec
from quill.core.ai.permissions import Decision, PermissionCategory
from quill.ui.agent_editor_host import (
    _WEAK_MODEL_MAX_STEPS,
    MainFrameEditorHost,
    _apply_result,
    _classify,
    _companion_loop_budget,
    _effective_scope,
)


@dataclass
class FakeEditor:
    value: str = "the cat sat on the mat"
    selection: str = "the cat sat on the mat"

    def GetValue(self) -> str:
        return self.value

    def GetStringSelection(self) -> str:
        return self.selection


def test_companion_loop_budget_degrades_small_model(monkeypatch):
    import quill.core.assistant_ai as aai
    from quill.core.ai.tool_loop import MAX_STEPS

    class _Conn:
        def __init__(self, model):
            self.model = model

    # A tiny model gets the near-single-shot budget and a simplified engine label.
    monkeypatch.setattr(aai, "load_assistant_connection_settings", lambda: _Conn("llama3.2:1b"))
    steps, engine = _companion_loop_budget()
    assert steps == _WEAK_MODEL_MAX_STEPS
    assert "small model" in engine.lower()

    # A capable model keeps the full loop budget.
    monkeypatch.setattr(
        aai, "load_assistant_connection_settings", lambda: _Conn("claude-haiku-4-5")
    )
    steps, engine = _companion_loop_budget()
    assert steps == MAX_STEPS
    assert engine == "Native (QUILL)"


def test_companion_loop_budget_never_raises(monkeypatch):
    import quill.core.assistant_ai as aai
    from quill.core.ai.tool_loop import MAX_STEPS

    def _boom():
        raise RuntimeError("no config")

    monkeypatch.setattr(aai, "load_assistant_connection_settings", _boom)
    steps, engine = _companion_loop_budget()
    assert steps == MAX_STEPS and engine == "Native (QUILL)"


@dataclass
class FakeOutline:
    title: str


@dataclass
class FakeDoc:
    path: str | None = "notes.md"


@dataclass
class FakeController:
    """Stands in for MainFrame; records the primitive calls the host makes."""

    editor: FakeEditor = field(default_factory=FakeEditor)
    document: FakeDoc = field(default_factory=FakeDoc)
    frame: object = None
    replaced: list[str] = field(default_factory=list)
    inserted: list[str] = field(default_factory=list)
    doc_writes: list[str] = field(default_factory=list)
    checkpoints: list[str] = field(default_factory=list)
    statuses: list[str] = field(default_factory=list)
    commands_run: list[str] = field(default_factory=list)
    new_docs: list[str] = field(default_factory=list)
    diff_calls: list[tuple[str, str]] = field(default_factory=list)
    # Set by the test to simulate the user accepting hunks in the diff dialog.
    diff_accept_text: str | None = None

    def _selected_text(self) -> str:
        return self.editor.GetStringSelection()

    def _outline_entries(self):
        return [FakeOutline("Intro"), FakeOutline("Body")]

    def _record_persistent_undo_state(self, text: str) -> None:
        self.checkpoints.append(text)

    def _ai_replace_selection(self, text: str) -> None:
        self.replaced.append(text)

    def _ai_insert_text(self, text: str) -> None:
        self.inserted.append(text)

    def _ai_set_document_text(self, text: str) -> None:
        self.doc_writes.append(text)

    def _ai_open_new_document(self, text: str) -> None:
        self.new_docs.append(text)

    def _ai_run_command(self, command_id: str) -> None:
        self.commands_run.append(command_id)

    def _set_status(self, message: str) -> None:
        self.statuses.append(message)

    def open_ai_diff_review(self, original, revised, on_apply, *, title="Review AI Changes"):
        self.diff_calls.append((original, revised))
        if self.diff_accept_text is not None:
            on_apply(self.diff_accept_text)


def test_reads_delegate_to_editor() -> None:
    c = FakeController()
    host = MainFrameEditorHost(c)
    assert host.get_document() == "the cat sat on the mat"
    assert host.get_selection() == "the cat sat on the mat"
    assert host.get_outline() == ["Intro", "Body"]
    assert host.get_file_type() == "md"


def test_apply_replacement_without_preview_uses_real_path() -> None:
    c = FakeController()
    host = MainFrameEditorHost(c)
    host.create_undo_checkpoint("Writing Companion")
    host.apply_replacement("The cat curled up on the mat.")
    assert c.checkpoints == ["the cat sat on the mat"]
    assert c.replaced == ["The cat curled up on the mat."]


def test_insert_and_run_command_delegate() -> None:
    c = FakeController()
    host = MainFrameEditorHost(c)
    host.apply_insert("hello")
    host.run_command("file.save")
    host.announce("done")
    assert c.inserted == ["hello"]
    assert c.commands_run == ["file.save"]
    assert c.statuses == ["done"]


def test_preview_applies_accepted_hunks_and_suppresses_double_apply() -> None:
    # Simulate the user accepting the proposed text in the per-hunk dialog.
    c = FakeController(diff_accept_text="The cat curled up on the mat.")
    host = MainFrameEditorHost(c)
    review = build_diff_review("the cat sat on the mat", "The cat curled up on the mat.")

    applied = host.preview_diff(review)
    assert applied is True
    # The dialog was shown with original + accept_all proposed.
    assert c.diff_calls == [("the cat sat on the mat", "The cat curled up on the mat.")]
    # Applied the accepted text via the real replace path, with an undo checkpoint.
    assert c.replaced == ["The cat curled up on the mat."]
    assert len(c.checkpoints) == 1

    # The gateway's follow-up checkpoint + apply must NOT double-apply this turn.
    host.create_undo_checkpoint("Writing Companion")
    host.apply_replacement("The cat curled up on the mat.")
    assert c.replaced == ["The cat curled up on the mat."]  # unchanged
    assert len(c.checkpoints) == 1  # unchanged


def test_preview_declined_returns_false_and_applies_nothing() -> None:
    c = FakeController(diff_accept_text=None)  # user closes without applying
    host = MainFrameEditorHost(c)
    review = build_diff_review("a", "b")
    assert host.preview_diff(review) is False
    assert c.replaced == []
    assert c.checkpoints == []


def test_file_type_empty_when_no_path() -> None:
    c = FakeController(document=FakeDoc(path=None))
    assert MainFrameEditorHost(c).get_file_type() == ""


# -- scope/classify/apply broadening --------------------------------------


def _spec(scope: ContextScope, perms: dict[PermissionCategory, Decision]) -> AgentSpec:
    return AgentSpec(
        id="x",
        display_name="X",
        system_prompt="do",
        default_scope=scope,
        permission_overrides=tuple(perms.items()),
    )


def test_effective_scope_selection_and_document() -> None:
    c = FakeController()
    c.editor.value = "WHOLE DOCUMENT BODY"
    c.editor.selection = "sel"
    scope, err = _effective_scope(c, ContextScope.SELECTION)
    assert scope is ContextScope.SELECTION and err == ""
    scope, err = _effective_scope(c, ContextScope.FULL_DOCUMENT)
    assert scope is ContextScope.FULL_DOCUMENT and err == ""


def test_effective_scope_large_document_downgrades_to_summary() -> None:
    c = FakeController()
    c.editor.selection = ""
    c.editor.value = "word " * 5000  # over the full-document token limit
    scope, err = _effective_scope(c, ContextScope.FULL_DOCUMENT)
    assert scope is ContextScope.DOCUMENT_SUMMARY and err == ""


def test_effective_scope_errors() -> None:
    c = FakeController()
    c.editor.selection = "   "
    scope, err = _effective_scope(c, ContextScope.SELECTION)
    assert scope is None and "Select text" in err
    c.editor.value = "   "
    scope, err = _effective_scope(c, ContextScope.FULL_DOCUMENT)
    assert scope is None and "empty" in err
    scope, err = _effective_scope(c, ContextScope.WORKSPACE_SUMMARY)
    assert scope is None and "not supported" in err


def test_classify_document_selection_produce() -> None:
    doc_agent = _spec(
        ContextScope.FULL_DOCUMENT,
        {PermissionCategory.MODIFY_DOCUMENT: Decision.PREVIEW_REQUIRED},
    )
    sel_agent = _spec(
        ContextScope.SELECTION,
        {PermissionCategory.MODIFY_SELECTION: Decision.PREVIEW_REQUIRED},
    )
    produce_agent = _spec(ContextScope.DOCUMENT_SUMMARY, {})
    assert _classify(doc_agent) == ("document", "document")
    assert _classify(sel_agent) == ("selection", "selection")
    assert _classify(produce_agent) == ("produce", "selection")


class FakeGateway:
    def __init__(self) -> None:
        self.patches: list[tuple[str, str]] = []
        self.replacements: list[str] = []

    def apply_text_patch(self, original: str, proposed: str, *, label: str = "") -> bool:
        self.patches.append((original, proposed))
        return True

    def replace_selection(self, text: str, *, label: str = "") -> bool:
        self.replacements.append(text)
        return True


def test_apply_result_document_uses_patch() -> None:
    c = FakeController()
    c.editor.value = "original document"
    gw = FakeGateway()
    host = MainFrameEditorHost(c)
    agent = _spec(
        ContextScope.FULL_DOCUMENT, {PermissionCategory.MODIFY_DOCUMENT: Decision.PREVIEW_REQUIRED}
    )
    _apply_result(c, gw, host, agent, "document", "document", "revised document")
    assert gw.patches == [("original document", "revised document")]
    assert host._apply_mode == "document"


def test_apply_result_selection_uses_replace() -> None:
    c = FakeController()
    gw = FakeGateway()
    host = MainFrameEditorHost(c)
    agent = _spec(
        ContextScope.SELECTION, {PermissionCategory.MODIFY_SELECTION: Decision.PREVIEW_REQUIRED}
    )
    _apply_result(c, gw, host, agent, "selection", "selection", "new sel")
    assert gw.replacements == ["new sel"]


def test_apply_result_produce_opens_new_document() -> None:
    c = FakeController()
    gw = FakeGateway()
    host = MainFrameEditorHost(c)
    agent = _spec(ContextScope.DOCUMENT_SUMMARY, {})
    _apply_result(c, gw, host, agent, "produce", "selection", "a summary")
    assert c.new_docs == ["a summary"]
    assert gw.patches == [] and gw.replacements == []


def test_preview_document_mode_applies_whole_buffer() -> None:
    c = FakeController(diff_accept_text="revised whole doc")
    host = MainFrameEditorHost(c)
    host.set_apply_mode("document")
    review = build_diff_review("original doc", "revised whole doc")
    assert host.preview_diff(review) is True
    assert c.doc_writes == ["revised whole doc"]  # set_document, not replace_selection
    assert c.replaced == []
