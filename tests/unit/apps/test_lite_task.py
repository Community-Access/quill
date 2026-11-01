"""Do a Document Task in QUILL Lite (codex.md 6.2): the handler, called for real.

Every handler is **called** in a lambda: ``quill.tools.lite_command_coverage``
finds coverage by walking the AST for real calls. The agent window is patched
where the shared mixin looks it up, ``quill.ui.agent_window``; QUILL runs the
same handler through its adapter (``test_main_frame_hosted_ai.py``).
"""

from __future__ import annotations

from typing import Any

import pytest


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


@pytest.fixture
def agent_window(monkeypatch):
    import quill.ui.agent_window as module

    cls = type("AgentWindow", (_Window,), {"last": None})
    monkeypatch.setattr(module, "AgentWindow", cls)
    return cls


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

    def choose(self, connection: str) -> bool:
        self.connection_in_use = connection
        self.tools = True
        return True


def test_on_copilot_the_task_window_opens_on_the_connection_in_use(
    lite_window, agent_window, monkeypatch
):
    win = lite_window("Some text.")
    service = _Service("copilot", tools=True)
    monkeypatch.setattr(win, "_ai_service", lambda: service)

    (lambda w: w.cmd_ai_task())(win)

    assert service.harnesses == ["copilot"]
    hooks = agent_window.last["args"][1]
    assert hooks.connection == "copilot"
    assert win.announcements == []  # the reader says the window; the app says nothing


def test_on_the_free_ai_it_sends_nothing_and_offers_the_switch(
    lite_window, agent_window, monkeypatch
):
    import quill.ui.hosted_ai_connections as connections

    win = lite_window("Some text.")
    service = _Service("free", tools=False)
    monkeypatch.setattr(win, "_ai_service", lambda: service)
    asked: list[str] = []
    monkeypatch.setattr(
        connections, "ask_yes_no", lambda _p, sentence, default_yes: asked.append(sentence)
    )

    (lambda w: w.cmd_ai_task())(win)

    assert asked and asked[0].startswith("Agent tasks need a connection that runs tasks.")
    assert agent_window.last is None
    assert service.harnesses == []


def test_the_menu_row_says_what_it_needs_on_the_free_ai(lite_window, monkeypatch):
    win = lite_window("Some text.")
    monkeypatch.setattr(win, "_ai_service", lambda: _Service("free", tools=False))

    label = win._ai_gated_label("cmd_ai_task", "&Do a Document Task...")

    assert label == "&Do a Document Task (needs Copilot or Codex)..."


def test_a_task_runs_a_lite_command_through_the_parity_table(lite_window, monkeypatch):
    win = lite_window("Some text.")
    ran: list[str] = []
    monkeypatch.setattr(win, "cmd_bold", lambda: ran.append("bold"))

    win._ai_run_command("format.bold")  # COMMAND_EQUIVALENTS: cmd_bold
    assert ran == ["bold"]


def test_safe_mode_says_ai_is_off_and_opens_nothing(lite_window, agent_window, monkeypatch):
    win = lite_window("Some text.")
    monkeypatch.setattr(win, "_ai_safe_mode", lambda: True)

    (lambda w: w.cmd_ai_task())(win)

    assert agent_window.last is None
    assert "Safe Mode" in win.announcements[-1]


def test_propose_alt_text_opens_the_task_with_the_request_filled_in(
    lite_window, agent_window, monkeypatch
):
    """codex.md 6.4: the same window, the alt-text request typed in, nothing sent."""
    from quill.core.ai.doc_images import ALT_TEXT_INSTRUCTION

    win = lite_window("![](a.png)")
    service = _Service("copilot", tools=True)
    monkeypatch.setattr(win, "_ai_service", lambda: service)

    (lambda w: w.cmd_ai_alt_text())(win)

    hooks = agent_window.last["args"][1]
    assert hooks.starter == ALT_TEXT_INSTRUCTION
    assert hooks.title == "Do a Document Task"
    assert win.announcements == []


def test_propose_alt_text_on_the_free_ai_sends_nothing(lite_window, agent_window, monkeypatch):
    import quill.ui.hosted_ai_connections as connections

    win = lite_window("![](a.png)")
    monkeypatch.setattr(win, "_ai_service", lambda: _Service("free", tools=False))
    monkeypatch.setattr(connections, "ask_yes_no", lambda *_a, **_k: False)

    (lambda w: w.cmd_ai_alt_text())(win)

    assert agent_window.last is None
    label = win._ai_gated_label("cmd_ai_alt_text", "Propose Alt &Text...")
    assert label == "Propose Alt &Text (needs Copilot or Codex)..."
