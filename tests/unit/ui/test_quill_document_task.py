"""Do a Document Task in QUILL: the shared handler, run through QUILL's adapter.

QUILL has no command of its own (main_frame_hosted_ai.py); this calls the
shared handler on an object shaped like MainFrame -- a controller whose window
is ``frame`` and whose document is ``editor`` -- and checks that QUILL's own
frame, editor and command registry are what the task is given.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.ui.main_frame_hosted_ai import HostedAiCommandsMixin


class _Frame:
    pass


class _Commands:
    def __init__(self) -> None:
        self.ran: list[str] = []

    def run(self, command_id: str) -> None:
        self.ran.append(command_id)


class _Service:
    connection_in_use = "codex"

    def can_do(self, _capability: str) -> bool:
        return True

    def agent_harness(self, connection: str) -> Any:
        return ("harness", connection)


class _Quill(HostedAiCommandsMixin):
    def __init__(self) -> None:
        self.frame = _Frame()
        self.editor = object()
        self.commands = _Commands()
        self.said: list[str] = []
        self._safe_mode = False

    def _announce(self, message: str) -> None:
        self.said.append(message)

    def _ai_service(self) -> Any:
        return _Service()

    def _ai_switched_on(self) -> bool:
        return True


@pytest.fixture
def opened(monkeypatch):
    import quill.ui.agent_window as module

    made: dict[str, Any] = {}

    class _Window:
        def __init__(self, parent, hooks) -> None:
            made["parent"], made["hooks"] = parent, hooks

    monkeypatch.setattr(module, "AgentWindow", _Window)
    monkeypatch.setattr(HostedAiCommandsMixin, "_open_ai_window", lambda self, name, build: build())
    return made


def test_quill_opens_the_task_on_its_own_frame_with_the_connection_in_use(opened) -> None:
    quill = _Quill()

    quill.cmd_ai_task()

    assert opened["parent"] is quill.frame
    assert opened["hooks"].connection == "codex"
    assert quill.said == []


def test_quills_task_tools_read_its_editor_and_run_its_registry(opened) -> None:
    quill = _Quill()
    quill.cmd_ai_task()
    host = opened["hooks"].make_host(object(), lambda _line: None)

    assert host._control() is quill.editor
    quill._ai_run_command("format.bold")
    assert quill.commands.ran == ["format.bold"]


def test_quills_propose_alt_text_fills_in_the_request(opened) -> None:
    """codex.md 6.4: QUILL reaches the same shared handler as QUILL Lite."""
    from quill.core.ai.doc_images import ALT_TEXT_INSTRUCTION

    quill = _Quill()
    quill.cmd_ai_alt_text()

    assert opened["parent"] is quill.frame
    assert opened["hooks"].starter == ALT_TEXT_INSTRUCTION
    assert quill.said == []


def test_a_task_on_a_connection_that_sees_gets_the_picture_tool(opened, tmp_path) -> None:
    from quill.core.ai.approvals import UiThreadBridge

    quill = _Quill()
    quill.document = type("Doc", (), {"path": tmp_path / "trip.md"})()
    loader = quill._ai_doc_pictures(UiThreadBridge(lambda fn: fn()))
    assert callable(loader)
    assert quill._ai_document_path() == tmp_path / "trip.md"
    from quill.core.ai.doc_images import list_document_images

    image = list_document_images("![](https://example.com/a.png)")[0]
    assert "not on this computer" in loader(image)  # a web address is never fetched
