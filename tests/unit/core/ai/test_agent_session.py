"""Unit tests for quill.core.ai.agent_session."""

from __future__ import annotations

import threading

import pytest

from quill.core.ai.agent_session import (
    AgentContext,
    AgentResult,
    AgentSessionAuthError,
    AgentSessionCancelledError,
    AgentSessionError,
    AgentStep,
    run_agent,
)
from quill.core.assistant_agents import build_agent_plan

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_conn() -> object:
    from quill.core.assistant_ai import AssistantConnectionSettings

    return AssistantConnectionSettings(provider="openai", model="gpt-4o-mini")


def _make_ctx(stop_event=None, on_progress=None) -> AgentContext:
    plan = build_agent_plan("summarize", selection_text="", document_text="Hello world.")
    assert plan is not None
    return AgentContext(
        plan=plan,
        connection=_make_conn(),
        api_key="test-key",
        stop_event=stop_event or threading.Event(),
        on_progress=on_progress,
    )


# ---------------------------------------------------------------------------
# AgentStep
# ---------------------------------------------------------------------------


def test_agent_step_is_frozen() -> None:
    s = AgentStep("label", "output")
    with pytest.raises((AttributeError, TypeError)):
        s.label = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# AgentResult
# ---------------------------------------------------------------------------


def test_agent_result_succeeded_when_output_present() -> None:
    r = AgentResult(plan_id="x", final_output="some text")
    assert r.succeeded is True


def test_agent_result_not_succeeded_when_cancelled() -> None:
    r = AgentResult(plan_id="x", final_output="text", cancelled=True)
    assert r.succeeded is False


def test_agent_result_not_succeeded_when_error() -> None:
    r = AgentResult(plan_id="x", final_output="text", error="oops")
    assert r.succeeded is False


def test_agent_result_not_succeeded_when_empty_output() -> None:
    r = AgentResult(plan_id="x", final_output="")
    assert r.succeeded is False


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------


def test_auth_error_is_agent_session_error() -> None:
    assert issubclass(AgentSessionAuthError, AgentSessionError)


def test_cancelled_error_is_agent_session_error() -> None:
    assert issubclass(AgentSessionCancelledError, AgentSessionError)


# ---------------------------------------------------------------------------
# AgentContext
# ---------------------------------------------------------------------------


def test_agent_context_is_cancelled_when_event_set() -> None:
    ev = threading.Event()
    ev.set()
    ctx = _make_ctx(stop_event=ev)
    assert ctx.is_cancelled() is True


def test_agent_context_not_cancelled_by_default() -> None:
    ctx = _make_ctx()
    assert ctx.is_cancelled() is False


# ---------------------------------------------------------------------------
# run_agent — mocked AI
# ---------------------------------------------------------------------------


def test_run_agent_returns_result(monkeypatch: pytest.MonkeyPatch) -> None:
    import quill.core.ai.agent_session as ag

    monkeypatch.setattr(ag, "generate_assistant_response", lambda *a, **kw: ("output text", None))
    ctx = _make_ctx()
    result = run_agent(ctx)
    assert result.succeeded
    assert result.final_output == "output text"
    assert len(result.steps) == 1
    assert result.steps[0].label == "Initial generation"


def test_run_agent_no_refine_gives_single_step(monkeypatch: pytest.MonkeyPatch) -> None:
    import quill.core.ai.agent_session as ag

    monkeypatch.setattr(ag, "generate_assistant_response", lambda *a, **kw: ("output", None))
    ctx = _make_ctx()
    result = run_agent(ctx, refine=False)
    assert len(result.steps) == 1


def test_run_agent_refine_gives_two_steps(monkeypatch: pytest.MonkeyPatch) -> None:
    import quill.core.ai.agent_session as ag

    responses = iter([("first draft", None), ("refined draft", None)])
    monkeypatch.setattr(ag, "generate_assistant_response", lambda *a, **kw: next(responses))
    ctx = _make_ctx()
    result = run_agent(ctx, refine=True)
    assert len(result.steps) == 2
    assert result.final_output == "refined draft"


def test_run_agent_cancelled_before_start(monkeypatch: pytest.MonkeyPatch) -> None:
    import quill.core.ai.agent_session as ag

    called = []
    monkeypatch.setattr(
        ag, "generate_assistant_response", lambda *a, **kw: called.append(1) or ("x", None)
    )
    ev = threading.Event()
    ev.set()
    ctx = _make_ctx(stop_event=ev)
    result = run_agent(ctx)
    assert result.cancelled is True
    assert not called  # AI was never called


def test_run_agent_raises_auth_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import quill.core.ai.agent_session as ag

    monkeypatch.setattr(
        ag, "generate_assistant_response", lambda *a, **kw: (None, "401 unauthorized")
    )
    ctx = _make_ctx()
    with pytest.raises(AgentSessionAuthError):
        run_agent(ctx)


def test_run_agent_raises_agent_error_on_generic_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    import quill.core.ai.agent_session as ag

    monkeypatch.setattr(ag, "generate_assistant_response", lambda *a, **kw: (None, "timeout"))
    ctx = _make_ctx()
    with pytest.raises(AgentSessionError):
        run_agent(ctx)


def test_run_agent_on_progress_called(monkeypatch: pytest.MonkeyPatch) -> None:
    import quill.core.ai.agent_session as ag

    monkeypatch.setattr(ag, "generate_assistant_response", lambda *a, **kw: ("done", None))
    calls = []
    ctx = _make_ctx(on_progress=lambda label, idx, total: calls.append(label))
    run_agent(ctx)
    assert len(calls) == 1
    assert calls[0] == "Generating..."


def test_run_agent_refine_fallback_on_refine_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import quill.core.ai.agent_session as ag

    responses = iter([("first draft", None), (None, "timeout during refine")])
    monkeypatch.setattr(ag, "generate_assistant_response", lambda *a, **kw: next(responses))
    ctx = _make_ctx()
    result = run_agent(ctx, refine=True)
    # Refine failed non-fatally — should keep initial output
    assert result.final_output == "first draft"
    assert result.succeeded


# ---------------------------------------------------------------------------
# assistant_agents: expand and toc profiles
# ---------------------------------------------------------------------------


def test_expand_profile_exists() -> None:
    plan = build_agent_plan("expand", selection_text="A brief outline.", document_text="")
    assert plan is not None
    assert plan.profile.agent_id == "expand"


def test_toc_profile_exists() -> None:
    plan = build_agent_plan("toc", selection_text="", document_text="# Heading 1\n## Subheading")
    assert plan is not None
    assert plan.profile.agent_id == "toc"


def test_unknown_agent_returns_none() -> None:
    plan = build_agent_plan("nonexistent_agent", selection_text="", document_text="")
    assert plan is None


def test_expand_prompt_contains_selection() -> None:
    plan = build_agent_plan("expand", selection_text="My brief outline.", document_text="")
    assert plan is not None
    assert "My brief outline." in plan.prompt


def test_toc_prompt_contains_document() -> None:
    plan = build_agent_plan(
        "toc", selection_text="", document_text="# Chapter One\n## Introduction"
    )
    assert plan is not None
    assert "Chapter One" in plan.prompt
