"""Speakers, Sections and Summary, QUILL Transcribe's agent task (codex.md 6.6).

The command, called for real on a real QUILL Transcribe window with the agent
window patched where the shared opener imports it. Then both tools through a
real ``FamilyToolRegistry``: the read answers without a question; the write
asks with one exact sentence, shows the whole text, and changes nothing when
refused or not applied. Only text is involved: no audio is ever read.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.apps.transcribe_ai_task import (
    CHANGE_LABEL,
    SPEAKERS_AND_SECTIONS,
    speaker_labels,
    transcribe_task_tools,
)
from quill.core.ai.activity_log import ActivityLog
from quill.core.ai.approvals import ApprovalChoice
from quill.core.ai.family_tools import FamilyToolRegistry
from quill.core.ai.permissions import PermissionBroker, RiskLevel
from quill.core.ai.tool_gateway import AgentIdentity

wx = pytest.importorskip("wx")

_DIARIZED = (
    "Speaker 1 [00:00:01]: Thanks, Ann, for joining.\n"
    "Speaker 2 [00:00:04]: Glad to. Bo will send the budget by Friday.\n"
    "Speaker 1 [00:00:09]: Good."
)

# --------------------------------------------------------------------------- #
# The command, on a real QUILL Transcribe window
# --------------------------------------------------------------------------- #


class _Window:
    last: dict | None = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        type(self).last = {"args": args, "kwargs": kwargs}

    def Show(self):  # noqa: N802 - wx API shape
        pass

    def Raise(self):  # noqa: N802 - wx API shape
        pass

    def SetFocus(self):  # noqa: N802 - wx API shape
        pass

    def Bind(self, *_args: Any, **_kwargs: Any):  # noqa: N802 - wx API shape
        pass


class _Service:
    signed_in = True
    direct = True

    def __init__(self, connection: str, *, tools: bool) -> None:
        self.connection_in_use = connection
        self.tools = tools
        self.harnesses: list[str] = []

    def can_do(self, capability: str) -> bool:
        return capability != "agent_tools" or self.tools

    def needs_label(self, capability: str) -> str:
        return "" if self.can_do(capability) else "(needs Copilot or Codex)"

    def agent_harness(self, connection: str) -> object:
        self.harnesses.append(connection)
        return object()

    def capability_offer(self, capability: str) -> Any:
        from quill.core.ai.connection_caps import SwitchOffer

        return SwitchOffer(
            "Agent tasks need a connection that runs tasks. My GitHub Copilot can. "
            "Switch to it and ask?",
            target="copilot",
        )


@pytest.fixture
def agent_window(monkeypatch):
    import quill.ui.agent_window as module

    cls = type("AgentWindow", (_Window,), {"last": None})
    monkeypatch.setattr(module, "AgentWindow", cls)
    return cls


@pytest.fixture
def transcribe(quill_data_dir: Path, wx_session_app, closed_machine_doors, monkeypatch):
    from quill.apps.transcribe import QuillTranscribeFrame
    from quill.ui.dialog_contract import set_transition_announcement_policy

    frame = QuillTranscribeFrame()
    said: list[str] = []
    frame._announce = lambda message, **_kw: said.append(str(message))
    frame.said = said
    monkeypatch.setattr(type(frame), "_show_ai_window", lambda self, window: None)
    try:
        yield frame
    finally:
        frame._close_review()
        frame._shut_down()
        set_transition_announcement_policy(None)
        frame.frame.Destroy()


def test_on_copilot_the_task_opens_on_the_transcript_with_a_starter(
    transcribe, agent_window, monkeypatch
) -> None:
    service = _Service("copilot", tools=True)
    monkeypatch.setattr(transcribe, "_ai_service", lambda: service)
    transcribe._last_transcript = ("Board meeting", _DIARIZED)

    (lambda w: w.cmd_ai_task())(transcribe)

    assert service.harnesses == ["copilot"]
    hooks = agent_window.last["args"][1]
    assert hooks.title == "Speakers, Sections and Summary"
    assert hooks.starter.startswith("Name the speakers, add section headings")
    assert "never your voice" in hooks.instruction_help
    runner = hooks.make_runner(object(), SimpleNamespace(on_ui=lambda fn, default=None: fn()))
    assert runner.spec is SPEAKERS_AND_SECTIONS
    facts = runner.context()
    assert "Transcript: the transcript Board meeting, 23 words." in facts
    assert "Speaker labels in it: Speaker 1, Speaker 2." in facts
    assert [t.name for t in runner.tools()] == [
        "transcribe.read_transcript",
        "transcribe.write_sections",
    ]
    assert transcribe.said == []


def test_on_a_connection_without_agent_tools_it_sends_nothing(
    transcribe, agent_window, monkeypatch
) -> None:
    import quill.ui.hosted_ai_connections as connections

    service = _Service("free", tools=False)
    monkeypatch.setattr(transcribe, "_ai_service", lambda: service)
    asked: list[str] = []
    monkeypatch.setattr(
        connections, "ask_yes_no", lambda _p, sentence, **_kw: asked.append(sentence) or False
    )

    (lambda w: w.cmd_ai_task())(transcribe)

    assert asked and asked[0].startswith("Agent tasks need a connection that runs tasks.")
    assert agent_window.last is None
    assert service.harnesses == []


def test_safe_mode_refuses_the_task(transcribe, agent_window) -> None:
    transcribe._safe_mode = True

    (lambda w: w.cmd_ai_task())(transcribe)

    assert agent_window.last is None
    assert transcribe.said == ["AI is off in Safe Mode."]


def test_the_row_is_in_the_ai_menu_on_ctrl_f3_and_registered(transcribe) -> None:
    bar = transcribe.frame.GetMenuBar()
    menu = bar.GetMenu(bar.FindMenu("AI"))
    labels = [i.GetItemLabel() for i in menu.GetMenuItems() if not i.IsSeparator()]
    task = next(label for label in labels if label.startswith("Sp&eakers"))
    assert task.endswith("\tCtrl+F3")
    assert transcribe.commands.get("tools.hosted_ai_task") is not None


# --------------------------------------------------------------------------- #
# The tools, through a real registry
# --------------------------------------------------------------------------- #


class _Approver:
    def __init__(self, choice: ApprovalChoice) -> None:
        self.choice = choice
        self.asked: list[str] = []

    def ask(self, tool, summary: str) -> ApprovalChoice:
        self.asked.append(summary)
        return self.choice


class _Ctx:
    def __init__(self, apply: bool = True) -> None:
        self.apply = apply
        self.previews: list[tuple[str, str]] = []

    def on_ui(self, fn, default=None):
        return fn()

    def preview(self, title: str, text: str) -> bool:
        self.previews.append((title, text))
        return self.apply

    def note(self, text: str) -> None:
        pass


class _Conversation:
    def __init__(self, text: str) -> None:
        self.session = SimpleNamespace(current=text)
        self.applied: list[tuple[str, str]] = []

    def apply(self, label: str, text: str) -> str:
        self.applied.append((label, text))
        self.session.current = text
        return "changed"


class _Desk:
    def __init__(self, open_text: str | None = None) -> None:
        self.frame = (
            SimpleNamespace(conversation=_Conversation(open_text))
            if open_text is not None
            else None
        )
        self.opened: list[str] = []

    def open(self, text: str) -> None:
        self.opened.append(text)
        self.frame = SimpleNamespace(conversation=_Conversation(text))


def _host(tmp_path: Path, *, review: str | None = None, transcript: str = _DIARIZED) -> Any:
    desk = _Desk(review)
    host = SimpleNamespace(
        _review=desk,
        _last_transcript=("Board meeting", transcript),
        _dictation=None,
        _review_rescue_path=lambda: tmp_path / "rescue.json",
    )
    host._review_desk = lambda: desk
    return host


def _registry(host: Any, approver: _Approver, ctx: _Ctx) -> FamilyToolRegistry:
    registry = FamilyToolRegistry(
        PermissionBroker(),
        ActivityLog(),
        AgentIdentity("transcribe-speakers-sections", RiskLevel.LOW),
        app_scope="transcribe",
    )
    registry.register_app("transcribe", transcribe_task_tools(host, ctx))
    registry.gate.begin_task(approver)
    return registry


_WRITE_QUESTION = (
    "Write the transcript with speakers named, section headings, a summary and an "
    "action list into Review Dictation."
)
_NEW = "# Welcome\nAnn: Thanks for joining.\n\n# Summary\nBudget by Friday.\n\n# Actions\n- Bo"


def test_speaker_labels_reads_diarized_and_named_turns() -> None:
    assert speaker_labels(_DIARIZED) == ["Speaker 1", "Speaker 2"]
    assert speaker_labels("Ann [00:00:01]: Hi.\nSpeaker 3: Yes.") == ["Ann", "Speaker 3"]
    assert speaker_labels("Just some words.\nNo labels: here") == []


def test_read_transcript_is_a_read_with_the_speaker_labels(tmp_path) -> None:
    approver = _Approver(ApprovalChoice.DENY)
    registry = _registry(_host(tmp_path), approver, _Ctx())

    result = registry.call("transcribe_read_transcript", {})

    assert result.ok
    lines = result.text.splitlines()
    assert lines[0] == "From the transcript Board meeting."
    assert lines[1] == "Speaker labels from diarization: Speaker 1, Speaker 2."
    assert lines[3] == "Speaker 1 [00:00:01]: Thanks, Ann, for joining."
    assert approver.asked == []


def test_an_open_review_is_read_first(tmp_path) -> None:
    registry = _registry(
        _host(tmp_path, review="Dictated words."), _Approver(ApprovalChoice.DENY), _Ctx()
    )

    result = registry.call("transcribe_read_transcript", {})

    assert result.text.splitlines()[0] == "From the words in Review Dictation."
    assert result.text.endswith("Dictated words.")


def test_nothing_to_read_says_how_to_get_a_transcript(tmp_path) -> None:
    registry = _registry(_host(tmp_path, transcript=""), _Approver(ApprovalChoice.DENY), _Ctx())

    result = registry.call("transcribe_read_transcript", {})

    assert not result.ok
    assert "There is no transcript here yet." in result.text


def test_write_asks_previews_then_opens_review_on_the_transcript_as_one_change(tmp_path) -> None:
    host = _host(tmp_path)
    approver = _Approver(ApprovalChoice.ONCE)
    ctx = _Ctx(apply=True)
    registry = _registry(host, approver, ctx)
    registry.call("transcribe_read_transcript", {})

    result = registry.call("transcribe_write_sections", {"text": _NEW})

    assert approver.asked == [_WRITE_QUESTION]
    assert ctx.previews == [(f"{CHANGE_LABEL}, for Review Dictation", _NEW)]
    assert result.ok and "Undo Change" in result.text
    assert host._review.opened == [_DIARIZED]  # the words as they were come first
    assert host._review.frame.conversation.applied == [(CHANGE_LABEL, _NEW)]


def test_write_goes_into_an_open_review(tmp_path) -> None:
    host = _host(tmp_path, review="Dictated words.")
    registry = _registry(host, _Approver(ApprovalChoice.ONCE), _Ctx(apply=True))

    result = registry.call("transcribe_write_sections", {"text": _NEW})

    assert result.ok
    assert host._review.opened == []
    assert host._review.frame.conversation.applied == [(CHANGE_LABEL, _NEW)]


def test_write_refused_writes_nothing_and_shows_nothing(tmp_path) -> None:
    host = _host(tmp_path)
    ctx = _Ctx(apply=True)
    registry = _registry(host, _Approver(ApprovalChoice.DENY), ctx)

    result = registry.call("transcribe_write_sections", {"text": _NEW})

    assert not result.ok
    assert ctx.previews == []
    assert host._review.opened == [] and host._review.frame is None
    assert not registry.mutated()


def test_write_not_applied_in_the_preview_writes_nothing(tmp_path) -> None:
    host = _host(tmp_path)
    registry = _registry(host, _Approver(ApprovalChoice.ONCE), _Ctx(apply=False))

    result = registry.call("transcribe_write_sections", {"text": _NEW})

    assert not result.ok
    assert result.text.endswith("The person did not apply it.")
    assert host._review.opened == []


def test_write_never_replaces_words_kept_from_last_time(tmp_path) -> None:
    from quill.core.windows_dictation.review_session import ReviewSession, save_rescue

    host = _host(tmp_path)
    save_rescue(tmp_path / "rescue.json", ReviewSession("Kept words."))
    registry = _registry(host, _Approver(ApprovalChoice.ONCE), _Ctx(apply=True))

    result = registry.call("transcribe_write_sections", {"text": _NEW})

    assert not result.ok
    assert "kept from last time" in result.text
    assert host._review.opened == []


def test_the_review_conversation_applies_a_change_undo_takes_back() -> None:
    from quill.core.windows_dictation.review_conversation import ReviewConversation
    from quill.core.windows_dictation.review_session import ReviewSession

    shown: list[str] = []
    port = SimpleNamespace(
        say=lambda _t: pytest.fail("an applied change says nothing"),
        status=lambda _t: None,
        show_text=shown.append,
        show_changes=lambda _t: None,
        mute=lambda _t: None,
    )
    conversation = ReviewConversation(ReviewSession("Plain words."), port, ai=None)

    conversation.apply(CHANGE_LABEL, _NEW)
    assert conversation.session.current == _NEW and shown[-1] == _NEW
    conversation.session.undo_revision()
    assert conversation.session.current == "Plain words."
