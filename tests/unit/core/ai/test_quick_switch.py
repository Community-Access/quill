"""Quick-switch the active AI engine (Phase 6 plumbing)."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.ai.harness import HarnessCapabilities, HarnessRegistry
from quill.core.ai.quick_switch import (
    AUTO,
    active_target,
    announce_active,
    announce_switch,
    cycle_next,
    list_targets,
    preferred_harness_id,
    set_active,
)


class _FakeHarness:
    def __init__(self, hid: str, name: str, available: bool, reason: str | None) -> None:
        self._id = hid
        self._name = name
        self._available = available
        self._reason = reason

    @property
    def id(self) -> str:
        return self._id

    @property
    def display_name(self) -> str:
        return self._name

    def is_available(self) -> tuple[bool, str | None]:
        return self._available, self._reason

    def capabilities(self) -> HarnessCapabilities:
        return HarnessCapabilities()

    def start_session(self, *args: object, **kwargs: object) -> object:  # pragma: no cover
        raise NotImplementedError


@pytest.fixture(autouse=True)
def _isolated_app_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # conftest sets _DEV_BUILD=True so QUILL_DATA_DIR is honored for isolation.
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))


def _registry() -> HarnessRegistry:
    reg = HarnessRegistry()
    reg.register(_FakeHarness("native", "Native (QUILL)", True, None))
    reg.register(_FakeHarness("openai_agents", "OpenAI Agents SDK", True, None))
    reg.register(
        _FakeHarness("copilot", "GitHub Copilot SDK", False, "Install the ai-copilot pack")
    )
    return reg


def test_default_preference_is_auto_and_runs_first_available() -> None:
    reg = _registry()
    assert preferred_harness_id() == AUTO
    active = active_target(reg)
    assert active is not None and active.harness_id == "native"


def test_list_targets_reports_readiness_and_active() -> None:
    targets = {t.harness_id: t for t in list_targets(_registry())}
    assert targets["copilot"].available is False
    assert "ai-copilot" in (targets["copilot"].reason or "")
    assert targets["native"].active is True
    assert targets["openai_agents"].active is False


def test_set_active_persists_and_changes_running_engine() -> None:
    reg = _registry()
    target = set_active(reg, "openai_agents")
    assert target.available and target.active
    assert preferred_harness_id() == "openai_agents"
    assert active_target(reg).harness_id == "openai_agents"


def test_set_active_unavailable_persists_but_does_not_run() -> None:
    reg = _registry()
    target = set_active(reg, "copilot")
    # Preference is saved (so the UI can offer onboarding) but it is not "active":
    # the running engine falls back to the first available (Native).
    assert preferred_harness_id() == "copilot"
    assert target.available is False
    assert target.active is False
    assert active_target(reg).harness_id == "native"


def test_set_active_rejects_unknown_engine() -> None:
    with pytest.raises(ValueError):
        set_active(_registry(), "does_not_exist")


def test_cycle_next_round_robins_available_only() -> None:
    reg = _registry()
    # Start on native -> next available is openai_agents (copilot is skipped).
    first = cycle_next(reg)
    assert first.harness_id == "openai_agents"
    second = cycle_next(reg)
    assert second.harness_id == "native"


def test_cycle_next_single_available_is_stable() -> None:
    reg = HarnessRegistry()
    reg.register(_FakeHarness("native", "Native (QUILL)", True, None))
    assert cycle_next(reg).harness_id == "native"
    assert cycle_next(reg).harness_id == "native"


def test_cycle_next_raises_when_nothing_available() -> None:
    reg = HarnessRegistry()
    reg.register(_FakeHarness("copilot", "GitHub Copilot SDK", False, "Install it"))
    with pytest.raises(ValueError):
        cycle_next(reg)


def test_announcements() -> None:
    reg = _registry()
    assert "Native" in announce_active(active_target(reg))
    assert announce_active(None) == "No AI engine is available."
    assert (
        announce_switch(set_active(reg, "openai_agents"))
        == "Switched AI engine to OpenAI Agents SDK."
    )
    not_ready = set_active(reg, "copilot")
    assert "not ready" in announce_switch(not_ready)
